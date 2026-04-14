from django import template

register = template.Library()


@register.filter
def status_badge_class(value):
    mapping = {
        "available": "bg-success-subtle text-success",
        "low": "bg-warning-subtle text-warning-emphasis",
        "out": "bg-danger-subtle text-danger",
    }
    return mapping.get(value, "bg-secondary-subtle text-secondary")
