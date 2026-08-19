import json
from tads.schema.raw import coerce_hit_to_canonical

def main():
    print("=== Demo: Deterministic Event Identity ===")
    
    # Simulate a hit missing its ES `_id` (e.g. from unstable index or raw file)
    hit_1 = {
        "_source": {
            "@timestamp": "2026-08-19T10:00:00Z",
            "host": {"name": "app-server-01"},
            "event": {"category": "authentication", "action": "login_failed"},
            "message": "  Failed password for user admin from 192.168.1.5 port 22 ssh2  ",
            "random_field": "12345"
        }
    }
    
    # Exact same hit, extracted again later
    hit_2 = {
        "_source": {
            "@timestamp": "2026-08-19T10:00:00Z",
            "host": {"name": "app-server-01"},
            "event": {"category": "authentication", "action": "login_failed"},
            "message": "Failed password for user admin from 192.168.1.5 port 22 ssh2", # Whitespace stripped
            "random_field": "67890" # Different random field
        }
    }
    
    # Hit 3 has a different core field (different host)
    hit_3 = {
        "_source": {
            "@timestamp": "2026-08-19T10:00:00Z",
            "host": {"name": "app-server-02"},
            "event": {"category": "authentication", "action": "login_failed"},
            "message": "Failed password for user admin from 192.168.1.5 port 22 ssh2",
            "random_field": "12345"
        }
    }
    
    print("\n[TEST 1] First Extraction")
    canonical_1 = coerce_hit_to_canonical(hit_1)
    id_1 = canonical_1["_id"]
    print(f"Generated ID: {id_1}")
    
    print("\n[TEST 2] Second Extraction (identical core semantics, different random field/whitespace)")
    canonical_2 = coerce_hit_to_canonical(hit_2)
    id_2 = canonical_2["_id"]
    print(f"Generated ID: {id_2}")
    
    print("\n[TEST 3] Different Core Field")
    canonical_3 = coerce_hit_to_canonical(hit_3)
    id_3 = canonical_3["_id"]
    print(f"Generated ID: {id_3}")
    
    assert id_1 == id_2, "IDs must match for identical core events!"
    assert id_1 != id_3, "IDs must NOT match if core fields differ!"
    
    print("\nSUCCESS: Event Identity is deterministic and stable!")

if __name__ == "__main__":
    main()
