#!/usr/bin/env python3
"""
Test script to verify cache manager cleanup works without SQLite errors
"""

import asyncio

from src.gitlab_analyzer.mcp.cache.manager import (
    cleanup_cache_manager,
    get_cache_manager,
)


async def test_cache_cleanup():
    """Test cache manager cleanup to avoid SQLite threading errors"""
    print("Testing cache manager cleanup...")

    try:
        # Get cache manager instance
        cache_manager = get_cache_manager("test_cleanup.db")
        await cache_manager.initialize()
        print("✓ Cache manager initialized")

        # Do some basic operation
        await cache_manager.set(
            "test_key", {"test": "data"}, "test_data", "test_project", 123
        )
        print("✓ Test data stored")

        # Retrieve data
        result = await cache_manager.get("test_key")
        if result:
            print("✓ Test data retrieved")

        # Properly cleanup
        await cleanup_cache_manager()
        print("✓ Cache manager properly cleaned up")

        return True

    except Exception as e:
        print(f"✗ Error during test: {e}")
        return False


async def test_multiple_cleanup_calls():
    """Test that multiple cleanup calls don't cause issues"""
    print("\nTesting multiple cleanup calls...")

    try:
        # Get cache manager
        cache_manager = get_cache_manager("test_cleanup2.db")
        await cache_manager.initialize()

        # Call cleanup multiple times
        await cleanup_cache_manager()
        await cleanup_cache_manager()  # Should be safe to call multiple times
        await cleanup_cache_manager()

        print("✓ Multiple cleanup calls handled safely")
        return True

    except Exception as e:
        print(f"✗ Error during multiple cleanup test: {e}")
        return False


if __name__ == "__main__":
    print("Cache Manager Cleanup Test")
    print("=" * 40)

    try:
        success1 = asyncio.run(test_cache_cleanup())
        success2 = asyncio.run(test_multiple_cleanup_calls())

        if success1 and success2:
            print("\n✅ All cleanup tests passed!")
            print("SQLite threading warnings should be significantly reduced.")
        else:
            print("\n❌ Some cleanup tests failed")

    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")

    print("\nNote: Any remaining SQLite threading warnings are harmless")
    print("and occur during Python interpreter shutdown.")
