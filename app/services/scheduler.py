import time
import threading
import logging
from datetime import datetime, timezone
from app.extensions import db
from app.models.endpoint import Endpoint
from app.services.monitor import execute_health_check

logger = logging.getLogger("api_sentinel.scheduler")

class MonitoringScheduler:
    """
    Lightweight background monitoring worker that automatically
    evaluates due endpoints and executes real HTTP health checks.
    """
    def __init__(self, app=None, poll_interval=10):
        self.app = app
        self.poll_interval = poll_interval
        self._stop_event = threading.Event()
        self._thread = None
        self._is_running = False

    def init_app(self, app):
        self.app = app
        self.poll_interval = app.config.get("SCHEDULER_INTERVAL_SECONDS", 10)

    def start(self):
        """Start the background scheduler thread if not already running."""
        if self._is_running or not self.app:
            return

        # Check if background scheduler is enabled in config
        if not self.app.config.get("ENABLE_BACKGROUND_SCHEDULER", True):
            logger.info("Background scheduler is disabled by configuration.")
            return

        self._stop_event.clear()
        self._is_running = True
        self._thread = threading.Thread(
            target=self._run_loop,
            name="API-Sentinel-Scheduler",
            daemon=True
        )
        self._thread.start()
        logger.info("Background monitoring scheduler started.")

    def stop(self):
        """Signal the background thread to stop and wait for it."""
        if not self._is_running:
            return
        logger.info("Stopping background monitoring scheduler...")
        self._stop_event.set()
        self._is_running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        logger.info("Background monitoring scheduler stopped.")

    def _run_loop(self):
        """Main loop executed by the daemon thread."""
        allow_local = self.app.config.get("ALLOW_LOCAL_MONITORING", False)

        while not self._stop_event.is_set():
            try:
                with self.app.app_context():
                    self._check_due_endpoints(allow_local)
            except Exception as e:
                logger.error(f"Error in scheduler check loop: {e}", exc_info=True)

            # Sleep in small increments so we can exit quickly when stop_event is set
            for _ in range(self.poll_interval):
                if self._stop_event.is_set():
                    break
                time.sleep(1)

    def _check_due_endpoints(self, allow_local: bool):
        """Find active endpoints due for a health check and run them."""
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        endpoints = Endpoint.query.filter_by(is_active=True).all()

        for ep in endpoints:
            if self._stop_event.is_set():
                break

            should_check = False
            if ep.last_checked_at is None:
                should_check = True
            else:
                last_checked = ep.last_checked_at.replace(tzinfo=None) if ep.last_checked_at.tzinfo else ep.last_checked_at
                elapsed = (now - last_checked).total_seconds()
                if elapsed >= ep.check_interval:
                    should_check = True

            if should_check:
                try:
                    logger.debug(f"Scheduler checking endpoint #{ep.id}: {ep.name} ({ep.url})")
                    execute_health_check(ep, allow_local=allow_local)
                except Exception as err:
                    logger.error(f"Failed to check endpoint #{ep.id}: {err}")

# Singleton scheduler instance
scheduler = MonitoringScheduler()
