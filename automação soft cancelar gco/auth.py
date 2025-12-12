from playwright.sync_api import Page
import config
import time
import os

class Autenticador:
    def __init__(self, page: Page):
        self.page = page

    def realizar_login(self):
        print("--> [LOGIN] Acessando página inicial...")
        
        try:
            self.page.goto(config.URL_LOGIN)
            print("--> [ESPERA] Aguardando carregamento da rede...")
            self.page.wait_for_load_state("networkidle", timeout=60000)
        except:
            print("--> [AVISO] Rede demorou, mas vamos tentar seguir.")

        # 2. Preenchimento de Login
        try:
            self.page.wait_for_selector(config.SEL_CAMPO_USUARIO, state="visible", timeout=10000)
            
            if self.page.is_visible(config.SEL_CAMPO_USUARIO):
                print("--> [LOGIN] Campos encontrados!")
                print("--> [PAUSA] Esperando 3 SEGUNDOS para o site estabilizar...")
                time.sleep(3) 
                
                print("--> [AÇÃO] Preenchendo Usuário...")
                self.page.click(config.SEL_CAMPO_USUARIO)
                self.page.fill(config.SEL_CAMPO_USUARIO, config.USUARIO)
                
                print("--> [AÇÃO] Preenchendo Senha...")
                self.page.click(config.SEL_CAMPO_SENHA)
                self.page.fill(config.SEL_CAMPO_SENHA, config.SENHA)
                
                print("--> [AÇÃO] Clicando em Entrar...")
                self.page.click(config.SEL_BOTAO_ENTRAR)
            else:
                print("--> [LOGIN] Campos não apareceram (provável sessão ativa).")
                
        except Exception as e:
            print(f"--> [INFO] Status login: {e}")
            pass

        # --- TRATAMENTO IMEDIATO DO MODAL ---
        print("--> [VERIFICAÇÃO] Procurando modal 'alertConfirm' imediatamente...")
        try:
            for _ in range(10): 
                if self.page.is_visible(config.SEL_BOTAO_ALERT_CONFIRM):
                    print("--> [AÇÃO] Modal 'alertConfirm' encontrado. Clicando!")
                    self.page.click(config.SEL_BOTAO_ALERT_CONFIRM)
                    time.sleep(3)
                    break 
                time.sleep(0.5)
        except:
            pass

        print("\n" + "="*60)
        print("ESTADO: MONITORANDO ACESSO FINAL")
        print("SE O SITE PEDIR MFA, OLHE O TERMINAL PARA DIGITAR.")
        print("="*60 + "\n")

        # 3. LOOP DE VIGILÂNCIA INTELIGENTE (MFA + Screenshot)
        tempo_limite = time.time() + 300 # 5 minutos
        screenshot_tirado = False
        
        while time.time() < tempo_limite:
            
            # A) SUCESSO?
            if self.page.is_visible(config.SEL_BARRA_PESQUISA):
                print("--> [SUCESSO] Sistema carregado!")
                self.page.wait_for_load_state("networkidle")
                return True 

            # B) Modal Desconectar
            try:
                if hasattr(config, 'SEL_BOTAO_DESCONECTAR') and self.page.is_visible(config.SEL_BOTAO_DESCONECTAR):
                    print("--> [AÇÃO] Clicando em 'Desconectar'...")
                    self.page.click(config.SEL_BOTAO_DESCONECTAR)
                    time.sleep(3)
                    continue
            except: pass

            # C) Modal Confirmar (novamente, por segurança)
            if self.page.is_visible(config.SEL_BOTAO_ALERT_CONFIRM):
                self.page.click(config.SEL_BOTAO_ALERT_CONFIRM)
                time.sleep(2)
                continue

            # D) DETECÇÃO DE MFA (NOVA LÓGICA PARA DOCKER)
            # Se passou 10 segundos e ainda não entrou, tira print e procura input de texto
            if time.time() > (tempo_limite - 290) and not screenshot_tirado:
                print("--> [DEBUG] Sistema ainda não carregou. Tirando foto da tela...")
                self.page.screenshot(path="debug_tela_login.png")
                print("--> [DEBUG] Foto salva como 'debug_tela_login.png'. Verifique a pasta.")
                screenshot_tirado = True

                # Tenta achar um campo de input visível que NÃO seja usuário/senha
                # Geralmente o campo de token é o único input text visível nessa fase
                inputs_visiveis = self.page.locator("input[type='text']:visible, input[type='tel']:visible, input[type='number']:visible")
                
                if inputs_visiveis.count() > 0:
                    print("\n" + "!"*50)
                    print("ATENÇÃO: Um campo de texto foi detectado na tela.")
                    print("Provavelmente é o MFA (Código do E-mail/App).")
                    print("!"*50)
                    
                    # --- INTERAÇÃO COM O USUÁRIO NO TERMINAL ---
                    codigo = input(">>> DIGITE O CÓDIGO MFA AQUI E DÊ ENTER: ")
                    
                    if codigo:
                        print(f"--> [AÇÃO] Enviando código '{codigo}' para o navegador...")
                        # Preenche no primeiro campo encontrado
                        inputs_visiveis.first.fill(codigo)
                        self.page.keyboard.press("Enter")
                        
                        # Tenta clicar em botões comuns de confirmação se o Enter não for suficiente
                        try:
                            self.page.locator("button:has-text('Verificar'), button:has-text('Confirmar'), button:has-text('Enviar')").first.click(timeout=2000)
                        except:
                            pass
                        
                        time.sleep(3)
                        continue

            time.sleep(1)

        raise Exception("Tempo esgotado! Login não finalizado. Veja 'debug_tela_login.png'.")