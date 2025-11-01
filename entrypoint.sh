
set -e

echo "Applying database migrations using Alembic..."
alembic upgrade head
echo "Database migrations completed."

echo "Starting Supervisor to manage Uvicorn and Celery..."
exec /usr/bin/supervisord -n -c /etc/supervisor/conf.d/supervisord.conf
