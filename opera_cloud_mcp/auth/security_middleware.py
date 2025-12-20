"""
Security middleware for OPERA Cloud MCP server.

This module provides comprehensive security middleware including rate limiting,
request validation, security headers, and threat detection.
"""

import asyncio
import hashlib
import ipaddress
import logging
import time
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from pydantic import BaseModel

from opera_cloud_mcp.auth.audit_logger import audit_logger
from opera_cloud_mcp.config.security_settings import SecuritySettings
from opera_cloud_mcp.utils.exceptions import SecurityError

logger = logging.getLogger(__name__)


class SecurityContext(BaseModel):
    """Security context for request processing."""

    client_id: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    request_id: str
    timestamp: datetime
    risk_score: int = 0
    blocked_reason: str | None = None
    security_flags: set[str] = set()


class ThreatDetector:
    """Advanced threat detection system."""

    def __init__(self, settings: SecuritySettings):
        self.settings = settings
        self._suspicious_ips: dict[str, list[datetime]] = {}
        self._user_agent_patterns: set[str] = {
            # Suspicious user agent patterns
            "bot",
            "crawler",
            "spider",
            "scraper",
            "scanner",
            "nikto",
            "sqlmap",
            "burp",
            "nmap",
            "curl/7.0",
            "python-requests/0.",
            "python-urllib/0.",
        }
        self._known_attack_patterns: set[str] = {
            # Common attack patterns in requests
            "../",
            "..\\",
            "<script",
            "javascript:",
            "vbscript:",
            "onload=",
            "onerror=",
            "union select",
            "' or '1'='1",
            "exec(",
            "system(",
            "eval(",
            "base64_decode(",
        }

    async def analyze_request(self, context: SecurityContext) -> tuple[int, list[str]]:
        """
        Analyze request for security threats.

        Returns:
            Tuple of (risk_score, threat_indicators)
        """
        # Perform all threat analyses in parallel
        analysis_results = await asyncio.gather(
            self._analyze_ip_threats(context),
            self._analyze_user_agent_threats(context),
            self._analyze_frequency_threats(context),
            self._analyze_behavioral_patterns(context),
            return_exceptions=True,
        )

        # Handle any exceptions and combine results
        risk_scores = []
        all_threats = []

        for result in analysis_results:
            if isinstance(result, Exception):
                logger.warning(f"Threat analysis failed: {result}")
                continue
            elif isinstance(result, tuple) and len(result) == 2:
                risk_score, threats = result
                risk_scores.append(risk_score)
                all_threats.extend(threats)

        # Combine all threats with a maximum cap
        total_risk = sum(risk_scores)
        return min(100, total_risk), all_threats

    async def _analyze_ip_threats(
        self, context: SecurityContext
    ) -> tuple[int, list[str]]:
        """Analyze IP-based threats."""
        if context.ip_address:
            return await self._analyze_ip_address(context.ip_address)
        return 0, []

    async def _analyze_user_agent_threats(
        self, context: SecurityContext
    ) -> tuple[int, list[str]]:
        """Analyze user agent threats."""
        if context.user_agent:
            return self._analyze_user_agent(context.user_agent)
        return 0, []

    async def _analyze_frequency_threats(
        self, context: SecurityContext
    ) -> tuple[int, list[str]]:
        """Analyze request frequency threats."""
        return await self._analyze_request_frequency(context)

    async def _analyze_behavioral_threats(
        self, context: SecurityContext
    ) -> tuple[int, list[str]]:
        """Analyze behavioral pattern threats."""
        if self.settings.enable_anomaly_detection:
            return await self._analyze_behavioral_patterns(context)
        return 0, []

    def _check_private_ip_in_production(
        self, ip, ip_address: str, risk_score: int, threats: list[str]
    ) -> tuple[int, list[str]]:
        """Check for private/local addresses in production."""
        if (
            self.settings.require_https
            and (ip.is_private or ip.is_loopback)
            and not self.settings.security_testing_mode
        ):
            risk_score += 20
            threats.append("private_ip_in_production")
        return risk_score, threats

    def _check_malicious_ip_ranges(
        self, ip, ip_address: str, risk_score: int, threats: list[str]
    ) -> tuple[int, list[str]]:
        """Check for known malicious ranges."""
        if self._is_suspicious_ip_range(ip):
            risk_score += 30
            threats.append("suspicious_ip_range")
        return risk_score, threats

    def _check_request_frequency(
        self, ip_address: str, risk_score: int, threats: list[str]
    ) -> tuple[int, list[str]]:
        """Check request frequency from this IP."""
        if ip_address in self._suspicious_ips:
            recent_requests = self._suspicious_ips[ip_address]
            cutoff = datetime.now(UTC) - timedelta(minutes=10)
            recent_requests = [req for req in recent_requests if req > cutoff]

            if len(recent_requests) > 50:  # More than 50 requests in 10 minutes
                risk_score += 40
                threats.append("high_frequency_requests")
            elif len(recent_requests) > 20:
                risk_score += 20
                threats.append("elevated_request_frequency")
        return risk_score, threats

    def _record_ip_request(self, ip_address: str) -> None:
        """Record this request and clean old entries."""
        now = datetime.now(UTC)
        if ip_address not in self._suspicious_ips:
            self._suspicious_ips[ip_address] = []
        self._suspicious_ips[ip_address].append(now)

        # Clean old entries
        cutoff = now - timedelta(hours=1)
        self._suspicious_ips[ip_address] = [
            req for req in self._suspicious_ips[ip_address] if req > cutoff
        ]

    async def _analyze_ip_address(self, ip_address: str) -> tuple[int, list[str]]:
        """Analyze IP address for threats."""
        risk_score = 0
        threats: list[str] = []

        try:
            ip = ipaddress.ip_address(ip_address)

            # Check for private/local addresses in production
            risk_score, threats = self._check_private_ip_in_production(
                ip, ip_address, risk_score, threats
            )

            # Check for known malicious ranges
            risk_score, threats = self._check_malicious_ip_ranges(
                ip, ip_address, risk_score, threats
            )

            # Check request frequency from this IP
            risk_score, threats = self._check_request_frequency(
                ip_address, risk_score, threats
            )

            # Record this request
            self._record_ip_request(ip_address)

        except ValueError:
            risk_score += 50
            threats.append("invalid_ip_address")

        # IP reputation check (if enabled)
        if self.settings.enable_ip_reputation_check:
            reputation_risk, reputation_threats = await self._check_ip_reputation(
                ip_address
            )
            risk_score += reputation_risk
            threats.extend(reputation_threats)

        return risk_score, threats

    def _analyze_user_agent(self, user_agent: str) -> tuple[int, list[str]]:
        """Analyze user agent for suspicious patterns."""
        risk_score = 0
        threats = []

        if not user_agent or len(user_agent) < 10:
            risk_score += 15
            threats.append("missing_or_short_user_agent")
            return risk_score, threats

        ua_lower = user_agent.lower()

        # Check for suspicious patterns
        for pattern in self._user_agent_patterns:
            if pattern in ua_lower:
                risk_score += 25
                threats.append(f"suspicious_user_agent_pattern_{pattern}")
                break

        # Check for attack patterns in user agent
        for pattern in self._known_attack_patterns:
            if pattern in ua_lower:
                risk_score += 40
                threats.append("attack_pattern_in_user_agent")
                break

        # Check user agent length (extremely long UAs can be suspicious)
        if len(user_agent) > 2000:
            risk_score += 20
            threats.append("extremely_long_user_agent")

        # Check for common legitimate patterns to reduce false positives
        legitimate_patterns = [
            "mozilla",
            "chrome",
            "safari",
            "firefox",
            "opera",
            "edge",
        ]
        has_legitimate = any(pattern in ua_lower for pattern in legitimate_patterns)

        if not has_legitimate and not self.settings.security_testing_mode:
            risk_score += 10
            threats.append("non_standard_user_agent")

        return risk_score, threats

    async def _analyze_request_frequency(
        self, context: SecurityContext
    ) -> tuple[int, list[str]]:
        """Analyze request frequency patterns."""
        risk_score = 0
        threats: list[str] = []

        if not context.client_id:
            return risk_score, threats

        # Get recent authentication attempts
        recent_events = audit_logger.get_audit_trail(
            client_id=context.client_id,
            hours=1,
            event_types={"auth_attempt", "auth_failure", "rate_limit_exceeded"},
        )

        # Analyze patterns
        auth_attempts = len(
            [e for e in recent_events if e.event_type == "auth_attempt"]
        )
        auth_failures = len(
            [e for e in recent_events if e.event_type == "auth_failure"]
        )
        rate_limit_hits = len(
            [e for e in recent_events if e.event_type == "rate_limit_exceeded"]
        )

        # High authentication attempt frequency
        if auth_attempts > 30:  # More than 30 attempts in 1 hour
            risk_score += 35
            threats.append("high_auth_attempt_frequency")
        elif auth_attempts > 15:
            risk_score += 20
            threats.append("elevated_auth_attempt_frequency")

        # High failure rate
        if auth_attempts > 0:
            failure_rate = auth_failures / auth_attempts
            if failure_rate > 0.5:  # More than 50% failures
                risk_score += 30
                threats.append("high_authentication_failure_rate")

        # Rate limiting violations
        if rate_limit_hits > 0:
            risk_score += 25
            threats.append("rate_limit_violations")

        return risk_score, threats

    def _get_historical_events(self, context: SecurityContext) -> list[Any]:
        """Get historical events for behavioral analysis."""
        if not context.client_id:
            return []

        return audit_logger.get_audit_trail(
            client_id=context.client_id,
            hours=24 * 7,  # Last week
            success_only=True,
        )

    def _analyze_time_based_patterns(
        self, historical_events: list[Any], context: SecurityContext
    ) -> tuple[int, list[str]]:
        """Analyze time-based patterns."""
        risk_score = 0
        threats: list[str] = []

        if len(historical_events) < 10:  # Not enough data
            return risk_score, threats

        request_hours = [event.timestamp.hour for event in historical_events]
        typical_hours = set(request_hours)

        current_hour = context.timestamp.hour
        if current_hour not in typical_hours:
            risk_score += 15
            threats.append("unusual_request_time")

        return risk_score, threats

    def _analyze_ip_patterns(
        self, historical_events: list[Any], context: SecurityContext
    ) -> tuple[int, list[str]]:
        """Analyze IP pattern anomalies."""
        risk_score = 0
        threats: list[str] = []

        if len(historical_events) < 10:  # Not enough data
            return risk_score, threats

        historical_ips = {
            event.ip_address for event in historical_events if event.ip_address
        }
        if (
            context.ip_address
            and context.ip_address not in historical_ips
            and historical_ips
        ):  # Only if we have historical data
            risk_score += 20
            threats.append("unusual_source_ip")

        return risk_score, threats

    def _analyze_activity_spikes(
        self, historical_events: list[Any]
    ) -> tuple[int, list[str]]:
        """Analyze unusual activity spikes."""
        risk_score = 0
        threats: list[str] = []

        if len(historical_events) < 10:  # Not enough data
            return risk_score, threats

        recent_events = [
            e
            for e in historical_events
            if e.timestamp > datetime.now(UTC) - timedelta(hours=2)
        ]

        if (
            len(recent_events) > len(historical_events) * 0.3
        ):  # 30% of total activity in 2 hours
            risk_score += 25
            threats.append("unusual_activity_spike")

        return risk_score, threats

    async def _analyze_behavioral_patterns(
        self, context: SecurityContext
    ) -> tuple[int, list[str]]:
        """Analyze behavioral patterns for anomaly detection."""
        risk_score = 0
        threats: list[str] = []

        if not context.client_id or not self.settings.enable_anomaly_detection:
            return risk_score, threats

        # Get historical behavior pattern
        historical_events = self._get_historical_events(context)
        if len(historical_events) < 10:  # Not enough data
            return risk_score, threats

        # Analyze time-based patterns
        time_risk, time_threats = self._analyze_time_based_patterns(
            historical_events, context
        )
        risk_score += time_risk
        threats.extend(time_threats)

        # Analyze IP patterns
        ip_risk, ip_threats = self._analyze_ip_patterns(historical_events, context)
        risk_score += ip_risk
        threats.extend(ip_threats)

        # Check for rapid pattern changes
        spike_risk, spike_threats = self._analyze_activity_spikes(historical_events)
        risk_score += spike_risk
        threats.extend(spike_threats)

        return risk_score, threats

    def _is_suspicious_ip_range(
        self, ip: ipaddress.IPv4Address | ipaddress.IPv6Address
    ) -> bool:
        """Check if IP is in known suspicious ranges."""
        # This is a simplified implementation
        # In production, this would integrate with threat intelligence feeds

        suspicious_ranges = [
            # Tor exit nodes, VPN providers, etc. would be here
            # This is just an example
            "10.0.0.0/8",  # Example: could be suspicious in certain contexts
        ]

        for range_str in suspicious_ranges:
            try:
                network = ipaddress.ip_network(range_str)
                if ip in network:
                    return True
            except ValueError:
                continue

        return False

    async def _check_ip_reputation(self, ip_address: str) -> tuple[int, list[str]]:
        """Check IP reputation using external services."""
        risk_score = 0
        threats = []

        # This would integrate with services like:
        # - VirusTotal
        # - AbuseIPDB
        # - Shodan
        # - Custom threat intelligence feeds

        # Placeholder implementation
        try:
            # In a real implementation, this would make API calls to reputation services
            # For now, just simulate the check
            await asyncio.sleep(0.01)  # Simulate API call

            # Example: if IP is in known bad lists
            # This would be replaced with actual API calls
            if self._is_known_malicious_ip(ip_address):
                risk_score += 50
                threats.append("known_malicious_ip")

        except Exception as e:
            logger.warning(f"IP reputation check failed: {e}")
            # Don't add risk for service failures

        return risk_score, threats

    def _is_known_malicious_ip(self, ip_address: str) -> bool:
        """Check against known malicious IP list (placeholder)."""
        # In production, this would check against:
        # - Local threat intelligence database
        # - Cached results from reputation services
        # - Internal blocklists
        return False


class SecurityMiddleware:
    """Comprehensive security middleware for MCP server."""

    def __init__(self, settings: SecuritySettings):
        self.settings = settings
        self.threat_detector = ThreatDetector(settings)
        self._request_counter = 0

        # Security caches
        self._blocked_ips: dict[str, datetime] = {}
        self._blocked_clients: dict[str, datetime] = {}
        self._rate_limits: dict[str, list[datetime]] = {}

        logger.info(
            "Security middleware initialized",
            extra={
                "rate_limiting": settings.enable_rate_limiting,
                "threat_detection": settings.enable_anomaly_detection,
                "ip_restrictions": bool(settings.allowed_ip_addresses),
            },
        )

    async def process_request(
        self, request_data: dict[str, Any], client_context: dict[str, Any] | None = None
    ) -> SecurityContext:
        """
        Process incoming request through security pipeline.

        Args:
            request_data: Request data
            client_context: Client context (IP, user agent, etc.)

        Returns:
            SecurityContext with security assessment

        Raises:
            SecurityError: If request is blocked by security policy
        """
        self._request_counter += 1

        # Create security context
        context = SecurityContext(
            request_id=f"req_{self._request_counter:08d}_{int(time.time())}",
            timestamp=datetime.now(UTC),
            ip_address=client_context.get("ip_address") if client_context else None,
            user_agent=client_context.get("user_agent") if client_context else None,
            client_id=client_context.get("client_id") if client_context else None,
        )

        # Security validation pipeline
        await self._validate_ip_restrictions(context)
        await self._check_blocked_entities(context)
        await self._enforce_rate_limits(context)

        # Threat detection
        if self.settings.enable_anomaly_detection:
            risk_score, threats = await self.threat_detector.analyze_request(context)
            context.risk_score = risk_score
            context.security_flags.update(threats)

            # Block high-risk requests
            if risk_score >= 80:
                await self._handle_high_risk_request(context)

        # Audit logging
        if self.settings.enable_audit_logging:
            audit_logger.log_authentication_event(
                event_type="request_processed",
                client_id=context.client_id or "unknown",
                success=True,
                ip_address=context.ip_address,
                user_agent=context.user_agent,
                details={
                    "request_id": context.request_id,
                    "risk_score": context.risk_score,
                    "security_flags": list(context.security_flags),
                },
                risk_score=context.risk_score,
            )

        return context

    async def _validate_ip_restrictions(self, context: SecurityContext) -> None:
        """Validate IP address restrictions."""
        if not context.ip_address or not self.settings.allowed_ip_addresses:
            return

        allowed_ips = self.settings.get_allowed_ips()
        if not allowed_ips:
            return

        try:
            client_ip = ipaddress.ip_address(context.ip_address)
            allowed = False

            for allowed_range in allowed_ips:
                try:
                    network = ipaddress.ip_network(allowed_range, strict=False)
                    if client_ip in network:
                        allowed = True
                        break
                except ValueError:
                    continue

            if not allowed:
                context.blocked_reason = (
                    f"IP {context.ip_address} not in allowed ranges"
                )
                context.security_flags.add("ip_not_allowed")

                # Log security event
                audit_logger.log_authentication_event(
                    event_type="ip_blocked",
                    client_id=context.client_id or "unknown",
                    success=False,
                    ip_address=context.ip_address,
                    details={"allowed_ranges": list(allowed_ips)},
                    risk_score=100,
                )

                raise SecurityError("Access denied: IP address not allowed")

        except ValueError as e:
            context.blocked_reason = f"Invalid IP address: {context.ip_address}"
            context.security_flags.add("invalid_ip_address")

            audit_logger.log_authentication_event(
                event_type="invalid_ip",
                client_id=context.client_id or "unknown",
                success=False,
                ip_address=context.ip_address,
                details={"error": str(e)},
                risk_score=50,
            )

            raise SecurityError("Access denied: Invalid IP address") from None

    async def _check_blocked_entities(self, context: SecurityContext) -> None:
        """Check if IP or client is blocked."""
        now = datetime.now(UTC)

        # Check blocked IPs
        if context.ip_address and context.ip_address in self._blocked_ips:
            blocked_until = self._blocked_ips[context.ip_address]
            if now < blocked_until:
                context.blocked_reason = "IP temporarily blocked"
                context.security_flags.add("ip_blocked")

                remaining = (blocked_until - now).total_seconds()
                raise SecurityError(f"IP blocked for {remaining:.0f} more seconds")
            else:
                # Unblock expired entries
                del self._blocked_ips[context.ip_address]

        # Check blocked clients
        if context.client_id and context.client_id in self._blocked_clients:
            blocked_until = self._blocked_clients[context.client_id]
            if now < blocked_until:
                context.blocked_reason = "Client temporarily blocked"
                context.security_flags.add("client_blocked")

                remaining = (blocked_until - now).total_seconds()
                raise SecurityError(f"Client blocked for {remaining:.0f} more seconds")
            else:
                # Unblock expired entries
                del self._blocked_clients[context.client_id]

    async def _enforce_rate_limits(self, context: SecurityContext) -> None:
        """Enforce rate limiting."""
        if not self.settings.enable_rate_limiting:
            return

        # Use IP address or client ID for rate limiting
        rate_limit_key = context.ip_address or context.client_id or "anonymous"
        if not rate_limit_key:
            return

        now = datetime.now(UTC)
        window_start = now - timedelta(
            minutes=self.settings.auth_rate_limit_window_minutes
        )

        # Clean old requests
        if rate_limit_key not in self._rate_limits:
            self._rate_limits[rate_limit_key] = []

        self._rate_limits[rate_limit_key] = [
            req_time
            for req_time in self._rate_limits[rate_limit_key]
            if req_time > window_start
        ]

        # Check rate limit
        request_count = len(self._rate_limits[rate_limit_key])
        if request_count >= self.settings.auth_rate_limit_requests:
            context.blocked_reason = "Rate limit exceeded"
            context.security_flags.add("rate_limited")

            # Log rate limit event
            audit_logger.log_authentication_event(
                event_type="rate_limit_exceeded",
                client_id=context.client_id or "unknown",
                success=False,
                ip_address=context.ip_address,
                details={
                    "requests_in_window": request_count,
                    "window_minutes": self.settings.auth_rate_limit_window_minutes,
                    "max_requests": self.settings.auth_rate_limit_requests,
                },
                risk_score=30,
            )

            # Temporary block for repeated violations
            if request_count > self.settings.auth_rate_limit_requests * 2:
                block_duration = timedelta(
                    minutes=self.settings.client_lockout_duration_minutes
                )
                if context.ip_address:
                    self._blocked_ips[context.ip_address] = now + block_duration
                if context.client_id:
                    self._blocked_clients[context.client_id] = now + block_duration

                logger.warning(
                    f"Temporarily blocked {rate_limit_key} "
                    + "for severe rate limit violation"
                )

            oldest_request = min(self._rate_limits[rate_limit_key])
            reset_time = oldest_request + timedelta(
                minutes=self.settings.auth_rate_limit_window_minutes
            )
            wait_time = (reset_time - now).total_seconds()

            raise SecurityError(
                f"Rate limit exceeded. Try again in {wait_time:.1f} seconds"
            )

        # Record this request
        self._rate_limits[rate_limit_key].append(now)

    async def _handle_high_risk_request(self, context: SecurityContext) -> None:
        """Handle high-risk requests."""
        logger.warning(
            "High-risk request detected",
            extra={
                "request_id": context.request_id,
                "risk_score": context.risk_score,
                "security_flags": list(context.security_flags),
                "ip_address": context.ip_address,
                "client_id": context.client_id,
            },
        )

        # Automatic incident response
        if self.settings.enable_automatic_incident_response:
            await self._trigger_incident_response(context)

        # Temporary block for very high-risk requests
        if context.risk_score >= 90:
            now = datetime.now(UTC)
            block_duration = timedelta(
                minutes=self.settings.client_lockout_duration_minutes * 2
            )

            if context.ip_address:
                self._blocked_ips[context.ip_address] = now + block_duration
            if context.client_id:
                self._blocked_clients[context.client_id] = now + block_duration

            context.blocked_reason = "High-risk request blocked"

            # Log security incident
            audit_logger.log_authentication_event(
                event_type="security_incident",
                client_id=context.client_id or "unknown",
                success=False,
                ip_address=context.ip_address,
                details={
                    "incident_type": "high_risk_request",
                    "risk_score": context.risk_score,
                    "security_flags": list(context.security_flags),
                    "auto_blocked": True,
                },
                risk_score=context.risk_score,
            )

            raise SecurityError("Request blocked due to security policy violation")

    async def _trigger_incident_response(self, context: SecurityContext) -> None:
        """Trigger incident response for security events."""
        incident_data = {
            "timestamp": context.timestamp.isoformat(),
            "request_id": context.request_id,
            "risk_score": context.risk_score,
            "security_flags": list(context.security_flags),
            "ip_address": context.ip_address,
            "client_id": context.client_id,
            "user_agent": context.user_agent,
        }

        # Send webhook notification
        if self.settings.security_notification_webhook:
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    await client.post(
                        self.settings.security_notification_webhook,
                        json={
                            "event_type": "security_incident",
                            "severity": "high"
                            if context.risk_score >= 90
                            else "medium",
                            "data": incident_data,
                        },
                    )
                logger.info("Security incident webhook notification sent")
            except Exception as e:
                logger.error(f"Failed to send security webhook: {e}")

        # Email notification would be implemented here
        if self.settings.security_notification_email:
            logger.info(
                "Security incident notification needed for "
                + str(self.settings.security_notification_email)
            )

    def get_security_status(self) -> dict[str, Any]:
        """Get current security status."""
        now = datetime.now(UTC)

        # Count active blocks
        active_ip_blocks = sum(
            1 for blocked_until in self._blocked_ips.values() if blocked_until > now
        )
        active_client_blocks = sum(
            1 for blocked_until in self._blocked_clients.values() if blocked_until > now
        )

        # Rate limit statistics
        rate_limit_stats = {}
        for key, requests in self._rate_limits.items():
            cutoff = now - timedelta(
                minutes=self.settings.auth_rate_limit_window_minutes
            )
            active_requests = [req for req in requests if req > cutoff]
            if active_requests:
                rate_limit_stats[hashlib.sha256(key.encode()).hexdigest()[:8]] = len(
                    active_requests
                )

        return {
            "middleware_active": True,
            "request_count": self._request_counter,
            "active_ip_blocks": active_ip_blocks,
            "active_client_blocks": active_client_blocks,
            "active_rate_limits": len(rate_limit_stats),
            "rate_limit_stats": rate_limit_stats,
            "security_features": {
                "rate_limiting": self.settings.enable_rate_limiting,
                "threat_detection": self.settings.enable_anomaly_detection,
                "audit_logging": self.settings.enable_audit_logging,
                "ip_restrictions": bool(self.settings.allowed_ip_addresses),
                "incident_response": self.settings.enable_automatic_incident_response,
            },
            "status_timestamp": now.isoformat(),
        }


def create_security_middleware(settings: SecuritySettings) -> SecurityMiddleware:
    """Create security middleware with provided settings."""
    return SecurityMiddleware(settings)
