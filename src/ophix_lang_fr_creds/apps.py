from django.apps import AppConfig


class OphixLangFrCredsConfig(AppConfig):
    name = "ophix_lang_fr_creds"
    verbose_name = "Ophix French — Credentials"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        from django.db.models.signals import post_migrate
        post_migrate.connect(_import_docs, sender=self)


def _import_docs(sender, **kwargs):
    """Auto-import French translated docs after migration."""
    try:
        from django.core.management import call_command
        call_command(
            "ophix_docs_update",
            include_app_docs="ophix_lang_fr_creds",
            language="fr",
            verbosity=0,
        )
    except Exception:
        pass
