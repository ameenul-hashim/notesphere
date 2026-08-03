"""Forms for the academics module."""

from django import forms

from accounts.forms import INPUT_CLASS

from .models import Semester


class SemesterForm(forms.ModelForm):
    """Create or update a semester.

    The ARCHIVED status is intentionally not offered here: archiving is a
    dedicated soft-delete action, not a value an admin picks on the form.
    """

    class Meta:
        model = Semester
        fields = ["name", "description", "status", "display_order"]
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["status"].choices = [
            (Semester.Status.ACTIVE, Semester.Status.ACTIVE.label),
            (Semester.Status.INACTIVE, Semester.Status.INACTIVE.label),
        ]
