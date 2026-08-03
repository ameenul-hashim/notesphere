"""Custom admin interface views (under /dashboard/ - NOT Django's /admin/)."""

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.decorators import admin_required
from accounts.forms import LoginForm
from accounts.models import User, UserActivity
from accounts.services import create_and_send_otp, log_activity


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
    context = {
        "total_students": User.objects.filter(role=User.Role.STUDENT).count(),
        "active_students": User.objects.filter(role=User.Role.STUDENT, status=User.Status.ACTIVE).count(),
        "blocked_students": User.objects.filter(role=User.Role.STUDENT, status=User.Status.BLOCKED).count(),
        "inactive_students": User.objects.filter(role=User.Role.STUDENT, status=User.Status.INACTIVE).count(),
    }
    return render(request, "admins/dashboard.html", context)


@login_required
@admin_required
def student_list(request):
    query = request.GET.get("q", "").strip()
    students = User.objects.filter(role=User.Role.STUDENT).order_by("-created_at")

    if query:
        students = students.filter(
            Q(full_name__icontains=query)
            | Q(username__icontains=query)
            | Q(email__icontains=query)
            | Q(phone__icontains=query)
        )

    paginator = Paginator(students, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "admins/student_list.html", {"page_obj": page_obj, "query": query})


@login_required
@admin_required
def student_detail(request, pk):
    student = get_object_or_404(User, pk=pk, role=User.Role.STUDENT)
    return render(request, "admins/student_detail.html", {"student": student})


@login_required
@admin_required
def block_student(request, pk):
    if request.method == "POST":
        student = get_object_or_404(User, pk=pk, role=User.Role.STUDENT)
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
        student = get_object_or_404(User, pk=pk, role=User.Role.STUDENT)
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
    student = get_object_or_404(User, pk=pk, role=User.Role.STUDENT)
    if request.method == "POST":
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
        return redirect("admins:student_list")
    return render(request, "admins/student_confirm_delete.html", {"student": student})


@login_required
@admin_required
def initiate_student_password_reset(request, pk):
    """Admins never set passwords directly.

    This initiates the reset: an OTP is emailed to the student, who completes
    the password change themselves through the shared OTP flow.
    """
    student = get_object_or_404(User, pk=pk, role=User.Role.STUDENT)
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
    return render(request, "admins/profile.html", {"profile_user": request.user})
