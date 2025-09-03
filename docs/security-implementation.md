# OPERA Cloud MCP Security Implementation Guide

## Overview

This guide provides comprehensive documentation for the production-grade security enhancements implemented in the OPERA Cloud MCP server. The security system provides enterprise-level protection for sensitive hotel data and guest information with Oracle OPERA Cloud APIs.

## 🔒 Security Architecture

### Core Security Components

1. **SecureOAuthHandler** - Enhanced OAuth2 implementation with token binding and security monitoring
1. **SecurityMiddleware** - Request validation, rate limiting, and threat detection
1. **AuditLogger** - Tamper-resistant audit logging with encryption
1. **SecurityMonitor** - Real-time threat detection and anomaly analysis
1. **SecureTokenCache** - Encrypted token storage with integrity protection

### Security Features

- ✅ **Token Binding** - Prevents token theft and misuse
- ✅ **Rate Limiting** - Protects against brute force attacks
- ✅ **Audit Logging** - Comprehensive security event tracking
- ✅ **Threat Detection** - Behavioral anomaly analysis
- ✅ **IP Restrictions** - Network-level access control
- ✅ **Credential Rotation** - Secure credential management
- ✅ **Incident Response** - Automated security alerts

## 🚀 Quick Start

### 1. Basic Security Configuration

```bash
# Copy security configuration template
cp .env.example .env

# Enable core security features
OPERA_SECURITY_ENABLE_SECURITY_MONITORING=true
OPERA_SECURITY_ENABLE_AUDIT_LOGGING=true
OPERA_SECURITY_ENABLE_RATE_LIMITING=true
OPERA_SECURITY_ENABLE_TOKEN_BINDING=true
```

### 2. Generate Encryption Keys

```python
import base64
import secrets

# Generate 32-byte encryption key
encryption_key = base64.b64encode(secrets.token_bytes(32)).decode()
print(f"OPERA_SECURITY_AUDIT_DB_ENCRYPTION_KEY={encryption_key}")
```

### 3. Initialize Secure OAuth Handler

```python
from opera_cloud_mcp.auth import create_oauth_handler
from opera_cloud_mcp.config.security_settings import SecuritySettings

# Create security settings
security_settings = SecuritySettings()

# Create secure OAuth handler
oauth_handler = create_oauth_handler(
    settings=app_settings,
    enable_security_features=True,
    allowed_ips=security_settings.get_allowed_ips(),
)
```

## 🔧 Configuration Reference

### Environment Variables

#### Core Security Features

```bash
# Essential security controls
OPERA_SECURITY_ENABLE_SECURITY_MONITORING=true
OPERA_SECURITY_ENABLE_AUDIT_LOGGING=true
OPERA_SECURITY_ENABLE_RATE_LIMITING=true
OPERA_SECURITY_ENABLE_TOKEN_BINDING=true
```

#### Rate Limiting

```bash
# Requests per time window
OPERA_SECURITY_AUTH_RATE_LIMIT_REQUESTS=10
OPERA_SECURITY_AUTH_RATE_LIMIT_WINDOW_MINUTES=5

# Client blocking after failures
OPERA_SECURITY_MAX_FAILED_ATTEMPTS=5
OPERA_SECURITY_CLIENT_LOCKOUT_DURATION_MINUTES=15
```

#### Token Security

```bash
# Token lifetime and refresh
OPERA_SECURITY_TOKEN_MAX_LIFETIME_HOURS=24
OPERA_SECURITY_TOKEN_REFRESH_THRESHOLD_MINUTES=5
OPERA_SECURITY_TOKEN_BINDING_LIFETIME_HOURS=24
```

#### Network Security

```bash
# IP address restrictions (CIDR notation)
OPERA_SECURITY_ALLOWED_IP_ADDRESSES=192.168.1.0/24,10.0.0.0/8
OPERA_SECURITY_REQUIRE_HTTPS=true
OPERA_SECURITY_MIN_TLS_VERSION=1.2
```

#### Audit Database

```bash
# Encrypted audit storage
OPERA_SECURITY_AUDIT_DB_ENCRYPTION_KEY=your_base64_key_here
OPERA_SECURITY_SECURITY_EVENT_RETENTION_DAYS=90
OPERA_SECURITY_AUDIT_DB_MAX_SIZE_MB=1024
```

#### Threat Detection

```bash
# Behavioral analysis
OPERA_SECURITY_ENABLE_ANOMALY_DETECTION=true
OPERA_SECURITY_ANOMALY_DETECTION_SENSITIVITY=0.7
OPERA_SECURITY_ENABLE_IP_REPUTATION_CHECK=false
```

#### Incident Response

```bash
# Security notifications
OPERA_SECURITY_ENABLE_AUTOMATIC_INCIDENT_RESPONSE=true
OPERA_SECURITY_SECURITY_NOTIFICATION_WEBHOOK=https://hooks.slack.com/your-webhook
OPERA_SECURITY_SECURITY_NOTIFICATION_EMAIL=security@yourcompany.com
```

## 🏭 Production Deployment

### 1. Security Validation

```python
from opera_cloud_mcp.auth import validate_security_configuration
from opera_cloud_mcp.config.security_settings import ProductionSecuritySettings

# Validate configuration for production
security_settings = ProductionSecuritySettings()
validation = validate_security_configuration(app_settings, security_settings)

if not validation["valid"]:
    print("❌ Security validation failed:")
    for error in validation["errors"]:
        print(f"  - {error}")
    exit(1)

if validation["warnings"]:
    print("⚠️ Security warnings:")
    for warning in validation["warnings"]:
        print(f"  - {warning}")
```

### 2. Production Security Checklist

- [ ] **Encryption Keys Generated** - All encryption keys are cryptographically secure
- [ ] **IP Restrictions Configured** - Only authorized networks can access
- [ ] **HTTPS Enforced** - All communications use TLS 1.2+
- [ ] **Rate Limiting Enabled** - Protection against brute force attacks
- [ ] **Audit Logging Active** - All security events are logged
- [ ] **Incident Response Setup** - Security alerts configured
- [ ] **Credential Rotation Planned** - Regular credential updates scheduled
- [ ] **Testing Mode Disabled** - No debug or testing features enabled

### 3. Security Monitoring Setup

```python
# Enable comprehensive security monitoring
security_middleware, audit_logger, security_monitor = create_security_components(
    security_settings=ProductionSecuritySettings(),
    audit_db_path=Path("/var/log/opera-mcp/audit.db"),
    audit_encryption_key=your_encryption_key,
)

# Get security status
status = security_middleware.get_security_status()
print(f"Security Status: {status}")
```

## 🔍 Security Monitoring

### Real-Time Monitoring

```python
# Get current security status
oauth_handler = create_oauth_handler(settings, enable_security_features=True)
security_status = oauth_handler.get_security_status()

print(f"Risk Level: {security_status['risk_assessment']['risk_level']}")
print(f"Recent Events: {security_status['recent_events_24h']}")
print(f"Failed Attempts: {security_status['recent_failures']}")
```

### Audit Trail Analysis

```python
from opera_cloud_mcp.auth.audit_logger import audit_logger

# Get recent security events
events = audit_logger.get_audit_trail(
    hours=24, event_types={"auth_failure", "security_incident"}
)

# Generate security report
report = audit_logger.get_security_report(hours=24)
print(f"Threat Level: {report['threat_level']}")
print(f"Failure Rate: {report['failure_rate_percent']:.1f}%")
```

### Health Checks

```python
# Comprehensive health check with security status
@app.tool()
async def security_health_check():
    """Enhanced health check with security metrics."""

    # Basic health
    health = await health_check()

    # Security metrics
    security_status = oauth_handler.get_security_status()
    audit_stats = audit_logger.get_security_report(hours=1)

    health["security"] = {
        "monitoring_active": security_status["security_monitoring"],
        "threat_level": audit_stats["threat_level"],
        "recent_incidents": audit_stats["high_risk_events"],
        "authentication_health": security_status["risk_assessment"]["risk_level"],
    }

    return health
```

## 🛡️ Security Best Practices

### 1. Credential Management

```python
# Secure credential rotation
async def rotate_credentials():
    """Rotate OAuth credentials securely."""

    new_secret = generate_secure_secret()  # Your secure secret generation

    success = await oauth_handler.rotate_credentials(
        new_client_secret=new_secret, validate_new_credentials=True
    )

    if success:
        # Update configuration
        update_environment_variable("OPERA_CLIENT_SECRET", new_secret)
        logger.info("Credentials rotated successfully")
    else:
        logger.error("Credential rotation failed")
        # Implement your rollback strategy
```

### 2. Incident Response

```python
# Custom security incident handler
async def handle_security_incident(context, threat_level):
    """Handle security incidents based on threat level."""

    if threat_level == "high":
        # Block source immediately
        await security_middleware.block_client(context.client_id, hours=24)

        # Send immediate alert
        await send_security_alert(
            "CRITICAL",
            {
                "threat_level": threat_level,
                "client_id": context.client_id,
                "ip_address": context.ip_address,
                "timestamp": context.timestamp.isoformat(),
            },
        )

    elif threat_level == "medium":
        # Increase monitoring
        await security_monitor.increase_monitoring(context.client_id)

        # Log for review
        logger.warning(f"Medium threat detected: {context.security_flags}")
```

### 3. Compliance Features

```python
# Enable GDPR compliance mode
security_settings = SecuritySettings(
    enable_gdpr_mode=True, enable_pii_anonymization=True, data_retention_policy_days=365
)

# Automatic PII anonymization in logs
# IP addresses and user agents are automatically hashed
# Personal data is encrypted in audit logs
```

## 🔧 Advanced Configuration

### Custom Threat Detection

```python
class CustomThreatDetector(ThreatDetector):
    """Custom threat detection with business logic."""

    async def analyze_hotel_specific_threats(self, context, hotel_id):
        """Analyze threats specific to hotel operations."""
        risk_score = 0
        threats = []

        # Check for unusual booking patterns
        if await self.detect_unusual_booking_activity(context, hotel_id):
            risk_score += 30
            threats.append("unusual_booking_pattern")

        # Check for rate manipulation attempts
        if await self.detect_rate_manipulation(context):
            risk_score += 50
            threats.append("rate_manipulation_attempt")

        return risk_score, threats
```

### Custom Audit Events

```python
# Log custom business events
audit_logger.log_authentication_event(
    event_type="reservation_access",
    client_id=client_id,
    success=True,
    ip_address=request.remote_addr,
    details={
        "reservation_id": reservation_id,
        "hotel_id": hotel_id,
        "access_type": "read",
        "guest_data_accessed": True,
    },
    risk_score=0,
)
```

## 🚨 Troubleshooting

### Common Issues

#### 1. High False Positive Rate

```python
# Adjust anomaly detection sensitivity
OPERA_SECURITY_ANOMALY_DETECTION_SENSITIVITY = 0.5  # Lower = less sensitive

# Whitelist known good IPs
OPERA_SECURITY_ALLOWED_IP_ADDRESSES = your_trusted_networks

# Review and tune threat detection rules
```

#### 2. Rate Limiting Too Restrictive

```python
# Increase rate limits for production load
OPERA_SECURITY_AUTH_RATE_LIMIT_REQUESTS = 25
OPERA_SECURITY_AUTH_RATE_LIMIT_WINDOW_MINUTES = 5

# Or implement tiered rate limiting based on client type
```

#### 3. Audit Database Growth

```python
# Configure automatic cleanup
OPERA_SECURITY_SECURITY_EVENT_RETENTION_DAYS = 30
OPERA_SECURITY_AUDIT_DB_MAX_SIZE_MB = 2048

# Manual cleanup
from opera_cloud_mcp.auth.audit_logger import audit_logger

deleted_count = audit_logger.database.cleanup_old_records(days=90)
```

### Debugging

```python
# Enable security debug logging
OPERA_SECURITY_ENABLE_SECURITY_DEBUG_LOGS = true

# Monitor security events in real-time
import logging

logging.getLogger("opera_cloud_mcp.auth").setLevel(logging.DEBUG)
```

### Performance Tuning

```python
# Optimize for high-volume environments
security_settings = SecuritySettings(
    # Reduce database writes
    enable_audit_logging=True,
    audit_db_max_size_mb=5120,
    # Optimize rate limiting
    auth_rate_limit_requests=50,
    auth_rate_limit_window_minutes=1,
    # Tune threat detection
    enable_anomaly_detection=True,
    anomaly_detection_sensitivity=0.8,  # Reduce false positives
)
```

## 📊 Security Metrics

### Key Performance Indicators

- **Authentication Success Rate** - Target: >99%
- **Average Response Time** - Target: \<500ms
- **False Positive Rate** - Target: \<2%
- **Mean Time to Detection** - Target: \<1 minute
- **Mean Time to Response** - Target: \<5 minutes

### Monitoring Queries

```python
# Daily security metrics
metrics = audit_logger.get_security_report(hours=24)

print(f"Success Rate: {metrics['success_rate']:.1f}%")
print(f"Threat Level: {metrics['threat_level']}")
print(f"High-Risk Events: {metrics['high_risk_events']}")
print(f"Unique Clients: {metrics['unique_clients']}")
```

## 🔒 Security Compliance

### Standards Supported

- **OAuth 2.1** - Latest OAuth security standards
- **GDPR** - EU privacy regulation compliance
- **PCI DSS** - Payment card data protection (Level 4)
- **SOC 2 Type II** - Security and availability controls
- **ISO 27001** - Information security management

### Compliance Features

- Encrypted data at rest and in transit
- Comprehensive audit trails
- Data retention controls
- Privacy by design principles
- Incident response procedures

## 🆘 Support

### Security Issues

For security vulnerabilities or concerns:

- Email: security@yourcompany.com
- Encrypted communication preferred
- Include detailed reproduction steps
- Expected response time: 24 hours

### Documentation Updates

This security implementation represents enterprise-grade protection for Oracle OPERA Cloud integration. Regular security reviews and updates are recommended to maintain the highest security standards.

______________________________________________________________________

**Last Updated:** January 2025
**Version:** 1.0.0
**Security Review Date:** January 2025
