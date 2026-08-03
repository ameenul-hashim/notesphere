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
    thumbnail = models.ImageField(upload_to="semesters/", null=True, blank=True)
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
    thumbnail = models.ImageField(upload_to="subjects/", null=True, blank=True)
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
        return self.name
