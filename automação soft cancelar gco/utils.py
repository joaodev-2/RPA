import os
import config
from playwright.sync_api import BrowserContext

def esta_no_docker():
    """Retorna True se estiver rodando no container, False no Windows."""
    return os.getenv("MODO_DOCKER") == "true"

def configurar_contexto(playwright_instance) -> BrowserContext:
    """
    Cria o navegador já configurado com base no ambiente (PC ou Docker).
    """
    headless_mode = esta_no_docker()
    
    print(f"--> [SETUP] Ambiente Docker: {headless_mode} | Headless: {headless_mode}")

    # Argumentos para evitar quebra no Docker
    args_navegador = ["--start-maximized"] if not headless_mode else ["--no-sandbox", "--disable-setuid-sandbox"]
    
    context = playwright_instance.chromium.launch_persistent_context(
        user_data_dir=config.DIR_PERFIL,
        headless=headless_mode,
        args=args_navegador,
        viewport={'width': 1920, 'height': 1080} if headless_mode else None
    )
    
    return context

# --- NOVA FUNÇÃO GLOBAL ---
def fatiar_dataframe(df):
    """
    Pergunta ao usuário o intervalo de execução e retorna o DataFrame fatiado.
    """
    total_linhas = len(df)
    start_index = 0
    end_index = total_linhas

    print("\n" + "="*50)
    print(" ⚙️  CONFIGURAÇÃO DE EXECUÇÃO")
    print("="*50)
    print(f"--> Registros disponíveis no arquivo: {total_linhas}")

    # Se estiver rodando sem terminal interativo (ex: cronjob), pula perguntar
    # Mas como você usa 'docker run -it', vai funcionar.
    try:
        entrada_inicio = input(f"Começar de qual linha? (Padrão 0): ")
        if entrada_inicio.strip():
            start_index = int(entrada_inicio)
        
        entrada_qtd = input(f"Quantos registros processar? (Enter = Todos): ")
        if entrada_qtd.strip():
            end_index = start_index + int(entrada_qtd)
            
        # Proteção para não estourar o limite
        if start_index < 0: start_index = 0
        if end_index > total_linhas: end_index = total_linhas
            
    except (EOFError, ValueError):
        print("--> [AVISO] Entrada não detectada ou inválida. Processando arquivo inteiro.")
        start_index = 0
        end_index = total_linhas

    # Realiza o corte (Slice)
    df_fatiado = df.iloc[start_index:end_index]
    
    print(f"--> [CONFIG] Processando: Linha {start_index} até {end_index} ({len(df_fatiado)} itens).")
    print("="*50 + "\n")

    return df_fatiado