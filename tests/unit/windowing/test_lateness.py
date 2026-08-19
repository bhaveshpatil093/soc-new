from datetime import UTC, datetime, timedelta

from tads.windowing.lateness import WatermarkTracker


class TestWatermarkTracker:
    def test_in_order_events(self) -> None:
        tracker = WatermarkTracker(allowed_lateness=60)

        # Stream starts
        t1 = datetime(2026, 8, 1, 12, 0, 1, tzinfo=UTC)
        ev1 = tracker.evaluate_event("e1", t1)
        assert ev1.status == "ON_TIME"
        assert not ev1.is_finalized
        assert tracker.high_water_mark == t1

        # Stream moves forward 10 seconds
        t2 = t1 + timedelta(seconds=10)
        ev2 = tracker.evaluate_event("e2", t2)
        assert ev2.status == "ON_TIME"
        assert not ev2.is_finalized
        assert tracker.high_water_mark == t2

    def test_out_of_order_but_on_time(self) -> None:
        tracker = WatermarkTracker(allowed_lateness=60)

        # High watermark advances to 12:00:30
        t_high = datetime(2026, 8, 1, 12, 0, 30, tzinfo=UTC)
        tracker.evaluate_event("e_high", t_high)

        # Event arrives out of order at 12:00:10
        # Its window is 12:00:10 -> 12:00:15
        # Finalization threshold is 12:00:15 + 60 = 12:01:15
        # High watermark is 12:00:30, which is < 12:01:15, so it's ON_TIME
        t_late_but_fine = datetime(2026, 8, 1, 12, 0, 10, tzinfo=UTC)
        ev = tracker.evaluate_event("e_late_ok", t_late_but_fine)

        assert ev.status == "ON_TIME"
        assert not ev.is_finalized
        assert tracker.high_water_mark == t_high  # Watermark didn't recede

    def test_late_event_dropped(self) -> None:
        tracker = WatermarkTracker(allowed_lateness=60)

        # High watermark advances massively to 12:05:00
        t_high = datetime(2026, 8, 1, 12, 5, 0, tzinfo=UTC)
        tracker.evaluate_event("e_high", t_high)

        # Event arrives at 12:00:10
        # Window end: 12:00:15
        # Threshold: 12:01:15
        # High watermark (12:05:00) > 12:01:15 -> Window is finalized!
        t_dropped = datetime(2026, 8, 1, 12, 0, 10, tzinfo=UTC)
        ev = tracker.evaluate_event("e_dropped", t_dropped)

        assert ev.status == "LATE"
        assert ev.is_finalized

    def test_exact_finalization_boundary(self) -> None:
        tracker = WatermarkTracker(allowed_lateness=60)

        # Window: 12:00:00 -> 12:00:05
        # Threshold: 12:01:05

        # Watermark is exactly at threshold
        tracker.evaluate_event("e1", datetime(2026, 8, 1, 12, 1, 5, tzinfo=UTC))
        ev1 = tracker.evaluate_event("e_test1", datetime(2026, 8, 1, 12, 0, 1, tzinfo=UTC))
        # high_water_mark > threshold -> False (they are equal)
        assert ev1.status == "ON_TIME"

        # Watermark moves 1 microsecond past threshold
        tracker.evaluate_event("e2", datetime(2026, 8, 1, 12, 1, 5, 1, tzinfo=UTC))
        ev2 = tracker.evaluate_event("e_test2", datetime(2026, 8, 1, 12, 0, 1, tzinfo=UTC))
        # high_water_mark > threshold -> True
        assert ev2.status == "LATE"
