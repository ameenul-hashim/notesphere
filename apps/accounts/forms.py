"""Forms for the NoteSphere authentication module."""

import re

from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import check_password
from django.core.exceptions import ValidationError
from django.utils import timezone

from config.integrations.cloudinary_storage import (
    delete_image_by_url,
    upload_image,
)

from .models import Avatar, PasswordResetOTP, User
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
        default_avatar = Avatar.objects.filter(is_active=True).first()
        user = User.objects.create_user(
            username=data["username"],
            email=data["email"],
            phone=data["phone"],
            full_name=data["full_name"],
            password=data["password"],
            role=User.Role.STUDENT,
            status=User.Status.ACTIVE,
            avatar=default_avatar,
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


class AdminProfileForm(forms.ModelForm):
    """Admin account details: identity + contact information."""

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

    class Meta:
        model = User
        fields = ["full_name", "username", "email", "phone"]

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


class StudentContactForm(forms.ModelForm):
    """Student contact details: email and phone."""

    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"class": INPUT_CLASS, "placeholder": "john@example.com"}),
        error_messages={"required": "Email is required.", "invalid": "Invalid email address."},
    )
    phone = forms.CharField(
        widget=forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "1234567890", "maxlength": "10"}),
        validators=[validate_phone],
        error_messages={"required": "Phone number is required."},
    )

    class Meta:
        model = User
        fields = ["email", "phone"]

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


class StudentUsernameForm(forms.ModelForm):
    """Student login username (changeable, with uniqueness check)."""

    username = forms.CharField(
        widget=forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "john_123"}),
        validators=[validate_username],
        error_messages={"required": "Username is required."},
    )

    class Meta:
        model = User
        fields = ["username"]

    def clean_username(self):
        username = self.cleaned_data.get("username")
        queryset = User.objects.filter(username__iexact=username)
        if self.instance.pk is not None:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise ValidationError("Username already exists.")
        return username


class AvatarSelectionForm(forms.ModelForm):
    """Profile picture: pick from the curated avatar library."""

    avatar = forms.ModelChoiceField(
        queryset=Avatar.objects.filter(is_active=True),
        required=False,
        label="Avatar",
    )

    class Meta:
        model = User
        fields = ["avatar"]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.photo = None
        if commit:
            user.save()
        return user


class AdminPictureForm(forms.ModelForm):
    """Admin profile picture: custom photo upload only (clears the curated avatar)."""

    photo = forms.ImageField(
        required=False,
        label="Upload a photo",
        widget=forms.ClearableFileInput(attrs={"class": INPUT_CLASS, "data-preview": "photo"}),
        error_messages={"required": "Please choose a photo."},
    )

    class Meta:
        model = User
        fields = ["photo"]

    def get_initial_for_field(self, field, field_name):
        if field_name == "photo":
            return None
        return super().get_initial_for_field(field, field_name)

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("photo"):
            raise ValidationError("Please choose a photo to upload.")
        return cleaned

    def save(self, commit=True):
        # 1. Capture old Cloudinary URL before anything changes
        old_photo_url = None
        try:
            old_val = self.instance.photo
            if old_val:
                name = getattr(old_val, "name", None) or str(old_val)
                if name and "cloudinary.com" in str(name):
                    old_photo_url = str(name)
                elif old_val and hasattr(old_val, "url"):
                    old_photo_url = str(old_val.url)
        except Exception:
            pass

        # 2. Upload new photo to Cloudinary
        new_photo = self.cleaned_data.get("photo")
        cloudinary_url = None
        if new_photo:
            cloudinary_url = upload_image(new_photo, folder="notesphere/profile")

        # 3. Save user WITHOUT photo (clear it so Django doesn't touch file storage)
        self.instance.photo = None
        self.instance.avatar = None
        user = super().save(commit=False)
        user.photo = None
        user.avatar = None
        if commit:
            user.save()

        # 4. Set Cloudinary URL via raw update
        if cloudinary_url and user.pk:
            User.objects.filter(pk=user.pk).update(photo=cloudinary_url)
            user.photo = cloudinary_url

        # 5. Delete old Cloudinary image
        if old_photo_url and cloudinary_url and old_photo_url != cloudinary_url:
            delete_image_by_url(old_photo_url)
        elif old_photo_url and not cloudinary_url:
            delete_image_by_url(old_photo_url)

        return user


class AvatarForm(forms.ModelForm):
    """Admin CRUD for the avatar library (create, edit, delete)."""

    name = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={"class": INPUT_CLASS, "placeholder": "Professional Woman 1"}
        ),
    )
    image = forms.ImageField(
        required=False,
        label="Upload image",
        widget=forms.ClearableFileInput(
            attrs={"class": INPUT_CLASS, "data-preview": "avatar_image"}
        ),
    )
    display_order = forms.IntegerField(
        widget=forms.NumberInput(attrs={"class": INPUT_CLASS}),
        help_text="Female: 1-5 and Male: 11-15 map to the built-in static illustrations.",
    )

    class Meta:
        model = Avatar
        fields = ["name", "gender", "image", "display_order", "is_active", "color_from", "color_to"]
        widgets = {
            "gender": forms.Select(attrs={"class": "select"}),
            "is_active": forms.CheckboxInput(),
            "color_from": forms.TextInput(attrs={"class": INPUT_CLASS, "type": "color"}),
            "color_to": forms.TextInput(attrs={"class": INPUT_CLASS, "type": "color"}),
        }

    def clean(self):
        cleaned = super().clean()
        if self.instance.pk is None and not cleaned.get("image"):
            raise ValidationError("Please upload an image for a new avatar.")
        return cleaned


class StudentPasswordForm(forms.Form):
    """Admin sets a new password for a student directly (no current password)."""

    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": INPUT_CLASS, "data-toggle": "password"}),
        validators=[validate_password_strength],
        error_messages={"required": "New password is required."},
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": INPUT_CLASS, "data-toggle": "password"}),
        error_messages={"required": "Confirm password is required."},
    )

    def clean(self):
        cleaned = super().clean()
        new_password = cleaned.get("new_password")
        confirm_password = cleaned.get("confirm_password")
        if new_password and confirm_password and new_password != confirm_password:
            raise ValidationError("Passwords do not match.")
        return cleaned


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
