from datetime import time as time_type

from django.conf import settings
from django.db import models


class Department(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="科室名称")
    code = models.CharField(max_length=50, unique=True, blank=True, default="", verbose_name="科室编码")
    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    handover_cutoff_time = models.TimeField(default=time_type(hour=8, minute=10), verbose_name="交班填报截止时间")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_departments",
        verbose_name="创建人",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "科室"
        verbose_name_plural = "科室"
        indexes = [
            models.Index(fields=["is_active"]),
        ]

    def __str__(self) -> str:
        return self.name


class DepartmentMember(models.Model):
    class Role(models.TextChoices):
        ADMIN = "admin", "科室管理员"
        MEMBER = "member", "科室成员"

    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="members", verbose_name="科室")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="department_memberships", verbose_name="用户")
    role_in_department = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBER, verbose_name="科室角色")
    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    joined_at = models.DateTimeField(null=True, blank=True, verbose_name="加入时间")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_department_memberships",
        verbose_name="创建人",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "科室成员"
        verbose_name_plural = "科室成员"
        constraints = [
            models.UniqueConstraint(fields=["department", "user"], name="uniq_department_user"),
        ]
        indexes = [
            models.Index(fields=["department"]),
            models.Index(fields=["user"]),
            models.Index(fields=["department", "role_in_department"]),
        ]

    def __str__(self) -> str:
        return f"{self.department} - {self.user} ({self.role_in_department})"
