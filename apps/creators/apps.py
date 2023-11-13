from django.apps import AppConfig


class CreatorsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.creators'

    def ready(self):
        import apps.creators.signals  # noqa: F401 PLC0415
