import pandas as pd
import warnings
import config
import time
import os
import utils  # <--- Importante: Importando o utils

# Ignora avisos do Excel
warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

# --- CONFIGURAÇÃO ESPECÍFICA DESTA TAREFA ---
ARQUIVO_EXCEL = 'Cancelar+-+GCO-004.xlsx'
COLUNA_EXCEL = 'Identificador'
SRC_ICONE_CANCELADO = "cancelado.png"

# Configuração de Performance
TIMEOUT_PACIENCIA = 120000  # 2 minutos de tolerância para lentidão

# --- FUNÇÕES AUXILIARES ---
def formatar_valor(valor):
    valor = str(valor).strip()
    if len(valor) > 3 and "-" not in valor:
        return f"{valor[:3]}-{valor[3:]}"
    return valor

def buscar_elemento_em_frames(page, seletor):
    try:
        if page.locator(seletor).first.is_visible():
            return page.locator(seletor).first
    except: pass
    for frame in page.frames:
        try:
            if frame.locator(seletor).first.is_visible():
                return frame.locator(seletor).first
        except: continue
    return None

def realizar_pesquisa(page, termo):
    print(f"   -> [BUSCA] Procurando barra...")
    barra = buscar_elemento_em_frames(page, config.SEL_BARRA_PESQUISA)
    
    if not barra:
        barra = buscar_elemento_em_frames(page, 'input[placeholder="Pesquisar"]')
        
    if not barra:
        raise Exception("Barra de pesquisa não encontrada!")

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

def verificar_icone_cancelado(item_locator):
    try:
        linha = item_locator.locator("xpath=ancestor::tr | ancestor::div[contains(@class, 'row')] | ancestor::div[contains(@class, 'Row')]").first
        if linha.count() == 0:
            linha = item_locator.locator("xpath=..")

        icone = linha.locator(f'img[src*="{SRC_ICONE_CANCELADO}"]').first
        if icone.is_visible(): return True
        return False
    except:
        return False

def localizar_item_com_insistencia(page, termo):
    for tentativa in range(5): 
        # 1. Procura na Principal
        loc = page.get_by_text(termo, exact=False)
        if loc.count() > 0 and loc.first.is_visible():
            return loc.first
        
        # 2. Procura nos Frames
        for frame in page.frames:
            loc_frame = frame.get_by_text(termo, exact=False)
            if loc_frame.count() > 0 and loc_frame.first.is_visible():
                return loc_frame.first
        
        print(f"   -> [SCROLL] Item não visível. Rolando lista... ({tentativa+1}/5)")
        try:
            page.mouse.click(500, 500) 
            page.keyboard.press("PageDown")
            page.wait_for_timeout(1000)
        except:
            pass
            
    return None

# --- FUNÇÃO PRINCIPAL CHAMADA PELA MAIN ---
def executar(page):
    print(f"--> [TAREFA 01] Lendo Excel: {ARQUIVO_EXCEL}")
    try:
        df = pd.read_excel(ARQUIVO_EXCEL)
        # O print de total é feito no utils agora
    except Exception as e:
        print(f"ERRO EXCEL: {e}")
        return

    # 1. FATIADOR (Pergunta quantidade)
    df_processamento = utils.fatiar_dataframe(df)

    # --- 2. INPUT DE JUSTIFICATIVA (NOVIDADE) ---
    print("\n" + "="*40)
    print("📝 CONFIGURAÇÃO DA TAREFA")
    print("="*40)
    
    texto_padrao = "Documentos assinados e enviados no e-mail"
    texto_usuario = input(f"Digite a justificativa (Enter para usar padrão): ")
    
    # Se o usuário digitar algo, usa o que ele digitou. Se der enter vazio, usa o padrão.
    justificativa_final = texto_usuario.strip() if texto_usuario.strip() else texto_padrao
    
    print(f"--> [CONFIG] Justificativa definida: '{justificativa_final}'")
    print("="*40 + "\n")
    # --------------------------------------------

    # Configura paciência para rede lenta
    page.set_default_timeout(TIMEOUT_PACIENCIA)

    print("\n--- INICIANDO PROCESSAMENTO ---")
    page.wait_for_load_state("networkidle")
    time.sleep(3) 
    
    # Itera sobre o DataFrame fatiado
    for index, row in df_processamento.iterrows():
        
        valor_original = row[COLUNA_EXCEL]
        valor_formatado = formatar_valor(valor_original)
        
        # index+1 é a linha real do Excel
        print(f"\n[Linha {index+1}] Item: {valor_formatado}")
        
        try:
            # PESQUISA
            realizar_pesquisa(page, valor_formatado)
            page.wait_for_timeout(2000) 

            # LOCALIZAR
            item_locator = localizar_item_com_insistencia(page, valor_formatado)
            
            # RETRY DE PESQUISA
            if not item_locator:
                print("   -> [RETRY] Tentando pesquisar novamente...")
                barra = buscar_elemento_em_frames(page, config.SEL_BARRA_PESQUISA)
                if barra:
                    barra.click()
                    barra.fill("")
                    time.sleep(0.5)
                    barra.type(valor_formatado, delay=100)
                    barra.press("Enter")
                    page.wait_for_timeout(3000)
                    item_locator = localizar_item_com_insistencia(page, valor_formatado)

            if not item_locator:
                print("   -> [ERRO] Item não encontrado.")
                continue

            # CHECK DE CANCELAMENTO
            if verificar_icone_cancelado(item_locator):
                print(f"   -> [PULADO] Já cancelado (ícone detectado).")
                continue 

            # CLICAR BOTÃO DIREITO
            item_locator.scroll_into_view_if_needed()
            item_locator.click(button="right")

            # MENU
            try:
                page.get_by_text("Alterar situação").first.click(timeout=4000)
            except:
                clicou = False
                for frame in page.frames:
                    try:
                        frame.get_by_text("Alterar situação").first.click(timeout=500)
                        clicou = True; break
                    except: continue
                if not clicou: raise Exception("Menu sumiu.")
            
            # POPUP
            with page.context.expect_page(timeout=TIMEOUT_PACIENCIA) as evento_janela:
                pass 
            
            nova_pagina = evento_janela.value
            nova_pagina.wait_for_load_state()
            
            # CONFIRMAÇÃO EXTRA
            opcao_cancelar = nova_pagina.get_by_label("Cancelar").first
            if not opcao_cancelar.count():
                opcao_cancelar = nova_pagina.get_by_text("Cancelar").first

            if opcao_cancelar.is_disabled():
                print(f"   -> [PULADO] Opção desabilitada no popup.")
                nova_pagina.close()
                page.bring_to_front()
                continue 
            
            # EXECUTAR
            opcao_cancelar.click()
            
            # --- PREENCHIMENTO COM A VARIÁVEL ---
            nova_pagina.locator("textarea").fill(justificativa_final) 
            # ------------------------------------
            
            nova_pagina.keyboard.press("Tab")
            nova_pagina.keyboard.press("Enter")
            
            print(f"   -> [SUCESSO] Cancelado.")
            
            # RETORNAR
            page.bring_to_front()
            
        except Exception as e:
            print(f"   -> [FALHA] {e}")
            try: nova_pagina.close()
            except: pass
            try: page.bring_to_front() 
            except: pass

    print("--> Tarefa 01 concluída.")