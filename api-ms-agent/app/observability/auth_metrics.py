"""In-process auth metrics for lightweight observability.

This module intentionally avoids external dependencies (e.g., prometheus_client).
It provides a minimal Prometheus text format exporter suitable for scraping.

Metrics are process-local and reset on restart.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock

_BUCKETS_MS: tuple[float, ...] = (5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000)

# Simple safeguards against unbounded label cardinality (in-process metrics).
_MAX_PROVIDER_LABELS = 10
_MAX_ROLE_LABELS = 50
_MAX_FAILURE_LABELS = 50
_OTHER_LABEL = "other"
_KNOWN_PROVIDERS: set[str] = {"entra", "keycloak", "unknown"}


def _sanitize_label_value(value: str) -> str:
    # Prometheus label values are quoted, but escaping keeps output safe.
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


@dataclass
class _Histogram:
    buckets_ms: tuple[float, ...] = _BUCKETS_MS
    # bucket upper bound -> count
    bucket_counts: dict[float, int] = field(default_factory=dict)
    count: int = 0
    sum_ms: float = 0.0

    def observe(self, value_ms: float) -> None:
        self.count += 1
        self.sum_ms += float(value_ms)
        for bound in self.buckets_ms:
            if value_ms <= bound:
                self.bucket_counts[bound] = self.bucket_counts.get(bound, 0) + 1
        # +Inf bucket is represented implicitly as count


class AuthMetrics:
    """Thread-safe in-process counters/histograms for auth."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._auth_success_total: dict[str, int] = {}
        self._auth_failure_total: dict[tuple[str, str], int] = {}
        self._role_denied_total: dict[str, int] = {}
        self._validation_duration_ms: dict[str, _Histogram] = {}
        self._authorization_duration_ms: dict[tuple[str, str], _Histogram] = {}

    def _normalize_provider_label(self, provider: str) -> str:
        provider = (provider or "unknown").strip().lower()
        if provider in _KNOWN_PROVIDERS:
            return provider

        # Guardrails: allow limited number of unknown providers.
        if (
            len(self._auth_success_total) >= _MAX_PROVIDER_LABELS
            and provider not in self._auth_success_total
        ):
            return _OTHER_LABEL

        return provider

    def _normalize_role_label(self, role: str) -> str:
        role = (role or "").strip()
        if not role:
            return "unknown"

        if len(self._role_denied_total) >= _MAX_ROLE_LABELS and role not in self._role_denied_total:
            return _OTHER_LABEL
        return role

    def _normalize_failure_key(self, reason: str, code: str) -> tuple[str, str]:
        reason = (reason or "unknown").strip()
        code = (code or "unknown").strip()
        key = (reason, code)
        if (
            len(self._auth_failure_total) >= _MAX_FAILURE_LABELS
            and key not in self._auth_failure_total
        ):
            return (_OTHER_LABEL, _OTHER_LABEL)
        return key

    def inc_auth_success(self, *, provider: str) -> None:
        with self._lock:
            provider_label = self._normalize_provider_label(provider)
            current = self._auth_success_total.get(provider_label, 0)
            self._auth_success_total[provider_label] = current + 1

    def inc_auth_failure(self, *, reason: str, code: str) -> None:
        with self._lock:
            key = self._normalize_failure_key(reason, code)
            self._auth_failure_total[key] = self._auth_failure_total.get(key, 0) + 1

    def inc_role_denied(self, *, role: str) -> None:
        with self._lock:
            role_label = self._normalize_role_label(role)
            self._role_denied_total[role_label] = self._role_denied_total.get(role_label, 0) + 1

    def observe_validation_duration_ms(self, *, provider: str, duration_ms: float) -> None:
        with self._lock:
            provider_label = self._normalize_provider_label(provider)
            hist = self._validation_duration_ms.get(provider_label)
            if hist is None:
                hist = _Histogram()
                self._validation_duration_ms[provider_label] = hist
            hist.observe(duration_ms)

    def observe_authorization_duration_ms(
        self,
        *,
        provider: str,
        outcome: str,
        duration_ms: float,
    ) -> None:
        outcome = (outcome or "unknown").strip().lower()
        if outcome not in {"allowed", "denied", "unknown"}:
            outcome = "unknown"

        with self._lock:
            provider_label = self._normalize_provider_label(provider)
            key = (provider_label, outcome)
            hist = self._authorization_duration_ms.get(key)
            if hist is None:
                hist = _Histogram()
                self._authorization_duration_ms[key] = hist
            hist.observe(duration_ms)

    def render_prometheus(self) -> str:
        """Render all metrics in Prometheus text exposition format."""
        lines: list[str] = []

        with self._lock:
            # auth_success_total
            lines.append("# HELP auth_success_total Count of successful authentications")
            lines.append("# TYPE auth_success_total counter")
            for provider, count in sorted(self._auth_success_total.items()):
                lines.append(
                    f'auth_success_total{{provider="{_sanitize_label_value(provider)}"}} {count}'
                )

            # auth_failure_total
            lines.append("# HELP auth_failure_total Count of failed authentications")
            lines.append("# TYPE auth_failure_total counter")
            for (reason, code), count in sorted(self._auth_failure_total.items()):
                reason_label = _sanitize_label_value(reason)
                code_label = _sanitize_label_value(code)
                lines.append(
                    "auth_failure_total"
                    f'{{reason="{reason_label}",code="{code_label}"}} {count}'
                )

            # auth_role_denied_total
            lines.append("# HELP auth_role_denied_total Count of authorization role denials")
            lines.append("# TYPE auth_role_denied_total counter")
            for role, count in sorted(self._role_denied_total.items()):
                lines.append(
                    f'auth_role_denied_total{{role="{_sanitize_label_value(role)}"}} {count}'
                )

            # auth_validation_duration_ms
            lines.append(
                "# HELP auth_validation_duration_ms Token validation duration in milliseconds"
            )
            lines.append("# TYPE auth_validation_duration_ms histogram")
            for provider, hist in sorted(self._validation_duration_ms.items()):
                provider_label = _sanitize_label_value(provider)
                cumulative = 0
                for bound in hist.buckets_ms:
                    cumulative += hist.bucket_counts.get(bound, 0)
                            labels = f'provider="{provider_label}",le="{bound}"'
                            lines.append(f'auth_validation_duration_ms_bucket{{{labels}}} {cumulative}')
                # +Inf bucket
                labels_inf = f'provider="{provider_label}",le="+Inf"'
                lines.append(f'auth_validation_duration_ms_bucket{{{labels_inf}}} {hist.count}')
                labels_no_le = f'provider="{provider_label}"'
                lines.append(f'auth_validation_duration_ms_sum{{{labels_no_le}}} {hist.sum_ms}')
                lines.append(f'auth_validation_duration_ms_count{{{labels_no_le}}} {hist.count}')

            # auth_authorization_duration_ms
            lines.append("# HELP auth_authorization_duration_ms Authorization duration (ms)")
            lines.append("# TYPE auth_authorization_duration_ms histogram")
            for (provider, outcome), hist in sorted(self._authorization_duration_ms.items()):
                provider_label = _sanitize_label_value(provider)
                outcome_label = _sanitize_label_value(outcome)
                cumulative = 0
                for bound in hist.buckets_ms:
                    cumulative += hist.bucket_counts.get(bound, 0)
                    labels = f'provider="{provider_label}",outcome="{outcome_label}",le="{bound}"'
                    lines.append(f'auth_authorization_duration_ms_bucket{{{labels}}} {cumulative}')
                labels_inf = f'provider="{provider_label}",outcome="{outcome_label}",le="+Inf"'
                lines.append(f'auth_authorization_duration_ms_bucket{{{labels_inf}}} {hist.count}')
                labels_no_le = f'provider="{provider_label}",outcome="{outcome_label}"'
                lines.append(f'auth_authorization_duration_ms_sum{{{labels_no_le}}} {hist.sum_ms}')
                lines.append(f'auth_authorization_duration_ms_count{{{labels_no_le}}} {hist.count}')

        return "\n".join(lines) + "\n"


_metrics_singleton: AuthMetrics | None = None


def get_auth_metrics() -> AuthMetrics:
    global _metrics_singleton
    if _metrics_singleton is None:
        _metrics_singleton = AuthMetrics()
    return _metrics_singleton
