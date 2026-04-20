# 宝塔面板部署（Django 版 ORS）

## 0. 推荐部署方式

生产环境推荐固定为：

- `gunicorn` 作为 Django 应用服务器
- `nginx` 负责反向代理与静态资源
- MySQL 可直接使用 `PyMySQL`，无需再折腾 `mysqlclient` 编译依赖

不再建议使用 `uWSGI`。在宝塔环境下，`uWSGI + MySQL` 更容易出现 worker 进程异常退出，表现为登录时 `502 Bad Gateway`。

## 1. 上传代码

把整个 `ORS` 目录上传到服务器，例如：

```bash
/www/wwwroot/ors
```

## 2. 准备 `.env`

复制 `.env.example` 为 `.env`，并至少确认这些值：

```env
DJANGO_SECRET_KEY=请改成你自己的随机密钥
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=你的域名,127.0.0.1,localhost
DJANGO_CSRF_TRUSTED_ORIGINS=https://你的域名
```

MySQL 示例：

```env
DB_ENGINE=django.db.backends.mysql
DB_NAME=ors
DB_USER=ors
DB_PASSWORD=strong-password
DB_HOST=127.0.0.1
DB_PORT=3306
```

注意：

- `DJANGO_CSRF_TRUSTED_ORIGINS` 不要额外加引号
- 脚本不会替你创建 MySQL 数据库和用户，只会使用你提供的连接信息运行迁移

如果你不想手工改 `.env`，也可以在运行安装脚本时传入环境变量，脚本会自动写回 `.env`：

```bash
cd /www/wwwroot/ors
DB_ENGINE=django.db.backends.mysql \
DB_NAME=ors \
DB_USER=ors \
DB_PASSWORD=strong-password \
DB_HOST=127.0.0.1 \
DB_PORT=3306 \
DJANGO_DEBUG=False \
DJANGO_ALLOWED_HOSTS=ors.example.com,127.0.0.1,localhost \
DJANGO_CSRF_TRUSTED_ORIGINS=https://ors.example.com \
./scripts/baota_install.sh
```

## 3. 一键安装（推荐）

```bash
cd /www/wwwroot/ors
chmod +x scripts/baota_install.sh
./scripts/baota_install.sh
```

如果你想指定端口和 worker 数量：

```bash
cd /www/wwwroot/ors
BIND_PORT=8989 GUNICORN_WORKERS=3 ./scripts/baota_install.sh
```

脚本会完成：

- 创建/复用 `.venv`
- 安装 `requirements.txt`
- 自动生成生产 `DJANGO_SECRET_KEY`（若仍为默认值）
- 执行 `migrate`
- 执行 `bootstrap_ors`
- 执行 `collectstatic`
- 输出推荐的 `gunicorn` 启动命令

## 4. gunicorn 启动方式

示例：

```bash
cd /www/wwwroot/ors
./.venv/bin/gunicorn ors_site.wsgi:application -b 127.0.0.1:8989 --workers 3
```

宝塔 Python 项目管理里建议：

- 启动方式：`gunicorn`
- 项目端口：`8989`
- 绑定地址：`127.0.0.1`
- 入口：`ors_site.wsgi:application`

### 宝塔界面最终填写清单

如果你在宝塔 Python 项目管理中直接新建/修改项目，推荐按下面填写：

- 项目路径：`/www/wwwroot/ors.summerecho.cn`
- 项目端口：`8989`
- 启动方式：`gunicorn`
- 框架：`django`
- 入口文件：`/www/wwwroot/ors.summerecho.cn/ors_site/wsgi.py`
- 通讯协议：`wsgi`
- 应用名称：`application`
- 环境变量：`从文件加载`
- 环境变量文件：`/www/wwwroot/ors.summerecho.cn/.env`
- 启动用户：`www`
- 进程数：`3`
- 线程数：`1`
- 是否开机启动：`开启`

如果宝塔要求填写 gunicorn 启动命令，可使用：

```bash
/www/wwwroot/ors.summerecho.cn/.venv/bin/gunicorn ors_site.wsgi:application -b 127.0.0.1:8989 --workers 3
```

不建议再使用：

- `uWSGI`
- `threads=2` 或更高的多线程配置
- `proxy_set_header Host 127.0.0.1:$server_port;`

## 5. nginx 反向代理与静态资源

请确保站点配置中同时包含静态资源与反向代理配置。

```nginx
location /static/ {
    alias /www/wwwroot/ors/staticfiles/;
}

location /media/ {
    alias /www/wwwroot/ors/media/;
}

location / {
    proxy_pass http://127.0.0.1:8989;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

说明：

- `proxy_set_header Host $host;` 不要写成 `127.0.0.1:$server_port`
- `X-Forwarded-Proto $scheme` 必须带上，否则 HTTPS 下登录/重定向/cookie 判断可能异常
- 修改 nginx 后记得重载配置

## 6. 初始化命令（手工方式）

如果你不使用安装脚本，也可以手工执行：

```bash
cd /www/wwwroot/ors
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
cp .env.example .env
./.venv/bin/python manage.py migrate
./.venv/bin/python manage.py bootstrap_ors \
  --root-username root --root-password root123456 \
  --dept-name 手术室 --dept-code ors \
  --admin-username admin --admin-password admin123456
./.venv/bin/python manage.py collectstatic --noinput
```

## 7. 使用入口

- 后台（root/科室管理员）：`/admin/`
- 成员入口：登录后会自动跳科室移动端
- 固定交班二维码页面：`/m/<dept_code>/handover/today/`

## 8. 权限说明

- `root`：`is_superuser=True`，全局管理所有科室与数据
- 科室管理员：`DepartmentMember.role_in_department=admin`，只能管理本科室数据
- 科室成员：`member`，可查看/新增/编辑自己填报的交班条目

## 9. 一键检查更新与升级（推荐）

新增脚本：`scripts/release_manager.py`（交互式）。

仅检查远端是否有更新：

```bash
cd /www/wwwroot/ors
./.venv/bin/python scripts/release_manager.py --check
```

交互式升级（支持输入 `n/y/main/指定tag`）：

```bash
cd /www/wwwroot/ors
./.venv/bin/python scripts/release_manager.py
```

如果当前站点目录没有 `.git`，首次使用请传入仓库地址：

```bash
cd /www/wwwroot/ors
./.venv/bin/python scripts/release_manager.py --repo-url https://github.com/Eunsolfs/ORS.git --check
./.venv/bin/python scripts/release_manager.py --repo-url https://github.com/Eunsolfs/ORS.git
```

交互输入说明：

- `y`：升级到推荐目标（优先最新 tag，其次 main）
- `main`：升级到 `origin/main`
- `v1.2.0`：升级到指定版本
- `n`：取消升级

自动化（非交互）示例：

```bash
cd /www/wwwroot/ors
./.venv/bin/python scripts/release_manager.py --target v1.2.0 --yes
```

脚本内置流程：

- 检查工作区是否干净（避免误覆盖）
- `git fetch --tags origin`
- 切换目标版本
- `pip install -r requirements.txt`
- `manage.py migrate --noinput`
- `manage.py collectstatic --noinput`
- `manage.py check`
- 默认执行 `manage.py test training`（可用 `--skip-test` 跳过）

