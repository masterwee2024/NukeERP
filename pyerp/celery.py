import os

from celery import Celery

# Set default settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pyerp.settings")

app = Celery("pyerp")

# Configure Celery using settings.py values prefixed with CELERY_
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks from all installed Django apps
app.autodiscover_tasks()
