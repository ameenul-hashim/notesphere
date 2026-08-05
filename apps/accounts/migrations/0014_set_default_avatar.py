"""Set the default avatar (second male, "Noah") for every existing user."""

from django.db import migrations


def set_default_avatar(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    Avatar = apps.get_model("accounts", "Avatar")
    default = Avatar.objects.filter(is_active=True, gender="male", display_order=12).first()
    if default is not None:
        User.objects.update(avatar=default)


def unset_default_avatar(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0013_alter_user_phone"),
    ]

    operations = [
        migrations.RunPython(set_default_avatar, unset_default_avatar),
    ]
