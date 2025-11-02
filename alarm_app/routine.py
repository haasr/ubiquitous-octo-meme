"""
Routine class for managing and executing sequences of RoutineSteps.
"""

import threading
import time
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

from .routine_steps import create_routine_step, RoutineStep


class Routine:
    """
    A Routine is a sequence of RoutineSteps that execute in order.

    Routines can be scheduled to run at specific times and days of the week.
    Only one routine can execute at a time (mutual exclusion).
    """

    # Class-level lock for mutual exclusion
    _execution_lock = threading.Lock()
    _currently_running = None

    def __init__(
        self,
        name: str,
        steps_config: List[Dict[str, Any]],
        routine_id: Optional[int] = None,
    ):
        """
        Initialize a Routine.

        Args:
            name: Human-readable name for the routine
            steps_config: List of step configurations, each containing:
                - 'type': The step type (e.g., 'alarm', 'news')
                - 'config': Dictionary of configuration for that step
            routine_id: Database ID (if persisted)
        """
        self.name = name
        self.routine_id = routine_id
        self.steps_config = steps_config
        self.steps: List[RoutineStep] = []
        self._stop_event = threading.Event()
        self._execution_thread = None

        # Build the steps from configuration
        self._build_steps()

    def _build_steps(self):
        """Build RoutineStep instances from configuration."""
        self.steps = []
        for step_config in self.steps_config:
            step_type = step_config.get("type")
            step_params = step_config.get("config", {})

            step = create_routine_step(step_type, step_params)
            if step:
                self.steps.append(step)
            else:
                print(
                    f"Warning: Unknown step type '{step_type}' in routine '{self.name}'"
                )

    def start(self, blocking: bool = True) -> bool:
        """
        Start executing the routine.

        Args:
            blocking: If True, blocks until routine completes.
                     If False, runs in background thread.

        Returns:
            bool: True if routine started successfully
        """
        # Check if another routine is running
        if not Routine._execution_lock.acquire(blocking=False):
            print(
                f"Cannot start routine '{self.name}': another routine is currently running"
            )
            return False

        try:
            Routine._currently_running = self.name

            if blocking:
                self._execute()
            else:
                self._execution_thread = threading.Thread(
                    target=self._execute, name=f"Routine-{self.name}"
                )
                self._execution_thread.daemon = True
                self._execution_thread.start()

            return True

        except Exception as e:
            print(f"Error starting routine: {e}")
            Routine._execution_lock.release()
            Routine._currently_running = None
            return False

    def _execute(self):
        """Execute all steps in sequence."""
        print(f"Starting routine: {self.name}")
        start_time = datetime.now()

        try:
            for i, step in enumerate(self.steps):
                if self._stop_event.is_set():
                    print(
                        f"Routine '{self.name}' stopped at step {i+1}/{len(self.steps)}"
                    )
                    break

                print(
                    f"Executing step {i+1}/{len(self.steps)}: {step.__class__.__name__}"
                )

                # Execute the step
                success = step.execute()

                if not success:
                    print(f"Step {i+1} failed, but continuing...")

                # Small delay between steps
                time.sleep(0.5)

            duration = (datetime.now() - start_time).total_seconds()
            print(f"Routine '{self.name}' completed in {duration:.1f} seconds")

        except Exception as e:
            print(f"Error executing routine '{self.name}': {e}")

        finally:
            # Release the lock
            Routine._execution_lock.release()
            Routine._currently_running = None
            self._stop_event.clear()

    def stop(self):
        """Stop the routine execution."""
        print(f"Stopping routine: {self.name}")
        self._stop_event.set()

        # Stop all steps
        for step in self.steps:
            step.stop()

        # Wait for execution thread to finish
        if self._execution_thread and self._execution_thread.is_alive():
            self._execution_thread.join(timeout=10)

    def validate(self) -> tuple[bool, List[str]]:
        """
        Validate the routine configuration.

        Returns:
            tuple: (is_valid, list_of_error_messages)
        """
        errors = []

        if not self.name:
            errors.append("Routine name is required")

        if not self.steps_config:
            errors.append("Routine must have at least one step")

        # Validate each step
        for i, step in enumerate(self.steps):
            is_valid, error = step.validate_config()
            if not is_valid:
                errors.append(f"Step {i+1} ({step.__class__.__name__}): {error}")

        return len(errors) == 0, errors

    def to_dict(self) -> Dict[str, Any]:
        """Serialize routine to dictionary."""
        return {"id": self.routine_id, "name": self.name, "steps": self.steps_config}

    def to_json(self) -> str:
        """Serialize routine to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Routine":
        """Create a Routine from a dictionary."""
        return cls(
            name=data["name"], steps_config=data["steps"], routine_id=data.get("id")
        )

    @classmethod
    def from_json(cls, json_str: str) -> "Routine":
        """Create a Routine from a JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)

    @classmethod
    def get_currently_running(cls) -> Optional[str]:
        """Get the name of the currently running routine, if any."""
        return cls._currently_running

    def __repr__(self):
        return f"<Routine '{self.name}' with {len(self.steps)} steps>"


# Example usage
if __name__ == "__main__":
    # Example routine configuration
    morning_routine_config = {
        "name": "Morning Wake-up",
        "steps": [
            {
                "type": "alarm",
                "config": {"audio_file": "/home/pi/alarm.wav", "duration": 30},
            },
            {
                "type": "news",
                "config": {
                    "rss_url": "https://www.theguardian.com/world/rss",
                    "num_images": 6,
                },
            },
            {
                "type": "weather",
                "config": {
                    "latitude": "36.3406",
                    "longitude": "-82.3804",
                    "location_name": "Johnson City",
                },
            },
            {"type": "quote", "config": {"intro_text": "Your quote of the day is"}},
            {
                "type": "url_opener",
                "config": {
                    "url": "https://en.wikipedia.org/wiki/Main_Page",
                    "message": "And now, todays history lesson",
                },
            },
        ],
    }

    # Create and validate routine
    routine = Routine.from_dict(morning_routine_config)
    is_valid, errors = routine.validate()

    if is_valid:
        print("Routine is valid!")
        print(routine)
        # routine.start(blocking=True)  # Would actually execute
    else:
        print("Routine has errors:")
        for error in errors:
            print(f"  - {error}")
