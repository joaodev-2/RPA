import sys
import os
from datetime import datetime
from dotenv import load_dotenv # <--- IMPORT NOVO

from src.database import DatabaseHandler, Imovel, DebitoIPTU
from src.handlers.data_manager import TemporaryDataHandler
from src.core.scraper import IPTUScraper

# --- CARREGAR VARIÁVEIS DE AMBIENTE ---
load_dotenv() # Isso lê o arquivo .env e joga na memória

# Pega do .env ou lança erro se não existir
DB_CONNECTION = os.getenv("DB_CONNECTION")
if not DB_CONNECTION:
    print("❌ ERRO: A variável DB_CONNECTION não foi encontrada no arquivo .env")
    sys.exit(1)

# Pega URL do .env ou usa um valor padrão (se você preferir manter no código)
URL_ALVO = os.getenv("URL_ALVO")

def processar_imovel(session, scraper, temp_handler, codigo_reduzido):
    print(f"\n🏠 --- Iniciando Imóvel: {codigo_reduzido} ---")

    # 1. Busca ou cria o imóvel no banco
    imovel = session.query(Imovel).filter_by(codigo_reduzido=codigo_reduzido).first()
    if not imovel:
        imovel = Imovel(codigo_reduzido=codigo_reduzido)
        session.add(imovel)
        session.commit()
    
    # 2. Extração via Playwright
    dados_brutos = scraper.extrair_dados(codigo_reduzido)
    
    if not dados_brutos:
        print(f"❌ Falha na extração do imóvel {codigo_reduzido}")
        imovel.status = "ERRO_EXTRACAO"
        imovel.data_atualizacao = datetime.now()
        session.commit()
        return False

    # 3. Backup do JSON bruto
    temp_handler.salvar_json_cru(codigo_reduzido, dados_brutos)

    # 4. Parse e Salvamento no Banco
    try:
        # Limpa débitos antigos para refresh
        for debito in imovel.debitos:
            session.delete(debito)
        
        # Pega a lista (Ajuste a chave 'debitos' conforme seu JSON)
        lista_debitos = dados_brutos.get('debitos', []) 
        
        for d in lista_debitos:
            novo_debito = DebitoIPTU(
                ano=d.get('ano'),
                parcela=d.get('parcela'),
                valor=d.get('valor'), 
                vencimento=d.get('vencimento'),
                situacao=d.get('situacao'),
                link_boleto=d.get('linkBoleto'), 
                imovel=imovel
            )
            session.add(novo_debito)

        imovel.status = "SUCESSO"
        imovel.data_atualizacao = datetime.now()
        
        session.commit()
        print(f"✅ Imóvel {codigo_reduzido} atualizado com {len(lista_debitos)} débitos!")
        return True

    except Exception as e:
        session.rollback()
        print(f"💥 Erro ao salvar no banco: {e}")
        return False

def main():
    print("🏁 Inicializando Sistema RPA IPTU Lavras...")
    print(f"🔧 Ambiente carregado. Banco: PostgreSQL")

    try:
        # Inicializa infraestrutura
        db = DatabaseHandler(DB_CONNECTION)
        db.init_db() 
        session = db.get_session()
        
        temp_handler = TemporaryDataHandler()
        scraper = IPTUScraper(URL_ALVO)
    except Exception as e:
        print(f"❌ Erro Crítico na inicialização: {e}")
        sys.exit(1)

    # Lista de Imóveis para processar
    # Futuramente você pode ler isso de um arquivo txt ou csv
    lista_codigos = ["2166"] 

    sucessos = 0
    erros = 0

    for codigo in lista_codigos:
        resultado = processar_imovel(session, scraper, temp_handler, codigo)
        if resultado:
            sucessos += 1
        else:
            erros += 1

    print("\n" + "="*40)
    print(f"📊 Resumo Final:")
    print(f"✅ Sucessos: {sucessos}")
    print(f"❌ Erros: {erros}")
    print("="*40)
    
    session.close()

if __name__ == "__main__":
    main()