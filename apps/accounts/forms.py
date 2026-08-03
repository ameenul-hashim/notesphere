"""Forms for the NoteSphere authentication module."""

import re

from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import check_password
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import PasswordResetOTP, User
from .validators import (
    validate_full_name,
    validate_password_strength,
    validate_phone,
    validate_username,
)

INPUT_CLASS = "input"


class SignUpForm(forms.Form):
    """Student registration. Every field is mandatory."""

    full_name = forms.CharField(
        widget=forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "John Smith"}),
        validators=[validate_full_name],
        error_messages={"required": "Full name is required."},
    )
    username = forms.CharField(
        widget=forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "john_123"}),
        validators=[validate_username],
        error_messages={"required": "Username is required."},
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"class": INPUT_CLASS, "placeholder": "john@example.com"}),
        error_messages={"required": "Email is required.", "invalid": "Invalid email address."},
    )
    phone = forms.CharField(
        widget=forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "1234567890", "maxlength": "10"}),
        validators=[validate_phone],
        error_messages={"required": "Phone number is required."},
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": INPUT_CLASS, "data-toggle": "password"}),
        validators=[validate_password_strength],
        error_messages={"required": "Password is required."},
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": INPUT_CLASS, "data-toggle": "password"}),
        error_messages={"required": "Confirm password is required."},
    )

    def clean_username(self):
        username = self.cleaned_data.get("username")
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("Username already exists.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("Email already exists.")
        return email

    def clean_phone(self):
        phone = self.cleaned_data.get("phone")
        if User.objects.filter(phone=phone).exists():
            raise ValidationError("Phone number already exists.")
        return phone

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get("password")
        confirm_password = cleaned.get("confirm_password")
        if password and confirm_password and password != confirm_password:
            raise ValidationError("Passwords do not match.")
        return cleaned

    def save(self):
        data = self.cleaned_data
        user = User.objects.create_user(
            username=data["username"],
            email=data["email"],
            phone=data["phone"],
            full_name=data["full_name"],
            password=data["password"],
            role=User.Role.STUDENT,
            status=User.Status.ACTIVE,
        )
        user.password_changed_at = timezone.now()
        user.save(update_fields=["password_changed_at", "updated_at"])
        return user


class LoginForm(forms.Form):
    """Shared login form for students and admins.

    Pass `allowed_role` to restrict login to a specific role (e.g. ADMIN for
    the admin login page). Login errors are generic to prevent enumeration.
    """

    username = forms.CharField(
        widget=forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "Username"}),
        error_messages={"required": "Username is required."},
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": INPUT_CLASS, "data-toggle": "password"}),
        error_messages={"required": "Password is required."},
    )

    def __init__(self, *args, request=None, allowed_role=None, **kwargs):
        self.request = request
        self.allowed_role = allowed_role
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        username = cleaned.get("username")
        password = cleaned.get("password")

        if not (username and password):
            return cleaned

        if self.request is not None:
            user = authenticate(self.request, username=username, password=password)
        else:
            user = authenticate(username=username, password=password)

        if user is None:
            raise ValidationError("Incorrect username or password.")

        if user.status == User.Status.BLOCKED:
            raise ValidationError("Your account has been blocked.")

        if user.status == User.Status.INACTIVE:
            raise ValidationError("Your account is inactive.")

        if self.allowed_role is not None and user.role != self.allowed_role:
            raise ValidationError("Incorrect username or password.")

        cleaned["user"] = user
        return cleaned


class ForgotPasswordForm(forms.Form):
    """Step 1 of the password reset: username + email must belong together."""

    username = forms.CharField(
        widget=forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "Username"}),
        error_messages={"required": "Username is required."},
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"class": INPUT_CLASS, "placeholder": "you@example.com"}),
        error_messages={"required": "Email is required.", "invalid": "Invalid email address."},
    )

    def clean(self):
        cleaned = super().clean()
        username = cleaned.get("username")
        email = cleaned.get("email")

        if not (username and email):
            return cleaned

        user = User.objects.filter(username__iexact=username).first()
        if user is None or user.email.lower() != email.lower():
            raise ValidationError("Username and Email do not match our records.")

        cleaned["user"] = user
        return cleaned


class OTPVerifyForm(forms.Form):
    """Step 2: verify the OTP for an active reset flow."""

    otp = forms.CharField(
        widget=forms.TextInput(
            attrs={"class": INPUT_CLASS, "placeholder": "123456", "maxlength": "6", "inputmode": "numeric", "autocomplete": "one-time-code"}
        ),
        min_length=6,
        max_length=6,
        error_messages={
            "required": "OTP is required.",
            "min_length": "OTP must be exactly 6 digits.",
            "max_length": "OTP must be exactly 6 digits.",
        },
    )

    def __init__(self, *args, otp_obj=None, **kwargs):
        self.otp_obj = otp_obj
        super().__init__(*args, **kwargs)

    def clean_otp(self):
        otp = self.cleaned_data.get("otp")
        if otp and not re.fullmatch(r"\d{6}", otp):
            raise ValidationError("OTP must be exactly 6 digits.")
        return otp

    def clean(self):
        cleaned = super().clean()
        otp = cleaned.get("otp")
        otp_obj = self.otp_obj

        if otp_obj is None:
            raise ValidationError("This password reset session is invalid or expired.")

        if otp_obj.is_used:
            raise ValidationError("This OTP has already been used.")

        if otp_obj.is_expired:
            raise ValidationError("This OTP has expired. Please request a new one.")

        if otp_obj.attempts >= 3:
            raise ValidationError("Too many incorrect attempts. Please request a new OTP.")

        if otp and not check_password(otp, otp_obj.otp_hash):
            otp_obj.attempts += 1
            update_fields = ["attempts"]
            if otp_obj.attempts >= 3:
                otp_obj.is_used = True
                update_fields.append("is_used")
            otp_obj.save(update_fields=update_fields)
            raise ValidationError("Invalid OTP.")

        cleaned["otp_obj"] = otp_obj
        return cleaned


class SetNewPasswordForm(forms.Form):
    """Step 3: choose a new password (same strength rules as signup)."""

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": INPUT_CLASS, "data-toggle": "password"}),
        validators=[validate_password_strength],
        error_messages={"required": "Password is required."},
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": INPUT_CLASS, "data-toggle": "password"}),
        error_messages={"required": "Confirm password is required."},
    )

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get("password")
        confirm_password = cleaned.get("confirm_password")
        if password and confirm_password and password != confirm_password:
            raise ValidationError("Passwords do not match.")
        return cleaned


class ProfileForm(forms.ModelForm):
    """Edit profile details for the logged-in user (admin or student)."""

    full_name = forms.CharField(
        widget=forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "John Smith"}),
        validators=[validate_full_name],
        error_messages={"required": "Full name is required."},
    )
    username = forms.CharField(
        widget=forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "john_123"}),
        validators=[validate_username],
        error_messages={"required": "Username is required."},
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"class": INPUT_CLASS, "placeholder": "john@example.com"}),
        error_messages={"required": "Email is required.", "invalid": "Invalid email address."},
    )
    phone = forms.CharField(
        widget=forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "1234567890", "maxlength": "10"}),
        validators=[validate_phone],
        error_messages={"required": "Phone number is required."},
    )
    profile_image = forms.ImageField(
        required=False,
        label="Profile Image",
        widget=forms.FileInput(attrs={"class": INPUT_CLASS, "accept": "image/*", "data-preview": ""}),
    )
    theme = forms.ChoiceField(
        choices=User.Theme.choices,
        widget=forms.Select(attrs={"class": INPUT_CLASS}),
        label="Theme Preference",
    )

    class Meta:
        model = User
        fields = ["full_name", "username", "email", "phone", "profile_image", "theme"]

    def clean_username(self):
        username = self.cleaned_data.get("username")
        queryset = User.objects.filter(username__iexact=username)
        if self.instance.pk is not None:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise ValidationError("Username already exists.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get("email")
        queryset = User.objects.filter(email__iexact=email)
        if self.instance.pk is not None:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise ValidationError("Email already exists.")
        return email

    def clean_phone(self):
        phone = self.cleaned_data.get("phone")
        queryset = User.objects.filter(phone=phone)
        if self.instance.pk is not None:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise ValidationError("Phone number already exists.")
        return phone


class ChangePasswordForm(forms.Form):
    """Change the logged-in user's password (requires the current password)."""

    current_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": INPUT_CLASS, "data-toggle": "password"}),
        error_messages={"required": "Current password is required."},
    )
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": INPUT_CLASS, "data-toggle": "password"}),
        validators=[validate_password_strength],
        error_messages={"required": "New password is required."},
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": INPUT_CLASS, "data-toggle": "password"}),
        error_messages={"required": "Confirm password is required."},
    )

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_current_password(self):
        current_password = self.cleaned_data.get("current_password")
        if current_password and not check_password(current_password, self.user.password):
            raise ValidationError("Current password is incorrect.")
        return current_password

    def clean(self):
        cleaned = super().clean()
        new_password = cleaned.get("new_password")
        confirm_password = cleaned.get("confirm_password")
        if new_password and confirm_password and new_password != confirm_password:
            raise ValidationError("Passwords do not match.")
        return cleaned
