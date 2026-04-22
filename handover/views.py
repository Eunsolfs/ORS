from __future__ import annotations

import io
import calendar
from datetime import date as date_type
from datetime import time as time_type
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.http import HttpResponse
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseNotAllowed
from django.shortcuts import redirect, render
from django.utils import timezone
from django.urls import reverse

from orgs.decorators import require_department_roles
from orgs.models import DepartmentMember
from orgs.services import get_active_department_by_code

from .forms import (
    HandoverItemMobileForm,
    HandoverSessionChecksForm,
    HandoverSessionSummaryForm,
)
from .models import HandoverItem, HandoverSession

import qrcode


def _parse_date_yyyy_mm_dd(s: str) -> date_type:
    try:
        y, m, d = s.split("-")
        return date_type(int(y), int(m), int(d))
    except Exception as e:
        raise Http404("日期格式错误") from e


def _can_manage_all(user, department) -> bool:
    membership = DepartmentMember.objects.filter(user=user, department=department, is_active=True).first()
    return bool(user.is_superuser or (membership and membership.role_in_department == DepartmentMember.Role.ADMIN))


def _business_handover_date(department, dt=None) -> date_type:
    current = timezone.localtime(dt) if dt else timezone.localtime()
    cutoff_time = getattr(department, "handover_cutoff_time", None) or time_type(hour=8, minute=10)
    if current.time() < cutoff_time:
        return current.date() - timedelta(days=1)
    return current.date()


def _ensure_member_can_edit_target_date(request, department, target_date: date_type):
    if _can_manage_all(request.user, department):
        return
    if target_date != _business_handover_date(department):
        raise PermissionDenied("普通成员仅可编辑当前值班日交班，历史交班仅可查看")


def _get_existing_session(department, target_date: date_type):
    return HandoverSession.objects.filter(department=department, handover_date=target_date).first()


def _build_unsaved_session(department, target_date: date_type, user):
    return HandoverSession(
        department=department,
        handover_date=target_date,
        created_by=user if user.is_authenticated else None,
    )


def _get_or_build_session(department, target_date: date_type, user):
    session = _get_existing_session(department, target_date)
    if session:
        return session, False
    return _build_unsaved_session(department, target_date, user), True


def _get_or_create_session(department, target_date: date_type, user):
    return HandoverSession.objects.get_or_create(
        department=department,
        handover_date=target_date,
        defaults={"created_by": user if user.is_authenticated else None},
    )


def _ensure_session_mutable(session: HandoverSession):
    if session.locked_at:
        raise PermissionDenied("当前交班已锁定，无法修改")


def _ensure_item_mutable(item: HandoverItem):
    if item.status and item.status != "active":
        raise PermissionDenied("当前条目状态不允许修改")


def _ensure_item_edit_permission(request, department, item: HandoverItem):
    if _can_manage_all(request.user, department):
        return
    if item.reported_by_id != request.user.id:
        raise PermissionDenied("无权限修改他人填报条目")


@login_required
@require_department_roles(DepartmentMember.Role.ADMIN, DepartmentMember.Role.MEMBER)
def m_home(request, dept_code: str):
    department = get_active_department_by_code(dept_code)
    if not department:
        raise Http404("科室不存在")
    today = _business_handover_date(department)
    membership = DepartmentMember.objects.filter(user=request.user, department=department, is_active=True).first()
    role_in_department = membership.role_in_department if membership else DepartmentMember.Role.MEMBER

    session, _ = _get_or_build_session(department=department, target_date=today, user=request.user)
    all_items = (session.items if session.pk else HandoverItem.objects.none()).order_by("id")
    my_items = all_items.filter(reported_by=request.user)

    can_manage_all = bool(request.user.is_superuser or role_in_department == DepartmentMember.Role.ADMIN)
    return render(
        request,
        "m/home.html",
        {
            "department": department,
            "dept_code": dept_code,
            "today": today,
            "session": session,
            "my_items": my_items,
            "today_items_count": all_items.count(),
            "has_submitted_today": my_items.exists(),
            "has_department_submitted_today": all_items.exists(),
            "role_in_department": role_in_department,
            "can_manage_all": can_manage_all,
        },
    )


@login_required
@require_department_roles(DepartmentMember.Role.ADMIN, DepartmentMember.Role.MEMBER)
def handover_today(request, dept_code: str):
    department = request.department  # type: ignore[attr-defined]
    today = _business_handover_date(department)
    can_manage_all = _can_manage_all(request.user, department)

    session, created = _get_or_build_session(department=department, target_date=today, user=request.user)

    items = (session.items if session.pk else HandoverItem.objects.none()).order_by("id")
    return render(
        request,
        "m/handover_cards.html",
        {
            "department": department,
            "dept_code": dept_code,
            "session": session,
            "items": items,
            "created": created,
            "can_manage_all": can_manage_all,
            "is_today": True,
        },
    )


@login_required
@require_department_roles(DepartmentMember.Role.ADMIN, DepartmentMember.Role.MEMBER)
def handover_by_date(request, dept_code: str, date: str):
    department = request.department  # type: ignore[attr-defined]
    target_date = _parse_date_yyyy_mm_dd(date)
    can_manage_all = _can_manage_all(request.user, department)

    session, _ = _get_or_build_session(department=department, target_date=target_date, user=request.user)
    items = (session.items if session.pk else HandoverItem.objects.none()).order_by("id")
    return render(
        request,
        "m/handover_cards.html",
        {
            "department": department,
            "dept_code": dept_code,
            "session": session,
            "items": items,
            "created": False,
            "target_date": target_date,
            "can_manage_all": can_manage_all,
            "is_today": False,
        },
    )


@login_required
@require_department_roles(DepartmentMember.Role.ADMIN, DepartmentMember.Role.MEMBER)
def handover_history(request, dept_code: str):
    department = request.department  # type: ignore[attr-defined]
    can_manage_all = _can_manage_all(request.user, department)
    business_today = _business_handover_date(department)
    selected_date_raw = (request.GET.get("date") or "").strip()

    try:
        selected_year = int((request.GET.get("year") or business_today.year))
    except (TypeError, ValueError):
        selected_year = business_today.year
    try:
        selected_month = int((request.GET.get("month") or business_today.month))
    except (TypeError, ValueError):
        selected_month = business_today.month

    selected_month = min(max(selected_month, 1), 12)
    all_years = sorted(
        HandoverSession.objects.filter(department=department)
        .dates("handover_date", "year", order="DESC"),
        reverse=True,
    )
    year_options = [d.year for d in all_years] or [business_today.year]
    if selected_year not in year_options:
        selected_year = year_options[0]

    day_list = []
    no_data_message = ""
    if selected_date_raw:
        selected_day = _parse_date_yyyy_mm_dd(selected_date_raw)
        session = _get_existing_session(department=department, target_date=selected_day)
        if session:
            day_list.append(
                {
                    "handover_date": selected_day,
                    "session": session,
                    "items_count": session.items.count(),
                }
            )
        else:
            no_data_message = f"{selected_day} 暂无交班数据。"
    else:
        month_start = date_type(selected_year, selected_month, 1)
        _, month_days = calendar.monthrange(selected_year, selected_month)
        month_end = date_type(selected_year, selected_month, month_days)
        sessions = (
            HandoverSession.objects.filter(
                department=department, handover_date__gte=month_start, handover_date__lte=month_end
            )
            .prefetch_related("items")
            .order_by("-handover_date")
        )
        for curr_session in sessions:
            day_list.append(
                {
                    "handover_date": curr_session.handover_date,
                    "session": curr_session,
                    "items_count": curr_session.items.count(),
                }
            )

    return render(
        request,
        "m/handover_history.html",
        {
            "department": department,
            "dept_code": dept_code,
            "rows": day_list,
            "year_options": year_options,
            "month_options": list(range(1, 13)),
            "selected_year": selected_year,
            "selected_month": selected_month,
            "selected_date": selected_date_raw,
            "can_manage_all": can_manage_all,
            "no_data_message": no_data_message,
        },
    )


@login_required
@require_department_roles(DepartmentMember.Role.ADMIN, DepartmentMember.Role.MEMBER)
def handover_fill_today(request, dept_code: str):
    department = request.department  # type: ignore[attr-defined]
    today = _business_handover_date(department)
    session, _ = _get_or_build_session(department=department, target_date=today, user=request.user)
    return _handover_fill_overview(request, dept_code=dept_code, session=session, target_date=today)


@login_required
@require_department_roles(DepartmentMember.Role.ADMIN, DepartmentMember.Role.MEMBER)
def handover_fill_by_date(request, dept_code: str, date: str):
    department = request.department  # type: ignore[attr-defined]
    target_date = _parse_date_yyyy_mm_dd(date)
    _ensure_member_can_edit_target_date(request, department, target_date)
    session, _ = _get_or_build_session(department=department, target_date=target_date, user=request.user)
    return _handover_fill_overview(request, dept_code=dept_code, session=session, target_date=target_date)


def _session_fill_statuses(session: HandoverSession):
    top_filled = any(
        [
            session.elective_count is not None,
            session.emergency_count is not None,
            session.rescue_count is not None,
            bool((session.notes or "").strip()),
        ]
    )
    checks_filled = any(
        [
            bool((session.specimen_handover_status or "").strip()),
            bool((session.specimen_handover_note or "").strip()),
            bool((session.laminar_flow_running_status or "").strip()),
            bool((session.laminar_flow_running_note or "").strip()),
            bool((session.bio_monitoring_status or "").strip()),
            bool((session.bio_monitoring_note or "").strip()),
            bool((session.crash_cart_status or "").strip()),
            bool((session.crash_cart_note or "").strip()),
            bool((session.fire_safety_status or "").strip()),
            bool((session.fire_safety_note or "").strip()),
            bool((session.key_management_status or "").strip()),
            bool((session.key_management_note or "").strip()),
            bool((session.certs_in_place_status or "").strip()),
            bool((session.certs_in_place_note or "").strip()),
            bool((session.other_incidents or "").strip()),
        ]
    )
    items_count = session.items.count() if session.pk else 0
    return {
        "top_filled": top_filled,
        "checks_filled": checks_filled,
        "items_filled": items_count > 0,
        "items_count": items_count,
    }


def _redirect_fill_overview(dept_code: str, target_date: date_type):
    department = get_active_department_by_code(dept_code)
    today = _business_handover_date(department) if department else timezone.localdate()
    if target_date == today:
        return redirect("handover_fill_today", dept_code=dept_code)
    return redirect("handover_fill_by_date", dept_code=dept_code, date=target_date)


def _handover_fill_overview(request, dept_code: str, session: HandoverSession, target_date: date_type):
    statuses = _session_fill_statuses(session)
    is_today = target_date == _business_handover_date(session.department)
    return render(
        request,
        "m/handover_fill_overview.html",
        {
            "dept_code": dept_code,
            "department": session.department,
            "session": session,
            "target_date": target_date,
            "is_today": is_today,
            **statuses,
        },
    )


def _redirect_fill_items(dept_code: str, target_date: date_type):
    department = get_active_department_by_code(dept_code)
    today = _business_handover_date(department) if department else timezone.localdate()
    if target_date == today:
        return redirect("handover_fill_section_today", dept_code=dept_code, section="items")
    return redirect("handover_fill_section_by_date", dept_code=dept_code, date=target_date, section="items")


def _get_session_item_or_404(session: HandoverSession, item_id: int) -> HandoverItem:
    if not session.pk:
        raise Http404("当前交班不存在")
    item = session.items.filter(id=item_id).first()
    if not item:
        raise Http404("手术条目不存在")
    return item


def _handover_fill_items_list(request, dept_code: str, session: HandoverSession, target_date: date_type):
    items = (session.items if session.pk else HandoverItem.objects.none()).order_by("-id")
    return render(
        request,
        "m/handover_fill_items.html",
        {
            "dept_code": dept_code,
            "department": session.department,
            "session": session,
            "target_date": target_date,
            "is_today": target_date == _business_handover_date(session.department),
            "items": items,
        },
    )


def _handover_fill_item_form(
    request, dept_code: str, session: HandoverSession, target_date: date_type, item: HandoverItem | None = None
):
    department = request.department  # type: ignore[attr-defined]
    if request.method == "POST":
        if not session.pk:
            session, _ = _get_or_create_session(department=department, target_date=target_date, user=request.user)
        _ensure_session_mutable(session)
        form = HandoverItemMobileForm(request.POST, instance=item)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.session = session
            if not obj.reported_by_id:
                obj.reported_by = request.user
                obj.reported_at = timezone.now()
            obj.updated_by = request.user
            obj.save()
            return _redirect_fill_items(dept_code=dept_code, target_date=target_date)
    else:
        form = HandoverItemMobileForm(instance=item)

    return render(
        request,
        "m/handover_fill_item_form.html",
        {
            "dept_code": dept_code,
            "department": session.department,
            "session": session,
            "target_date": target_date,
            "is_today": target_date == _business_handover_date(session.department),
            "form": form,
            "item": item,
        },
    )


@login_required
@require_department_roles(DepartmentMember.Role.ADMIN, DepartmentMember.Role.MEMBER)
def handover_fill_section_today(request, dept_code: str, section: str):
    department = request.department  # type: ignore[attr-defined]
    today = _business_handover_date(department)
    session, _ = _get_or_build_session(department=department, target_date=today, user=request.user)
    return _handover_fill_section(request, dept_code=dept_code, session=session, target_date=today, section=section)


@login_required
@require_department_roles(DepartmentMember.Role.ADMIN, DepartmentMember.Role.MEMBER)
def handover_fill_section_by_date(request, dept_code: str, date: str, section: str):
    department = request.department  # type: ignore[attr-defined]
    target_date = _parse_date_yyyy_mm_dd(date)
    _ensure_member_can_edit_target_date(request, department, target_date)
    session, _ = _get_or_build_session(department=department, target_date=target_date, user=request.user)
    return _handover_fill_section(
        request, dept_code=dept_code, session=session, target_date=target_date, section=section
    )


def _handover_fill_section(
    request, dept_code: str, session: HandoverSession, target_date: date_type, section: str
):
    department = request.department  # type: ignore[attr-defined]
    if section == "top":
        if request.method == "POST":
            if not session.pk:
                session, _ = _get_or_create_session(department=department, target_date=target_date, user=request.user)
            _ensure_session_mutable(session)
            form = HandoverSessionSummaryForm(request.POST, instance=session)
            if form.is_valid():
                form.save()
                return _redirect_fill_overview(dept_code=dept_code, target_date=target_date)
        else:
            form = HandoverSessionSummaryForm(instance=session)
        return render(
            request,
            "m/handover_fill_top.html",
            {
                "dept_code": dept_code,
                "department": session.department,
                "session": session,
                "target_date": target_date,
                "is_today": target_date == _business_handover_date(session.department),
                "form": form,
            },
        )

    if section == "checks":
        if request.method == "POST":
            if not session.pk:
                session, _ = _get_or_create_session(department=department, target_date=target_date, user=request.user)
            _ensure_session_mutable(session)
            form = HandoverSessionChecksForm(request.POST, instance=session)
            if form.is_valid():
                form.save()
                return _redirect_fill_overview(dept_code=dept_code, target_date=target_date)
        else:
            form = HandoverSessionChecksForm(instance=session)
        return render(
            request,
            "m/handover_fill_checks.html",
            {
                "dept_code": dept_code,
                "department": session.department,
                "session": session,
                "target_date": target_date,
                "is_today": target_date == _business_handover_date(session.department),
                "form": form,
            },
        )

    if section == "items":
        return _handover_fill_items_list(request, dept_code=dept_code, session=session, target_date=target_date)

    raise Http404("未知填报项")


@login_required
@require_department_roles(DepartmentMember.Role.ADMIN, DepartmentMember.Role.MEMBER)
def handover_fill_item_create_today(request, dept_code: str):
    department = request.department  # type: ignore[attr-defined]
    today = _business_handover_date(department)
    session, _ = _get_or_build_session(department=department, target_date=today, user=request.user)
    return _handover_fill_item_form(request, dept_code=dept_code, session=session, target_date=today)


@login_required
@require_department_roles(DepartmentMember.Role.ADMIN, DepartmentMember.Role.MEMBER)
def handover_fill_item_create_by_date(request, dept_code: str, date: str):
    department = request.department  # type: ignore[attr-defined]
    target_date = _parse_date_yyyy_mm_dd(date)
    _ensure_member_can_edit_target_date(request, department, target_date)
    session, _ = _get_or_build_session(department=department, target_date=target_date, user=request.user)
    return _handover_fill_item_form(request, dept_code=dept_code, session=session, target_date=target_date)


@login_required
@require_department_roles(DepartmentMember.Role.ADMIN, DepartmentMember.Role.MEMBER)
def handover_fill_item_edit_today(request, dept_code: str, item_id: int):
    department = request.department  # type: ignore[attr-defined]
    today = _business_handover_date(department)
    session = _get_existing_session(department=department, target_date=today)
    if not session:
        raise Http404("当前交班不存在")
    item = _get_session_item_or_404(session=session, item_id=item_id)
    _ensure_item_edit_permission(request, department, item)
    _ensure_item_mutable(item)
    return _handover_fill_item_form(request, dept_code=dept_code, session=session, target_date=today, item=item)


@login_required
@require_department_roles(DepartmentMember.Role.ADMIN, DepartmentMember.Role.MEMBER)
def handover_fill_item_edit_by_date(request, dept_code: str, date: str, item_id: int):
    department = request.department  # type: ignore[attr-defined]
    target_date = _parse_date_yyyy_mm_dd(date)
    _ensure_member_can_edit_target_date(request, department, target_date)
    session = _get_existing_session(department=department, target_date=target_date)
    if not session:
        raise Http404("当前交班不存在")
    item = _get_session_item_or_404(session=session, item_id=item_id)
    _ensure_item_edit_permission(request, department, item)
    _ensure_item_mutable(item)
    return _handover_fill_item_form(
        request, dept_code=dept_code, session=session, target_date=target_date, item=item
    )


@login_required
@require_department_roles(DepartmentMember.Role.ADMIN, DepartmentMember.Role.MEMBER)
def handover_fill_item_delete_today(request, dept_code: str, item_id: int):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    department = request.department  # type: ignore[attr-defined]
    today = _business_handover_date(department)
    session = _get_existing_session(department=department, target_date=today)
    if not session:
        raise Http404("当前交班不存在")
    _ensure_session_mutable(session)
    item = _get_session_item_or_404(session=session, item_id=item_id)
    _ensure_item_edit_permission(request, department, item)
    _ensure_item_mutable(item)
    item.delete()
    return _redirect_fill_items(dept_code=dept_code, target_date=today)


@login_required
@require_department_roles(DepartmentMember.Role.ADMIN, DepartmentMember.Role.MEMBER)
def handover_fill_item_delete_by_date(request, dept_code: str, date: str, item_id: int):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    department = request.department  # type: ignore[attr-defined]
    target_date = _parse_date_yyyy_mm_dd(date)
    _ensure_member_can_edit_target_date(request, department, target_date)
    session = _get_existing_session(department=department, target_date=target_date)
    if not session:
        raise Http404("当前交班不存在")
    _ensure_session_mutable(session)
    item = _get_session_item_or_404(session=session, item_id=item_id)
    _ensure_item_edit_permission(request, department, item)
    _ensure_item_mutable(item)
    item.delete()
    return _redirect_fill_items(dept_code=dept_code, target_date=target_date)


@login_required
@require_department_roles(DepartmentMember.Role.ADMIN, DepartmentMember.Role.MEMBER)
def handover_today_qr(request, dept_code: str):
    url = request.build_absolute_uri(reverse("handover_today", kwargs={"dept_code": dept_code}))
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return HttpResponse(buf.getvalue(), content_type="image/png")
