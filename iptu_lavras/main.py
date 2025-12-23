import sys
import os
import traceback
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

from sqlalchemy import text # Importante para teste de conexão
from src.database import DatabaseHandler, Imovel, DebitoIPTU
from src.handlers.data_manager import TemporaryDataHandler
from src.core.scraper import IPTUScraper

# --- CONFIGURAÇÃO ---
BOLETOS_DIR = Path("data/boletos")
load_dotenv()

def debug_print(msg, icone="🔍"):
    print(f"{icone} {msg}")

def processar_imovel(session, scraper, temp_handler, codigo_reduzido):
    debug_print(f"--- Iniciando processamento do Imóvel: {codigo_reduzido} ---", "🏠")

    # 1. Teste de existência do imóvel
    try:
        imovel = session.query(Imovel).filter_by(codigo_reduzido=str(codigo_reduzido)).first()
        if not imovel:
            debug_print("Imóvel não existe no banco. Criando novo...", "🆕")
            imovel = Imovel(codigo_reduzido=str(codigo_reduzido))
            session.add(imovel)
            session.commit()
            debug_print(f"Imóvel criado com ID: {imovel.id}", "✅")
        else:
            debug_print(f"Imóvel encontrado com ID: {imovel.id}", "📌")
    except Exception as e:
        debug_print(f"ERRO ao acessar/criar imóvel: {e}", "❌")
        traceback.print_exc()
        return False

    # 2. Executar Scraper
    debug_print("Chamando scraper...", "🚀")
    dados_brutos = scraper.extrair_dados(codigo_reduzido)
    
    if not dados_brutos:
        debug_print("Scraper retornou VAZIO (None). Abortando.", "💀")
        return False

    # 3. Validar JSON
    if "guia" not in dados_brutos:
        debug_print(f"JSON inválido! Chaves encontradas: {list(dados_brutos.keys())}", "⚠️")
        return False
    
    lista_parcelas = dados_brutos["guia"][0].get("parcelaIPTU", [])
    debug_print(f"O JSON contém {len(lista_parcelas)} itens em 'parcelaIPTU'", "📋")

    # 4. Processar Débitos
    debitos_adicionados = 0
    try:
        # Limpar antigos
        num_deletados = session.query(DebitoIPTU).filter_by(imovel_id=imovel.id).delete()
        debug_print(f"Limpando {num_deletados} débitos antigos do banco.", "🧹")
        
        for p in lista_parcelas:
            # Filtra Pagos
            linha_dig = p.get("linhaDigitavel", "").upper()
            num = p.get("numero")
            
            if "GUIA PAGA" in linha_dig or "NÃO RECEBER" in linha_dig:
                continue
            
            # --- NOVA LÓGICA DE ARQUIVO BINÁRIO ---
            venc = p.get('vencimento')
            nome_pdf = f"boleto_{codigo_reduzido}_parc{num}_{venc}.pdf"
            caminho_completo = BOLETOS_DIR / nome_pdf
            
            conteudo_binario = None
            
            if caminho_completo.exists():
                debug_print(f"Parcela {num}: Lendo binário do arquivo... ({nome_pdf})", "📥")
                try:
                    # 'rb' = Read Binary (Lê os bytes do arquivo)
                    with open(caminho_completo, "rb") as arquivo_pdf:
                        conteudo_binario = arquivo_pdf.read()
                    debug_print(f"   -> Leitura OK! ({len(conteudo_binario)} bytes carregados na memória)", "✅")
                except Exception as erro_leitura:
                    debug_print(f"   -> ERRO ao ler arquivo: {erro_leitura}", "⚠️")
            else:
                debug_print(f"Parcela {num}: PDF NÃO ACHADO no disco. Banco ficará sem anexo.", "🚫")
                
                # Debug extra de diretório se falhar
                if debitos_adicionados == 0: 
                    try:
                        arquivos = os.listdir(BOLETOS_DIR)
                        debug_print(f"Arquivos na pasta: {arquivos}", "📂")
                    except:
                        debug_print("Pasta data/boletos não existe!", "😱")

            # Criar Objeto no Banco
            novo_debito = DebitoIPTU(
                ano=p.get('ano'),
                parcela=num,
                valor=p.get('totalParcela'),
                vencimento=venc,
                situacao="Aberto",
                # MUDANÇA AQUI: Passamos os bytes, não o link
                boleto_pdf=conteudo_binario, 
                imovel=imovel
            )
            session.add(novo_debito)
            debitos_adicionados += 1

        # 5. Commit Final
        if debitos_adicionados > 0:
            session.commit()
            debug_print(f"SUCESSO! {debitos_adicionados} débitos salvos no banco (com BLOBs).", "💾")
        else:
            debug_print("Nenhum débito em aberto encontrado para salvar.", "🤷")
            
        return True

    except Exception as e:
        session.rollback()
        debug_print(f"ERRO CRÍTICO AO SALVAR NO BANCO: {e}", "🔥")
        traceback.print_exc() 
        return False

def main():
    print("\n" + "="*40)
    print("🏁 INICIANDO DEBUGGER DO SISTEMA (MODO BLOB)")
    print("="*40)

    # 1. Testar Variáveis de Ambiente
    db_conn = os.getenv("DB_CONNECTION")
    if not db_conn:
        debug_print("ERRO: .env não carregado ou DB_CONNECTION vazio!", "❌")
        sys.exit(1)
    
    # 2. Testar Conexão com Banco
    try:
        db = DatabaseHandler(db_conn)
        db.init_db()
        session = db.get_session()
        
        # Teste real de SQL
        session.execute(text("SELECT 1"))
        debug_print("Conexão com Banco de Dados: OK!", "🔌")
    except Exception as e:
        debug_print(f"FALHA AO CONECTAR NO BANCO: {e}", "💥")
        debug_print("Verifique se o container 'db' está rodando e se a senha no .env está certa.", "💡")
        sys.exit(1)

    # 3. Iniciar Processo
    temp_handler = TemporaryDataHandler()
    scraper = IPTUScraper(os.getenv("URL_ALVO"))
    
    codigos = ["2166"] 
    
    for c in codigos:
        processar_imovel(session, scraper, temp_handler, c)
    
    session.close()
    print("\n🏁 Fim do Debug.")

if __name__ == "__main__":
    main()