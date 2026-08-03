"""Seed the library of 20 predefined avatars.

Avatars are rendered purely from CSS gradients plus an inline SVG path (or a
monogram initial). Users only store a foreign key to the avatar; no image
files are uploaded.
"""

from django.db import migrations

# (name, icon_markup, color_from, color_to, monogram, display_order)
# icon_markup is raw inner-SVG content rendered inside <svg viewBox="0 0 24 24">.
AVATARS = [
    ("Classic", "", "#6366f1", "#8b5cf6", True, 1),
    ("Slate", "", "#64748b", "#475569", True, 2),
    ("Rose", "", "#f43f5e", "#fb7185", True, 3),
    (
        "Indigo",
        '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
        "#6366f1",
        "#818cf8",
        False,
        4,
    ),
    (
        "Blossom",
        '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/><path d="M12 11v6"/>',
        "#ec4899",
        "#f472b6",
        False,
        5,
    ),
    (
        "Graphite",
        '<rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2"/>',
        "#475569",
        "#64748b",
        False,
        6,
    ),
    (
        "Campus",
        '<path d="M22 10 12 5 2 10l10 5 10-5z"/><path d="M6 12v5c3 3 9 3 12 0v-5"/>',
        "#10b981",
        "#059669",
        False,
        7,
    ),
    (
        "Smile",
        '<circle cx="12" cy="12" r="10"/><path d="M8 14s1.5 2 4 2 4-2 4-2"/><line x1="9" y1="9" x2="9.01" y2="9"/><line x1="15" y1="9" x2="15.01" y2="9"/>',
        "#f59e0b",
        "#f97316",
        False,
        8,
    ),
    (
        "Prism",
        '<circle cx="13.5" cy="6.5" r=".5"/><circle cx="17.5" cy="10.5" r=".5"/><circle cx="8.5" cy="7.5" r=".5"/><circle cx="6.5" cy="12.5" r=".5"/><path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c.926 0 1.648-.746 1.648-1.688 0-.437-.18-.835-.437-1.125-.29-.289-.438-.652-.438-1.125a1.64 1.64 0 0 1 1.668-1.668h1.996c3.051 0 5.555-2.503 5.555-5.554C21.965 6.012 17.461 2 12 2z"/>',
        "#8b5cf6",
        "#ec4899",
        False,
        9,
    ),
    (
        "Forest",
        '<path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10z"/><path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12"/>',
        "#22c55e",
        "#15803d",
        False,
        10,
    ),
    (
        "Amber",
        '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/>',
        "#f59e0b",
        "#d97706",
        False,
        11,
    ),
    (
        "Night",
        '<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9z"/>',
        "#312e81",
        "#4338ca",
        False,
        12,
    ),
    (
        "Electron",
        '<path d="M13 2 3 14h9l-1 8 10-12h-9l1-8z"/>',
        "#06b6d4",
        "#3b82f6",
        False,
        13,
    ),
    (
        "Furry",
        '<circle cx="4" cy="10" r="1.2"/><circle cx="9" cy="6" r="1.2"/><circle cx="15" cy="6" r="1.2"/><circle cx="20" cy="10" r="1.2"/><path d="M6 20c0-3 3-4 6-4s6 1 6 4"/>',
        "#a16207",
        "#d97706",
        False,
        14,
    ),
    (
        "Byte",
        '<rect x="4" y="8" width="16" height="12" rx="2"/><path d="M12 8V4"/><circle cx="12" cy="4" r="2"/><rect x="8" y="13" width="3" height="3" rx="1"/><rect x="13" y="13" width="3" height="3" rx="1"/>',
        "#64748b",
        "#0ea5e9",
        False,
        15,
    ),
    (
        "Focus",
        '<circle cx="7" cy="11" r="3"/><circle cx="17" cy="11" r="3"/><path d="M10 11h4"/><path d="M3 20c1-3 2.5-4.5 4-4.5S9 17 10 20M21 20c-1-3-2.5-4.5-4-4.5s-3 1.5-4 4.5"/>',
        "#0f766e",
        "#14b8a6",
        False,
        16,
    ),
    (
        "Royal",
        '<path d="m2 6 4 4 6-6 6 6 4-4v11a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1z"/>',
        "#7c3aed",
        "#6d28d9",
        False,
        17,
    ),
    (
        "Beat",
        '<path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>',
        "#db2777",
        "#9333ea",
        False,
        18,
    ),
    (
        "Lens",
        '<path d="M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3l-2.5-3z"/><circle cx="12" cy="13" r="3"/>',
        "#1f2937",
        "#4b5563",
        False,
        19,
    ),
    (
        "Sail",
        '<path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"/><path d="m12 15-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z"/><path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0"/><path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5"/>',
        "#0284c7",
        "#0ea5e9",
        False,
        20,
    ),
]


def seed_avatars(apps, schema_editor):
    Avatar = apps.get_model("accounts", "Avatar")
    for name, markup, c_from, c_to, monogram, order in AVATARS:
        Avatar.objects.update_or_create(
            name=name,
            defaults={
                "icon_path": markup,
                "color_from": c_from,
                "color_to": c_to,
                "monogram": monogram,
                "is_active": True,
                "display_order": order,
            },
        )


def unseed_avatars(apps, schema_editor):
    Avatar = apps.get_model("accounts", "Avatar")
    Avatar.objects.filter(name__in=[a[0] for a in AVATARS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_avatar_remove_user_profile_image_user_avatar"),
    ]

    operations = [
        migrations.RunPython(seed_avatars, unseed_avatars),
    ]
