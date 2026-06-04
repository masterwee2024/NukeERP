"""Seed command — register known industry module configurations."""

from django.core.management.base import BaseCommand

from apps.core.platform.module_registry import registry


class Command(BaseCommand):
    help = "Register seed industry module configurations"

    def handle(self, *args, **options):
        modules = [
            {
                "name": "Property Management",
                "code": "property",
                "version": "1.0.0",
                "description": "Lease management, tenant management, utility billing",
                "dependencies": [],
                "menu_items": [],
                "signals_emitted": [
                    "tenant.registered",
                    "lease.signed",
                    "rent.invoice.created",
                ],
                "signals_handled": [
                    "invoice.posted",
                    "payment.received",
                ],
            },
        ]

        for cfg in modules:
            code = cfg["code"]
            try:
                registry.register_module(cfg)
                self.stdout.write(self.style.SUCCESS(f"Module registered: {code}"))
            except ValueError as exc:
                self.stdout.write(self.style.WARNING(f"Skip {code}: {exc}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"{len(modules)} module(s) registered, "
                f"{len(registry.get_all_modules())} total"
            )
        )
