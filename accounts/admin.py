from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import UserCreationForm
from django.db import transaction

from orgs.admin_utils import ensure_dept_admin_model_perms, get_admin_departments_for_user
from orgs.models import Department
from orgs.models import DepartmentMember

from .models import User


class UserCreationWithDeptRoleForm(UserCreationForm):
    department = forms.ModelChoiceField(
        label="科室",
        queryset=Department.objects.none(),
        required=False,
        help_text="可选：创建用户的同时指定所属科室。",
    )
    role_in_department = forms.ChoiceField(
        label="科室角色",
        choices=DepartmentMember.Role.choices,
        required=False,
        help_text="可选：与科室一起设置。",
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "name", "phone", "email")

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        req = self.request
        if req and getattr(req, "user", None) and req.user.is_authenticated and not req.user.is_superuser:
            dept_ids = get_admin_departments_for_user(req.user)
            self.fields["department"].queryset = Department.objects.filter(id__in=dept_ids, is_active=True)
        else:
            self.fields["department"].queryset = Department.objects.filter(is_active=True)

    def clean(self):
        cleaned = super().clean()
        dept = cleaned.get("department")
        role = cleaned.get("role_in_department")
        if (dept and not role) or (role and not dept):
            raise forms.ValidationError("科室与科室角色需要同时填写，或同时留空。")
        return cleaned


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("基本信息", {"fields": ("name", "phone", "email")}),
        ("权限", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("重要时间", {"fields": ("last_login_at", "last_login", "date_joined")}),
    )
    list_display = ("username", "name", "phone", "is_active", "is_staff", "is_superuser")
    search_fields = ("username", "name", "phone", "email")
    ordering = ("username",)
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "name",
                    "phone",
                    "email",
                    "password1",
                    "password2",
                    "department",
                    "role_in_department",
                    "is_staff",
                    "is_superuser",
                ),
            },
        ),
    )

    add_form = UserCreationWithDeptRoleForm

    def get_form(self, request, obj=None, change=False, **kwargs):
        form = super().get_form(request, obj=obj, change=change, **kwargs)
        # 仅 add_form 需要 request 来过滤科室下拉框
        if obj is None and issubclass(form, UserCreationWithDeptRoleForm):
            class _RequestBoundForm(form):  # type: ignore[misc]
                def __init__(self2, *args, **kw):
                    kw["request"] = request
                    super().__init__(*args, **kw)

            return _RequestBoundForm
        return form

    def get_fieldsets(self, request, obj=None):
        """
        科室管理员仅允许管理本科室用户的基础信息，不允许操作全局权限字段：
        - is_superuser / groups / user_permissions
        """
        fieldsets = super().get_fieldsets(request, obj=obj)
        if request.user.is_superuser:
            return fieldsets

        filtered = []
        for name, opts in fieldsets:
            fields = list(opts.get("fields") or [])
            fields = [f for f in fields if f not in ("is_superuser", "groups", "user_permissions")]
            # 如果某个 fieldset 被清空，则跳过
            if not fields:
                continue
            new_opts = dict(opts)
            new_opts["fields"] = tuple(fields)
            filtered.append((name, new_opts))
        return tuple(filtered)

    def get_add_fieldsets(self, request, obj=None):
        fieldsets = super().get_add_fieldsets(request, obj=obj)
        if request.user.is_superuser:
            return fieldsets

        filtered = []
        for name, opts in fieldsets:
            fields = list(opts.get("fields") or [])
            fields = [f for f in fields if f not in ("is_superuser", "groups", "user_permissions")]
            if not fields:
                continue
            new_opts = dict(opts)
            new_opts["fields"] = tuple(fields)
            filtered.append((name, new_opts))
        return tuple(filtered)

    def save_model(self, request, obj, form, change):
        # 最后一层兜底：非全局系统管理员绝对不能创建/提升任何 superuser
        if not request.user.is_superuser:
            obj.is_superuser = False
        with transaction.atomic():
            super().save_model(request, obj, form, change)
            # 新建用户时：如果填写了科室/角色，则同步创建 DepartmentMember
            if not change and hasattr(form, "cleaned_data"):
                dept = form.cleaned_data.get("department")
                role = form.cleaned_data.get("role_in_department")
                if dept and role:
                    DepartmentMember.objects.update_or_create(
                        department=dept,
                        user=obj,
                        defaults={
                            "role_in_department": role,
                            "is_active": True,
                            "created_by": request.user if request.user.is_authenticated else None,
                        },
                    )
        return None

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs

        dept_ids = get_admin_departments_for_user(request.user)
        if not dept_ids:
            return qs.none()
        user_ids = DepartmentMember.objects.filter(department_id__in=dept_ids, is_active=True).values_list("user_id", flat=True)
        return qs.filter(id__in=user_ids).distinct()

    def has_view_permission(self, request, obj=None):
        ensure_dept_admin_model_perms(request.user, ["accounts.user"])
        return super().has_view_permission(request, obj=obj)

    def has_module_permission(self, request):
        ensure_dept_admin_model_perms(request.user, ["accounts.user"])
        return super().has_module_permission(request)
