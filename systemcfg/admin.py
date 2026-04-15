from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError

from .models import SystemStorageSetting


class SystemStorageSettingForm(forms.ModelForm):
    class Meta:
        model = SystemStorageSetting
        fields = "__all__"

    def clean(self):
        cleaned = super().clean()
        backend = cleaned.get("backend")

        def req(field: str, label: str | None = None):
            if not cleaned.get(field):
                raise ValidationError({field: f"{label or field} 为必填项"})

        if backend == SystemStorageSetting.Backend.LOCAL:
            req("local_subdir", "本地子目录")
        elif backend == SystemStorageSetting.Backend.S3:
            req("s3_bucket", "S3 Bucket")
            req("s3_access_key", "S3 Access Key")
            req("s3_secret_key", "S3 Secret Key")
        elif backend == SystemStorageSetting.Backend.WEBDAV:
            req("webdav_base_url", "WebDAV Base URL")
            req("webdav_username", "WebDAV 用户名")
            req("webdav_password", "WebDAV 密码")
        return cleaned


@admin.register(SystemStorageSetting)
class SystemStorageSettingAdmin(admin.ModelAdmin):
    form = SystemStorageSettingForm
    list_display = ("name", "backend", "is_active", "updated_at")
    list_filter = ("backend", "is_active")

    fieldsets = (
        ("基础", {"fields": ("name", "backend", "is_active")}),
        (
            "本地存储（LOCAL）",
            {
                "fields": ("local_subdir", "local_base_url"),
                "classes": ("collapse",),
            },
        ),
        (
            "S3 对象存储（S3）",
            {
                "fields": (
                    "s3_endpoint_url",
                    "s3_region",
                    "s3_bucket",
                    "s3_access_key",
                    "s3_secret_key",
                    "s3_base_url",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "WebDAV（WEBDAV）",
            {
                "fields": ("webdav_base_url", "webdav_username", "webdav_password", "webdav_upload_path"),
                "classes": ("collapse",),
            },
        ),
        ("时间", {"fields": ("updated_at",)}),
    )

    readonly_fields = ("updated_at",)

    class Media:
        js = ("systemcfg/admin_storage.js",)
