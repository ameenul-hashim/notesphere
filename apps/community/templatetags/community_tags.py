import json
import time

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
    """Return JSON of currently active users for initial page render."""
    from accounts.models import User

    ACTIVE_THRESHOLD = 120  # 2 minutes
    cutoff_epoch = int(time.time()) - ACTIVE_THRESHOLD

    sessions = Session.objects.filter(expire_date__gte=timezone.now())
    user_ids = set()
    for session in sessions:
        data = session.get_decoded()
        uid = data.get("_auth_user_id")
        last_active = data.get("last_active") or 0
        if uid and int(last_active) >= cutoff_epoch:
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
