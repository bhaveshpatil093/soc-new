from datetime import UTC, datetime, timedelta, timezone

from tads.windowing.assign import get_window_boundaries


class TestWindowBoundaries:

    def test_exact_boundary(self) -> None:
        # 12:00:00.000 is divisible by 5
        t = datetime(2026, 8, 1, 12, 0, 0, tzinfo=UTC)
        start, end = get_window_boundaries(t)
        assert start == datetime(2026, 8, 1, 12, 0, 0, tzinfo=UTC)
        assert end == datetime(2026, 8, 1, 12, 0, 5, tzinfo=UTC)

    def test_mid_window_subsecond(self) -> None:
        # 12:00:02.123456
        t = datetime(2026, 8, 1, 12, 0, 2, 123456, tzinfo=UTC)
        start, end = get_window_boundaries(t)
        assert start == datetime(2026, 8, 1, 12, 0, 0, tzinfo=UTC)
        assert end == datetime(2026, 8, 1, 12, 0, 5, tzinfo=UTC)

    def test_end_boundary_inclusive_check(self) -> None:
        # 12:00:04.999999
        t = datetime(2026, 8, 1, 12, 0, 4, 999999, tzinfo=UTC)
        start, end = get_window_boundaries(t)
        assert start == datetime(2026, 8, 1, 12, 0, 0, tzinfo=UTC)
        assert end == datetime(2026, 8, 1, 12, 0, 5, tzinfo=UTC)

    def test_next_boundary_exact(self) -> None:
        # 12:00:05.000000 -> Should jump to next window
        t = datetime(2026, 8, 1, 12, 0, 5, 0, tzinfo=UTC)
        start, end = get_window_boundaries(t)
        assert start == datetime(2026, 8, 1, 12, 0, 5, tzinfo=UTC)
        assert end == datetime(2026, 8, 1, 12, 0, 10, tzinfo=UTC)

    def test_hour_boundary(self) -> None:
        # 12:59:59 -> 12:59:55 to 13:00:00
        t = datetime(2026, 8, 1, 12, 59, 59, tzinfo=UTC)
        start, end = get_window_boundaries(t)
        assert start == datetime(2026, 8, 1, 12, 59, 55, tzinfo=UTC)
        assert end == datetime(2026, 8, 1, 13, 0, 0, tzinfo=UTC)

    def test_day_boundary(self) -> None:
        # 23:59:59.999999 -> 23:59:55 to 00:00:00 (next day)
        t = datetime(2026, 8, 1, 23, 59, 59, 999999, tzinfo=UTC)
        start, end = get_window_boundaries(t)
        assert start == datetime(2026, 8, 1, 23, 59, 55, tzinfo=UTC)
        assert end == datetime(2026, 8, 2, 0, 0, 0, tzinfo=UTC)

    def test_naive_timestamp_forces_utc(self) -> None:
        # 12:00:02 without tzinfo
        t = datetime(2026, 8, 1, 12, 0, 2)
        start, end = get_window_boundaries(t)
        assert start.tzinfo == UTC
        assert end.tzinfo == UTC
        assert start == datetime(2026, 8, 1, 12, 0, 0, tzinfo=UTC)

    def test_different_timezone_converts_to_utc(self) -> None:
        # Timezone +05:00
        tz = timezone(timedelta(hours=5))
        # 17:00:02 +05:00 is exactly 12:00:02 UTC
        t = datetime(2026, 8, 1, 17, 0, 2, tzinfo=tz)
        start, _ = get_window_boundaries(t)
        assert start.tzinfo == UTC
        assert start == datetime(2026, 8, 1, 12, 0, 0, tzinfo=UTC)
