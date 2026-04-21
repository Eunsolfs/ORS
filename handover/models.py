from django.conf import settings
from django.db import models

from orgs.models import Department


class HandoverSession(models.Model):
    class TriStatus(models.TextChoices):
        YES = "yes", "✅"
        NO = "no", "❌"
        OTHER = "other", "其他"

    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="handover_sessions", verbose_name="科室")
    handover_date = models.DateField(verbose_name="交班日期")

    elective_count = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name="择期手术数")
    emergency_count = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name="急诊手术数")
    rescue_count = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name="抢救手术数")
    notes = models.TextField(blank=True, default="", verbose_name="备注")

    other_incidents = models.TextField(blank=True, default="", verbose_name="其他事件")

    specimen_handover_status = models.CharField(max_length=10, choices=TriStatus.choices, blank=True, default="", verbose_name="标本交接状态")
    specimen_handover_note = models.CharField(max_length=300, blank=True, default="", verbose_name="标本交接说明")
    laminar_flow_running_status = models.CharField(max_length=10, choices=TriStatus.choices, blank=True, default="", verbose_name="层流运行状态")
    laminar_flow_running_note = models.CharField(max_length=300, blank=True, default="", verbose_name="层流运行说明")
    bio_monitoring_status = models.CharField(max_length=10, choices=TriStatus.choices, blank=True, default="", verbose_name="生物监测状态")
    bio_monitoring_note = models.CharField(max_length=300, blank=True, default="", verbose_name="生物监测说明")
    crash_cart_status = models.CharField(max_length=10, choices=TriStatus.choices, blank=True, default="", verbose_name="急救车状态")
    crash_cart_note = models.CharField(max_length=300, blank=True, default="", verbose_name="急救车说明")
    fire_safety_status = models.CharField(max_length=10, choices=TriStatus.choices, blank=True, default="", verbose_name="消防安全状态")
    fire_safety_note = models.CharField(max_length=300, blank=True, default="", verbose_name="消防安全说明")
    key_management_status = models.CharField(max_length=10, choices=TriStatus.choices, blank=True, default="", verbose_name="钥匙管理状态")
    key_management_note = models.CharField(max_length=300, blank=True, default="", verbose_name="钥匙管理说明")
    certs_in_place_status = models.CharField(max_length=10, choices=TriStatus.choices, blank=True, default="", verbose_name="合格证收纳状态")
    certs_in_place_note = models.CharField(max_length=300, blank=True, default="", verbose_name="合格证收纳说明")

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_handover_sessions",
        verbose_name="创建人",
    )
    locked_at = models.DateTimeField(null=True, blank=True, verbose_name="锁定时间")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "交班记录"
        verbose_name_plural = "交班记录"
        constraints = [
            models.UniqueConstraint(fields=["department", "handover_date"], name="uniq_dept_handover_date"),
        ]
        indexes = [
            models.Index(fields=["department", "handover_date"]),
        ]

    def __str__(self) -> str:
        return f"{self.department} {self.handover_date}"


class HandoverItem(models.Model):
    class YesNo(models.TextChoices):
        YES = "√", "✅"
        NO = "×", "❌"

    class SkinCondition(models.TextChoices):
        NORMAL = "完整", "完整"
        DAMAGED = "缺损", "缺损"

    session = models.ForeignKey(HandoverSession, on_delete=models.CASCADE, related_name="items", verbose_name="所属交班")

    department_text = models.CharField(max_length=100, blank=True, default="", verbose_name="科室")
    patient_name = models.CharField(max_length=100, blank=True, default="", verbose_name="姓名")
    age = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name="年龄")
    surgery_name = models.TextField(blank=True, default="", verbose_name="手术名称")

    special_handover = models.TextField(blank=True, default="", verbose_name="特殊病情交接")
    blood_transfusion_checks = models.CharField(max_length=2, choices=YesNo.choices, blank=True, default="", verbose_name="输血前九项")
    pressure_ulcer_assessment = models.CharField(max_length=2, choices=YesNo.choices, blank=True, default="", verbose_name="压疮评估单")
    skin_condition = models.CharField(max_length=4, choices=SkinCondition.choices, blank=True, default="", verbose_name="皮肤情况")
    preop_visit = models.CharField(max_length=2, choices=YesNo.choices, blank=True, default="", verbose_name="术前访视")
    special_instruments = models.TextField(blank=True, default="", verbose_name="特殊器械准备")
    status = models.CharField(max_length=20, default="active", verbose_name="状态")

    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reported_handover_items",
        verbose_name="填报人",
    )
    reported_at = models.DateTimeField(null=True, blank=True, verbose_name="填报时间")
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_handover_items",
        verbose_name="更新人",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "手术交班条目"
        verbose_name_plural = "手术交班条目"
        indexes = [
            models.Index(fields=["session"]),
            models.Index(fields=["reported_by"]),
        ]

    def __str__(self) -> str:
        return f"{self.session} - {self.patient_name or self.surgery_name}"
