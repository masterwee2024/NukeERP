"""Base model mixins — TimeStampedModel, CustomFieldsMixin, ConcurrencyModel, ConcurrencyError."""

import uuid

from django.db import models

from apps.core.mixins.audit_mixin import AuditModelMixin


class ConcurrencyError(Exception):
    """Raised when optimistic locking detects a conflict."""

    pass


class TimeStampedModel(models.Model):
    """Abstract base that adds created_at and updated_at to every model."""

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class CustomFieldsMixin(models.Model):
    """Adds a `custom_fields` JSONB column and routes unknown field values into it.

    Subclasses get:
    - `custom_fields` JSONField – stores any field value whose name does not match a
      model column (user-defined custom fields).
    - `set_field(name, value)` – sets a value on the model field if the name matches
      a column, otherwise stores it in `custom_fields`.
    - `get_field(name)` – reads from model field or `custom_fields`.
    - `split_payload(data)` – splits a flat dict into (model_fields, custom_fields)
      dicts for use in service/API create paths.
    """

    custom_fields = models.JSONField(default=dict, blank=True)

    class Meta:
        abstract = True

    @classmethod
    def _model_field_names(cls):
        names = set()
        for f in cls._meta.get_fields():
            if f.is_relation and (f.many_to_many or f.one_to_many):
                continue
            if hasattr(f, "column") and f.column is not None:
                names.add(f.attname)
                if f.name != f.attname:
                    names.add(f.name)
        names.discard("custom_fields")
        return names

    def __init__(self, *args, **kwargs):
        model_fields = self._model_field_names()
        model_kw = {}
        custom_kw = {}
        explicit_custom = kwargs.pop("custom_fields", {})
        for k, v in kwargs.items():
            (model_kw if k in model_fields else custom_kw)[k] = v
        super().__init__(*args, **model_kw)
        merged = {**explicit_custom, **custom_kw}
        if merged:
            self.custom_fields = merged

    def set_field(self, name, value):
        if name in self._model_field_names():
            setattr(self, name, value)
        else:
            current = dict(self.custom_fields) if self.custom_fields else {}
            current[name] = value
            self.custom_fields = current

    def get_field(self, name):
        if name in self._model_field_names():
            return getattr(self, name)
        return (self.custom_fields or {}).get(name)

    @classmethod
    def split_payload(cls, data: dict) -> tuple[dict, dict]:
        model_fields = cls._model_field_names()
        model_data = {}
        custom_data = {}
        for k, v in data.items():
            (model_data if k in model_fields else custom_data)[k] = v
        return model_data, custom_data


class ConcurrencyModel(AuditModelMixin, CustomFieldsMixin, TimeStampedModel):
    """Abstract base with concurrency control and custom fields support.

    Every model MUST inherit from this. Provides:
    - id: UUID primary key
    - created_at, updated_at: from TimeStampedModel
    - version: optimistic locking field (auto-increments on save)
    - custom_fields: JSONB column for user-defined fields
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self.pk:
            try:
                original = self.__class__.objects.get(pk=self.pk)
                if original.version != self.version:
                    raise ConcurrencyError(
                        "Record was modified by another user. Please reload and try again."
                    )
                self.version += 1
            except self.__class__.DoesNotExist:
                pass
        super().save(*args, **kwargs)
