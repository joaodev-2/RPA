# Dockerfile
FROM python:3.10-slim

# Instala dependências do sistema (para Playwright/Postgres)
RUN apt-get update && apt-get install -y \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 1. Copia e instala as libs (Cache layer)
COPY requirements.txt .
RUN apt-get update && apt-get install -y \
    libpq-dev gcc ffmpeg \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install --with-deps chromium

# 2. O GRANDE SEGREDO: Copia TODO o seu projeto para dentro da imagem
COPY . .

# Comando padrão
CMD ["python", "main.py"]