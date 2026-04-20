#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${ROOT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
cd "$ROOT_DIR"

if [ -x ".venv/bin/python" ]; then
  PYTHON_BIN=".venv/bin/python"
elif [ -x ".venv/Scripts/python.exe" ]; then
  PYTHON_BIN=".venv/Scripts/python.exe"
else
  echo "[ERROR] 未找到项目虚拟环境 Python，请先初始化 .venv"
  exit 1
fi

usage() {
  cat <<'EOF'
ORS 管理脚本

用法:
  ./scripts/ors.sh root show
  ./scripts/ors.sh root create --username root --password 'xxx' [--name Root]
  ./scripts/ors.sh root update --username root [--new-username root2] [--password 'xxx'] [--name '新名称'] [--active true|false]

  ./scripts/ors.sh upgrade check [--repo-url URL]
  ./scripts/ors.sh upgrade run [--repo-url URL] [--target main|v1.2.0] [--yes] [--skip-test]

说明:
  - root create: 创建 root 超级管理员（若已存在会报错）
  - root update: 修改 root 用户信息（用户名/密码/姓名/启用状态）
  - upgrade 命令封装 scripts/release_manager.py
EOF
}

bool_to_py() {
  case "${1:-}" in
    true|True|1|yes|y) echo "True" ;;
    false|False|0|no|n) echo "False" ;;
    *)
      echo "[ERROR] 非法布尔值: $1 (允许 true/false)"
      exit 1
      ;;
  esac
}

root_show() {
  "$PYTHON_BIN" manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
qs = User.objects.filter(is_superuser=True).order_by('id')
if not qs.exists():
    print('未找到 root/superuser 用户')
else:
    for u in qs:
        print(f'id={u.id} username={u.username} name={u.name or \"-\"} active={u.is_active} staff={u.is_staff} superuser={u.is_superuser}')
"
}

root_create() {
  local username="" password="" name="root"
  while [ $# -gt 0 ]; do
    case "$1" in
      --username) username="${2:-}"; shift 2 ;;
      --password) password="${2:-}"; shift 2 ;;
      --name) name="${2:-}"; shift 2 ;;
      *) echo "[ERROR] 未知参数: $1"; exit 1 ;;
    esac
  done
  if [ -z "$username" ] || [ -z "$password" ]; then
    echo "[ERROR] root create 需要 --username 和 --password"
    exit 1
  fi

  "$PYTHON_BIN" manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if User.objects.filter(username='$username').exists():
    raise SystemExit('用户已存在: $username')
u = User.objects.create(username='$username', is_superuser=True, is_staff=True, is_active=True, name='$name')
u.set_password('$password')
u.save(update_fields=['password'])
print('已创建 root 用户: $username')
"
}

root_update() {
  local username="" new_username="" password="" name="" active=""
  while [ $# -gt 0 ]; do
    case "$1" in
      --username) username="${2:-}"; shift 2 ;;
      --new-username) new_username="${2:-}"; shift 2 ;;
      --password) password="${2:-}"; shift 2 ;;
      --name) name="${2:-}"; shift 2 ;;
      --active) active="${2:-}"; shift 2 ;;
      *) echo "[ERROR] 未知参数: $1"; exit 1 ;;
    esac
  done
  if [ -z "$username" ]; then
    echo "[ERROR] root update 需要 --username"
    exit 1
  fi
  if [ -z "$new_username" ] && [ -z "$password" ] && [ -z "$name" ] && [ -z "$active" ]; then
    echo "[ERROR] root update 至少提供一个修改项"
    exit 1
  fi

  local active_py=""
  if [ -n "$active" ]; then
    active_py="$(bool_to_py "$active")"
  fi

  "$PYTHON_BIN" manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
u = User.objects.filter(username='$username').first()
if not u:
    raise SystemExit('用户不存在: $username')
u.is_superuser = True
u.is_staff = True
if '$new_username':
    u.username = '$new_username'
if '$name':
    u.name = '$name'
if '$active_py':
    u.is_active = $active_py
if '$password':
    u.set_password('$password')
u.save()
print('已更新 root 用户:', u.username)
"
}

upgrade_check() {
  local args=()
  while [ $# -gt 0 ]; do
    case "$1" in
      --repo-url) args+=("--repo-url" "${2:-}"); shift 2 ;;
      *) echo "[ERROR] 未知参数: $1"; exit 1 ;;
    esac
  done
  "$PYTHON_BIN" scripts/release_manager.py --check "${args[@]}"
}

upgrade_run() {
  local args=()
  while [ $# -gt 0 ]; do
    case "$1" in
      --repo-url|--target)
        args+=("$1" "${2:-}")
        shift 2
        ;;
      --yes|--skip-test)
        args+=("$1")
        shift
        ;;
      *)
        echo "[ERROR] 未知参数: $1"
        exit 1
        ;;
    esac
  done
  "$PYTHON_BIN" scripts/release_manager.py "${args[@]}"
}

main() {
  local module="${1:-}"
  local action="${2:-}"
  if [ -z "$module" ] || [ -z "$action" ]; then
    usage
    exit 1
  fi
  shift 2

  case "$module:$action" in
    root:show) root_show "$@" ;;
    root:create) root_create "$@" ;;
    root:update) root_update "$@" ;;
    upgrade:check) upgrade_check "$@" ;;
    upgrade:run) upgrade_run "$@" ;;
    *)
      usage
      exit 1
      ;;
  esac
}

main "$@"
