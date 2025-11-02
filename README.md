# Smart Alarm Web Application

A modern, extensible smart alarm clock system built with Django and Python, featuring customizable morning routines with news, weather, quotes, and more.

## Architecture Overview

### Core Design Pattern: Strategy + Chain of Responsibility

The system uses a **RoutineStep** abstraction that allows any alarm component to be plugged in and chained together into morning routines.

```
┌─────────────────────────────────────────────────┐
│                  Django Web UI                  │
│  (Configure routines, schedules, preferences)   │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│            RoutineScheduler                     │
│         (APScheduler Singleton)                 │
│  - Loads routines from database                 │
│  - Triggers at scheduled times                  │
│  - Enforces mutual exclusion                    │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│                  Routine                        │
│  - Executes RoutineSteps sequentially           │
│  - Manages start/stop/cleanup                   │
│  - Logs execution                               │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│             RoutineStep (ABC)                   │
│                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │  Alarm   │  │   News   │  │ Weather  │     │
│  └──────────┘  └──────────┘  └──────────┘     │
│                                                 │
│  ┌──────────┐  ┌──────────────────────┐        │
│  │  Quote   │  │    URLOpener         │        │
│  └──────────┘  └──────────────────────┘        │
└─────────────────────────────────────────────────┘
```

## Project Structure

```
smart_alarm_web/
├── alarm_app/
│   ├── models.py              # Django models (Routine, Quote, etc.)
│   ├── routine_steps.py       # RoutineStep classes (Alarm, News, Weather, etc.)
│   ├── routine.py             # Routine execution engine
│   ├── scheduler.py           # APScheduler singleton
│   ├── admin.py               # Django admin configuration
│   ├── views.py               # Django views (to be created)
│   ├── urls.py                # URL routing (to be created)
│   ├── management/
│   │   └── commands/
│   │       └── import_quotes.py  # Import quotes from file
│   ├── templates/
│   │   └── alarm_app/         # HTML templates (to be created)
│   ├── static/
│   │   └── alarm_app/
│   │       ├── js/
│   │       │   └── slideshow.js  # Fullscreen image slideshow
│   │       ├── css/
│   │       │   └── style.css     # Application styles
│   │       └── images/
│   │           └── news/         # Downloaded news images
│   └── migrations/
└── config/
    ├── settings.py            # Django settings (to be created)
    ├── urls.py                # Root URL config (to be created)
    └── wsgi.py                # WSGI config (to be created)
```

## Core Components

### 1. RoutineStep (Abstract Base Class)

All routine components inherit from `RoutineStep`:

```python
class RoutineStep(ABC):
    def __init__(self, config: Dict[str, Any])
    
    @abstractmethod
    def execute(self) -> bool
    
    def stop(self)
    def format_html(self) -> str
    def validate_config(self) -> tuple[bool, Optional[str]]
```

**Available RoutineSteps:**

- **Alarm**: Plays audio file alarm with optional auto-stop
- **News**: Fetches RSS feed, downloads images, displays slideshow with TTS narration
- **WeatherUtil**: Gets forecast from Weather.gov API, provides clothing recommendations
- **URLOpener**: Opens URLs in browser with optional TTS message
- **QuoteFetcher**: Retrieves random quote from database and speaks it

### 2. Routine Class

Chains multiple RoutineSteps together and manages execution:

```python
routine = Routine(
    name="Morning Wake-up",
    steps_config=[
        {'type': 'alarm', 'config': {...}},
        {'type': 'news', 'config': {...}},
        {'type': 'weather', 'config': {...}},
        {'type': 'quote', 'config': {...}}
    ]
)

routine.start(blocking=True)  # Execute all steps in sequence
```

**Key features:**
- Sequential execution with cleanup
- Mutual exclusion (only one routine runs at a time)
- Start/stop control
- Validation before execution
- JSON serialization

### 3. RoutineScheduler (Singleton)

Uses APScheduler to trigger routines at scheduled times:

```python
scheduler = RoutineScheduler.get_instance()
scheduler.start()
scheduler.reload_schedules()  # Load from database
```

**Scheduling options:**
- **One-time**: Execute at specific datetime
- **Recurring**: Execute on selected days at specific time

**Features:**
- Automatic database synchronization
- Job pause/resume/removal
- Execution logging
- Error handling

### 4. Django Models

**UserProfile** (Singleton)
- Default weather location
- TTS command template
- Greeting preferences

**Routine**
- Name, description, enabled status
- Schedule configuration (one-time or recurring)
- Steps stored as JSON
- Execution tracking

**NewsSource**
- RSS feed URLs organized by category

**WeatherLocation**
- Saved locations with lat/lon coordinates

**Quote**
- Inspirational quotes with optional author/category

**RoutineLog**
- Execution history for debugging

## Configuration Examples

### Example Routine Configuration

```json
{
  "name": "Morning Wake-up",
  "steps": [
    {
      "type": "alarm",
      "config": {
        "audio_file": "/path/to/alarm.wav",
        "duration": 30
      }
    },
    {
      "type": "news",
      "config": {
        "rss_url": "https://www.theguardian.com/world/rss",
        "num_images": 6
      }
    },
    {
      "type": "weather",
      "config": {
        "latitude": "36.3406",
        "longitude": "-82.3804",
        "location_name": "Johnson City"
      }
    },
    {
      "type": "quote",
      "config": {
        "intro_text": "Your quote of the day is"
      }
    },
    {
      "type": "url_opener",
      "config": {
        "url": "https://en.wikipedia.org/wiki/Main_Page",
        "message": "And now, today's history lesson"
      }
    }
  ]
}
```

## Key Design Decisions

### 1. JSON Configuration Storage
**Rationale**: Steps are stored as JSON in the database rather than complex relational models. This provides:
- Flexibility to add new step types without migrations
- Easy serialization for API/export
- Simpler configuration UI
- Configuration versioning capability

### 2. Mutual Exclusion
**Implementation**: Class-level threading lock in `Routine` class
**Rationale**: Prevents overlapping routines from interfering with TTS, audio playback, or browser actions

### 3. Singleton Scheduler
**Rationale**: 
- Single source of truth for all scheduled jobs
- Prevents duplicate job scheduling
- Centralized lifecycle management
- Easy to reload/refresh schedules

### 4. Context Managers
**Implementation**: `RoutineStep` implements `__enter__`/`__exit__`
**Rationale**: Ensures proper cleanup even if step fails

### 5. Validation Before Execution
**Implementation**: `validate_config()` method on each step
**Rationale**: Fail fast - catch configuration errors before execution

## Extensibility

### Adding New RoutineStep Types

1. **Create the class**:
```python
class CustomStep(RoutineStep):
    def execute(self) -> bool:
        # Your logic here
        return True
    
    def validate_config(self) -> tuple[bool, Optional[str]]:
        # Validate configuration
        return True, None
```

2. **Register in factory**:
```python
ROUTINE_STEP_REGISTRY = {
    'custom': CustomStep,
    # ... existing steps
}
```

3. **Use in routines**:
```json
{
  "type": "custom",
  "config": {
    "your_param": "value"
  }
}
```

## Installation & Setup

### Dependencies

```bash
pip install django apscheduler feedparser requests google-images-downloader
```

### Database Setup

```bash
python manage.py makemigrations
python manage.py migrate
```

### Import Initial Data

```bash
# Import quotes
python manage.py import_quotes /path/to/quotes.txt --category "Programming"

# Import weather locations from CSV (TODO: create command)
# Import news sources (can be done via admin or fixture)
```

### Start Scheduler

Add to Django's app ready hook (`apps.py`):

```python
from django.apps import AppConfig

class AlarmAppConfig(AppConfig):
    name = 'alarm_app'
    
    def ready(self):
        from .scheduler import get_scheduler
        scheduler = get_scheduler()
        scheduler.start()
```

## Usage

### Via Django Admin
1. Create news sources, quotes, locations
2. Configure UserProfile defaults
3. Create Routine with schedule
4. Enable routine

### Via Django Views (To Be Implemented)
- Landing page: View active routines
- Settings page: Configure defaults
- Routines page: Create/edit/schedule routines

## Slideshow Functionality

News images display in fullscreen with JavaScript:

```javascript
const images = ['/static/images/news/img1.jpg', ...];
startSlideshow(images, 5000);  // 5 second interval
```

**Controls**:
- Arrow keys: Navigate
- Space: Pause/resume
- Escape: Exit
- On-screen buttons for touch devices

## Migration from Original Project

Original `smart_alarm.py` functionality mapped to new architecture:

| Original | New Architecture |
|----------|-----------------|
| `trigger_alarm()` | `Routine.start()` |
| `tts()` calls | `RoutineStep._speak_text()` |
| `news_util.get_news()` | `News.execute()` |
| `weather_util.get_weather()` | `WeatherUtil.execute()` |
| `quotes_util.get_quote()` | `QuoteFetcher.execute()` |
| `get_history_article()` | `URLOpener.execute()` |
| Polling loop | APScheduler |
| Command-line args | Django UI + Database |

## Future Enhancements

- Web-based routine builder with drag-and-drop
- Mobile app integration
- Voice control integration
- Routine templates/presets
- Integration with smart home systems
- Cloud sync for multi-device support
- Advanced scheduling (sunrise/sunset triggers)
- Routine performance analytics

## Advantages Over Original

1. **Web Interface**: Configure without editing code
2. **Persistent Storage**: Schedules survive restarts
3. **Professional Scheduling**: APScheduler vs polling
4. **Extensibility**: Plugin architecture for new steps
5. **Monitoring**: Execution logs and history
6. **Modern Stack**: Django ecosystem benefits
7. **Maintainability**: Separation of concerns, testability
8. **Deployment**: Standard Django deployment options

## License

[Your License Here]
