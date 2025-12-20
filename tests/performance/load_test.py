"""
Load testing script for OPERA Cloud MCP server.

This script simulates production load to validate performance and stability
under realistic conditions.
"""

import asyncio
import secrets
import statistics
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from opera_cloud_mcp.auth.oauth_handler import OAuthHandler, Token
from opera_cloud_mcp.clients.base_client import BaseAPIClient
from opera_cloud_mcp.config.settings import Settings


@dataclass
class LoadTestResult:
    """Results from a load test run."""

    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time: float
    median_response_time: float
    p95_response_time: float
    p99_response_time: float
    total_duration: float
    requests_per_second: float
    error_rate: float


class LoadTester:
    """Load tester for OPERA Cloud MCP server."""

    def __init__(self, api_client: BaseAPIClient):
        self.api_client = api_client
        self.results: list[dict[str, Any]] = []

    async def run_load_test(
        self,
        duration_seconds: int = 60,
        requests_per_second: int = 10,
        concurrent_users: int = 5,
    ) -> LoadTestResult:
        """
        Run a load test simulation.

        Args:
            duration_seconds: Duration of the test in seconds
            requests_per_second: Target requests per second
            concurrent_users: Number of concurrent user sessions

        Returns:
            LoadTestResult with performance metrics
        """
        print(
            f"Starting load test: {duration_seconds}s duration, "
            f"{requests_per_second} req/s, {concurrent_users} concurrent users"
        )

        start_time = time.time()
        end_time = start_time + duration_seconds

        # Track all request tasks
        all_tasks = []

        # Run the test for the specified duration
        while time.time() < end_time:
            # Create a batch of requests
            batch_size = min(requests_per_second, int(end_time - time.time()))
            batch_tasks = []

            for i in range(batch_size):
                # Simulate different types of requests
                request_types = [
                    "get_reservation",
                    "search_reservations",
                    "get_guest",
                    "search_guests",
                    "get_room_status",
                    "check_availability",
                ]
                # Use secrets to select a random request type
                request_type = request_types[secrets.randbelow(len(request_types))]

                task = self._make_request(request_type, i)
                batch_tasks.append(task)

            # Add batch tasks to all tasks
            all_tasks.extend(batch_tasks)

            # Wait for next batch (simulate RPS control)
            await asyncio.sleep(1.0 / requests_per_second)

        # Wait for all requests to complete
        print(f"Waiting for {len(all_tasks)} requests to complete...")
        responses = await asyncio.gather(*all_tasks, return_exceptions=True)

        # Calculate results
        total_duration = time.time() - start_time
        successful_requests = sum(1 for r in responses if not isinstance(r, Exception))
        failed_requests = len(responses) - successful_requests
        total_requests = len(responses)

        # Calculate response time statistics
        response_times = [r.get("duration", 0) for r in self.results if "duration" in r]
        avg_response_time = statistics.mean(response_times) if response_times else 0
        median_response_time = (
            statistics.median(response_times) if response_times else 0
        )
        p95_response_time = (
            self._percentile(response_times, 95) if response_times else 0
        )
        p99_response_time = (
            self._percentile(response_times, 99) if response_times else 0
        )

        requests_per_second_actual = total_requests / total_duration
        error_rate = (failed_requests / total_requests) if total_requests > 0 else 0

        result = LoadTestResult(
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            avg_response_time=avg_response_time,
            median_response_time=median_response_time,
            p95_response_time=p95_response_time,
            p99_response_time=p99_response_time,
            total_duration=total_duration,
            requests_per_second=requests_per_second_actual,
            error_rate=error_rate,
        )

        return result

    async def _make_request(self, request_type: str, request_id: int) -> dict[str, Any]:
        """Make a single request and track its performance."""
        start_time = time.time()

        try:
            # Simulate different request types
            if request_type == "get_reservation":
                response = await self.api_client.get(
                    f"/reservations/CONF{request_id:06d}"
                )
            elif request_type == "search_reservations":
                response = await self.api_client.get(
                    "/reservations", params={"hotelId": "TEST_HOTEL", "limit": 10}
                )
            elif request_type == "get_guest":
                response = await self.api_client.get(f"/guests/GUEST{request_id:06d}")
            elif request_type == "search_guests":
                response = await self.api_client.get(
                    "/guests",
                    params={"hotelId": "TEST_HOTEL", "name": f"Guest {request_id}"},
                )
            elif request_type == "get_room_status":
                response = await self.api_client.get(f"/rooms/ROOM{request_id:03d}")
            elif request_type == "check_availability":
                response = await self.api_client.get(
                    "/availability",
                    params={
                        "hotelId": "TEST_HOTEL",
                        "arrivalDate": "2024-12-01",
                        "departureDate": "2024-12-05",
                    },
                )
            else:
                # Default fallback
                response = await self.api_client.get(f"/test/endpoint/{request_id}")

            duration = time.time() - start_time

            # Store result
            result = {
                "request_id": request_id,
                "request_type": request_type,
                "duration": duration,
                "success": response.success if hasattr(response, "success") else True,
                "status_code": response.status_code
                if hasattr(response, "status_code")
                else 200,
                "timestamp": datetime.now(),
            }

            self.results.append(result)
            return result

        except Exception as e:
            duration = time.time() - start_time
            result = {
                "request_id": request_id,
                "request_type": request_type,
                "duration": duration,
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(),
            }
            self.results.append(result)
            return result

    def _percentile(self, data: list[float], percentile: int) -> float:
        """Calculate percentile of data."""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int((percentile / 100.0) * len(sorted_data))
        index = min(index, len(sorted_data) - 1)
        return sorted_data[index]

    def print_results(self, result: LoadTestResult):
        """Print formatted load test results."""
        print("\n" + "=" * 60)
        print("LOAD TEST RESULTS")
        print("=" * 60)
        print(f"Duration: {result.total_duration:.2f} seconds")
        print(f"Total Requests: {result.total_requests}")
        print(f"Successful Requests: {result.successful_requests}")
        print(f"Failed Requests: {result.failed_requests}")
        print(f"Error Rate: {result.error_rate:.2%}")
        print(f"Requests Per Second: {result.requests_per_second:.2f}")
        print("\nResponse Time Statistics:")
        print(f"  Average: {result.avg_response_time:.3f}s")
        print(f"  Median:  {result.median_response_time:.3f}s")
        print(f"  95th %:  {result.p95_response_time:.3f}s")
        print(f"  99th %:  {result.p99_response_time:.3f}s")
        print("=" * 60)


async def main():
    """Main function to run load tests."""
    print("OPERA Cloud MCP Load Testing")
    print("=" * 40)

    # Create mock components for testing
    mock_auth_handler = OAuthHandler(
        client_id="test_client",
        client_secret="test_secret",
        token_url="https://api.test.com/oauth/token",
    )

    # Set a valid token for testing
    mock_auth_handler._token_cache = Token(
        access_token="test_token", expires_in=3600, issued_at=datetime.now()
    )

    mock_settings = Settings(
        opera_client_id="test_client_id",
        opera_client_secret="test_client_secret",
        opera_token_url="https://api.test.com/oauth/v1/tokens",
        opera_base_url="https://api.test.com",
        opera_api_version="v1",
        opera_environment="test",
        default_hotel_id="TEST_HOTEL",
        request_timeout=30,
        max_retries=3,
        retry_backoff=1.0,
        enable_cache=True,
        cache_ttl=300,
        cache_max_memory=10000,
        oauth_max_retries=3,
        oauth_retry_backoff=1.0,
        enable_persistent_token_cache=True,
        token_cache_dir=None,  # Use default secure location
        log_level="INFO",
        log_format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        enable_structured_logging=True,
    )

    # Create API client
    api_client = BaseAPIClient(
        auth_handler=mock_auth_handler,
        hotel_id="TEST_HOTEL",
        settings=mock_settings,
        enable_rate_limiting=True,
        enable_monitoring=True,
        enable_caching=True,
        requests_per_second=50,
        burst_capacity=100,
    )

    # Create load tester
    load_tester = LoadTester(api_client)

    # Run different load test scenarios
    scenarios = [
        {"name": "Low Load Test", "duration": 30, "rps": 5, "users": 2},
        {"name": "Medium Load Test", "duration": 60, "rps": 20, "users": 5},
        {"name": "High Load Test", "duration": 120, "rps": 50, "users": 10},
    ]

    for scenario in scenarios:
        print(f"\nRunning {scenario['name']}...")
        result = await load_tester.run_load_test(
            duration_seconds=scenario["duration"],
            requests_per_second=scenario["rps"],
            concurrent_users=scenario["users"],
        )
        load_tester.print_results(result)

        # Add a small delay between tests
        await asyncio.sleep(2)

    # Clean up
    await api_client.close()
    print("\nLoad testing completed!")


if __name__ == "__main__":
    asyncio.run(main())
