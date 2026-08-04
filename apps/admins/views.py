"""Custom admin interface views (under /dashboard/ - NOT Django's /admin/)."""

from datetime import datetime, time, timedelta

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from accounts.decorators import admin_required
from accounts.forms import (
    AdminPictureForm,
    AdminProfileForm,
    AvatarForm,
    AvatarSelectionForm,
    ChangePasswordForm,
    LoginForm,
    StudentContactForm,
    StudentPasswordForm,
    StudentUsernameForm,
)
from accounts.models import Avatar, User
from accounts.services import set_password_and_track
from academics.models import Semester, Subject

STUDENTS_PER_PAGE = 20
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
        request.session.flush()
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
        start = timezone.make_aware(datetime.combine(_shift_month(current_month, -i), time.min))
        end = timezone.make_aware(datetime.combine(_shift_month(current_month, -i + 1), time.min))
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
    username_form = StudentUsernameForm(instance=student)
    password_form = StudentPasswordForm()
    show_edit = request.GET.get("edit") == "1"

    if request.method == "POST":
        if "save_username" in request.POST:
            username_form = StudentUsernameForm(instance=student, data=request.POST)
            if username_form.is_valid():
                username_form.save()
                messages.success(
                    request,
                    f"Username updated to @{username_form.cleaned_data['username']}.",
                )
                return redirect("admins:student_detail", pk=pk)
            else:
                show_edit = True
        elif "save_password" in request.POST:
            password_form = StudentPasswordForm(data=request.POST)
            if password_form.is_valid():
                set_password_and_track(student, password_form.cleaned_data["new_password"])
                messages.success(request, f"Password updated for {student.full_name}.")
                return redirect("admins:student_detail", pk=pk)
            else:
                show_edit = True

    return render(
        request,
        "admins/student_detail.html",
        {
            "student": student,
            "username_form": username_form,
            "password_form": password_form,
            "show_edit": show_edit,
        },
    )


@login_required
@admin_required
def block_student(request, pk):
    if request.method == "POST":
        student = get_object_or_404(User.objects, pk=pk, role=User.Role.STUDENT)
        if student.status in (User.Status.ACTIVE, User.Status.INACTIVE):
            student.status = User.Status.BLOCKED
            student.save(update_fields=["status", "updated_at"])
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
        student.delete()
        messages.success(request, f"{full_name} has been permanently deleted.")
        return redirect("admins:student_list")
    return render(request, "admins/student_confirm_delete.html", {"student": student})


@login_required
@admin_required
def avatar_add(request):
    """Create a new avatar in the library."""
    if request.method == "POST":
        form = AvatarForm(data=request.POST, files=request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Avatar added successfully.")
            return redirect("admins:avatar_list")
    else:
        form = AvatarForm()
    return render(request, "admins/avatar_form.html", {"form": form, "mode": "add"})


@login_required
@admin_required
def avatar_edit(request, pk):
    """Edit an existing avatar."""
    avatar = get_object_or_404(Avatar, pk=pk)
    if request.method == "POST":
        form = AvatarForm(instance=avatar, data=request.POST, files=request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Avatar updated successfully.")
            return redirect("admins:avatar_list")
    else:
        form = AvatarForm(instance=avatar)
    return render(
        request,
        "admins/avatar_form.html",
        {"form": form, "avatar": avatar, "mode": "edit"},
    )


@login_required
@admin_required
def avatar_delete(request, pk):
    """Permanently delete an avatar from the library."""
    avatar = get_object_or_404(Avatar, pk=pk)
    if request.method == "POST":
        label = str(avatar)
        avatar.delete()
        messages.success(request, f"Avatar deleted.")
    return redirect("admins:avatar_list")


@login_required
@admin_required
def avatar_list(request):
    """Admin avatar management: view the library and toggle avatars on/off."""
    if request.method == "POST":
        avatar = get_object_or_404(Avatar, pk=request.POST.get("pk"))
        avatar.is_active = not avatar.is_active
        avatar.save(update_fields=["is_active"])
        messages.success(
            request,
            f"{avatar} is now {'active' if avatar.is_active else 'inactive'}.",
        )
        return redirect("admins:avatar_list")

    avatars = Avatar.objects.all()
    context = {
        "avatars": avatars,
        "active_count": avatars.filter(is_active=True).count(),
        "total_count": avatars.count(),
        "male_count": avatars.filter(gender=Avatar.Gender.MALE).count(),
        "female_count": avatars.filter(gender=Avatar.Gender.FEMALE).count(),
    }
    return render(request, "admins/avatar_list.html", context)


@login_required
def profile(request):
    """Admin profile page. Students are redirected to their own profile page."""
    if not request.user.is_admin:
        return redirect("accounts:student_profile")

    details_form = AdminProfileForm(instance=request.user)
    picture_form = AdminPictureForm(instance=request.user)
    password_form = ChangePasswordForm(user=request.user)

    if request.method == "POST":
        if "save_details" in request.POST:
            details_form = AdminProfileForm(instance=request.user, data=request.POST)
            if details_form.is_valid():
                details_form.save()
                messages.success(request, "Profile details updated successfully.")
                return redirect("admins:profile")
        elif "save_picture" in request.POST:
            picture_form = AdminPictureForm(
                instance=request.user,
                data=request.POST,
                files=request.FILES,
            )
            if picture_form.is_valid():
                picture_form.save()
                messages.success(request, "Profile picture updated successfully.")
                return redirect("admins:profile")
        elif "change_password" in request.POST:
            password_form = ChangePasswordForm(user=request.user, data=request.POST)
            if password_form.is_valid():
                set_password_and_track(
                    request.user,
                    password_form.cleaned_data["new_password"],
                )
                messages.success(request, "Password changed successfully.")
                return redirect("admins:profile")

    return render(
        request,
        "admins/profile.html",
        {
            "profile_user": request.user,
            "is_admin": True,
            "details_form": details_form,
            "picture_form": picture_form,
            "password_form": password_form,
        },
    )


@login_required
def appearance(request):
    """Appearance settings: pick the color theme (separate from avatar/profile)."""
    return render(request, "accounts/settings.html", {"settings_user": request.user})
