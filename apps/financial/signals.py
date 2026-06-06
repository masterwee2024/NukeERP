"""Signal handlers for the financial app."""

import logging

from django.db.models.signals import post_save

from apps.core.models import DOC_TYPE_JOURNAL_ENTRY
from apps.financial.services.posting_service import approve_submitted_entry

logger = logging.getLogger(__name__)


def on_workflow_completed(sender, instance, created, raw, update_fields, **kwargs):
    """Auto-approve journal entries when their workflow completes."""
    if raw:
        return
    if instance.status != "completed":
        return
    if instance.document_type != DOC_TYPE_JOURNAL_ENTRY:
        return
    try:
        approve_submitted_entry(instance.document_id)
        logger.info(
            "Journal entry %s auto-approved on workflow %s completion",
            instance.document_id,
            instance.id,
        )
    except Exception as exc:
        logger.error(
            "Failed to auto-approve journal entry %s: %s",
            instance.document_id,
            exc,
        )


def connect_signals():
    """Connect workflow completion signal to auto-approve journal entries."""
    from django.apps import apps

    WorkflowExecution = apps.get_model("core", "WorkflowExecution")
    post_save.connect(on_workflow_completed, sender=WorkflowExecution, weak=False)
