#!/bin/sh
set -e

echo "=========================================="
echo "Starting container entrypoint..."
echo "=========================================="

# Move to app directory
cd /app/ticketing_app

# ------------------------------
# Run Alembic migrations
# ------------------------------
# echo "Applying database migrations using Alembic..."
# alembic revision --autogenerate -m "Added new models"
# alembic upgrade head
# echo "Database migrations completed."

# ------------------------------
# Start Supervisor to manage Uvicorn + Celery
# ------------------------------
echo "Starting Supervisor to manage Uvicorn and Celery..."
exec /usr/bin/supervisord -n -c /etc/supervisor/conf.d/supervisord.conf
