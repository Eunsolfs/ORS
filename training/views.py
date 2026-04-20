import io

import qrcode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import Http404
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from orgs.decorators import require_department_roles
from orgs.models import DepartmentMember
from orgs.services import get_active_department_by_code

from systemcfg.services import save_uploaded_bytes_with_meta

from .forms import CourseForm
from .models import Course, MediaAsset


def _public_course_session_key(course: Course) -> str:
    return f"course_public_ok:{course.id}"


def _ensure_course_visible_for_member(request, department, course: Course):
    if course.status == Course.Status.PUBLISHED:
        return
    membership = DepartmentMember.objects.filter(user=request.user, department=department, is_active=True).first()
    is_dept_admin = bool(membership and membership.role_in_department == DepartmentMember.Role.ADMIN)
    if not request.user.is_superuser and not is_dept_admin:
        raise Http404("课程不可访问")


def _ensure_course_visible_for_public(course: Course):
    if course.status != Course.Status.PUBLISHED or course.visibility != Course.Visibility.PUBLIC:
        raise Http404("课程不可访问")


def _find_courses_referencing_asset(department, asset: MediaAsset):
    return Course.objects.filter(department=department).filter(
        Q(content_html__icontains=asset.file_url)
        | Q(cover_image_path__icontains=asset.file_url)
        | Q(video_embed_html__icontains=asset.file_url)
        | Q(video_url__icontains=asset.file_url)
    )


@login_required
@require_department_roles(DepartmentMember.Role.ADMIN, DepartmentMember.Role.MEMBER)
def course_list(request, dept_code: str):
    department = get_active_department_by_code(dept_code)
    if not department:
        raise Http404("科室不存在")

    courses = Course.objects.filter(department=department, status=Course.Status.PUBLISHED).order_by("-published_at", "-id")
    membership = DepartmentMember.objects.filter(user=request.user, department=department, is_active=True).first()
    can_manage = bool(request.user.is_superuser or (membership and membership.role_in_department == DepartmentMember.Role.ADMIN))
    return render(
        request,
        "m/course_list.html",
        {"department": department, "dept_code": dept_code, "courses": courses, "can_manage_courses": can_manage},
    )


@login_required
@require_department_roles(DepartmentMember.Role.ADMIN, DepartmentMember.Role.MEMBER)
def course_detail(request, dept_code: str, course_id: int):
    department = request.department  # type: ignore[attr-defined]
    course = get_object_or_404(Course, pk=course_id, department=department)
    _ensure_course_visible_for_member(request, department, course)
    return render(
        request,
        "m/course_detail.html",
        {"department": department, "dept_code": dept_code, "course": course, "is_public_view": False},
    )


def course_public_detail(request, dept_code: str, course_id: int):
    department = get_active_department_by_code(dept_code)
    if not department:
        raise Http404("科室不存在")
    course = get_object_or_404(Course, pk=course_id, department=department)
    _ensure_course_visible_for_public(course)

    needs_password = course.has_public_access_password
    has_verified = request.session.get(_public_course_session_key(course), False)

    if needs_password and not has_verified:
        if request.method == "POST":
            entered_password = (request.POST.get("access_password") or "").strip()
            if course.check_public_access_password(entered_password):
                request.session[_public_course_session_key(course)] = True
                return redirect("course_public_detail", dept_code=dept_code, course_id=course.id)
            messages.error(request, "访问密码错误，请重试。")
        return render(
            request,
            "m/course_public_access.html",
            {"department": department, "dept_code": dept_code, "course": course},
        )

    return render(
        request,
        "m/course_detail.html",
        {"department": department, "dept_code": dept_code, "course": course, "is_public_view": True},
    )


@login_required
@require_department_roles(DepartmentMember.Role.ADMIN, DepartmentMember.Role.MEMBER)
def course_qr(request, dept_code: str, course_id: int):
    department = get_active_department_by_code(dept_code)
    if not department:
        raise Http404("科室不存在")
    course = get_object_or_404(Course, pk=course_id, department=department)
    if course.visibility == Course.Visibility.PUBLIC:
        url = request.build_absolute_uri(reverse("course_public_detail", kwargs={"dept_code": dept_code, "course_id": course_id}))
    else:
        url = request.build_absolute_uri(reverse("course_detail", kwargs={"dept_code": dept_code, "course_id": course_id}))
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return HttpResponse(buf.getvalue(), content_type="image/png")


@login_required
@require_department_roles(DepartmentMember.Role.ADMIN)
def course_manage_list(request, dept_code: str):
    department = request.department  # type: ignore[attr-defined]
    courses = Course.objects.filter(department=department).order_by("-updated_at")
    courses_draft = [c for c in courses if c.status == Course.Status.DRAFT]
    courses_published = [c for c in courses if c.status == Course.Status.PUBLISHED]
    courses_inactive = [c for c in courses if c.status == Course.Status.INACTIVE]
    return render(
        request,
        "m/course_manage_list.html",
        {
            "department": department,
            "dept_code": dept_code,
            "courses": courses,
            "courses_draft": courses_draft,
            "courses_published": courses_published,
            "courses_inactive": courses_inactive,
        },
    )


@login_required
@require_department_roles(DepartmentMember.Role.ADMIN)
def course_create(request, dept_code: str):
    department = request.department  # type: ignore[attr-defined]
    if request.method == "POST":
        form = CourseForm(request.POST)
        if form.is_valid():
            course: Course = form.save(commit=False)
            course.department = department
            course.created_by = request.user
            if course.status == Course.Status.PUBLISHED and not course.published_at:
                course.published_at = timezone.now()
            if course.status != Course.Status.PUBLISHED:
                course.published_at = None
            course.save()
            return redirect("course_manage_list", dept_code=dept_code)
    else:
        form = CourseForm(initial={"status": Course.Status.PUBLISHED, "visibility": Course.Visibility.DEPARTMENT})
    return render(
        request,
        "m/course_form.html",
        {"department": department, "dept_code": dept_code, "form": form, "mode": "create"},
    )


@login_required
@require_department_roles(DepartmentMember.Role.ADMIN)
def course_edit(request, dept_code: str, course_id: int):
    department = request.department  # type: ignore[attr-defined]
    course = get_object_or_404(Course, pk=course_id, department=department)
    if request.method == "POST":
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            course = form.save(commit=False)
            if course.status == Course.Status.PUBLISHED and not course.published_at:
                course.published_at = timezone.now()
            if course.status != Course.Status.PUBLISHED:
                course.published_at = None
            course.save()
            return redirect("course_manage_list", dept_code=dept_code)
    else:
        form = CourseForm(instance=course)
    return render(
        request,
        "m/course_form.html",
        {"department": department, "dept_code": dept_code, "form": form, "mode": "edit", "course": course},
    )


@login_required
@require_department_roles(DepartmentMember.Role.ADMIN)
def course_delete(request, dept_code: str, course_id: int):
    department = request.department  # type: ignore[attr-defined]
    course = get_object_or_404(Course, pk=course_id, department=department)
    if request.method == "POST":
        course.delete()
        return redirect("course_manage_list", dept_code=dept_code)
    return render(
        request,
        "m/course_delete_confirm.html",
        {"department": department, "dept_code": dept_code, "course": course},
    )


@login_required
@require_department_roles(DepartmentMember.Role.ADMIN)
def course_upload_image(request, dept_code: str):
    department = request.department  # type: ignore[attr-defined]
    if request.method != "POST":
        return JsonResponse({"error": "method_not_allowed"}, status=405)

    f = request.FILES.get("file")
    if not f:
        return JsonResponse({"error": "missing_file"}, status=400)

    meta = save_uploaded_bytes_with_meta(f.read(), f.name)
    asset = MediaAsset.objects.create(
        department=department,
        uploaded_by=request.user,
        file_name=f.name,
        file_url=meta["url"],
        storage_backend=meta.get("backend", "local"),
        object_key=meta.get("object_key", ""),
    )
    return JsonResponse(
        {
            "location": asset.file_url,
            "asset": {
                "id": asset.id,
                "file_name": asset.file_name,
                "file_url": asset.file_url,
                "created_at": asset.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            },
        }
    )


@login_required
@require_department_roles(DepartmentMember.Role.ADMIN)
def media_library_page(request, dept_code: str):
    department = request.department  # type: ignore[attr-defined]
    assets = MediaAsset.objects.filter(department=department).order_by("-created_at")[:200]
    return render(
        request,
        "m/media_library.html",
        {"department": department, "dept_code": dept_code, "assets": assets},
    )


@login_required
@require_department_roles(DepartmentMember.Role.ADMIN)
def media_assets_api(request, dept_code: str):
    department = request.department  # type: ignore[attr-defined]
    q = (request.GET.get("q") or "").strip()
    qs = MediaAsset.objects.filter(department=department)
    if q:
        qs = qs.filter(file_name__icontains=q)
    assets = list(qs.order_by("-created_at")[:200])
    return JsonResponse(
        {
            "assets": [
                {
                    "id": a.id,
                    "file_name": a.file_name,
                    "file_url": a.file_url,
                    "storage_backend": a.storage_backend,
                    "created_at": a.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                }
                for a in assets
            ]
        }
    )


@login_required
@require_department_roles(DepartmentMember.Role.ADMIN)
def media_asset_delete(request, dept_code: str, asset_id: int):
    department = request.department  # type: ignore[attr-defined]
    asset = get_object_or_404(MediaAsset, pk=asset_id, department=department)
    if request.method != "POST":
        return JsonResponse({"error": "method_not_allowed"}, status=405)

    referencing_courses = list(_find_courses_referencing_asset(department, asset).values_list("title", flat=True)[:20])
    if referencing_courses:
        return JsonResponse(
            {
                "error": "asset_in_use",
                "message": "该图片仍被教程引用，无法删除。",
                "courses": referencing_courses,
            },
            status=409,
        )

    asset.delete()
    return JsonResponse({"ok": True})
