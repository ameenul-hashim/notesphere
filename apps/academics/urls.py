"""URL configuration for the academics app.

Admin semester/subject management lives under /dashboard/semesters/ and
/dashboard/subjects/; student-facing semester pages under
/dashboard/student/semesters/.
"""

from django.urls import path

from . import views

app_name = "academics"

urlpatterns = [
    # Semesters
    path("dashboard/semesters/", views.semester_list, name="semester_list"),
    path("dashboard/semesters/new/", views.semester_create, name="semester_create"),
    path("dashboard/semesters/<int:pk>/", views.semester_detail, name="semester_detail"),
    path("dashboard/semesters/<int:pk>/edit/", views.semester_edit, name="semester_edit"),
    path("dashboard/semesters/<int:pk>/delete/", views.semester_delete, name="semester_delete"),
    # Subjects
    path("dashboard/subjects/", views.subject_list, name="subject_list"),
    path("dashboard/subjects/new/", views.subject_create, name="subject_create"),
    path("dashboard/subjects/<int:pk>/", views.subject_detail, name="subject_detail"),
    path("dashboard/subjects/<int:pk>/edit/", views.subject_edit, name="subject_edit"),
    path("dashboard/subjects/<int:pk>/delete/", views.subject_delete, name="subject_delete"),
    # Chapters
    path("dashboard/chapters/new/", views.chapter_create, name="chapter_create"),
    path("dashboard/chapters/next-number/", views.chapter_next_number, name="chapter_next_number"),
    path("dashboard/chapters/<int:pk>/edit/", views.chapter_edit, name="chapter_edit"),
    path("dashboard/chapters/<int:pk>/delete/", views.chapter_delete, name="chapter_delete"),
    path("dashboard/chapters/<int:pk>/read/", views.chapter_read, name="chapter_read"),
    path("dashboard/chapters/<int:pk>/download/", views.chapter_download, name="chapter_download"),
]
