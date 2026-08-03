"""Forms for the academics module."""

from django import forms

from accounts.forms import INPUT_CLASS

from .models import Semester, Subject


class SemesterForm(forms.ModelForm):
    """Create or update a semester."""

    class Meta:
        model = Semester
        fields = ["name", "description", "thumbnail", "status", "display_order"]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": INPUT_CLASS, "placeholder": "Semester 1", "maxlength": "50"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": INPUT_CLASS,
                    "placeholder": "Optional description of this semester",
                    "rows": 3,
                }
            ),
            "thumbnail": forms.FileInput(attrs={"class": INPUT_CLASS, "accept": "image/*", "data-preview": ""}),
            "status": forms.Select(attrs={"class": INPUT_CLASS}),
            "display_order": forms.NumberInput(
                attrs={"class": INPUT_CLASS, "min": "0", "placeholder": "0"}
            ),
        }
        error_messages = {
            "name": {"required": "Semester name is required."},
            "display_order": {
                "required": "Display order is required.",
                "invalid": "Display order must be a non-negative number.",
            },
        }


class SubjectForm(forms.ModelForm):
    """Create or update a subject."""

    class Meta:
        model = Subject
        fields = ["semester", "name", "description", "thumbnail", "status", "display_order"]
        widgets = {
            "semester": forms.Select(attrs={"class": INPUT_CLASS}),
            "name": forms.TextInput(
                attrs={"class": INPUT_CLASS, "placeholder": "Mathematics", "maxlength": "100"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": INPUT_CLASS,
                    "placeholder": "Optional description of this subject",
                    "rows": 3,
                }
            ),
            "thumbnail": forms.FileInput(attrs={"class": INPUT_CLASS, "accept": "image/*", "data-preview": ""}),
            "status": forms.Select(attrs={"class": INPUT_CLASS}),
            "display_order": forms.NumberInput(
                attrs={"class": INPUT_CLASS, "min": "0", "placeholder": "0"}
            ),
        }
        error_messages = {
            "semester": {"required": "Please choose a semester."},
            "name": {"required": "Subject name is required."},
            "display_order": {
                "required": "Display order is required.",
                "invalid": "Display order must be a non-negative number.",
            },
        }
