"""Academic models for NoteSphere (semesters and subjects)."""

from django.db import models


class SemesterManager(models.Manager):
    """Legacy manager retained so the initial migration can be loaded.

    Semester soft-deletion (ARCHIVED) was removed, so this manager behaves
    exactly like the default manager.
    """

    use_in_migrations = True

    def get_queryset(self):
        return super().get_queryset()


class Semester(models.Model):
    """A study semester such as "Semester 1" or "Semester 2".

    Deletion is permanent: deleting a semester cascades to its subjects.
    """

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        INACTIVE = "INACTIVE", "Inactive"

    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    thumbnail = models.ImageField(upload_to="semesters/", max_length=500, null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    display_order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_order", "-created_at"]
        indexes = [
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return self.name


class Subject(models.Model):
    """A subject that belongs to one semester."""

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        INACTIVE = "INACTIVE", "Inactive"

    semester = models.ForeignKey(Semester, on_delete=models.CASCADE, related_name="subjects")
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    thumbnail = models.ImageField(upload_to="subjects/", max_length=500, null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    display_order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_order", "name"]
        indexes = [
            models.Index(fields=["semester", "status"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.semester.name})"


class Chapter(models.Model):
    """A chapter or module belonging to a subject."""

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        INACTIVE = "INACTIVE", "Inactive"

    class Language(models.TextChoices):
        ENGLISH = "ENGLISH", "English Notes"
        MALAYALAM = "MALAYALAM", "Malayalam Notes"

    class Kind(models.TextChoices):
        MODULE = "MODULE", "Module"
        CHAPTER = "CHAPTER", "Chapter"

    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="chapters")
    kind = models.CharField(
        max_length=10,
        choices=Kind.choices,
        default=Kind.MODULE,
        help_text="Whether this entry is a Module or a Chapter.",
    )
    language = models.CharField(
        max_length=15,
        choices=Language.choices,
        default=Language.ENGLISH,
        help_text="Language medium of this chapter (English or Malayalam)",
    )
    title = models.CharField(max_length=150, help_text="Chapter name / main title")
    subname = models.CharField(max_length=200, blank=True, help_text="Subname or subtitle (e.g. Unit 1 / Topic)")
    description = models.TextField(blank=True)
    chapter_number = models.PositiveIntegerField(default=1, help_text="Chapter number or module index")
    pdf_url = models.URLField(max_length=500, blank=True, help_text="Direct URL to PDF (Supabase, Drive, CDN)")
    pdf_file = models.FileField(upload_to="chapters/pdfs/", null=True, blank=True, help_text="Upload local PDF file")
    thumbnail = models.ImageField(upload_to="chapters/thumbnails/", max_length=500, null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    display_order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_order", "chapter_number", "id"]
        indexes = [
            models.Index(fields=["subject", "status"]),
            models.Index(fields=["subject", "language", "status"]),
        ]

    def __str__(self):
        return f"{self.subject.name} - Chapter {self.chapter_number}: {self.title}"

    @property
    def document_url(self):
        if self.pdf_file:
            return self.pdf_file.url
        return self.pdf_url or ""

