FROM python:3.11-slim

WORKDIR /app

# Установить зависимости системы
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Скопировать requirements
COPY requirements.txt .

# Установить Python зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Скопировать всё остальное
COPY . .

# Создать директорию для данных
RUN mkdir -p /data

# Запустить бота
CMD ["python", "autopost_bot_v2.py"]
