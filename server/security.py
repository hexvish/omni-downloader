"""
SSRF and URL Security Validator for Omni Downloader Server.
Protects against Server-Side Request Forgery (SSRF) and access to internal metadata/private IP ranges.
"""

import ipaddress
import socket
from urllib.parse import urlparse

# Private, loopback, and cloud metadata networks that must NEVER be accessed
DISALLOWED_NETWORKS = [
    ipaddress.ip_network('127.0.0.0/8'),        # IPv4 Loopback
    ipaddress.ip_network('10.0.0.0/8'),         # RFC 1918 Private Class A
    ipaddress.ip_network('172.16.0.0/12'),      # RFC 1918 Private Class B
    ipaddress.ip_network('192.168.0.0/16'),     # RFC 1918 Private Class C
    ipaddress.ip_network('169.254.0.0/16'),     # Link-Local / Cloud Metadata (169.254.169.254)
    ipaddress.ip_network('0.0.0.0/8'),          # Current network
    ipaddress.ip_network('100.64.0.0/10'),      # Carrier-grade NAT
    ipaddress.ip_network('::1/128'),            # IPv6 Loopback
    ipaddress.ip_network('fc00::/7'),           # IPv6 Unique Local Address
    ipaddress.ip_network('fe80::/10'),          # IPv6 Link-Local
]

BLOCKED_HOSTNAMES = {
    'localhost',
    'metadata.google.internal',
    'instance-data',
    '169.254.169.254',
}

def is_safe_url(url: str) -> tuple[bool, str]:
    """
    Validates that a URL is safe to fetch on the server:
    1. Must use http or https scheme.
    2. Must have a valid hostname.
    3. Resolves DNS and checks that no resolved IP is private, loopback, or cloud metadata.
    
    Returns (is_safe, error_message).
    """
    if not url or not isinstance(url, str):
        return False, "URL cannot be empty."

    cleaned_url = url.strip()

    try:
        parsed = urlparse(cleaned_url)
    except Exception:
        return False, "Invalid URL structure."

    # 1. Scheme check
    if parsed.scheme.lower() not in ('http', 'https'):
        return False, "Only HTTP and HTTPS URLs are permitted."

    # 2. Hostname check
    hostname = parsed.hostname
    if not hostname:
        return False, "Missing or invalid hostname in URL."

    if hostname.lower() in BLOCKED_HOSTNAMES:
        return False, "Access to internal or metadata hostnames is forbidden."

    # 3. DNS Resolution and IP range validation
    try:
        # Resolve all IPv4 and IPv6 addresses for the host
        addr_info = socket.getaddrinfo(hostname, None)
        resolved_ips = {item[4][0] for item in addr_info}
    except socket.gaierror:
        return False, f"Could not resolve domain: {hostname}"
    except Exception as e:
        return False, f"DNS resolution failed: {str(e)}"

    if not resolved_ips:
        return False, "Host resolved to no valid IP addresses."

    for ip_str in resolved_ips:
        try:
            ip_obj = ipaddress.ip_address(ip_str)
            
            # Check disallowed CIDRs
            for net in DISALLOWED_NETWORKS:
                if ip_obj in net:
                    return False, f"Access to private/internal network ({ip_str}) is blocked."

            # Extra safety checks
            if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_reserved:
                return False, f"Access to restricted IP address ({ip_str}) is blocked."

        except ValueError:
            return False, f"Unrecognized IP address format: {ip_str}"

    return True, ""
