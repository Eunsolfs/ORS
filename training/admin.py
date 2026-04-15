from urllib.parse import urlencode

from django.contrib import admin, messages
from django.shortcuts import redirect, render
from django.urls import path, reverse

from orgs.admin_utils import ensure_dept_admin_model_perms, get_admin_departments_for_user

from .models import Course, MediaAsset


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("department", "title", "status", "published_at")
    list_filter = ("department", "status")
    search_fields = ("title", "content_html")

    def get_urls(self):
        urls = super().get_urls()
        extra = [
            path("grouped/", self.admin_site.admin_view(self.grouped_view), name="training_course_grouped"),
            path(
                "<int:course_id>/quick-delete/",
                self.admin_site.admin_view(self.quick_delete_view),
                name="training_course_quick_delete",
            ),
        ]
        return extra + urls

    def grouped_view(self, request):
        qs = self.get_queryset(request).select_related("department", "created_by").order_by("department__name", "-updated_at")

        by_dept = {}
        total = 0
        for c in qs:
            by_dept.setdefault(c.department, []).append(c)
            total += 1

        ctx = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "title": "课程列表（按科室分组）",
            "by_dept": by_dept,
            "total": total,
        }
        return render(request, "admin/training/course/grouped.html", ctx)

    def quick_delete_view(self, request, course_id: int):
        course = self.get_queryset(request).filter(pk=course_id).first()
        if not course:
            messages.error(request, "课程不存在或无权限")
            return redirect("..")

        if not self.has_delete_permission(request, obj=course):
            messages.error(request, "无删除权限")
            return redirect(reverse("admin:training_course_grouped"))

        if request.method != "POST":
            return redirect(reverse("admin:training_course_grouped"))

        title = course.title
        course.delete()
        messages.success(request, f"已删除课程：{title}")

        back = request.POST.get("next") or ""
        if back:
            return redirect(back)
        return redirect(reverse("admin:training_course_grouped"))

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        dept_ids = get_admin_departments_for_user(request.user)
        if not dept_ids:
            return qs.none()
        return qs.filter(department_id__in=dept_ids)

    def has_module_permission(self, request):
        ensure_dept_admin_model_perms(request.user, ["training.course", "training.mediaasset"])
        return super().has_module_permission(request)


@admin.register(MediaAsset)
class MediaAssetAdmin(admin.ModelAdmin):
    list_display = ("department", "file_name", "storage_backend", "uploaded_by", "created_at")
    list_filter = ("department", "storage_backend")
    search_fields = ("file_name", "file_url", "object_key")

    def get_urls(self):
        urls = super().get_urls()
        extra = [
            path("grouped/", self.admin_site.admin_view(self.grouped_view), name="training_mediaasset_grouped"),
            path(
                "<int:asset_id>/quick-delete/",
                self.admin_site.admin_view(self.quick_delete_view),
                name="training_mediaasset_quick_delete",
            ),
        ]
        return extra + urls

    def grouped_view(self, request):
        qs = self.get_queryset(request).select_related("department", "uploaded_by").order_by("department__name", "-created_at")

        by_dept = {}
        total = 0
        for a in qs:
            by_dept.setdefault(a.department, []).append(a)
            total += 1

        ctx = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "title": "资源列表（按科室分组）",
            "by_dept": by_dept,
            "total": total,
        }
        return render(request, "admin/training/mediaasset/grouped.html", ctx)

    def quick_delete_view(self, request, asset_id: int):
        asset = self.get_queryset(request).filter(pk=asset_id).first()
        if not asset:
            messages.error(request, "资源不存在或无权限")
            return redirect("..")

        if not self.has_delete_permission(request, obj=asset):
            messages.error(request, "无删除权限")
            return redirect(reverse("admin:training_mediaasset_grouped"))

        if request.method != "POST":
            # 不提供提示页，直接返回分组列表
            return redirect(reverse("admin:training_mediaasset_grouped"))

        asset.delete()
        messages.success(request, f"已删除：{asset.file_name}")

        back = request.POST.get("next") or ""
        if back:
            return redirect(back)
        return redirect(reverse("admin:training_mediaasset_grouped"))

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        dept_ids = get_admin_departments_for_user(request.user)
        if not dept_ids:
            return qs.none()
        return qs.filter(department_id__in=dept_ids)
