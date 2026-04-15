from __future__ import annotations

from typing import Optional

from django.contrib.auth import get_user_model

from .models import Department, DepartmentMember


def get_active_department_by_code(code: str) -> Optional[Department]:
    if not code:
        return None
    return Department.objects.filter(is_active=True, code=code).first()


def user_is_root(user) -> bool:
    return bool(user and user.is_authenticated and user.is_superuser)


def get_user_membership(user, department: Department) -> Optional[DepartmentMember]:
    if not user or not user.is_authenticated:
        return None
    return DepartmentMember.objects.filter(user=user, department=department, is_active=True).first()


def user_has_department_role(user, department: Department, roles: set[str]) -> bool:
    if user_is_root(user):
        return True
    m = get_user_membership(user, department)
    return bool(m and m.role_in_department in roles)


def ensure_root_user_exists() -> None:
    User = get_user_model()
    if not User.objects.filter(is_superuser=True).exists():
        # 留空：实际创建交给 createsuperuser
        return

