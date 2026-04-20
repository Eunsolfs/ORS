#!/usr/bin/env bash
set -euo pipefail

# ORS (Django) 1Panel non-container install helper
# - Source code deployment in website directory
# - Create/prepare venv
# - Ensure .env exists (copy from .env.example if missing)
# - Generate DJANGO_SECRET_KEY if still default
# - django migrate + bootstrap_ors + collectstatic
# - Print recommended gunicorn start command

ORS_DIR="${ORS_DIR:-$(pwd)}"
VENV_DIR="${VENV_DIR:-.venv}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

BIND_HOST="${BIND_HOST:-127.0.0.1}"
BIND_PORT="${BIND_PORT:-8989}"
GUNICORN_WORKERS="${GUNICORN_WORKERS:-3}"

ROOT_USERNAME="${ROOT_USERNAME:-root}"
DEPT_NAME="${DEPT_NAME:-手术室}"
DEPT_CODE="${DEPT_CODE:-ors}"
ADMIN_USERNAME="${ADMIN_USERNAME:-admin}"
ADMIN_NAME="${ADMIN_NAME:-科室管理员}"

random_password() {
  "$PYTHON_BIN" - <<'PY'
import secrets
print(secrets.token_urlsafe(18))
PY
}

set_kv_in_env() {
  key="$1"
  val="$2"
  tmp="$(mktemp)"
  awk -v k="$key" -v v="$val" '
    BEGIN{found=0}
    $0 ~ ("^" k "=") {print k "=" v; found=1; next}
    {print}
    END{if(found==0) print k "=" v}
  ' .env > "$tmp"
  mv "$tmp" .env
}

maybe_set_from_runtime_env() {
  key="$1"
  env_key="$2"
  value="${!env_key:-}"
  if [ -n "$value" ]; then
    set_kv_in_env "$key" "$value"
    masked="$value"
    case "$key" in
      *PASSWORD*|*SECRET*|*KEY*)
        masked="******"
        ;;
    esac
    echo "[INFO] .env set: ${key}=${masked}"
  fi
}

main() {
  if [ ! -d "$ORS_DIR" ]; then
    echo "[ERROR] ORS_DIR not found: $ORS_DIR"
    exit 1
  fi

  cd "$ORS_DIR"

  if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "[INFO] Copied .env.example -> .env"
  fi

  # Runtime overrides (optional)
  maybe_set_from_runtime_env "DB_ENGINE" "DB_ENGINE"
  maybe_set_from_runtime_env "DB_NAME" "DB_NAME"
  maybe_set_from_runtime_env "DB_USER" "DB_USER"
  maybe_set_from_runtime_env "DB_PASSWORD" "DB_PASSWORD"
  maybe_set_from_runtime_env "DB_HOST" "DB_HOST"
  maybe_set_from_runtime_env "DB_PORT" "DB_PORT"
  maybe_set_from_runtime_env "DJANGO_DEBUG" "DJANGO_DEBUG"
  maybe_set_from_runtime_env "DJANGO_ALLOWED_HOSTS" "DJANGO_ALLOWED_HOSTS"
  maybe_set_from_runtime_env "DJANGO_CSRF_TRUSTED_ORIGINS" "DJANGO_CSRF_TRUSTED_ORIGINS"
  maybe_set_from_runtime_env "ORS_SOFFICE_PATH" "ORS_SOFFICE_PATH"

  if grep -qE '^DJANGO_SECRET_KEY=' .env; then
    current_secret="$(grep -E '^DJANGO_SECRET_KEY=' .env | tail -n 1 | cut -d'=' -f2-)"
    if [ "$current_secret" = "change-me" ] || [ "$current_secret" = "dev-insecure-change-me" ] || [ -z "$current_secret" ]; then
      new_secret="$(random_password)"
      if command -v perl >/dev/null 2>&1; then
        perl -pi -e "s/^DJANGO_SECRET_KEY=.*/DJANGO_SECRET_KEY=$new_secret/" .env
      else
        tmp="$(mktemp)"
        awk -v sec="$new_secret" 'BEGIN{FS=OFS="="} /^DJANGO_SECRET_KEY=/{$1="DJANGO_SECRET_KEY";$2=sec} {print}' .env > "$tmp"
        mv "$tmp" .env
      fi
      echo "[INFO] Regenerated DJANGO_SECRET_KEY"
    fi
  fi

  if [ ! -d "$VENV_DIR" ]; then
    echo "[INFO] Creating virtualenv: $VENV_DIR"
    "$PYTHON_BIN" -m venv "$VENV_DIR"
  fi

  PIP="$VENV_DIR/bin/pip"
  PY="$VENV_DIR/bin/python"

  echo "[INFO] Installing dependencies..."
  "$PIP" install -U pip
  "$PIP" install -r requirements.txt
  "$PIP" install -U gunicorn

  echo "[INFO] Running migrations..."
  "$PY" manage.py migrate --noinput

  ROOT_PASSWORD="${ROOT_PASSWORD:-}"
  ADMIN_PASSWORD="${ADMIN_PASSWORD:-}"
  if [ -z "$ROOT_PASSWORD" ]; then
    ROOT_PASSWORD="$(random_password)"
  fi
  if [ -z "$ADMIN_PASSWORD" ]; then
    ADMIN_PASSWORD="$(random_password)"
  fi

  echo "[INFO] Bootstrapping ORS data..."
  "$PY" manage.py bootstrap_ors \
    --root-username "$ROOT_USERNAME" --root-password "$ROOT_PASSWORD" \
    --dept-name "$DEPT_NAME" --dept-code "$DEPT_CODE" \
    --admin-username "$ADMIN_USERNAME" --admin-password "$ADMIN_PASSWORD" \
    --admin-name "$ADMIN_NAME"

  echo "[INFO] Collecting static assets..."
  "$PY" manage.py collectstatic --noinput

  echo ""
  echo "[OK] Install finished."
  echo ""
  echo "[NEXT] Recommended gunicorn start command:"
  echo "  $VENV_DIR/bin/gunicorn ors_site.wsgi:application -b ${BIND_HOST}:${BIND_PORT} --workers ${GUNICORN_WORKERS}"
  echo ""
  echo "[NEXT] Login credentials (if created now):"
  echo "  root:  ${ROOT_USERNAME} / ${ROOT_PASSWORD}"
  echo "  admin: ${ADMIN_USERNAME} / ${ADMIN_PASSWORD}"
}

main "$@"
