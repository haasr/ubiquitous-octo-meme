"""
Django models for Smart Alarm application.
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import json


class UserProfile(models.Model):
    """
    User profile storing default settings and preferences.
    """

    # Singleton pattern - only one profile per system
    user_name = models.CharField(max_length=100, default="User")

    # Default weather location
    default_location_name = models.CharField(max_length=200, default="Johnson City")
    default_latitude = models.DecimalField(
        max_digits=9, decimal_places=6, default=36.3406
    )
    default_longitude = models.DecimalField(
        max_digits=9, decimal_places=6, default=-82.3804
    )

    # TTS configuration
    tts_command = models.CharField(
        max_length=500,
        default='simple_google_tts -p en "{text}"',
        help_text="TTS command template. Use {text} as placeholder for the text to speak.",
    )

    # Greeting settings
    greeting_enabled = models.BooleanField(default=True)
    greeting_text = models.CharField(
        max_length=200,
        default="Good morning, {name}!",
        help_text="Greeting template. Use {name} as placeholder.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profile"

    def __str__(self):
        return f"Profile for {self.user_name}"

    @classmethod
    def get_profile(cls):
        """Get or create the singleton profile."""
        profile, created = cls.objects.get_or_create(pk=1)
        return profile


class NewsSource(models.Model):
    """
    RSS news sources organized by category.
    """

    name = models.CharField(max_length=200)
    rss_url = models.URLField(max_length=500)
    category = models.CharField(
        max_length=100,
        default="General",
        help_text="Category like 'World', 'Technology', 'Sports', etc.",
    )
    active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["category", "name"]

    def __str__(self):
        return f"{self.name} ({self.category})"


class WeatherLocation(models.Model):
    """
    Saved weather locations for quick access.
    """

    name = models.CharField(max_length=200)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["state", "city"]
        unique_together = ["latitude", "longitude"]

    def __str__(self):
        return f"{self.city}, {self.state}"


class Quote(models.Model):
    """
    Inspirational quotes for daily rotation.
    """

    text = models.TextField()
    author = models.CharField(max_length=200, blank=True)
    category = models.CharField(
        max_length=100,
        blank=True,
        help_text="Optional category like 'Motivational', 'Programming', etc.",
    )
    active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["?"]  # Random ordering for variety

    def __str__(self):
        if self.author:
            return f'"{self.text[:50]}..." - {self.author}'
        return f'"{self.text[:50]}..."'

    @classmethod
    def get_random_quote(cls):
        """Get a random active quote."""
        return cls.objects.filter(active=True).order_by("?").first()


class Routine(models.Model):
    """
    A routine is a scheduled sequence of steps (alarm, news, weather, etc.).
    """

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    # Steps stored as JSON
    # Format: [{'type': 'alarm', 'config': {...}}, ...]
    steps_json = models.JSONField(
        default=list, help_text="List of step configurations in JSON format"
    )

    # Scheduling
    enabled = models.BooleanField(default=True)

    # Schedule type: 'once' or 'recurring'
    schedule_type = models.CharField(
        max_length=20,
        choices=[("once", "One-time"), ("recurring", "Recurring")],
        default="recurring",
    )

    # For one-time schedules
    scheduled_datetime = models.DateTimeField(
        null=True, blank=True, help_text="Specific date/time for one-time execution"
    )

    # For recurring schedules
    time_of_day = models.TimeField(
        null=True, blank=True, help_text="Time of day for recurring execution"
    )

    # Days of week for recurring schedules (0=Monday, 6=Sunday)
    monday = models.BooleanField(default=False)
    tuesday = models.BooleanField(default=False)
    wednesday = models.BooleanField(default=False)
    thursday = models.BooleanField(default=False)
    friday = models.BooleanField(default=False)
    saturday = models.BooleanField(default=False)
    sunday = models.BooleanField(default=False)

    # Tracking
    last_run = models.DateTimeField(null=True, blank=True)
    run_count = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def get_scheduled_days(self):
        """Get list of day names when this routine is scheduled."""
        days = []
        day_mapping = [
            (self.monday, "Monday"),
            (self.tuesday, "Tuesday"),
            (self.wednesday, "Wednesday"),
            (self.thursday, "Thursday"),
            (self.friday, "Friday"),
            (self.saturday, "Saturday"),
            (self.sunday, "Sunday"),
        ]
        for enabled, name in day_mapping:
            if enabled:
                days.append(name)
        return days

    def is_scheduled_today(self):
        """Check if routine is scheduled for today."""
        if not self.enabled:
            return False

        if self.schedule_type == "once":
            if self.scheduled_datetime:
                return self.scheduled_datetime.date() == timezone.now().date()
            return False

        # Recurring schedule
        weekday = timezone.now().weekday()  # 0=Monday, 6=Sunday
        day_flags = [
            self.monday,
            self.tuesday,
            self.wednesday,
            self.thursday,
            self.friday,
            self.saturday,
            self.sunday,
        ]
        return day_flags[weekday]

    def mark_as_run(self):
        """Mark this routine as having been run."""
        self.last_run = timezone.now()
        self.run_count += 1
        self.save(update_fields=["last_run", "run_count"])

    def to_routine_config(self):
        """Convert to format expected by Routine class."""
        return {"name": self.name, "steps": self.steps_json}


class AudioFile(models.Model):
    """
    Uploaded audio files for alarms.
    """

    name = models.CharField(max_length=200)
    file = models.FileField(upload_to="audio/")
    duration_seconds = models.IntegerField(
        null=True,
        blank=True,
        help_text="Duration in seconds (auto-detected if possible)",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class RoutineLog(models.Model):
    """
    Log of routine executions for debugging and monitoring.
    """

    routine = models.ForeignKey(Routine, on_delete=models.CASCADE, related_name="logs")

    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=[
            ("started", "Started"),
            ("completed", "Completed"),
            ("failed", "Failed"),
            ("stopped", "Stopped"),
        ],
    )

    error_message = models.TextField(blank=True)

    # Details about each step execution
    step_details = models.JSONField(
        default=dict, help_text="Details about each step's execution"
    )

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.routine.name} - {self.started_at.strftime('%Y-%m-%d %H:%M')} - {self.status}"

    def duration_seconds(self):
        """Calculate duration of execution."""
        if self.completed_at and self.started_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
