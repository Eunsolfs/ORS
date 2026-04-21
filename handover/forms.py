from __future__ import annotations

from django import forms
from django.forms import inlineformset_factory

from .models import HandoverItem, HandoverSession


class _TriRadio(forms.RadioSelect):
    option_template_name = "django/forms/widgets/radio_option.html"


TRI_CHOICES = [
    ("yes", "✅"),
    ("no", "❌"),
    ("other", "其他"),
]

YES_NO_CHOICES = [
    ("√", "✅"),
    ("×", "❌"),
]

SKIN_CHOICES = [
    ("完整", "完整"),
    ("缺损", "缺损"),
]


class HandoverSessionSummaryForm(forms.ModelForm):
    class Meta:
        model = HandoverSession
        fields = [
            "elective_count",
            "emergency_count",
            "rescue_count",
            "notes",
        ]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
        }


class HandoverSessionChecksForm(forms.ModelForm):
    class Meta:
        model = HandoverSession
        fields = [
            "specimen_handover_status",
            "specimen_handover_note",
            "laminar_flow_running_status",
            "laminar_flow_running_note",
            "bio_monitoring_status",
            "bio_monitoring_note",
            "crash_cart_status",
            "crash_cart_note",
            "fire_safety_status",
            "fire_safety_note",
            "key_management_status",
            "key_management_note",
            "certs_in_place_status",
            "certs_in_place_note",
            "other_incidents",
        ]
        widgets = {
            "other_incidents": forms.Textarea(attrs={"rows": 3}),
            "specimen_handover_status": _TriRadio(choices=TRI_CHOICES),
            "laminar_flow_running_status": _TriRadio(choices=TRI_CHOICES),
            "bio_monitoring_status": _TriRadio(choices=TRI_CHOICES),
            "crash_cart_status": _TriRadio(choices=TRI_CHOICES),
            "fire_safety_status": _TriRadio(choices=TRI_CHOICES),
            "key_management_status": _TriRadio(choices=TRI_CHOICES),
            "certs_in_place_status": _TriRadio(choices=TRI_CHOICES),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in (
            "specimen_handover_status",
            "laminar_flow_running_status",
            "bio_monitoring_status",
            "crash_cart_status",
            "fire_safety_status",
            "key_management_status",
            "certs_in_place_status",
        ):
            self.fields[field_name].choices = TRI_CHOICES


class HandoverItemMobileForm(forms.ModelForm):
    blood_transfusion_checks = forms.ChoiceField(choices=YES_NO_CHOICES, required=False, widget=_TriRadio())
    pressure_ulcer_assessment = forms.ChoiceField(choices=YES_NO_CHOICES, required=False, widget=_TriRadio())
    skin_condition = forms.ChoiceField(choices=SKIN_CHOICES, required=False, widget=_TriRadio())
    preop_visit = forms.ChoiceField(choices=YES_NO_CHOICES, required=False, widget=_TriRadio())

    class Meta:
        model = HandoverItem
        fields = [
            "department_text",
            "patient_name",
            "age",
            "surgery_name",
            "special_handover",
            "blood_transfusion_checks",
            "pressure_ulcer_assessment",
            "skin_condition",
            "preop_visit",
            "special_instruments",
        ]
        widgets = {
            "surgery_name": forms.Textarea(attrs={"rows": 2}),
            "special_handover": forms.Textarea(attrs={"rows": 2}),
            "special_instruments": forms.Textarea(attrs={"rows": 2}),
        }

HandoverItemFormSet = inlineformset_factory(
    HandoverSession,
    HandoverItem,
    form=HandoverItemMobileForm,
    extra=1,
    can_delete=True,
)

