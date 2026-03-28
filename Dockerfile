FROM python:3.13-slim

# Empêche Python de générer des fichiers .pyc et assure un affichage direct des logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=config.settings.production

WORKDIR /app

# Dépendances système (Postgres, Pillow, WeasyPrint, etc.)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Dépendances Python
COPY requirements/ requirements/
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements/production.txt

# Code source
COPY . /app/

EXPOSE 8000
