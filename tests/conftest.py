"""
TADS Test Configuration

Shared fixtures, synthetic data generators, and test utilities.
"""

from __future__ import annotations

import datetime
import random
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from tads.constants import WINDOW_SIZE_MS, WINDOW_SIZE_SECONDS

# ============================================================
# Path fixtures
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def project_root() -> Path:
    """Return the project root directory."""
    return PROJECT_ROOT


@pytest.fixture
def src_root() -> Path:
    """Return the source code root directory."""
    return PROJECT_ROOT / "src"


@pytest.fixture
def tads_root() -> Path:
    """Return the tads package directory."""
    return PROJECT_ROOT / "src" / "tads"


@pytest.fixture(scope="session")
def tmp_data_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Create a temporary data directory for test outputs."""
    return tmp_path_factory.mktemp("tads_test_data")


# ============================================================
# Synthetic data generators
# ============================================================


def _generate_timestamp(
    base: datetime.datetime,
    offset_seconds: float,
) -> datetime.datetime:
    """Generate a timestamp offset from a base time."""
    return base + datetime.timedelta(seconds=offset_seconds)


@pytest.fixture
def july_base_timestamp() -> datetime.datetime:
    """Base timestamp in July for training data."""
    return datetime.datetime(2025, 7, 15, 12, 0, 0, tzinfo=datetime.timezone.utc)


@pytest.fixture
def august_base_timestamp() -> datetime.datetime:
    """Base timestamp in August for evaluation data."""
    return datetime.datetime(2025, 8, 15, 12, 0, 0, tzinfo=datetime.timezone.utc)


@pytest.fixture
def synthetic_events_schema() -> pa.Schema:
    """PyArrow schema for synthetic cybersecurity events."""
    return pa.schema([
        pa.field("@timestamp", pa.timestamp("ms", tz="UTC")),
        pa.field("source_ip", pa.string()),
        pa.field("dest_ip", pa.string()),
        pa.field("dest_port", pa.int32()),
        pa.field("protocol", pa.string()),
        pa.field("action", pa.string()),
        pa.field("bytes_sent", pa.int64()),
        pa.field("bytes_received", pa.int64()),
        pa.field("user_agent", pa.string()),
        pa.field("event_type", pa.string()),
    ])


def generate_synthetic_events(
    n_events: int,
    base_timestamp: datetime.datetime,
    duration_seconds: float = 60.0,
    seed: int = 42,
) -> pa.Table:
    """
    Generate synthetic cybersecurity events as a PyArrow Table.

    Events are distributed across the specified duration with realistic-looking
    but synthetic field values. Used for testing pipeline correctness without
    requiring a real Elasticsearch connection.

    Args:
        n_events: Number of events to generate.
        base_timestamp: Starting timestamp for event generation.
        duration_seconds: Time span over which to distribute events.
        seed: Random seed for reproducibility (Constraint #20).

    Returns:
        PyArrow Table with synthetic events.
    """
    rng = random.Random(seed)

    source_ips = [f"10.0.{rng.randint(1, 254)}.{rng.randint(1, 254)}" for _ in range(20)]
    dest_ips = [f"192.168.{rng.randint(1, 254)}.{rng.randint(1, 254)}" for _ in range(30)]
    protocols = ["TCP", "UDP", "ICMP", "HTTP", "HTTPS", "DNS", "SSH"]
    actions = ["allow", "deny", "drop", "reset", "monitor"]
    user_agents = [
        "Mozilla/5.0",
        "curl/7.68.0",
        "python-requests/2.28.0",
        "Wget/1.21",
        "Go-http-client/1.1",
    ]
    event_types = ["connection", "dns_query", "http_request", "authentication", "file_access"]

    timestamps = []
    for _ in range(n_events):
        offset = rng.uniform(0, duration_seconds)
        ts = _generate_timestamp(base_timestamp, offset)
        timestamps.append(ts)

    timestamps.sort()

    data = {
        "@timestamp": timestamps,
        "source_ip": [rng.choice(source_ips) for _ in range(n_events)],
        "dest_ip": [rng.choice(dest_ips) for _ in range(n_events)],
        "dest_port": [rng.choice([22, 53, 80, 443, 445, 3389, 8080, 8443]) for _ in range(n_events)],
        "protocol": [rng.choice(protocols) for _ in range(n_events)],
        "action": [rng.choice(actions) for _ in range(n_events)],
        "bytes_sent": [rng.randint(40, 65535) for _ in range(n_events)],
        "bytes_received": [rng.randint(40, 65535) for _ in range(n_events)],
        "user_agent": [rng.choice(user_agents) for _ in range(n_events)],
        "event_type": [rng.choice(event_types) for _ in range(n_events)],
    }

    return pa.table(data)


@pytest.fixture
def small_synthetic_events(july_base_timestamp: datetime.datetime) -> pa.Table:
    """Generate a small set of synthetic events (100 events, 60 seconds) for unit tests."""
    return generate_synthetic_events(
        n_events=100,
        base_timestamp=july_base_timestamp,
        duration_seconds=60.0,
        seed=42,
    )


@pytest.fixture
def medium_synthetic_events(july_base_timestamp: datetime.datetime) -> pa.Table:
    """Generate a medium set of synthetic events (10,000 events, 1 hour) for integration tests."""
    return generate_synthetic_events(
        n_events=10_000,
        base_timestamp=july_base_timestamp,
        duration_seconds=3600.0,
        seed=42,
    )


@pytest.fixture
def synthetic_events_parquet(
    small_synthetic_events: pa.Table,
    tmp_data_dir: Path,
) -> Path:
    """Write synthetic events to a Parquet file and return its path."""
    path = tmp_data_dir / "synthetic_events.parquet"
    pq.write_table(small_synthetic_events, path, compression="zstd")
    return path


# ============================================================
# Window fixtures
# ============================================================


@pytest.fixture
def expected_window_count() -> int:
    """Expected number of 5-second windows in a 60-second span."""
    return 60 // WINDOW_SIZE_SECONDS  # 12 windows
