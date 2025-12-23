# -*- coding: utf-8 -*-
import os
import time
from playwright.sync_api import sync_playwright
from src.handlers.captcha import CaptchaHandler

class IPTUScraper:
    def __init__(self, url_alvo):
        self.url = url_alvo
        # Não criamos mais pastas físicas, pois o processamento é em memória.
        
    def extrair_dados(self, codigo_reduzido):
        with sync_playwright() as p:
            # Configuração do Browser (Headless controlado por env)
            modo_headless = os.getenv("HEADLESS", "false").lower() == "true"
            browser = p.chromium.launch(
                headless=modo_headless,
                args=["--no-sandbox", "--disable-setuid-sandbox"]
            )
            
            context = browser.new_context(accept_downloads=True)
            page = context.new_page()
            
            try:
                # 1. Acesso e Preenchimento
                page.goto(self.url, timeout=60000)
                
                # Tentativa de localizar o input por texto ou classe genérica
                try:
                    page.locator("//div[contains(text(), 'Código Reduzido')]/following-sibling::input").first.fill(str(codigo_reduzido))
                except:
                    page.locator("input.form-control").first.fill(str(codigo_reduzido))
                
                # 2. Resolução do Captcha
                captcha = CaptchaHandler(page)
                if not captcha.resolver_via_audio():
                    return None # Falha no captcha aborta o processo
                
                # 3. Interceptação da Requisição JSON (Dados da Dívida)
                # Aguarda o POST/PUT que retorna os dados após clicar em consultar
                with page.expect_response(lambda r: "getExtratoIPTU" in r.url and r.request.method == "PUT", timeout=30000) as captura:
                    btn = page.locator(".gwt-SubmitButton").first
                    if not btn.is_visible():
                        btn = page.locator("button").last 
                    btn.click(force=True)
                
                response = captura.value
                dados_json = {}
                
                if response.status == 200:
                    dados_json = response.json()
                    
                    # Se houver débitos (chave 'guia'), iniciamos o download em memória
                    if "guia" in dados_json:
                        self._baixar_pdf_para_memoria(page, dados_json)

                elif response.status == 204:
                    # Status 204 geralmente indica "Nenhum débito encontrado"
                    dados_json = {"guia": []}
                
                return dados_json
                    
            except Exception:
                return None
            finally:
                context.close()
                browser.close()

    def _baixar_pdf_para_memoria(self, page, dados_json):
        """
        Cruza os dados do JSON com a tabela HTML, clica no botão de download,
        lê o arquivo temporário para a memória RAM e injeta no dicionário JSON.
        """
        try:
            # Filtra apenas parcelas em aberto para evitar processamento inútil
            lista_parcelas = dados_json.get("guia", [{}])[0].get("parcelaIPTU", [])
            debitos_abertos = [
                p for p in lista_parcelas 
                if "GUIA PAGA" not in p.get("linhaDigitavel", "").upper() 
                and "NÃO RECEBER" not in p.get("linhaDigitavel", "").upper()
            ]
            
            if not debitos_abertos:
                return

            # Localiza todas as linhas da tabela que possuem botão de download
            linhas_com_botao = page.locator("tr:has(a:has-text('Emitir 2ª Via PDF'))").all()

            for debito in debitos_abertos:
                # Prepara dados para o "Match" (Encontro) entre JSON e HTML
                vencimento_json = debito.get("vencimento")
                valor_json = str(debito.get("totalParcela")).replace(".", ",")
                vencimento_tela = vencimento_json.replace("-", "/") # Ajuste de formato de data

                # Itera sobre as linhas visuais para encontrar a correspondente
                for linha in linhas_com_botao:
                    texto_linha = linha.inner_text()
                    
                    # Verifica se a linha contém a data ou o valor do débito atual
                    match_vencimento = (vencimento_tela in texto_linha or vencimento_json in texto_linha)
                    match_valor = (valor_json in texto_linha)

                    if match_vencimento or match_valor:
                        botao = linha.locator("a:has-text('Emitir 2ª Via PDF')").first
                        botao.scroll_into_view_if_needed()
                        
                        try:
                            # Gerencia o evento de download
                            with page.expect_download(timeout=60000) as download_info:
                                botao.click(force=True)
                            
                            download = download_info.value
                            path_temp = download.path()
                            
                            # Lê os bytes do arquivo temporário para a memória
                            with open(path_temp, "rb") as f:
                                bytes_pdf = f.read()
                            
                            # Injeta os bytes direto no objeto JSON original
                            debito['blob_pdf'] = bytes_pdf
                            
                            # Pequena pausa para evitar sobrecarga ou bloqueio do servidor
                            time.sleep(2)
                            break 
                            
                        except Exception:
                            # Se falhar um download, continua para o próximo débito
                            continue

        except Exception:
            pass