"""
Django-Q based scheduler for Smart Alarm.

Django-Q is a native Django task queue that properly handles:
- Database connections
- Threading issues
- Task scheduling
- No blocking

Install: pip install django-q
"""

# INSTALLATION INSTRUCTIONS
# =========================
# 
# 1. Install Django-Q:
#    pip install django-q
#
# 2. Add to INSTALLED_APPS in config/settings.py:
#    INSTALLED_APPS = [
#        # ... other apps ...
#        'django_q',
#        'alarm_app',
#    ]
#
# 3. Add Django-Q configuration to config/settings.py:
#    Q_CLUSTER = {
#        'name': 'smart_alarm',
#        'workers': 2,
#        'timeout': 600,
#        'retry': 3600,
#        'queue_limit': 50,
#        'bulk': 10,
#        'orm': 'default',
#    }
#
# 4. Run migrations:
#    python manage.py migrate
#
# 5. Start the worker (in separate terminal):
#    python manage.py qcluster
#
# 6. Schedule routines using this module

from django_q.tasks import schedule, Schedule
from django_q.models import Schedule as ScheduleModel
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


def execute_routine(routine_id):
    """
    Execute a routine by ID.
    This function is called by Django-Q workers.
    """
    from .models import Routine, RoutineLog
    from .routine import Routine as RoutineExecutor
    
    logger.info(f"Django-Q executing routine ID: {routine_id}")
    
    try:
        routine_model = Routine.objects.get(id=routine_id, enabled=True)
        
        # Create log entry
        log = RoutineLog.objects.create(
            routine=routine_model,
            started_at=timezone.now(),
            status="started"
        )
        
        try:
            # Convert to executor format
            config = routine_model.to_routine_config()
            
            # Create routine executor
            executor = RoutineExecutor(
                name=config["name"],
                steps_config=config["steps"],
                routine_id=routine_id,
            )
            
            # Validate
            is_valid, errors = executor.validate()
            if not is_valid:
                error_msg = "; ".join(errors)
                logger.error(f"Routine validation failed: {error_msg}")
                log.status = "failed"
                log.error_message = error_msg
                log.completed_at = timezone.now()
                log.save()
                return False
            
            # Execute
            success = executor.start(blocking=True)
            
            # Update log
            log.completed_at = timezone.now()
            log.status = "completed" if success else "failed"
            log.save()
            
            # Mark routine as run
            routine_model.mark_as_run()
            
            logger.info(f"Routine '{routine_model.name}' completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error executing routine: {e}")
            log.status = "failed"
            log.error_message = str(e)
            log.completed_at = timezone.now()
            log.save()
            return False
            
    except Exception as e:
        logger.error(f"Error in execute_routine: {e}")
        return False


def schedule_routine(routine):
    """
    Schedule a routine using Django-Q.
    
    Args:
        routine: Routine model instance
    """
    schedule_name = f"routine_{routine.id}"
    
    # Remove existing schedule if it exists
    ScheduleModel.objects.filter(name=schedule_name).delete()
    
    if not routine.enabled:
        logger.info(f"Routine '{routine.name}' is disabled, not scheduling")
        return
    
    if routine.schedule_type == "once":
        # One-time execution
        if not routine.scheduled_datetime:
            logger.warning(f"Routine '{routine.name}' has no scheduled_datetime")
            return
        
        schedule(
            'alarm_app.scheduler.execute_routine',
            routine.id,
            name=schedule_name,
            schedule_type='O',  # Once
            next_run=routine.scheduled_datetime,
        )
        
        logger.info(f"Scheduled one-time routine '{routine.name}' for {routine.scheduled_datetime}")
        
    elif routine.schedule_type == "recurring":
        # Recurring execution
        if not routine.time_of_day:
            logger.warning(f"Routine '{routine.name}' has no time_of_day")
            return
        
        # Build cron expression
        days = []
        if routine.monday:
            days.append('1')
        if routine.tuesday:
            days.append('2')
        if routine.wednesday:
            days.append('3')
        if routine.thursday:
            days.append('4')
        if routine.friday:
            days.append('5')
        if routine.saturday:
            days.append('6')
        if routine.sunday:
            days.append('0')
        
        if not days:
            logger.warning(f"Routine '{routine.name}' has no days selected")
            return
        
        # Cron format: minute hour day month day_of_week
        cron = f"{routine.time_of_day.minute} {routine.time_of_day.hour} * * {','.join(days)}"
        
        schedule(
            'alarm_app.scheduler.execute_routine',
            routine.id,
            name=schedule_name,
            schedule_type='C',  # Cron
            cron=cron,
        )
        
        logger.info(f"Scheduled recurring routine '{routine.name}' with cron: {cron}")


def reload_all_schedules():
    """
    Reload all routine schedules.
    Call this after creating/updating routines.
    """
    from .models import Routine
    
    logger.info("Reloading all schedules with Django-Q")
    
    # Get all enabled routines
    routines = Routine.objects.filter(enabled=True)
    
    # Remove all existing routine schedules
    ScheduleModel.objects.filter(name__startswith='routine_').delete()
    
    # Schedule each routine
    for routine in routines:
        try:
            schedule_routine(routine)
        except Exception as e:
            logger.error(f"Error scheduling routine '{routine.name}': {e}")
    
    logger.info(f"Scheduled {routines.count()} routine(s)")


def remove_routine_schedule(routine_id):
    """Remove a routine's schedule."""
    schedule_name = f"routine_{routine_id}"
    ScheduleModel.objects.filter(name=schedule_name).delete()
    logger.info(f"Removed schedule for routine {routine_id}")
