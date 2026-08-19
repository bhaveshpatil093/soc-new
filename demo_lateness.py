from datetime import UTC, datetime, timedelta

from tads.windowing.lateness import LateEventRouter

def main() -> None:
    print("=== Demo: Late-Arriving Event Finalization Semantics ===")
    
    router = LateEventRouter()
    
    # Simulate an ordered chronological stream of events arriving at the pipeline.
    # Note: For this demo, chronological arrival order is simulated by the order 
    # the events are passed to process_event.
    
    events_stream = [
        # Window: 12:00:00 -> 12:00:05. Finalizes when watermark > 12:01:05
        {"_id": "ev1", "@timestamp": datetime(2026, 8, 1, 12, 0, 1, tzinfo=UTC), "desc": "Arrives on time"},
        {"_id": "ev2", "@timestamp": datetime(2026, 8, 1, 12, 0, 4, tzinfo=UTC), "desc": "Arrives on time"},
        
        # Advance the watermark heavily. 
        # Stream jumps forward. High watermark hits 12:02:00
        {"_id": "ev3", "@timestamp": datetime(2026, 8, 1, 12, 2, 0, tzinfo=UTC), "desc": "Advances Watermark to 12:02:00"},
        
        # INJECT LATE EVENT
        # This event physically occurred at 12:00:02, but arrived *chronologically* 
        # after the stream had already progressed to 12:02:00.
        # It belongs to the 12:00:00 window, which was finalized at 12:01:05.
        {"_id": "ev4_late", "@timestamp": datetime(2026, 8, 1, 12, 0, 2, tzinfo=UTC), "desc": "DELIBERATELY LATE. Should be rejected."},
        
        # Another on-time event for the current window
        {"_id": "ev5", "@timestamp": datetime(2026, 8, 1, 12, 2, 1, tzinfo=UTC), "desc": "Arrives on time"},
    ]
    
    print("\n--- Processing Stream ---")
    print(f"{'ID':<10} | {'@Timestamp':<25} | {'Watermark':<25} | {'Status':<10} | {'Finalized?'}")
    print("-" * 90)
    
    for ev in events_stream:
        res = router.process_event(ev)
        wm = router.tracker.high_water_mark.isoformat() if router.tracker.high_water_mark else "None"
        print(f"{res.event_id:<10} | {ev['@timestamp'].isoformat():<25} | {wm:<25} | {res.status:<10} | {res.is_finalized}")
        
    print("\n--- Routing Summary ---")
    print(f"Total Processed: {router.tracker.total_processed}")
    print(f"ON_TIME Events Routed to ML Feature Engine: {len(router.on_time_events)}")
    print(f"LATE Events Quarantined to late_events.parquet: {len(router.late_events)}")
    
    assert len(router.late_events) == 1
    assert router.late_events[0]["_id"] == "ev4_late"
    
    print("\nSUCCESS: Pipeline correctly classified the deliberately late event, quarantined it, and protected the finalized window.")

if __name__ == "__main__":
    main()
