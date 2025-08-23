"""
Cache database manager

Copyright (c) 2025 Siarhei Skuratovich
Licensed under the MIT License - see LICENSE file for details
"""

import asyncio
import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import aiosqlite

from .models import CacheData, CacheStats

logger = logging.getLogger(__name__)


class CacheManager:
    """Manages cache database operations and lifecycle"""

    def __init__(self, db_path: str = "mcp_cache.db"):
        """Initialize cache manager with database path"""
        self.db_path = Path(db_path)
        self.ttl_config = {
            "pipeline": None,  # Never expires (pipelines are immutable)
            "job": 86400,  # 24 hours (jobs can be retried)
            "analysis": 604800,  # 7 days (analysis results are stable)
            "file_errors": 604800,  # 7 days (file errors are stable)
            "error": 604800,  # 7 days (individual errors are stable)
            "file_index": 3600,  # 1 hour (file listings change)
            "error_patterns": 21600,  # 6 hours (error patterns evolve)
        }
        self._initialized = False
        self._stats = CacheStats(
            total_entries=0,
            total_size_bytes=0,
            entries_by_type={},
            oldest_entry=None,
            newest_entry=None,
        )

    async def initialize(self) -> None:
        """Initialize database schema and create tables"""
        if self._initialized:
            return

        logger.info(f"Initializing cache database at {self.db_path}")

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS cache_metadata (
                    key TEXT PRIMARY KEY,
                    data_type TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    project_id TEXT NOT NULL,
                    pipeline_id INTEGER,
                    job_id INTEGER,
                    file_path TEXT,
                    parser_type TEXT,
                    data_size INTEGER DEFAULT 0
                )
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_project_pipeline
                ON cache_metadata(project_id, pipeline_id)
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_project_job
                ON cache_metadata(project_id, job_id)
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_expires_at
                ON cache_metadata(expires_at)
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_data_type
                ON cache_metadata(data_type)
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS cache_data (
                    key TEXT PRIMARY KEY REFERENCES cache_metadata(key) ON DELETE CASCADE,
                    json_data TEXT NOT NULL,
                    mcp_info TEXT NOT NULL
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS cleanup_log (
                    run_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    items_cleaned INTEGER,
                    space_freed INTEGER
                )
            """)

            await db.commit()

        self._initialized = True
        await self._update_stats()
        logger.info("Cache database initialized successfully")

    async def get(self, key: str) -> dict[str, Any] | None:
        """Get data from cache by key"""
        await self._ensure_initialized()

        async with (
            aiosqlite.connect(self.db_path) as db,
            db.execute(
                """
                SELECT cd.json_data, cd.mcp_info, cm.expires_at
                FROM cache_data cd
                JOIN cache_metadata cm ON cd.key = cm.key
                WHERE cd.key = ? AND (cm.expires_at IS NULL OR cm.expires_at > ?)
            """,
                (key, datetime.now(UTC)),
            ) as cursor,
        ):
            row = await cursor.fetchone()

            if row is None:
                return None

            json_data, mcp_info, expires_at = row
            data = CacheData.deserialize(json_data)

            # Always include mcp_info in response
            if "mcp_info" not in data and mcp_info:
                mcp_info_data = CacheData.deserialize(mcp_info)
                data["mcp_info"] = mcp_info_data

            return data

    async def set(
        self,
        key: str,
        data: dict[str, Any],
        data_type: str,
        project_id: str,
        pipeline_id: int | None = None,
        job_id: int | None = None,
        file_path: str | None = None,
        parser_type: str | None = None,
    ) -> None:
        """Store data in cache"""
        await self._ensure_initialized()

        # Extract mcp_info if present but don't remove from data
        mcp_info = data.get("mcp_info", {})
        mcp_info_json = CacheData.serialize(mcp_info)

        # Calculate expiration
        expires_at = None
        ttl_seconds = self.ttl_config.get(data_type)
        if ttl_seconds is not None:
            expires_at = datetime.now(UTC) + timedelta(seconds=ttl_seconds)

        # Serialize main data
        json_data = CacheData.serialize(data)
        data_size = CacheData.calculate_size(data)

        async with aiosqlite.connect(self.db_path) as db:
            # Insert or replace metadata
            await db.execute(
                """
                INSERT OR REPLACE INTO cache_metadata
                (key, data_type, project_id, pipeline_id, job_id, file_path, parser_type, expires_at, data_size)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    key,
                    data_type,
                    project_id,
                    pipeline_id,
                    job_id,
                    file_path,
                    parser_type,
                    expires_at,
                    data_size,
                ),
            )

            # Insert or replace data
            await db.execute(
                """
                INSERT OR REPLACE INTO cache_data
                (key, json_data, mcp_info)
                VALUES (?, ?, ?)
            """,
                (key, json_data, mcp_info_json),
            )

            await db.commit()

        await self._update_stats()
        logger.debug(
            f"Cached data for key: {key} (type: {data_type}, size: {data_size} bytes)"
        )

    async def get_or_compute(
        self,
        key: str,
        compute_func: Callable[[], Any],
        data_type: str,
        project_id: str,
        **kwargs,
    ) -> dict[str, Any]:
        """Get from cache or compute and store"""
        # Try to get from cache first
        cached_data = await self.get(key)
        if cached_data is not None:
            logger.debug(f"Cache hit for key: {key}")
            return cached_data

        logger.debug(f"Cache miss for key: {key}, computing...")

        # Compute the data
        if asyncio.iscoroutinefunction(compute_func):
            computed_data = await compute_func()
        else:
            computed_data = compute_func()

        # Store in cache
        await self.set(
            key=key,
            data=computed_data,
            data_type=data_type,
            project_id=project_id,
            **kwargs,
        )

        return computed_data

    async def invalidate_project(self, project_id: str) -> int:
        """Invalidate all cache entries for a project"""
        await self._ensure_initialized()

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                DELETE FROM cache_metadata WHERE project_id = ?
            """,
                (project_id,),
            )
            deleted_count = cursor.rowcount
            await db.commit()

        logger.info(
            f"Invalidated {deleted_count} cache entries for project {project_id}"
        )
        await self._update_stats()
        return deleted_count

    async def invalidate_pipeline(self, project_id: str, pipeline_id: int) -> int:
        """Invalidate cache entries for a specific pipeline"""
        await self._ensure_initialized()

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                DELETE FROM cache_metadata
                WHERE project_id = ? AND pipeline_id = ?
            """,
                (project_id, pipeline_id),
            )
            deleted_count = cursor.rowcount
            await db.commit()

        logger.info(
            f"Invalidated {deleted_count} cache entries for pipeline {project_id}/{pipeline_id}"
        )
        await self._update_stats()
        return deleted_count

    async def cleanup_expired(self) -> int:
        """Remove expired cache entries"""
        await self._ensure_initialized()

        current_time = datetime.now(UTC)

        async with aiosqlite.connect(self.db_path) as db:
            # Get size of expired entries before deletion
            async with db.execute(
                """
                SELECT COUNT(*), COALESCE(SUM(data_size), 0)
                FROM cache_metadata
                WHERE expires_at IS NOT NULL AND expires_at <= ?
            """,
                (current_time,),
            ) as cursor:
                count, size = await cursor.fetchone()

            # Delete expired entries
            await db.execute(
                """
                DELETE FROM cache_metadata
                WHERE expires_at IS NOT NULL AND expires_at <= ?
            """,
                (current_time,),
            )

            # Log cleanup
            await db.execute(
                """
                INSERT INTO cleanup_log (items_cleaned, space_freed)
                VALUES (?, ?)
            """,
                (count, size),
            )

            await db.commit()

        logger.info(f"Cleaned up {count} expired cache entries, freed {size} bytes")
        await self._update_stats()
        return count

    async def get_stats(self) -> CacheStats:
        """Get current cache statistics"""
        await self._update_stats()
        return self._stats

    async def _ensure_initialized(self) -> None:
        """Ensure database is initialized"""
        if not self._initialized:
            await self.initialize()

    async def _update_stats(self) -> None:
        """Update internal cache statistics"""
        if not self._initialized:
            return

        async with aiosqlite.connect(self.db_path) as db:
            # Get total entries and size
            async with db.execute("""
                SELECT COUNT(*), COALESCE(SUM(data_size), 0)
                FROM cache_metadata
            """) as cursor:
                total_entries, total_size = await cursor.fetchone()

            # Get entries by type
            entries_by_type = {}
            async with db.execute("""
                SELECT data_type, COUNT(*)
                FROM cache_metadata
                GROUP BY data_type
            """) as cursor:
                async for row in cursor:
                    data_type, count = row
                    entries_by_type[data_type] = count

            # Get oldest and newest entries
            async with db.execute("""
                SELECT MIN(created_at), MAX(created_at)
                FROM cache_metadata
            """) as cursor:
                oldest, newest = await cursor.fetchone()

            self._stats = CacheStats(
                total_entries=total_entries or 0,
                total_size_bytes=total_size or 0,
                entries_by_type=entries_by_type,
                oldest_entry=datetime.fromisoformat(oldest) if oldest else None,
                newest_entry=datetime.fromisoformat(newest) if newest else None,
            )

    async def close(self) -> None:
        """Close database connections and cleanup"""
        if self._initialized:
            logger.info("Cache manager closed")
            self._initialized = False


# Global cache manager instance
_cache_manager: CacheManager | None = None


def get_cache_manager(db_path: str = "mcp_cache.db") -> CacheManager:
    """Get or create global cache manager instance"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager(db_path)
    return _cache_manager
