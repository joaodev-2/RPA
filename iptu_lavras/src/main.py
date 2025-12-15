import time
import os
import requests
import speech_recognition as sr
from pydub import AudioSegment
from playwright.sync_api import sync_playwright

# Configurações
URL_ALVO = "https://sistemas.lavras.mg.gov.br/portalcidadao/#78c3e513dd43cb27d8a3e2f376196ffc656d7ea577b2c6fbb60d64c%C4%B2f519ae11de579d3556429a3a0d60d4126ce6124f4cb72c40f74b9be24c4ace0717f414682b9084f7f2f2badbde691ae9ac4beb640736cff1faebe42754e339242d8418003c6c5819aa28eace2710516b433e206b090b5806d05681f33a046be86a2499f7b46767e90bb7d0822aa8f94fd4decc318e3e180ff3b793678ea76aaa108c007815e5a98b32c687c24cee6b599eb926306b35da8e66fa5686c4ca84940821dd5cf90c719a9dc91262a649441dca545f27983a68ef6d89da24ca85ded900914c64" # Ajuste para a URL com hash se necessário
ARQUIVO_AUDIO_MP3 = "captcha_audio.mp3"
ARQUIVO_AUDIO_WAV = "captcha_audio.wav"

def resolver_recaptcha_audio(page):
    """
    Tenta resolver o reCAPTCHA v2 usando o desafio de áudio.
    """
    print("🤖 Iniciando resolução de reCAPTCHA via áudio...")

    # 1. Achar o iframe do reCAPTCHA e clicar no checkbox
    try:
        # O reCAPTCHA geralmente fica dentro de um iframe. Precisamos achá-lo.
        frame_checkbox = page.frame_locator("iframe[src*='recaptcha/api2/anchor']")
        frame_checkbox.locator(".recaptcha-checkbox-border").click()
        print("✅ Checkbox clicado.")
    except Exception as e:
        print("❌ Não achei o checkbox do reCAPTCHA. Verifique se ele está na tela.")
        return False

    time.sleep(2) # Espera a animação/verificação

    # 2. Verificar se já passou direto (às vezes o Google libera de primeira)
    status = frame_checkbox.locator("#recaptcha-anchor").get_attribute("aria-checked")
    if status == "true":
        print("🎉 Passamos direto sem desafio!")
        return True

    # 3. Se pediu desafio, achar o frame do desafio (bchallenge)
    frame_desafio = page.frame_locator("iframe[src*='recaptcha/api2/bframe']")
    
    # Clicar no botão de áudio
    try:
        frame_desafio.locator("#recaptcha-audio-button").click()
        print("🎧 Botão de áudio clicado.")
        time.sleep(2)
    except:
        print("⚠️ Não achei botão de áudio ou fui bloqueado temporariamente.")
        return False

    # 4. Pegar a URL do áudio (src)
    try:
        src_audio = frame_desafio.locator("#audio-source").get_attribute("src")
        print(f"🔗 Link do áudio encontrado: {src_audio[:30]}...")
    except:
        print("❌ Erro ao pegar link do áudio. O Google pode ter bloqueado esta automação.")
        return False

    # 5. Baixar o áudio
    # Usamos requests aqui mesmo para baixar o arquivo rápido
    resp = requests.get(src_audio)
    with open(ARQUIVO_AUDIO_MP3, "wb") as f:
        f.write(resp.content)

    # 6. Converter MP3 para WAV (Pydub precisa do FFmpeg aqui!)
    try:
        sound = AudioSegment.from_mp3(ARQUIVO_AUDIO_MP3)
        sound.export(ARQUIVO_AUDIO_WAV, format="wav")
    except Exception as e:
        print(f"❌ Erro na conversão de áudio. O FFmpeg está instalado? Erro: {e}")
        return False

    # 7. Transcrever o áudio (Google Speech Recognition)
    recognizer = sr.Recognizer()
    texto_audio = ""
    with sr.AudioFile(ARQUIVO_AUDIO_WAV) as source:
        audio_data = recognizer.record(source)
        try:
            # Usa a API free do Google
            texto_audio = recognizer.recognize_google(audio_data, language="en-US") # Captchas de áudio são números em inglês geralmente
            print(f"🗣️ Áudio transcrito: {texto_audio}")
        except sr.UnknownValueError:
            print("❌ Não consegui entender o áudio.")
            return False

    # 8. Preencher e Verificar
    frame_desafio.locator("#audio-response").fill(texto_audio)
    frame_desafio.locator("#recaptcha-verify-button").click()
    
    time.sleep(2)
    
    # Verifica se o checkbox principal ficou "checked"
    status_final = frame_checkbox.locator("#recaptcha-anchor").get_attribute("aria-checked")
    if status_final == "true":
        print("✅ Captcha resolvido com sucesso!")
        return True
    else:
        print("❌ Falha na verificação final.")
        return False

def main():
    with sync_playwright() as p:
        # Inicializa o navegador (headless=False para ver a mágica)
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        print("🌍 Acessando o site...")
        page.goto(URL_ALVO)
        
        # --- ETAPA 1: Playwright resolve a burocracia ---
        
        # Aqui você insere a lógica de chegar até onde o captcha aparece
        # Exemplo: Preencher código reduzido antes
        # page.fill("#inputCodigoReduzido", "12345") 
        
        sucesso = resolver_recaptcha_audio(page)
        
        if not sucesso:
            print("Abortando...")
            browser.close()
            return

        # Clica no botão de consultar final (após captcha resolvido)
        # page.click("#btnConsultar") 
        # page.wait_for_load_state("networkidle") # Espera carregar a próxima tela

        # --- ETAPA 2: Roubar os Cookies ---
        print("🍪 Capturando cookies para o Requests...")
        cookies_playwright = context.cookies()
        browser.close() # Pode fechar o navegador agora!

        # --- ETAPA 3: Requests assume daqui ---
        
        # Prepara a sessão
        session = requests.Session()
        
        # Converte cookies do formato Playwright para Requests
        for cookie in cookies_playwright:
            session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])

        # Adiciona Headers padrão para não ser bloqueado
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...'
        })

        print("🚀 Iniciando scraping via Requests...")
        
        # Exemplo: Agora você chama a API interna que descobrimos antes
        # url_api = "https://sistemas.lavras.mg.gov.br/api/dados-imovel"
        # resp = session.get(url_api)
        # print(resp.json())

        # Limpeza
        if os.path.exists(ARQUIVO_AUDIO_MP3): os.remove(ARQUIVO_AUDIO_MP3)
        if os.path.exists(ARQUIVO_AUDIO_WAV): os.remove(ARQUIVO_AUDIO_WAV)

if __name__ == "__main__":
    main()