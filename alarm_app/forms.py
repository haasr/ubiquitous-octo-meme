"""
Django forms for the Smart Alarm application.
"""

from django import forms
from django.core.exceptions import ValidationError
import json

from .models import Routine, UserProfile


class RoutineForm(forms.ModelForm):
    """
    Form for creating and editing routines.
    """

    class Meta:
        model = Routine
        fields = [
            "name",
            "description",
            "enabled",
            "schedule_type",
            "scheduled_datetime",
            "time_of_day",
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
            "steps_json",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Morning Wake-up Routine",
                    "style": "width: 100%; padding: 0.75rem; border: 1px solid #ddd; border-radius: 5px; font-size: 1rem;",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "A comprehensive morning routine to start the day...",
                    "style": "width: 100%; padding: 0.75rem; border: 1px solid #ddd; border-radius: 5px; font-size: 1rem;",
                }
            ),
            "enabled": forms.CheckboxInput(
                attrs={
                    "style": "width: 20px; height: 20px; cursor: pointer;",
                }
            ),
            "scheduled_datetime": forms.DateTimeInput(
                attrs={
                    "type": "datetime-local",
                    "class": "form-control",
                    "style": "width: 100%; padding: 0.75rem; border: 1px solid #ddd; border-radius: 5px; font-size: 1rem;",
                }
            ),
            "time_of_day": forms.TimeInput(
                attrs={
                    "type": "time",
                    "class": "form-control",
                    "style": "width: 100%; padding: 0.75rem; border: 1px solid #ddd; border-radius: 5px; font-size: 1rem;",
                }
            ),
            "monday": forms.CheckboxInput(
                attrs={"style": "width: 20px; height: 20px; cursor: pointer;"}
            ),
            "tuesday": forms.CheckboxInput(
                attrs={"style": "width: 20px; height: 20px; cursor: pointer;"}
            ),
            "wednesday": forms.CheckboxInput(
                attrs={"style": "width: 20px; height: 20px; cursor: pointer;"}
            ),
            "thursday": forms.CheckboxInput(
                attrs={"style": "width: 20px; height: 20px; cursor: pointer;"}
            ),
            "friday": forms.CheckboxInput(
                attrs={"style": "width: 20px; height: 20px; cursor: pointer;"}
            ),
            "saturday": forms.CheckboxInput(
                attrs={"style": "width: 20px; height: 20px; cursor: pointer;"}
            ),
            "sunday": forms.CheckboxInput(
                attrs={"style": "width: 20px; height: 20px; cursor: pointer;"}
            ),
            "steps_json": forms.HiddenInput(),
        }

    def clean_steps_json(self):
        """
        Validate the steps JSON data.
        """
        steps_json = self.cleaned_data.get("steps_json")

        # If it's a string, try to parse it
        if isinstance(steps_json, str):
            try:
                steps_json = json.loads(steps_json)
            except json.JSONDecodeError:
                raise ValidationError("Invalid JSON format for steps")

        # Ensure it's a list
        if not isinstance(steps_json, list):
            raise ValidationError("Steps must be a list")

        # Validate each step
        for i, step in enumerate(steps_json):
            if not isinstance(step, dict):
                raise ValidationError(f"Step {i+1} must be a dictionary")

            if "type" not in step:
                raise ValidationError(f"Step {i+1} is missing 'type' field")

            if "config" not in step:
                step["config"] = {}

        return steps_json

    def clean(self):
        """
        Validate the entire form.
        """
        cleaned_data = super().clean()
        schedule_type = cleaned_data.get("schedule_type")

        # Validate one-time schedule
        if schedule_type == "once":
            scheduled_datetime = cleaned_data.get("scheduled_datetime")
            if not scheduled_datetime:
                raise ValidationError(
                    {"scheduled_datetime": "Scheduled date/time is required for one-time routines"}
                )

        # Validate recurring schedule
        elif schedule_type == "recurring":
            time_of_day = cleaned_data.get("time_of_day")
            if not time_of_day:
                raise ValidationError(
                    {"time_of_day": "Time of day is required for recurring routines"}
                )

            # Check if at least one day is selected
            days = [
                cleaned_data.get("monday"),
                cleaned_data.get("tuesday"),
                cleaned_data.get("wednesday"),
                cleaned_data.get("thursday"),
                cleaned_data.get("friday"),
                cleaned_data.get("saturday"),
                cleaned_data.get("sunday"),
            ]

            if not any(days):
                raise ValidationError(
                    "At least one day of the week must be selected for recurring routines"
                )

        return cleaned_data


class UserProfileForm(forms.ModelForm):
    """
    Form for editing user profile settings.
    """

    class Meta:
        model = UserProfile
        fields = [
            "user_name",
            "default_location_name",
            "default_latitude",
            "default_longitude",
            "tts_command",
            "greeting_enabled",
            "greeting_text",
        ]
        widgets = {
            "user_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Your Name",
                    "style": "width: 100%; padding: 0.75rem; border: 1px solid #ddd; border-radius: 5px; font-size: 1rem;",
                }
            ),
            "default_location_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Johnson City, TN",
                    "style": "width: 100%; padding: 0.75rem; border: 1px solid #ddd; border-radius: 5px; font-size: 1rem;",
                }
            ),
            "default_latitude": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "36.3406",
                    "step": "0.000001",
                    "style": "width: 100%; padding: 0.75rem; border: 1px solid #ddd; border-radius: 5px; font-size: 1rem;",
                }
            ),
            "default_longitude": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "-82.3804",
                    "step": "0.000001",
                    "style": "width: 100%; padding: 0.75rem; border: 1px solid #ddd; border-radius: 5px; font-size: 1rem;",
                }
            ),
            "tts_command": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "style": "width: 100%; padding: 0.75rem; border: 1px solid #ddd; border-radius: 5px; font-family: monospace; font-size: 0.95rem;",
                }
            ),
            "greeting_enabled": forms.CheckboxInput(
                attrs={"style": "width: 20px; height: 20px; cursor: pointer;"}
            ),
            "greeting_text": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Good morning, {name}!",
                    "style": "width: 100%; padding: 0.75rem; border: 1px solid #ddd; border-radius: 5px; font-size: 1rem;",
                }
            ),
        }
