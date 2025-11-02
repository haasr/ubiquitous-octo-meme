"""
Middleware to initialize Django-Q schedules after Django is fully ready.

This loads all routine schedules into Django-Q when the first request comes in.
"""

from django.utils.deprecation import MiddlewareMixin
import logging

logger = logging.getLogger(__name__)

# Track whether schedules have been initialized
_schedules_initialized = False


class SchedulerMiddleware(MiddlewareMixin):
    """
    Middleware that loads Django-Q schedules on the first request.
    
    This ensures Django is fully initialized (including database)
    before we try to load routines from the database.
    """

    def process_request(self, request):
        global _schedules_initialized
        
        if not _schedules_initialized:
            try:
                # Check if Django-Q is available
                try:
                    from django_q.models import Schedule
                    from .scheduler_djangoq import reload_all_schedules
                    
                    logger.info("Loading Django-Q schedules...")
                    reload_all_schedules()
                    
                    _schedules_initialized = True
                    logger.info("Django-Q schedules loaded successfully")
                    
                except ImportError:
                    # Django-Q not installed
                    logger.warning("Django-Q not installed. Install with: pip install django-q")
                    _schedules_initialized = True  # Don't keep trying
                    
            except Exception as e:
                logger.error(f"Failed to load schedules: {e}")
                # Don't set _schedules_initialized = True so it will retry
        
        return None
