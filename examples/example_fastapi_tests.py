#!/usr/bin/env python
"""
Test script for the satya FastAPI integration with assertion-based testing.

This script provides a validation suite that both demonstrates the API
functionality and verifies that the implementation is working as expected.

This script contains curl commands and explanations for testing the satya FastAPI integration.

To use this script:
1. Start the FastAPI server in one terminal:
   python example_fastapi.py

2. Run this script in another terminal to test the endpoints:
   python example_fastapi_tests.py

This will send various curl requests to the running server to test the satya
model serialization and validation.
"""
import subprocess
import json
import time
import sys
from colorama import init, Fore, Style

# Initialize colorama for colored output
init()

# Base URL for the API
BASE_URL = "http://localhost:8000"

def print_header(text):
    """Print a formatted header for each test."""
    print(f"\n{Fore.BLUE}{'=' * 80}{Style.RESET_ALL}")
    print(f"{Fore.BLUE}## {text}{Style.RESET_ALL}")
    print(f"{Fore.BLUE}{'=' * 80}{Style.RESET_ALL}\n")

def run_curl(command, description=None, expected_status=0, expected_content=None):
    """Run a curl command and return the result."""
    if description:
        print(f"{Fore.YELLOW}Test: {description}{Style.RESET_ALL}")
    
    print(f"{Fore.CYAN}Command:{Style.RESET_ALL}")
    print(f"  {command}")
    
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True
        )
        
        status_ok = result.returncode == expected_status
        response_text = result.stdout if status_ok else result.stderr
        
        # Format the response
        if status_ok:
            try:
                # Try to parse as JSON for prettier printing
                json_data = json.loads(response_text)
                print(f"{Fore.GREEN}Response (Status: {result.returncode}):{Style.RESET_ALL}")
                print(json.dumps(json_data, indent=2))
                
                # Validate expected content if provided
                content_valid = True
                content_errors = []
                if expected_content and json_data:
                    if isinstance(expected_content, dict):
                        for key, value in expected_content.items():
                            # Check if the key exists and has the expected value or type
                            if key not in json_data:
                                content_valid = False
                                content_errors.append(f"Expected key '{key}' not found")
                            elif isinstance(value, type):
                                if not isinstance(json_data[key], value):
                                    content_valid = False
                                    content_errors.append(f"Expected '{key}' to be {value.__name__}, got {type(json_data[key]).__name__}")
                            elif json_data[key] != value:
                                content_valid = False
                                content_errors.append(f"Expected '{key}' to be {value}, got {json_data[key]}")
                
                if expected_content and content_valid:
                    print(f"{Fore.GREEN}✓ Response content validation PASSED{Style.RESET_ALL}")
                elif expected_content and not content_valid:
                    print(f"{Fore.RED}✗ Response content validation FAILED:{Style.RESET_ALL}")
                    for error in content_errors:
                        print(f"  - {error}")
                
                return {
                    "success": status_ok and (not expected_content or content_valid),
                    "data": json_data,
                    "errors": content_errors if expected_content and not content_valid else []
                }
                
            except json.JSONDecodeError:
                print(f"{Fore.GREEN}Response (Status: {result.returncode}):{Style.RESET_ALL}")
                print(response_text)
                return {"success": status_ok, "data": response_text, "errors": ["Not JSON"]}
        else:
            print(f"{Fore.RED}Error (Status: {result.returncode}):{Style.RESET_ALL}")
            print(response_text)
            return {"success": False, "data": response_text, "errors": [f"Status code: {result.returncode}"]}
    except Exception as e:
        print(f"{Fore.RED}Failed to execute command: {e}{Style.RESET_ALL}")
    
    print()  # Add newline for readability

def main():
    print(f"{Fore.GREEN}Testing satya FastAPI integration with curl commands{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Make sure the FastAPI server is running (python example_fastapi.py){Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Press Ctrl+C to stop the tests at any time{Style.RESET_ALL}")
    
    # Small wait for user to read the message
    time.sleep(1)
    
    # Track test results
    test_results = []
    
    try:
        # Test 1: Basic route
        print_header("Test 1: Basic route")
        result = run_curl(
            f"curl -s {BASE_URL}/",
            "GET request to root endpoint",
            expected_content={"message": "Welcome to Satya FastAPI Example!"}
        )
        test_results.append(("Basic route", result["success"]))
        
        # Test 2: Create an item (satya model in response)
        print_header("Test 2: Create an item")
        result = run_curl(
            f"""curl -s -X POST {BASE_URL}/items/ -H "Content-Type: application/json" -d '{{"name": "Test Item", "description": "A test item created with curl", "price": 29.99, "is_offer": true, "tags": ["test", "curl", "api"]}}'""",
            "POST request to create an item (returns a satya Model in response)",
            expected_content={
                "item": dict,
                "message": str
            }
        )
        test_results.append(("Create item", result["success"]))
        
        # Test 3: Query items - no filters should return all items
        print_header("Test 3: Query items with no filters")
        result = run_curl(
            f"curl -s {BASE_URL}/items/search",
            "GET request to search items with no filters",
            expected_content={
                "items": list,
                "count": int
            }
        )
        test_results.append(("Query items - no filters", result["success"]))
        
        # Test 4: Query items with price filter - should return filtered results
        print_header("Test 4: Query items with price filters")
        result = run_curl(
            f"curl -s '{BASE_URL}/items/search?min_price=25&max_price=45'",
            "GET request to search items with min and max price filters",
            expected_content={
                "items": list,
                "count": int
            }
        )
        # Verify filtering worked by checking prices
        if result["success"] and result["data"]["items"]:
            all_within_range = all(
                25 <= item["price"] <= 45 for item in result["data"]["items"]
            )
            if all_within_range:
                print(f"{Fore.GREEN}✓ All prices are within the requested range (25-45){Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}✗ Some prices are outside the requested range (25-45){Style.RESET_ALL}")
                result["success"] = False
        
        test_results.append(("Query items - price filters", result["success"]))
        
        # Test 5: Query items with tag filter
        print_header("Test 5: Query items with tag filter")
        result = run_curl(
            f"curl -s '{BASE_URL}/items/search?tag=premium'",
            "GET request to search items with a tag filter",
            expected_content={
                "items": list,
                "count": int
            }
        )
        # Verify tag filtering worked by checking tags
        if result["success"] and result["data"]["items"]:
            all_have_tag = all(
                "premium" in item["tags"] for item in result["data"]["items"]
            )
            if all_have_tag:
                print(f"{Fore.GREEN}✓ All items have the requested tag ('premium'){Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}✗ Some items don't have the requested tag ('premium'){Style.RESET_ALL}")
                result["success"] = False
        
        test_results.append(("Query items - tag filter", result["success"]))
        
        # Test 6: Get custom response (direct satya model)
        print_header("Test 6: Get custom response (direct satya model)")
        result = run_curl(
            f"curl -s {BASE_URL}/custom",
            "GET request that returns a satya Model directly",
            expected_content={
                "id": 999,
                "name": "Custom Item",
                "price": 99.99,
                "is_offer": True,
                "tags": list
            }
        )
        test_results.append(("Direct satya model response", result["success"]))
        
        # Test 7: Invalid request (bad data)
        print_header("Test 7: Invalid request (missing required field)")
        result = run_curl(
            f"""curl -s -X POST {BASE_URL}/items/ -H "Content-Type: application/json" -d '{{"description": "Missing required name field", "price": 0}}'""",
            "POST request with invalid data (missing required fields)"
        )
        # This should fail with validation errors
        validation_error_present = "detail" in result["data"] if isinstance(result["data"], dict) else False
        if validation_error_present:
            print(f"{Fore.GREEN}✓ Properly rejected request with missing required field{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}✗ Failed to reject request with missing required field{Style.RESET_ALL}")
        
        test_results.append(("Validation - missing field", validation_error_present))
        
        # Test 8: Invalid request (bad price)
        print_header("Test 8: Invalid request (invalid price)")
        result = run_curl(
            f"""curl -s -X POST {BASE_URL}/items/ -H "Content-Type: application/json" -d '{{"name": "Bad Price Item", "price": -10.0}}'""",
            "POST request with invalid data (negative price)",
            expected_content={
                "error": "Price must be greater than zero"
            }
        )
        test_results.append(("Validation - negative price", result["success"]))
        
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Tests interrupted by user.{Style.RESET_ALL}")
        return
    
    # Print test summary
    print(f"\n{Fore.BLUE}{'=' * 80}{Style.RESET_ALL}")
    print(f"{Fore.BLUE}TEST RESULTS SUMMARY{Style.RESET_ALL}")
    print(f"{Fore.BLUE}{'=' * 80}{Style.RESET_ALL}")
    
    passed = 0
    failed = 0
    
    for test_name, result in test_results:
        if result:
            passed += 1
            print(f"{Fore.GREEN}✓ {test_name}: PASSED{Style.RESET_ALL}")
        else:
            failed += 1
            print(f"{Fore.RED}✗ {test_name}: FAILED{Style.RESET_ALL}")
    
    total = passed + failed
    pass_rate = (passed / total) * 100 if total > 0 else 0
    
    print(f"\n{Fore.BLUE}Test Summary:{Style.RESET_ALL}")
    print(f"  Total Tests: {total}")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")
    print(f"  Pass Rate: {pass_rate:.1f}%")
    
    if failed == 0:
        print(f"\n{Fore.GREEN}✓ All tests passed successfully! The satya FastAPI integration is working correctly.{Style.RESET_ALL}")
    else:
        print(f"\n{Fore.YELLOW}⚠ Some tests failed. Please review the results above.{Style.RESET_ALL}")

if __name__ == "__main__":
    main()
