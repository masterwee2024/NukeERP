"""Seed command to create a default company."""

from django.core.management.base import BaseCommand

from apps.core.models import Company


class Command(BaseCommand):
    help = "Create a default company for development"

    def handle(self, *args, **options):
        if Company.objects.filter(code="DEFAULT").exists():
            self.stdout.write("Default company already exists")
            return

        Company.objects.create(
            name="Default Company",
            code="DEFAULT",
            registration_number="123456-A",
            is_active=True,
            base_currency="MYR",
            date_format="Y-m-d",
            timezone="Asia/Kuala_Lumpur",
            country="MY",
        )
        self.stdout.write(self.style.SUCCESS("Default company created"))
