FROM python:3.11-slim

# Definir fuso horário para Brasília
ENV TZ="America/Sao_Paulo"
RUN apt-get update && apt-get install -y tzdata && \
    ln -fs /usr/share/zoneinfo/$TZ /etc/localtime && \
    dpkg-reconfigure -f noninteractive tzdata

# Instalar dependências de sistema necessárias para o Playwright
RUN apt-get update && apt-get install -y curl xvfb

WORKDIR /app

# Copiar requirements primeiro para aproveitar o cache do Docker
COPY requirements.txt .

# Instalar bibliotecas Python
RUN pip install --no-cache-dir -r requirements.txt

# Instalar navegadores do Playwright (Chromium) e suas dependências de sistema
RUN playwright install --with-deps chromium

# Copiar todo o código do projeto
COPY . .

# Expor a porta que o Flask utiliza
EXPOSE 5000

# Executar o servidor
CMD ["python", "servidor.py"]
