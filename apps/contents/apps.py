from django.apps import AppConfig


class ContentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.contents'

    def ready(self):  # noqa: PLR6301
        import apps.contents.signals  # noqa: F401
