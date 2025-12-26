import sys
import os
import copy
import time  # <--- IMPORTANTE: Adicionado para o sleep
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import text
from loguru import logger 

from src.database import DatabaseHandler, Imovel, DebitoIPTU
from src.core.scraper import IPTUScraper

load_dotenv()

# --- CONFIGURAÇÃO DO LOGGER ---
logger.remove()
logger.add(sys.stderr, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>")
os.makedirs("logs", exist_ok=True)
logger.add(
    "logs/robo_iptu_{time:YYYY-MM-DD}.log", 
    rotation="00:00",      
    level="INFO",          
    encoding="utf-8"
)
# ------------------------------

# Função auxiliar para formatar datas (DD-MM-YYYY -> YYYY-MM-DD)
def converter_data(data_str):
    if not data_str: return None
    try:
        # Transforma "24-12-2025" em objeto data e depois em "2025-12-24"
        return datetime.strptime(data_str, "%d-%m-%Y").strftime("%Y-%m-%d")
    except:
        # Se der erro (ex: data já formatada ou texto estranho), retorna como veio
        return data_str

def processar_imovel(session, scraper, codigo_reduzido):
    try:
        # 1. Busca ou Cria Imóvel no Banco
        imovel = session.query(Imovel).filter_by(codigo_reduzido=str(codigo_reduzido)).first()
        if not imovel:
            imovel = Imovel(codigo_reduzido=str(codigo_reduzido))
            session.add(imovel)
            session.commit()
            logger.debug(f"[{codigo_reduzido}] Imóvel criado no banco.")

        # ==============================================================================
        # LÓGICA DE RETENTATIVA (RETRY) - 3 TENTATIVAS
        # ==============================================================================
        dados_com_bytes = None
        tentativa_atual = 1
        max_tentativas = 3

        while tentativa_atual <= max_tentativas:
            # Tenta extrair dados
            dados_com_bytes = scraper.extrair_dados(codigo_reduzido)

            if dados_com_bytes:
                # SUCESSO: Dados obtidos, sai do loop imediatamente
                break
            else:
                # FALHA: Loga e prepara para tentar de novo
                logger.warning(f"[{codigo_reduzido}] Falha na tentativa {tentativa_atual}/{max_tentativas}.")
                
                if tentativa_atual < max_tentativas:
                    tempo_espera = 5
                    logger.info(f"[{codigo_reduzido}] Aguardando {tempo_espera}s para tentar novamente...")
                    time.sleep(tempo_espera)
                
                tentativa_atual += 1
        
        # Se saiu do loop e a variável continua vazia, falhou todas as vezes
        if not dados_com_bytes:
            logger.error(f"[{codigo_reduzido}] ❌ FALHA TOTAL. Esgotadas {max_tentativas} tentativas.")
            imovel.status = "ERRO_SCRAPER"
            session.commit()
            return False
        # ==============================================================================

        # 2. Tratamento para Comparação (Remove bytes do PDF para não quebrar a lógica de igualdade)
        dados_limpos_novos = copy.deepcopy(dados_com_bytes)
        if "guia" in dados_limpos_novos:
            for guia in dados_limpos_novos["guia"]:
                for parcela in guia.get("parcelaIPTU", []):
                    if "blob_pdf" in parcela:
                        del parcela["blob_pdf"]

        # 3. Válvula de Escape (FORCE_UPDATE)
        forcar_atualizacao = os.getenv("FORCE_UPDATE", "false").lower() == "true"

        # Verifica Cache: Se não for para forçar E os dados forem iguais, pula.
        if not forcar_atualizacao and imovel.dados_brutos == dados_limpos_novos:
            imovel.data_atualizacao = datetime.now()
            imovel.status = "SEM_MUDANCA"
            session.commit()
            logger.info(f"[{codigo_reduzido}] Sem alterações identificadas (Cache).")
            return True

        if forcar_atualizacao:
            logger.warning(f"[{codigo_reduzido}] Ignorando cache (FORCE_UPDATE=true)...")

        # 4. Auditoria (Salva o JSON bruto novo)
        imovel.dados_brutos = dados_limpos_novos
        imovel.data_atualizacao = datetime.now()
        imovel.status = "PROCESSANDO"
        session.commit()

        # 5. Processamento dos Débitos (Salva na tabela filha)
        if "guia" in dados_com_bytes:
            lista_parcelas = dados_com_bytes["guia"][0].get("parcelaIPTU", [])
            
            # Limpa débitos antigos deste imóvel
            session.query(DebitoIPTU).filter_by(imovel_id=imovel.id).delete()
            
            debitos_para_adicionar = []

            for p in lista_parcelas:
                linha_dig = p.get("linhaDigitavel", "").upper()
                
                # Define a situação baseada no PDF ou Texto
                conteudo_binario = p.get('blob_pdf')
                situacao_parcela = "Aberto"
                
                if conteudo_binario:
                    situacao_parcela = "Aberto"
                elif "GUIA PAGA" in linha_dig:
                    situacao_parcela = "Quitado"
                elif "CANCELADO" in linha_dig or "NÃO RECEBER" in linha_dig:
                    situacao_parcela = "Cancelado"
                else:
                    situacao_parcela = "Indefinido"

                # Cria o objeto Débito
                novo_debito = DebitoIPTU(
                    ano=p.get('ano'),
                    parcela=p.get('numero'),
                    valor=p.get('totalParcela'),
                    
                    # Usa a função auxiliar para converter data BR -> SQL
                    vencimento=converter_data(p.get('vencimento')), 
                    vencimento_original=converter_data(p.get('vencOriginal')), 
                    
                    situacao=situacao_parcela,
                    boleto_pdf=conteudo_binario,
                    imovel=imovel
                )
                debitos_para_adicionar.append(novo_debito)

            if debitos_para_adicionar:
                session.add_all(debitos_para_adicionar)
                imovel.status = "SUCESSO"
                logger.success(f"[{codigo_reduzido}] Atualizado com sucesso: {len(debitos_para_adicionar)} débitos.")
            else:
                imovel.status = "SEM_DEBITOS"
                logger.info(f"[{codigo_reduzido}] Atualizado: Sem débitos pendentes.")
            
            session.commit()

        return True

    except Exception as e:
        session.rollback()
        logger.exception(f"[{codigo_reduzido}] Falha Crítica no processamento.")
        return False

def main():
    # Verifica conexão
    db_conn = os.getenv("DB_CONNECTION")
    if not db_conn:
        logger.critical("Variável DB_CONNECTION não definida. Encerrando.")
        sys.exit(1)

    try:
        db = DatabaseHandler(db_conn)
        db.init_db()
        session = db.get_session()
        session.execute(text("SELECT 1"))
        logger.info("Conexão com Banco de Dados estabelecida.")
    except Exception as e:
        logger.critical(f"Não foi possível conectar ao Banco de Dados: {e}")
        sys.exit(1)

    url = os.getenv("URL_ALVO")
    logger.info(f"Iniciando robô alvo: {url}")
    
    scraper = IPTUScraper(url)
    
    # Pega todos os imóveis para processar
    todos_imoveis = session.query(Imovel).all()
    logger.info(f"Fila de processamento: {len(todos_imoveis)} imóveis.")
    
    for imovel in todos_imoveis:
        processar_imovel(session, scraper, imovel.codigo_reduzido)
    
    session.close()
    logger.info("Processamento finalizado.")

if __name__ == "__main__":
    main()