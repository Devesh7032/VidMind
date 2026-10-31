import os
import re
import urllib.parse
import ipaddress
from typing import Optional, Dict, Any, List, Tuple
from app.config import settings


class SecurityError(Exception):
    """Base exception for security violations (SSRF, IDOR, Secret Leak, Path Traversal)."""
    pass


class SecurityService:
    """
    VidMind Security & Compliance Service.
    Pillar 1: Security (SSRF protection, YouTube URL validation, input size bounds, secret scrubbing, path safety).
    """

    MAX_PROMPT_LENGTH = 10000
    MAX_CHAT_MESSAGE_LENGTH = 4000
    MAX_PAGE_SIZE = 50
    MAX_PLAYLIST_VIDEOS = 50

    ALLOWED_SCHEMES = {"http", "https"}
    ALLOWED_DOMAINS = {
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "music.youtube.com",
        "youtu.be"
    }

    PRIVATE_IP_NETWORKS = [
        ipaddress.ip_network("127.0.0.0/8"),
        ipaddress.ip_network("10.0.0.0/8"),
        ipaddress.ip_network("172.16.0.0/12"),
        ipaddress.ip_network("192.168.0.0/16"),
        ipaddress.ip_network("169.254.0.0/16"),  # Cloud Instance Metadata
        ipaddress.ip_network("::1/128"),
        ipaddress.ip_network("fc00::/7"),
        ipaddress.ip_network("fe80::/10")
    ]

    def validate_youtube_url(self, source_url: str) -> str:
        """
        SSRF & YouTube URL Validation:
        Strictly validates source_url before any network request.
        Only allows public YouTube domain formats. Rejects internal IPs, localhost, cloud metadata, and arbitrary protocols.
        """
        if not source_url or not isinstance(source_url, str):
            raise SecurityError("Invalid URL: Source URL must be a non-empty string.")

        url_clean = source_url.strip()
        if len(url_clean) > 2048:
            raise SecurityError("Invalid URL: Source URL exceeds maximum allowed length.")

        parsed = urllib.parse.urlparse(url_clean)

        # 1. Scheme Check
        if parsed.scheme.lower() not in self.ALLOWED_SCHEMES:
            raise SecurityError(f"Invalid URL protocol '{parsed.scheme}'. Only HTTP and HTTPS are permitted.")

        # 2. Hostname Check
        hostname = (parsed.hostname or "").lower()
        if not hostname:
            raise SecurityError("Invalid URL: Missing hostname.")

        # Check for direct IP inputs (localhost / private IPs)
        try:
            ip_obj = ipaddress.ip_address(hostname)
            for priv_net in self.PRIVATE_IP_NETWORKS:
                if ip_obj in priv_net:
                    raise SecurityError(f"SSRF Violation: Access to private IP range '{hostname}' is blocked.")
        except ValueError:
            # Hostname is a domain name, not a raw IP address
            pass

        if hostname == "localhost" or hostname.endswith(".localhost") or hostname == "127.0.0.1":
            raise SecurityError("SSRF Violation: Access to local loopback addresses is blocked.")

        # Verify domain against allowed YouTube domain whitelist
        if not any(hostname == domain or hostname.endswith("." + domain) for domain in self.ALLOWED_DOMAINS):
            raise SecurityError(f"SSRF Violation: Domain '{hostname}' is not a supported public YouTube domain.")

        # 3. Path & Query Check for Video/Playlist format
        path = parsed.path
        query = parsed.query
        is_video = "v=" in query or "/watch" in path or "youtu.be/" in url_clean or "/shorts/" in path
        is_playlist = "list=" in query or "/playlist" in path

        if not (is_video or is_playlist):
            raise SecurityError("Invalid YouTube URL: URL must contain a valid video ID ('v=') or playlist ID ('list=').")

        return url_clean

    def validate_prompt(self, user_prompt: str) -> str:
        """Enforces prompt length bounds."""
        if not user_prompt or not user_prompt.strip():
            raise SecurityError("User prompt cannot be empty.")
        prompt_clean = user_prompt.strip()
        if len(prompt_clean) > self.MAX_PROMPT_LENGTH:
            raise SecurityError(f"User prompt exceeds maximum length of {self.MAX_PROMPT_LENGTH} characters.")
        return prompt_clean

    def validate_chat_message(self, content: str) -> str:
        """Enforces chat message length bounds."""
        if not content or not content.strip():
            raise SecurityError("Chat message cannot be empty.")
        clean_content = content.strip()
        if len(clean_content) > self.MAX_CHAT_MESSAGE_LENGTH:
            raise SecurityError(f"Chat message exceeds maximum length of {self.MAX_CHAT_MESSAGE_LENGTH} characters.")
        return clean_content

    def validate_pagination(self, page: int, page_size: int) -> Tuple[int, int]:
        """Enforces pagination bounds."""
        safe_page = max(1, page)
        safe_size = max(1, min(self.MAX_PAGE_SIZE, page_size))
        return safe_page, safe_size

    def sanitize_path_component(self, name: str) -> str:
        """Sanitizes path against path traversal attacks (`..`)."""
        if not name:
            return "safe_resource"
        base = os.path.basename(name)
        cleaned = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', base)
        return cleaned.replace("..", "_") or "safe_resource"

    def scrub_secrets(self, text: str) -> str:
        """Scrubs any secret API keys from text or exception strings."""
        if not text or not isinstance(text, str):
            return ""
        for key_name in ["gemini_api_key_1", "gemini_api_key_2", "gemini_api_key", "secret_key"]:
            val = getattr(settings, key_name, None)
            if val and isinstance(val, str) and len(val) > 8:
                text = text.replace(val, "[REDACTED_SECRET]")
        return text


# Global singleton instance for security service
security_service = SecurityService()
