# ORS（手术室事项安排系统）

**当前版本：1.0.0**（2026-04-16）

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

## 存储配置位置（root）
- 后台 `SystemStorageSetting` 中设置 `backend` 与对应参数
- 建议仅保留一条 `is_active=True` 配置作为当前生效配置

