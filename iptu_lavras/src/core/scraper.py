# -*- coding: utf-8 -*-
import os
from playwright.sync_api import sync_playwright
from src.handlers.captcha import CaptchaHandler

class IPTUScraper:
    def __init__(self, url_alvo):
        self.url = url_alvo
        
    def extrair_dados(self, codigo_reduzido):
        """
        Acessa o site, resolve captcha e intercepta o JSON de resposta.
        """
        print(f"🚀 [Scraper] Iniciando extração para: {codigo_reduzido}")
        
        with sync_playwright() as p:
            modo_headless = os.getenv("HEADLESS", "false").lower() == "true"
            
            browser = p.chromium.launch(
                headless=modo_headless,
                args=["--no-sandbox", "--disable-setuid-sandbox"]
            )
            
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            
            try:
                # 1. Acessar URL
                print(f"🌍 [Scraper] Acessando URL (Headless: {modo_headless})...")
                page.goto(self.url, timeout=60000)
                page.wait_for_load_state("networkidle")

                # 2. Preencher Código
                print(f"✍️ [Scraper] Preenchendo 'Código Reduzido': {codigo_reduzido}")
                try:
                    page.locator("//div[contains(text(), 'Código Reduzido')]/following-sibling::input").first.fill(str(codigo_reduzido))
                except Exception as e:
                    print(f"⚠️ [Scraper] Seletor principal falhou: {e}. Tentando genérico...")
                    page.locator("input.form-control").first.fill(str(codigo_reduzido))
                
                # 3. Resolver Captcha
                captcha = CaptchaHandler(page)
                if not captcha.resolver_via_audio():
                    raise Exception("Não foi possível resolver o Captcha após tentativas.")
                
                # 4. Interceptar a Requisição JSON
                print("🕵️ [Scraper] Aguardando JSON da API...")
                
                # --- CORREÇÃO AQUI ---
                def filtro_response(response):
                    # O objeto é uma RESPOSTA. Para ver o método (PUT), temos que olhar a requisição dela.
                    return "getExtratoIPTU" in response.url and response.request.method == "PUT"

                with page.expect_response(filtro_response, timeout=30000) as captura:
                    # Clica no botão Consultar
                    btn = page.locator(".gwt-SubmitButton").first
                    if not btn.is_visible():
                        btn = page.locator("button").last 
                    btn.click(force=True)
                
                # 5. Processar Resposta
                response = captura.value
                
                if response.status == 200:
                    print("✅ [Scraper] JSON capturado com sucesso!")
                    return response.json()
                elif response.status == 204:
                    print("ℹ️ [Scraper] Imóvel não possui débitos (No Content).")
                    return {"debitos": []}
                else:
                    raise Exception(f"Erro HTTP {response.status} ao consultar API.")
                    
            except Exception as e:
                print(f"💥 [Scraper] Erro durante o processo: {e}")
                
                if modo_headless:
                    try:
                        os.makedirs("data/erros", exist_ok=True)
                        page.screenshot(path=f"data/erros/erro_{codigo_reduzido}.png")
                        print(f"📸 Screenshot salva em data/erros/erro_{codigo_reduzido}.png")
                    except:
                        pass
                return None
                
            finally:
                context.close()
                browser.close()