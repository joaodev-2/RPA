# Usa a imagem oficial do Playwright (já tem Python e navegadores)
FROM mcr.microsoft.com/playwright/python:v1.57.0

# Define a pasta de trabalho dentro do container
WORKDIR /app

# Copia o arquivo de requisitos e instala as bibliotecas
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instala o navegador Chromium (garantia extra)
RUN playwright install chromium

# Copia todo o resto do seu código para dentro do container
COPY . .

# Comando padrão ao rodar o container
CMD ["python", "main.py"]