"""
Base Formatter

Common formatting utilities and base classes for all formatters.

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseFormatter(ABC):
    """Base class for all formatters"""

    @abstractmethod
    def format(self, data: dict[str, Any], mode: str = "balanced") -> dict[str, Any]:
        """
        Format data based on the specified mode.

        Args:
            data: Raw data to format
            mode: Formatting mode (minimal, balanced, detailed, fixing)

        Returns:
            Formatted data
        """
        pass

    def optimize_for_mode(self, data: dict[str, Any], mode: str) -> dict[str, Any]:
        """
        Apply mode-specific optimizations to data.

        Args:
            data: Data to optimize
            mode: Target mode

        Returns:
            Optimized data
        """
        if mode == "minimal":
            return self._apply_minimal_optimization(data)
        elif mode == "detailed" or mode == "fixing":
            return self._apply_detailed_optimization(data)
        else:  # balanced
            return self._apply_balanced_optimization(data)

    def _apply_minimal_optimization(self, data: dict[str, Any]) -> dict[str, Any]:
        """Apply minimal mode optimization - remove verbose fields"""
        # Remove common verbose fields
        minimal_data = data.copy()
        verbose_fields = ["metadata", "cached_at", "debug_timing", "auto_cleanup"]
        for field in verbose_fields:
            minimal_data.pop(field, None)
        return minimal_data

    def _apply_balanced_optimization(self, data: dict[str, Any]) -> dict[str, Any]:
        """Apply balanced mode optimization - moderate detail level"""
        return data  # Balanced is usually the default, no changes needed

    def _apply_detailed_optimization(self, data: dict[str, Any]) -> dict[str, Any]:
        """Apply detailed mode optimization - include all available information"""
        return data  # Detailed mode includes everything
