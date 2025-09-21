#!/usr/bin/env python3
"""
Example demonstrating the OAuth2 authentication system for OPERA Cloud MCP.

This example shows how to:
1. Initialize the OAuth handler with settings
2. Validate credentials
3. Get and use access tokens
4. Monitor token health
5. Handle authentication errors
"""

import asyncio
import logging
import os

from opera_cloud_mcp.auth import create_oauth_handler
from opera_cloud_mcp.config.settings import Settings
from opera_cloud_mcp.utils.exceptions import AuthenticationError, ConfigurationError

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Main example function."""
    try:
        logger.info("🚀 OPERA Cloud MCP OAuth2 Authentication Example")
        logger.info("=" * 50)

        # 1. Initialize settings (normally from environment variables)
        logger.info("1. Loading configuration...")

        # For this example, we'll use demo values if environment variables aren't set
        if not os.getenv("OPERA_CLIENT_ID"):
            logger.warning("Note: Using demo credentials for demonstration")
            logger.info(
                "Set OPERA_CLIENT_ID and OPERA_CLIENT_SECRET environment "
                "variables for real usage"
            )
            os.environ["OPERA_CLIENT_ID"] = os.getenv(
                "OPERA_CLIENT_ID", "your_client_id"
            )
            os.environ["OPERA_CLIENT_SECRET"] = os.getenv(
                "OPERA_CLIENT_SECRET", "your_client_secret"
            )
            os.environ["OPERA_TOKEN_URL"] = os.getenv(
                "OPERA_TOKEN_URL",
                "https://your-domain.oracle-hospitality.com/oauth/v1/tokens",
            )

        settings = Settings()
        logger.info("✅ Configuration loaded:")
        logger.info(f"   - Client ID: {settings.opera_client_id[:8]}...")
        logger.info(f"   - Token URL: {settings.opera_token_url}")
        logger.info(f"   - Persistent cache: {settings.enable_persistent_token_cache}")

        # 2. Create OAuth handler
        logger.info("2. Creating OAuth handler...")
        try:
            oauth_handler = create_oauth_handler(settings)
            logger.info("✅ OAuth handler created successfully")
        except (AuthenticationError, ConfigurationError) as e:
            logger.error(f"❌ Failed to create OAuth handler: {e}")
            return

        # 3. Validate credentials (this will attempt to get a token)
        logger.info("3. Validating OAuth credentials...")
        try:
            is_valid = await oauth_handler.validate_credentials()
            if is_valid:
                logger.info("✅ OAuth credentials are valid")
            else:
                logger.error("❌ OAuth credentials are invalid")
                return
        except AuthenticationError as e:
            logger.error(f"❌ Credential validation failed: {e}")
            logger.info("   This is expected with demo credentials")
            # Continue with example using mock data

        # 4. Get token information
        logger.info("4. Checking token status...")
        token_info = oauth_handler.get_token_info()
        logger.info("📊 Token Status:")
        logger.info(f"   - Has token: {token_info['has_token']}")
        if token_info["has_token"]:
            logger.info(f"   - Status: {token_info['status']}")
            logger.info(f"   - Type: {token_info.get('token_type', 'N/A')}")
            logger.info(
                f"   - Expires in: {token_info.get('expires_in', 'N/A')} seconds"
            )
            logger.info(f"   - Refresh count: {token_info['refresh_count']}")

        # 5. Demonstrate proactive token refresh
        logger.info("5. Testing proactive token refresh...")
        try:
            # Request token with 10 minutes minimum validity
            token = await oauth_handler.ensure_valid_token(min_validity_seconds=600)
            logger.info(f"✅ Token ensured with 10 minutes validity: {token[:20]}...")
        except AuthenticationError as e:
            logger.error(f"❌ Token refresh failed: {e}")

        # 6. Show cache information
        logger.info("6. Cache information:")
        if oauth_handler.persistent_cache:
            cache_dir = oauth_handler.persistent_cache.cache_dir
            logger.info(f"   - Cache directory: {cache_dir}")
            logger.info(f"   - Cache files: {len(list(cache_dir.glob('*.cache')))}")
        else:
            logger.info("   - Persistent cache disabled")

        # 7. Demonstrate token invalidation
        logger.info("7. Testing token invalidation...")
        await oauth_handler.invalidate_token()
        token_info_after = oauth_handler.get_token_info()
        logger.info("📊 Token Status after invalidation:")
        logger.info(f"   - Has token: {token_info_after['has_token']}")
        logger.info(f"   - Status: {token_info_after['status']}")

        logger.info("🎉 OAuth2 authentication example completed successfully!")

    except Exception as e:
        logger.error(f"Example failed: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
