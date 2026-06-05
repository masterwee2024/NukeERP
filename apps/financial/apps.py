from django.apps import AppConfig


class FinancialConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.financial"
    verbose_name = "Financial"

    def ready(self):
        from apps.financial.signals import connect_signals  # noqa: F401

        connect_signals()
