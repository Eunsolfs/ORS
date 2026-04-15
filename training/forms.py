from django import forms

from .models import Course


class CourseForm(forms.ModelForm):
    STATUS_CHOICES = (
        ("draft", "草稿"),
        ("published", "已发布"),
        ("archived", "已归档"),
    )

    status = forms.ChoiceField(choices=STATUS_CHOICES, widget=forms.Select(attrs={"class": "input combo"}))

    class Meta:
        model = Course
        fields = [
            "title",
            "status",
            "content_html",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "input title-input", "placeholder": "输入教程标题…"}),
            "content_html": forms.Textarea(attrs={"rows": 16, "id": "id_content_html_editor"}),
        }

