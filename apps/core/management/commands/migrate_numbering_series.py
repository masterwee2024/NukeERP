"""Migrate old NumberingSeries records to new NumberingSeriesPolicy + CompanyNumberingSeries."""

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.core.models import (
    CompanyNumberingSeries,
    NumberingSeries,
    NumberingSeriesPolicy,
)


class Command(BaseCommand):
    help = "Migrate old NumberingSeries records to the new policy + assignment model"

    def handle(self, *args, **options):
        old_count = NumberingSeries.objects.count()
        if old_count == 0:
            self.stdout.write("No old NumberingSeries records to migrate.")
            return

        created_policies = 0
        created_assignments = 0
        skipped = 0

        for old in NumberingSeries.objects.select_related("company").all():
            policy, was_policy_created = NumberingSeriesPolicy.objects.get_or_create(
                document_type=old.document_type,
                defaults={
                    "prefix": old.prefix,
                    "date_format": old.date_format,
                    "padding": old.padding,
                    "description": old.description,
                    "is_active": old.is_active,
                },
            )
            if was_policy_created:
                created_policies += 1

            _, was_assignment_created = CompanyNumberingSeries.objects.get_or_create(
                policy=policy,
                company=old.company,
                defaults={
                    "next_number": old.next_number,
                    "reset_period": old.reset_period,
                    "last_reset_at": old.last_reset_at or timezone.now(),
                    "is_active": old.is_active,
                },
            )
            if was_assignment_created:
                created_assignments += 1
            else:
                skipped += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Migrated {old_count} old records → "
                f"{created_policies} policies, {created_assignments} assignments "
                f"({skipped} existing assignments skipped)."
            )
        )
