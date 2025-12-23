# 1. Usar versão SLIM (Muito mais leve que a normal)
FROM python:3.10-slim

# Variáveis para o Python não gerar arquivos .pyc e logs imediatos
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# 2. Instalar dependências do sistema e LIMPAR o cache na mesma camada
# Isso evita que o "lixo" do apt-get fique salvo na imagem
RUN apt-get update && apt-get install -y \
    wget \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 3. Copiar e instalar requirements (usando cache do Docker inteligentemente)
COPY requirements.txt .

# --no-cache-dir: Não guarda o cache do instalador pip (economiza muito espaço)
RUN pip install --no-cache-dir -r requirements.txt

# 4. Playwright: Instalar APENAS o Chromium
# O 'install-deps' instala as libs do linux que o chrome precisa
RUN playwright install chromium
RUN playwright install-deps chromium

# 5. Copiar o código fonte (O resto é ignorado pelo .dockerignore)
COPY . .

# Comando final (lembre-se: em prod, tire o tail -f)
CMD ["python", "main.py"]