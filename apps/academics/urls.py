"""URL configuration for the academics app.

Admin semester/subject management lives under /dashboard/semesters/ and
/dashboard/subjects/; student-facing semester pages under
/dashboard/student/semesters/.
"""

from django.urls import path

from . import views

app_name = "academics"

urlpatterns = [
    # Admin: semester management
    path("dashboard/semesters/", views.semester_list, name="semester_list"),
    path("dashboard/semesters/new/", views.semester_create, name="semester_create"),
    path("dashboard/semesters/<int:pk>/edit/", views.semester_edit, name="semester_edit"),
    path("dashboard/semesters/<int:pk>/delete/", views.semester_delete, name="semester_delete"),
    # Admin: subject management
    path("dashboard/subjects/", views.subject_list, name="subject_list"),
    path("dashboard/subjects/new/", views.subject_create, name="subject_create"),
    path("dashboard/subjects/<int:pk>/edit/", views.subject_edit, name="subject_edit"),
    path("dashboard/subjects/<int:pk>/delete/", views.subject_delete, name="subject_delete"),
    # Student: browse active semesters
    path("dashboard/student/semesters/<int:pk>/", views.semester_detail, name="semester_detail"),
]
