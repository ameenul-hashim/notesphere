"""Forms for the academics module."""

from django import forms

from accounts.forms import INPUT_CLASS
from config.integrations.cloudinary_storage import delete_image_by_url, upload_image

from .models import Chapter, Semester, Subject


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

    def save(self, commit=True):
        old_thumb_url = None

        # Capture old thumbnail URL before saving
        if self.instance.pk and self.instance.thumbnail:
            try:
                old_thumb_url = str(self.instance.thumbnail) if hasattr(self.instance.thumbnail, "url") else str(self.instance.thumbnail)
            except Exception:
                pass

        # Upload new thumbnail to Cloudinary
        new_thumb = self.cleaned_data.get("thumbnail")
        cloudinary_url = None
        if new_thumb and hasattr(new_thumb, "read"):
            cloudinary_url = upload_image(new_thumb, folder="notesphere/semesters")

        # Clear thumbnail so Django doesn't save to local storage
        self.instance.thumbnail = None
        instance = super().save(commit=False)
        instance.thumbnail = None
        if commit:
            instance.save()

        # Set Cloudinary URL via raw update
        if cloudinary_url and instance.pk:
            Semester.objects.filter(pk=instance.pk).update(thumbnail=cloudinary_url)
            instance.thumbnail = cloudinary_url

        # Delete old Cloudinary image after successful save
        if old_thumb_url and "cloudinary.com" in old_thumb_url:
            if old_thumb_url != (cloudinary_url or ""):
                delete_image_by_url(old_thumb_url)

        return instance


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

    def save(self, commit=True):
        old_thumb_url = None

        # Capture old thumbnail URL before saving
        if self.instance.pk and self.instance.thumbnail:
            try:
                old_thumb_url = str(self.instance.thumbnail) if hasattr(self.instance.thumbnail, "url") else str(self.instance.thumbnail)
            except Exception:
                pass

        # Upload new thumbnail to Cloudinary
        new_thumb = self.cleaned_data.get("thumbnail")
        cloudinary_url = None
        if new_thumb and hasattr(new_thumb, "read"):
            cloudinary_url = upload_image(new_thumb, folder="notesphere/subjects")

        # Clear thumbnail so Django doesn't save to local storage
        self.instance.thumbnail = None
        instance = super().save(commit=False)
        instance.thumbnail = None
        if commit:
            instance.save()

        # Set Cloudinary URL via raw update
        if cloudinary_url and instance.pk:
            Subject.objects.filter(pk=instance.pk).update(thumbnail=cloudinary_url)
            instance.thumbnail = cloudinary_url

        # Delete old Cloudinary image after successful save
        if old_thumb_url and "cloudinary.com" in old_thumb_url:
            if old_thumb_url != (cloudinary_url or ""):
                delete_image_by_url(old_thumb_url)

        return instance


class ChapterForm(forms.ModelForm):
    """Create or update a chapter/module with PDF link or upload."""

    class Meta:
        model = Chapter
        fields = [
            "subject",
            "language",
            "title",
            "subname",
            "chapter_number",
            "description",
            "pdf_url",
            "pdf_file",
            "status",
            "display_order",
        ]
        widgets = {
            "subject": forms.Select(attrs={"class": INPUT_CLASS}),
            "language": forms.Select(attrs={"class": INPUT_CLASS}),
            "title": forms.TextInput(
                attrs={"class": INPUT_CLASS, "placeholder": "Chapter Name (e.g. Module 1)", "maxlength": "150"}
            ),
            "subname": forms.TextInput(
                attrs={"class": INPUT_CLASS, "placeholder": "Subname (e.g. Introduction & Basic Concepts)", "maxlength": "200"}
            ),
            "chapter_number": forms.NumberInput(
                attrs={"class": INPUT_CLASS, "min": "1", "placeholder": "1"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": INPUT_CLASS,
                    "placeholder": "Brief description of topics covered in this chapter",
                    "rows": 3,
                }
            ),
            "pdf_url": forms.URLInput(
                attrs={
                    "class": INPUT_CLASS,
                    "placeholder": "https://supabase-storage-url.pdf or direct PDF URL",
                }
            ),
            "pdf_file": forms.FileInput(attrs={"class": INPUT_CLASS, "accept": ".pdf,application/pdf"}),
            "status": forms.Select(attrs={"class": INPUT_CLASS}),
            "display_order": forms.NumberInput(
                attrs={"class": INPUT_CLASS, "min": "0", "placeholder": "0"}
            ),
        }
        error_messages = {
            "subject": {"required": "Please select a subject."},
            "title": {"required": "Chapter title is required."},
            "chapter_number": {
                "required": "Chapter number is required.",
                "invalid": "Chapter number must be a valid positive integer.",
            },
        }

    def clean(self):
        cleaned_data = super().clean()
        pdf_url = cleaned_data.get("pdf_url")
        pdf_file = cleaned_data.get("pdf_file")
        if not pdf_url and not pdf_file:
            raise forms.ValidationError("Please provide either a PDF URL or upload a PDF file.")
        return cleaned_data

