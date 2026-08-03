"""Custom admin interface views (under /dashboard/ - NOT Django's /admin/)."""

from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from accounts.decorators import admin_required
from accounts.forms import ChangePasswordForm, LoginForm, ProfileForm
from accounts.models import User, UserActivity
from accounts.services import create_and_send_otp, log_activity, set_password_and_track
from academics.models import Semester, Subject

STUDENTS_PER_PAGE = 20
ACTIVITIES_PER_PAGE = 10
REGISTRATION_MONTHS = 6

# Whitelist of sortable columns -> model field.
SORTABLE_FIELDS = {
    "full_name": "full_name",
    "username": "username",
    "email": "email",
    "phone": "phone",
    "status": "status",
    "created_at": "created_at",
}

# Student list filter presets (used by the filter chips).
FILTER_LABELS = {
    "latest_joined": "Latest Joined",
    "oldest_joined": "Oldest Joined",
    "login_today": "Last Login Today",
    "login_yesterday": "Last Login Yesterday",
    "inactive_30d": "Inactive for 30 Days",
}


def _shift_month(day, delta):
    """Shift a 1st-of-month date by `delta` months."""
    month_index = day.month - 1 + delta
    year = day.year + month_index // 12
    month = month_index % 12 + 1
    return day.replace(year=year, month=month, day=1)


def admin_login(request):
    if request.user.is_authenticated:
        return redirect("admins:dashboard")

    form = LoginForm(request.POST or None, request=request, allowed_role=User.Role.ADMIN)
    if request.method == "POST" and form.is_valid():
        user = form.cleaned_data["user"]
        login(request, user)
        return redirect("admins:dashboard")
    return render(request, "admins/admin_login.html", {"form": form})


def admin_logout(request):
    if request.method == "POST":
        logout(request)
        messages.success(request, "You have been logged out.")
    return redirect("admins:admin_login")


@login_required
@admin_required
def dashboard(request):
    base = User.objects.filter(role=User.Role.STUDENT)
    student_list_url = reverse("admins:student_list")

    status_counts = {
        row["status"]: row["total"]
        for row in base.values("status").annotate(total=Count("id"))
    }
    active = status_counts.get(User.Status.ACTIVE, 0)
    inactive = status_counts.get(User.Status.INACTIVE, 0)
    blocked = status_counts.get(User.Status.BLOCKED, 0)
    total = active + inactive + blocked

    # Student registrations over the last N months.
    current_month = timezone.localdate().replace(day=1)
    months = []
    for i in range(REGISTRATION_MONTHS - 1, -1, -1):
        start = _shift_month(current_month, -i)
        end = _shift_month(current_month, -i + 1)
        months.append(
            {
                "label": start.strftime("%b"),
                "count": base.filter(created_at__gte=start, created_at__lt=end).count(),
            }
        )
    max_registrations = max((m["count"] for m in months), default=1) or 1

    status_segments = [
        {"label": "Active", "count": active, "color": "var(--success)"},
        {"label": "Inactive", "count": inactive, "color": "var(--warning)"},
        {"label": "Blocked", "count": blocked, "color": "var(--danger)"},
    ]
    for segment in status_segments:
        segment["pct"] = round((segment["count"] / total * 100), 1) if total else 0

    context = {
        "total_students": total,
        "active_students": active,
        "inactive_students": inactive,
        "blocked_students": blocked,
        "semester_count": Semester.objects.count(),
        "subject_count": Subject.objects.count(),
        "student_list_url": student_list_url,
        "active_list_url": f"{student_list_url}?status=ACTIVE",
        "inactive_list_url": f"{student_list_url}?status=INACTIVE",
        "blocked_list_url": f"{student_list_url}?status=BLOCKED",
        "reg_chart": months,
        "reg_max": max_registrations,
        "status_segments": status_segments,
        "recent_students": base.order_by("-created_at")[:6],
        "recent_logins": base.exclude(last_login__isnull=True).order_by("-last_login")[:6],
    }
    return render(request, "admins/dashboard.html", context)


@login_required
@admin_required
def student_list(request):
    query = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "").strip().upper()
    filter_key = request.GET.get("filter", "").strip()
    sort = request.GET.get("sort", "created_at")
    direction = request.GET.get("dir", "desc")

    students = User.objects.filter(role=User.Role.STUDENT)

    if query:
        students = students.filter(
            Q(full_name__icontains=query)
            | Q(username__icontains=query)
            | Q(email__icontains=query)
            | Q(phone__icontains=query)
        )

    if filter_key == "latest_joined":
        students = students.order_by("-created_at")
    elif filter_key == "oldest_joined":
        students = students.order_by("created_at")
    elif filter_key == "login_today":
        students = students.filter(last_login__date=timezone.localdate())
    elif filter_key == "login_yesterday":
        students = students.filter(last_login__date=timezone.localdate() - timedelta(days=1))
    elif filter_key == "inactive_30d":
        cutoff = timezone.now() - timedelta(days=30)
        students = students.filter(Q(last_login__isnull=True) | Q(last_login__lt=cutoff))
    else:
        filter_key = ""

    if status_filter in User.Status.values:
        students = students.filter(status=status_filter)
    else:
        status_filter = ""

    if filter_key not in ("latest_joined", "oldest_joined"):
        sort_field = SORTABLE_FIELDS.get(sort, "created_at")
        order = f"-{sort_field}" if direction == "desc" else sort_field
        students = students.order_by(order, "-created_at")

    counts = {
        row["status"]: row["total"]
        for row in User.objects.filter(role=User.Role.STUDENT)
        .values("status")
        .annotate(total=Count("id"))
    }

    today = timezone.localdate()
    yesterday = today - timedelta(days=1)
    cutoff = timezone.now() - timedelta(days=30)
    student_qs = User.objects.filter(role=User.Role.STUDENT)
    filter_counts = {
        "all": student_qs.count(),
        "login_today": student_qs.filter(last_login__date=today).count(),
        "login_yesterday": student_qs.filter(last_login__date=yesterday).count(),
        "inactive_30d": student_qs.filter(
            Q(last_login__isnull=True) | Q(last_login__lt=cutoff)
        ).count(),
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
            "filter_key": filter_key,
            "filter_counts": filter_counts,
            "filter_labels": FILTER_LABELS,
            "sort": sort,
            "direction": direction,
            "qs": qs,
            "counts": counts,
            "total_students": filter_counts["all"],
        },
    )


@login_required
@admin_required
def student_detail(request, pk):
    student = get_object_or_404(User.objects, pk=pk, role=User.Role.STUDENT)
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
        student = get_object_or_404(User.objects, pk=pk, role=User.Role.STUDENT)
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
        student = get_object_or_404(User.objects, pk=pk, role=User.Role.STUDENT)
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
    student = get_object_or_404(User.objects, pk=pk, role=User.Role.STUDENT)
    if request.method == "POST":
        full_name = student.full_name
        log_activity(
            request.user,
            UserActivity.Action.ACCOUNT_DELETED,
            request,
            detail=f"Deleted student \"{full_name}\" (username: {student.username})",
        )
        student.delete()
        messages.success(request, f"{full_name} has been permanently deleted.")
        return redirect("admins:student_list")
    return render(request, "admins/student_confirm_delete.html", {"student": student})


@login_required
@admin_required
def initiate_student_password_reset(request, pk):
    """Admins never set passwords directly.

    This initiates the reset: an OTP is emailed to the student, who completes
    the password change themselves through the shared OTP flow.
    """
    student = get_object_or_404(User.objects, pk=pk, role=User.Role.STUDENT)
    if request.method == "POST":
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
    """Edit the logged-in user's profile and password (shared by admins and students)."""
    profile_form = ProfileForm(
        instance=request.user,
        data=request.POST or None,
        files=request.FILES or None,
    )
    password_form = ChangePasswordForm(user=request.user, data=request.POST or None)

    if request.method == "POST":
        if "save_profile" in request.POST:
            if profile_form.is_valid():
                profile_form.save()
                log_activity(
                    request.user,
                    UserActivity.Action.PROFILE_UPDATED,
                    request,
                    detail="Profile details updated",
                )
                messages.success(request, "Profile updated successfully.")
                return redirect("admins:profile")
        elif "change_password" in request.POST:
            if password_form.is_valid():
                set_password_and_track(
                    request.user,
                    password_form.cleaned_data["new_password"],
                    request,
                    action=UserActivity.Action.PASSWORD_RESET,
                    detail="Password changed from profile",
                )
                messages.success(request, "Password changed successfully.")
                return redirect("admins:profile")

    return render(
        request,
        "admins/profile.html",
        {
            "profile_user": request.user,
            "profile_form": profile_form,
            "password_form": password_form,
        },
    )
