import pandas as pd
import warnings
import config
import time
import os
import utils  # <--- Import do Fatiador

# Ignora avisos do Excel
warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

# --- CONFIGURAÇÃO ---
ARQUIVO_EXCEL = 'GCO-004 - 6ª Importação - 08-12-2024_1715.xlsx'
COLUNA_CLIENTE = 'Nome do Cliente'
SRC_ICONE_CANCELADO = "cancelado.png"
SELETOR_BARRA_RAPIDA = '#bc_quick_filter'

# Configuração de Performance
ITENS_PARA_REFRESH = 25  
TIMEOUT_PACIENCIA = 120000 

# --- FUNÇÃO PARA LIDAR COM ALERTS (POP-UPS DE AVISO) ---
def lidar_com_alerta(dialog):
    print(f"   -> [ALERTA DETECTADO] Mensagem: {dialog.message}")
    try:
        dialog.accept() # Clica em OK
        print("   -> [AÇÃO] Alerta aceito (OK pressionado).")
    except:
        pass

def formatar_valor(valor):
    if pd.isna(valor): return ""
    return str(valor).strip()

def buscar_elemento_em_frames(page, seletor, timeout=5000):
    try:
        loc = page.locator(seletor).first
        if loc.is_visible(timeout=timeout): return loc
    except: pass
    for frame in page.frames:
        try:
            loc = frame.locator(seletor).first
            if loc.is_visible(timeout=timeout): return loc
        except: continue
    return None

def clicar_filtro_escrituracao(page):
    print("--> [AÇÃO] Procurando filtro 'Escrituração de Lotes'...")
    texto_filtro = "Escrituração de Lotes"
    inicio = time.time()
    
    while time.time() - inicio < (TIMEOUT_PACIENCIA / 1000):
        try:
            alvo = page.locator(".listsItem").filter(has_text=texto_filtro).first
            if alvo.is_visible():
                alvo.click()
                return True
        except: pass

        for frame in page.frames:
            try:
                alvo = frame.locator(".listsItem").filter(has_text=texto_filtro).first
                if alvo.is_visible():
                    alvo.click()
                    return True
            except: continue
        time.sleep(1)
    return False

def realizar_pesquisa_rapida(page, termo):
    print(f"   -> [BUSCA] Procurando barra '{SELETOR_BARRA_RAPIDA}'...")
    barra = None
    inicio = time.time()
    while not barra and (time.time() - inicio < (TIMEOUT_PACIENCIA / 1000)):
        barra = buscar_elemento_em_frames(page, SELETOR_BARRA_RAPIDA, timeout=1000)
        if not barra: time.sleep(1)
    
    if not barra: raise Exception("Barra de pesquisa não carregou.")

    try:
        barra.click()
        barra.press("Control+A")
        barra.press("Backspace")
        time.sleep(0.5) 
        barra.fill(termo)
        time.sleep(0.5)
        barra.press("Enter")
        print(f"   -> [BUSCA] '{termo}' enviado.")
    except Exception as e:
        raise Exception(f"Erro na barra: {e}")

def verificar_grid_vazia(page):
    mensagem = "Não encontramos nenhum resultado"
    if page.get_by_text(mensagem).is_visible(): return True
    for frame in page.frames:
        if frame.get_by_text(mensagem).is_visible(): return True
    return False

def localizar_item_na_grid(page, nome_cliente):
    for _ in range(10):
        if verificar_grid_vazia(page):
            print("   -> [INFO] Mensagem 'Não encontramos nenhum resultado' detectada.")
            return "VAZIO"

        loc = page.get_by_text(nome_cliente, exact=False)
        if loc.count() > 0 and loc.first.is_visible():
            return loc.first
        
        for frame in page.frames:
            loc_frame = frame.get_by_text(nome_cliente, exact=False)
            if loc_frame.count() > 0 and loc_frame.first.is_visible():
                return loc_frame.first
        
        time.sleep(1)
    return None

def executar(page):
    print(f"--> [TAREFA 02] Lendo Excel: {ARQUIVO_EXCEL}")
    try:
        df = pd.read_excel(ARQUIVO_EXCEL)
        df.columns = df.columns.str.strip()
    except Exception as e:
        print(f"ERRO EXCEL: {e}")
        return

    # --- 1. FATIADOR (Pergunta quantidade) ---
    df_processamento = utils.fatiar_dataframe(df)
    # -----------------------------------------

    # --- 2. VIGILANTE DE ALERTS ---
    # Se aparecer qualquer window.alert, clica em OK automaticamente
    page.on("dialog", lidar_com_alerta)
    # ------------------------------

    page.set_default_timeout(TIMEOUT_PACIENCIA)
    
    def resetar_ambiente():
        print("--> [REFRESH] Carregando página...")
        page.goto("https://pemi.softexpert.com/softexpert/workspace?page=execution,104,1")
        try: page.wait_for_load_state("networkidle", timeout=60000)
        except: pass
        clicar_filtro_escrituracao(page)
        time.sleep(5) 

    resetar_ambiente()
    print("\n--- INICIANDO LOOP ---")
    
    itens_processados = 0

    for index, row in df_processamento.iterrows():
        # Índice real do Excel
        idx_excel = index + 1

        if itens_processados > 0 and itens_processados % ITENS_PARA_REFRESH == 0:
            print(f"\n--- [REFRESH] Limpeza de memória (Item {itens_processados}) ---")
            try: resetar_ambiente()
            except: pass
        
        try:
            nome_cliente = str(row[COLUNA_CLIENTE]).strip()
        except: continue
        
        if not nome_cliente or nome_cliente.lower() == 'nan': continue

        print(f"\n[Linha {idx_excel}] Cliente: {nome_cliente}")
        itens_processados += 1
        
        try:
            # 1. PESQUISA
            realizar_pesquisa_rapida(page, nome_cliente)
            time.sleep(2)

            # 2. LOCALIZAR
            resultado_localizacao = localizar_item_na_grid(page, nome_cliente)

            if resultado_localizacao == "VAZIO":
                print("   -> [PULADO] Cliente não consta na base (Sem resultados).")
                continue 
            
            if not resultado_localizacao:
                print("   -> [ERRO] Cliente não encontrado (Timeout de busca).")
                continue

            item_locator = resultado_localizacao

            # 3. ABRIR TAREFA
            print("   -> [AÇÃO] Abrindo atividade...")
            item_locator.scroll_into_view_if_needed()
            
            # Aqui pode ocorrer o Alert. O 'page.on("dialog")' configurado acima vai lidar com ele.
            with page.context.expect_page(timeout=TIMEOUT_PACIENCIA) as evento_janela:
                item_locator.dblclick()
            
            nova_pagina = evento_janela.value
            nova_pagina.wait_for_load_state(timeout=TIMEOUT_PACIENCIA)
            print("   -> [JANELA] Carregada.")

            # 4. CLICAR NO BOTÃO
            print("   -> [AÇÃO] Aguardando botão...")
            btn = None
            try:
                nova_pagina.wait_for_selector('span[style*="13.png"]', state="visible", timeout=10000)
                btn = nova_pagina.locator('span[style*="13.png"]').first
            except: pass
            
            if not btn:
                try:
                    nova_pagina.wait_for_selector("span.x-btn-inner:has-text('Aguarda para')", state="visible", timeout=5000)
                    btn = nova_pagina.locator('span.x-btn-inner').filter(has_text="Aguarda para").first
                except: pass

            if btn and btn.is_visible():
                time.sleep(1) 
                btn.click(force=True)
                print("   -> [SUCESSO] Botão clicado!")
                time.sleep(3) 
                try: nova_pagina.close()
                except: pass
            else:
                print("   -> [ERRO] Botão não encontrado.")
                if os.getenv("MODO_DOCKER") == "true":
                    nova_pagina.screenshot(path=f"erro_janela_{idx_excel}.png")
                nova_pagina.close()

            page.bring_to_front()
            
        except Exception as e:
            print(f"   -> [FALHA] {e}")
            try: nova_pagina.close()
            except: pass
            try: page.bring_to_front() 
            except: pass

    print("--> Tarefa 02 concluída.")