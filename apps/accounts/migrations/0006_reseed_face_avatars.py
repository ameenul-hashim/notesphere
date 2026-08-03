"""Reseed the avatar library with 20 illustrated faces (10 male + 10 female).

Each avatar is a flat vector face rendered from pure inline SVG (drawn behind
the CSS gradient circle), so no image files are uploaded or served. Rows are
updated IN PLACE by their existing primary keys (1-20) so user foreign keys
remain valid.
"""

from django.db import migrations

SKINS = {
    "light": "#f3d5bd",
    "tan": "#eec39a",
    "medium": "#e0ac69",
    "brown": "#c68642",
    "deep": "#8d5524",
}

# ---------------------------------------------------------------------------
# Hair style builders (viewBox 0 0 24 24)
# ---------------------------------------------------------------------------

def cap(h):
    return (
        f'<path d="M3.8 11.6 C3.8 4.4 7.4 2.8 12 2.8 C16.6 2.8 20.2 4.4 '
        f'20.2 11.6 C18.2 9.2 15.8 8.4 12 8.4 C8.2 8.4 5.8 9.2 3.8 11.6 Z" fill="{h}"/>'
    )


def long_back(h):
    return (
        f'<path d="M4.2 12.4 C4.2 5.6 7.4 3.8 12 3.8 C16.6 3.8 19.8 5.6 '
        f'19.8 12.4 C19.8 15.6 18.4 18.2 15.8 19.6 C14.6 20.3 13.4 20.6 '
        f'12 20.6 C10.6 20.6 9.4 20.3 8.2 19.6 C5.6 18.2 4.2 15.6 4.2 12.4 Z" fill="{h}"/>'
    )


def bob_back(h):
    return (
        f'<path d="M4.6 12.2 C4.6 5.6 7.6 3.8 12 3.8 C16.4 3.8 19.4 5.6 '
        f'19.4 12.2 C19.4 14.8 18.2 16.6 16.2 17.6 C14.9 18.2 13.5 18.4 '
        f'12 18.4 C10.5 18.4 9.1 18.2 7.8 17.6 C5.8 16.6 4.6 14.8 4.6 12.2 Z" fill="{h}"/>'
    )


def side_strands_long(h):
    return (
        f'<path d="M4.6 12.2 C4.6 15.2 5.8 17.4 7.6 18.2 L7.9 14.6 '
        f'C6.4 13.9 5.4 12.9 4.6 12.2 Z" fill="{h}"/>'
        f'<path d="M19.4 12.2 C19.4 15.2 18.2 17.4 16.4 18.2 L16.1 14.6 '
        f'C17.6 13.9 18.6 12.9 19.4 12.2 Z" fill="{h}"/>'
    )


def side_strands_bob(h):
    return (
        f'<path d="M4.8 12.2 C4.8 14.6 5.8 16.2 7.4 16.9 L7.8 14 '
        f'C6.4 13.5 5.5 12.7 4.8 12.2 Z" fill="{h}"/>'
        f'<path d="M19.2 12.2 C19.2 14.6 18.2 16.2 16.6 16.9 L16.2 14 '
        f'C17.6 13.5 18.5 12.7 19.2 12.2 Z" fill="{h}"/>'
    )


def curls(h):
    return (
        f'<circle cx="6.4" cy="5.6" r="2.1" fill="{h}"/><circle cx="9.2" cy="4.4" r="2.4" fill="{h}"/>'
        f'<circle cx="12.2" cy="4.1" r="2.5" fill="{h}"/><circle cx="15.2" cy="4.4" r="2.4" fill="{h}"/>'
        f'<circle cx="18" cy="5.7" r="2" fill="{h}"/><circle cx="7.8" cy="7.2" r="1.6" fill="{h}"/>'
        f'<circle cx="16.4" cy="7.2" r="1.6" fill="{h}"/>'
    )


def fro(h):
    return (
        f'<circle cx="6" cy="6.6" r="2.6" fill="{h}"/><circle cx="9.4" cy="4.8" r="2.9" fill="{h}"/>'
        f'<circle cx="12.8" cy="4.6" r="3" fill="{h}"/><circle cx="16.2" cy="5" r="2.8" fill="{h}"/>'
        f'<circle cx="18.6" cy="6.8" r="2.3" fill="{h}"/><circle cx="7.2" cy="8" r="2" fill="{h}"/>'
        f'<circle cx="17" cy="8" r="1.9" fill="{h}"/>'
    )


def spikes(h):
    return (
        f'<path d="M5.8 4.8 l-1.2-2.2 M8.4 3.8 l-.9-2.4 M11 3.4 l-.5-2.6 '
        f'M13.6 3.4 l.4-2.6 M16.2 3.9 l1-2.4 M18.6 4.9 l1.2-2.2" '
        f'stroke="{h}" stroke-width="2" stroke-linecap="round"/>'
    )


def top_bun(h):
    return (
        f'<circle cx="12" cy="3.2" r="2" fill="{h}"/>'
        f'<path d="M10.2 4.2 h3.6" stroke="#ffffff33" stroke-width=".9" stroke-linecap="round"/>'
    )


def space_buns(h):
    return f'<circle cx="7.4" cy="3.4" r="1.8" fill="{h}"/><circle cx="16.6" cy="3.4" r="1.8" fill="{h}"/>'


def ponytail(h):
    return (
        f'<path d="M15.4 5.4 C16.8 6.6 16.9 9.4 16.2 12.6" stroke="{h}" '
        f'stroke-width="3" stroke-linecap="round" fill="none"/>'
        f'<circle cx="15.2" cy="4.4" r="1.8" fill="{h}"/>'
    )


def waves(h):
    return (
        f'<path d="M6.4 7.4 q1.2-.8 2.4 0 M12 6.2 q1.2-.8 2.4 0 M16.6 7.4 q1.2-.8 2.4 0" '
        f'stroke="#00000018" stroke-width=".7" fill="none" stroke-linecap="round"/>'
    )


def shine(h):
    return (
        f'<path d="M7.6 5.4 q2.2-.9 4.4 0" stroke="#ffffff2a" stroke-width=".7" fill="none" stroke-linecap="round"/>'
    )


def beard(h):
    return (
        f'<path d="M8.6 14.9 C9.4 16.8 14.6 16.8 15.4 14.9 L15.9 16.2 '
        f'C16 18.2 14.3 19.8 12 19.8 C9.7 19.8 8 18.2 8.1 16.2 Z" fill="{h}"/>'
    )


def stubble(h):
    return (
        f'<path d="M8.8 15.6 C10.4 17 13.6 17 15.2 15.6 C15.8 16.6 15.8 17.8 '
        f'14.4 18.8 C13.6 19.4 12 19.7 12 19.7 C12 19.7 10.4 19.4 9.6 18.8 '
        f'C8.2 17.8 8.2 16.6 8.8 15.6 Z" fill="{h}" opacity=".9"/>'
    )


def glasses():
    return (
        f'<circle cx="9" cy="13.8" r="2.3" fill="none" stroke="#1f2937" stroke-width=".85"/>'
        f'<circle cx="15" cy="13.8" r="2.3" fill="none" stroke="#1f2937" stroke-width=".85"/>'
        f'<path d="M11.3 13.8 h1.4" stroke="#1f2937" stroke-width=".85"/>'
        f'<path d="M2.9 13.6 l1.4-.5 M21.1 13.6 l-1.4-.5" stroke="#1f2937" stroke-width=".85" stroke-linecap="round"/>'
    )


def earrings():
    return (
        f'<circle cx="4.6" cy="16.4" r=".8" fill="#eab308"/>'
        f'<circle cx="19.4" cy="16.4" r=".8" fill="#eab308"/>'
    )


def face(skin, hair, back="", front="", pre="", post=""):
    parts = []
    if back:
        parts.append(back)
    parts.append(f'<circle cx="5.5" cy="13.6" r="1.6" fill="{skin}"/>')
    parts.append(f'<circle cx="18.5" cy="13.6" r="1.6" fill="{skin}"/>')
    parts.append(f'<circle cx="12" cy="12.8" r="6.8" fill="{skin}"/>')
    parts.append(front)
    if pre:
        parts.append(pre)
    parts.append(
        f'<path d="M7.7 11.5 q1.3-.8 2.6 0" stroke="{hair}" stroke-width=".7" fill="none" stroke-linecap="round"/>'
        f'<path d="M13.7 11.5 q1.3-.8 2.6 0" stroke="{hair}" stroke-width=".7" fill="none" stroke-linecap="round"/>'
    )
    parts.append(
        f'<circle cx="9" cy="13.8" r=".95" fill="#2a2630"/><circle cx="15" cy="13.8" r=".95" fill="#2a2630"/>'
        f'<circle cx="9.35" cy="13.55" r=".32" fill="#ffffff"/><circle cx="15.35" cy="13.55" r=".32" fill="#ffffff"/>'
    )
    parts.append(
        f'<path d="M9.7 16.4 q2.3 1.5 4.6 0" stroke="#b4593a" stroke-width=".9" fill="none" stroke-linecap="round"/>'
    )
    parts.append(
        '<circle cx="7.6" cy="15.5" r="1.05" fill="#f9a8c9" opacity=".4"/>'
        '<circle cx="16.4" cy="15.5" r="1.05" fill="#f9a8c9" opacity=".4"/>'
    )
    if post:
        parts.append(post)
    return "".join(parts)


# ---------------------------------------------------------------------------
# (name, gender, icon_path, color_from, color_to, display_order)
# ---------------------------------------------------------------------------

def _female(name, skin_key, hair, back_fn, extra_front, post, c_from, c_to, order):
    skin = SKINS[skin_key]
    back = back_fn(hair)
    front = cap(hair) + extra_front(hair)
    return (name, "female", face(skin, hair, back=back, front=front, post=post), c_from, c_to, order)


def _male(name, skin_key, hair, extra_front, pre, post, c_from, c_to, order):
    skin = SKINS[skin_key]
    front = cap(hair) + extra_front(hair)
    return (name, "male", face(skin, hair, front=front, pre=pre, post=post), c_from, c_to, order)


AVATARS = [
    # ---- Female (10) ----
    _female("Aisha", "deep", "#2b2b2b", long_back, side_strands_long, earrings(), "#f43f5e", "#fb7185", 1),
    _female("Maya", "tan", "#6f3e2b", long_back, side_strands_long, "", "#8b5cf6", "#6366f1", 2),
    _female("Sofia", "light", "#e8b04b", bob_back, side_strands_bob, "", "#ec4899", "#f472b6", 3),
    _female("Layla", "brown", "#3a2a28", long_back, lambda h: side_strands_long(h) + space_buns(h), earrings(), "#14b8a6", "#0ea5e9", 4),
    _female("Amara", "medium", "#8a4b2d", long_back, lambda h: side_strands_long(h) + ponytail(h), "", "#f97316", "#f43f5e", 5),
    _female("Nina", "light", "#6d3a63", bob_back, side_strands_bob, earrings(), "#a855f7", "#d946ef", 6),
    _female("Zara", "tan", "#d99a3d", long_back, side_strands_long, "", "#f59e0b", "#f97316", 7),
    _female("Elena", "light", "#b5543a", long_back, lambda h: side_strands_long(h) + top_bun(h), "", "#6366f1", "#3b82f6", 8),
    _female("Priya", "deep", "#2b2b2b", long_back, lambda h: side_strands_long(h) + curls(h), earrings(), "#d97706", "#eab308", 9),
    _female("Ines", "medium", "#2f7d78", long_back, side_strands_long, "", "#0ea5e9", "#22d3ee", 10),
    # ---- Male (10) ----
    _male("Liam", "tan", "#6f3e2b", shine, "", "", "#3b82f6", "#6366f1", 11),
    _male("Noah", "medium", "#2b2b2b", shine, "", "", "#06b6d4", "#3b82f6", 12),
    _male("Kai", "light", "#3a2a28", spikes, "", "", "#10b981", "#14b8a6", 13),
    _male("Diego", "deep", "#2b2b2b", lambda h: curls(h) + shine(h), beard("#2b2b2b"), "", "#f97316", "#ef4444", 14),
    _male("Adam", "tan", "#4a2c2a", waves, stubble("#4a2c2a"), "", "#64748b", "#475569", 15),
    _male("Omar", "deep", "#4a2c2a", fro, "", "", "#7c3aed", "#8b5cf6", 16),
    _male("Leo", "light", "#e8b04b", waves, "", glasses(), "#22c55e", "#84cc16", 17),
    _male("Ethan", "light", "#b5543a", shine, "", "", "#f43f5e", "#e11d48", 18),
    _male("Ravi", "brown", "#2b2b2b", lambda h: top_bun(h) + shine(h), "", "", "#ea580c", "#f59e0b", 19),
    _male("Marcus", "medium", "#8a4b2d", waves, "", glasses(), "#06b6d4", "#14b8a6", 20),
]


def reseed_avatars(apps, schema_editor):
    Avatar = apps.get_model("accounts", "Avatar")
    for pk, (name, gender, icon, c_from, c_to, order) in enumerate(AVATARS, start=1):
        Avatar.objects.update_or_create(
            pk=pk,
            defaults={
                "name": name,
                "gender": gender,
                "icon_path": icon,
                "color_from": c_from,
                "color_to": c_to,
                "monogram": False,
                "is_active": True,
                "display_order": order,
            },
        )


def unseed_avatars(apps, schema_editor):
    Avatar = apps.get_model("accounts", "Avatar")
    Avatar.objects.filter(pk__in=range(1, 21)).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0005_avatar_gender"),
    ]

    operations = [
        migrations.RunPython(reseed_avatars, unseed_avatars),
    ]
