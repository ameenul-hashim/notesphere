"""Replace the 20 cartoon faces with 10 professional avatar slots.

Avatars are now served as static PNG illustrations from
static/images/avatars/ (avatar_female_1..5.png, avatar_male_1..5.png).
Avatar rows only carry identity metadata (gender + display_order); users
store just the avatar foreign key. The legacy `name` and `monogram`
columns and the 20 cartoon rows are dropped, and existing users are
remapped to a gender-matched avatar in the new library.
"""

from django.db import migrations

FEMALE_ORDERS = [1, 2, 3, 4, 5]
MALE_ORDERS = [11, 12, 13, 14, 15]


def delete_legacy_avatars(apps, schema_editor):
    Avatar = apps.get_model("accounts", "Avatar")
    Avatar.objects.all().delete()


def seed_avatars(apps, schema_editor):
    Avatar = apps.get_model("accounts", "Avatar")
    rows = [
        Avatar(
            pk=pk,
            gender="female",
            display_order=order,
            is_active=True,
            color_from="#8b5cf6",
            color_to="#6366f1",
        )
        for pk, order in enumerate(FEMALE_ORDERS, start=1)
    ] + [
        Avatar(
            pk=pk,
            gender="male",
            display_order=order,
            is_active=True,
            color_from="#3b82f6",
            color_to="#06b6d4",
        )
        for pk, order in enumerate(MALE_ORDERS, start=6)
    ]
    Avatar.objects.bulk_create(rows)


def remap_users(apps, schema_editor):
    """Legacy cartoon rows used pk 1-10 (female) and pk 11-20 (male).

    New rows are pk 1-5 (female) and pk 6-10 (male), so map by slot.
    """
    User = apps.get_model("accounts", "User")
    for user in User.objects.exclude(avatar_id=None):
        old = user.avatar_id
        if old <= 10:
            user.avatar_id = 1 + ((old - 1) % 5)
        else:
            user.avatar_id = 6 + ((old - 11) % 5)
        user.save(update_fields=["avatar_id"])


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0007_user_photo_alter_user_theme"),
    ]

    operations = [
        migrations.RemoveField(model_name="avatar", name="name"),
        migrations.RemoveField(model_name="avatar", name="monogram"),
        migrations.RunPython(delete_legacy_avatars, migrations.RunPython.noop),
        migrations.RunPython(seed_avatars, migrations.RunPython.noop),
        migrations.RunPython(remap_users, migrations.RunPython.noop),
    ]
