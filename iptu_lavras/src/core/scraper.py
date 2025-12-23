# -*- coding: utf-8 -*-
import os
import time
import re
from pathlib import Path
from playwright.sync_api import sync_playwright
from src.handlers.captcha import CaptchaHandler

class IPTUScraper:
    def __init__(self, url_alvo):
        self.url = url_alvo
        self.download_path = Path("data/boletos")
        self.download_path.mkdir(parents=True, exist_ok=True)
        
    def extrair_dados(self, codigo_reduzido):
        print(f"🚀 [Scraper] Iniciando extração para: {codigo_reduzido}")
        
        with sync_playwright() as p:
            # Configuração do Browser
            modo_headless = os.getenv("HEADLESS", "false").lower() == "true"
            browser = p.chromium.launch(
                headless=modo_headless,
                args=["--no-sandbox", "--disable-setuid-sandbox"]
            )
            
            context = browser.new_context(accept_downloads=True)
            page = context.new_page()
            
            try:
                # 1. Acessar e Preencher
                print(f"🌍 [Scraper] Acessando URL...")
                page.goto(self.url, timeout=60000)
                
                # Tratamento para input que varia
                try:
                    page.locator("//div[contains(text(), 'Código Reduzido')]/following-sibling::input").first.fill(str(codigo_reduzido))
                except:
                    page.locator("input.form-control").first.fill(str(codigo_reduzido))
                
                # 2. Captcha
                captcha = CaptchaHandler(page)
                if not captcha.resolver_via_audio():
                    raise Exception("Falha no Captcha")
                
                # 3. Interceptação do JSON
                print("🕵️ [Scraper] Consultando dados...")
                
                # Prepara a interceptação
                with page.expect_response(lambda r: "getExtratoIPTU" in r.url and r.request.method == "PUT", timeout=30000) as captura:
                    btn = page.locator(".gwt-SubmitButton").first
                    if not btn.is_visible():
                        btn = page.locator("button").last 
                    btn.click(force=True)
                
                response = captura.value
                dados_json = {}
                
                # Processa o Retorno
                if response.status == 200:
                    dados_json = response.json()
                    print("✅ [Scraper] JSON capturado com sucesso!")
                    
                    # --- AQUI ESTÁ A MUDANÇA: DOWNLOAD GUIADO PELO JSON ---
                    # Passamos o JSON para a função de download
                    if "guia" in dados_json:
                        self._baixar_por_json(page, dados_json, codigo_reduzido)
                    else:
                        print("⚠️ JSON veio sem a chave 'guia'. Estrutura desconhecida.")

                elif response.status == 204:
                    print("ℹ️ [Scraper] Sem débitos (204).")
                    dados_json = {"debitos": []}
                
                return dados_json
                    
            except Exception as e:
                print(f"💥 [Scraper] Erro: {e}")
                return None
            finally:
                context.close()
                browser.close()

    def _baixar_por_json(self, page, dados_json, codigo_imovel):
        """
        Versão Robustez Total: Varre as linhas da tela e cruza com o JSON
        para garantir que estamos baixando a parcela certa.
        """
        print("   📉 Cruzando dados do JSON com a Tela...")
        
        try:
            # 1. Pega lista de débitos reais do JSON
            lista_original = dados_json.get("guia", [{}])[0].get("parcelaIPTU", [])
            debitos_abertos = []
            
            # Filtra apenas o que é dívida no JSON
            for p in lista_original:
                linha_dig = p.get("linhaDigitavel", "").upper()
                if "GUIA PAGA" not in linha_dig and "NÃO RECEBER" not in linha_dig:
                    debitos_abertos.append(p)
            
            print(f"      📋 O JSON indica {len(debitos_abertos)} parcelas em aberto.")

            if not debitos_abertos:
                return

            # 2. Na Tela: Pega todas as linhas (tr) que têm o botão de PDF
            # Isso ignora cabeçalhos e linhas sem ação
            linhas_com_botao = page.locator("tr:has(a:has-text('Emitir 2ª Via PDF'))").all()
            print(f"      👀 A Tela mostra {len(linhas_com_botao)} linhas com botão de download.")

            # 3. O Grande Encontro (Match)
            for debito in debitos_abertos:
                num_parc = str(debito.get("numero"))
                vencimento_json = debito.get("vencimento") # ex: 22-12-2025
                valor_json = str(debito.get("totalParcela")).replace(".", ",") # 198.3 -> 198,3
                
                # Ajuste de data: JSON usa hifen (22-12), tela costuma usar barra (22/12)
                vencimento_tela_padrao = vencimento_json.replace("-", "/")

                encontrou = False
                
                # Testa cada linha da tela para ver se é a dona desse débito
                for linha in linhas_com_botao:
                    texto_linha = linha.inner_text()
                    
                    # CRITÉRIO DE SEGURANÇA:
                    # Só clica se a linha contiver o VENCIMENTO ou o VALOR aproximado
                    # (Usar só o número da parcela é perigoso, pois "7" existe em datas e valores)
                    
                    match_vencimento = vencimento_tela_padrao in texto_linha or vencimento_json in texto_linha
                    match_valor = valor_json in texto_linha
                    
                    if match_vencimento or match_valor:
                        print(f"      🎯 Match confirmado! Parcela {num_parc} (Venc: {vencimento_json})")
                        
                        botao = linha.locator("a:has-text('Emitir 2ª Via PDF')").first
                        
                        # --- CLIQUE E DOWNLOAD ---
                        try:
                            # Rola até o botão
                            botao.scroll_into_view_if_needed()
                            
                            with page.expect_download(timeout=60000) as download_info:
                                botao.click(force=True)
                            
                            download = download_info.value
                            nome_arquivo = f"boleto_{codigo_imovel}_parc{num_parc}_{vencimento_json}.pdf"
                            caminho_final = self.download_path / nome_arquivo
                            
                            download.save_as(caminho_final)
                            print(f"         ✅ Arquivo Salvo: {nome_arquivo}")
                            encontrou = True
                            
                            # Remove a linha da lista para não clicar nela de novo (otimização)
                            # (Opcional, mas ajuda a evitar duplicidade se o match for fraco)
                            
                            time.sleep(3) # Respeita o loading do site
                            break # Sai do loop de linhas e vai para o próximo débito do JSON
                            
                        except Exception as e:
                            print(f"         ❌ Erro no download da parcela {num_parc}: {e}")
                
                if not encontrou:
                    print(f"      ⚠️ ALERTA: O JSON pede a parcela {num_parc} (Venc: {vencimento_json}), mas não achei ela na tabela visualmente.")

        except Exception as e:
            print(f"   ☠️ Erro crítico na lógica de cruzamento JSON/Tela: {e}")