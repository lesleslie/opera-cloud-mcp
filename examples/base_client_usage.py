#!/usr/bin/env python3
"""
Example usage of the enhanced BaseAPIClient for OPERA Cloud MCP.

This example demonstrates how to use the production-ready BaseAPIClient
with all its advanced features including rate limiting, monitoring,
data transformation, and comprehensive error handling.
"""

import asyncio
import logging
import os
from datetime import datetime
from pathlib import Path

from opera_cloud_mcp.auth.oauth_handler import OAuthHandler
from opera_cloud_mcp.clients.base_client import BaseAPIClient
from opera_cloud_mcp.config.settings import Settings
from opera_cloud_mcp.utils.exceptions import (
    AuthenticationError,
    RateLimitError,
    TimeoutError,
    ValidationError,
)

# Configure logging to see the detailed request/response logs
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


async def main():
    """Demonstrate BaseAPIClient usage with various features."""

    # Initialize settings (you would normally set these in environment variables)
    settings = Settings(
        opera_client_id=os.getenv("OPERA_CLIENT_ID", "your_client_id"),
        opera_client_secret=os.getenv("OPERA_CLIENT_SECRET", "your_client_secret"),
        opera_token_url=os.getenv(
            "OPERA_TOKEN_URL",
            "https://your-domain.oracle-hospitality.com/oauth/v1/tokens",
        ),
        opera_base_url=os.getenv(
            "OPERA_BASE_URL", "https://your-domain.oracle-hospitality.com"
        ),
        opera_api_version="v1",
        request_timeout=30,
        max_retries=3,
        retry_backoff=1.0,
    )

    # Initialize OAuth handler with enhanced features
    auth_handler = OAuthHandler(
        client_id=settings.opera_client_id,
        client_secret=settings.opera_client_secret,
        token_url=settings.opera_token_url,
        timeout=settings.request_timeout,
        max_retries=settings.oauth_max_retries,
        retry_backoff=settings.oauth_retry_backoff,
        enable_persistent_cache=settings.enable_persistent_token_cache,
        cache_dir=Path(settings.token_cache_dir) if settings.token_cache_dir else None,
    )

    # Initialize BaseAPIClient with all features enabled
    hotel_id = "HOTEL123"

    async with BaseAPIClient(
        auth_handler=auth_handler,
        hotel_id=hotel_id,
        settings=settings,
        enable_rate_limiting=True,  # Enable rate limiting (10 requests/second)
        enable_monitoring=True,  # Enable health monitoring and metrics
        requests_per_second=10.0,  # Configure rate limiting
        burst_capacity=20,  # Allow bursts up to 20 requests
    ) as client:
        logger.info("BaseAPIClient initialized successfully")

        # Example 1: Basic health check
        try:
            health_status = await client.health_check()
            logger.info(f"Client health status: {health_status['status']}")
            auth_status = health_status["authentication"]["token_status"]
            logger.info(f"Authentication status: {auth_status}")

            if client.enable_rate_limiting:
                rate_stats = health_status.get("rate_limiter", {})
                current_tokens = rate_stats.get("current_tokens", 0)
                logger.info(f"Rate limiter - Current tokens: {current_tokens}")

        except Exception as e:
            logger.error(f"Health check failed: {e}")

        # Example 2: GET request with data transformations
        try:
            # Define data transformations for response processing
            def format_date(date_str: str) -> str:
                """Transform date strings to a consistent format."""
                if not date_str:
                    return ""
                try:
                    dt = datetime.fromisoformat(date_str)
                    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
                except (ValueError, TypeError):
                    return date_str

            transformations = {
                "created_date": format_date,
                "modified_date": format_date,
            }

            # Make a GET request with transformations
            response = await client.get(
                endpoint="rsv/reservations",
                params={
                    "arrival_date": "2024-12-01",
                    "departure_date": "2024-12-05",
                    "limit": 10,
                },
                timeout=15.0,  # Custom timeout
                data_transformations=transformations,
            )

            if response.success:
                logger.info(f"GET request successful - Status: {response.status_code}")
                data_keys = list(response.data.keys()) if response.data else "No data"
                logger.info(f"Response data keys: {data_keys}")

                # Access metrics if available
                if response.metrics:
                    duration = response.metrics.duration_ms
                    size = response.metrics.response_size_bytes
                    logger.info(f"Request took {duration:.2f}ms")
                    logger.info(f"Response size: {size} bytes")
            else:
                logger.warning(f"GET request failed: {response.error}")

        except ValidationError as e:
            logger.error(f"Validation error: {e}")
            logger.error(f"Error details: {e.details}")

        except RateLimitError as e:
            logger.warning(f"Rate limit exceeded: {e}")
            wait_time = e.get_backoff_time()
            logger.info(f"Recommended wait time: {wait_time} seconds")

        except TimeoutError as e:
            logger.error(f"Request timeout: {e}")
            if e.timeout_duration:
                logger.error(f"Timeout duration: {e.timeout_duration} seconds")

        except AuthenticationError as e:
            logger.error(f"Authentication failed: {e}")

        except Exception as e:
            logger.error(f"Unexpected error: {e}")

        # Example 3: POST request with data sanitization
        try:
            # Create reservation data (with some None values that will be sanitized)
            reservation_data = {
                "guest": {
                    "first_name": "John",
                    "last_name": "Doe",
                    "email": "john.doe@example.com",
                    "phone": None,  # This will be removed by sanitization
                    "preferences": {
                        "room_type": "Standard",
                        "smoking": False,
                        "special_requests": "",  # This will be removed by sanitization
                    },
                },
                "arrival_date": "2024-12-01",
                "departure_date": "2024-12-05",
                "room_type": "Standard",
                "rate_code": "RACK",
                "comments": None,  # This will be removed by sanitization
            }

            response = await client.post(
                endpoint="rsv/reservations", json_data=reservation_data, timeout=30.0
            )

            if response.success:
                logger.info(f"POST request successful - Status: {response.status_code}")
                reservation_id = (
                    response.data.get("reservation_id") if response.data else None
                )
                logger.info(f"Created reservation ID: {reservation_id}")
            else:
                logger.warning(f"POST request failed: {response.error}")

        except Exception as e:
            logger.error(f"POST request error: {e}")

        # Example 4: Check comprehensive health status
        try:
            final_health = client.get_health_status()

            logger.info("\n=== Final Health Status ===")
            logger.info(f"Overall status: {final_health.get('status', 'unknown')}")
            logger.info(f"Total requests: {final_health.get('total_requests', 0)}")
            logger.info(f"Recent requests: {final_health.get('recent_requests', 0)}")
            error_rate = final_health.get("error_rate", 0)
            avg_time = final_health.get("avg_response_time_ms", 0)
            logger.info(f"Error rate: {error_rate:.2%}")
            logger.info(f"Avg response time: {avg_time:.2f}ms")

            # Show top endpoints
            top_endpoints = final_health.get("top_endpoints", {})
            if top_endpoints:
                logger.info("\nTop API endpoints:")
                for endpoint, stats in list(top_endpoints.items())[:3]:
                    count = stats["count"]
                    avg_duration = stats["avg_duration"]
                    logger.info(
                        f"  {endpoint}: {count} requests, {avg_duration:.2f}ms avg"
                    )

            # Show error breakdown
            error_counts = final_health.get("error_counts", {})
            if error_counts:
                logger.info("\nError breakdown:")
                for error_type, count in error_counts.items():
                    logger.info(f"  {error_type}: {count}")

        except Exception as e:
            logger.error(f"Failed to get final health status: {e}")


if __name__ == "__main__":
    """
    Run the example.

    Note: This example requires valid OPERA Cloud API credentials.
    Set the following environment variables:

    OPERA_CLIENT_ID=your_client_id
    OPERA_CLIENT_SECRET=your_client_secret
    OPERA_TOKEN_URL=https://api.oracle-hospitality.com/oauth/v1/tokens
    OPERA_BASE_URL=https://api.oracle-hospitality.com
    """
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Example interrupted by user")
    except Exception as e:
        logger.error(f"Example failed: {e}")
        raise
