from __future__ import annotations

from typing import Iterable

from django.contrib.auth.models import Permission

from .models import DepartmentMember


def get_admin_departments_for_user(user):
    if not user or not user.is_authenticated:
        return []
    if user.is_superuser:
        return []
    return list(
        DepartmentMember.objects.filter(user=user, is_active=True, role_in_department=DepartmentMember.Role.ADMIN)
        .select_related("department")
        .values_list("department_id", flat=True)
    )


def ensure_dept_admin_model_perms(user, model_labels: Iterable[str]):
    """
    给科室管理员授予指定模型的 add/change/delete/view 权限（Django admin 使用）。
    model_labels: 形如 ["accounts.user", "orgs.departmentmember"].
    """
    if not user or not user.is_authenticated or user.is_superuser:
        return
    dept_ids = get_admin_departments_for_user(user)
    if not dept_ids:
        return

    perms = []
    for label in model_labels:
        app_label, model = label.split(".")
        for codename in (f"add_{model}", f"change_{model}", f"delete_{model}", f"view_{model}"):
            p = Permission.objects.filter(content_type__app_label=app_label, codename=codename).first()
            if p:
                perms.append(p)
    if perms:
        user.user_permissions.add(*perms)

