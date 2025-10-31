#!/usr/bin/env python3
"""
Comprehensive Integration Test Script for Azure AI POC API

This script runs all integration tests with detailed output and reporting.
"""

import os
import sys
from pathlib import Path

import pytest


def print_banner(title: str):
    """Print a formatted banner for test sections."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def run_quick_api_check():
    """Quick check to ensure API is accessible."""
    print_banner("🔍 QUICK API CONNECTIVITY CHECK")

    try:
        import httpx

        client = httpx.Client(timeout=5.0)
        response = client.get("http://localhost:3001/api/v1/health/")

        if response.status_code == 200:
            print("✅ API server is accessible")
            print(f"   Health status: {response.json().get('status', 'unknown')}")
            return True
        else:
            print(f"⚠️  API returned status {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Cannot connect to API: {e}")
        print("   Make sure API server is running at http://localhost:3001")
        return False


def run_test_suite(test_name: str, test_file: str):
    """Run a specific test suite with detailed output."""
    print_banner(f"🧪 {test_name}")

    test_path = Path(__file__).parent / "tests" / "integration" / test_file

    result = pytest.main(
        [
            str(test_path),
            "-v",
            "--tb=short",
            "--color=yes",
            "-s",  # Show print statements
            "--disable-warnings",  # Reduce noise
        ]
    )

    if result == 0:
        print(f"✅ {test_name} - ALL TESTS PASSED")
        return True
    else:
        print(f"❌ {test_name} - SOME TESTS FAILED")
        return False


def main():
    """Main test execution function."""
    print_banner("🚀 AZURE AI POC - INTEGRATION TEST SUITE")

    # Check API connectivity first
    if not run_quick_api_check():
        print("\n❌ Cannot proceed without API connectivity")
        print("\nTo start the API server:")
        print("   cd C:\\projects\\NRS\\azure-ai-poc\\api")
        print("   uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 3001")
        sys.exit(1)

    # Check for Bearer token
    token = os.getenv("BEARER_TOKEN")
    if not token:
        print_banner("🔐 AUTHENTICATION SETUP")
        print("No BEARER_TOKEN environment variable found.")
        print("You'll be prompted to enter your token during tests.")
        print("\nTo set token in environment:")
        print('   $env:BEARER_TOKEN = "your_token_here"')
        print("   uv run python test_all_integration.py")
    else:
        print("✅ Bearer token found in environment")

    # Test suites to run
    test_suites = [
        ("CAPABILITIES & HEALTH ENDPOINTS", "test_capabilities.py"),
        ("LANGGRAPH AGENT ENDPOINTS", "test_langgraph_agent.py"),
    ]

    results = []

    # Run each test suite
    for suite_name, test_file in test_suites:
        success = run_test_suite(suite_name, test_file)
        results.append((suite_name, success))

    # Final summary
    print_banner("📊 FINAL TEST RESULTS SUMMARY")

    all_passed = True
    for suite_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"   {status}  {suite_name}")
        if not success:
            all_passed = False

    print(f"\nOverall Result: {'🎉 ALL TESTS PASSED' if all_passed else '⚠️  SOME TESTS FAILED'}")

    if all_passed:
        print("\n🚀 Your API endpoints are working correctly!")
        print("   All agent services are responding properly")
        print("   Authentication is working")
        print("   Health checks are functional")
        print("   Error handling is appropriate")
    else:
        print("\n🔧 Please review failed tests and:")
        print("   • Check API server logs for errors")
        print("   • Verify authentication tokens")
        print("   • Ensure all required services are running")
        print("   • Check network connectivity")

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
