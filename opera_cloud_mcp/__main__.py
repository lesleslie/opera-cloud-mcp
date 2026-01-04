#!/usr/bin/env python3
"""OPERA Cloud MCP Server - Oneiric CLI Entry Point."""

from mcp_common.cli import MCPServerCLIFactory
from mcp_common.server import BaseOneiricServerMixin, create_runtime_components
from oneiric.core.config import OneiricMCPConfig
from oneiric.runtime.mcp_health import HealthStatus

# Import the main server from the existing codebase
from opera_cloud_mcp.main import app, get_settings, initialize_server


class OperaCloudConfig(OneiricMCPConfig):
    """OPERA Cloud MCP Server Configuration."""

    http_port: int = 3040
    http_host: str = "127.0.0.1"
    enable_http_transport: bool = True

    class Config:
        env_prefix = "OPERA_CLOUD_MCP_"
        env_file = ".env"


class OperaCloudMCPServer(BaseOneiricServerMixin):
    """OPERA Cloud MCP Server with Oneiric integration."""

    def __init__(self, config: OperaCloudConfig):
        self.config = config
        self.app = app  # Use the existing FastMCP instance

        # Initialize runtime components using mcp-common helper
        self.runtime = create_runtime_components(
            server_name="opera-cloud-mcp",
            cache_dir=config.cache_dir or ".oneiric_cache",
        )
        self.snapshot_manager = self.runtime.snapshot_manager
        self.cache_manager = self.runtime.cache_manager
        self.health_monitor = self.runtime.health_monitor

    async def startup(self) -> None:
        """Server startup lifecycle hook."""
        # Initialize server components
        await initialize_server()

        # Initialize runtime components
        await self.runtime.initialize()

        # Create startup snapshot with custom components
        await self._create_startup_snapshot(
            custom_components={
                "oauth": {
                    "status": "initialized",
                    "timestamp": self._get_timestamp(),
                },
            }
        )

    async def shutdown(self) -> None:
        """Server shutdown lifecycle hook."""
        # Create shutdown snapshot
        await self._create_shutdown_snapshot()

        # Clean up runtime components
        await self.runtime.cleanup()

    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        import time

        return time.strftime("%Y-%m-%dT%H:%M:%SZ")

    async def health_check(self):
        """Perform health check."""
        # Build base health components using mixin helper
        base_components = await self._build_health_components()

        # Check OAuth configuration
        settings = get_settings()
        oauth_configured = bool(
            settings and settings.opera_client_id and settings.opera_client_secret
        )

        # Add opera-cloud-specific health checks
        base_components.append(
            self.runtime.health_monitor.create_component_health(
                name="oauth",
                status=HealthStatus.HEALTHY
                if oauth_configured
                else HealthStatus.UNHEALTHY,
                details={
                    "configured": oauth_configured,
                    "client_id": bool(settings.opera_client_id if settings else False),
                    "client_secret": bool(
                        settings.opera_client_secret if settings else False
                    ),
                },
            )
        )

        # Create health response
        return self.runtime.health_monitor.create_health_response(base_components)

    def get_app(self):
        """Get the ASGI application."""
        return self.app.http_app


def main():
    """Main entry point for OPERA Cloud MCP Server."""

    # Create CLI factory using mcp-common's enhanced factory
    cli_factory = MCPServerCLIFactory.create_server_cli(
        server_class=OperaCloudMCPServer,
        config_class=OperaCloudConfig,
        name="opera-cloud-mcp",
        description="OPERA Cloud MCP Server - Hospitality management",
    )

    # Create and run CLI
    cli_factory.create_app()()


if __name__ == "__main__":
    main()
