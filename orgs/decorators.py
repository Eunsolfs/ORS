from __future__ import annotations

from functools import wraps

from django.http import Http404, HttpResponseForbidden

from .services import get_active_department_by_code, user_has_department_role


def require_department_roles(*allowed_roles: str):
    allowed = set(allowed_roles)

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, dept_code: str, *args, **kwargs):
            department = get_active_department_by_code(dept_code)
            if not department:
                raise Http404("科室不存在")

            if not user_has_department_role(request.user, department, allowed):
                return HttpResponseForbidden("无权限")

            request.department = department  # type: ignore[attr-defined]
            return view_func(request, dept_code=dept_code, *args, **kwargs)

        return _wrapped

    return decorator

