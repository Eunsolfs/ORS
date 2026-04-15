from django.db import models


class SystemStorageSetting(models.Model):
    class Backend(models.TextChoices):
        LOCAL = "local", "本机服务器"
        S3 = "s3", "S3 对象存储"
        WEBDAV = "webdav", "WebDAV"

    name = models.CharField(max_length=100, default="default")
    backend = models.CharField(max_length=20, choices=Backend.choices, default=Backend.LOCAL)

    # local
    local_subdir = models.CharField(max_length=200, default="uploads")
    local_base_url = models.CharField(max_length=300, blank=True, default="")

    # S3
    s3_endpoint_url = models.CharField(max_length=500, blank=True, default="")
    s3_region = models.CharField(max_length=100, blank=True, default="")
    s3_bucket = models.CharField(max_length=200, blank=True, default="")
    s3_access_key = models.CharField(max_length=200, blank=True, default="")
    s3_secret_key = models.CharField(max_length=200, blank=True, default="")
    s3_base_url = models.CharField(max_length=500, blank=True, default="")

    # webdav
    webdav_base_url = models.CharField(max_length=500, blank=True, default="")
    webdav_username = models.CharField(max_length=200, blank=True, default="")
    webdav_password = models.CharField(max_length=200, blank=True, default="")
    webdav_upload_path = models.CharField(max_length=300, blank=True, default="uploads/")

    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "系统存储配置"
        verbose_name_plural = "系统存储配置"

    def __str__(self) -> str:
        return f"{self.name} ({self.backend})"

