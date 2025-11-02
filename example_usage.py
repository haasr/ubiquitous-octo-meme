#!/usr/bin/env python3
"""
Example script demonstrating the Smart Alarm system.

This shows how to create and execute routines programmatically
without using the Django web interface.
"""

import sys
import os

# Add the alarm_app to the path
sys.path.insert(0, os.path.dirname(__file__))

from alarm_app.routine import Routine
from alarm_app.routine_steps import Alarm, News, WeatherUtil, URLOpener, QuoteFetcher


def example_basic_routine():
    """
    Example 1: Create and execute a basic routine with individual steps.
    """
    print("=" * 60)
    print("EXAMPLE 1: Basic Routine with Manual Step Creation")
    print("=" * 60)

    # Create individual steps
    alarm = Alarm(
        config={"audio_file": "/usr/share/sounds/alsa/Front_Center.wav", "duration": 5}
    )

    weather = WeatherUtil(
        config={
            "latitude": "36.3406",
            "longitude": "-82.3804",
            "location_name": "Johnson City",
        }
    )

    quote = QuoteFetcher(
        config={"intro_text": "Here is your inspirational quote for today"}
    )

    # Validate each step
    steps = [alarm, weather, quote]
    for step in steps:
        is_valid, error = step.validate_config()
        if not is_valid:
            print(f"❌ {step.__class__.__name__} validation failed: {error}")
        else:
            print(f"✓ {step.__class__.__name__} configuration is valid")

    print(
        "\n[Note: This would execute the routine, but we're skipping actual execution in demo mode]\n"
    )


def example_json_configuration():
    """
    Example 2: Create routine from JSON configuration (Django model format).
    """
    print("=" * 60)
    print("EXAMPLE 2: Routine from JSON Configuration")
    print("=" * 60)

    routine_config = {
        "name": "Comprehensive Morning Routine",
        "steps": [
            {
                "type": "alarm",
                "config": {
                    "audio_file": "/usr/share/sounds/alsa/Front_Center.wav",
                    "duration": 30,
                },
            },
            {
                "type": "weather",
                "config": {
                    "latitude": "36.3406",
                    "longitude": "-82.3804",
                    "location_name": "Johnson City, TN",
                },
            },
            {
                "type": "news",
                "config": {
                    "rss_url": "https://www.theguardian.com/world/rss",
                    "num_images": 6,
                },
            },
            {"type": "quote", "config": {"intro_text": "Your quote of the day is"}},
            {
                "type": "url_opener",
                "config": {
                    "url": "https://en.wikipedia.org/wiki/Main_Page",
                    "message": "Opening your daily reading",
                },
            },
        ],
    }

    # Create routine from config
    routine = Routine.from_dict(routine_config)

    print(f"Routine Name: {routine.name}")
    print(f"Number of Steps: {len(routine.steps)}")
    print("\nSteps:")
    for i, step in enumerate(routine.steps, 1):
        print(f"  {i}. {step.__class__.__name__}")

    # Validate the routine
    print("\nValidating routine...")
    is_valid, errors = routine.validate()

    if is_valid:
        print("✓ Routine is valid and ready to execute!")
    else:
        print("❌ Routine has validation errors:")
        for error in errors:
            print(f"   - {error}")

    # Show JSON representation
    print("\nJSON Representation:")
    print(routine.to_json())

    print("\n[Note: Would execute with routine.start(blocking=True)]\n")


def example_step_customization():
    """
    Example 3: Demonstrate step configuration options.
    """
    print("=" * 60)
    print("EXAMPLE 3: Step Configuration Options")
    print("=" * 60)

    # Weather step with all options
    weather_config = {
        "latitude": "40.7128",
        "longitude": "-74.0060",
        "location_name": "New York City",
        "tts_command": 'espeak "{text}"',  # Alternative TTS
    }

    print("\n1. Weather Step Configuration:")
    print(f"   Location: {weather_config['location_name']}")
    print(
        f"   Coordinates: {weather_config['latitude']}, {weather_config['longitude']}"
    )
    print(f"   TTS Command: {weather_config['tts_command']}")

    # News step options
    news_config = {
        "rss_url": "https://feeds.bbci.co.uk/news/world/rss.xml",
        "num_images": 8,
        "tts_command": 'simple_google_tts -p en "{text}"',
    }

    print("\n2. News Step Configuration:")
    print(f"   RSS Feed: {news_config['rss_url']}")
    print(f"   Images to Download: {news_config['num_images']}")

    # URL opener with custom message
    url_config = {
        "url": "https://github.com/trending",
        "message": "Opening trending GitHub repositories for your daily tech update",
    }

    print("\n3. URL Opener Configuration:")
    print(f"   URL: {url_config['url']}")
    print(f"   Message: {url_config['message']}")

    print()


def example_routine_registry():
    """
    Example 4: Show available routine step types.
    """
    print("=" * 60)
    print("EXAMPLE 4: Available Routine Step Types")
    print("=" * 60)

    from alarm_app.routine_steps import ROUTINE_STEP_REGISTRY

    print("\nRegistered Step Types:")
    for step_type, step_class in ROUTINE_STEP_REGISTRY.items():
        print(f"\n  '{step_type}' -> {step_class.__name__}")
        print(f"     {step_class.__doc__.strip()}")


def example_error_handling():
    """
    Example 5: Demonstrate validation and error handling.
    """
    print("=" * 60)
    print("EXAMPLE 5: Validation and Error Handling")
    print("=" * 60)

    # Create routine with invalid configuration
    invalid_config = {
        "name": "Invalid Routine",
        "steps": [
            {
                "type": "alarm",
                "config": {
                    # Missing required 'audio_file'
                    "duration": 30
                },
            },
            {
                "type": "weather",
                "config": {
                    # Missing required coordinates
                    "location_name": "Somewhere"
                },
            },
            {"type": "unknown_type", "config": {}},  # Invalid step type
        ],
    }

    routine = Routine.from_dict(invalid_config)

    print(f"Routine: {routine.name}")
    print(f"Attempting to validate...\n")

    is_valid, errors = routine.validate()

    if not is_valid:
        print("❌ Validation failed with the following errors:")
        for error in errors:
            print(f"   • {error}")

    print("\nThis demonstrates how the system catches configuration errors")
    print("before attempting execution, preventing runtime failures.\n")


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("SMART ALARM SYSTEM - EXAMPLE DEMONSTRATIONS")
    print("=" * 60 + "\n")

    examples = [
        example_basic_routine,
        example_json_configuration,
        example_step_customization,
        example_routine_registry,
        example_error_handling,
    ]

    for example_func in examples:
        example_func()
        input("Press Enter to continue to next example...")
        print()

    print("=" * 60)
    print("Examples completed!")
    print("\nTo use this system with Django:")
    print("1. Configure routines via Django admin or web interface")
    print("2. Scheduler will automatically trigger routines at scheduled times")
    print("3. View execution logs and history in the admin panel")
    print("=" * 60)


if __name__ == "__main__":
    main()
