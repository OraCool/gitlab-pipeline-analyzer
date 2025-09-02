"""
Automatic Cache Cleanup Manager

Provides efficient background cache cleanup that runs periodically
during resource access without blocking requests.

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import asyncio
import os
import time
from typing import Any

from gitlab_analyzer.cache.mcp_cache import get_cache_manager
from gitlab_analyzer.utils.debug import debug_print, error_print, verbose_debug_print


class AutoCleanupManager:
    """Manages automatic cache cleanup with rate limiting"""

    def __init__(self):
        # Configuration from environment variables
        self.enabled = os.getenv("MCP_AUTO_CLEANUP_ENABLED", "true").lower() == "true"
        self.cleanup_interval_minutes = int(
            os.getenv("MCP_AUTO_CLEANUP_INTERVAL_MINUTES", "60")
        )  # Default: 1 hour
        self.max_age_hours = int(
            os.getenv("MCP_AUTO_CLEANUP_MAX_AGE_HOURS", "24")
        )  # Default: 24 hours

        # Debug initialization info
        verbose_debug_print("🧹 [AUTO-CLEANUP] Initializing auto cleanup manager:")
        verbose_debug_print(f"  - Enabled: {self.enabled}")
        verbose_debug_print(
            f"  - Cleanup interval: {self.cleanup_interval_minutes} minutes"
        )
        verbose_debug_print(f"  - Max age: {self.max_age_hours} hours")

        # Internal state
        self._last_cleanup_time: float | None = None
        self._cleanup_in_progress = False

    def should_run_cleanup(self) -> bool:
        """Check if cleanup should run based on interval and current state"""
        if not self.enabled:
            verbose_debug_print("🧹 [AUTO-CLEANUP] Cleanup disabled via configuration")
            return False

        if self._cleanup_in_progress:
            verbose_debug_print(
                "🧹 [AUTO-CLEANUP] Cleanup already in progress, skipping"
            )
            return False

        if self._last_cleanup_time is None:
            verbose_debug_print("🧹 [AUTO-CLEANUP] No previous cleanup, should run")
            return True

        elapsed_minutes = (time.time() - self._last_cleanup_time) / 60
        should_run = elapsed_minutes >= self.cleanup_interval_minutes

        if should_run:
            verbose_debug_print(
                f"🧹 [AUTO-CLEANUP] Cleanup needed: {elapsed_minutes:.1f} minutes elapsed (interval: {self.cleanup_interval_minutes})"
            )
        else:
            verbose_debug_print(
                f"🧹 [AUTO-CLEANUP] Cleanup not needed yet: {elapsed_minutes:.1f}/{self.cleanup_interval_minutes} minutes"
            )

        return should_run

    async def trigger_cleanup_if_needed(self) -> dict[str, Any]:
        """
        Trigger cleanup if needed, runs in background without blocking.
        Returns status information.
        """
        verbose_debug_print("🧹 [AUTO-CLEANUP] Checking if cleanup should be triggered")

        if not self.should_run_cleanup():
            reason = "disabled" if not self.enabled else "not_needed"
            verbose_debug_print(f"🧹 [AUTO-CLEANUP] Cleanup not triggered: {reason}")

            return {
                "cleanup_triggered": False,
                "reason": reason,
                "last_cleanup": self._last_cleanup_time,
                "next_cleanup_in_minutes": self._get_next_cleanup_minutes(),
            }

        # Start cleanup in background (fire and forget)
        debug_print("🧹 [AUTO-CLEANUP] Triggering background cleanup task")
        asyncio.create_task(self._run_cleanup_background())

        return {
            "cleanup_triggered": True,
            "max_age_hours": self.max_age_hours,
            "interval_minutes": self.cleanup_interval_minutes,
        }

    async def _run_cleanup_background(self) -> None:
        """Run the actual cleanup in background"""
        if self._cleanup_in_progress:
            verbose_debug_print(
                "🧹 [AUTO-CLEANUP] Cleanup already in progress, aborting"
            )
            return

        debug_print(
            f"🧹 [AUTO-CLEANUP] Starting background cleanup (max age: {self.max_age_hours}h)"
        )
        self._cleanup_in_progress = True

        try:
            cache_manager = get_cache_manager()
            verbose_debug_print(
                "🧹 [AUTO-CLEANUP] Calling cache manager to clear old entries"
            )

            cleared_count = await cache_manager.clear_old_entries(self.max_age_hours)
            self._last_cleanup_time = time.time()

            debug_print(
                f"✅ [AUTO-CLEANUP] Completed: {cleared_count} entries removed "
                f"(older than {self.max_age_hours}h)"
            )

        except Exception as e:
            error_print(f"❌ [AUTO-CLEANUP] Failed: {e}")
        finally:
            self._cleanup_in_progress = False
            verbose_debug_print("🧹 [AUTO-CLEANUP] Background cleanup finished")

    def _get_next_cleanup_minutes(self) -> float | None:
        """Get minutes until next cleanup"""
        if not self.enabled or self._last_cleanup_time is None:
            return None

        elapsed_minutes = (time.time() - self._last_cleanup_time) / 60
        return max(0, self.cleanup_interval_minutes - elapsed_minutes)

    def get_status(self) -> dict[str, Any]:
        """Get current cleanup status"""
        status = {
            "enabled": self.enabled,
            "cleanup_interval_minutes": self.cleanup_interval_minutes,
            "max_age_hours": self.max_age_hours,
            "last_cleanup_time": self._last_cleanup_time,
            "cleanup_in_progress": self._cleanup_in_progress,
            "next_cleanup_in_minutes": self._get_next_cleanup_minutes(),
        }

        verbose_debug_print("🧹 [AUTO-CLEANUP] Status requested:")
        for key, value in status.items():
            verbose_debug_print(f"  - {key}: {value}")

        return status


# Global instance
_auto_cleanup_manager: AutoCleanupManager | None = None


def get_auto_cleanup_manager() -> AutoCleanupManager:
    """Get the global auto cleanup manager instance"""
    global _auto_cleanup_manager
    if _auto_cleanup_manager is None:
        verbose_debug_print(
            "🧹 [AUTO-CLEANUP] Creating global auto cleanup manager instance"
        )
        _auto_cleanup_manager = AutoCleanupManager()
        debug_print("✅ [AUTO-CLEANUP] Global auto cleanup manager initialized")
    return _auto_cleanup_manager
