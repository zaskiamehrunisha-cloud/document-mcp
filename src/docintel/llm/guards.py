"""
Offline guard for DOCINTEL.
Enforces the hard constraint that all LLM/embedding calls must go to
local/on-premise hosts only. No cloud API calls are permitted anywhere
in the pipeline.
"""

import ipaddress
import socket
from typing import List, Optional

from docintel.common.exceptions import OfflineGuardViolationError
from docintel.common.logging import get_logger

logger = get_logger(__name__)


class OfflineGuard:
    """
    Validates that target hosts are in the allowed list.
    Blocks any attempt to call cloud or external endpoints.
    """
    
    def __init__(self, allowed_hosts: Optional[List[str]] = None):
        """
        Initialize the offline guard.
        
        Args:
            allowed_hosts: List of allowed hostnames/IPs. If None, uses defaults.
        """
        if allowed_hosts is None:
            allowed_hosts = [
                "localhost",
                "127.0.0.1",
                "::1",
                "ollama",
                "vllm",
                "localhost.localdomain",
            ]
        self.allowed_hosts = set(allowed_hosts)
        self._resolved_cache: dict[str, str] = {}
    
    def is_allowed(self, url: str) -> bool:
        """
        Check if a URL's host is in the allowed list.
        
        Args:
            url: The URL to check (e.g., "http://localhost:11434/v1")
            
        Returns:
            True if the host is allowed, False otherwise
        """
        from urllib.parse import urlparse
        
        try:
            parsed = urlparse(url)
            host = parsed.hostname
            
            if not host:
                logger.warning("URL has no hostname", extra={"url": url})
                return False
            
            # Check direct match
            if host.lower() in self.allowed_hosts:
                logger.debug("Host allowed by direct match", extra={"host": host, "url": url})
                return True
            
            # Check if it's an IP address in private ranges
            try:
                ip = ipaddress.ip_address(host)
                if ip.is_private or ip.is_loopback or ip.is_link_local:
                    logger.debug("Host allowed as private/loopback IP", extra={"host": host, "url": url})
                    return True
            except ValueError:
                # Not an IP address, try DNS resolution
                pass
            
            # Try to resolve the hostname and check if it resolves to a private IP
            try:
                resolved_ip = self._resolve_host(host)
                ip_obj = ipaddress.ip_address(resolved_ip)
                if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local:
                    logger.debug("Host allowed by resolved IP", extra={"host": host, "resolved_ip": resolved_ip, "url": url})
                    return True
            except (socket.gaierror, ValueError) as e:
                logger.warning("Could not resolve host", extra={"host": host, "error": str(e)})
            
            # Host is not allowed
            logger.warning(
                "Host not in allowed list",
                extra={"host": host, "url": url, "allowed_hosts": list(self.allowed_hosts)},
            )
            return False
            
        except Exception as e:
            logger.error("Error parsing URL for offline guard", extra={"url": url, "error": str(e)})
            return False
    
    def validate(self, url: str) -> None:
        """
        Validate a URL and raise an exception if not allowed.
        
        Args:
            url: The URL to validate
            
        Raises:
            OfflineGuardViolationError: If the host is not in the allowed list
        """
        if not self.is_allowed(url):
            raise OfflineGuardViolationError(
                host=self._extract_host(url),
                allowed_hosts=list(self.allowed_hosts),
            )
    
    def _extract_host(self, url: str) -> str:
        """Extract the host from a URL."""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.hostname or url
    
    def _resolve_host(self, host: str) -> str:
        """Resolve a hostname to an IP address (with caching)."""
        if host in self._resolved_cache:
            return self._resolved_cache[host]
        
        try:
            # Try IPv4 first
            results = socket.getaddrinfo(host, None, socket.AF_INET)
            if results:
                ip = results[0][4][0]
                self._resolved_cache[host] = ip
                return ip
            
            # Try IPv6
            results = socket.getaddrinfo(host, None, socket.AF_INET6)
            if results:
                ip = results[0][4][0]
                self._resolved_cache[host] = ip
                return ip
        except socket.gaierror:
            pass
        
        raise socket.gaierror(f"Could not resolve host: {host}")
    
    def add_allowed_host(self, host: str) -> None:
        """Add a host to the allowed list."""
        self.allowed_hosts.add(host.lower())
        logger.info("Added allowed host", extra={"host": host})
    
    def remove_allowed_host(self, host: str) -> None:
        """Remove a host from the allowed list."""
        self.allowed_hosts.discard(host.lower())
        logger.info("Removed allowed host", extra={"host": host})


# Global offline guard instance
_offline_guard: Optional[OfflineGuard] = None


def get_offline_guard() -> OfflineGuard:
    """Get the global offline guard instance."""
    global _offline_guard
    if _offline_guard is None:
        from docintel.config.settings import settings
        _offline_guard = OfflineGuard(allowed_hosts=settings.allowed_hosts_list)
    return _offline_guard


def validate_url(url: str) -> None:
    """
    Convenience function to validate a URL against the offline guard.
    
    Args:
        url: The URL to validate
        
    Raises:
        OfflineGuardViolationError: If the host is not allowed
    """
    get_offline_guard().validate(url)