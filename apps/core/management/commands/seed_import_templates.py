"""Seed command — create predefined import templates."""

from django.core.management.base import BaseCommand

from apps.core.services.import_service import seed_templates


class Command(BaseCommand):
    help = "Create predefined import templates (COA, items, customers, vendors, employees, etc.)"

    def handle(self, *args, **options):
        seed_templates()
        self.stdout.write(self.style.SUCCESS("Import templates seeded successfully"))
