"""Data migration: copy old NumberingSeries into NumberingSeriesPolicy + CompanyNumberingSeries."""

from django.db import migrations
from django.utils import timezone


def migrate_data(apps, schema_editor):
    OldSeries = apps.get_model("core", "NumberingSeries")
    Policy = apps.get_model("core", "NumberingSeriesPolicy")
    Assignment = apps.get_model("core", "CompanyNumberingSeries")

    for old in OldSeries.objects.select_related("company").all():
        policy, _ = Policy.objects.get_or_create(
            document_type=old.document_type,
            defaults={
                "prefix": old.prefix,
                "date_format": old.date_format,
                "padding": old.padding,
                "description": old.description,
                "is_active": old.is_active,
            },
        )
        Assignment.objects.get_or_create(
            policy=policy,
            company=old.company,
            defaults={
                "next_number": old.next_number,
                "reset_period": old.reset_period,
                "last_reset_at": old.last_reset_at or timezone.now(),
                "is_active": old.is_active,
            },
        )


def reverse_data(apps, schema_editor):
    apps.get_model("core", "CompanyNumberingSeries").objects.all().delete()
    apps.get_model("core", "NumberingSeriesPolicy").objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0011_numberingseriespolicy_companynumberingseries"),
    ]

    operations = [
        migrations.RunPython(migrate_data, reverse_data),
    ]
