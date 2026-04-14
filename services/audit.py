from apps.inventory.models import AuditLog


def log_action(*, actor, action, obj, metadata=None):
    AuditLog.objects.create(
        action=action,
        actor=actor,
        content_type=obj.__class__.__name__,
        object_id=str(obj.pk),
        object_repr=str(obj),
        metadata=metadata or {},
    )
