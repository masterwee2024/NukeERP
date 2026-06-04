"""AuditModelMixin — auto-track model changes to AuditLog."""

import threading
from typing import Any

from django.db import models

_audit_context = threading.local()


def set_audit_context(user, ip_address=None):
    """Store current user and IP for the audit mixin to consume."""
    _audit_context.user = user
    _audit_context.ip_address = ip_address


def clear_audit_context():
    """Clear thread-local audit context after the request completes."""
    _audit_context.user = None
    _audit_context.ip_address = None


def get_audit_user():
    return getattr(_audit_context, "user", None)


def get_audit_ip():
    return getattr(_audit_context, "ip_address", None)


AUDIT_EXCLUDE_FIELDS = {"updated_at", "created_at", "version"}


def compute_changes(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    """Return a JSON diff {field: {old: X, new: Y}} between two field dicts."""
    changes: dict[str, Any] = {}
    all_keys = set(old.keys()) | set(new.keys())
    for key in all_keys:
        if key in AUDIT_EXCLUDE_FIELDS:
            continue
        old_val = old.get(key)
        new_val = new.get(key)
        if old_val != new_val:
            changes[key] = {"old": old_val, "new": new_val}
    return changes


def serialize_field_value(value: Any) -> Any:
    """Convert a field value to a JSON-serializable form."""
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, models.Model):
        return str(value.pk)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, (list, tuple)):
        return [serialize_field_value(v) for v in value]
    if isinstance(value, dict):
        return {k: serialize_field_value(v) for k, v in value.items()}
    return str(value)


def get_model_name(instance: models.Model) -> str:
    """Return the dotted model name (e.g. 'core.Company')."""
    meta = instance._meta
    return f"{meta.app_label}.{meta.object_name}"


def get_field_dict(instance: models.Model) -> dict[str, Any]:
    """Return a JSON-serializable dict of all field values for an instance."""
    result: dict[str, Any] = {}
    for field in instance._meta.fields:
        name = field.name
        if isinstance(field, models.AutoField):
            continue
        value = serialize_field_value(getattr(instance, name))
        result[name] = value
    return result


class AuditModelMixin(models.Model):
    """Abstract mixin that auto-creates AuditLog entries on save/delete.

    Usage:
        class MyModel(AuditModelMixin, ConcurrencyModel):
            ...

    To disable auditing on a subclass, set _audit_enabled = False (class attribute).
    """

    _audit_enabled = True

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        is_new = self._state.adding

        if is_new or not getattr(self, "_audit_enabled", True):
            super().save(*args, **kwargs)
            if is_new and getattr(self, "_audit_enabled", True):
                self._create_audit_entry("create")
            return

        # Track old values before save
        if self.pk:
            try:
                old_instance = self.__class__.objects.get(pk=self.pk)
                old_fields = get_field_dict(old_instance)
            except self.__class__.DoesNotExist:
                old_fields = {}

        super().save(*args, **kwargs)

        if not getattr(self, "_audit_enabled", True):
            return

        new_fields = get_field_dict(self)
        changes = compute_changes(old_fields, new_fields) if old_fields else {}
        if changes:
            from apps.core.models import AuditLog

            AuditLog.objects.create(
                model_name=get_model_name(self),
                record_id=str(self.pk),
                action="update",
                changes=changes,
                user=get_audit_user(),
                ip_address=get_audit_ip(),
                company=getattr(self, "company", None),
            )

    def delete(self, *args, **kwargs):
        if not getattr(self, "_audit_enabled", True):
            super().delete(*args, **kwargs)
            return

        old_fields = get_field_dict(self)
        record_pk = str(self.pk)
        super().delete(*args, **kwargs)
        changes = {
            k: {"old": v, "new": None}
            for k, v in old_fields.items()
            if k not in AUDIT_EXCLUDE_FIELDS
        }
        from apps.core.models import AuditLog

        AuditLog.objects.create(
            model_name=get_model_name(self),
            record_id=record_pk,
            action="delete",
            changes=changes,
            user=get_audit_user(),
            ip_address=get_audit_ip(),
            company=getattr(self, "company", None),
        )

    def _create_audit_entry(self, action: str):
        """Create an audit log entry for this instance."""
        from apps.core.models import AuditLog

        fields = get_field_dict(self)
        changes = {
            k: {"old": None, "new": v}
            for k, v in fields.items()
            if k not in AUDIT_EXCLUDE_FIELDS
        }
        AuditLog.objects.create(
            model_name=get_model_name(self),
            record_id=str(self.pk),
            action=action,
            changes=changes,
            user=get_audit_user(),
            ip_address=get_audit_ip(),
            company=getattr(self, "company", None),
        )


class AuditConfigMixin(models.Model):
    """Mixin that auto-tracks configuration changes on config models.

    Usage:
        class WorkflowDefinition(AuditConfigMixin, ConcurrencyModel):
            ...

    Logs changes as 'config' category in the audit log.
    Does NOT extend AuditModelMixin's CRUD behavior — only config-specific logging.
    """

    _audit_config_enabled = True

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        if is_new or not getattr(self, "_audit_config_enabled", True):
            super().save(*args, **kwargs)
            if is_new and getattr(self, "_audit_config_enabled", True):
                self._create_config_audit_entry("create")
            return

        if self.pk:
            try:
                old_instance = self.__class__.objects.get(pk=self.pk)
                old_fields = get_field_dict(old_instance)
            except self.__class__.DoesNotExist:
                old_fields = {}

        super().save(*args, **kwargs)

        if not getattr(self, "_audit_config_enabled", True):
            return

        new_fields = get_field_dict(self)
        changes = compute_changes(old_fields, new_fields) if old_fields else {}
        if changes:
            from apps.core.models import AuditLog

            AuditLog.objects.create(
                model_name=get_model_name(self),
                record_id=str(self.pk),
                action="update",
                category="config",
                changes=changes,
                user=get_audit_user(),
                ip_address=get_audit_ip(),
                company=getattr(self, "company", None),
            )

    def delete(self, *args, **kwargs):
        if not getattr(self, "_audit_config_enabled", True):
            super().delete(*args, **kwargs)
            return

        old_fields = get_field_dict(self)
        record_pk = str(self.pk)
        super().delete(*args, **kwargs)
        changes = {
            k: {"old": v, "new": None}
            for k, v in old_fields.items()
            if k not in AUDIT_EXCLUDE_FIELDS
        }
        from apps.core.models import AuditLog

        AuditLog.objects.create(
            model_name=get_model_name(self),
            record_id=record_pk,
            action="delete",
            category="config",
            changes=changes,
            user=get_audit_user(),
            ip_address=get_audit_ip(),
            company=getattr(self, "company", None),
        )

    def _create_config_audit_entry(self, action: str):
        from apps.core.models import AuditLog

        fields = get_field_dict(self)
        changes = {
            k: {"old": None, "new": v}
            for k, v in fields.items()
            if k not in AUDIT_EXCLUDE_FIELDS
        }
        AuditLog.objects.create(
            model_name=get_model_name(self),
            record_id=str(self.pk),
            action=action,
            category="config",
            changes=changes,
            user=get_audit_user(),
            ip_address=get_audit_ip(),
            company=getattr(self, "company", None),
        )
