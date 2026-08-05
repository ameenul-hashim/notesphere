"""Forms for the academics module."""

from django import forms
from django.core.files.uploadedfile import UploadedFile

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
        # 1. Read old thumbnail URL directly from DB
        old_thumb_url = None
        if self.instance.pk:
            try:
                db_val = Semester.objects.filter(pk=self.instance.pk).values_list("thumbnail", flat=True).first()
                if db_val and "cloudinary.com" in str(db_val):
                    old_thumb_url = str(db_val)
            except Exception:
                pass

        # 2. Upload a NEW thumbnail to Cloudinary only when a file was chosen
        new_thumb = self.cleaned_data.get("thumbnail")
        cloudinary_url = None
        if isinstance(new_thumb, UploadedFile):
            cloudinary_url = upload_image(new_thumb, folder="notesphere/semesters")

        # 3. Keep the existing thumbnail unless a replacement was uploaded
        instance = super().save(commit=False)
        if cloudinary_url:
            instance.thumbnail = cloudinary_url
        elif old_thumb_url:
            instance.thumbnail = old_thumb_url
        else:
            instance.thumbnail = None
        if commit:
            instance.save()

        # 4. Delete the old Cloudinary image only when replaced by a new one
        if cloudinary_url and old_thumb_url and old_thumb_url != cloudinary_url:
            try:
                delete_image_by_url(old_thumb_url)
            except Exception:
                pass

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
        # 1. Read old thumbnail URL directly from DB
        old_thumb_url = None
        if self.instance.pk:
            try:
                db_val = Subject.objects.filter(pk=self.instance.pk).values_list("thumbnail", flat=True).first()
                if db_val and "cloudinary.com" in str(db_val):
                    old_thumb_url = str(db_val)
            except Exception:
                pass

        # 2. Upload a NEW thumbnail to Cloudinary only when a file was chosen
        new_thumb = self.cleaned_data.get("thumbnail")
        cloudinary_url = None
        if isinstance(new_thumb, UploadedFile):
            cloudinary_url = upload_image(new_thumb, folder="notesphere/subjects")

        # 3. Keep the existing thumbnail unless a replacement was uploaded
        instance = super().save(commit=False)
        if cloudinary_url:
            instance.thumbnail = cloudinary_url
        elif old_thumb_url:
            instance.thumbnail = old_thumb_url
        else:
            instance.thumbnail = None
        if commit:
            instance.save()

        # 4. Delete the old Cloudinary image only when replaced by a new one
        if cloudinary_url and old_thumb_url and old_thumb_url != cloudinary_url:
            try:
                delete_image_by_url(old_thumb_url)
            except Exception:
                pass

        return instance


class ChapterForm(forms.ModelForm):
    """Create or update a chapter/module with a PDF URL."""

    subname = forms.CharField(
        label="Subname (optional)",
        required=False,
        widget=forms.TextInput(
            attrs={"class": INPUT_CLASS, "placeholder": "Subname (e.g. Introduction & Basic Concepts)", "maxlength": "200"}
        ),
    )

    class Meta:
        model = Chapter
        fields = [
            "subject",
            "kind",
            "language",
            "title",
            "subname",
            "chapter_number",
            "thumbnail",
            "pdf_url",
            "status",
            "display_order",
        ]
        widgets = {
            "subject": forms.Select(attrs={"class": INPUT_CLASS}),
            "kind": forms.Select(attrs={"class": INPUT_CLASS}),
            "language": forms.Select(attrs={"class": INPUT_CLASS}),
            "title": forms.TextInput(
                attrs={"class": INPUT_CLASS, "placeholder": "Chapter Name (e.g. Module 1)", "maxlength": "150"}
            ),
            "chapter_number": forms.NumberInput(
                attrs={"class": INPUT_CLASS, "min": "1", "placeholder": "1"}
            ),
            "thumbnail": forms.FileInput(attrs={"class": INPUT_CLASS, "accept": "image/*", "data-preview": ""}),
            "pdf_url": forms.URLInput(
                attrs={
                    "class": INPUT_CLASS,
                    "placeholder": "https://supabase-storage-url.pdf or direct PDF URL",
                }
            ),
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
            "pdf_url": {"required": "PDF URL is required.", "invalid": "Please enter a valid PDF URL."},
        }

    def clean_pdf_url(self):
        pdf_url = self.cleaned_data.get("pdf_url")
        if not pdf_url:
            raise forms.ValidationError("PDF URL is required.")
        return pdf_url

    def save(self, commit=True):
        # 1. Read old thumbnail URL directly from DB
        old_thumb_url = None
        if self.instance.pk:
            try:
                db_val = Chapter.objects.filter(pk=self.instance.pk).values_list("thumbnail", flat=True).first()
                if db_val and "cloudinary.com" in str(db_val):
                    old_thumb_url = str(db_val)
            except Exception:
                pass

        # 2. Upload a NEW thumbnail to Cloudinary only when a file was chosen
        new_thumb = self.cleaned_data.get("thumbnail")
        cloudinary_url = None
        if isinstance(new_thumb, UploadedFile):
            cloudinary_url = upload_image(new_thumb, folder="notesphere/chapters")

        # 3. Keep the existing thumbnail unless a replacement was uploaded
        instance = super().save(commit=False)
        if cloudinary_url:
            instance.thumbnail = cloudinary_url
        elif old_thumb_url:
            instance.thumbnail = old_thumb_url
        else:
            instance.thumbnail = None
        if commit:
            instance.save()

        # 4. Delete the old Cloudinary image only when replaced by a new one
        if cloudinary_url and old_thumb_url and old_thumb_url != cloudinary_url:
            try:
                delete_image_by_url(old_thumb_url)
            except Exception:
                pass

        return instance

