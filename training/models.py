from django.conf import settings
from django.db import models
from django.contrib.auth.hashers import check_password, make_password

from orgs.models import Department


class Course(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "草稿"
        PUBLISHED = "published", "发布"
        INACTIVE = "inactive", "失效"

    class Visibility(models.TextChoices):
        DEPARTMENT = "department", "同科室可见（需登录）"
        PUBLIC = "public", "所有人可见（可选访问密码）"

    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="courses", verbose_name="科室")
    title = models.CharField(max_length=200, verbose_name="课程标题")
    slug = models.SlugField(max_length=220, blank=True, default="", verbose_name="别名")

    content_html = models.TextField(blank=True, default="", verbose_name="课程内容")
    cover_image_path = models.CharField(max_length=500, blank=True, default="", verbose_name="封面图")

    video_provider = models.CharField(max_length=30, blank=True, default="", verbose_name="视频平台")
    video_url = models.CharField(max_length=500, blank=True, default="", verbose_name="视频链接")
    video_embed_html = models.TextField(blank=True, default="", verbose_name="视频嵌入代码")

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PUBLISHED, verbose_name="状态")
    visibility = models.CharField(
        max_length=20,
        choices=Visibility.choices,
        default=Visibility.DEPARTMENT,
        verbose_name="访问权限",
    )
    public_access_password_hash = models.CharField(max_length=128, blank=True, default="", verbose_name="公开访问密码哈希")
    public_access_password_plain = models.CharField(max_length=128, blank=True, default="", verbose_name="公开访问密码明文")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_courses", verbose_name="创建人"
    )
    published_at = models.DateTimeField(null=True, blank=True, verbose_name="发布时间")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "课程"
        verbose_name_plural = "课程"
        indexes = [
            models.Index(fields=["department", "status"]),
            models.Index(fields=["slug"]),
        ]

    def __str__(self) -> str:
        return self.title

    @property
    def has_public_access_password(self) -> bool:
        return bool(self.public_access_password_hash)

    def set_public_access_password(self, raw_password: str) -> None:
        raw = (raw_password or "").strip()
        self.public_access_password_hash = make_password(raw) if raw else ""
        self.public_access_password_plain = raw

    def check_public_access_password(self, raw_password: str) -> bool:
        if not self.public_access_password_hash:
            return True
        return check_password(raw_password or "", self.public_access_password_hash)


class MediaAsset(models.Model):
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="media_assets", verbose_name="科室")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="uploaded_media_assets", verbose_name="上传人"
    )
    file_name = models.CharField(max_length=255, verbose_name="文件名")
    file_url = models.CharField(max_length=1000, verbose_name="文件地址")
    storage_backend = models.CharField(max_length=30, default="local", verbose_name="存储后端")
    object_key = models.CharField(max_length=500, blank=True, default="", verbose_name="对象键")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        verbose_name = "媒体素材"
        verbose_name_plural = "媒体素材"
        indexes = [
            models.Index(fields=["department", "created_at"]),
        ]

    def __str__(self) -> str:
        return self.file_name
