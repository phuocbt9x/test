"""
Timezone Utilities

Provides timezone-aware datetime utilities to replace deprecated datetime.utcnow().
All datetime objects returned are timezone-aware and properly handle the application timezone.

Why this module:
- datetime.utcnow() is deprecated in Python 3.12+
- Using datetime.now(timezone.utc) is the recommended approach
- Centralizes timezone handling for consistency

Usage:
    from src.core.utils import utcnow, now, to_timezone

    # Get current time in UTC (timezone-aware)
    current_utc = utcnow()

    # Get current time in app timezone
    current_local = now()

    # Convert datetime to specific timezone
    tokyo_time = to_timezone(current_utc, "Asia/Tokyo")
"""
from datetime import datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from src.core.configs import settings


def utcnow() -> datetime:
    """
    Get current datetime in UTC timezone.

    This replaces the deprecated datetime.utcnow() with a timezone-aware version.

    Returns:
        datetime: Current UTC time with timezone information.

    Example:
        >>> current = utcnow()
        >>> print(current)
        2024-12-14 10:30:45.123456+00:00
        >>> print(current.tzinfo)
        UTC
    """
    return datetime.now(timezone.utc)


def now(tz: Optional[str] = None) -> datetime:
    """
    Get current datetime in the specified timezone.

    If no timezone is provided, uses the application's configured timezone
    from settings.APP_TIMEZONE.

    Args:
        tz: Timezone name (e.g., 'Asia/Tokyo', 'America/New_York').
            If None, uses settings.APP_TIMEZONE.

    Returns:
        datetime: Current time in the specified timezone.

    Example:
        >>> # Get current time in app timezone (Asia/Tokyo)
        >>> tokyo_time = now()
        >>> print(tokyo_time)
        2024-12-14 19:30:45.123456+09:00

        >>> # Get current time in specific timezone
        >>> ny_time = now("America/New_York")
        >>> print(ny_time)
        2024-12-14 05:30:45.123456-05:00

    Raises:
        ZoneInfoNotFoundError: If the timezone name is invalid.
    """
    tz_name = tz or settings.APP_TIMEZONE
    tz_info = ZoneInfo(tz_name)
    return datetime.now(tz_info)


def to_timezone(dt: datetime, tz: str) -> datetime:
    """
    Convert a datetime object to a specific timezone.

    If the input datetime is naive (no timezone info), it will be treated
    as UTC before conversion.

    Args:
        dt: The datetime object to convert.
        tz: Target timezone name (e.g., 'Asia/Tokyo', 'UTC').

    Returns:
        datetime: The datetime converted to the target timezone.

    Example:
        >>> utc_time = utcnow()
        >>> print(utc_time)
        2024-12-14 10:30:45.123456+00:00

        >>> tokyo_time = to_timezone(utc_time, "Asia/Tokyo")
        >>> print(tokyo_time)
        2024-12-14 19:30:45.123456+09:00

        >>> # If datetime is naive, assumes UTC
        >>> naive_dt = datetime(2024, 12, 14, 10, 30, 45)
        >>> tokyo_time = to_timezone(naive_dt, "Asia/Tokyo")
        >>> print(tokyo_time)
        2024-12-14 19:30:45+09:00

    Raises:
        ZoneInfoNotFoundError: If the timezone name is invalid.
    """
    tz_info = ZoneInfo(tz)

    # If datetime is naive, assume it's UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(tz_info)


def to_utc(dt: datetime) -> datetime:
    """
    Convert a datetime object to UTC timezone.

    If the input datetime is naive (no timezone info), it will be treated
    as being in the application's configured timezone before conversion.

    Args:
        dt: The datetime object to convert.

    Returns:
        datetime: The datetime converted to UTC.

    Example:
        >>> # Convert timezone-aware datetime to UTC
        >>> tokyo_time = now("Asia/Tokyo")  # 2024-12-14 19:30:45+09:00
        >>> utc_time = to_utc(tokyo_time)
        >>> print(utc_time)
        2024-12-14 10:30:45+00:00

        >>> # Convert naive datetime (assumes app timezone)
        >>> naive_dt = datetime(2024, 12, 14, 19, 30, 45)
        >>> utc_time = to_utc(naive_dt)  # Treats as Asia/Tokyo
        >>> print(utc_time)
        2024-12-14 10:30:45+00:00
    """
    # If datetime is naive, assume it's in app timezone
    if dt.tzinfo is None:
        app_tz = ZoneInfo(settings.APP_TIMEZONE)
        dt = dt.replace(tzinfo=app_tz)

    return dt.astimezone(timezone.utc)


def get_timezone(tz_name: Optional[str] = None) -> ZoneInfo:
    """
    Get a ZoneInfo object for the specified timezone.

    Args:
        tz_name: Timezone name. If None, returns app timezone.

    Returns:
        ZoneInfo: The timezone object.

    Example:
        >>> tokyo_tz = get_timezone("Asia/Tokyo")
        >>> print(tokyo_tz)
        zoneinfo.ZoneInfo(key='Asia/Tokyo')

        >>> app_tz = get_timezone()  # Uses settings.APP_TIMEZONE

    Raises:
        ZoneInfoNotFoundError: If the timezone name is invalid.
    """
    tz = tz_name or settings.APP_TIMEZONE
    return ZoneInfo(tz)


def format_datetime(
    dt: datetime,
    fmt: str = "%Y-%m-%d %H:%M:%S",
    tz: Optional[str] = None,
) -> str:
    """
    Format a datetime object as a string, optionally converting timezone first.

    Args:
        dt: The datetime object to format.
        fmt: The strftime format string. Default: "%Y-%m-%d %H:%M:%S"
        tz: Optional timezone to convert to before formatting.
            If None, uses the datetime's current timezone.

    Returns:
        str: The formatted datetime string.

    Example:
        >>> dt = utcnow()
        >>>
        >>> # Format in UTC
        >>> print(format_datetime(dt))
        2024-12-14 10:30:45
        >>>
        >>> # Format in Tokyo timezone
        >>> print(format_datetime(dt, tz="Asia/Tokyo"))
        2024-12-14 19:30:45
        >>>
        >>> # Custom format
        >>> print(format_datetime(dt, fmt="%Y/%m/%d %H:%M", tz="Asia/Tokyo"))
        2024/12/14 19:30
        >>>
        >>> # ISO 8601 format
        >>> print(format_datetime(dt, fmt="%Y-%m-%dT%H:%M:%S%z"))
        2024-12-14T10:30:45+0000
    """
    if tz:
        dt = to_timezone(dt, tz)

    return dt.strftime(fmt)
