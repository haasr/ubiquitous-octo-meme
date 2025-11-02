"""
Django app configuration for alarm_app.
"""

from django.apps import AppConfig


class AlarmAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "alarm_app"
    verbose_name = "Smart Alarm System"

    def ready(self):
        """
        Called when Django starts.
        We DON'T start the scheduler here because it would access the database.
        Instead, the scheduler is started via middleware on the first request.
        """
        pass
