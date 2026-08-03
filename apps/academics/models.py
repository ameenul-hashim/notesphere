"""Academic models for NoteSphere (semesters and, in later phases, subjects)."""

from django.db import models
from django.utils import timezone


class SemesterManager(models.Manager):
    """Default manager: hides ARCHIVED semesters.

    `all_objects` (the base manager) keeps archived semesters visible so they
    always remain restorable.
    """

    use_in_migrations = True

    def get_queryset(self):
        return super().get_queryset().exclude(status="ARCHIVED")


class Semester(models.Model):
    """A study semester such as "Semester 1" or "Semester 2".

    - `status` is the source of truth: ACTIVE / INACTIVE / ARCHIVED.
    - ARCHIVED is a soft delete: `archived_at`/`archived_by` are recorded and
      the row is hidden from the default manager until restored.
    """

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        INACTIVE = "INACTIVE", "Inactive"
        ARCHIVED = "ARCHIVED", "Archived"

    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    display_order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    archived_at = models.DateTimeField(null=True, blank=True)
    archived_by = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="archived_semesters",
    )

    objects = SemesterManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ["display_order", "-created_at"]
        indexes = [
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.status == self.Status.ARCHIVED:
            if self.archived_at is None:
                self.archived_at = timezone.now()
        else:
            self.archived_at = None
            self.archived_by = None
        super().save(*args, **kwargs)
