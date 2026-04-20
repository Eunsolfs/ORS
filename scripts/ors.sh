#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${ROOT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
DEFAULT_REPO_URL="${DEFAULT_REPO_URL:-https://github.com/Eunsolfs/ORS.git}"
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
  ./scripts/ors.sh
  ./scripts/ors.sh menu

  # root 用户管理
  ./scripts/ors.sh root show
  ./scripts/ors.sh root create --username root --password 'xxx' [--name Root]
  ./scripts/ors.sh root update --username root [--new-username root2] [--password 'xxx'] [--name '新名称'] [--active true|false]
  ./scripts/ors.sh root reset-password --username root --password '新密码'

  # ORS 版本管理
  ./scripts/ors.sh upgrade check [--repo-url URL]
  ./scripts/ors.sh upgrade run [--repo-url URL] [--target main|v1.2.0] [--yes] [--skip-test]
  ./scripts/ors.sh upgrade tags

常用示例:
  # 首次接入（站点目录没有 .git）
  ./scripts/ors.sh upgrade check --repo-url https://github.com/Eunsolfs/ORS.git
  ./scripts/ors.sh upgrade run --repo-url https://github.com/Eunsolfs/ORS.git

  # 查看可用版本标签
  ./scripts/ors.sh upgrade tags

  # 升级到最新推荐版本（交互输入 y/n/main/tag）
  ./scripts/ors.sh upgrade run

  # 非交互升级到指定版本
  ./scripts/ors.sh upgrade run --target v1.3.0 --yes

  # 非交互升级到主分支最新提交
  ./scripts/ors.sh upgrade run --target main --yes

说明:
  - root create: 创建 root 超级管理员（若已存在会报错）
  - root update: 修改 root 用户信息（用户名/密码/姓名/启用状态）
  - root reset-password: 仅重置密码（最常用）
  - upgrade 命令封装 scripts/release_manager.py
EOF
}

show_menu() {
  cat <<'EOF'

================ ORS 管理菜单 ================
  1) 查看 root/superuser 列表
  2) 创建 root 用户
  3) 修改 root 用户信息（用户名/密码/姓名/启用状态）
  4) 快速重置 root 密码
  5) 检查版本更新
  6) 查看版本标签列表
  7) 交互升级（y/n/main/tag）
  8) 升级到指定 tag（非交互）
  9) 升级到 main 最新提交（非交互）
  0) 退出
=============================================
EOF
}

menu_loop() {
  local repo_url="" username="" password="" name="" new_username="" active="" target=""
  while true; do
    show_menu
    read -r -p "请输入数字选项: " choice
    case "$choice" in
      1)
        root_show
        ;;
      2)
        read -r -p "root 用户名: " username
        read -r -p "root 密码: " password
        read -r -p "root 姓名(默认 root): " name
        name="${name:-root}"
        root_create --username "$username" --password "$password" --name "$name"
        ;;
      3)
        read -r -p "当前用户名: " username
        read -r -p "新用户名(可留空): " new_username
        read -r -p "新密码(可留空): " password
        read -r -p "新姓名(可留空): " name
        read -r -p "是否启用(true/false，可留空): " active
        local args=(--username "$username")
        if [ -n "$new_username" ]; then args+=(--new-username "$new_username"); fi
        if [ -n "$password" ]; then args+=(--password "$password"); fi
        if [ -n "$name" ]; then args+=(--name "$name"); fi
        if [ -n "$active" ]; then args+=(--active "$active"); fi
        root_update "${args[@]}"
        ;;
      4)
        read -r -p "用户名: " username
        read -r -p "新密码: " password
        root_reset_password --username "$username" --password "$password"
        ;;
      5)
        read -r -p "仓库地址(可留空): " repo_url
        repo_url="${repo_url:-$DEFAULT_REPO_URL}"
        upgrade_check --repo-url "$repo_url"
        ;;
      6)
        upgrade_tags
        ;;
      7)
        read -r -p "仓库地址(可留空): " repo_url
        repo_url="${repo_url:-$DEFAULT_REPO_URL}"
        upgrade_run --repo-url "$repo_url"
        ;;
      8)
        read -r -p "目标 tag（如 v1.3.0）: " target
        read -r -p "仓库地址(可留空): " repo_url
        repo_url="${repo_url:-$DEFAULT_REPO_URL}"
        upgrade_run --repo-url "$repo_url" --target "$target" --yes
        ;;
      9)
        read -r -p "仓库地址(可留空): " repo_url
        repo_url="${repo_url:-$DEFAULT_REPO_URL}"
        upgrade_run --repo-url "$repo_url" --target main --yes
        ;;
      0)
        echo "已退出。"
        return 0
        ;;
      *)
        echo "[ERROR] 无效选项: $choice"
        ;;
    esac
    echo ""
    read -r -p "按回车继续..."
  done
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

root_reset_password() {
  local username="" password=""
  while [ $# -gt 0 ]; do
    case "$1" in
      --username) username="${2:-}"; shift 2 ;;
      --password) password="${2:-}"; shift 2 ;;
      *) echo "[ERROR] 未知参数: $1"; exit 1 ;;
    esac
  done
  if [ -z "$username" ] || [ -z "$password" ]; then
    echo "[ERROR] root reset-password 需要 --username 和 --password"
    exit 1
  fi

  "$PYTHON_BIN" manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
u = User.objects.filter(username='$username').first()
if not u:
    raise SystemExit('用户不存在: $username')
u.is_superuser = True
u.is_staff = True
u.set_password('$password')
u.save(update_fields=['password', 'is_superuser', 'is_staff'])
print('已重置密码:', u.username)
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

upgrade_tags() {
  git -C "$ROOT_DIR" fetch --tags origin >/dev/null 2>&1 || true
  git -C "$ROOT_DIR" tag --list | sort -V
}

main() {
  local module="${1:-}"
  local action="${2:-}"

  if [ -z "$module" ]; then
    menu_loop
    exit 0
  fi

  if [ "$module" = "menu" ]; then
    menu_loop
    exit 0
  fi

  if [ -z "$action" ]; then
    usage
    exit 1
  fi
  shift 2

  case "$module:$action" in
    root:show) root_show "$@" ;;
    root:create) root_create "$@" ;;
    root:update) root_update "$@" ;;
    root:reset-password) root_reset_password "$@" ;;
    upgrade:check) upgrade_check "$@" ;;
    upgrade:run) upgrade_run "$@" ;;
    upgrade:tags) upgrade_tags "$@" ;;
    *)
      usage
      exit 1
      ;;
  esac
}

main "$@"
