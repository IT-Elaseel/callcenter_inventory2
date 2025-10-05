# ==============================
# Base image
# ==============================
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (for psycopg2 & channels)
RUN apt-get update && apt-get install -y build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files
COPY . .

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=sweets_factory.settings

# Expose Daphne port
EXPOSE 8000

# Run entrypoint script (includes migrations and Daphne)
ENTRYPOINT ["bash", "entrypoint.sh"]