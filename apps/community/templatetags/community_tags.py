import json

from django import template
from django.contrib.sessions.models import Session
from django.utils import timezone

from community.utils import format_clean_name

register = template.Library()


@register.filter(name="clean_name")
def clean_name_filter(value):
    if not value:
        return ""
    return format_clean_name(str(value))


@register.simple_tag
def online_users_json():
    """Return JSON of currently logged-in users for initial page render."""
    from accounts.models import User

    cutoff = timezone.now()
    sessions = Session.objects.filter(expire_date__gte=cutoff)
    user_ids = set()
    for session in sessions:
        data = session.get_decoded()
        uid = data.get("_auth_user_id")
        if uid:
            user_ids.add(int(uid))

    users = User.objects.filter(id__in=user_ids, is_active=True).values(
        "id", "username", "full_name", "role"
    )
    result = []
    for u in users:
        result.append({
            "id": u["id"],
            "username": u["username"],
            "display_name": format_clean_name(u["full_name"]),
            "role": u["role"],
        })
    return json.dumps(result)
