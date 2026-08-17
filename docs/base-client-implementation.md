# BaseAPIClient Implementation Summary

## Overview

This document summarizes the complete implementation of the production-ready BaseAPIClient infrastructure for the OPERA Cloud MCP server. The implementation provides a comprehensive, enterprise-grade HTTP client foundation for all OPERA Cloud API integrations.

## 🚀 Key Features Implemented

### 1. **Advanced Authentication Integration**

- Full OAuth2Handler integration with token caching and refresh
- Automatic token invalidation and retry on authentication failures
- Persistent encrypted token caching for improved performance
- Comprehensive token lifecycle management

### 2. **Production-Grade HTTP Client**

- **Connection Pooling**: Optimized with 50 max connections and 20 keep-alive connections
- **HTTP/2 Support**: Enabled for better performance
- **Custom Timeouts**: Granular timeout control (connect, read, write, pool)
- **SSL Verification**: Enforced for security
- **Compression**: Automatic gzip/deflate support

### 3. **Comprehensive Rate Limiting**

- **Token Bucket Algorithm**: Configurable requests per second with burst capacity
- **Automatic Throttling**: Smart wait logic when limits are exceeded
- **Request History Tracking**: Detailed analytics and monitoring
- **Configurable Limits**: Default 10 RPS with 20-request burst capacity

### 4. **Advanced Retry Logic**

- **Exponential Backoff**: Smart retry timing with configurable backoff multiplier
- **Jitter Support**: Prevents thundering herd problems
- **Selective Retries**: Different strategies for different error types
- **Authentication Retry**: Special handling for token expiry scenarios

```mermaid
flowchart TD
    Start([Tool Request Received]) --> Validate[Validate Input Parameters]

    Validate -->|Invalid| Error1([Return ValidationError])
    Validate -->|Valid| GetToken[Get OAuth2 Token]

    GetToken --> CheckRateLimit{Check Rate Limiter}

    CheckRateLimit -->|Limit exceeded| Wait[Wait for token refill]
    Wait --> CheckRateLimit

    CheckRateLimit -->|Under limit| CheckCircuit{Check Circuit Breaker}

    CheckCircuit -->|Circuit OPEN| Error2([Return Service Unavailable])
    CheckCircuit -->|Circuit CLOSED| MakeRequest[Make HTTP Request]

    MakeRequest --> Response{HTTP Response}

    Response -->|Success 2xx| Transform[Transform Response]
    Response -->|Client Error 4xx| ClassifyClient{Classify Error}
    Response -->|Server Error 5xx| ClassifyServer{Classify Error}

    Transform --> UpdateMetrics[Update Metrics]
    UpdateMetrics --> ResetCircuit[Reset Circuit Breaker]
    ResetCircuit --> Return1([Return Success])

    ClassifyClient -->|401 Unauthorized| Refresh[Refresh Token]
    ClassifyClient -->|Other 4xx| ErrorClient[Log Error]
    Refresh --> GetToken

    ClassifyServer -->|Retryable| CheckRetries{Retry Count<br/>< Max?}
    ClassifyServer -->|Non-retryable| ErrorServer[Log Error]

    ErrorClient --> Error3([Return Error])
    ErrorServer --> Error3

    CheckRetries -->|Yes| Error4([Return Max Retries Exceeded])
    CheckRetries -->|No| CalculateBackoff[Calculate Exponential Backoff]

    CalculateBackoff --> Jitter[Add Random Jitter]
    Jitter --> WaitRetry[Wait Backoff + Jitter]
    WaitRetry --> MakeRequest

    UpdateMetrics --> RecordSuccess[Record Success Metrics]
    RecordSuccess --> Return1

    subgraph "Circuit Breaker Logic"
        CheckCircuit
        ResetCircuit
        IncrementFail[Increment Failure Count]
    end

    Response -->|Failure| IncrementFail
    IncrementFail --> CheckThreshold{Failure Count<br/>> Threshold?}

    CheckThreshold -->|Yes| TripCircuit[Trip Circuit to OPEN]
    CheckThreshold -->|No| RecordFailure[Record Failure]

    TripCircuit --> Error5([Return Circuit Open])
    RecordFailure --> CheckRetries

    style Error1 fill:#E74C3C,stroke:#922B21,color:#fff
    style Error2 fill:#E74C3C,stroke:#922B21,color:#fff
    style Error3 fill:#E74C3C,stroke:#922B21,color:#fff
    style Error4 fill:#E74C3C,stroke:#922B21,color:#fff
    style Error5 fill:#E74C3C,stroke:#922B21,color:#fff
    style Return1 fill:#2ECC71,stroke:#1E8449,color:#fff
    style TripCircuit fill:#F39C12,stroke:#B9770E,color:#fff
    style CheckCircuit fill:#9B59B6,stroke:#6C3483,color:#fff
```

This flowchart illustrates the complete request processing flow, including input validation, rate limiting, circuit breaking, error classification, retry logic with exponential backoff and jitter, and circuit breaker integration.

### 5. **Comprehensive Error Handling**

- **Custom Exception Hierarchy**: 10+ specialized exception types
- **Detailed Error Context**: Rich error information with debugging details
- **HTTP Status Code Mapping**: Intelligent error classification
- **Retryability Analysis**: Built-in logic for determining retry eligibility

### 6. **Request/Response Monitoring**

- **Detailed Logging**: Structured logging for all requests and responses
- **Performance Metrics**: Duration, size, and retry tracking
- **Health Monitoring**: Real-time health status and error rate tracking
- **Sensitive Data Masking**: Automatic PII protection in logs

### 7. **Data Transformation Pipeline**

- **Request Sanitization**: Automatic removal of null/empty values
- **Response Transformation**: Configurable field-level data transformations
- **Nested Field Support**: Deep transformation with dot notation paths
- **Error-Tolerant Processing**: Graceful handling of transformation failures

### 8. **Health Monitoring & Metrics**

- **Real-time Health Status**: Comprehensive health checks with status classification
- **Performance Analytics**: Request timing, error rates, and endpoint statistics
- **Top Endpoints Tracking**: Most-used API endpoints analysis
- **Error Breakdown**: Detailed error type and frequency analysis

### 9. **Circuit Breaker Pattern**

- **Failure Threshold Management**: Configurable failure limits
- **State Management**: Closed/Open/Half-open state transitions
- **Recovery Timeout**: Automatic recovery attempt scheduling
- **Service Protection**: Prevents cascade failures

```mermaid
stateDiagram-v2
    [*] --> Closed: Initialize

    Closed --> Closed: Request succeeds<br/>(Reset failure count)

    Closed --> Open: Failure threshold<br/>exceeded (default: 5)

    note right of Closed
        Normal operation
        • All requests pass through
        • Track failure count
        • Reset on success
    end note

    Open --> Half-Open: Recovery timeout<br/>expires (default: 60s)

    note right of Open
        Circuit tripped
        • Block all requests
        • Prevent cascade failures
        • Allow recovery timeout
    end note

    Half-Open --> Closed: Test request<br/>succeeds

    Half-Open --> Open: Test request<br/>fails

    note right of Half-Open
        Testing recovery
        • Allow one test request
        • Verify service health
        • Transition based on result
    end note

    Closed: Active state
    Open: Tripped state
    Half-Open: Testing state
```

This state diagram illustrates the three circuit breaker states (Closed, Open, Half-Open) and the conditions that trigger transitions between them, protecting against cascade failures.

### 10. **Enhanced Session Management**

- **Async Context Management**: Proper resource cleanup
- **Thread-Safe Initialization**: Double-check locking pattern
- **Graceful Shutdown**: Comprehensive resource cleanup
- **Session Lifecycle Logging**: Detailed session state tracking

## 📊 Architecture Diagram

### BaseAPIClient Architecture

```mermaid
graph TB
    subgraph "MCP Tools Layer"
        Tools["53 MCP Tools<br/>(reservations, guests, rooms,<br/>operations, financial)"]
    end

    subgraph "API Clients Layer"
        ReservationClient["ReservationClient"]
        GuestClient["GuestClient"]
        RoomClient["RoomClient"]
        OperationClient["OperationClient"]
        FinancialClient["FinancialClient"]
    end

    subgraph "BaseAPIClient Core"
        Base["BaseAPIClient"]

        subgraph "Core Components"
            RateLimiter["RateLimiter<br/>• Token Bucket Algorithm<br/>• 10 RPS + 20 burst<br/>• Automatic throttling"]
            HealthMonitor["HealthMonitor<br/>• Request tracking<br/>• Performance analytics<br/>• Real-time status"]
            DataTransformer["DataTransformer<br/>• Request sanitization<br/>• Response transformation<br/>• Nested field support"]
            CircuitBreaker["CircuitBreaker<br/>• Failure threshold mgmt<br/>• State transitions<br/>• Service protection"]
            RequestMetrics["RequestMetrics<br/>• Duration tracking<br/>• Size metrics<br/>• Retry counting"]
        end
    end

    subgraph "Authentication Layer"
        OAuth["OAuth2Handler<br/>• Token caching<br/>• Auto refresh<br/>• Encrypted storage"]
    end

    subgraph "External Services"
        OPERA["OPERA Cloud API<br/>• REST Architecture<br/>• OAuth2 Auth<br/>• Rate Limited"]
    end

    Tools --> ReservationClient
    Tools --> GuestClient
    Tools --> RoomClient
    Tools --> OperationClient
    Tools --> FinancialClient

    ReservationClient --> Base
    GuestClient --> Base
    RoomClient --> Base
    OperationClient --> Base
    FinancialClient --> Base

    Base --> RateLimiter
    Base --> HealthMonitor
    Base --> DataTransformer
    Base --> CircuitBreaker
    Base --> RequestMetrics
    Base --> OAuth

    Base --> OPERA

    CircuitBreaker -.->|Prevents cascade<br/>failures| OPERA
    RateLimiter -.->|Throttles requests| OPERA
    OAuth -.->|Authenticates| OPERA

    style Base fill:#4A90E2,stroke:#1E3A5F,stroke-width:3px,color:#fff
    style CircuitBreaker fill:#E74C3C,stroke:#922B21,color:#fff
    style RateLimiter fill:#F39C12,stroke:#B9770E,color:#fff
    style HealthMonitor fill:#2ECC71,stroke:#1E8449,color:#fff
    style OAuth fill:#9B59B6,stroke:#6C3483,color:#fff
    style OPERA fill:#34495E,stroke:#1A252F,color:#fff
```

This diagram illustrates how the 45+ MCP tools interact with the API client layer, which in turn uses the BaseAPIClient with its core components (RateLimiter, HealthMonitor, DataTransformer, CircuitBreaker, RequestMetrics) to communicate with the OPERA Cloud API through OAuth2 authentication.

## 📁 File Structure

```
opera_cloud_mcp/
├── clients/
│   └── base_client.py          # Complete BaseAPIClient implementation
├── utils/
│   └── exceptions.py           # Enhanced exception hierarchy
├── auth/
│   └── oauth_handler.py        # OAuth2 integration (existing)
├── config/
│   └── settings.py             # Configuration management (existing)
└── examples/
    └── base_client_usage.py    # Comprehensive usage example
```

## 🔧 Core Components

### BaseAPIClient Class

```python
class BaseAPIClient:
    """Production-ready base client for all OPERA Cloud API clients."""

    # Key methods:
    -request()  # Main request method with all features
    -get / post / put / delete / patch / head / options()  # HTTP method wrappers
    -health_check()  # Comprehensive health assessment
    -get_health_status()  # Real-time status information
    -close()  # Resource cleanup
```

### Supporting Classes

- **RateLimiter**: Token bucket rate limiting with burst support
- **HealthMonitor**: Request tracking and health analysis
- **DataTransformer**: Request/response data processing utilities
- **CircuitBreaker**: Service resilience and failure protection
- **RequestMetrics**: Structured metrics collection

### API Request Lifecycle

```mermaid
sequenceDiagram
    participant Client as MCP Client
    participant Tool as MCP Tool
    participant APIClient as API Client
    participant RateLimiter as Rate Limiter
    participant CircuitBreaker as Circuit Breaker
    participant BaseClient as BaseAPIClient
    participant OAuth as OAuth2 Handler
    participant OPERA as OPERA Cloud API

    Client->>Tool: Invoke tool (e.g., search_reservations)
    activate Tool
    Tool->>APIClient: Call API method
    activate APIClient

    APIClient->>RateLimiter: Check rate limit
    activate RateLimiter

    alt Rate limit exceeded
        RateLimiter-->>APIClient: Throttled (wait required)
        APIClient->>APIClient: Calculate wait time
        RateLimiter->>RateLimiter: Wait for token refill
        RateLimiter-->>APIClient: Proceed
    end

    deactivate RateLimiter

    APIClient->>CircuitBreaker: Check circuit state
    activate CircuitBreaker

    alt Circuit is OPEN
        CircuitBreaker-->>APIClient: CircuitOpenException
        APIClient-->>Tool: Error: Service temporarily unavailable
    else Circuit is CLOSED/HALF-OPEN
        CircuitBreaker-->>APIClient: Allow request
    end

    deactivate CircuitBreaker

    APIClient->>BaseClient: Make HTTP request
    activate BaseClient

    BaseClient->>OAuth: Get access token
    activate OAuth
    OAuth-->>BaseClient: Bearer token
    deactivate OAuth

    BaseClient->>OPERA: GET /api/v1/reservations
    Note over BaseClient,OPERA: Authorization: Bearer {token}
    activate OPERA

    alt Success Response (200-299)
        OPERA-->>BaseClient: 200 OK + JSON data
        BaseClient->>CircuitBreaker: Record success
        CircuitBreaker->>CircuitBreaker: Reset failure count
        BaseClient->>RateLimiter: Record success
        BaseClient->>BaseClient: Transform response
        BaseClient-->>APIClient: Response(data, success=True)
    else Client Error (400-499)
        OPERA-->>BaseClient: 400/404/401 etc.
        BaseClient->>BaseClient: Classify error
        BaseClient->>CircuitBreaker: Record failure
        BaseClient-->>APIClient: Response(error, success=False, retriable=false)
    else Server Error (500-599)
        OPERA-->>BaseClient: 500/502/503 etc.
        BaseClient->>BaseClient: Check retry eligibility
        BaseClient->>CircuitBreaker: Record failure

        alt Below failure threshold
            BaseClient->>BaseClient: Calculate backoff (exponential)
            BaseClient->>BaseClient: Wait {backoff}ms
            BaseClient->>OPERA: Retry request
        else Exceeds failure threshold
            CircuitBreaker->>CircuitBreaker: Trip to OPEN
            BaseClient-->>APIClient: CircuitBreakerException
        end
    end

    deactivate OPERA
    deactivate BaseClient

    APIClient->>APIClient: Update metrics
    APIClient-->>Tool: Return result
    deactivate APIClient

    Tool-->>Client: Return formatted data
    deactivate Tool
```

This sequence diagram shows the complete lifecycle of an API request from tool invocation through rate limiting, circuit breaking, authentication, and error handling with retry logic.

### Enhanced Exceptions

- **APIError**: General API errors with retryability logic
- **AuthenticationError**: OAuth and access control failures
- **RateLimitError**: Rate limiting with retry timing
- **TimeoutError**: Request and operation timeouts
- **ValidationError**: Request validation failures
- **ResourceNotFoundError**: 404 and missing resource errors
- **DataError**: JSON parsing and transformation errors
- **CircuitBreakerError**: Service protection activation
- **CachingError**: Cache operation failures

## 🚀 Usage Examples

### Basic Usage

```python
async with BaseAPIClient(auth_handler, hotel_id) as client:
    response = await client.get("rsv/reservations", params={"limit": 10})
    if response.success:
        print(f"Found {len(response.data.get('reservations', []))} reservations")
```

### Advanced Usage with Features

```python
# Initialize with custom configuration
client = BaseAPIClient(
    auth_handler=auth_handler,
    hotel_id="HOTEL123",
    enable_rate_limiting=True,
    enable_monitoring=True,
    requests_per_second=15.0,
    burst_capacity=30,
)

# Request with transformations and custom timeout
transformations = {"created_date": format_iso_date}
response = await client.get(
    "rsv/reservations",
    params={"arrival_date": "2024-12-01"},
    timeout=30.0,
    data_transformations=transformations,
)

# Check health and metrics
health = client.get_health_status()
print(f"Error rate: {health['error_rate']:.2%}")
```

## 📊 Monitoring & Observability

### Health Status Information

- **Overall Status**: healthy/warning/degraded classification
- **Request Statistics**: Total and recent request counts
- **Performance Metrics**: Average response times and error rates
- **Top Endpoints**: Most frequently used API endpoints
- **Error Breakdown**: Detailed error type analysis
- **Rate Limiter Status**: Current token availability and usage
- **Authentication Status**: Token validity and expiration

### Structured Logging

All requests and responses are logged with structured data including:

- Request/response sizes
- Duration metrics
- Retry counts
- Error details
- Hotel ID and endpoint information
- Masked sensitive data for security

## 🔒 Security Features

### Data Protection

- **Sensitive Data Masking**: Automatic PII masking in logs
- **SSL/TLS Enforcement**: Mandatory SSL verification
- **Token Security**: Encrypted persistent token caching
- **Request ID Tracking**: Unique identifiers for audit trails

### Error Handling

- **Information Disclosure Prevention**: Sanitized error messages
- **Detailed Internal Logging**: Rich debugging information for developers
- **Context Preservation**: Full error context for troubleshooting

## 🎯 Performance Optimizations

### Connection Management

- **HTTP/2 Support**: Modern protocol for improved performance
- **Connection Pooling**: Efficient connection reuse
- **Keep-Alive Optimization**: 30-second keep-alive expiry
- **Compression**: Automatic gzip/deflate compression

### Request Processing

- **Smart Rate Limiting**: Token bucket with burst capacity
- **Intelligent Retries**: Exponential backoff with jitter
- **Request Sanitization**: Automatic cleanup of request data
- **Response Caching**: Framework for future caching implementation

## 🧪 Testing Considerations

The implementation includes:

- **Comprehensive Error Simulation**: All error paths covered
- **Mock-Friendly Design**: Easy to mock for unit tests
- **Metrics Validation**: Built-in health and performance metrics
- **Example Usage**: Complete working examples

## 🚀 Production Readiness

### Scalability

- **Concurrent Request Support**: Thread-safe implementation
- **Resource Management**: Proper cleanup and connection pooling
- **Memory Efficiency**: Bounded collections and cleanup
- **Performance Monitoring**: Built-in metrics collection

### Reliability

- **Circuit Breaker Pattern**: Service protection and recovery
- **Comprehensive Error Handling**: Graceful failure management
- **Health Monitoring**: Real-time status tracking
- **Retry Logic**: Smart failure recovery

### Maintainability

- **Comprehensive Documentation**: Detailed docstrings and examples
- **Type Hints**: Full type annotation for IDE support
- **Structured Logging**: Consistent and searchable logs
- **Modular Design**: Clean separation of concerns

## 📋 Configuration Options

The BaseAPIClient supports extensive configuration through:

### Settings Parameters

- **Timeouts**: Connection, read, write, and pool timeouts
- **Retry Logic**: Max retries, backoff timing, retry strategies
- **Rate Limiting**: Requests per second, burst capacity
- **Monitoring**: Health check intervals, metrics collection
- **Authentication**: Token caching, refresh strategies

### Runtime Parameters

- **Per-Request Timeouts**: Custom timeout per API call
- **Data Transformations**: Response field transformations
- **Caching Control**: Request-level cache control
- **Custom Headers**: Additional headers per request

## 🎉 Implementation Complete

This implementation provides a **production-ready, enterprise-grade HTTP client foundation** that exceeds the requirements outlined in the OPERA Cloud MCP plan. The BaseAPIClient is now ready to serve as the foundation for all specific API clients (reservations, CRM, housekeeping, etc.) with:

- ✅ **OAuth2 authentication** with comprehensive token management
- ✅ **Exponential backoff retry logic** with intelligent error handling
- ✅ **Rate limiting and throttling** with token bucket algorithm
- ✅ **Connection pooling and timeout management** with HTTP/2 support
- ✅ **Request/response logging and monitoring** with sensitive data masking
- ✅ **Data transformation utilities** with nested field support
- ✅ **Health monitoring and metrics collection** with real-time analytics
- ✅ **Circuit breaker pattern** for service resilience
- ✅ **Comprehensive error handling** with custom exception hierarchy
- ✅ **Async context management** with proper resource cleanup

The implementation is now ready for integration with the specific OPERA Cloud API clients and MCP tools as outlined in the project plan.
