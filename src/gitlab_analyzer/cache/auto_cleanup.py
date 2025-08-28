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

        # Internal state
        self._last_cleanup_time: float | None = None
        self._cleanup_in_progress = False

    def should_run_cleanup(self) -> bool:
        """Check if cleanup should run based on interval and current state"""
        if not self.enabled:
            return False

        if self._cleanup_in_progress:
            return False

        if self._last_cleanup_time is None:
            return True

        elapsed_minutes = (time.time() - self._last_cleanup_time) / 60
        return elapsed_minutes >= self.cleanup_interval_minutes

    async def trigger_cleanup_if_needed(self) -> dict[str, Any]:
        """
        Trigger cleanup if needed, runs in background without blocking.
        Returns status information.
        """
        if not self.should_run_cleanup():
            return {
                "cleanup_triggered": False,
                "reason": "not_needed" if self.enabled else "disabled",
                "last_cleanup": self._last_cleanup_time,
                "next_cleanup_in_minutes": self._get_next_cleanup_minutes(),
            }

        # Start cleanup in background (fire and forget)
        asyncio.create_task(self._run_cleanup_background())

        return {
            "cleanup_triggered": True,
            "max_age_hours": self.max_age_hours,
            "interval_minutes": self.cleanup_interval_minutes,
        }

    async def _run_cleanup_background(self) -> None:
        """Run the actual cleanup in background"""
        if self._cleanup_in_progress:
            return

        self._cleanup_in_progress = True
        try:
            cache_manager = get_cache_manager()
            cleared_count = await cache_manager.clear_old_entries(self.max_age_hours)
            self._last_cleanup_time = time.time()

            print(
                f"🧹 Auto-cleanup completed: {cleared_count} entries removed "
                f"(older than {self.max_age_hours}h)"
            )

        except Exception as e:
            print(f"⚠️ Auto-cleanup failed: {e}")
        finally:
            self._cleanup_in_progress = False

    def _get_next_cleanup_minutes(self) -> float | None:
        """Get minutes until next cleanup"""
        if not self.enabled or self._last_cleanup_time is None:
            return None

        elapsed_minutes = (time.time() - self._last_cleanup_time) / 60
        return max(0, self.cleanup_interval_minutes - elapsed_minutes)

    def get_status(self) -> dict[str, Any]:
        """Get current cleanup status"""
        return {
            "enabled": self.enabled,
            "cleanup_interval_minutes": self.cleanup_interval_minutes,
            "max_age_hours": self.max_age_hours,
            "last_cleanup_time": self._last_cleanup_time,
            "cleanup_in_progress": self._cleanup_in_progress,
            "next_cleanup_in_minutes": self._get_next_cleanup_minutes(),
        }


# Global instance
_auto_cleanup_manager: AutoCleanupManager | None = None


def get_auto_cleanup_manager() -> AutoCleanupManager:
    """Get the global auto cleanup manager instance"""
    global _auto_cleanup_manager
    if _auto_cleanup_manager is None:
        _auto_cleanup_manager = AutoCleanupManager()
    return _auto_cleanup_manager
