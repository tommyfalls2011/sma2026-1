#!/usr/bin/env python3
"""
Backend Authentication and Subscription API Testing
Tests the new authentication and subscription endpoints
"""

import requests
import json
import sys
from datetime import datetime

# Get backend URL from frontend environment
def get_backend_url():
    """Get the backend URL from frontend .env file"""
    try:
        with open('/app/frontend/.env', 'r') as f:
            for line in f:
                if line.startswith('EXPO_PUBLIC_BACKEND_URL='):
                    base_url = line.split('=', 1)[1].strip().strip('"')
                    return f"{base_url}/api"
    except Exception as e:
        print(f"Error reading frontend .env: {e}")
    
    # Fallback
    return "http://localhost:8001/api"

BACKEND_URL = get_backend_url()

class AuthenticationTester:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.test_results = {
            "calculate_endpoint": {"passed": 0, "failed": 0, "errors": []},
            "history_get": {"passed": 0, "failed": 0, "errors": []},
            "history_delete": {"passed": 0, "failed": 0, "errors": []}
        }
        
    def log_result(self, test_name: str, success: bool, message: str):
        """Log test result"""
        if success:
            self.test_results[test_name]["passed"] += 1
            print(f"✅ {message}")
        else:
            self.test_results[test_name]["failed"] += 1
            self.test_results[test_name]["errors"].append(message)
            print(f"❌ {message}")
    
    def test_calculate_valid_meters(self):
        """Test POST /api/calculate with valid meters input"""
        test_data = {
            "num_elements": 5,
            "height_from_ground": 10,
            "boom_diameter": 0.025,
            "element_size": 0.01,
            "tapered": False,
            "frequency_mhz": 144,
            "unit": "meters"
        }
        
        try:
            response = requests.post(f"{self.base_url}/calculate", json=test_data, timeout=10)
            
            if response.status_code != 200:
                self.log_result("calculate_endpoint", False, 
                              f"Calculate meters - HTTP {response.status_code}: {response.text}")
                return
            
            data = response.json()
            
            # Validate required fields
            required_fields = [
                "swr", "fb_ratio", "beamwidth", "bandwidth", "gain_dbi", 
                "multiplication_factor", "antenna_efficiency", "far_field_pattern"
            ]
            
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                self.log_result("calculate_endpoint", False, 
                              f"Calculate meters - Missing fields: {missing_fields}")
                return
            
            # Validate data types and ranges
            if not isinstance(data["swr"], (int, float)) or data["swr"] < 1.0:
                self.log_result("calculate_endpoint", False, 
                              f"Calculate meters - Invalid SWR: {data['swr']}")
                return
            
            if not isinstance(data["gain_dbi"], (int, float)):
                self.log_result("calculate_endpoint", False, 
                              f"Calculate meters - Invalid gain_dbi: {data['gain_dbi']}")
                return
            
            if not isinstance(data["far_field_pattern"], list) or len(data["far_field_pattern"]) == 0:
                self.log_result("calculate_endpoint", False, 
                              f"Calculate meters - Invalid far_field_pattern")
                return
            
            # Check far field pattern structure
            pattern_point = data["far_field_pattern"][0]
            if not ("angle" in pattern_point and "magnitude" in pattern_point):
                self.log_result("calculate_endpoint", False, 
                              f"Calculate meters - Invalid pattern point structure")
                return
            
            self.log_result("calculate_endpoint", True, 
                          f"Calculate meters - Success: SWR={data['swr']}, Gain={data['gain_dbi']}dBi")
            
        except requests.exceptions.RequestException as e:
            self.log_result("calculate_endpoint", False, f"Calculate meters - Network error: {e}")
        except Exception as e:
            self.log_result("calculate_endpoint", False, f"Calculate meters - Error: {e}")
    
    def test_calculate_valid_inches(self):
        """Test POST /api/calculate with valid inches input"""
        test_data = {
            "num_elements": 3,
            "height_from_ground": 394,
            "boom_diameter": 1,
            "element_size": 0.4,
            "tapered": True,
            "frequency_mhz": 432,
            "unit": "inches"
        }
        
        try:
            response = requests.post(f"{self.base_url}/calculate", json=test_data, timeout=10)
            
            if response.status_code != 200:
                self.log_result("calculate_endpoint", False, 
                              f"Calculate inches - HTTP {response.status_code}: {response.text}")
                return
            
            data = response.json()
            
            # Basic validation
            if "swr" not in data or "gain_dbi" not in data:
                self.log_result("calculate_endpoint", False, 
                              f"Calculate inches - Missing basic fields")
                return
            
            self.log_result("calculate_endpoint", True, 
                          f"Calculate inches - Success: SWR={data['swr']}, Gain={data['gain_dbi']}dBi")
            
        except requests.exceptions.RequestException as e:
            self.log_result("calculate_endpoint", False, f"Calculate inches - Network error: {e}")
        except Exception as e:
            self.log_result("calculate_endpoint", False, f"Calculate inches - Error: {e}")
    
    def test_calculate_invalid_inputs(self):
        """Test POST /api/calculate with invalid inputs"""
        
        # Test negative values
        invalid_data = {
            "num_elements": -1,
            "height_from_ground": 10,
            "boom_diameter": 0.025,
            "element_size": 0.01,
            "tapered": False,
            "frequency_mhz": 144,
            "unit": "meters"
        }
        
        try:
            response = requests.post(f"{self.base_url}/calculate", json=invalid_data, timeout=10)
            
            if response.status_code == 422:  # Validation error expected
                self.log_result("calculate_endpoint", True, 
                              "Calculate invalid - Correctly rejected negative num_elements")
            else:
                self.log_result("calculate_endpoint", False, 
                              f"Calculate invalid - Should reject negative values, got {response.status_code}")
        except Exception as e:
            self.log_result("calculate_endpoint", False, f"Calculate invalid - Error: {e}")
        
        # Test missing required field
        incomplete_data = {
            "num_elements": 5,
            "height_from_ground": 10,
            # Missing boom_diameter
            "element_size": 0.01,
            "tapered": False,
            "frequency_mhz": 144,
            "unit": "meters"
        }
        
        try:
            response = requests.post(f"{self.base_url}/calculate", json=incomplete_data, timeout=10)
            
            if response.status_code == 422:  # Validation error expected
                self.log_result("calculate_endpoint", True, 
                              "Calculate invalid - Correctly rejected missing field")
            else:
                self.log_result("calculate_endpoint", False, 
                              f"Calculate invalid - Should reject missing fields, got {response.status_code}")
        except Exception as e:
            self.log_result("calculate_endpoint", False, f"Calculate invalid missing field - Error: {e}")
    
    def test_get_history(self):
        """Test GET /api/history"""
        try:
            response = requests.get(f"{self.base_url}/history", timeout=10)
            
            if response.status_code != 200:
                self.log_result("history_get", False, 
                              f"Get history - HTTP {response.status_code}: {response.text}")
                return
            
            data = response.json()
            
            if not isinstance(data, list):
                self.log_result("history_get", False, 
                              f"Get history - Expected list, got {type(data)}")
                return
            
            self.log_result("history_get", True, 
                          f"Get history - Success: Retrieved {len(data)} records")
            
        except requests.exceptions.RequestException as e:
            self.log_result("history_get", False, f"Get history - Network error: {e}")
        except Exception as e:
            self.log_result("history_get", False, f"Get history - Error: {e}")
    
    def test_delete_history(self):
        """Test DELETE /api/history"""
        try:
            response = requests.delete(f"{self.base_url}/history", timeout=10)
            
            if response.status_code != 200:
                self.log_result("history_delete", False, 
                              f"Delete history - HTTP {response.status_code}: {response.text}")
                return
            
            data = response.json()
            
            if "deleted_count" not in data:
                self.log_result("history_delete", False, 
                              f"Delete history - Missing deleted_count in response")
                return
            
            if not isinstance(data["deleted_count"], int):
                self.log_result("history_delete", False, 
                              f"Delete history - deleted_count should be integer")
                return
            
            self.log_result("history_delete", True, 
                          f"Delete history - Success: Deleted {data['deleted_count']} records")
            
        except requests.exceptions.RequestException as e:
            self.log_result("history_delete", False, f"Delete history - Network error: {e}")
        except Exception as e:
            self.log_result("history_delete", False, f"Delete history - Error: {e}")
    
    def test_backend_connectivity(self):
        """Test basic backend connectivity"""
        try:
            response = requests.get(f"{self.base_url}/", timeout=10)
            if response.status_code == 200:
                print(f"✅ Backend connectivity - API is reachable")
                return True
            else:
                print(f"❌ Backend connectivity - HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Backend connectivity - Error: {e}")
            return False
    
    def run_all_tests(self):
        """Run all backend tests"""
        print("=" * 60)
        print("ANTENNA CALCULATOR BACKEND API TESTS")
        print("=" * 60)
        
        # Test connectivity first
        if not self.test_backend_connectivity():
            print("\n❌ Backend is not reachable. Stopping tests.")
            return False
        
        print("\n--- Testing POST /api/calculate ---")
        self.test_calculate_valid_meters()
        self.test_calculate_valid_inches()
        self.test_calculate_invalid_inputs()
        
        print("\n--- Testing GET /api/history ---")
        self.test_get_history()
        
        print("\n--- Testing DELETE /api/history ---")
        self.test_delete_history()
        
        # Summary
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        
        total_passed = 0
        total_failed = 0
        all_success = True
        
        for test_name, results in self.test_results.items():
            passed = results["passed"]
            failed = results["failed"]
            total_passed += passed
            total_failed += failed
            
            status = "✅ PASS" if failed == 0 else "❌ FAIL"
            print(f"{test_name}: {status} ({passed} passed, {failed} failed)")
            
            if failed > 0:
                all_success = False
                for error in results["errors"]:
                    print(f"  - {error}")
        
        print(f"\nOVERALL: {total_passed} passed, {total_failed} failed")
        
        if all_success:
            print("🎉 All backend tests PASSED!")
        else:
            print("⚠️  Some backend tests FAILED!")
        
        return all_success

if __name__ == "__main__":
    tester = AntennaCalculatorTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)