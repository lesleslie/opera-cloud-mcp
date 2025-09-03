# Production Deployment and Monitoring Guide

This guide provides instructions for deploying and monitoring the OPERA Cloud MCP server in production environments.

## Deployment Architecture

### System Requirements

- **Python Version**: 3.11 or higher
- **Memory**: Minimum 2GB RAM (4GB recommended)
- **CPU**: 2 cores minimum (4 cores recommended)
- **Storage**: 10GB available disk space
- **Network**: Outbound HTTPS access to OPERA Cloud APIs

### Deployment Options

#### Docker Deployment (Recommended)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen

# Copy application code
COPY . .

# Expose port (if using HTTP transport)
EXPOSE 8000

# Run the application
CMD ["uv", "run", "python", "-m", "opera_cloud_mcp.main"]
```

#### Direct Deployment

```bash
# Clone the repository
git clone <repository-url>
cd opera-cloud-mcp

# Install dependencies
pip install uv
uv sync --frozen

# Set environment variables
export OPERA_CLIENT_ID="your_client_id"
export OPERA_CLIENT_SECRET="your_client_secret"
export OPERA_DEFAULT_HOTEL_ID="your_hotel_id"

# Run the application
uv run python -m opera_cloud_mcp.main
```

## Environment Configuration

### Required Environment Variables

```bash
# OAuth Configuration
OPERA_CLIENT_ID=your_client_id
OPERA_CLIENT_SECRET=your_client_secret
OPERA_TOKEN_URL=https://api.oracle-hospitality.com/oauth/v1/tokens

# API Configuration
OPERA_BASE_URL=https://api.oracle-hospitality.com
OPERA_API_VERSION=v1
OPERA_ENVIRONMENT=production

# Default Configuration
OPERA_DEFAULT_HOTEL_ID=HOTEL123

# Performance Settings
OPERA_REQUEST_TIMEOUT=30
OPERA_MAX_RETRIES=3
OPERA_ENABLE_CACHE=true
OPERA_CACHE_TTL=300
```

### Optional Environment Variables

```bash
# Logging Configuration
OPERA_LOG_LEVEL=INFO
OPERA_ENABLE_STRUCTURED_LOGGING=true

# Security Configuration
OPERA_ENABLE_PERSISTENT_TOKEN_CACHE=true
OPERA_TOKEN_CACHE_DIR=/var/lib/opera-cloud-mcp/cache

# Caching Configuration
OPERA_CACHE_MAX_MEMORY=10000

# Rate Limiting
OPERA_REQUESTS_PER_SECOND=10
OPERA_BURST_CAPACITY=20
```

## Monitoring and Observability

### Health Check Endpoints

The OPERA Cloud MCP server provides several health check endpoints:

#### Tool-based Health Check

```bash
# Call the health_check tool through MCP protocol
# This provides detailed internal system status
```

#### Resource-based Health Check

```bash
# Access the health status resource
# URI: health://status
# Provides comprehensive health information
```

#### Readiness Check

```bash
# Access the readiness check resource
# URI: health://ready
# Indicates if the service is ready to serve requests
```

#### Liveness Check

```bash
# Access the liveness check resource
# URI: health://live
# Indicates if the service process is alive
```

### Metrics Collection

The server collects and exposes various metrics:

#### Performance Metrics

- **Request Counters**: Total requests, successful requests, failed requests
- **Response Times**: Average, median, 95th percentile, 99th percentile
- **Throughput**: Requests per second
- **Error Rates**: Overall error rate, error rate by type

#### Resource Metrics

- **Memory Usage**: Current memory consumption
- **CPU Usage**: CPU utilization
- **Connection Pool**: Active connections, available connections
- **Cache Performance**: Hit rate, miss rate, eviction count

#### Business Metrics

- **API Usage**: Calls by endpoint
- **Authentication**: Token refresh count, authentication success/failure
- **Hotel Operations**: Reservation operations, guest operations

### Structured Logging

The server uses structured JSON logging for better observability:

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "INFO",
  "logger": "opera_cloud_mcp.clients.base_client",
  "message": "API Request: GET /reservations",
  "method": "GET",
  "url": "https://api.oracle-hospitality.com/v1/reservations",
  "hotel_id": "HOTEL123",
  "request_size_bytes": 0,
  "params": {
    "limit": 10
  }
}
```

### Distributed Tracing

The server supports distributed tracing for request correlation:

- **Trace IDs**: Unique identifiers for request flows
- **Span Tracking**: Individual operation timing
- **Service Correlation**: Cross-service request tracking
- **Error Propagation**: Error context propagation

## Performance Tuning

### Connection Pooling

The server uses HTTP connection pooling for optimal performance:

```python
# Default connection pool settings
httpx.Limits(
    max_connections=50,  # Maximum total connections
    max_keepalive_connections=20,  # Keep-alive connections
    keepalive_expiry=30.0,  # Keep-alive timeout
)
```

### Caching Strategy

The server implements intelligent caching:

- **Multi-layer Caching**: Memory and persistent storage
- **TTL-based Invalidation**: Time-based cache expiration
- **Dependency-based Invalidation**: Cache invalidation based on dependencies
- **Size Limits**: Memory usage controls

### Rate Limiting

Built-in rate limiting protects against API abuse:

```python
# Rate limiting configuration
RateLimiter(
    requests_per_second=10.0,  # Maximum requests per second
    burst_capacity=20,  # Burst capacity
)
```

## Security Monitoring

### Authentication Monitoring

- **Token Refresh Tracking**: Monitor token refresh frequency
- **Authentication Failures**: Track failed authentication attempts
- **Credential Rotation**: Monitor credential changes

### Security Events

- **Rate Limit Violations**: Track rate limit exceedances
- **Suspicious Activity**: Detect unusual access patterns
- **Security Violations**: Monitor policy violations

## Alerting and Notifications

### Critical Alerts

- **Service Unavailability**: Server down or unresponsive
- **Authentication Failures**: OAuth token issues
- **High Error Rates**: Error rates exceeding thresholds
- **Performance Degradation**: Response times exceeding SLAs

### Warning Alerts

- **High Memory Usage**: Memory consumption approaching limits
- **Cache Miss Rates**: High cache miss rates indicating performance issues
- **Rate Limiting**: Frequent rate limit triggers
- **Slow Response Times**: Response times trending upward

## Backup and Recovery

### Token Cache Backup

The server persists OAuth tokens for recovery:

```bash
# Token cache location
/var/lib/opera-cloud-mcp/cache/

# Backup strategy
# Regular backup of cache directory
```

### Configuration Backup

```bash
# Backup environment variables
# Store in secure configuration management system
```

## Troubleshooting

### Common Issues

#### Authentication Failures

```bash
# Check logs for authentication errors
# Verify OAuth credentials
# Check token URL connectivity
```

#### Performance Issues

```bash
# Check response time metrics
# Monitor connection pool usage
# Review cache hit rates
```

#### Rate Limiting

```bash
# Check rate limit metrics
# Review request patterns
# Adjust rate limiting configuration
```

### Diagnostic Commands

```bash
# Check service health
curl http://localhost:8000/health

# Check logs
journalctl -u opera-cloud-mcp -f

# Check resource usage
htop
```

## Scaling Considerations

### Horizontal Scaling

For high-traffic environments, consider horizontal scaling:

- **Load Balancer**: Distribute requests across multiple instances
- **Shared Cache**: Use distributed cache for consistency
- **Database Scaling**: Scale audit logging database

### Vertical Scaling

For increased capacity per instance:

- **More Memory**: Increase RAM allocation
- **More CPU**: Add CPU cores
- **Faster Storage**: Use SSD storage

## Maintenance

### Regular Maintenance Tasks

- **Log Rotation**: Implement log rotation policies
- **Cache Cleanup**: Periodic cache cleanup
- **Security Updates**: Regular security patching
- **Performance Reviews**: Periodic performance analysis

### Monitoring Maintenance

- **Alert Tuning**: Adjust alert thresholds based on historical data
- **Dashboard Updates**: Update monitoring dashboards
- **Report Generation**: Generate regular performance reports

This guide provides a comprehensive overview of deploying and monitoring the OPERA Cloud MCP server in production environments. Regular review and updates to monitoring configurations will ensure optimal performance and reliability.
