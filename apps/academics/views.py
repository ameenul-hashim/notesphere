"""Views for the academics module (semester management for admins, semester
browsing for students)."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from accounts.decorators import admin_required, student_required

from .forms import SemesterForm
from .models import Semester

SEMESTERS_PER_PAGE = 10

# Whitelist of sortable columns -> model field.
SORTABLE_FIELDS = {
    "name": "name",
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

    # `all_objects` so archived semesters stay visible and restorable.
    semesters = Semester.all_objects.all()

    if query:
        semesters = semesters.filter(Q(name__icontains=query) | Q(description__icontains=query))

    if status_filter in Semester.Status.values:
        semesters = semesters.filter(status=status_filter)

    sort_field = SORTABLE_FIELDS.get(sort, "display_order")
    order = f"-{sort_field}" if direction == "desc" else sort_field
    semesters = semesters.order_by(order, "display_order")

    counts = {
        row["status"]: row["total"]
        for row in Semester.all_objects.values("status").annotate(total=Count("id"))
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
            "archived_list_url": f"{semester_list_url}?status=ARCHIVED",
        },
    )


@login_required
@admin_required
def semester_create(request):
    form = SemesterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Semester \"{form.cleaned_data['name']}\" has been created.")
        return redirect("academics:semester_list")
    return render(request, "academics/semester_form.html", {"form": form, "title": "Create Semester"})


@login_required
@admin_required
def semester_edit(request, pk):
    semester = get_object_or_404(Semester, pk=pk)
    form = SemesterForm(request.POST or None, instance=semester)
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
def semester_archive(request, pk):
    if request.method == "POST":
        semester = get_object_or_404(Semester.all_objects, pk=pk)
        if semester.status != Semester.Status.ARCHIVED:
            semester.status = Semester.Status.ARCHIVED
            semester.archived_at = timezone.now()
            semester.archived_by = request.user
            semester.save(update_fields=["status", "archived_at", "archived_by", "updated_at"])
            messages.success(request, f"Semester \"{semester.name}\" has been archived.")
        else:
            messages.error(request, "This semester is already archived.")
    return redirect("academics:semester_list")


@login_required
@admin_required
def semester_restore(request, pk):
    if request.method == "POST":
        semester = get_object_or_404(Semester.all_objects, pk=pk)
        if semester.status == Semester.Status.ARCHIVED:
            semester.status = Semester.Status.ACTIVE
            semester.archived_at = None
            semester.archived_by = None
            semester.save(update_fields=["status", "archived_at", "archived_by", "updated_at"])
            messages.success(request, f"Semester \"{semester.name}\" has been restored.")
        else:
            messages.error(request, "Only archived semesters can be restored.")
    return redirect("academics:semester_list")


@login_required
@student_required
def semester_detail(request, pk):
    """Students only ever see ACTIVE semesters."""
    semester = get_object_or_404(Semester.objects, pk=pk, status=Semester.Status.ACTIVE)
    return render(request, "academics/semester_detail.html", {"semester": semester})
