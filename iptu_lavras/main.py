import sys
import os
import traceback
import copy  # <--- IMPORTANTE: Adicione isso no topo
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import text 

from src.database import DatabaseHandler, Imovel, DebitoIPTU
from src.core.scraper import IPTUScraper

load_dotenv()

def processar_imovel(session, scraper, codigo_reduzido):
    print(f"Processando imóvel: {codigo_reduzido}...")

    try:
        # 1. Busca ou Cria o Imóvel
        imovel = session.query(Imovel).filter_by(codigo_reduzido=str(codigo_reduzido)).first()
        if not imovel:
            imovel = Imovel(codigo_reduzido=str(codigo_reduzido))
            session.add(imovel)
            session.commit()

        # 2. Scraper (Retorna dados + Bytes)
        dados_com_bytes = scraper.extrair_dados(codigo_reduzido)
        
        if not dados_com_bytes:
            print(f"Erro: Scraper não retornou dados para {codigo_reduzido}.")
            return False

        # --- CORREÇÃO DO ERRO JSON SERIALIZABLE ---
        # Criamos uma cópia para salvar no histórico (JSONB) removendo os bytes
        dados_para_auditoria = copy.deepcopy(dados_com_bytes)
        
        if "guia" in dados_para_auditoria:
            for guia in dados_para_auditoria["guia"]:
                for parcela in guia.get("parcelaIPTU", []):
                    # Removemos o campo binário da cópia de auditoria
                    if "blob_pdf" in parcela:
                        del parcela["blob_pdf"]
        
        imovel.dados_brutos = dados_para_auditoria # Agora salva sem erro!
        imovel.data_atualizacao = datetime.now()
        imovel.status = "PROCESSANDO"
        session.commit()
        # ------------------------------------------

        # 3. Processamento dos Débitos (Usamos 'dados_com_bytes' que ainda tem os PDFs)
        if "guia" in dados_com_bytes:
            lista_parcelas = dados_com_bytes["guia"][0].get("parcelaIPTU", [])
            
            session.query(DebitoIPTU).filter_by(imovel_id=imovel.id).delete()
            
            debitos_para_adicionar = []

            for p in lista_parcelas:
                linha_dig = p.get("linhaDigitavel", "").upper()
                if "GUIA PAGA" in linha_dig or "NÃO RECEBER" in linha_dig:
                    continue
                
                # Aqui pegamos os bytes da variável original
                conteudo_binario = p.get('blob_pdf')

                novo_debito = DebitoIPTU(
                    ano=p.get('ano'),
                    parcela=p.get('numero'),
                    valor=p.get('totalParcela'),
                    vencimento=p.get('vencimento'),
                    situacao="Aberto",
                    boleto_pdf=conteudo_binario, # Salva o PDF na tabela certa (DebitoIPTU)
                    imovel=imovel
                )
                debitos_para_adicionar.append(novo_debito)

            if debitos_para_adicionar:
                session.add_all(debitos_para_adicionar)
                imovel.status = "SUCESSO"
                print(f" -> {len(debitos_para_adicionar)} débitos salvos.")
            else:
                imovel.status = "SEM_DEBITOS"
                print(" -> Nenhum débito em aberto.")
            
            session.commit()
            return True

    except Exception as e:
        session.rollback()
        print(f"Erro crítico no processamento do imóvel {codigo_reduzido}: {e}")
        traceback.print_exc()
        return False

def main():
    db_conn = os.getenv("DB_CONNECTION")
    if not db_conn:
        print("Erro: DB_CONNECTION ausente.")
        sys.exit(1)

    try:
        db = DatabaseHandler(db_conn)
        db.init_db()
        session = db.get_session()
        session.execute(text("SELECT 1"))
    except Exception as e:
        print(f"Erro de conexão: {e}")
        sys.exit(1)

    scraper = IPTUScraper(os.getenv("URL_ALVO"))
    
    lista_codigos = ["2166"] 
    
    for codigo in lista_codigos:
        processar_imovel(session, scraper, codigo)
    
    session.close()
    print("Processamento finalizado.")

if __name__ == "__main__":
    main()