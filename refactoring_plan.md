# BaseAPIClient Request Method Refactoring Plan

## Current Complexity Analysis

The `request` method in `opera_cloud_mcp/clients/base_client.py` has a cyclomatic complexity of 61, which is extremely high. The method is responsible for:

1. Cache checking and retrieval
1. Distributed tracing setup
1. Rate limiting
1. Request preparation (URL, headers, data sanitization)
1. Retry logic with multiple exception types
1. Response handling
1. Metrics recording
1. Cache storage
1. Error handling with specific exception mapping

## Refactoring Strategy

### 1. Extract Cache Operations

- `_check_cache()` - Check and retrieve cached responses
- `_store_cache()` - Store successful responses in cache

### 2. Extract Request Preparation

- `_prepare_request_context()` - Initialize timing, ensure session
- `_build_request_url()` - Construct full URL
- `_prepare_request_headers()` - Build and merge headers
- `_prepare_request_data()` - Sanitize and transform request data

### 3. Extract Metrics and Monitoring

- `_record_metrics()` - Record request metrics
- `_start_tracing()` - Start distributed tracing span
- `_finish_tracing()` - Complete tracing span

### 4. Extract Retry Logic

- `_execute_with_retry()` - Main retry loop
- `_handle_retry_exception()` - Process exceptions and determine retry behavior
- `_calculate_backoff()` - Calculate retry backoff time

### 5. Extract Request Execution

- `_execute_single_request()` - Execute a single HTTP request
- `_apply_rate_limiting()` - Apply rate limiting before request

### 6. Simplify Error Handling

- `_convert_to_opera_error()` - Convert exceptions to appropriate OperaCloudError types

## Implementation Steps

1. Create helper methods for each extracted component
1. Update the main `request` method to orchestrate these components
1. Ensure all functionality is preserved
1. Add proper type hints and documentation
1. Test thoroughly to ensure no regression

## Expected Benefits

- Reduce cyclomatic complexity from 61 to below 15 for the main method
- Each extracted method will have complexity below 10
- Improved readability and maintainability
- Easier testing of individual components
- Better separation of concerns
- Clearer error handling flow

## Risk Mitigation

- Preserve all existing functionality
- Maintain backward compatibility
- Keep the same public API
- Ensure all error cases are handled identically
- Maintain the same retry behavior
- Keep metrics and logging intact
