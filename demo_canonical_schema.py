import json
from tads.schema.raw import coerce_hit_to_canonical

def main():
    print("=== Demo: Versioned Canonical Event Schema ===")
    
    # 1. Valid hit with nested and flat fields
    valid_hit = {
        "_id": "valid_123",
        "_source": {
            "@timestamp": "2026-08-19T10:00:00Z",
            "event": {
                "action": "login",
                "category": ["authentication"],
                "outcome": "SUCCESS"
            },
            "source": {
                "ip": "192.168.1.5",
                "port": 50000
            },
            "user": {
                "name": "admin"
            },
            # Extra fields
            "unknown_field_1": "test_value"
        }
    }
    
    print("\n[TEST 1] Valid complex hit coercion")
    try:
        canonical = coerce_hit_to_canonical(valid_hit)
        print("Success! Coerced canonical record:")
        print(json.dumps(canonical, indent=2, default=str))
        assert canonical["source_ip"] == "192.168.1.5"
        assert canonical["event_outcome"] == "success" # Normalized to lowercase
        assert json.loads(canonical["raw_extra"])["unknown_field_1"] == "test_value"
    except Exception as e:
        print(f"FAILED: {e}")
        
    # 2. Missing optional fields (nullability test)
    sparse_hit = {
        "_id": "sparse_123",
        "_source": {
            "@timestamp": "2026-08-19T10:05:00Z"
            # Missing everything else
        }
    }
    print("\n[TEST 2] Nullability test (missing optional fields)")
    try:
        canonical = coerce_hit_to_canonical(sparse_hit)
        print("Success! Successfully coerced with nulls:")
        print(json.dumps(canonical, indent=2, default=str))
        assert canonical["source_ip"] is None
        assert canonical["event_action"] is None
    except Exception as e:
        print(f"FAILED: {e}")
        
    # 3. Malformed validation failure (bad IP)
    invalid_hit = {
        "_id": "invalid_123",
        "_source": {
            "@timestamp": "2026-08-19T10:10:00Z",
            "source": {
                "ip": "999.999.999.999" # Invalid IPv4
            }
        }
    }
    print("\n[TEST 3] Validation Rule failure (Invalid IP address)")
    try:
        canonical = coerce_hit_to_canonical(invalid_hit)
        print(f"FAILED! Should have been rejected but got: {canonical}")
    except ValueError as e:
        print(f"Success! Correctly rejected: {e}")

if __name__ == "__main__":
    main()
