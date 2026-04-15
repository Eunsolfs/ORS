from django.contrib import admin

from orgs.admin_utils import ensure_dept_admin_model_perms, get_admin_departments_for_user

from .models import HandoverItem, HandoverSession


class HandoverItemInline(admin.TabularInline):
    model = HandoverItem
    extra = 0


@admin.register(HandoverSession)
class HandoverSessionAdmin(admin.ModelAdmin):
    list_display = ("department", "handover_date", "elective_count", "emergency_count", "rescue_count")
    list_filter = ("department", "handover_date")
    search_fields = ("department__name",)
    inlines = [HandoverItemInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        dept_ids = get_admin_departments_for_user(request.user)
        if not dept_ids:
            return qs.none()
        return qs.filter(department_id__in=dept_ids)

    def has_module_permission(self, request):
        ensure_dept_admin_model_perms(request.user, ["handover.handoversession", "handover.handoveritem"])
        return super().has_module_permission(request)


@admin.register(HandoverItem)
class HandoverItemAdmin(admin.ModelAdmin):
    list_display = ("session", "patient_name", "surgery_name", "reported_by", "reported_at", "status")
    list_filter = ("session__department", "session__handover_date", "status")
    search_fields = ("patient_name", "surgery_name", "special_handover")

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related("session", "reported_by")
        if request.user.is_superuser:
            return qs
        dept_ids = get_admin_departments_for_user(request.user)
        if not dept_ids:
            return qs.none()
        return qs.filter(session__department_id__in=dept_ids)
