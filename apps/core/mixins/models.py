"""Base model mixins — TimeStampedModel, ConcurrencyModel, ConcurrencyError."""

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


class ConcurrencyModel(AuditModelMixin, TimeStampedModel):
    """Abstract base with concurrency control fields.

    Every model MUST inherit from this. Provides:
    - id: UUID primary key
    - created_at, updated_at: from TimeStampedModel
    - version: optimistic locking field (auto-increments on save)
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
