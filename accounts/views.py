from django.contrib.auth import logout as django_logout
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect

from orgs.models import DepartmentMember


def root_redirect(request):
    if not request.user.is_authenticated:
        return redirect("login")

    if request.user.is_superuser:
        return redirect("/admin/")

    membership = (
        DepartmentMember.objects.select_related("department")
        .filter(user=request.user, is_active=True, department__is_active=True)
        .order_by("department__name")
        .first()
    )
    if not membership:
        return redirect("/admin/")  # 兜底：让管理员在后台处理

    dept_code = membership.department.code or str(membership.department.id)
    return redirect("m_home", dept_code=dept_code)


class LoginView(auth_views.LoginView):
    template_name = "auth/login.html"


class LogoutView(auth_views.LogoutView):
    next_page = "login"

    def get(self, request, *args, **kwargs):
        # 兼容旧版/外部直接 GET /logout/ 的退出方式：直接执行登出并跳转
        return self.post(request, *args, **kwargs)


def switch_user(request):
    """
    用于“已登录但无权限”的场景：允许用户一键退出并回到普通登录页。
    这里使用 GET，避免用户卡在 403 页面无法操作。
    """
    if request.user.is_authenticated:
        django_logout(request)
    return redirect("login")
