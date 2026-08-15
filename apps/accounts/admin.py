from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html

from .models import Avatar, PasswordResetOTP, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        "full_name",
        "username",
        "email",
        "role",
        "status",
        "is_email_verified",
        "avatar_preview",
        "created_at",
    )
    list_filter = ("role", "status", "is_email_verified", "theme", "created_at")
    search_fields = ("full_name", "username", "email", "phone")
    ordering = ("-created_at",)

    fieldsets = (
        ("Account Credentials", {"fields": ("username", "email", "password")}),
        ("Personal Information", {"fields": ("full_name", "phone", "avatar", "photo")}),
        (
            "Role & Permissions",
            {
                "fields": (
                    "role",
                    "status",
                    "is_email_verified",
                    "is_phone_verified",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                )
            },
        ),
        ("Preferences", {"fields": ("theme",)}),
        ("Important Dates", {"fields": ("last_login", "password_changed_at", "created_at", "updated_at")}),
    )
    readonly_fields = ("created_at", "updated_at", "password_changed_at")

    def avatar_preview(self, obj):
        url = obj.get_avatar_url()
        return format_html(
            '<img src="{}" style="width: 32px; height: 32px; border-radius: 50%; object-fit: cover;" />',
            url,
        )

    avatar_preview.short_description = "Avatar"


@admin.register(Avatar)
class AvatarAdmin(admin.ModelAdmin):
    list_display = ("name", "gender", "display_order", "is_active")
    list_filter = ("gender", "is_active")
    search_fields = ("name",)


@admin.register(PasswordResetOTP)
class PasswordResetOTPAdmin(admin.ModelAdmin):
    list_display = ("user", "expires_at", "attempts", "is_used", "created_at")
    list_filter = ("is_used", "created_at")
    search_fields = ("user__email", "user__full_name")
