from datetime import UTC, datetime, timedelta

from tads.constants import WINDOW_SIZE_SECONDS


def get_window_boundaries(timestamp: datetime) -> tuple[datetime, datetime]:
    """
    Computes the 5-second semantic window boundaries for a given timestamp.

    The window start is computed by flooring the timestamp to the nearest 5-second boundary.
    The window end is exactly window_start + 5 seconds.

    This is a pure, deterministic function. The resulting timestamps are always returned in UTC.

    Args:
        timestamp: The datetime to calculate the window for. If naive, it is assumed to be UTC.

    Returns:
        (window_start, window_end): A tuple of UTC datetimes representing the inclusive start
                                    and exclusive end of the 5-second window.
    """
    timestamp = timestamp.replace(tzinfo=UTC) if timestamp.tzinfo is None else timestamp.astimezone(UTC)

    # Calculate total seconds since epoch to floor correctly
    epoch = datetime(1970, 1, 1, tzinfo=UTC)
    delta = timestamp - epoch
    total_seconds = delta.total_seconds()

    # Floor to nearest WINDOW_SIZE_SECONDS (default 5)
    floored_seconds = (total_seconds // WINDOW_SIZE_SECONDS) * WINDOW_SIZE_SECONDS

    window_start = epoch + timedelta(seconds=floored_seconds)
    window_end = window_start + timedelta(seconds=WINDOW_SIZE_SECONDS)

    return window_start, window_end
