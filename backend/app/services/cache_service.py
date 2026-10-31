import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from app.config import settings


class CacheType:
    METADATA = "METADATA"
    TRANSCRIPT = "TRANSCRIPT"
    FRAMES = "FRAMES"
    VISION = "VISION"
    KNOWLEDGE = "KNOWLEDGE"
    PLAYLIST = "PLAYLIST"


class CacheStatus:
    PENDING = "PENDING"
    READY = "READY"
    INVALID = "INVALID"
    FAILED = "FAILED"


class CacheService:
    """
    VidMind Multi-Tiered Cache Service.
    Caches expensive Operations (Video Metadata, Transcripts, Keyframes, Vision Observations, AI Knowledge Reasoning, Playlist Metadata).
    Uses explicit content & processing fingerprints to prevent incorrect cache hits across different prompts/intents.
    Supports atomic commits (READY status) and safe invalidation without touching user Library knowledge.
    """

    def __init__(self):
        # In-memory cache index: cache_key -> CacheEntry dict
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.processing_version = "m8-v1"

    def _extract_video_id(self, url_or_id: str) -> str:
        """Standardizes YouTube URL or video ID into a clean stable video_id."""
        if not url_or_id:
            return "unknown_video"
        clean = url_or_id.strip()
        if "v=" in clean:
            clean = clean.split("v=")[1].split("&")[0]
        elif "youtu.be/" in clean:
            clean = clean.split("youtu.be/")[1].split("?")[0]
        elif "list=" in clean:
            clean = clean.split("list=")[1].split("&")[0]
        return clean.replace("/", "_").replace("..", "_")

    def generate_content_fingerprint(self, resource_id: str, content_raw: Any = None) -> str:
        v_id = self._extract_video_id(resource_id)
        raw_str = f"{v_id}:{json.dumps(content_raw, sort_keys=True) if content_raw else ''}"
        return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()[:16]

    def generate_processing_fingerprint(
        self,
        intent_category: str,
        user_prompt: str,
        model: str = "gemini-2.5-flash",
        sampling_config: str = "default"
    ) -> str:
        raw = f"{self.processing_version}:{intent_category}:{user_prompt.lower().strip()}:{model}:{sampling_config}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def make_cache_key(self, cache_type: str, resource_id: str, fingerprint: str) -> str:
        v_id = self._extract_video_id(resource_id)
        return f"{cache_type.lower()}:{v_id}:{fingerprint}"

    def get_cache(self, cache_type: str, resource_id: str, fingerprint: str) -> Optional[Any]:
        key = self.make_cache_key(cache_type, resource_id, fingerprint)
        entry = self._cache.get(key)
        if not entry:
            return None
        if entry["status"] != CacheStatus.READY:
            return None
        entry["last_accessed_at"] = datetime.now(timezone.utc).isoformat()
        entry["hit_count"] += 1
        return entry["data"]

    def put_cache_pending(self, cache_type: str, resource_id: str, fingerprint: str) -> str:
        key = self.make_cache_key(cache_type, resource_id, fingerprint)
        now = datetime.now(timezone.utc).isoformat()
        self._cache[key] = {
            "key": key,
            "cache_type": cache_type,
            "resource_id": resource_id,
            "fingerprint": fingerprint,
            "status": CacheStatus.PENDING,
            "data": None,
            "created_at": now,
            "updated_at": now,
            "last_accessed_at": now,
            "hit_count": 0
        }
        return key

    def commit_cache(self, cache_type: str, resource_id: str, fingerprint: str, data: Any) -> bool:
        """Atomic commit: Only transitions to READY when data is fully validated."""
        if data is None:
            return False
        key = self.make_cache_key(cache_type, resource_id, fingerprint)
        now = datetime.now(timezone.utc).isoformat()

        self._cache[key] = {
            "key": key,
            "cache_type": cache_type,
            "resource_id": resource_id,
            "fingerprint": fingerprint,
            "status": CacheStatus.READY,
            "data": data,
            "created_at": self._cache.get(key, {}).get("created_at", now),
            "updated_at": now,
            "last_accessed_at": now,
            "hit_count": self._cache.get(key, {}).get("hit_count", 0)
        }
        return True

    def invalidate_cache(self, cache_type: str, resource_id: str, fingerprint: Optional[str] = None):
        """Invalidates cache entries without deleting user library knowledge."""
        v_id = self._extract_video_id(resource_id)
        prefix = f"{cache_type.lower()}:{v_id}"
        
        keys_to_del = []
        for k, entry in self._cache.items():
            if k.startswith(prefix):
                if fingerprint is None or entry["fingerprint"] == fingerprint:
                    keys_to_del.append(k)

        for k in keys_to_del:
            del self._cache[k]

    def get_cache_stats(self) -> Dict[str, Any]:
        total_entries = len(self._cache)
        ready_entries = sum(1 for e in self._cache.values() if e["status"] == CacheStatus.READY)
        total_hits = sum(e["hit_count"] for e in self._cache.values())
        return {
            "total_entries": total_entries,
            "ready_entries": ready_entries,
            "total_hits": total_hits,
            "processing_version": self.processing_version
        }


# Global singleton instance for cache service
cache_service = CacheService()
