from django.conf import settings
from django.contrib.auth import logout
from django.utils import timezone


class SessionAbsoluteTimeoutMiddleware:
    """
    Enforce absolute authenticated session lifetime regardless of activity.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.absolute_age = int(getattr(settings, "SESSION_ABSOLUTE_AGE", settings.SESSION_COOKIE_AGE))

    def __call__(self, request):
        if request.user.is_authenticated:
            now_ts = int(timezone.now().timestamp())
            login_at_ts = request.session.get("auth_login_at_ts")
            if not login_at_ts:
                request.session["auth_login_at_ts"] = now_ts
            elif now_ts - int(login_at_ts) > self.absolute_age:
                logout(request)
                request.session.flush()
        return self.get_response(request)
