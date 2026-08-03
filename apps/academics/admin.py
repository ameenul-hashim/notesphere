from django.contrib import admin
from .models import Chapter, Semester, Subject

@admin.register(Semester)
class SemesterAdmin(admin.ModelAdmin):
    list_display = ("name", "status", "display_order", "created_at")
    list_filter = ("status",)
    search_fields = ("name", "description")


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("name", "semester", "status", "display_order", "created_at")
    list_filter = ("semester", "status")
    search_fields = ("name", "description")


@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ("title", "subject", "chapter_number", "status", "display_order", "created_at")
    list_filter = ("subject__semester", "subject", "status")
    search_fields = ("title", "description", "subject__name")

