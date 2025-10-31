#!/usr/bin/env python3
"""
Integration test runner for Azure AI POC API endpoints.

This script helps run integration tests against live API endpoints with
proper authentication and detailed output.
"""

import os
import sys
from pathlib import Path

import pytest


def setup_test_environment():
    """Setup test environment and check prerequisites."""
    print("🔧 Setting up integration test environment...")

    # Check if API is running
    try:
        import httpx

        client = httpx.Client(timeout=5.0)
        response = client.get("http://localhost:3001/api/v1/health/")
        if response.status_code == 200:
            print("✅ API server is running at http://localhost:3001")
        else:
            print(f"⚠️  API server returned status {response.status_code}")
    except Exception as e:
        print(f"❌ Could not connect to API server: {e}")
        print("   Make sure the API server is running at http://localhost:3001")
        return False

    # Check for bearer token
    token = os.getenv("BEARER_TOKEN")
    if not token:
        print("⚠️  No BEARER_TOKEN environment variable found")
        print("   You'll be prompted to enter it during tests")
    else:
        print("✅ Bearer token found in environment")

    return True


def run_langgraph_tests():
    """Run LangGraph agent integration tests."""
    print("\n🚀 Running LangGraph Agent Integration Tests")
    print("=" * 50)

    test_file = Path(__file__).parent / "tests" / "integration" / "test_langgraph_agent.py"

    # Run pytest with verbose output
    result = pytest.main(
        [
            str(test_file),
            "-v",
            "--tb=short",
            "--color=yes",
            "-s",  # Don't capture output so we see print statements
        ]
    )

    return result == 0


def run_all_tests():
    """Run all integration tests."""
    print("\n🚀 Running All Integration Tests")
    print("=" * 50)

    test_dir = Path(__file__).parent / "tests" / "integration"

    result = pytest.main(
        [
            str(test_dir),
            "-v",
            "--tb=short",
            "--color=yes",
            "-s",
        ]
    )

    return result == 0


def main():
    """Main test runner function."""
    print("🧪 Azure AI POC - Integration Test Runner")
    print("=" * 60)

    if not setup_test_environment():
        print("\n❌ Environment setup failed. Please fix issues and retry.")
        sys.exit(1)

    # Parse command line arguments
    if len(sys.argv) > 1:
        test_type = sys.argv[1].lower()

        if test_type == "langgraph":
            success = run_langgraph_tests()
        elif test_type == "all":
            success = run_all_tests()
        else:
            print(f"❌ Unknown test type: {test_type}")
            print("Usage: python run_integration_tests.py [langgraph|all]")
            sys.exit(1)
    else:
        # Default to LangGraph tests
        success = run_langgraph_tests()

    if success:
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Some tests failed. Check output above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
