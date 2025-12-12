import pandas as pd
import warnings
import config
import time
import datetime
import os
import utils # <--- 1. Importante: Importar o utils

# Ignora avisos do Excel
warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

# --- CONFIGURAÇÃO ---
ARQUIVO_EXCEL = 'GCO-004 - 6ª Importação - 08-12-2024_1715.xlsx' 
COLUNA_CLIENTE = 'Nome do Cliente'
ARQUIVO_RELATORIO = 'relatorio_verificacao.txt'
STATUS_ESPERADO = "Aguarda para retorno"

# --- FUNÇÕES AUXILIARES ---

def buscar_elemento_em_frames(page, seletor):
    """Procura elemento na página principal e nos iframes"""
    try:
        if page.locator(seletor).first.is_visible():
            return page.locator(seletor).first
    except:
        pass
    for frame in page.frames:
        try:
            if frame.locator(seletor).first.is_visible():
                return frame.locator(seletor).first
        except:
            continue
    return None

def realizar_pesquisa(page, termo):
    print(f"   -> [BUSCA] Pesquisando: {termo}")
    barra = buscar_elemento_em_frames(page, config.SEL_BARRA_PESQUISA)
    
    if not barra:
        barra = buscar_elemento_em_frames(page, 'input[placeholder="Pesquisar"]')
        
    if not barra:
        return False

    try:
        barra.click()
        # Limpa campo
        barra.press("Control+A")
        barra.press("Backspace")
        time.sleep(0.5)
        
        # Digita e envia
        barra.fill(termo)
        barra.press("Enter")
        return True
    except:
        return False

def verificar_status_na_linha(page, nome_cliente):
    """
    Encontra a linha do cliente e verifica se contém o texto esperado.
    """
    item_encontrado = None
    
    # 1. Procura o cliente (Texto exato ou parcial)
    loc = page.get_by_text(nome_cliente, exact=False)
    if loc.count() > 0 and loc.first.is_visible():
        item_encontrado = loc.first
    else:
        # Tenta nos frames
        for frame in page.frames:
            loc = frame.get_by_text(nome_cliente, exact=True)
            if loc.count() > 0 and loc.first.is_visible():
                item_encontrado = loc.first
                break
    
    if not item_encontrado:
        return "NAO ENCONTRADO"

    try:
        # 2. Sobe para o elemento pai (Linha TR ou DIV)
        linha = item_encontrado.locator("xpath=ancestor::tr | ancestor::div[contains(@class, 'row')] | ancestor::div[contains(@class, 'Row')]").first
        
        if linha.count() == 0:
            linha = item_encontrado.locator("xpath=..") # Pai imediato se não achar estrutura de linha

        texto_linha = linha.inner_text()
        
        # 3. Verifica se o status esperado está no texto da linha
        if STATUS_ESPERADO.lower() in texto_linha.lower():
            return f"CONFIRMADO ({STATUS_ESPERADO})"
        else:
            # Pega os primeiros 50 chars para dar uma dica do que está escrito lá
            texto_limpo = texto_linha.replace('\n', ' ')[:50]
            return f"DIVERGENTE (Encontrado: {texto_limpo}...)"
            
    except Exception as e:
        return f"ERRO LEITURA: {e}"

def escrever_relatorio(mensagem):
    with open(ARQUIVO_RELATORIO, "a", encoding="utf-8") as f:
        f.write(mensagem + "\n")

# --- FUNÇÃO PRINCIPAL CHAMADA PELA MAIN ---
def executar(page):
    print("--> [TAREFA 03] Iniciando Auditoria de Status...")
    
    # Prepara o arquivo de relatório (Sobrescreve o anterior com "w")
    with open(ARQUIVO_RELATORIO, "w", encoding="utf-8") as f:
        f.write(f"RELATÓRIO DE AUDITORIA - {datetime.datetime.now()}\n")
        f.write("="*60 + "\n")

    # Lê o Excel
    try:
        df = pd.read_excel(ARQUIVO_EXCEL)
        df.columns = df.columns.str.strip()
        # O print de total de registros agora é feito dentro do utils.fatiar_dataframe
    except Exception as e:
        print(f"ERRO CRÍTICO AO LER EXCEL: {e}")
        return

    # --- 2. CHAMADA DO MÉTODO CENTRALIZADO ---
    # Pergunta ao usuário quantas linhas processar
    df_processamento = utils.fatiar_dataframe(df)
    # -----------------------------------------

    print("--> [SISTEMA] Aguardando estabilização da página...")
    page.wait_for_load_state("networkidle")
    time.sleep(3)

    # Loop de processamento (Itera sobre o DF fatiado)
    for index, row in df_processamento.iterrows():
        
        try:
            nome_cliente = str(row[COLUNA_CLIENTE]).strip()
        except:
            continue
        
        # Pula vazios
        if not nome_cliente or nome_cliente.lower() == 'nan': 
            continue

        # index+1 dá o número real da linha do Excel (pois o índice original é preservado)
        print(f"\nVerificando [Linha {index+1}]: {nome_cliente}")
        
        # 1. Realiza a pesquisa na grid
        if realizar_pesquisa(page, nome_cliente):
            time.sleep(2) # Tempo para a grid filtrar
            
            # 2. Verifica o status visualmente
            resultado = verificar_status_na_linha(page, nome_cliente)
            
            print(f"   -> Status: {resultado}")
            
            # 3. Salva no TXT
            escrever_relatorio(f"[Linha {index+1}] {nome_cliente}: {resultado}")
            
        else:
            print("   -> [ERRO] Falha ao tentar pesquisar na barra.")
            escrever_relatorio(f"[Linha {index+1}] {nome_cliente}: ERRO DE PESQUISA (Barra não encontrada)")

        # Limpa o foco para a próxima iteração
        page.bring_to_front()

    print(f"\n--> Auditoria finalizada. Verifique o arquivo: {ARQUIVO_RELATORIO}")