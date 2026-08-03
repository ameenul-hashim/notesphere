"""URL configuration for the academics app.

Admin semester management lives under /dashboard/semesters/ and the
student-facing semester pages under /dashboard/student/semesters/.
"""

from django.urls import path

from . import views

app_name = "academics"

urlpatterns = [
    # Admin: semester management
    path("dashboard/semesters/", views.semester_list, name="semester_list"),
    path("dashboard/semesters/new/", views.semester_create, name="semester_create"),
    path("dashboard/semesters/<int:pk>/edit/", views.semester_edit, name="semester_edit"),
    path("dashboard/semesters/<int:pk>/archive/", views.semester_archive, name="semester_archive"),
    path("dashboard/semesters/<int:pk>/restore/", views.semester_restore, name="semester_restore"),
    # Student: browse active semesters
    path("dashboard/student/semesters/<int:pk>/", views.semester_detail, name="semester_detail"),
]
