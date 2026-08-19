import logging
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from pydantic import BaseModel

from tads.constants import ALLOWED_LATENESS_SECONDS
from tads.windowing.assign import get_window_boundaries

logger = logging.getLogger(__name__)

EventStatus = Literal["ON_TIME", "LATE"]

class EventEvaluation(BaseModel):
    event_id: str
    status: EventStatus
    window_start: datetime
    window_end: datetime
    is_finalized: bool

class WatermarkTracker:
    """
    Tracks the stream's high-water mark and evaluates events for lateness.

    A 5-second window is considered 'finalized' when the high-water mark
    (the maximum chronological @timestamp seen across the ingested stream so far)
    crosses (window_end + ALLOWED_LATENESS_SECONDS).

    Once finalized, any subsequent event mapped to that window is flagged as LATE
    and routed away from feature processing.
    """

    def __init__(self, allowed_lateness: int = ALLOWED_LATENESS_SECONDS) -> None:
        self.allowed_lateness = timedelta(seconds=allowed_lateness)
        # The highest semantic timestamp (@timestamp) observed across all processed events.
        self.high_water_mark: datetime | None = None

        self.total_processed = 0
        self.total_late = 0

    def evaluate_event(self, event_id: str, event_timestamp: datetime) -> EventEvaluation:
        """
        Evaluates an incoming event against the current high-water mark.
        Updates the high-water mark if this event advances it.
        """
        event_timestamp = event_timestamp.replace(tzinfo=UTC) if event_timestamp.tzinfo is None else event_timestamp.astimezone(UTC)

        window_start, window_end = get_window_boundaries(event_timestamp)

        # Advance the watermark if necessary
        if self.high_water_mark is None or event_timestamp > self.high_water_mark:
            self.high_water_mark = event_timestamp

        # Determine if the window is already finalized
        # A window is finalized if high_water_mark > window_end + allowed_lateness
        finalization_threshold = window_end + self.allowed_lateness
        is_finalized = self.high_water_mark > finalization_threshold

        # If the window is already finalized, this event is LATE.
        # Otherwise, even if it's slightly out-of-order but the window isn't finalized, it's ON_TIME.
        status: EventStatus = "LATE" if is_finalized else "ON_TIME"

        self.total_processed += 1
        if status == "LATE":
            self.total_late += 1

        return EventEvaluation(
            event_id=event_id,
            status=status,
            window_start=window_start,
            window_end=window_end,
            is_finalized=is_finalized
        )

class LateEventRouter:
    """
    A conceptual router that separates ON_TIME events from LATE events.
    In a real streaming engine, this would yield streams or write to segregated Parquet partitions.
    """
    def __init__(self) -> None:
        self.tracker = WatermarkTracker()
        self.on_time_events: list[dict[str, Any]] = []
        self.late_events: list[dict[str, Any]] = []

    def process_event(self, event: dict[str, Any]) -> EventEvaluation:
        event_id = event["_id"]
        ts = event["@timestamp"]

        evaluation = self.tracker.evaluate_event(event_id, ts)

        if evaluation.status == "LATE":
            self.late_events.append(event)
        else:
            self.on_time_events.append(event)

        return evaluation
