"""Download tracking utilities for session deduplication and statistics."""

import asyncio
import time
import uuid
from datetime import date, datetime, timedelta, timezone

from kohakuhub.config import cfg
from kohakuhub.db import DailyRepoStats, DownloadSession, Repository, User, db
from kohakuhub.db_operations import (
    count_repository_sessions,
    create_download_session,
    get_download_session,
    increment_download_session_files,
    update_repository,
)
from kohakuhub.logger import get_logger

logger = get_logger("DOWNLOADS")


def get_or_create_tracking_cookie(cookies: dict, response_cookies: dict) -> str:
    """Get or create anonymous tracking cookie.

    Args:
        cookies: Request cookies dict
        response_cookies: Dict to store new cookies (modified in place)

    Returns:
        Session ID string
    """
    session_id = cookies.get("hf_download_session")

    if not session_id:
        # Create new tracking cookie
        session_id = uuid.uuid4().hex
        response_cookies["hf_download_session"] = {
            "value": session_id,
            "max_age": 86400,  # 24 hours
            "httponly": True,
            "samesite": "lax",
        }
        logger.debug(f"Created new tracking cookie: {session_id[:8]}...")

    return session_id


async def track_download_async(
    repo: Repository, file_path: str, session_id: str, user: User | None
):
    """Track download in background (async, non-blocking).

    Updates TODAY's DailyRepoStats in real-time.
    Triggers cleanup if session count exceeds threshold.

    Args:
        repo: Repository being downloaded
        file_path: File path being downloaded
        session_id: Session cookie ID
        user: User (NULL if anonymous)
    """
    try:
        # Calculate time bucket using configured window
        time_bucket = int(time.time() / cfg.app.download_time_bucket_seconds)

        # Check for existing session
        existing = get_download_session(repo, session_id, time_bucket)

        if existing:
            # Existing session - just increment file count
            increment_download_session_files(existing.id)

            # Update TODAY's total_files count (real-time)
            today = datetime.now(timezone.utc).date()
            DailyRepoStats.update(total_files=DailyRepoStats.total_files + 1).where(
                (DailyRepoStats.repository == repo) & (DailyRepoStats.date == today)
            ).execute()

            logger.debug(
                f"Download session updated: {repo.full_id} (file #{existing.file_count + 1})"
            )
        else:
            # NEW session - create and update all counters
            with db.atomic():
                # Create session
                create_download_session(
                    repository=repo,
                    session_id=session_id,
                    time_bucket=time_bucket,
                    first_file=file_path,
                    user=user,
                )

                # Increment repo total downloads
                update_repository(repo, downloads=repo.downloads + 1)

                # Update TODAY's DailyRepoStats (REAL-TIME)
                today = datetime.now(timezone.utc).date()

                DailyRepoStats.insert(
                    repository=repo,
                    date=today,
                    download_sessions=1,
                    authenticated_downloads=1 if user else 0,
                    anonymous_downloads=0 if user else 1,
                    total_files=1,
                ).on_conflict(
                    conflict_target=(DailyRepoStats.repository, DailyRepoStats.date),
                    update={
                        DailyRepoStats.download_sessions: DailyRepoStats.download_sessions
                        + 1,
                        DailyRepoStats.authenticated_downloads: DailyRepoStats.authenticated_downloads
                        + (1 if user else 0),
                        DailyRepoStats.anonymous_downloads: DailyRepoStats.anonymous_downloads
                        + (0 if user else 1),
                        DailyRepoStats.total_files: DailyRepoStats.total_files + 1,
                    },
                ).execute()

            logger.info(
                f"New download session: {repo.full_id} by {user.username if user else 'anonymous'}"
            )

            # Trigger cleanup if threshold exceeded (async, non-blocking)
            session_count = count_repository_sessions(repo)

            if session_count > cfg.app.download_session_cleanup_threshold:
                asyncio.create_task(aggregate_old_sessions(repo))

    except Exception as e:
        # Don't fail the download if tracking fails
        logger.exception(f"Failed to track download for {repo.full_id}", e)


async def ensure_stats_up_to_date(repo: Repository):
    """Ensure DailyRepoStats is up-to-date (lazy aggregation for historical dates).

    TODAY is already real-time updated, this aggregates YESTERDAY and older.

    Args:
        repo: Repository to check
    """
    # Get latest DailyRepoStats entry
    latest_stat = (
        DailyRepoStats.select()
        .where(DailyRepoStats.repository == repo)
        .order_by(DailyRepoStats.date.desc())
        .first()
    )

    today = datetime.now(timezone.utc).date()
    yesterday = today - timedelta(days=1)

    if not latest_stat:
        # No stats yet - aggregate ALL historical sessions (not today)
        await aggregate_sessions_to_daily(repo, start_date=None, end_date=yesterday)
    elif latest_stat.date < yesterday:
        # Stale! Aggregate from (latest_date + 1) to yesterday
        await aggregate_sessions_to_daily(
            repo,
            start_date=latest_stat.date + timedelta(days=1),
            end_date=yesterday,
        )
    # else: Up-to-date (latest_stat.date >= yesterday)


async def aggregate_sessions_to_daily(
    repo: Repository, start_date: date | None, end_date: date
):
    """Aggregate DownloadSessions into DailyRepoStats for date range.

    Does NOT aggregate TODAY (it's real-time updated).

    Args:
        repo: Repository to aggregate
        start_date: Start date (inclusive, None = all historical)
        end_date: End date (inclusive, typically yesterday)
    """
    # Query sessions in date range (EXCLUDE TODAY)
    query = DownloadSession.select().where(DownloadSession.repository == repo)

    if start_date:
        start_datetime = datetime.combine(
            start_date, datetime.min.time(), tzinfo=timezone.utc
        )
        query = query.where(DownloadSession.first_download_at >= start_datetime)

    end_datetime = datetime.combine(end_date, datetime.max.time(), tzinfo=timezone.utc)
    query = query.where(DownloadSession.first_download_at <= end_datetime)

    sessions = list(query.order_by(DownloadSession.first_download_at))

    if not sessions:
        logger.debug(f"No sessions to aggregate for {repo.full_id}")
        return

    # Group by date
    daily_data = {}
    for session in sessions:
        day = session.first_download_at.date()

        if day not in daily_data:
            daily_data[day] = {"sessions": 0, "auth": 0, "anon": 0, "files": 0}

        daily_data[day]["sessions"] += 1
        daily_data[day]["files"] += session.file_count
        daily_data[day]["auth" if session.user else "anon"] += 1

    # Upsert DailyRepoStats
    with db.atomic():
        for day, stats in daily_data.items():
            DailyRepoStats.insert(
                repository=repo,
                date=day,
                download_sessions=stats["sessions"],
                authenticated_downloads=stats["auth"],
                anonymous_downloads=stats["anon"],
                total_files=stats["files"],
            ).on_conflict(
                conflict_target=(DailyRepoStats.repository, DailyRepoStats.date),
                update={
                    DailyRepoStats.download_sessions: stats["sessions"],
                    DailyRepoStats.authenticated_downloads: stats["auth"],
                    DailyRepoStats.anonymous_downloads: stats["anon"],
                    DailyRepoStats.total_files: stats["files"],
                },
            ).execute()

    logger.info(
        f"Aggregated {len(sessions)} sessions into {len(daily_data)} daily stats for {repo.full_id}"
    )


async def aggregate_old_sessions(repo: Repository):
    """Aggregate old sessions and clean up (triggered when session_count > threshold).

    Args:
        repo: Repository to clean up
    """
    try:
        # Step 1: Ensure all historical dates are aggregated
        await ensure_stats_up_to_date(repo)

        # Step 2: Delete sessions older than KEEP_SESSIONS_DAYS (now safe - already aggregated)
        cutoff = datetime.now(timezone.utc) - timedelta(
            days=cfg.app.download_keep_sessions_days
        )

        deleted = (
            DownloadSession.delete()
            .where(
                (DownloadSession.repository == repo)
                & (DownloadSession.first_download_at < cutoff)
            )
            .execute()
        )

        if deleted > 0:
            logger.info(
                f"Cleaned up {deleted} old download sessions for {repo.full_id} (older than {cfg.app.download_keep_sessions_days} days)"
            )

    except Exception as e:
        logger.exception(f"Failed to aggregate old sessions for {repo.full_id}", e)
