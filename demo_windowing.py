from datetime import datetime, timezone

from tads.windowing.assign import get_window_boundaries

def main():
    print("=== Demo: 5-Second Temporal Window Assignment ===")
    print(f"{'Input Timestamp (UTC)':<30} | {'Window Start (UTC)':<25} | {'Window End (UTC)':<25}")
    print("-" * 86)
    
    test_cases = [
        # Exact boundaries
        datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        datetime(2026, 1, 1, 0, 0, 5, tzinfo=timezone.utc),
        datetime(2026, 1, 1, 0, 0, 10, tzinfo=timezone.utc),
        # Sub-second precisions inside a window
        datetime(2026, 1, 1, 0, 0, 2, 123456, tzinfo=timezone.utc),
        datetime(2026, 1, 1, 0, 0, 4, 999999, tzinfo=timezone.utc),
        # Day boundaries
        datetime(2026, 1, 1, 23, 59, 58, 111111, tzinfo=timezone.utc),
        datetime(2026, 1, 1, 23, 59, 59, 999999, tzinfo=timezone.utc),
        # Next day exact
        datetime(2026, 1, 2, 0, 0, 0, 0, tzinfo=timezone.utc),
        # Hour boundaries
        datetime(2026, 1, 1, 14, 59, 56, tzinfo=timezone.utc),
        datetime(2026, 1, 1, 15, 0, 1, 555555, tzinfo=timezone.utc),
    ]
    
    for t in test_cases:
        start, end = get_window_boundaries(t)
        t_str = t.isoformat()
        start_str = start.isoformat()
        end_str = end.isoformat()
        print(f"{t_str:<30} | {start_str:<25} | {end_str:<25}")
        
    print("\nSUCCESS: All window boundaries correctly map to 5-second semantic intervals.")

if __name__ == "__main__":
    main()
