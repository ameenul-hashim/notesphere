"""Views for the academics module (semester and subject management for admins,
semester browsing for students)."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from accounts.decorators import admin_required, student_required

from .forms import SemesterForm, SubjectForm
from .models import Semester, Subject

SEMESTERS_PER_PAGE = 12
SUBJECTS_PER_PAGE = 12

# Whitelist of sortable columns -> model field.
SEMESTER_SORTABLE_FIELDS = {
    "name": "name",
    "status": "status",
    "display_order": "display_order",
    "created_at": "created_at",
}
SUBJECT_SORTABLE_FIELDS = {
    "name": "name",
    "semester": "semester__name",
    "status": "status",
    "display_order": "display_order",
    "created_at": "created_at",
}


@login_required
@admin_required
def semester_list(request):
    query = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "").strip().upper()
    sort = request.GET.get("sort", "display_order")
    direction = request.GET.get("dir", "asc")

    semesters = Semester.objects.annotate(subject_count=Count("subjects"))

    if query:
        semesters = semesters.filter(Q(name__icontains=query) | Q(description__icontains=query))

    if status_filter in Semester.Status.values:
        semesters = semesters.filter(status=status_filter)
    else:
        status_filter = ""

    sort_field = SEMESTER_SORTABLE_FIELDS.get(sort, "display_order")
    order = f"-{sort_field}" if direction == "desc" else sort_field
    semesters = semesters.order_by(order, "display_order")

    counts = {
        row["status"]: row["total"]
        for row in Semester.objects.values("status").annotate(total=Count("id"))
    }

    paginator = Paginator(semesters, SEMESTERS_PER_PAGE)
    page_obj = paginator.get_page(request.GET.get("page"))

    params = request.GET.copy()
    params.pop("page", None)
    params.pop("sort", None)
    params.pop("dir", None)
    qs = params.urlencode()

    semester_list_url = reverse("academics:semester_list")

    return render(
        request,
        "academics/semester_list.html",
        {
            "page_obj": page_obj,
            "query": query,
            "status_filter": status_filter,
            "sort": sort,
            "direction": direction,
            "qs": qs,
            "counts": counts,
            "total_semesters": sum(counts.values()),
            "semester_list_url": semester_list_url,
            "inactive_list_url": f"{semester_list_url}?status=INACTIVE",
        },
    )


@login_required
@admin_required
def semester_create(request):
    form = SemesterForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Semester \"{form.cleaned_data['name']}\" has been created.")
        return redirect("academics:semester_list")
    return render(request, "academics/semester_form.html", {"form": form, "title": "Create Semester"})


@login_required
@admin_required
def semester_edit(request, pk):
    semester = get_object_or_404(Semester, pk=pk)
    form = SemesterForm(request.POST or None, request.FILES or None, instance=semester)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Semester \"{semester.name}\" has been updated.")
        return redirect("academics:semester_list")
    return render(
        request,
        "academics/semester_form.html",
        {"form": form, "title": "Edit Semester", "semester": semester},
    )


@login_required
@admin_required
def semester_delete(request, pk):
    if request.method == "POST":
        semester = get_object_or_404(Semester, pk=pk)
        messages.success(
            request,
            f"Semester \"{semester.name}\" and its subjects have been deleted.",
        )
        semester.delete()
    return redirect("academics:semester_list")


@login_required
@admin_required
def subject_list(request):
    query = request.GET.get("q", "").strip()
    semester_filter = request.GET.get("semester", "").strip()
    status_filter = request.GET.get("status", "").strip().upper()
    sort = request.GET.get("sort", "display_order")
    direction = request.GET.get("dir", "asc")

    subjects = Subject.objects.select_related("semester")

    if query:
        subjects = subjects.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )

    if semester_filter.isdigit():
        subjects = subjects.filter(semester_id=int(semester_filter))
    else:
        semester_filter = ""

    if status_filter in Subject.Status.values:
        subjects = subjects.filter(status=status_filter)
    else:
        status_filter = ""

    sort_field = SUBJECT_SORTABLE_FIELDS.get(sort, "display_order")
    order = f"-{sort_field}" if direction == "desc" else sort_field
    subjects = subjects.order_by(order, "display_order")

    counts = {
        row["status"]: row["total"]
        for row in Subject.objects.values("status").annotate(total=Count("id"))
    }

    paginator = Paginator(subjects, SUBJECTS_PER_PAGE)
    page_obj = paginator.get_page(request.GET.get("page"))

    params = request.GET.copy()
    params.pop("page", None)
    params.pop("sort", None)
    params.pop("dir", None)
    qs = params.urlencode()

    return render(
        request,
        "academics/subject_list.html",
        {
            "page_obj": page_obj,
            "query": query,
            "semester_filter": semester_filter,
            "status_filter": status_filter,
            "semesters": Semester.objects.order_by("display_order"),
            "sort": sort,
            "direction": direction,
            "qs": qs,
            "counts": counts,
            "total_subjects": sum(counts.values()),
        },
    )


@login_required
@admin_required
def subject_create(request):
    form = SubjectForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Subject \"{form.cleaned_data['name']}\" has been created.")
        return redirect("academics:subject_list")
    return render(request, "academics/subject_form.html", {"form": form, "title": "Create Subject"})


@login_required
@admin_required
def subject_edit(request, pk):
    subject = get_object_or_404(Subject, pk=pk)
    form = SubjectForm(request.POST or None, request.FILES or None, instance=subject)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Subject \"{subject.name}\" has been updated.")
        return redirect("academics:subject_list")
    return render(
        request,
        "academics/subject_form.html",
        {"form": form, "title": "Edit Subject", "subject": subject},
    )


@login_required
@admin_required
def subject_delete(request, pk):
    if request.method == "POST":
        subject = get_object_or_404(Subject, pk=pk)
        messages.success(request, f"Subject \"{subject.name}\" has been deleted.")
        subject.delete()
    return redirect("academics:subject_list")


@login_required
@student_required
def semester_detail(request, pk):
    """Students only ever see ACTIVE semesters."""
    semester = get_object_or_404(Semester, pk=pk, status=Semester.Status.ACTIVE)
    subjects = semester.subjects.filter(status=Subject.Status.ACTIVE)
    return render(
        request,
        "academics/semester_detail.html",
        {"semester": semester, "subjects": subjects},
    )
