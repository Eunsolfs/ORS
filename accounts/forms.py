from django import forms
from django.contrib.auth.forms import AuthenticationForm

from captcha.fields import CaptchaField


class ORSLoginForm(AuthenticationForm):
    captcha = CaptchaField(label="验证码")

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request=request, *args, **kwargs)
        self.fields["username"].widget.attrs.update(
            {
                "class": "input",
                "autocomplete": "username",
                "required": True,
            }
        )
        self.fields["password"].widget.attrs.update(
            {
                "class": "input",
                "autocomplete": "current-password",
                "required": True,
            }
        )
        self.fields["captcha"].widget.attrs.update(
            {
                "class": "input",
                "autocomplete": "off",
                "required": True,
            }
        )
