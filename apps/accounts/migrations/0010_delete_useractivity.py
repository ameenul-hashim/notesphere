"""Drop the per-student activity log table.

The UserActivity audit log consumed storage for every account action and is
not needed; this removes the table and all of its rows. Student-related
timestamps (last_login, password_changed_at, created_at, updated_at) remain
on the User row itself.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0009_alter_avatar_icon_path_alter_user_photo"),
    ]

    operations = [
        migrations.DeleteModel(name="UserActivity"),
    ]
