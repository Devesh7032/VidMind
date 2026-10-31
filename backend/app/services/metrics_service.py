import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional


class MetricsService:
    """
    VidMind Operational Metrics & Observability Collector.
    Pillar 3: Observability (Request count, latency, error count, active jobs, cache hit/miss rate, Gemini 429/fallback count).
    Uses bounded labels to prevent cardinality explosion.
    """

    def __init__(self):
        self._http_requests_total: int = 0
        self._http_errors_total: int = 0
        self._http_latency_sum: float = 0.0
        
        self._cache_hits: int = 0
        self._cache_misses: int = 0

        self._active_jobs: int = 0
        self._completed_jobs: int = 0
        self._failed_jobs: int = 0

        self._gemini_requests: int = 0
        self._gemini_fallbacks: int = 0
        self._gemini_429s: int = 0

    def record_http_request(self, endpoint: str, status_code: int, duration_seconds: float):
        self._http_requests_total += 1
        self._http_latency_sum += duration_seconds
        if status_code >= 400:
            self._http_errors_total += 1

    def record_cache_access(self, hit: bool):
        if hit:
            self._cache_hits += 1
        else:
            self._cache_misses += 1

    def record_job_start(self):
        self._active_jobs += 1

    def record_job_finish(self, success: bool):
        self._active_jobs = max(0, self._active_jobs - 1)
        if success:
            self._completed_jobs += 1
        else:
            self._failed_jobs += 1

    def record_gemini_event(self, event_type: str):
        if event_type == "request":
            self._gemini_requests += 1
        elif event_type == "fallback":
            self._gemini_fallbacks += 1
        elif event_type == "429":
            self._gemini_429s += 1

    def get_metrics_summary(self) -> Dict[str, Any]:
        avg_latency = (self._http_latency_sum / self._http_requests_total) if self._http_requests_total > 0 else 0.0
        total_cache = self._cache_hits + self._cache_misses
        hit_ratio = (self._cache_hits / total_cache * 100) if total_cache > 0 else 0.0

        return {
            "http": {
                "total_requests": self._http_requests_total,
                "total_errors": self._http_errors_total,
                "avg_latency_seconds": round(avg_latency, 4)
            },
            "cache": {
                "hits": self._cache_hits,
                "misses": self._cache_misses,
                "hit_ratio_percent": round(hit_ratio, 2)
            },
            "jobs": {
                "active_jobs": self._active_jobs,
                "completed_jobs": self._completed_jobs,
                "failed_jobs": self._failed_jobs
            },
            "gemini": {
                "requests": self._gemini_requests,
                "fallbacks": self._gemini_fallbacks,
                "rate_limits_429": self._gemini_429s
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# Global singleton instance for metrics service
metrics_service = MetricsService()
