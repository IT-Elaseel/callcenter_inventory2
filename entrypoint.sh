#!/bin/sh

# ==============================
# Apply migrations
# ==============================
echo "🚀 Applying database migrations..."
python manage.py migrate --noinput

# ==============================
# Collect static files
# ==============================
echo "📦 Collecting static files..."
python manage.py collectstatic --noinput

# ==============================
# Start Daphne server
# ==============================
echo "🔥 Starting Daphne server..."
exec daphne -b 0.0.0.0 -p 8000 sweets_factory.asgi:application
