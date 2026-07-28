"""Small dependency-free Prometheus metric registry for manifest operations."""
from __future__ import annotations

from threading import Lock

_lock = Lock()
_values: dict[str, float] = {
    "mirrorone_manifest_last_success_timestamp": 0,
    "mirrorone_manifest_build_duration_seconds": 0,
    "mirrorone_manifest_artifact_count": 0,
    "mirrorone_manifest_checksum_available_count": 0,
    "mirrorone_manifest_checksum_missing_count": 0,
    "mirrorone_manifest_conflict_count": 0,
    "mirrorone_cache_checksum_mismatch_total": 0,
    "mirrorone_cache_unverified_artifact_count": 0,
}


def set_metric(name: str, value: float) -> None:
    with _lock:
        _values[name] = value


def increment_metric(name: str, amount: float = 1) -> None:
    with _lock:
        _values[name] = _values.get(name, 0) + amount


def render_metrics() -> str:
    """Render the registry in Prometheus text exposition format."""
    with _lock:
        values = dict(_values)
    lines = []
    for name, value in sorted(values.items()):
        metric_type = "counter" if name.endswith("_total") else "gauge"
        lines.append(f"# TYPE {name} {metric_type}")
        lines.append(f"{name} {value!r}")
    return "\n".join(lines) + "\n"
