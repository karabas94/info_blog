FROM python:3.13-slim

# Системные зависимости(обновляем список доступных пакетов, устанавливаем пакеты,
# уст бибилиотеку постгрес для разработки, с-компилятор и удаляем кеш списка пакетов
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем requirements и устанавливаем зависимости
COPY requirements/ requirements/
RUN pip install --no-cache-dir -r requirements/local.txt

# Копируем код проекта
COPY . .

# Создаём директории для медиа и статики
RUN mkdir -p media static_collected static

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]