#!/bin/sh
set -e

echo "🚀 Running migrations and collecting static files..."
python manage.py migrate --noinput
python manage.py collectstatic --noinput

echo "✅ Starting Daphne ASGI server..."
exec daphne -b 0.0.0.0 -p 8001 sweets_factory.asgi:application

