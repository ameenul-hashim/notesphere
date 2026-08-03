"""Custom admin interface views (under /dashboard/ - NOT Django's /admin/)."""

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from accounts.decorators import admin_required
from accounts.forms import LoginForm
from accounts.models import User, UserActivity
from accounts.services import create_and_send_otp, log_activity

STUDENTS_PER_PAGE = 20
ACTIVITIES_PER_PAGE = 10

# Whitelist of sortable columns -> model field.
SORTABLE_FIELDS = {
    "full_name": "full_name",
    "username": "username",
    "email": "email",
    "phone": "phone",
    "status": "status",
    "created_at": "created_at",
}


def admin_login(request):
    if request.user.is_authenticated:
        return redirect("admins:dashboard")

    form = LoginForm(request.POST or None, request=request, allowed_role=User.Role.ADMIN)
    if request.method == "POST" and form.is_valid():
        user = form.cleaned_data["user"]
        login(request, user)
        log_activity(user, UserActivity.Action.LOGIN, request, detail="Admin login")
        return redirect("admins:dashboard")
    return render(request, "admins/admin_login.html", {"form": form})


def admin_logout(request):
    if request.method == "POST":
        log_activity(request.user, UserActivity.Action.LOGOUT, request, detail="Admin logout")
        logout(request)
        messages.success(request, "You have been logged out.")
    return redirect("admins:admin_login")


@login_required
@admin_required
def dashboard(request):
    base = User.all_objects.filter(role=User.Role.STUDENT)
    student_list_url = reverse("admins:student_list")
    context = {
        "total_students": base.count(),
        "active_students": base.filter(status=User.Status.ACTIVE).count(),
        "blocked_students": base.filter(status=User.Status.BLOCKED).count(),
        "inactive_students": base.filter(status=User.Status.INACTIVE).count(),
        "deleted_students": base.filter(status=User.Status.DELETED).count(),
        "student_list_url": student_list_url,
        "active_list_url": f"{student_list_url}?status=ACTIVE",
        "inactive_list_url": f"{student_list_url}?status=INACTIVE",
        "blocked_list_url": f"{student_list_url}?status=BLOCKED",
        "deleted_list_url": f"{student_list_url}?status=DELETED",
    }
    return render(request, "admins/dashboard.html", context)


@login_required
@admin_required
def student_list(request):
    query = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "").strip().upper()
    sort = request.GET.get("sort", "created_at")
    direction = request.GET.get("dir", "desc")

    # `all_objects` so soft-deleted students stay visible and recoverable.
    students = User.all_objects.filter(role=User.Role.STUDENT)

    if query:
        students = students.filter(
            Q(full_name__icontains=query)
            | Q(username__icontains=query)
            | Q(email__icontains=query)
            | Q(phone__icontains=query)
        )

    if status_filter in User.Status.values:
        students = students.filter(status=status_filter)

    sort_field = SORTABLE_FIELDS.get(sort, "created_at")
    order = f"-{sort_field}" if direction == "desc" else sort_field
    students = students.order_by(order, "-created_at")

    counts = {
        row["status"]: row["total"]
        for row in User.all_objects.filter(role=User.Role.STUDENT)
        .values("status")
        .annotate(total=Count("id"))
    }

    paginator = Paginator(students, STUDENTS_PER_PAGE)
    page_obj = paginator.get_page(request.GET.get("page"))

    params = request.GET.copy()
    params.pop("page", None)
    params.pop("sort", None)
    params.pop("dir", None)
    qs = params.urlencode()

    return render(
        request,
        "admins/student_list.html",
        {
            "page_obj": page_obj,
            "query": query,
            "status_filter": status_filter,
            "sort": sort,
            "direction": direction,
            "qs": qs,
            "counts": counts,
            "total_students": sum(counts.values()),
        },
    )


@login_required
@admin_required
def student_detail(request, pk):
    student = get_object_or_404(User.all_objects, pk=pk, role=User.Role.STUDENT)
    activities = student.activities.all()
    paginator = Paginator(activities, ACTIVITIES_PER_PAGE)
    activities_page = paginator.get_page(request.GET.get("activity_page"))
    return render(
        request,
        "admins/student_detail.html",
        {"student": student, "activities_page": activities_page},
    )


@login_required
@admin_required
def block_student(request, pk):
    if request.method == "POST":
        student = get_object_or_404(User.all_objects, pk=pk, role=User.Role.STUDENT)
        if student.status in (User.Status.ACTIVE, User.Status.INACTIVE):
            student.status = User.Status.BLOCKED
            student.save(update_fields=["status", "updated_at"])
            log_activity(
                student,
                UserActivity.Action.ACCOUNT_BLOCKED,
                request,
                detail=f"Blocked by {request.user.full_name}",
            )
            messages.success(request, f"{student.full_name} has been blocked.")
        else:
            messages.error(request, "This student cannot be blocked in their current state.")
    return redirect("admins:student_detail", pk=pk)


@login_required
@admin_required
def unblock_student(request, pk):
    if request.method == "POST":
        student = get_object_or_404(User.all_objects, pk=pk, role=User.Role.STUDENT)
        if student.status == User.Status.BLOCKED:
            student.status = User.Status.ACTIVE
            student.save(update_fields=["status", "updated_at"])
            log_activity(
                student,
                UserActivity.Action.ACCOUNT_UNBLOCKED,
                request,
                detail=f"Unblocked by {request.user.full_name}",
            )
            messages.success(request, f"{student.full_name} has been unblocked.")
        else:
            messages.error(request, "Only blocked students can be unblocked.")
    return redirect("admins:student_detail", pk=pk)


@login_required
@admin_required
def delete_student(request, pk):
    student = get_object_or_404(User.all_objects, pk=pk, role=User.Role.STUDENT)
    if request.method == "POST":
        if student.status != User.Status.DELETED:
            student.status = User.Status.DELETED
            student.deleted_at = timezone.now()
            student.deleted_by = request.user
            student.save(
                update_fields=["status", "deleted_at", "deleted_by", "is_active", "updated_at"]
            )
            log_activity(
                student,
                UserActivity.Action.ACCOUNT_DELETED,
                request,
                detail=f"Soft-deleted by {request.user.full_name}",
            )
            messages.success(request, f"{student.full_name} has been deleted.")
        else:
            messages.error(request, "This student is already deleted.")
        return redirect("admins:student_list")
    return render(request, "admins/student_confirm_delete.html", {"student": student})


@login_required
@admin_required
def restore_student(request, pk):
    if request.method == "POST":
        student = get_object_or_404(User.all_objects, pk=pk, role=User.Role.STUDENT)
        if student.status == User.Status.DELETED:
            student.status = User.Status.ACTIVE
            student.deleted_at = None
            student.deleted_by = None
            student.save(
                update_fields=["status", "deleted_at", "deleted_by", "is_active", "updated_at"]
            )
            log_activity(
                student,
                UserActivity.Action.ACCOUNT_UNBLOCKED,
                request,
                detail=f"Restored from deleted state by {request.user.full_name}",
            )
            messages.success(request, f"{student.full_name} has been restored.")
        else:
            messages.error(request, "Only deleted students can be restored.")
    return redirect("admins:student_detail", pk=pk)


@login_required
@admin_required
def initiate_student_password_reset(request, pk):
    """Admins never set passwords directly.

    This initiates the reset: an OTP is emailed to the student, who completes
    the password change themselves through the shared OTP flow.
    """
    student = get_object_or_404(User.all_objects, pk=pk, role=User.Role.STUDENT)
    if request.method == "POST":
        if student.status == User.Status.DELETED:
            messages.error(request, "Deleted students cannot reset their password.")
            return redirect("admins:student_detail", pk=pk)
        create_and_send_otp(student, request)
        log_activity(
            student,
            UserActivity.Action.PASSWORD_RESET,
            request,
            detail=f"Password reset initiated by {request.user.full_name}",
        )
        messages.success(request, f"A password reset OTP has been sent to {student.email}.")
        return redirect("admins:student_detail", pk=pk)
    return render(request, "admins/student_reset_password.html", {"student": student})


@login_required
def profile(request):
    return render(request, "admins/profile.html", {"profile_user": request.user})
