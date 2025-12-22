# Usa a imagem oficial do Playwright (já tem Python e dependências de OS)
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

# Instala FFmpeg (Crucial para o pydub/AudioSegment funcionar)
RUN apt-get update && apt-get install -y ffmpeg

# Define diretório de trabalho
WORKDIR /app

# Copia e instala dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instala o navegador Chromium do Playwright
RUN playwright install chromium

# Copia todo o código do projeto para dentro do container
COPY . .

# Comando para rodar a aplicação
CMD ["python", "main.py"]