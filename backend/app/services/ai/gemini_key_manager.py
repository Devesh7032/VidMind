import time
import re
from typing import Dict, Any, Tuple, Optional, Callable
from app.config import settings


class GeminiKeyManager:
    """
    VidMind Multi-API-Key Manager & Automatic Failover Engine.
    Orchestrates Dual Gemini API Keys (Key 1 = Primary, Key 2 = Fallback).
    Provides automatic, seamless failover on HTTP 429 rate limit or quota exceeded errors
    without failing extraction jobs or restarting completed pipeline stages.
    Enforces server-side security: Secret key strings and internal slot labels are NEVER exposed to the frontend.
    """

    def __init__(self):
        self._cooldown_until: Dict[str, float] = {
            "KEY_1": 0.0,
            "KEY_2": 0.0
        }
        self._retry_after: Dict[str, Optional[float]] = {
            "KEY_1": None,
            "KEY_2": None
        }
        self._rr_index: int = 0

    def get_key_status(self) -> Dict[str, Any]:
        """Safely returns diagnostic status of configured Gemini keys without exposing key strings."""
        k1 = settings.get_key_1()
        k2 = settings.get_key_2()
        now = time.time()

        k1_status = "NOT CONFIGURED" if not k1 else ("RATE_LIMITED" if now < self._cooldown_until["KEY_1"] else "AVAILABLE")
        k2_status = "NOT CONFIGURED" if not k2 else ("RATE_LIMITED" if now < self._cooldown_until["KEY_2"] else "AVAILABLE")

        active_slot, _ = self.get_active_key_and_slot()

        return {
            "gemini_key_1_status": k1_status,
            "gemini_key_2_status": k2_status,
            "active_key": active_slot,
            "available_keys_count": sum(1 for s in [k1_status, k2_status] if s == "AVAILABLE")
        }

    def reset_expired_keys(self):
        """Automatically restores rate-limited keys back to AVAILABLE pool once cooldown expires."""
        now = time.time()
        for slot in ["KEY_1", "KEY_2"]:
            if self._cooldown_until[slot] > 0 and now >= self._cooldown_until[slot]:
                self._cooldown_until[slot] = 0.0
                self._retry_after[slot] = None

    def get_active_key_and_slot(self) -> Tuple[str, str]:
        """
        Selects an available Gemini API key slot ("KEY_1" or "KEY_2") from the key pool.
        Intelligently distributes requests when both keys are available and automatically
        bypasses rate-limited keys.
        """
        self.reset_expired_keys()
        now = time.time()

        k1 = settings.get_key_1()
        k2 = settings.get_key_2()

        k1_avail = bool(k1) and (now >= self._cooldown_until["KEY_1"])
        k2_avail = bool(k2) and (now >= self._cooldown_until["KEY_2"])

        if k1_avail and k2_avail:
            # Load Balance / Alternate between available keys
            slot = "KEY_1" if (self._rr_index % 2 == 0) else "KEY_2"
            self._rr_index += 1
            key = k1 if slot == "KEY_1" else k2
            return slot, key
        elif k1_avail:
            return "KEY_1", k1
        elif k2_avail:
            return "KEY_2", k2
        elif k1:
            # Fallback to KEY_1 if both are in cooldown (best effort)
            return "KEY_1", k1
        else:
            return "KEY_1", ""

    def mark_key_rate_limited(self, slot_name: str, cooldown_seconds: Optional[int] = None, retry_after_sec: Optional[float] = None):
        """
        Temporarily marks a rate-limited Gemini key as unavailable with a cooldown expiration.
        Respects Retry-After headers when provided by Gemini API.
        """
        cooldown = retry_after_sec or cooldown_seconds or settings.gemini_key_cooldown_seconds
        self._cooldown_until[slot_name] = time.time() + cooldown
        self._retry_after[slot_name] = cooldown
        print(f"[GeminiKeyManager] Key slot marked rate-limited. Cooldown set for {cooldown:.1f} seconds.")

    def is_retryable_error(self, error: Exception, status_code: Optional[int] = None) -> bool:
        """
        Determines if an error is a transient rate-limit / quota / resource exhaustion error suitable for failover.
        Does NOT rotate for permanent errors like bad parameters or unauthenticated keys.
        """
        if status_code in (429, 503, 504):
            return True
        err_msg = str(error).lower()
        retryable_terms = [
            "429", "rate limit", "quota exceeded", "resource exhausted",
            "too many requests", "capacity", "service unavailable", "timeout"
        ]
        return any(term in err_msg for term in retryable_terms)

    def execute_with_failover(self, api_call_func: Callable[[str, str], Any], max_attempts: int = 4) -> Any:
        """
        High-Level Failover Orchestrator:
        Executes `api_call_func(slot_name, api_key)` with automatic multi-key failover.
        On HTTP 429 or quota exceeded, marks active key rate-limited and retries using KEY_2 automatically.
        Only raises a user-facing error if ALL configured keys fail.
        """
        attempted_slots = set()
        last_exception = None

        for attempt in range(max_attempts):
            slot_name, api_key = self.get_active_key_and_slot()

            if not api_key:
                raise ValueError("Gemini API key is not configured. Please set GEMINI_API_KEY_1 in backend/.env.")

            attempted_slots.add(slot_name)

            try:
                # Execute the API call with the active key
                return api_call_func(slot_name, api_key)
            except Exception as e:
                last_exception = e
                # Check status_code attribute if available (e.g. from httpx / HTTP error)
                status_code = getattr(e, "status_code", None)

                if self.is_retryable_error(e, status_code):
                    # Mark rate-limited & failover to next available key in pool
                    self.mark_key_rate_limited(slot_name)
                    print(f"[GeminiKeyManager] Transient error on active key. Automatic failover to next available key...")
                    continue
                else:
                    # Non-retryable error (e.g. bad request, prompt error): do not blindly switch keys
                    raise e

        # If all keys in pool failed due to rate limits or quota
        user_facing_error = (
            "⚠️ I couldn't continue the extraction because the AI processing quota is temporarily unavailable. "
            "Your completed processing steps have been preserved."
        )
        raise RuntimeError(user_facing_error)


# Global singleton instance for Gemini Key Manager
gemini_key_manager = GeminiKeyManager()
