import os
import time
import requests
import speech_recognition as sr
from pydub import AudioSegment

class CaptchaHandler:
    def __init__(self, page):
        self.page = page
        self.audio_mp3 = "temp_captcha.mp3"
        self.audio_wav = "temp_captcha.wav"

    def _cleanup(self):
        """Remove arquivos temporários de áudio."""
        if os.path.exists(self.audio_mp3): os.remove(self.audio_mp3)
        if os.path.exists(self.audio_wav): os.remove(self.audio_wav)

    def resolver_via_audio(self):
        try:
            frame = self.page.frame_locator("iframe[src*='recaptcha/api2/anchor']")
            anchor = frame.locator("#recaptcha-anchor")
            
            # 1. Verifica se já está resolvido
            if anchor.get_attribute("aria-checked") == "true":
                return True
            
            # 2. Clica no Checkbox
            checkbox = frame.locator(".recaptcha-checkbox-border")
            if checkbox.is_visible():
                checkbox.click()
                self.page.wait_for_timeout(2000)
            
            # 3. Verifica aprovação automática
            if anchor.get_attribute("aria-checked") == "true":
                return True

            # 4. Inicia processo de áudio
            bframe = self.page.frame_locator("iframe[src*='recaptcha/api2/bframe']")
            btn_audio = bframe.locator("#recaptcha-audio-button")
            
            if btn_audio.is_visible():
                btn_audio.click()
                time.sleep(1.5) # Aguarda transição da interface
                
                # Obtém URL do áudio
                src = bframe.locator("#audio-source").get_attribute("src")
                if not src: 
                    return False
                
                # Download do arquivo MP3
                with open(self.audio_mp3, "wb") as f:
                    f.write(requests.get(src).content)
                
                # Conversão MP3 -> WAV (Necessário para a lib SpeechRecognition)
                AudioSegment.from_mp3(self.audio_mp3).export(self.audio_wav, format="wav")
                
                # Transcrição usando Google Speech API
                rec = sr.Recognizer()
                with sr.AudioFile(self.audio_wav) as source:
                    audio_data = rec.record(source)
                    texto = rec.recognize_google(audio_data, language="en-US")
                
                # Preenche e submete
                bframe.locator("#audio-response").fill(texto)
                bframe.locator("#recaptcha-verify-button").click()
                
                time.sleep(2) # Aguarda validação do Google
                
                self._cleanup()
                return anchor.get_attribute("aria-checked") == "true"
            
            return False
            
        except Exception:
            self._cleanup()
            return False