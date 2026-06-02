import django; django.setup()
from apps.core.models import EmailSetting
s = EmailSetting.load()
print("PK:", s.pk, "Host:", repr(s.smtp_host))
s.smtp_host = "test.example.com"
s.save()
s2 = EmailSetting.load()
print("Reloaded Host:", repr(s2.smtp_host))
print("Same PK:", s.pk == s2.pk)
