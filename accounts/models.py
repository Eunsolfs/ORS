from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    username = models.CharField(max_length=50, unique=True, verbose_name="用户名")
    name = models.CharField(max_length=100, blank=True, default="", verbose_name="姓名")
    phone = models.CharField(max_length=30, blank=True, default="", verbose_name="手机号")
    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    last_login_at = models.DateTimeField(null=True, blank=True, verbose_name="最后登录时间")

    class Meta:
        verbose_name = "用户"
        verbose_name_plural = "用户"

    def __str__(self) -> str:
        return self.name or self.username
