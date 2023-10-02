from django.apps import AppConfig


class CreatorsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.creators'

    def ready(self):  # noqa: PLR6301
        import apps.creators.signals  # noqa: F401
