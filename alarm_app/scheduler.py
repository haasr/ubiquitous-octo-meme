"""
Singleton scheduler for managing routine execution using APScheduler.

This scheduler is initialized when Django starts and manages all
routine executions based on database configuration.
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from django.utils import timezone
from datetime import datetime
import logging

from .routine import Routine as RoutineExecutor
from .models import Routine, RoutineLog

logger = logging.getLogger(__name__)


class RoutineScheduler:
    """
    Singleton scheduler that manages all routine executions.

    Uses APScheduler to trigger routines at their scheduled times.
    Ensures mutual exclusion - only one routine can run at a time.
    """

    _instance = None
    _scheduler = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RoutineScheduler, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._scheduler = BackgroundScheduler()
        self._initialized = True
        self._running = False
        logger.info("RoutineScheduler initialized")

    def start(self):
        """Start the scheduler."""
        if not self._running:
            self._scheduler.start()
            self._running = True
            logger.info("RoutineScheduler started")

            # Load all routines from database
            self.reload_schedules()

    def stop(self):
        """Stop the scheduler."""
        if self._running:
            self._scheduler.shutdown(wait=True)
            self._running = False
            logger.info("RoutineScheduler stopped")

    def reload_schedules(self):
        """
        Reload all routine schedules from the database.

        This clears all existing jobs and recreates them based on
        current database state.
        """
        # Remove all existing jobs
        self._scheduler.remove_all_jobs()

        # Load enabled routines from database
        try:
            from .models import Routine  # Import here to avoid circular imports

            routines = Routine.objects.filter(enabled=True)

            for routine in routines:
                self._schedule_routine(routine)

            logger.info(f"Loaded {len(routines)} routine(s)")

        except Exception as e:
            logger.error(f"Error loading routines: {e}")

    def _schedule_routine(self, routine: Routine):
        """
        Schedule a single routine.

        Args:
            routine: Routine model instance to schedule
        """
        try:
            job_id = f"routine_{routine.id}"

            if routine.schedule_type == "once":
                # One-time execution
                if routine.scheduled_datetime:
                    trigger = DateTrigger(run_date=routine.scheduled_datetime)

                    self._scheduler.add_job(
                        func=self._execute_routine,
                        trigger=trigger,
                        id=job_id,
                        args=[routine.id],
                        replace_existing=True,
                    )

                    logger.info(
                        f"Scheduled one-time routine '{routine.name}' "
                        f"for {routine.scheduled_datetime}"
                    )

            elif routine.schedule_type == "recurring":
                # Recurring execution
                if not routine.time_of_day:
                    logger.warning(
                        f"Routine '{routine.name}' has no time set, skipping"
                    )
                    return

                # Build day_of_week parameter for cron trigger
                days = []
                if routine.monday:
                    days.append("mon")
                if routine.tuesday:
                    days.append("tue")
                if routine.wednesday:
                    days.append("wed")
                if routine.thursday:
                    days.append("thu")
                if routine.friday:
                    days.append("fri")
                if routine.saturday:
                    days.append("sat")
                if routine.sunday:
                    days.append("sun")

                if not days:
                    logger.warning(
                        f"Routine '{routine.name}' has no days selected, skipping"
                    )
                    return

                # Create cron trigger
                trigger = CronTrigger(
                    day_of_week=",".join(days),
                    hour=routine.time_of_day.hour,
                    minute=routine.time_of_day.minute,
                    second=0,
                )

                self._scheduler.add_job(
                    func=self._execute_routine,
                    trigger=trigger,
                    id=job_id,
                    args=[routine.id],
                    replace_existing=True,
                )

                logger.info(
                    f"Scheduled recurring routine '{routine.name}' "
                    f"for {','.join(days)} at {routine.time_of_day}"
                )

        except Exception as e:
            logger.error(f"Error scheduling routine '{routine.name}': {e}")

    def _execute_routine(self, routine_id: int):
        """
        Execute a routine by its database ID.

        This is called by APScheduler when a routine is triggered.

        Args:
            routine_id: Database ID of the routine to execute
        """
        try:
            # Fetch routine from database
            routine_model = Routine.objects.get(id=routine_id, enabled=True)

            logger.info(f"Executing routine: {routine_model.name}")

            # Create log entry
            log = RoutineLog.objects.create(
                routine=routine_model, started_at=timezone.now(), status="started"
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

                # Validate before execution
                is_valid, errors = executor.validate()
                if not is_valid:
                    error_msg = "; ".join(errors)
                    logger.error(
                        f"Routine '{routine_model.name}' validation failed: {error_msg}"
                    )
                    log.status = "failed"
                    log.error_message = error_msg
                    log.completed_at = timezone.now()
                    log.save()
                    return

                # Execute the routine (blocking)
                success = executor.start(blocking=True)

                # Update log
                log.completed_at = timezone.now()
                log.status = "completed" if success else "failed"
                log.save()

                # Mark routine as run
                routine_model.mark_as_run()

                logger.info(
                    f"Routine '{routine_model.name}' completed "
                    f"({'success' if success else 'with errors'})"
                )

            except Exception as e:
                logger.error(f"Error executing routine '{routine_model.name}': {e}")
                log.status = "failed"
                log.error_message = str(e)
                log.completed_at = timezone.now()
                log.save()

        except Routine.DoesNotExist:
            logger.warning(f"Routine with ID {routine_id} not found or disabled")
        except Exception as e:
            logger.error(f"Unexpected error in _execute_routine: {e}")

    def get_scheduled_jobs(self):
        """
        Get list of currently scheduled jobs.

        Returns:
            list: List of job information dictionaries
        """
        jobs = []
        for job in self._scheduler.get_jobs():
            jobs.append(
                {
                    "id": job.id,
                    "name": job.name,
                    "next_run_time": job.next_run_time,
                    "trigger": str(job.trigger),
                }
            )
        return jobs

    def pause_routine(self, routine_id: int):
        """Pause a scheduled routine."""
        job_id = f"routine_{routine_id}"
        try:
            self._scheduler.pause_job(job_id)
            logger.info(f"Paused routine {routine_id}")
        except Exception as e:
            logger.error(f"Error pausing routine {routine_id}: {e}")

    def resume_routine(self, routine_id: int):
        """Resume a paused routine."""
        job_id = f"routine_{routine_id}"
        try:
            self._scheduler.resume_job(job_id)
            logger.info(f"Resumed routine {routine_id}")
        except Exception as e:
            logger.error(f"Error resuming routine {routine_id}: {e}")

    def remove_routine(self, routine_id: int):
        """Remove a routine from the schedule."""
        job_id = f"routine_{routine_id}"
        try:
            self._scheduler.remove_job(job_id)
            logger.info(f"Removed routine {routine_id}")
        except Exception as e:
            logger.error(f"Error removing routine {routine_id}: {e}")

    def is_running(self):
        """Check if scheduler is running."""
        return self._running

    @classmethod
    def get_instance(cls):
        """Get the singleton scheduler instance."""
        return cls()


# Convenience function to get the scheduler
def get_scheduler():
    """Get the singleton scheduler instance."""
    return RoutineScheduler.get_instance()
