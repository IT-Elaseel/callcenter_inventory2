# ==============================
# Base image
# ==============================
FROM python:3.11-slim

# ==============================
# Set working directory
# ==============================
WORKDIR /app

# ==============================
# Install dependencies
# ==============================
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ==============================
# Copy project files
# ==============================
COPY . .

# ==============================
# Set environment variables
# ==============================
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=sweets_factory.settings

# ==============================
# Expose port
# ==============================
EXPOSE 8000

# ==============================
# Run Daphne server (Channels)
# ==============================
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "sweets_factory.asgi:application"]
