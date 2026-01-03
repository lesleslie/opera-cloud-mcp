"""Runtime integration test for OPERA Cloud MCP Server.

This test verifies the Oneiric runtime integration is working correctly.
Tests import paths, configuration loading, and basic lifecycle operations.
"""

import pytest


# Test 1: Verify Oneiric modules can be imported
def test_oneiric_imports():
    """Test that Oneiric runtime modules are accessible."""
    # Core CLI imports
    from oneiric.core.cli import MCPServerCLIFactory
    from oneiric.core.config import OneiricMCPConfig

    # Runtime imports
    from oneiric.runtime.snapshot import RuntimeSnapshotManager
    from oneiric.runtime.cache import RuntimeCacheManager
    from oneiric.runtime.mcp_health import HealthCheckResponse, HealthStatus, HealthMonitor

    # Verify classes exist
    assert MCPServerCLIFactory is not None
    assert OneiricMCPConfig is not None
    assert RuntimeSnapshotManager is not None
    assert RuntimeCacheManager is not None
    assert HealthMonitor is not None
    assert HealthStatus is not None
    assert HealthCheckResponse is not None


# Test 2: Verify OperaCloudConfig configuration class
def test_opera_cloud_config():
    """Test that OperaCloudConfig can be instantiated."""
    from opera_cloud_mcp.__main__ import OperaCloudConfig

    # Create configuration with defaults
    config = OperaCloudConfig()

    # Verify default values
    assert config.http_port == 3040
    assert config.http_host == "127.0.0.1"
    assert config.enable_http_transport is True
    assert config.cache_dir is None or config.cache_dir == ".oneiric_cache"


# Test 3: Verify OperaCloudMCPServer can be created
def test_opera_cloud_server_creation():
    """Test that OperaCloudMCPServer can be instantiated."""
    from opera_cloud_mcp.__main__ import OperaCloudConfig, OperaCloudMCPServer

    # Create configuration
    config = OperaCloudConfig()

    # Create server instance
    server = OperaCloudMCPServer(config)

    # Verify runtime components are initialized
    assert server.config is not None
    assert server.snapshot_manager is not None
    assert server.cache_manager is not None
    assert server.health_monitor is not None
    assert server.app is not None


# Test 4: Verify health check can be executed
@pytest.mark.asyncio
async def test_opera_cloud_health_check():
    """Test that health check method works."""
    from opera_cloud_mcp.__main__ import OperaCloudConfig, OperaCloudMCPServer

    # Create server
    config = OperaCloudConfig()
    server = OperaCloudMCPServer(config)

    # Execute health check
    health_response = await server.health_check()

    # Verify response structure
    assert health_response is not None
    assert hasattr(health_response, 'status')
    assert hasattr(health_response, 'components')
    assert len(health_response.components) > 0


# Test 5: Verify cache directory can be configured
def test_cache_directory_configuration():
    """Test that custom cache directory can be set."""
    from opera_cloud_mcp.__main__ import OperaCloudConfig

    # Create config with custom cache dir
    config = OperaCloudConfig(cache_dir="/tmp/test_cache")

    # Verify cache directory is set
    assert config.cache_dir == "/tmp/test_cache"


# Test 6: Verify CLI factory can be created
def test_cli_factory_creation():
    """Test that MCPServerCLIFactory can be created for OPERA Cloud."""
    from oneiric.core.cli import MCPServerCLIFactory
    from opera_cloud_mcp.__main__ import OperaCloudConfig, OperaCloudMCPServer

    # Create CLI factory
    cli_factory = MCPServerCLIFactory(
        server_class=OperaCloudMCPServer,
        config_class=OperaCloudConfig,
        name="opera-cloud-mcp",
        use_subcommands=True,
        legacy_flags=False,
        description="OPERA Cloud MCP Server - Hospitality management via OPERA Cloud API"
    )

    # Verify factory configuration
    assert cli_factory.server_class == OperaCloudMCPServer
    assert cli_factory.config_class == OperaCloudConfig
    assert cli_factory.name == "opera-cloud-mcp"
    assert cli_factory.use_subcommands is True
    assert cli_factory.legacy_flags is False


# Test 7: Verify environment prefix configuration
def test_environment_prefix():
    """Test that environment variable prefix is correctly configured."""
    from opera_cloud_mcp.__main__ import OperaCloudConfig

    # Check Config class attributes
    assert hasattr(OperaCloudConfig.Config, 'env_prefix')
    assert OperaCloudConfig.Config.env_prefix == "OPERA_CLOUD_MCP_"


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
