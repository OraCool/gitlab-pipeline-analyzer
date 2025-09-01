"""
MCP Cache manager for webhook-triggered analysis cache.

This implements the cache-first architecture where:
1. Webhook phase: Ingest pipeline/job data once, parse and persist
2. Serving phase: Fast resource access from cache
3. Invalidation: Based on job_id + trace_hash + parser_version

Enhanced with async operations, TTL management, and statistics.
"""

import contextlib
import gzip
import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any

import aiosqlite

from .models import ErrorRecord, JobRecord, PipelineRecord, generate_standard_error_id


class McpCache:
    """
    Cache-first analysis storage with SQLite backend.

    Implements the recommended architecture:
    - Webhook phase: Parse once, store immutable records
    - Serving phase: Fast resource access from cache
    - Invalidation: Based on job_id + trace_hash + parser_version
    """

    def __init__(self, db_path: str | None = None):
        # Use environment variable or default to "analysis_cache.db"
        if db_path is None:
            db_path = os.environ.get("MCP_DATABASE_PATH", "analysis_cache.db")

        self.db_path = Path(db_path)
        self.parser_version = (
            2  # Bump when parser logic changes - v2 adds error_type classification
        )

        # TTL configuration for different data types
        self.ttl_config = {
            "pipeline": None,  # Never expires (pipelines are immutable)
            "job": 86400,  # 24 hours (jobs can be retried)
            "analysis": 604800,  # 7 days (analysis results are stable)
            "file_errors": 604800,  # 7 days (file errors are stable)
            "error": 604800,  # 7 days (individual errors are stable)
        }

        self._initialized = False
        self._init_database()

    def _init_database(self):
        """Initialize database schema with comprehensive debug information"""
        try:
            # Debug info: Database path and environment
            print(f"🔧 [DEBUG] Initializing database at: {self.db_path}")
            print(f"🔧 [DEBUG] Database path type: {type(self.db_path)}")
            print(f"🔧 [DEBUG] Database path absolute: {self.db_path.resolve()}")
            print(f"🔧 [DEBUG] Database path exists: {self.db_path.exists()}")

            # Check parent directory
            parent_dir = self.db_path.parent
            print(f"🔧 [DEBUG] Parent directory: {parent_dir}")
            print(f"🔧 [DEBUG] Parent directory exists: {parent_dir.exists()}")
            print(
                f"🔧 [DEBUG] Parent directory writable: "
                f"{os.access(parent_dir, os.W_OK) if parent_dir.exists() else 'N/A'}"
            )

            # Check file permissions if database exists
            if self.db_path.exists():
                print(
                    f"🔧 [DEBUG] Database file readable: {os.access(self.db_path, os.R_OK)}"
                )
                print(
                    f"🔧 [DEBUG] Database file writable: {os.access(self.db_path, os.W_OK)}"
                )
                print(
                    f"🔧 [DEBUG] Database file size: {self.db_path.stat().st_size} bytes"
                )

            # Environment variables debug
            mcp_db_path = os.environ.get("MCP_DATABASE_PATH")
            print(f"🔧 [DEBUG] MCP_DATABASE_PATH env var: {mcp_db_path}")
            print(f"🔧 [DEBUG] Current working directory: {Path.cwd()}")

            print("🔧 [DEBUG] Attempting to connect to SQLite database...")

        except Exception as e:
            print(f"❌ [ERROR] Failed during database path checks: {e}")
            print(f"❌ [ERROR] Exception type: {type(e).__name__}")
            raise

        try:
            with sqlite3.connect(self.db_path) as conn:
                print("✅ [DEBUG] Successfully connected to SQLite database")
                print("🔧 [DEBUG] Creating database schema...")

                conn.executescript(
                    """
                -- Pipelines table: pipeline metadata and branch resolution
                CREATE TABLE IF NOT EXISTS pipelines (
                    pipeline_id INTEGER PRIMARY KEY,
                    project_id INTEGER NOT NULL,
                    ref TEXT NOT NULL,
                    sha TEXT NOT NULL,
                    status TEXT NOT NULL,
                    web_url TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP,
                    source_branch TEXT,  -- Resolved source branch for MR pipelines
                    target_branch TEXT   -- Target branch for MR pipelines
                );

                -- Jobs table: core job metadata
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id INTEGER PRIMARY KEY,
                    project_id INTEGER NOT NULL,
                    pipeline_id INTEGER NOT NULL,
                    ref TEXT NOT NULL,
                    sha TEXT NOT NULL,
                    status TEXT NOT NULL,
                    trace_hash TEXT NOT NULL,
                    parser_version INTEGER NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    completed_at TIMESTAMP,
                    UNIQUE(job_id, trace_hash, parser_version),
                    FOREIGN KEY (pipeline_id) REFERENCES pipelines(pipeline_id)
                );

                -- Trace segments table: error-specific trace context
                CREATE TABLE IF NOT EXISTS trace_segments (
                    job_id INTEGER NOT NULL,
                    error_id TEXT NOT NULL,
                    error_fingerprint TEXT NOT NULL,
                    trace_segment_gzip BLOB NOT NULL,
                    context_before INTEGER DEFAULT 10,
                    context_after INTEGER DEFAULT 10,
                    error_line_start INTEGER,
                    error_line_end INTEGER,
                    original_trace_hash TEXT NOT NULL,
                    parser_type TEXT NOT NULL,
                    parser_version INTEGER NOT NULL,
                    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    segment_size INTEGER NOT NULL,
                    PRIMARY KEY (job_id, error_id),
                    FOREIGN KEY (job_id) REFERENCES jobs(job_id)
                );

                -- Errors table: individual error records for fast filtering
                CREATE TABLE IF NOT EXISTS errors (
                    job_id INTEGER NOT NULL,
                    error_id TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,
                    exception TEXT NOT NULL,
                    message TEXT NOT NULL,
                    file TEXT NOT NULL,
                    line INTEGER NOT NULL,
                    detail_json TEXT NOT NULL,
                    error_type TEXT DEFAULT 'unknown',
                    PRIMARY KEY (job_id, error_id),
                    FOREIGN KEY (job_id) REFERENCES jobs(job_id)
                );

                -- File index: fast file-based error lookup
                CREATE TABLE IF NOT EXISTS file_index (
                    job_id INTEGER NOT NULL,
                    path TEXT NOT NULL,
                    error_ids TEXT NOT NULL,  -- JSON array of error_ids
                    PRIMARY KEY (job_id, path),
                    FOREIGN KEY (job_id) REFERENCES jobs(job_id)
                );

                -- Indexes for performance
                CREATE INDEX IF NOT EXISTS idx_jobs_pipeline ON jobs(pipeline_id);
                CREATE INDEX IF NOT EXISTS idx_jobs_project ON jobs(project_id);
                CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
                CREATE INDEX IF NOT EXISTS idx_errors_fingerprint ON errors(fingerprint);
                CREATE INDEX IF NOT EXISTS idx_errors_file ON errors(file);
                CREATE INDEX IF NOT EXISTS idx_errors_error_type ON errors(error_type);
                CREATE INDEX IF NOT EXISTS idx_file_index_path ON file_index(path);
                """
                )

                # Migration: Add error_type column if it doesn't exist (for existing databases)
                cursor = conn.execute(
                    """
                    PRAGMA table_info(errors)
                    """
                )
                columns = [row[1] for row in cursor.fetchall()]
                if "error_type" not in columns:
                    conn.execute(
                        """
                        ALTER TABLE errors ADD COLUMN error_type TEXT DEFAULT 'unknown'
                        """
                    )
                    conn.execute(
                        """
                        CREATE INDEX IF NOT EXISTS idx_errors_error_type ON errors(error_type)
                        """
                    )
                    conn.commit()

                print("✅ [DEBUG] Database schema created/verified successfully")
                print(
                    f"✅ [DEBUG] Database initialization completed at: {self.db_path}"
                )

        except sqlite3.OperationalError as e:
            print("❌ [ERROR] SQLite Operational Error during database initialization:")
            print(f"❌ [ERROR] Error message: {e}")
            print(f"❌ [ERROR] Database path: {self.db_path}")
            print(
                "❌ [ERROR] This usually indicates permission issues or disk space problems"
            )

            # Additional disk space check
            try:
                import shutil

                free_space = shutil.disk_usage(self.db_path.parent).free
                print(
                    f"🔧 [DEBUG] Available disk space: {free_space / 1024 / 1024:.2f} MB"
                )
            except Exception as disk_e:
                print(f"🔧 [DEBUG] Could not check disk space: {disk_e}")
            raise

        except sqlite3.DatabaseError as e:
            print("❌ [ERROR] SQLite Database Error during initialization:")
            print(f"❌ [ERROR] Error message: {e}")
            print(f"❌ [ERROR] Database path: {self.db_path}")
            print(
                "❌ [ERROR] This might indicate database corruption or version incompatibility"
            )
            raise

        except PermissionError as e:
            print("❌ [ERROR] Permission Error during database initialization:")
            print(f"❌ [ERROR] Error message: {e}")
            print(f"❌ [ERROR] Database path: {self.db_path}")
            print("❌ [ERROR] Check file/directory permissions for the database path")

            # Show detailed permission info
            if self.db_path.exists():
                stat_info = self.db_path.stat()
                import stat as stat_module

                mode = stat_module.filemode(stat_info.st_mode)
                print(f"🔧 [DEBUG] Current file permissions: {mode}")
                print(f"🔧 [DEBUG] File owner UID: {stat_info.st_uid}")
                print(f"🔧 [DEBUG] Current process UID: {os.getuid()}")
            raise

        except OSError as e:
            print("❌ [ERROR] OS Error during database initialization:")
            print(f"❌ [ERROR] Error message: {e}")
            print(f"❌ [ERROR] Error code: {e.errno if hasattr(e, 'errno') else 'N/A'}")
            print(f"❌ [ERROR] Database path: {self.db_path}")
            print("❌ [ERROR] This might indicate filesystem issues or path problems")
            raise

        except Exception as e:
            print("❌ [ERROR] Unexpected error during database initialization:")
            print(f"❌ [ERROR] Error type: {type(e).__name__}")
            print(f"❌ [ERROR] Error message: {e}")
            print(f"❌ [ERROR] Database path: {self.db_path}")

            # Add traceback for debugging
            import traceback

            print("❌ [ERROR] Traceback:")
            traceback.print_exc()
            raise

    def is_job_cached(self, job_id: int, trace_hash: str) -> bool:
        """Check if job is already cached with current parser version"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT 1 FROM jobs WHERE job_id = ? AND trace_hash = ? AND parser_version = ?",
                (job_id, trace_hash, self.parser_version),
            )
            return cursor.fetchone() is not None

    def store_job_analysis(
        self, job_record: JobRecord, trace_text: str, parsed_data: dict[str, Any]
    ):
        """Store complete job analysis (webhook phase)"""
        with sqlite3.connect(self.db_path) as conn:
            # Store job metadata
            conn.execute(
                """
                INSERT OR REPLACE INTO jobs
                (job_id, project_id, pipeline_id, ref, sha, status, trace_hash, parser_version, created_at, completed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    job_record.job_id,
                    job_record.project_id,
                    job_record.pipeline_id,
                    job_record.ref,
                    job_record.sha,
                    job_record.status,
                    job_record.trace_hash,
                    job_record.parser_version,
                    job_record.created_at,
                    job_record.completed_at,
                ),
            )

            # Note: Trace storage is handled by store_error_trace_segments method
            # which stores trace segments per error with context
            # The raw trace is not stored in this method to avoid duplication

            # Store individual errors and build file index
            self._store_errors_and_file_index(conn, job_record.job_id, parsed_data)

    def _store_errors_and_file_index(
        self, conn: sqlite3.Connection, job_id: int, parsed_data: dict[str, Any]
    ):
        """Store errors and build file index"""
        # Clear existing records
        conn.execute("DELETE FROM errors WHERE job_id = ?", (job_id,))
        conn.execute("DELETE FROM file_index WHERE job_id = ?", (job_id,))

        errors = parsed_data.get("errors", [])
        file_errors: dict[str, list[str]] = {}  # file_path -> [error_ids]

        for i, error_data in enumerate(errors):
            error_record = ErrorRecord.from_parsed_error(job_id, error_data, i)

            # Store error
            conn.execute(
                """
                INSERT INTO errors
                (job_id, error_id, fingerprint, exception, message, file, line, detail_json, error_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    error_record.job_id,
                    error_record.error_id,
                    error_record.fingerprint,
                    error_record.exception,
                    error_record.message,
                    error_record.file,
                    error_record.line,
                    json.dumps(error_record.detail_json),
                    error_record.error_type,
                ),
            )

            # Build file index
            file_path = error_record.file
            if file_path:
                if file_path not in file_errors:
                    file_errors[file_path] = []
                file_errors[file_path].append(error_record.error_id)

        # Store file index
        for file_path, error_ids in file_errors.items():
            conn.execute(
                "INSERT INTO file_index (job_id, path, error_ids) VALUES (?, ?, ?)",
                (job_id, file_path, json.dumps(error_ids)),
            )

    def store_errors_only(self, job_id: int, parsed_data: dict[str, Any]):
        """Store only errors and file index without overwriting job metadata"""
        with sqlite3.connect(self.db_path) as conn:
            # Store only errors and file index - do not touch job metadata
            self._store_errors_and_file_index(conn, job_id, parsed_data)

    def store_pipeline_info(self, pipeline_record: PipelineRecord):
        """Store pipeline information (legacy sync method - use store_pipeline_info_async instead)

        DEPRECATED: This method is kept for backward compatibility only.
        Use store_pipeline_info_async() for new code as it follows the async pattern.
        """
        # Deprecated: Use async version store_pipeline_info_async instead
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO pipelines
                (pipeline_id, project_id, ref, sha, status, web_url, created_at, updated_at, source_branch, target_branch)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    pipeline_record.pipeline_id,
                    pipeline_record.project_id,
                    pipeline_record.ref,
                    pipeline_record.sha,
                    pipeline_record.status,
                    pipeline_record.web_url,
                    pipeline_record.created_at,
                    pipeline_record.updated_at,
                    pipeline_record.source_branch,
                    pipeline_record.target_branch,
                ),
            )

    def get_pipeline_info(self, pipeline_id: int) -> dict[str, Any] | None:
        """Get pipeline information from cache"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT pipeline_id, project_id, ref, sha, status, web_url,
                       created_at, updated_at, source_branch, target_branch
                FROM pipelines WHERE pipeline_id = ?
            """,
                (pipeline_id,),
            )
            row = cursor.fetchone()
            if row:
                return {
                    "pipeline_id": row[0],
                    "project_id": row[1],
                    "ref": row[2],
                    "sha": row[3],
                    "status": row[4],
                    "web_url": row[5],
                    "created_at": row[6],
                    "updated_at": row[7],
                    "source_branch": row[8],
                    "target_branch": row[9],
                }
            return None

    async def store_pipeline_info_async(
        self, project_id: str | int, pipeline_id: int, pipeline_info: dict
    ) -> None:
        """Store pipeline information asynchronously from dict data"""
        try:
            pipeline_data = pipeline_info.get("pipeline_info", {})
            if not pipeline_data:
                return

            # Extract real branch information
            pipeline_type = pipeline_info.get("pipeline_type", "branch")
            target_branch = pipeline_info.get("target_branch")
            source_branch = None

            if pipeline_type == "merge_request":
                merge_request_info = pipeline_info.get("merge_request_info", {})
                if (
                    isinstance(merge_request_info, dict)
                    and "error" not in merge_request_info
                ):
                    source_branch = merge_request_info.get("source_branch")
                    target_branch = merge_request_info.get("target_branch")
                else:
                    source_branch = target_branch
                    target_branch = "unknown"
            else:
                source_branch = target_branch
                target_branch = None

            # Store in pipelines table
            async with aiosqlite.connect(self.db_path) as db:
                data_to_store = (
                    pipeline_id,
                    int(project_id),
                    pipeline_data.get("ref", ""),
                    pipeline_data.get("sha", ""),
                    pipeline_data.get("status", ""),
                    pipeline_data.get("web_url", ""),
                    pipeline_data.get("created_at", ""),
                    pipeline_data.get("updated_at", ""),
                    source_branch,
                    target_branch,
                )

                await db.execute(
                    """
                    INSERT OR REPLACE INTO pipelines
                    (pipeline_id, project_id, ref, sha, status, web_url, created_at, updated_at, source_branch, target_branch)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    data_to_store,
                )
                await db.commit()

        except Exception as e:
            print(f"Error storing pipeline info: {e}")

    async def store_failed_jobs_basic(
        self,
        project_id: str | int,
        pipeline_id: int,
        failed_jobs: list,
        pipeline_info: dict,
    ) -> None:
        """Store basic failed job information asynchronously"""
        try:
            if not failed_jobs:
                return

            # Extract pipeline data correctly from nested structure
            pipeline_data = pipeline_info.get("pipeline_info", {})
            ref = pipeline_data.get("ref", "unknown")
            sha = pipeline_data.get("sha", "unknown")

            # Using ref='{ref}', sha='{sha}' for jobs

            async with aiosqlite.connect(self.db_path) as db:
                for job in failed_jobs:
                    # Generate meaningful trace hash based on job
                    trace_hash = (
                        f"job_{job.id}_{sha[:8]}"
                        if sha != "unknown"
                        else f"job_{job.id}"
                    )

                    await db.execute(
                        """
                        INSERT OR REPLACE INTO jobs
                        (job_id, project_id, pipeline_id, ref, sha, status, trace_hash,
                         parser_version, created_at, completed_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            job.id,
                            int(project_id),
                            pipeline_id,
                            ref,
                            sha,
                            job.status,
                            trace_hash,
                            self.parser_version,  # Use proper parser version
                            job.created_at,
                            job.finished_at,
                        ),
                    )
                await db.commit()

        except Exception as e:
            print(f"ERROR: Failed to store failed jobs: {e}")
            import traceback

            traceback.print_exc()
            raise

    async def store_job_file_errors(
        self,
        project_id: str | int,
        pipeline_id: int,
        job_id: int,
        files: list[dict],
        errors: list[dict],
        parser_type: str,
    ) -> None:
        """Store file and error information for a job asynchronously"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Store individual errors
                for i, error in enumerate(errors):
                    error_id = generate_standard_error_id(job_id, i)
                    fingerprint = f"{error.get('exception_type', 'unknown')}_{error.get('file_path', 'unknown')}_{error.get('line_number', 0)}"

                    await db.execute(
                        """
                        INSERT OR REPLACE INTO errors
                        (job_id, error_id, fingerprint, exception, message, file, line, detail_json)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            job_id,
                            error_id,
                            fingerprint,
                            error.get("exception_type", "unknown"),
                            error.get("exception_message", "")
                            or error.get("message", ""),
                            error.get("file_path", "unknown"),
                            error.get("line_number", 0) or 0,  # Default to 0 if None
                            json.dumps(error),
                        ),
                    )  # Store file index for fast file-based lookups
                for file_group in files:
                    file_path = file_group["file_path"]
                    error_ids = []

                    # Find error IDs for this file
                    for i, error in enumerate(errors):
                        error_file = error.get("file_path", "unknown")
                        if error_file == file_path or (
                            error_file == "unknown" and file_path == "unknown"
                        ):
                            error_ids.append(generate_standard_error_id(job_id, i))

                    if error_ids:  # Only store if there are errors for this file
                        await db.execute(
                            """
                            INSERT OR REPLACE INTO file_index
                            (job_id, path, error_ids)
                            VALUES (?, ?, ?)
                            """,
                            (
                                job_id,
                                file_path,
                                json.dumps(error_ids),
                            ),
                        )

                await db.commit()

        except Exception as e:
            print(f"ERROR: Failed to store job file errors: {e}")
            import traceback

            traceback.print_exc()
            raise

    async def store_error_trace_segments(
        self,
        job_id: int,
        trace_text: str,
        trace_hash: str,
        errors: list[ErrorRecord],
        parser_type: str,
        context_lines: int = 15,
    ) -> None:
        """Store trace segments for each error with context"""
        try:
            trace_lines = trace_text.split("\n")

            async with aiosqlite.connect(self.db_path) as db:
                for error in errors:
                    # Extract trace segment with context using utility function
                    from gitlab_analyzer.utils.trace_utils import (
                        extract_error_trace_segment,
                    )

                    segment_lines, start_line, end_line = extract_error_trace_segment(
                        trace_lines, error, context_lines
                    )

                    segment_text = "\n".join(segment_lines)
                    segment_gzip = gzip.compress(segment_text.encode("utf-8"))

                    await db.execute(
                        """INSERT OR REPLACE INTO trace_segments
                        (job_id, error_id, error_fingerprint, trace_segment_gzip,
                         context_before, context_after, error_line_start, error_line_end,
                         original_trace_hash, parser_type, parser_version, segment_size)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            job_id,
                            error.error_id,
                            error.fingerprint,
                            segment_gzip,
                            context_lines,
                            context_lines,
                            start_line,
                            end_line,
                            trace_hash,
                            parser_type,
                            self.parser_version,
                            len(segment_text),
                        ),
                    )

                await db.commit()

        except Exception as e:
            print(f"ERROR: Failed to store trace segments: {e}")
            import traceback

            traceback.print_exc()

    async def get_pipeline_jobs(self, pipeline_id: int) -> list[dict[str, Any]]:
        """Get all jobs for a pipeline"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT job_id, project_id, ref, sha, status, created_at, completed_at
                FROM jobs
                WHERE pipeline_id = ?
                ORDER BY created_at
                """,
                (pipeline_id,),
            )

            jobs = []
            async for row in cursor:
                jobs.append(
                    {
                        "job_id": row[0],
                        "project_id": row[1],
                        "ref": row[2],
                        "sha": row[3],
                        "status": row[4],
                        "created_at": row[5],
                        "completed_at": row[6],
                    }
                )
            return jobs

    async def get_pipeline_info_async(self, pipeline_id: int) -> dict[str, Any] | None:
        """Get pipeline information from cache asynchronously"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT pipeline_id, project_id, ref, sha, status, web_url,
                       created_at, updated_at, source_branch, target_branch
                FROM pipelines WHERE pipeline_id = ?
                """,
                (pipeline_id,),
            )
            row = await cursor.fetchone()
            if row:
                return {
                    "pipeline_id": row[0],
                    "project_id": row[1],
                    "ref": row[2],
                    "sha": row[3],
                    "status": row[4],
                    "web_url": row[5],
                    "created_at": row[6],
                    "updated_at": row[7],
                    "source_branch": row[8],
                    "target_branch": row[9],
                }
            return None

    async def check_pipeline_analysis_status(
        self, project_id: int, pipeline_id: int
    ) -> dict[str, Any]:
        """Check if a pipeline has been analyzed and what data is available"""
        async with aiosqlite.connect(self.db_path) as db:
            # Check if pipeline exists
            pipeline_cursor = await db.execute(
                "SELECT pipeline_id, status FROM pipelines WHERE pipeline_id = ?",
                (pipeline_id,),
            )
            pipeline_row = await pipeline_cursor.fetchone()

            if not pipeline_row:
                return {
                    "pipeline_exists": False,
                    "jobs_count": 0,
                    "errors_count": 0,
                    "files_count": 0,
                    "recommendation": f"Pipeline {pipeline_id} not found in database. Run failed_pipeline_analysis tool first.",
                    "suggested_action": f"failed_pipeline_analysis(project_id={project_id}, pipeline_id={pipeline_id})",
                }

            # Count jobs
            jobs_cursor = await db.execute(
                "SELECT COUNT(*) FROM jobs WHERE pipeline_id = ?", (pipeline_id,)
            )
            jobs_row = await jobs_cursor.fetchone()
            jobs_count = jobs_row[0] if jobs_row else 0

            # Count errors
            errors_cursor = await db.execute(
                """
                SELECT COUNT(*) FROM errors e
                JOIN jobs j ON e.job_id = j.job_id
                WHERE j.pipeline_id = ?
                """,
                (pipeline_id,),
            )
            errors_row = await errors_cursor.fetchone()
            errors_count = errors_row[0] if errors_row else 0

            # Count files with errors
            files_cursor = await db.execute(
                """
                SELECT COUNT(DISTINCT fi.path) FROM file_index fi
                JOIN jobs j ON fi.job_id = j.job_id
                WHERE j.pipeline_id = ? AND fi.error_ids IS NOT NULL AND fi.error_ids != '[]'
                """,
                (pipeline_id,),
            )
            files_row = await files_cursor.fetchone()
            files_count = files_row[0] if files_row else 0

            return {
                "pipeline_exists": True,
                "pipeline_status": pipeline_row[1],
                "jobs_count": jobs_count,
                "errors_count": errors_count,
                "files_count": files_count,
                "recommendation": self._get_analysis_recommendation(
                    jobs_count, errors_count, files_count, project_id, pipeline_id
                ),
                "suggested_action": (
                    None
                    if jobs_count > 0
                    else f"failed_pipeline_analysis(project_id={project_id}, pipeline_id={pipeline_id})"
                ),
            }

    def _get_analysis_recommendation(
        self,
        jobs_count: int,
        errors_count: int,
        files_count: int,
        project_id: int,
        pipeline_id: int,
    ) -> str:
        """Generate recommendation based on analysis status"""
        if jobs_count == 0:
            return f"No jobs found for pipeline {pipeline_id}. Run failed_pipeline_analysis first."
        elif errors_count == 0:
            return f"Pipeline {pipeline_id} has {jobs_count} jobs but no errors found. Pipeline might have succeeded or analysis incomplete."
        elif files_count == 0:
            return f"Pipeline {pipeline_id} has {errors_count} errors but no files indexed. Analysis might be incomplete."
        else:
            return f"Pipeline {pipeline_id} analysis complete: {jobs_count} jobs, {errors_count} errors across {files_count} files."

    async def get_job_files_with_errors(self, job_id: int) -> list[dict[str, Any]]:
        """Get all files with errors for a specific job"""
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.execute(
                "SELECT path, error_ids FROM file_index WHERE job_id = ? AND error_ids IS NOT NULL AND error_ids != '[]'",
                (job_id,),
            )
            rows = await cursor.fetchall()
            files = []
            for row in rows:
                path, error_ids_json = row
                try:
                    error_ids = json.loads(error_ids_json) if error_ids_json else []
                    if error_ids:  # Only include files that actually have errors
                        # Get the actual error details for this file
                        error_cursor = await conn.execute(
                            f"""
                            SELECT error_id, fingerprint, exception, message, file, line, detail_json
                            FROM errors
                            WHERE job_id = ? AND error_id IN ({",".join("?" * len(error_ids))})
                            ORDER BY line
                            """,  # nosec B608
                            [job_id] + error_ids,
                        )
                        error_rows = await error_cursor.fetchall()

                        errors = []
                        for error_row in error_rows:
                            error_data = {
                                "error_id": error_row[0],
                                "fingerprint": error_row[1],
                                "exception": error_row[2],
                                "message": error_row[3],
                                "file_path": error_row[
                                    4
                                ],  # Use file_path instead of file
                                "line": error_row[5],
                            }
                            if error_row[6]:  # detail_json
                                with contextlib.suppress(json.JSONDecodeError):
                                    error_data["detail"] = json.loads(error_row[6])
                            errors.append(error_data)

                        files.append(
                            {
                                "file_path": path,  # Use file_path instead of path
                                "error_count": len(error_ids),
                                "errors": errors,  # Include full error details
                            }
                        )
                except json.JSONDecodeError:
                    # Skip files with invalid JSON
                    continue
            return files

    async def get_job_info_async(self, job_id: int) -> dict[str, Any] | None:
        """Get job information from cache asynchronously"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT job_id, project_id, pipeline_id, ref, sha, status,
                       trace_hash, parser_version, created_at, completed_at
                FROM jobs
                WHERE job_id = ?
                """,
                (job_id,),
            )
            row = await cursor.fetchone()
            if row:
                return {
                    "job_id": row[0],
                    "project_id": row[1],
                    "pipeline_id": row[2],
                    "ref": row[3],
                    "sha": row[4],
                    "status": row[5],
                    "trace_hash": row[6],
                    "parser_version": row[7],
                    "created_at": row[8],
                    "completed_at": row[9],
                }
            return None

    def get_job_errors(self, job_id: int) -> list[dict[str, Any]]:
        """Get all errors for a specific job (serving phase)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT error_id, fingerprint, exception, message, file, line, detail_json, error_type
                FROM errors
                WHERE job_id = ?
                ORDER BY file, line
                """,
                (job_id,),
            )

            errors = []
            for row in cursor:
                error_data = {
                    "id": row[0],
                    "fingerprint": row[1],
                    "exception": row[2],
                    "message": row[3],
                    "file_path": row[4],
                    "line": row[5],
                    "error_type": row[7],  # Added error_type field
                }

                # Parse additional details if available
                if row[6]:
                    try:
                        detail_data = json.loads(row[6])
                        error_data.update(detail_data)
                    except json.JSONDecodeError:
                        pass

                errors.append(error_data)

            return errors

    def get_file_errors(self, job_id: int, file_path: str) -> list[dict[str, Any]]:
        """Get errors for a specific file (serving phase)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT error_ids FROM file_index WHERE job_id = ? AND path = ?",
                (job_id, file_path),
            )
            row = cursor.fetchone()
            if not row:
                return []

            error_ids = json.loads(row[0])
            placeholders = ",".join("?" * len(error_ids))
            cursor = conn.execute(
                f"""
                SELECT error_id, fingerprint, exception, message, file, line, detail_json, error_type
                FROM errors
                WHERE job_id = ? AND error_id IN ({placeholders})
                ORDER BY line
            """,  # nosec B608
                [job_id] + error_ids,
            )

            results = []
            for row in cursor.fetchall():
                error_data = {
                    "error_id": row[0],
                    "fingerprint": row[1],
                    "exception": row[2],
                    "message": row[3],
                    "file": row[4],
                    "line": row[5],
                    "error_type": row[7],  # Added error_type field
                }
                # Parse detail JSON safely
                try:
                    error_data["detail"] = json.loads(row[6]) if row[6] else {}
                except (json.JSONDecodeError, TypeError):
                    error_data["detail"] = {}
                results.append(error_data)

            return results

    def get_pipeline_failed_jobs(self, pipeline_id: int) -> list[dict[str, Any]]:
        """Get failed jobs for a pipeline (serving phase)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT job_id, project_id, ref, sha, status, created_at, completed_at
                FROM jobs
                WHERE pipeline_id = ? AND status = 'failed'
                ORDER BY created_at
            """,
                (pipeline_id,),
            )

            return [
                {
                    "job_id": row[0],
                    "project_id": row[1],
                    "ref": row[2],
                    "sha": row[3],
                    "status": row[4],
                    "created_at": row[5],
                    "completed_at": row[6],
                }
                for row in cursor.fetchall()
            ]

    def get_job_trace_excerpt(
        self, job_id: int, error_id: str, mode: str = "balanced"
    ) -> str | None:
        """Get trace excerpt for specific error from stored segments"""
        with sqlite3.connect(self.db_path) as conn:
            # Get trace segment directly for this error
            cursor = conn.execute(
                "SELECT trace_segment_gzip FROM trace_segments WHERE job_id = ? AND error_id = ?",
                (job_id, error_id),
            )
            segment_row = cursor.fetchone()
            if not segment_row:
                return None

            # Decompress segment - it already contains the relevant context
            segment_text = gzip.decompress(segment_row[0]).decode("utf-8")

            # For backwards compatibility, we can still apply mode-based filtering
            # but the segment already has appropriate context
            if mode == "minimal":
                # Return just a few lines around the error
                lines = segment_text.split("\n")
                mid = len(lines) // 2
                start = max(0, mid - 3)
                end = min(len(lines), mid + 4)
                return "\n".join(lines[start:end])
            else:
                # Return the full stored segment (already has balanced context)
                return segment_text

    def _extract_trace_excerpt(
        self, trace_text: str, error_detail: dict[str, Any], mode: str
    ) -> str:
        """Extract relevant trace excerpt based on mode"""
        lines = trace_text.split("\n")
        error_line = error_detail.get("line", 0)

        if mode == "minimal":
            context = 2
        elif mode == "balanced":
            context = 5
        elif mode == "full":
            context = 20
        else:
            context = 5

        start = max(0, error_line - context)
        end = min(len(lines), error_line + context)

        excerpt_lines = []
        for i in range(start, end):
            marker = ">>> " if i == error_line else "    "
            excerpt_lines.append(f"{marker}{i + 1:4d}: {lines[i]}")

        return "\n".join(excerpt_lines)

    async def cleanup_expired(self) -> int:
        """Remove expired cache entries (async version)"""
        async with aiosqlite.connect(self.db_path) as db:
            # Get count of expired entries
            async with db.execute(
                """
                SELECT COUNT(*) FROM jobs
                WHERE parser_version < ?
                """,
                (self.parser_version,),
            ) as cursor:
                result = await cursor.fetchone()
                count = result[0] if result else 0

            # Delete old parser version records
            await db.execute(
                "DELETE FROM jobs WHERE parser_version < ?", (self.parser_version,)
            )

            # Cascade delete orphaned records
            await db.execute(
                "DELETE FROM trace_segments WHERE job_id NOT IN (SELECT job_id FROM jobs)"
            )
            await db.execute(
                "DELETE FROM errors WHERE job_id NOT IN (SELECT job_id FROM jobs)"
            )
            await db.execute(
                "DELETE FROM file_index WHERE job_id NOT IN (SELECT job_id FROM jobs)"
            )

            await db.commit()

        return count

    async def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics (async version)"""
        async with aiosqlite.connect(self.db_path) as db:
            # Get total entries and pipeline count
            async with db.execute("SELECT COUNT(*) FROM jobs") as cursor:
                result = await cursor.fetchone()
                total_jobs = result[0] if result else 0

            async with db.execute("SELECT COUNT(*) FROM pipelines") as cursor:
                result = await cursor.fetchone()
                total_pipelines = result[0] if result else 0

            # Get parser version distribution
            parser_versions = {}
            async with db.execute(
                "SELECT parser_version, COUNT(*) FROM jobs GROUP BY parser_version"
            ) as cursor:
                async for row in cursor:
                    parser_versions[row[0]] = row[1]

            return {
                "total_jobs": total_jobs,
                "total_pipelines": total_pipelines,
                "parser_versions": parser_versions,
                "current_parser_version": self.parser_version,
            }

    def cleanup_old_versions(self):
        """Clean up records from old parser versions"""
        with sqlite3.connect(self.db_path) as conn:
            # Keep only current parser version
            conn.execute(
                "DELETE FROM jobs WHERE parser_version < ?", (self.parser_version,)
            )

            # Cascade delete orphaned records
            conn.execute(
                """
                DELETE FROM trace_segments WHERE job_id NOT IN (SELECT job_id FROM jobs)
            """
            )
            conn.execute(
                """
                DELETE FROM errors WHERE job_id NOT IN (SELECT job_id FROM jobs)
            """
            )
            conn.execute(
                """
                DELETE FROM file_index WHERE job_id NOT IN (SELECT job_id FROM jobs)
            """
            )

    async def clear_old_entries(self, max_age_hours: int) -> int:
        """Clear cache entries older than specified hours"""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                # Calculate cutoff timestamp
                cutoff_sql = f"datetime('now', '-{max_age_hours} hours')"

                # Count entries to be deleted
                cursor = await conn.execute(
                    f"""
                    SELECT COUNT(*) FROM (
                        SELECT 1 FROM jobs WHERE created_at < {cutoff_sql}
                        UNION ALL
                        SELECT 1 FROM errors WHERE created_at < {cutoff_sql}
                        UNION ALL
                        SELECT 1 FROM file_index WHERE created_at < {cutoff_sql}
                    )
                    """  # nosec B608
                )
                count_row = await cursor.fetchone()
                count = count_row[0] if count_row else 0

                # Delete old entries
                await conn.execute(f"DELETE FROM jobs WHERE created_at < {cutoff_sql}")  # nosec B608
                await conn.execute(
                    f"DELETE FROM errors WHERE created_at < {cutoff_sql}"  # nosec B608
                )
                await conn.execute(
                    f"DELETE FROM file_index WHERE created_at < {cutoff_sql}"  # nosec B608
                )
                await conn.commit()

                return count
        except Exception:
            return 0

    async def clear_all_cache(self, project_id: str | int | None = None) -> int:
        """Clear all cache entries, optionally for specific project"""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                if project_id:
                    # Count entries for specific project (using JOIN/subquery for all related tables)
                    cursor = await conn.execute(
                        """
                        SELECT COUNT(*) FROM (
                            SELECT 1 FROM jobs WHERE project_id = ?
                            UNION ALL
                            SELECT 1 FROM errors e
                            JOIN jobs j ON e.job_id = j.job_id
                            WHERE j.project_id = ?
                            UNION ALL
                            SELECT 1 FROM file_index fi
                            JOIN jobs j ON fi.job_id = j.job_id
                            WHERE j.project_id = ?
                            UNION ALL
                            SELECT 1 FROM trace_segments ts
                            JOIN jobs j ON ts.job_id = j.job_id
                            WHERE j.project_id = ?
                            UNION ALL
                            SELECT 1 FROM pipelines WHERE project_id = ?
                        )
                        """,
                        (
                            str(project_id),
                            str(project_id),
                            str(project_id),
                            str(project_id),
                            str(project_id),
                        ),
                    )
                    count_row = await cursor.fetchone()
                    count = count_row[0] if count_row else 0

                    # Delete entries for specific project (delete child tables first, then parent)
                    await conn.execute(
                        """DELETE FROM errors
                           WHERE job_id IN (SELECT job_id FROM jobs WHERE project_id = ?)""",
                        (str(project_id),),
                    )
                    await conn.execute(
                        """DELETE FROM file_index
                           WHERE job_id IN (SELECT job_id FROM jobs WHERE project_id = ?)""",
                        (str(project_id),),
                    )
                    await conn.execute(
                        """DELETE FROM trace_segments
                           WHERE job_id IN (SELECT job_id FROM jobs WHERE project_id = ?)""",
                        (str(project_id),),
                    )
                    # Delete jobs and pipelines last
                    await conn.execute(
                        "DELETE FROM jobs WHERE project_id = ?", (str(project_id),)
                    )
                    await conn.execute(
                        "DELETE FROM pipelines WHERE project_id = ?",
                        (str(project_id),),
                    )
                else:
                    # Count all entries (including pipelines and trace_segments for full clear)
                    cursor = await conn.execute(
                        """
                        SELECT COUNT(*) FROM (
                            SELECT 1 FROM jobs
                            UNION ALL
                            SELECT 1 FROM errors
                            UNION ALL
                            SELECT 1 FROM file_index
                            UNION ALL
                            SELECT 1 FROM trace_segments
                            UNION ALL
                            SELECT 1 FROM pipelines
                        )
                        """
                    )
                    count_row = await cursor.fetchone()
                    count = count_row[0] if count_row else 0

                    # Delete all cache entries (delete child tables first, then parent tables)
                    await conn.execute("DELETE FROM errors")
                    await conn.execute("DELETE FROM file_index")
                    await conn.execute("DELETE FROM trace_segments")
                    # Delete jobs and pipelines last
                    await conn.execute("DELETE FROM jobs")
                    await conn.execute("DELETE FROM pipelines")

                await conn.commit()
                return count
        except Exception:
            return 0

    async def clear_cache_by_type(
        self, cache_type: str, project_id: str | int | None = None
    ) -> int:
        """Clear cache entries by type"""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                table_map = {
                    "job": "jobs",
                    "error": "errors",
                    "file": "file_index",
                }

                table = table_map.get(cache_type)
                if not table:
                    return 0

                if project_id:
                    cursor = await conn.execute(
                        f"SELECT COUNT(*) FROM {table} WHERE project_id = ?",  # nosec B608
                        (str(project_id),),
                    )
                    count_row = await cursor.fetchone()
                    count = count_row[0] if count_row else 0
                    await conn.execute(
                        f"DELETE FROM {table} WHERE project_id = ?",  # nosec B608
                        (str(project_id),),
                    )
                else:
                    cursor = await conn.execute(f"SELECT COUNT(*) FROM {table}")  # nosec B608
                    count_row = await cursor.fetchone()
                    count = count_row[0] if count_row else 0
                    await conn.execute(f"DELETE FROM {table}")  # nosec B608

                await conn.commit()
                return count
        except Exception:
            return 0

    async def clear_cache_by_pipeline(
        self, project_id: str | int, pipeline_id: str | int
    ) -> dict[str, int | str]:
        """Clear all cache data for a specific pipeline"""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                project_id_str = str(project_id)
                pipeline_id_int = int(pipeline_id)

                counts = {}

                # Get all job IDs for this pipeline first
                cursor = await conn.execute(
                    "SELECT job_id FROM jobs WHERE project_id = ? AND pipeline_id = ?",
                    (project_id_str, pipeline_id_int),
                )
                job_ids = [row[0] for row in await cursor.fetchall()]

                if job_ids:
                    job_ids_placeholders = ",".join("?" * len(job_ids))

                    # Clear trace_segments for these jobs
                    cursor = await conn.execute(
                        f"SELECT COUNT(*) FROM trace_segments WHERE job_id IN ({job_ids_placeholders})",  # nosec B608
                        job_ids,
                    )
                    count_row = await cursor.fetchone()
                    counts["trace_segments"] = count_row[0] if count_row else 0
                    await conn.execute(
                        f"DELETE FROM trace_segments WHERE job_id IN ({job_ids_placeholders})",  # nosec B608
                        job_ids,
                    )

                    # Clear errors for these jobs
                    cursor = await conn.execute(
                        f"SELECT COUNT(*) FROM errors WHERE job_id IN ({job_ids_placeholders})",  # nosec B608
                        job_ids,
                    )
                    count_row = await cursor.fetchone()
                    counts["errors"] = count_row[0] if count_row else 0
                    await conn.execute(
                        f"DELETE FROM errors WHERE job_id IN ({job_ids_placeholders})",  # nosec B608
                        job_ids,
                    )

                    # Clear file_index for these jobs
                    cursor = await conn.execute(
                        f"SELECT COUNT(*) FROM file_index WHERE job_id IN ({job_ids_placeholders})",  # nosec B608
                        job_ids,
                    )
                    count_row = await cursor.fetchone()
                    counts["file_index"] = count_row[0] if count_row else 0
                    await conn.execute(
                        f"DELETE FROM file_index WHERE job_id IN ({job_ids_placeholders})",  # nosec B608
                        job_ids,
                    )
                else:
                    counts["trace_segments"] = 0
                    counts["errors"] = 0
                    counts["file_index"] = 0

                # Clear jobs for this pipeline
                cursor = await conn.execute(
                    "SELECT COUNT(*) FROM jobs WHERE project_id = ? AND pipeline_id = ?",
                    (project_id_str, pipeline_id_int),
                )
                count_row = await cursor.fetchone()
                counts["jobs"] = count_row[0] if count_row else 0
                await conn.execute(
                    "DELETE FROM jobs WHERE project_id = ? AND pipeline_id = ?",
                    (project_id_str, pipeline_id_int),
                )

                # Clear pipeline record
                cursor = await conn.execute(
                    "SELECT COUNT(*) FROM pipelines WHERE project_id = ? AND pipeline_id = ?",
                    (project_id_str, pipeline_id_int),
                )
                count_row = await cursor.fetchone()
                counts["pipelines"] = count_row[0] if count_row else 0
                await conn.execute(
                    "DELETE FROM pipelines WHERE project_id = ? AND pipeline_id = ?",
                    (project_id_str, pipeline_id_int),
                )

                await conn.commit()
                return counts
        except Exception as e:
            return {"error": -1, "message": str(e)}

    async def clear_cache_by_job(
        self, project_id: str | int, job_id: str | int
    ) -> dict[str, int | str]:
        """Clear all cache data for a specific job"""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                job_id_int = int(job_id)
                counts = {}

                # Clear trace_segments for this job
                cursor = await conn.execute(
                    "SELECT COUNT(*) FROM trace_segments WHERE job_id = ?",
                    (job_id_int,),
                )
                count_row = await cursor.fetchone()
                counts["trace_segments"] = count_row[0] if count_row else 0
                await conn.execute(
                    "DELETE FROM trace_segments WHERE job_id = ?", (job_id_int,)
                )

                # Clear errors for this job
                cursor = await conn.execute(
                    "SELECT COUNT(*) FROM errors WHERE job_id = ?", (job_id_int,)
                )
                count_row = await cursor.fetchone()
                counts["errors"] = count_row[0] if count_row else 0
                await conn.execute("DELETE FROM errors WHERE job_id = ?", (job_id_int,))

                # Clear file_index for this job
                cursor = await conn.execute(
                    "SELECT COUNT(*) FROM file_index WHERE job_id = ?", (job_id_int,)
                )
                count_row = await cursor.fetchone()
                counts["file_index"] = count_row[0] if count_row else 0
                await conn.execute(
                    "DELETE FROM file_index WHERE job_id = ?", (job_id_int,)
                )

                # Clear job record
                cursor = await conn.execute(
                    "SELECT COUNT(*) FROM jobs WHERE job_id = ?", (job_id_int,)
                )
                count_row = await cursor.fetchone()
                counts["jobs"] = count_row[0] if count_row else 0
                await conn.execute("DELETE FROM jobs WHERE job_id = ?", (job_id_int,))

                await conn.commit()
                return counts
        except Exception as e:
            return {"error": -1, "message": str(e)}

    async def check_health(self) -> dict[str, Any]:
        """Check cache system health with comprehensive diagnostics"""
        try:
            print("🔍 [HEALTH] Starting cache health check...")

            # Basic file system checks
            db_exists = self.db_path.exists()
            db_size = self.db_path.stat().st_size if db_exists else 0

            # Parent directory checks
            parent_dir = self.db_path.parent
            parent_exists = parent_dir.exists()
            parent_writable = os.access(parent_dir, os.W_OK) if parent_exists else False

            # File permission checks (if database exists)
            file_permissions: dict[str, Any] = {}
            if db_exists:
                file_permissions = {
                    "readable": os.access(self.db_path, os.R_OK),
                    "writable": os.access(self.db_path, os.W_OK),
                    "size_bytes": db_size,
                    "size_mb": round(db_size / 1024 / 1024, 2),
                }

                # Get detailed file permissions
                stat_info = self.db_path.stat()
                import stat as stat_module

                file_permissions["mode"] = stat_module.filemode(stat_info.st_mode)
                file_permissions["owner_uid"] = stat_info.st_uid
                file_permissions["current_uid"] = os.getuid()  # Disk space check
            disk_space: dict[str, Any] = {}
            try:
                import shutil

                usage = shutil.disk_usage(parent_dir if parent_exists else "/")
                disk_space = {
                    "total_mb": round(usage.total / 1024 / 1024, 2),
                    "free_mb": round(usage.free / 1024 / 1024, 2),
                    "used_mb": round(usage.used / 1024 / 1024, 2),
                    "free_percent": round((usage.free / usage.total) * 100, 1),
                }
            except Exception as e:
                disk_space = {"error": str(e)}

            print("🔍 [HEALTH] Checking database connectivity...")

            async with aiosqlite.connect(self.db_path) as conn:
                # Check database connectivity
                await conn.execute("SELECT 1")
                print("✅ [HEALTH] Database connectivity OK")

                # Check table schemas
                tables = [
                    "pipelines",
                    "jobs",
                    "errors",
                    "file_index",
                    "trace_segments",
                ]
                table_status = {}

                for table in tables:
                    try:
                        cursor = await conn.execute(f"SELECT COUNT(*) FROM {table}")  # nosec B608
                        count_row = await cursor.fetchone()
                        count = count_row[0] if count_row else 0

                        # Get table info for schema validation
                        info_cursor = await conn.execute(f"PRAGMA table_info({table})")  # nosec B608
                        columns = await info_cursor.fetchall()

                        table_status[table] = {
                            "status": "ok",
                            "count": count,
                            "columns": len(list(columns)),
                            "column_names": [col[1] for col in columns],
                        }
                        print(
                            f"✅ [HEALTH] Table {table}: {count} records, {len(list(columns))} columns"
                        )
                    except Exception as e:
                        table_status[table] = {"status": "error", "error": str(e)}
                        print(f"❌ [HEALTH] Table {table}: ERROR - {e}")

                # Check for any orphaned records
                orphaned_checks = {}
                try:
                    # Check for errors without corresponding jobs
                    cursor = await conn.execute(
                        """
                        SELECT COUNT(*) FROM errors e
                        LEFT JOIN jobs j ON e.job_id = j.job_id
                        WHERE j.job_id IS NULL
                    """
                    )
                    result = await cursor.fetchone()
                    orphaned_errors = result[0] if result else 0

                    # Check for file_index without corresponding jobs
                    cursor = await conn.execute(
                        """
                        SELECT COUNT(*) FROM file_index fi
                        LEFT JOIN jobs j ON fi.job_id = j.job_id
                        WHERE j.job_id IS NULL
                    """
                    )
                    result = await cursor.fetchone()
                    orphaned_files = result[0] if result else 0

                    # Check for trace_segments without corresponding jobs
                    cursor = await conn.execute(
                        """
                        SELECT COUNT(*) FROM trace_segments ts
                        LEFT JOIN jobs j ON ts.job_id = j.job_id
                        WHERE j.job_id IS NULL
                    """
                    )
                    result = await cursor.fetchone()
                    orphaned_traces = result[0] if result else 0

                    orphaned_checks = {
                        "orphaned_errors": orphaned_errors,
                        "orphaned_files": orphaned_files,
                        "orphaned_traces": orphaned_traces,
                        "total_orphaned": orphaned_errors
                        + orphaned_files
                        + orphaned_traces,
                    }

                    if orphaned_checks["total_orphaned"] > 0:
                        print(
                            f"⚠️ [HEALTH] Found {orphaned_checks['total_orphaned']} orphaned records"
                        )
                    else:
                        print("✅ [HEALTH] No orphaned records found")

                except Exception as e:
                    orphaned_checks = {"error": str(e)}

                print("✅ [HEALTH] Cache health check completed")

                return {
                    "status": "healthy",
                    "database_connectivity": "ok",
                    "database_path": str(self.db_path.resolve()),
                    "database_exists": db_exists,
                    "file_system": {
                        "parent_directory_exists": parent_exists,
                        "parent_directory_writable": parent_writable,
                        "file_permissions": file_permissions,
                        "disk_space": disk_space,
                    },
                    "database_size_bytes": db_size,
                    "database_size_mb": round(db_size / 1024 / 1024, 2),
                    "tables": table_status,
                    "orphaned_records": orphaned_checks,
                    "parser_version": self.parser_version,
                    "environment": {
                        "MCP_DATABASE_PATH": os.environ.get("MCP_DATABASE_PATH"),
                        "current_working_directory": str(Path.cwd()),
                        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                    },
                    "recommendations": self._generate_health_recommendations(
                        table_status, orphaned_checks, disk_space
                    ),
                }

        except Exception as e:
            print(f"❌ [HEALTH] Health check failed: {e}")
            import traceback

            traceback.print_exc()

            return {
                "status": "unhealthy",
                "error": str(e),
                "error_type": type(e).__name__,
                "database_connectivity": "failed",
                "database_path": (
                    str(self.db_path.resolve())
                    if hasattr(self, "db_path")
                    else "unknown"
                ),
            }

    def _generate_health_recommendations(
        self, table_status: dict, orphaned_checks: dict, disk_space: dict
    ) -> list[str]:
        """Generate health recommendations based on check results"""
        recommendations = []

        # Check for table issues
        for table, status in table_status.items():
            if status.get("status") == "error":
                recommendations.append(
                    f"Table {table} has errors - consider rebuilding database"
                )
            elif status.get("count", 0) == 0 and table != "pipelines":
                recommendations.append(
                    f"Table {table} is empty - run pipeline analysis to populate data"
                )

        # Check for orphaned records
        if (
            isinstance(orphaned_checks, dict)
            and orphaned_checks.get("total_orphaned", 0) > 0
        ):
            recommendations.append(
                "Found orphaned records - consider running cache cleanup"
            )

        # Check disk space
        if isinstance(disk_space, dict) and disk_space.get("free_percent", 100) < 10:
            recommendations.append(
                "Low disk space - consider clearing old cache entries"
            )
        elif isinstance(disk_space, dict) and disk_space.get("free_percent", 100) < 5:
            recommendations.append(
                "CRITICAL: Very low disk space - immediate cleanup required"
            )

        # General recommendations
        if not recommendations:
            recommendations.append("Cache system is healthy - no action required")

        return recommendations

    async def get_or_compute(
        self,
        key: str,
        compute_func,
        data_type: str,
        project_id: str,
        pipeline_id: int | None = None,
        job_id: int | None = None,
    ) -> Any:
        """Get cached data or compute and cache it"""
        # For now, just compute (can add caching later)
        return await compute_func()

    async def get(self, key: str) -> Any | None:
        """Get cached data by key (compatibility method for resources)"""
        # For now, return None (no cache hit) - can be enhanced later
        return None

    async def set(
        self,
        key: str,
        value: Any,
        data_type: str = "generic",
        project_id: str | int | None = None,
        pipeline_id: int | None = None,
        job_id: int | None = None,
    ) -> None:
        """Set a value in the cache (compatibility method for resources)"""
        # For now, just log that we're setting a value
        # The actual storage is handled by store_pipeline_info_async method
        # No implementation needed for compatibility method


# Global cache instance for compatibility with old CacheManager
_global_cache: McpCache | None = None


def get_cache_manager(db_path: str | None = None) -> McpCache:
    """
    Compatibility function for old CacheManager usage.
    Returns the global McpCache instance.

    Args:
        db_path: Optional database path. If None, uses MCP_DATABASE_PATH environment
                variable or defaults to "analysis_cache.db"
    """
    global _global_cache
    if _global_cache is None:
        try:
            print("🔧 [DEBUG] Creating new global McpCache instance...")
            _global_cache = McpCache(db_path)
            print("✅ [DEBUG] Global McpCache instance created successfully")
        except Exception as e:
            print(f"❌ [ERROR] Failed to create global McpCache instance: {e}")
            print(f"❌ [ERROR] Exception type: {type(e).__name__}")
            import traceback

            print("❌ [ERROR] Traceback:")
            traceback.print_exc()
            raise
    else:
        print("🔧 [DEBUG] Using existing global McpCache instance")
    return _global_cache


async def cleanup_cache_manager() -> None:
    """Cleanup global cache instance"""
    global _global_cache
    if _global_cache is not None:
        # Optionally run cleanup
        _global_cache.cleanup_old_versions()
        _global_cache = None
