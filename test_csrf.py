import django; import os; os.environ['DJANGO_SETTINGS_MODULE'] = 'pyerp.settings'; django.setup()
from django.test import Client
c = Client()
resp = c.post("/api/v1/core/admin/settings/email/test/", {"recipient": "test@test.com"}, content_type="application/json")
print("POST status:", resp.status_code, resp.content[:200])
