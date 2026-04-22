from django.contrib import admin

from orgs.admin_utils import ensure_dept_admin_model_perms, get_admin_departments_for_user

from .models import Department, DepartmentMember


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "handover_cutoff_time", "is_active")
    search_fields = ("name", "code")
    list_filter = ("is_active",)
    delete_confirmation_template = "admin/orgs/department/delete_confirmation.html"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        dept_ids = get_admin_departments_for_user(request.user)
        return qs.filter(id__in=dept_ids)

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(DepartmentMember)
class DepartmentMemberAdmin(admin.ModelAdmin):
    list_display = ("department", "user", "role_in_department", "is_active")
    search_fields = ("department__name", "user__username", "user__name")
    list_filter = ("role_in_department", "is_active", "department")

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related("department", "user")
        if request.user.is_superuser:
            return qs
        dept_ids = get_admin_departments_for_user(request.user)
        if not dept_ids:
            return qs.none()
        return qs.filter(department_id__in=dept_ids)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not request.user.is_superuser:
            dept_ids = get_admin_departments_for_user(request.user)
            if db_field.name == "department":
                kwargs["queryset"] = Department.objects.filter(id__in=dept_ids)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def has_module_permission(self, request):
        ensure_dept_admin_model_perms(request.user, ["orgs.departmentmember"])
        return super().has_module_permission(request)
