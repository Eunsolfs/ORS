# ORS（手术室事项安排系统）

**当前版本：1.3.0**（2026-04-20）

## 快速启动（本机开发）
```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
copy .env.example .env
.\.venv\Scripts\python manage.py migrate
.\.venv\Scripts\python manage.py createsuperuser
.\.venv\Scripts\python manage.py runserver
```

后台：`/admin/`

## 生产部署

- **1Panel（三种方式：Compose / 宿主机 Python / 1Panel Python 容器）**：见 [DEPLOY_1PANEL.md](DEPLOY_1PANEL.md)
- **宝塔面板**：见 [DEPLOY_BAOTA.md](DEPLOY_BAOTA.md)

## 新增能力（已完成）
- 教程编辑页支持可视化富文本（TinyMCE）
- 教程图片可直接上传并自动插入内容
- 超级管理员可在后台配置资源存储后端：
  - 本机服务器（默认）
  - S3 对象存储
  - WebDAV
- 科室管理员可使用：
  - 报表统计中心：`/m/<dept_code>/reports/`
  - 今日大屏：`/m/<dept_code>/dashboard/today/`
- 教程支持“访问权限”配置：
  - 同科室可见（登录后访问）
  - 公开可见（可配置访问密码）
- 教程详情支持公开访问入口：`/m/<dept_code>/courses/public/<course_id>/`

## 发布前最小检查
```powershell
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python manage.py migrate
.\.venv\Scripts\python manage.py check
.\.venv\Scripts\python manage.py test training
```

若以上命令通过，再执行 `collectstatic` 并启动 Gunicorn / 平台服务。

## 常用运维脚本

统一入口脚本：`scripts/ors.sh`

- 查看 root/superuser 列表：
  - `./scripts/ors.sh root show`
- 创建 root 用户：
  - `./scripts/ors.sh root create --username root --password '强密码' --name 'Root'`
- 修改 root 用户（用户名/密码/姓名/启用状态）：
  - `./scripts/ors.sh root update --username root --new-username root2 --password '新密码' --name '新名称' --active true`
- 检查版本更新：
  - `./scripts/ors.sh upgrade check --repo-url https://github.com/Eunsolfs/ORS.git`
- 交互升级：
  - `./scripts/ors.sh upgrade run --repo-url https://github.com/Eunsolfs/ORS.git`

## 存储配置位置（root）
- 后台 `SystemStorageSetting` 中设置 `backend` 与对应参数
- 建议仅保留一条 `is_active=True` 配置作为当前生效配置

