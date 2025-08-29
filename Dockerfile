# Python tabanlı lightweight image
FROM python:3.12-slim

# Çalışma dizini
WORKDIR /app

# Gereken sistem bağımlılıkları (ffmpeg vs. gerekmez, speech sdk kendi içinde çalışır)
RUN apt-get update && apt-get install -y build-essential curl && rm -rf /var/lib/apt/lists/*

# Gereken Python kütüphanelerini yükle
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kodları kopyala
COPY . .

# Azure Speech Service credentials - otomatik olarak ayarlanır
ENV SPEECH_KEY="CIMrj9BoBSnRjhhRAFexeiU0eYIyltoOBqKyMOBnRMaQYWV2twokJQQJ99BHACYeBjFXJ3w3AAAYACOGE7gO"
ENV SPEECH_REGION="eastus"

# Port'u expose et
EXPOSE 8000

# FastAPI app'i uvicorn ile çalıştır
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
