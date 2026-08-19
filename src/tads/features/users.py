"""
User behavioral features.

These features capture user-centric activity within a window, including
diversity of entities accessed by users, concentration of events among users,
and login behaviors.
"""
from __future__ import annotations

from typing import Any

from tads.features.registry import (
    FEATURE_REGISTRY,
    BaseFeature,
    FeatureGroup,
    FeatureMetadata,
)
from tads.features.utils import (
    average_distinct_per_entity,
    calculate_entropy,
    calculate_hhi,
    calculate_historical_deviation,
)


class ActiveUsersFeature(BaseFeature):  # type: ignore[misc]
    """Count of distinct users in the window."""

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="active_users",
            group=FeatureGroup.USERS,
            source_fields=["user_name"],
            mathematical_definition="COUNT(DISTINCT user_name)",
            data_type="int64",
            expected_range=(0, None),
            missing_value_behavior="Nulls mapped to 'unknown'",
            requires_baseline=False,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        events = window_data.get("events", [])
        users = {e.get("user_name") or "unknown" for e in events}
        # If the window is empty, there are 0 users. If there are events but no users, it's 1 ("unknown").
        count = len(users) if events else 0.0
        return {"active_users": float(count)}


class UserEventConcentrationFeature(BaseFeature):  # type: ignore[misc]
    """
    Herfindahl-Hirschman Index (HHI) for user event distribution.
    Ranges from 1/N (perfectly uniform) to 1.0 (all events by 1 user).
    """

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="user_event_concentration",
            group=FeatureGroup.USERS,
            source_fields=["user_name"],
            mathematical_definition="Sum of squared probabilities of events per user",
            data_type="float64",
            expected_range=(0.0, 1.0),
            missing_value_behavior="Nulls mapped to 'unknown'",
            requires_baseline=False,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        events = window_data.get("events", [])
        return {"user_event_concentration": float(calculate_hhi(events, "user_name"))}


class UserDiversityFeature(BaseFeature):  # type: ignore[misc]
    """
    Shannon entropy of the user event distribution.
    Higher values indicate activity is spread across more users.
    """

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="user_diversity",
            group=FeatureGroup.USERS,
            source_fields=["user_name"],
            mathematical_definition="-Sum(p * log2(p)) across distinct users",
            data_type="float64",
            expected_range=(0.0, None),
            missing_value_behavior="Nulls mapped to 'unknown'",
            requires_baseline=False,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        events = window_data.get("events", [])
        return {"user_diversity": float(calculate_entropy(events, "user_name"))}


class LoginVolumeFeature(BaseFeature):  # type: ignore[misc]
    """Count of authentication logon events."""

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="login_volume",
            group=FeatureGroup.USERS,
            source_fields=["event_category", "event_action"],
            mathematical_definition="COUNT(*) where event_category == 'authentication' AND event_action IN ('logon', 'login')",
            data_type="int64",
            expected_range=(0, None),
            missing_value_behavior="Excluded if category or action is missing",
            requires_baseline=False,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        events = window_data.get("events", [])
        count = sum(
            1 for e in events
            if e.get("event_category") == "authentication"
            and e.get("event_action") in ("logon", "login")
        )
        return {"login_volume": float(count)}


class FailedLoginRatioFeature(BaseFeature):  # type: ignore[misc]
    """Ratio of failed logins to total logins."""

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="failed_login_ratio",
            group=FeatureGroup.USERS,
            source_fields=["event_category", "event_action", "event_outcome"],
            mathematical_definition="Failed Logins / Total Logins. 0.0 if no logins.",
            data_type="float64",
            expected_range=(0.0, 1.0),
            missing_value_behavior="Excluded from total if missing category/action",
            requires_baseline=False,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        events = window_data.get("events", [])
        total_logins = 0
        failed_logins = 0

        for e in events:
            if e.get("event_category") == "authentication" and e.get("event_action") in ("logon", "login"):
                total_logins += 1
                if e.get("event_outcome") == "failure":
                    failed_logins += 1

        ratio = (failed_logins / total_logins) if total_logins > 0 else 0.0
        return {"failed_login_ratio": float(ratio)}


class UserHostDiversityFeature(BaseFeature):  # type: ignore[misc]
    """Average number of distinct hosts per user."""

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="user_host_diversity",
            group=FeatureGroup.USERS,
            source_fields=["user_name", "host_name"],
            mathematical_definition="MEAN(COUNT(DISTINCT host_name) GROUP BY user_name)",
            data_type="float64",
            expected_range=(0.0, None),
            missing_value_behavior="Nulls mapped to 'unknown'",
            requires_baseline=False,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        events = window_data.get("events", [])
        return {"user_host_diversity": average_distinct_per_entity(events, "user_name", "host_name")}


class UserIpDiversityFeature(BaseFeature):  # type: ignore[misc]
    """Average number of distinct IPs per user."""

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="user_ip_diversity",
            group=FeatureGroup.USERS,
            source_fields=["user_name", "source_ip"],
            mathematical_definition="MEAN(COUNT(DISTINCT source_ip) GROUP BY user_name)",
            data_type="float64",
            expected_range=(0.0, None),
            missing_value_behavior="Nulls mapped to 'unknown'",
            requires_baseline=False,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        events = window_data.get("events", [])
        return {"user_ip_diversity": average_distinct_per_entity(events, "user_name", "source_ip")}


class UserProcessDiversityFeature(BaseFeature):  # type: ignore[misc]
    """Average number of distinct processes per user."""

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="user_process_diversity",
            group=FeatureGroup.USERS,
            source_fields=["user_name", "process_name"],
            mathematical_definition="MEAN(COUNT(DISTINCT process_name) GROUP BY user_name)",
            data_type="float64",
            expected_range=(0.0, None),
            missing_value_behavior="Nulls mapped to 'unknown'",
            requires_baseline=False,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        events = window_data.get("events", [])
        return {"user_process_diversity": average_distinct_per_entity(events, "user_name", "process_name")}


class HistoricalUserDeviationFeature(BaseFeature):  # type: ignore[misc]
    """
    (Stubbed) Historical deviation of users against July baseline.
    Returns 1.0 for completely unseen users (maximally novel), and 0.0 for fully baseline users.
    """

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="historical_user_deviation",
            group=FeatureGroup.USERS,
            source_fields=["user_name"],
            mathematical_definition="Stubbed baseline comparison. Novel users -> 1.0.",
            data_type="float64",
            expected_range=(0.0, 1.0),
            missing_value_behavior="Null users mapped to 'unknown'",
            requires_baseline=True,
            is_causal=True,  # Assuming baselines are built strictly before t
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        events = window_data.get("events", [])
        baseline = window_data.get("baseline", {})
        dev = calculate_historical_deviation(events, "user_name", baseline, "known_users")
        return {"historical_user_deviation": dev}


# ------------------------------------------------------------------
# Auto-register
# ------------------------------------------------------------------
_FEATURES: list[type[BaseFeature]] = [
    ActiveUsersFeature,
    UserEventConcentrationFeature,
    UserDiversityFeature,
    LoginVolumeFeature,
    FailedLoginRatioFeature,
    UserHostDiversityFeature,
    UserIpDiversityFeature,
    UserProcessDiversityFeature,
    HistoricalUserDeviationFeature,
]

for _cls in _FEATURES:
    if _cls().metadata.name in FEATURE_REGISTRY.names:
        del FEATURE_REGISTRY._features[_cls().metadata.name]
    FEATURE_REGISTRY.register(_cls())
