"""
Auto-Solver Daemon
==================
Background loop that polls JDownloader for pending captchas and
automatically solves them using the registered solvers.

Usage:
    daemon = AutoSolverDaemon(device, router)
    daemon.start()   # Starts background thread
    daemon.stop()    # Stops the daemon
    daemon.status()  # Returns current status
"""

import base64
import time
import logging
import threading
from typing import Optional

from .base import CaptchaChallenge, CaptchaType
from .router import CaptchaRouter

logger = logging.getLogger("captcha-solver.daemon")


class AutoSolverDaemon:
    """
    Background daemon that monitors JDownloader for captchas and solves them.

    Features:
    - Configurable poll interval
    - Automatic retry on failure
    - Rate limiting to avoid API abuse
    - Statistics tracking
    - Thread-safe start/stop
    """

    def __init__(
        self,
        device,
        router: CaptchaRouter,
        poll_interval: float = 3.0,
        max_retries: int = 2,
        cooldown_after_solve: float = 1.0,
    ):
        """
        Args:
            device: myjdapi device instance (must be connected)
            router: CaptchaRouter with registered solvers
            poll_interval: Seconds between captcha checks
            max_retries: Max retry attempts per captcha
            cooldown_after_solve: Seconds to wait after solving one
        """
        self.device = device
        self.router = router
        self.poll_interval = poll_interval
        self.max_retries = max_retries
        self.cooldown_after_solve = cooldown_after_solve

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # Stats
        self._stats = {
            "started_at": None,
            "total_detected": 0,
            "total_solved": 0,
            "total_failed": 0,
            "last_captcha_at": None,
            "last_solve_at": None,
            "errors": 0,
        }

        # Track already-attempted captcha IDs to avoid infinite retries
        self._attempted: dict = {}  # {captcha_id: attempt_count}

    def start(self) -> str:
        """Start the auto-solver daemon in a background thread."""
        with self._lock:
            if self._running:
                return "Daemon already running"

            self._running = True
            self._stats["started_at"] = time.time()
            self._thread = threading.Thread(
                target=self._run_loop,
                name="captcha-auto-solver",
                daemon=True,
            )
            self._thread.start()

            logger.info("Auto-solver daemon started")
            return "Auto-solver daemon started"

    def stop(self) -> str:
        """Stop the auto-solver daemon."""
        with self._lock:
            if not self._running:
                return "Daemon not running"

            self._running = False
            if self._thread:
                self._thread.join(timeout=10)
                self._thread = None

            logger.info("Auto-solver daemon stopped")
            return "Auto-solver daemon stopped"

    @property
    def is_running(self) -> bool:
        """Check if daemon is currently running."""
        return self._running

    def status(self) -> dict:
        """Get current daemon status and statistics."""
        uptime = None
        if self._stats["started_at"] and self._running:
            uptime = time.time() - self._stats["started_at"]

        return {
            "running": self._running,
            "uptime_seconds": uptime,
            "poll_interval": self.poll_interval,
            "stats": self._stats.copy(),
            "solvers": self.router.solvers,
            "pending_attempts": len(self._attempted),
        }

    def _run_loop(self):
        """Main daemon loop — runs in background thread."""
        logger.info(
            f"Daemon loop started (poll every {self.poll_interval}s, "
            f"max retries: {self.max_retries})"
        )

        while self._running:
            try:
                self._check_and_solve()
            except Exception as e:
                self._stats["errors"] += 1
                logger.error(f"Daemon loop error: {e}")
                # Don't crash — wait and retry
                time.sleep(self.poll_interval * 2)
                continue

            time.sleep(self.poll_interval)

    def _check_and_solve(self):
        """Check for pending captchas and attempt to solve them."""
        try:
            captchas = self.device.captcha.list()
        except Exception as e:
            logger.debug(f"Failed to list captchas: {e}")
            return

        if not captchas:
            return

        for captcha_info in captchas:
            if not self._running:
                break

            captcha_id = captcha_info.get("id")
            if captcha_id is None:
                continue

            # Check if we've already exhausted retries
            attempts = self._attempted.get(captcha_id, 0)
            if attempts >= self.max_retries:
                continue

            self._stats["total_detected"] += 1
            self._stats["last_captcha_at"] = time.time()

            logger.info(
                f"Captcha detected: id={captcha_id}, "
                f"hoster={captcha_info.get('hoster', '?')}, "
                f"attempt={attempts + 1}/{self.max_retries}"
            )

            # Build challenge
            challenge = self._build_challenge(captcha_info)
            if challenge is None:
                self._attempted[captcha_id] = self.max_retries  # Skip
                continue

            # Solve
            solution = self.router.solve(challenge)

            if solution.success and solution.solution:
                # Submit solution to JDownloader
                try:
                    self.device.captcha.solve(captcha_id, solution.solution)
                    self._stats["total_solved"] += 1
                    self._stats["last_solve_at"] = time.time()
                    # Remove from attempted (solved)
                    self._attempted.pop(captcha_id, None)
                    logger.info(
                        f"Captcha #{captcha_id} solved: "
                        f"'{solution.solution}' by {solution.solver_name}"
                    )
                except Exception as e:
                    logger.error(f"Failed to submit solution: {e}")
                    self._attempted[captcha_id] = attempts + 1

                # Cooldown between solves
                time.sleep(self.cooldown_after_solve)
            else:
                self._stats["total_failed"] += 1
                self._attempted[captcha_id] = attempts + 1
                logger.warning(
                    f"Captcha #{captcha_id} failed: {solution.error}"
                )

    def _build_challenge(self, captcha_info: dict) -> Optional[CaptchaChallenge]:
        """Build a CaptchaChallenge from JDownloader's captcha info."""
        captcha_id = captcha_info.get("id")

        try:
            # Get the captcha image from JDownloader
            image_b64 = self.device.captcha.get(captcha_id)
        except Exception as e:
            logger.error(f"Failed to get captcha image #{captcha_id}: {e}")
            return None

        if not image_b64:
            return None

        # Decode image
        try:
            image_data = base64.b64decode(image_b64)
        except Exception:
            image_data = None

        challenge = CaptchaChallenge(
            captcha_id=captcha_id,
            hoster=captcha_info.get("hoster", ""),
            image_data=image_data,
            image_base64=image_b64,
            extra=captcha_info,
        )

        return challenge

    def reset_stats(self):
        """Reset all statistics."""
        self._stats = {
            "started_at": self._stats.get("started_at"),
            "total_detected": 0,
            "total_solved": 0,
            "total_failed": 0,
            "last_captcha_at": None,
            "last_solve_at": None,
            "errors": 0,
        }
        self._attempted.clear()

    def clear_attempted(self):
        """Clear the attempted captcha cache (allows re-solving)."""
        self._attempted.clear()
