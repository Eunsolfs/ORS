from django import forms

from .models import Course


class CourseForm(forms.ModelForm):
    enable_public_access_password = forms.BooleanField(
        required=False,
        label="启用访问密码",
        help_text="勾选后，公开访问需输入密码。",
    )
    public_access_password = forms.CharField(
        required=False,
        label="公开访问密码",
        help_text="勾选启用访问密码后生效。编辑时留空表示保持现有密码。",
        widget=forms.PasswordInput(
            attrs={"class": "input", "placeholder": "可选：为公开访问设置密码"},
            render_value=False,
        ),
    )

    class Meta:
        model = Course
        fields = [
            "title",
            "status",
            "visibility",
            "enable_public_access_password",
            "public_access_password",
            "content_html",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "input title-input", "placeholder": "输入教程标题…"}),
            "status": forms.Select(attrs={"class": "input combo"}),
            "visibility": forms.Select(attrs={"class": "input combo"}),
            "content_html": forms.Textarea(attrs={"rows": 16, "id": "id_content_html_editor"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._clear_public_password = False
        self.fields["status"].choices = Course.Status.choices
        self.fields["visibility"].choices = Course.Visibility.choices
        if self.instance and self.instance.pk:
            self.fields["enable_public_access_password"].initial = self.instance.has_public_access_password

    def clean(self):
        cleaned_data = super().clean()
        visibility = cleaned_data.get("visibility")
        enable_public_access_password = bool(cleaned_data.get("enable_public_access_password"))
        public_access_password = (cleaned_data.get("public_access_password") or "").strip()

        if visibility != Course.Visibility.PUBLIC:
            self._clear_public_password = True
            return cleaned_data

        if not enable_public_access_password:
            self._clear_public_password = True
            return cleaned_data

        self._clear_public_password = False
        if not public_access_password and not (self.instance and self.instance.pk and self.instance.has_public_access_password):
            self.add_error("public_access_password", "首次启用访问密码时必须填写密码。")
        return cleaned_data

    def save(self, commit=True):
        course: Course = super().save(commit=False)
        password = (self.cleaned_data.get("public_access_password") or "").strip()
        if course.visibility != Course.Visibility.PUBLIC or self._clear_public_password:
            course.public_access_password_hash = ""
            course.public_access_password_plain = ""
        elif password:
            course.set_public_access_password(password)
        if commit:
            course.save()
        return course

