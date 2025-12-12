import sys
from playwright.sync_api import sync_playwright
import config
from auth import Autenticador
import utils
import time

# Importa as tarefas (certifique-se que os arquivos existem na pasta)
try:
    
    from tarefas import tarefa_01, tarefa_02, tarefa_03
    
except ImportError as e:
    print(f"ERRO: Faltando arquivo de tarefa. {e}")

def exibir_menu():
    print("\n" + "="*40)
    print("🤖 CENTRAL DE AUTOMAÇÃO SOFTEXPERT 🤖")
    print("="*40)
    print("1. Cancelar GCOs (Duplicidade)")
    print("2. Executar Atividade (Aguarda Retorno)")
    print("3. Auditoria de Status (Gerar Relatório)")
    print("0. Sair")
    print("="*40)
    
    try:
        opcao = input("Escolha uma opção: ")
        return  opcao
    except EOFError:
        # Se rodar no Docker sem modo interativo, retorna None
        return None

def main():
    # Se estiver no Docker, podemos passar o ID da tarefa como argumento
    # Ex: docker compose run robo python main.py 3
    opcao_automatica = sys.argv[1] if len(sys.argv) > 1 else None

    # 1. Escolha da Tarefa
    if opcao_automatica:
        escolha = opcao_automatica
        print(f"--> [AUTO] Iniciando tarefa {escolha} via argumento.")
    else:
        escolha = exibir_menu()

    if escolha not in ['1', '2', '3']:
        print("Saindo...")
        return

    # 2. Inicialização do Navegador (Centralizada)
    with sync_playwright() as p:
        # Usa o utils para configurar (Headless ou Não) automaticamente
        context = utils.configurar_contexto(p)
        page = context.pages[0]

        # 3. Autenticação (Centralizada)
        auth = Autenticador(page)
        try:
            auth.realizar_login()
        except Exception as e:
            print(f"Falha fatal no login: {e}")
            return

        # 4. Navegação Inicial (Garante que está na Home/Workspace)
        if config.URL_LOGIN not in page.url:
            page.goto(config.URL_LOGIN)
        
        # 5. Roteamento para a Tarefa Específica
        if escolha == '1':
            # Renomeie seu arquivo antigo de cancelar gco para tarefa_01.py
            if hasattr(tarefa_01, 'executar'):
                tarefa_01.executar(page)
            else:
                print("Erro: tarefa_01 não tem função executar()")

        elif escolha == '2':
            # Vai para a tela de Execução de Tarefas
            print("--> [NAVEGAÇÃO] Indo para tela de Execução...")
            page.goto("https://pemi.softexpert.com/softexpert/workspace?page=execution,104,1")
            
            # Chama a função executar do arquivo tarefa_02.py
            tarefa_02.executar(page)
        elif escolha == '3':
            # A tarefa 03 usa a mesma url da 01 (Home), então não precisa navegar
            tarefa_03.executar(page)

        print("\n✅ Fluxo Encerrado.")
        
        # No Docker não pedimos input para fechar
        if not utils.esta_no_docker():
            input("Pressione Enter para fechar...")
        
        context.close()

if __name__ == "__main__":
    main()