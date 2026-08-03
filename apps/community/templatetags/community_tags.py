from django import template

from community.utils import format_clean_name

register = template.Library()


@register.filter(name="clean_name")
def clean_name_filter(value):
    if not value:
        return ""
    return format_clean_name(str(value))
