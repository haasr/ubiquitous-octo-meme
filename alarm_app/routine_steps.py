"""
Routine Step Classes for Smart Alarm System

Each RoutineStep subclass represents a distinct action that can be
performed as part of a morning routine (alarm, news, weather, etc.)
"""

from abc import ABC, abstractmethod
import subprocess
import time
import os
import re
import json
from typing import Optional, Dict, Any
import threading


class RoutineStep(ABC):
    """
    Abstract base class for all routine steps.

    Each step can be configured via a config dict, executed,
    and cleaned up. Steps are meant to be run sequentially
    in a Routine chain.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the routine step with configuration.

        Args:
            config: Dictionary containing step-specific configuration
        """
        self.config = config or {}
        self._stop_event = threading.Event()
        self._process = None

    @abstractmethod
    def execute(self) -> bool:
        """
        Execute this routine step.

        Returns:
            bool: True if execution was successful, False otherwise
        """
        pass

    def stop(self):
        """Stop execution of this step if it's running."""
        self._stop_event.set()
        if self._process and self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()

    def format_html(self) -> str:
        """
        Format this step for display in HTML.

        Returns:
            str: HTML representation of this step's output
        """
        return f"<div class='routine-step'>{self.__class__.__name__}</div>"

    def validate_config(self) -> tuple[bool, Optional[str]]:
        """
        Validate the configuration for this step.

        Returns:
            tuple: (is_valid, error_message)
        """
        return True, None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures cleanup."""
        self.stop()
        return False


class Alarm(RoutineStep):
    """
    Plays an audio file alarm.

    Config:
        audio_file (str): Path to the audio file
        duration (int, optional): Auto-stop after this many seconds
    """

    def execute(self) -> bool:
        audio_file = self.config.get("audio_file")
        duration = self.config.get("duration")

        if not audio_file or not os.path.exists(audio_file):
            print(f"Audio file not found: {audio_file}")
            return False

        try:
            # Use aplay for audio playback
            self._process = subprocess.Popen(
                ["play", audio_file],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            # Wait for duration or until stopped
            if duration:
                start_time = time.time()
                while time.time() - start_time < duration:
                    if self._stop_event.is_set():
                        break
                    time.sleep(0.1)
                self.stop()
            else:
                # Wait for process to complete
                self._process.wait()

            return True

        except Exception as e:
            print(f"Error playing alarm: {e}")
            return False

    def validate_config(self) -> tuple[bool, Optional[str]]:
        audio_file = self.config.get("audio_file")
        if not audio_file:
            return False, "audio_file is required"
        if not os.path.exists(audio_file):
            return False, f"Audio file not found: {audio_file}"
        return True, None


class News(RoutineStep):
    """
    Fetches news from RSS feed, downloads related images,
    and presents them with text-to-speech narration.

    Config:
        rss_url (str): URL of the RSS feed
        image_keywords (list, optional): Additional keywords for image search
        num_images (int): Number of images to download (default: 6)
        tts_command (str): TTS command template (default: 'simple_google_tts en "{text}"')
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.images = []
        self.news_text = ""
        self.news_title = ""

    def execute(self) -> bool:
        try:
            import feedparser

            rss_url = self.config.get("rss_url")
            if not rss_url:
                return False

            # Parse RSS feed
            feed = feedparser.parse(rss_url)

            if not feed.entries:
                print("No news articles found")
                return False

            article = feed.entries[0]
            self.news_title = article.get("title", "")

            # Extract summary and clean HTML tags
            summary = article.get("summary", "")
            summary = re.sub(r"<.*?>", "", summary)
            summary = re.sub(r'[â€œâ€"]', "", summary)
            summary = re.sub(r"Continue reading...", "", summary)

            self.news_text = f"Now, today's news: {self.news_title}. {summary}"

            # Download images based on title keywords
            self._download_images()

            # Speak the news using TTS
            self._speak_text(self.news_text)

            return True

        except Exception as e:
            print(f"Error fetching news: {e}")
            return False

    def _download_images(self):
        """Download images related to the news article."""
        try:
            from google_images_downloader import GoogleImagesDownloader

            # Extract keywords from title (simple approach: use title)
            keywords = self.news_title
            num_images = self.config.get("num_images", 6)

            # Define download destination
            images_dir = os.path.join(
                os.path.dirname(__file__), "static/alarm_app/images/news"
            )
            os.makedirs(images_dir, exist_ok=True)

            downloader = GoogleImagesDownloader(
                browser="chrome", show=False, debug=False, quiet=True
            )

            downloader.download(
                keywords,
                destination=images_dir,
                limit=num_images,
                resize=(1920, 1080),
                file_format="JPEG",
            )

            downloader.close()

            # Store list of downloaded images
            self.images = [
                f
                for f in os.listdir(images_dir)
                if f.endswith((".jpg", ".jpeg", ".png"))
            ]

        except Exception as e:
            print(f"Error downloading images: {e}")
            self.images = []

    def _speak_text(self, text: str):
        """Use TTS to speak the provided text."""
        tts_command = self.config.get("tts_command", 'simple_google_tts en "{text}"')

        # Format the command with the text
        command = tts_command.replace("{text}", text)

        try:
            self._process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self._process.wait()
        except Exception as e:
            print(f"Error with TTS: {e}")

    def format_html(self) -> str:
        """Generate HTML for displaying news with slideshow."""
        if not self.images:
            return f"<div class='news-item'><h3>{self.news_title}</h3><p>{self.news_text}</p></div>"

        image_html = "\n".join(
            [
                f'<img src="/static/alarm_app/images/news/{img}" alt="News image" class="slideshow-image" />'
                for img in self.images
            ]
        )

        return f"""
        <div class='news-container'>
            <h2>Today's News</h2>
            <div class='slideshow'>
                {image_html}
            </div>
            <div class='news-text'>
                <h3>{self.news_title}</h3>
                <p>{self.news_text}</p>
            </div>
        </div>
        """

    def validate_config(self) -> tuple[bool, Optional[str]]:
        rss_url = self.config.get("rss_url")
        if not rss_url:
            return False, "rss_url is required"
        return True, None


class WeatherUtil(RoutineStep):
    """
    Fetches weather forecast and provides clothing recommendations.

    Config:
        location_name (str): Name of the location
        latitude (float): Latitude coordinate
        longitude (float): Longitude coordinate
        tts_command (str): TTS command template
    """

    OUTFIT_SUGGESTIONS = [
        "I recommend long sleeves and a thick coat",
        "I recommend dressing in long sleeves",
        "I recommend wearing shorts and a light jacket",
        "I recommend wearing short sleeves",
        " and I suggest wearing a wind-breaker",
        "; I also recommend a rain jacket or an umbrella",
    ]

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.weather_text = ""

    def execute(self) -> bool:
        try:
            import requests

            latitude = self.config.get("latitude")
            longitude = self.config.get("longitude")

            if not latitude or not longitude:
                return False

            # Get weather from Weather.gov API
            response = requests.get(
                f"https://api.weather.gov/points/{latitude},{longitude}"
            )

            if not response.ok:
                print("Failed to fetch weather data")
                return False

            data = response.json()
            forecast_url = data["properties"]["forecast"]

            forecast_response = requests.get(forecast_url)
            forecast_data = forecast_response.json()

            # Extract current period forecast
            current_period = forecast_data["properties"]["periods"][0]

            temp = int(current_period["temperature"])
            wind_speed = current_period["windSpeed"]
            detailed_forecast = current_period["detailedForecast"]

            # Parse wind speed
            top_wind_speed = self._parse_wind_speed(wind_speed)

            # Generate outfit recommendation
            outfit = self._get_outfit_recommendation(
                temp, top_wind_speed, detailed_forecast
            )

            self.weather_text = (
                f"{outfit} as the forecast for today calls for: {detailed_forecast}"
            )

            # Speak the weather
            self._speak_text(self.weather_text)

            return True

        except Exception as e:
            print(f"Error fetching weather: {e}")
            return False

    def _parse_wind_speed(self, wind_speed_str: str) -> int:
        """Parse wind speed string to get maximum speed."""
        if " to " in wind_speed_str:
            parts = wind_speed_str.split(" to ")
            speed = re.sub(r" mph", "", parts[1])
            return int(speed)
        else:
            speed = re.sub(r" mph", "", wind_speed_str)
            return int(speed)

    def _get_outfit_recommendation(
        self, temp: int, wind_speed: int, forecast: str
    ) -> str:
        """Generate clothing recommendation based on weather conditions."""
        if temp < 53:
            recommendation = self.OUTFIT_SUGGESTIONS[0]
        elif temp < 60:
            recommendation = self.OUTFIT_SUGGESTIONS[1]
        elif temp < 69:
            recommendation = self.OUTFIT_SUGGESTIONS[2]
        else:
            recommendation = self.OUTFIT_SUGGESTIONS[3]

        if wind_speed > 14:
            recommendation += self.OUTFIT_SUGGESTIONS[4]

        if "rain" in forecast.lower():
            recommendation += self.OUTFIT_SUGGESTIONS[5]

        return recommendation

    def _speak_text(self, text: str):
        """Use TTS to speak the weather forecast."""
        tts_command = self.config.get("tts_command", 'simple_google_tts en "{text}"')

        command = tts_command.replace("{text}", text)

        try:
            self._process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self._process.wait()
        except Exception as e:
            print(f"Error with TTS: {e}")

    def format_html(self) -> str:
        """Generate HTML for displaying weather."""
        return f"""
        <div class='weather-container'>
            <h2>Today's Weather</h2>
            <p>{self.weather_text}</p>
        </div>
        """

    def validate_config(self) -> tuple[bool, Optional[str]]:
        latitude = self.config.get("latitude")
        longitude = self.config.get("longitude")

        if not latitude or not longitude:
            return False, "latitude and longitude are required"

        return True, None


class URLOpener(RoutineStep):
    """
    Opens a URL in the default web browser.

    Config:
        url (str): URL to open
        message (str, optional): Optional message to speak before opening
        tts_command (str): TTS command template
    """

    def execute(self) -> bool:
        url = self.config.get("url")
        message = self.config.get("message")

        if not url:
            return False

        try:
            # Speak message if provided
            if message:
                self._speak_text(message)

            # Open URL in browser
            import webbrowser

            webbrowser.open_new_tab(url)

            return True

        except Exception as e:
            print(f"Error opening URL: {e}")
            return False

    def _speak_text(self, text: str):
        """Use TTS to speak the message."""
        tts_command = self.config.get("tts_command", 'simple_google_tts en "{text}"')

        command = tts_command.replace("{text}", text)

        try:
            subprocess.run(command, shell=True, check=True)
        except Exception as e:
            print(f"Error with TTS: {e}")

    def validate_config(self) -> tuple[bool, Optional[str]]:
        url = self.config.get("url")
        if not url:
            return False, "url is required"
        return True, None


class QuoteFetcher(RoutineStep):
    """
    Fetches and presents a random quote.

    Config:
        tts_command (str): TTS command template
        intro_text (str): Text to speak before the quote (default: "Your quote of the day is")
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)

    def execute(self) -> bool:
        try:
            from .models import Quote
            self.quote = Quote.get_random_quote()
            intro = self.config.get("intro_text", "Your quote of the day is")
            if self.quote.author:
                message = f"{intro}: {self.quote.text} - {self.quote.author}"
            else:
                message = f"{intro}: {self.quote.text}"

            # Speak the quote
            self._speak_text(message)

            return True

        except Exception as e:
            print(f"Error fetching quote: {e}")
            return False

    def _speak_text(self, text: str):
        """Use TTS to speak the quote."""
        tts_command = self.config.get("tts_command", 'simple_google_tts en "{text}"')

        command = tts_command.replace("{text}", text)

        try:
            self._process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self._process.wait()
        except Exception as e:
            print(f"Error with TTS: {e}")

    def format_html(self) -> str:
        """Generate HTML for displaying the quote."""
        return f"""
        <div class='quote-container'>
            <h2>Quote of the Day</h2>
            <blockquote>{self.quote}</blockquote>
        </div>
        """

    def validate_config(self) -> tuple[bool, Optional[str]]:
        return True, None


# Registry mapping step type names to classes
ROUTINE_STEP_REGISTRY = {
    "alarm": Alarm,
    "news": News,
    "weather": WeatherUtil,
    "url_opener": URLOpener,
    "quote": QuoteFetcher,
}


def create_routine_step(
    step_type: str, config: Dict[str, Any]
) -> Optional[RoutineStep]:
    """
    Factory function to create routine step instances.

    Args:
        step_type: Type of step (e.g., 'alarm', 'news', 'weather')
        config: Configuration dictionary for the step

    Returns:
        RoutineStep instance or None if type not found
    """
    step_class = ROUTINE_STEP_REGISTRY.get(step_type)
    if step_class:
        return step_class(config)
    return None
