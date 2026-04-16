# 宝塔面板部署（Django 版 ORS）

## 0. 服务器准备
- 宝塔：Python 项目管理器（或手动 venv + gunicorn + nginx）
- MySQL 8（可选：也可先用 sqlite）
- Nginx

## 1. 上传代码
把整个 `ORS` 目录上传到服务器（建议：`/www/wwwroot/ors`）。

## 2. 创建 `.env`
复制 `.env.example` 为 `.env` 并按你的环境改：

- **生产建议**
  - `DJANGO_DEBUG=False`
  - `DJANGO_ALLOWED_HOSTS=你的域名,服务器IP`
  - 数据库切换为 MySQL（见 `.env.example`）

如果你不想手动改 `.env`，也可以在执行“一键安装脚本”时，通过命令行临时传入环境变量（脚本会写回 `.env`），例如 MySQL：

```bash
cd /www/wwwroot/ors
DB_ENGINE=django.db.backends.mysql \
DB_NAME=ors \
DB_USER=ors \
DB_PASSWORD=strong-password \
DB_HOST=127.0.0.1 \
DB_PORT=3306 \
./scripts/baota_install.sh
```

> 注意：脚本不会替你创建 MySQL 数据库/用户，只负责把参数写入 `.env` 后运行 `migrate`。

## 3. 安装依赖与初始化
```bash
cd /www/wwwroot/ors
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt

cp .env.example .env
./.venv/bin/python manage.py migrate

# 初始化 root + 默认科室 + 科室管理员（可改密码）
./.venv/bin/python manage.py bootstrap_ors \
  --root-username root --root-password root123456 \
  --dept-name 手术室 --dept-code ors \
  --admin-username admin --admin-password admin123456

./.venv/bin/python manage.py collectstatic --noinput
```

## 4. 启动方式（推荐 gunicorn）
安装 gunicorn：
```bash
./.venv/bin/pip install gunicorn
```

启动（示例）：
```bash
./.venv/bin/gunicorn ors_site.wsgi:application -b 127.0.0.1:9001 --workers 3
```

## 5. Nginx 反代示例
宝塔站点配置里添加（核心段）：
```nginx
location /static/ {
  alias /www/wwwroot/ors/staticfiles/;
}
location /media/ {
  alias /www/wwwroot/ors/media/;
}
location / {
  proxy_set_header Host $host;
  proxy_set_header X-Real-IP $remote_addr;
  proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
  proxy_set_header X-Forwarded-Proto $scheme;
  proxy_pass http://127.0.0.1:9001;
}
```

## 6. 使用入口
- 后台（root/科室管理员）：`/admin/`
- 成员入口：登录后会自动跳科室移动端
- **固定交班二维码（科室级固定）**：移动端首页会显示；对应链接为：
  - `/m/<dept_code>/handover/today/`

## 7. 权限说明
- **root**：`is_superuser=True`，全局管理所有科室与数据
- **科室管理员**：`DepartmentMember.role_in_department=admin`，只能管理本科室数据（导出权限也在此）
- **科室成员**：`member`，可查看/新增/编辑自己填报的交班条目

## 8. 一键安装脚本（宝塔推荐）

你可以跳过“手工步骤”，直接用脚本初始化 venv、依赖、数据库迁移、bootstrap 数据与静态文件。

```bash
cd /www/wwwroot/ors
chmod +x scripts/baota_install.sh
./scripts/baota_install.sh
```

若要改端口/worker（会影响脚本输出的 gunicorn 启动命令），可在执行前设置环境变量：

```bash
cd /www/wwwroot/ors
BIND_PORT=9001 GUNICORN_WORKERS=3 ./scripts/baota_install.sh
```

脚本会在结束时输出：
- 推荐的 `gunicorn` 启动命令
- 若未提供 `ROOT_PASSWORD` / `ADMIN_PASSWORD`，则会生成并打印初次 `root/admin` 密码

