"""
Version detection utility for GitLab Pipeline Analyzer

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

from pathlib import Path


def get_version() -> str:
    """Get version from package metadata or pyproject.toml"""
    # First try to read from pyproject.toml (prioritize local development)
    try:
        potential_paths = [
            # Relative to this file (for development)
            Path(__file__).parent / ".." / ".." / "pyproject.toml",
            # Look for it in the current working directory
            Path.cwd() / "pyproject.toml",
        ]

        for pyproject_path in potential_paths:
            if pyproject_path.exists():
                content = pyproject_path.read_text(encoding="utf-8")
                for line in content.split("\n"):
                    if line.startswith("version = "):
                        return line.split('"')[1]
    except Exception:  # nosec B110
        pass

    # Fallback to package metadata for installed packages
    try:
        try:
            from importlib.metadata import (
                version,
            )  # pylint: disable=import-outside-toplevel

            return version("gitlab-pipeline-analyzer")
        except ImportError:
            # Python < 3.8 compatibility
            import pkg_resources  # pylint: disable=import-outside-toplevel

            return pkg_resources.get_distribution("gitlab-pipeline-analyzer").version
    except Exception:  # nosec B110
        pass

    # Final fallback
    return "0.6.2-fallback"
