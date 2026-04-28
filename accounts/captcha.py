import random
import string

from django.conf import settings


def _allowed_chars_by_mode(mode: str) -> str:
    normalized = (mode or "").strip().lower()
    if normalized == "digit":
        return string.digits
    if normalized == "alpha":
        return string.ascii_letters
    return string.ascii_letters + string.digits


def ors_login_challenge():
    """
    Challenge function for django-simple-captcha.
    Returns (challenge, response).
    """
    mode = getattr(settings, "ORS_LOGIN_CAPTCHA_MODE", "alnum")
    length = int(getattr(settings, "ORS_LOGIN_CAPTCHA_LENGTH", 5) or 5)
    length = max(4, min(length, 8))
    chars = _allowed_chars_by_mode(mode)
    value = "".join(random.choice(chars) for _ in range(length))
    return value, value
