from django.apps import AppConfig


class AccountingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.accounting'

    def ready(self):
        # Registrar las señales post_save de AccountMovement (Plan 04, item 2).
        from . import signals  # noqa: F401
