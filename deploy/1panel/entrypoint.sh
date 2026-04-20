#!/bin/sh
set -e

cd /app

echo "[ors] Waiting for database..."
i=0
until python manage.py shell -c "from django.db import connection; connection.ensure_connection()" >/dev/null 2>&1; do
  i=$((i + 1))
  if [ "$i" -ge 60 ]; then
    echo "[ors] ERROR: database not reachable after ~120s"
    exit 1
  fi
  sleep 2
done

echo "[ors] migrate"
python manage.py migrate --noinput

echo "[ors] collectstatic"
python manage.py collectstatic --noinput

if [ -z "${ROOT_PASSWORD:-}" ]; then
  ROOT_PASSWORD="$(python -c "import secrets; print(secrets.token_urlsafe(18))")"
  export ROOT_PASSWORD
  echo "[ors] ROOT_PASSWORD was empty; generated for first bootstrap (see logs once, then set ROOT_PASSWORD in .env)"
fi
if [ -z "${ADMIN_PASSWORD:-}" ]; then
  ADMIN_PASSWORD="$(python -c "import secrets; print(secrets.token_urlsafe(18))")"
  export ADMIN_PASSWORD
  echo "[ors] ADMIN_PASSWORD was empty; generated for first bootstrap (see logs once, then set ADMIN_PASSWORD in .env)"
fi

ROOT_USERNAME="${ROOT_USERNAME:-root}"
DEPT_NAME="${DEPT_NAME:-手术室}"
DEPT_CODE="${DEPT_CODE:-ors}"
ADMIN_USERNAME="${ADMIN_USERNAME:-admin}"
ADMIN_NAME="${ADMIN_NAME:-科室管理员}"

echo "[ors] bootstrap_ors (idempotent)"
python manage.py bootstrap_ors \
  --root-username "$ROOT_USERNAME" --root-password "$ROOT_PASSWORD" \
  --dept-name "$DEPT_NAME" --dept-code "$DEPT_CODE" \
  --admin-username "$ADMIN_USERNAME" --admin-password "$ADMIN_PASSWORD" \
  --admin-name "$ADMIN_NAME"

echo "[ors] Starting gunicorn on 0.0.0.0:8000 workers=${GUNICORN_WORKERS:-3}"
exec gunicorn ors_site.wsgi:application \
  --bind "0.0.0.0:8000" \
  --workers "${GUNICORN_WORKERS:-3}" \
  --threads 1 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -
