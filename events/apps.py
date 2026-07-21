from django.apps import AppConfig
import os

class EventsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'events'

    def ready(self):
        try:
            from django.conf import settings
            for folder in ['event_banners', 'certificate_templates', 'certificates']:
                os.makedirs(os.path.join(settings.MEDIA_ROOT, folder), exist_ok=True)
        except Exception:
            pass
