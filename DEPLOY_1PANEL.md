# 1Panel 部署（含三种方式）

当前项目在 1Panel 下支持三种方式：

- 方式 A：`Docker Compose`（见本文后半段，原方案保留）
- 方式 B：源码目录 + Python 虚拟环境（宿主机直接运行）
- 方式 C：**1Panel UI 创建 Python 环境（容器运行，适配你截图）**

---

## 方式 C：1Panel UI 创建 Python 环境（容器运行，按页面填写）

你截图中的页面包含“容器名称/端口/挂载”，本质是 **容器内运行 Python**。  
因此连接 1Panel MySQL 时，应使用容器连接地址：`1Panel-mysql-Fp5Y:3306`。

### 1. 页面填写建议

- 名称：`ors-python`
- 项目目录：`/opt/www/ors`（你上传源码目录）
- 应用：`Python`
- 版本：建议 `3.12.x`（不建议 3.14，三方依赖兼容性风险更高）
- 容器名称：`ors-python`

启动命令（可直接粘贴）：

```bash
pip install -r requirements.txt && python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn ors_site.wsgi:application -b 0.0.0.0:8989 --workers 3
```

### 2. 端口

在“端口”里新增一条：

- 容器端口：`8989`
- 主机端口：`8989`（或你要暴露的其它端口）

### 3. 环境变量

可在“环境变量”页签逐项添加（或挂载 `.env` 文件）：

```env
DJANGO_SECRET_KEY=请改成随机长密钥
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=你的域名,127.0.0.1,localhost
DJANGO_CSRF_TRUSTED_ORIGINS=https://你的域名
DJANGO_SESSION_COOKIE_SECURE=True
DJANGO_CSRF_COOKIE_SECURE=True
DJANGO_SECURE_SSL_REDIRECT=True
DJANGO_SESSION_IDLE_AGE=43200
DJANGO_SESSION_ABSOLUTE_AGE=43200
ORS_LOGIN_CAPTCHA_MODE=alnum
ORS_LOGIN_CAPTCHA_LENGTH=5

DB_ENGINE=django.db.backends.mysql
DB_NAME=ors
DB_USER=ors
DB_PASSWORD=请填写数据库密码
DB_HOST=1Panel-mysql-Fp5Y
DB_PORT=3306
```

### 4. 站点反代

在 1Panel 网站/Nginx 中将域名反代到 `127.0.0.1:8989`，并保留：

- `proxy_set_header Host $host;`
- `proxy_set_header X-Forwarded-Proto $scheme;`

---

## 方式 B：源码目录 + Python 虚拟环境（推荐你当前场景）

## 1. 上传源码到网站目录

示例目录：

```bash
/opt/www/ors
```

进入目录后确保有 `manage.py`、`requirements.txt`、`.env.example`。

## 2. 配置 `.env`（连接 1Panel MySQL 容器）

```bash
cd /opt/www/ors
cp .env.example .env
```

编辑 `.env`，至少确认：

```env
DJANGO_SECRET_KEY=请改成随机长密钥
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=你的域名,127.0.0.1,localhost
DJANGO_CSRF_TRUSTED_ORIGINS=https://你的域名

DB_ENGINE=django.db.backends.mysql
DB_NAME=ors
DB_USER=ors
DB_PASSWORD=请填写数据库密码
DB_HOST=127.0.0.1
DB_PORT=3306
DJANGO_SESSION_IDLE_AGE=43200
DJANGO_SESSION_ABSOLUTE_AGE=43200
ORS_LOGIN_CAPTCHA_MODE=alnum
ORS_LOGIN_CAPTCHA_LENGTH=5
```

### 连接地址说明（按你给的规则）

- 容器内应用 / PHP 运行环境：使用 `1Panel-mysql-Fp5Y:3306`
- **非容器环境（当前 Python 网站目录部署）**：使用 `127.0.0.1:3306`

因此本方案里，`DB_HOST` 应写 `127.0.0.1`。

### 登录安全参数说明

- `DJANGO_SESSION_IDLE_AGE`：无操作超时（秒）
- `DJANGO_SESSION_ABSOLUTE_AGE`：登录后最长保活时长（秒）
- `ORS_LOGIN_CAPTCHA_MODE`：`digit` / `alpha` / `alnum`
- `ORS_LOGIN_CAPTCHA_LENGTH`：验证码长度（建议 4-8）

## 3. 一键初始化（Python 环境）

执行：

```bash
cd /opt/www/ors
chmod +x scripts/1panel_python_install.sh
./scripts/1panel_python_install.sh
```

脚本会自动完成：

- 创建/复用 `.venv`
- 安装 `requirements.txt`
- 在 `.env` 仍为默认值时自动生成生产 `DJANGO_SECRET_KEY`
- 执行 `migrate`
- 执行 `bootstrap_ors`
- 执行 `collectstatic`
- 输出推荐 Gunicorn 启动命令

也可以用统一脚本快速写入登录策略：

```bash
cd /opt/www/ors
./scripts/ors.sh auth set-policy --idle-age 43200 --absolute-age 43200 --captcha-mode alnum --captcha-length 5
```

可选指定端口/worker：

```bash
BIND_PORT=8989 GUNICORN_WORKERS=3 ./scripts/1panel_python_install.sh
```

## 4. 在 1Panel 网站中配置 Python 项目

建议参数：

- 项目路径：`/opt/www/ors`
- 启动方式：`gunicorn`
- 监听地址：`127.0.0.1`
- 项目端口：`8989`（与上一步保持一致）
- 入口：`ors_site.wsgi:application`
- 环境变量文件：`/opt/www/ors/.env`

可用启动命令示例：

```bash
/opt/www/ors/.venv/bin/gunicorn ors_site.wsgi:application -b 127.0.0.1:8989 --workers 3
```

## 5. 1Panel 站点反向代理（HTTPS）

若你使用 1Panel 网站/Nginx 转发到 Gunicorn，请确保：

- `proxy_set_header Host $host;`
- `proxy_set_header X-Forwarded-Proto $scheme;`

否则 HTTPS 下登录、重定向、Cookie 可能异常。

## 6. 功能说明

- 交班表导出 PDF 依赖 `soffice`（LibreOffice），若未安装可先不启用该能力。
- 使用入口：后台 `/admin/`；固定交班二维码 `/m/<dept_code>/handover/today/`。

## 7. 一键检查更新与升级（推荐）

新增脚本：`scripts/release_manager.py`（交互式）。

先检查是否有更新：

```bash
cd /opt/www/ors
python scripts/release_manager.py --check
```

交互式升级（支持输入 `n/y/main/指定tag`）：

```bash
cd /opt/www/ors
python scripts/release_manager.py
```

如果网站目录是“仅上传代码、没有 `.git`”的首次接入，请带仓库地址：

```bash
cd /opt/www/ors
python scripts/release_manager.py --repo-url https://github.com/Eunsolfs/ORS.git --check
python scripts/release_manager.py --repo-url https://github.com/Eunsolfs/ORS.git
```

说明：

- 输入 `y`：自动升级到推荐目标（优先最新 tag，其次 main）
- 输入 `main`：升级到 `origin/main`
- 输入 `v1.2.0` 这类 tag：升级到指定版本
- 输入 `n`：取消

非交互方式示例：

```bash
cd /opt/www/ors
python scripts/release_manager.py --target v1.2.0 --yes
```

脚本会自动执行：

- `git fetch --tags origin`
- 切换目标版本（`main` 或指定 `tag`）
- 安装依赖
- `migrate`
- `collectstatic`
- `check`
- 默认执行 `test training`（可加 `--skip-test` 跳过）

---

## 方式 A：Docker Compose（原方案保留）

如你后续改回容器化应用部署，可继续使用 `deploy/1panel/` 下文件：

- `docker-compose.yml`（内置 MySQL）
- `docker-compose.external-db.yml`（外部 MySQL）
- `env.example`
- `Dockerfile`

容器化模式下，`DB_HOST` 规则和本文方式 B 不同，请以 `deploy/1panel` 内文档为准。
