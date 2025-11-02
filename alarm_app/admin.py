"""
Django admin configuration for Smart Alarm models.
"""

from django.contrib import admin
from .models import (
    UserProfile,
    NewsSource,
    WeatherLocation,
    Quote,
    Routine,
    AudioFile,
    RoutineLog,
)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ["user_name", "default_location_name", "greeting_enabled"]
    fieldsets = (
        ("User Information", {"fields": ("user_name",)}),
        (
            "Default Location",
            {
                "fields": (
                    "default_location_name",
                    "default_latitude",
                    "default_longitude",
                )
            },
        ),
        ("Text-to-Speech", {"fields": ("tts_command",)}),
        ("Greeting", {"fields": ("greeting_enabled", "greeting_text")}),
    )


@admin.register(NewsSource)
class NewsSourceAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "active", "created_at"]
    list_filter = ["category", "active"]
    search_fields = ["name", "rss_url"]
    ordering = ["category", "name"]


@admin.register(WeatherLocation)
class WeatherLocationAdmin(admin.ModelAdmin):
    list_display = ["name", "city", "state", "latitude", "longitude"]
    list_filter = ["state"]
    search_fields = ["name", "city", "state"]


@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display = ["text_preview", "author", "category", "active"]
    list_filter = ["category", "active"]
    search_fields = ["text", "author"]

    def text_preview(self, obj):
        return obj.text[:100] + "..." if len(obj.text) > 100 else obj.text

    text_preview.short_description = "Quote"


@admin.register(Routine)
class RoutineAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "enabled",
        "schedule_type",
        "time_of_day",
        "last_run",
        "run_count",
    ]
    list_filter = ["enabled", "schedule_type"]
    search_fields = ["name", "description"]

    fieldsets = (
        ("Basic Information", {"fields": ("name", "description", "enabled")}),
        (
            "Schedule",
            {
                "fields": (
                    "schedule_type",
                    "scheduled_datetime",
                    "time_of_day",
                    ("monday", "tuesday", "wednesday", "thursday"),
                    ("friday", "saturday", "sunday"),
                )
            },
        ),
        (
            "Steps Configuration",
            {
                "fields": ("steps_json",),
                "description": "JSON array of step configurations",
            },
        ),
        ("Statistics", {"fields": ("last_run", "run_count"), "classes": ("collapse",)}),
    )

    readonly_fields = ["last_run", "run_count"]


@admin.register(AudioFile)
class AudioFileAdmin(admin.ModelAdmin):
    list_display = ["name", "duration_seconds", "created_at"]
    search_fields = ["name"]


@admin.register(RoutineLog)
class RoutineLogAdmin(admin.ModelAdmin):
    list_display = [
        "routine",
        "started_at",
        "status",
        "duration_display",
        "error_preview",
    ]
    list_filter = ["status", "started_at"]
    search_fields = ["routine__name"]
    readonly_fields = [
        "routine",
        "started_at",
        "completed_at",
        "status",
        "error_message",
        "step_details",
    ]

    def duration_display(self, obj):
        duration = obj.duration_seconds()
        if duration:
            return f"{duration:.1f}s"
        return "-"

    duration_display.short_description = "Duration"

    def error_preview(self, obj):
        if obj.error_message:
            return (
                obj.error_message[:100] + "..."
                if len(obj.error_message) > 100
                else obj.error_message
            )
        return "-"

    error_preview.short_description = "Error"

    def has_add_permission(self, request):
        # Logs are created automatically, not manually
        return False
