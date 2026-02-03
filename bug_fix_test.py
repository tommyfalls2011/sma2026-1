#!/usr/bin/env python3
"""
Bug Fix Testing for Antenna Calculator Application
Tests specific bug fixes for dynamic SWR calculation and auto-tune endpoint
"""

import requests
import json
import os
from typing import Dict, Any
import sys

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
print(f"Testing backend at: {BACKEND_URL}")

class BugFixTester:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.test_results = {
            "dynamic_swr": {"passed": 0, "failed": 0, "errors": []},
            "auto_tune": {"passed": 0, "failed": 0, "errors": []}
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
    
    def test_dynamic_swr_calculation(self):
        """Test that SWR changes dynamically with different element lengths"""
        print("\n=== Testing Dynamic SWR Calculation ===")
        
        # Test 1: Standard elements
        test1_data = {
            "num_elements": 3,
            "elements": [
                {"element_type": "reflector", "length": 216, "diameter": 0.5, "position": 0},
                {"element_type": "driven", "length": 204, "diameter": 0.5, "position": 48},
                {"element_type": "director", "length": 195, "diameter": 0.5, "position": 96}
            ],
            "height_from_ground": 35,
            "height_unit": "ft",
            "boom_diameter": 2,
            "boom_unit": "inches",
            "band": "11m_cb"
        }
        
        # Test 2: Modified driven element (longer)
        test2_data = {
            "num_elements": 3,
            "elements": [
                {"element_type": "reflector", "length": 216, "diameter": 0.5, "position": 0},
                {"element_type": "driven", "length": 220, "diameter": 0.5, "position": 48},
                {"element_type": "director", "length": 195, "diameter": 0.5, "position": 96}
            ],
            "height_from_ground": 35,
            "height_unit": "ft",
            "boom_diameter": 2,
            "boom_unit": "inches",
            "band": "11m_cb"
        }
        
        # Test 3: Shorter driven element
        test3_data = {
            "num_elements": 3,
            "elements": [
                {"element_type": "reflector", "length": 216, "diameter": 0.5, "position": 0},
                {"element_type": "driven", "length": 190, "diameter": 0.5, "position": 48},
                {"element_type": "director", "length": 195, "diameter": 0.5, "position": 96}
            ],
            "height_from_ground": 35,
            "height_unit": "ft",
            "boom_diameter": 2,
            "boom_unit": "inches",
            "band": "11m_cb"
        }
        
        swr_values = []
        test_configs = [
            ("Standard elements (204\" driven)", test1_data),
            ("Longer driven element (220\")", test2_data),
            ("Shorter driven element (190\")", test3_data)
        ]
        
        for config_name, test_data in test_configs:
            try:
                response = requests.post(f"{self.base_url}/calculate", json=test_data, timeout=15)
                
                if response.status_code != 200:
                    self.log_result("dynamic_swr", False, 
                                  f"SWR Test {config_name} - HTTP {response.status_code}: {response.text}")
                    continue
                
                data = response.json()
                
                if "swr" not in data:
                    self.log_result("dynamic_swr", False, 
                                  f"SWR Test {config_name} - Missing SWR in response")
                    continue
                
                swr = data["swr"]
                swr_values.append(swr)
                print(f"  {config_name}: SWR = {swr}")
                
                # Validate SWR is reasonable
                if not isinstance(swr, (int, float)) or swr < 1.0 or swr > 10.0:
                    self.log_result("dynamic_swr", False, 
                                  f"SWR Test {config_name} - Invalid SWR value: {swr}")
                    continue
                
            except requests.exceptions.RequestException as e:
                self.log_result("dynamic_swr", False, f"SWR Test {config_name} - Network error: {e}")
                continue
            except Exception as e:
                self.log_result("dynamic_swr", False, f"SWR Test {config_name} - Error: {e}")
                continue
        
        # Critical test: All SWR values must be different
        if len(swr_values) == 3:
            unique_swr_values = len(set(swr_values))
            if unique_swr_values == 3:
                self.log_result("dynamic_swr", True, 
                              f"Dynamic SWR - SUCCESS: All 3 SWR values are different {swr_values}")
            elif unique_swr_values == 1:
                self.log_result("dynamic_swr", False, 
                              f"Dynamic SWR - CRITICAL BUG: All SWR values are the same {swr_values} - Bug NOT fixed!")
            else:
                self.log_result("dynamic_swr", False, 
                              f"Dynamic SWR - PARTIAL BUG: Only {unique_swr_values} unique SWR values {swr_values}")
        else:
            self.log_result("dynamic_swr", False, 
                          f"Dynamic SWR - Could not complete all 3 tests, only got {len(swr_values)} results")
    
    def test_auto_tune_endpoint(self):
        """Test the auto-tune endpoint functionality"""
        print("\n=== Testing Auto-Tune Endpoint ===")
        
        # Test 1: 3-element auto-tune
        test1_data = {
            "num_elements": 3,
            "height_from_ground": 35,
            "height_unit": "ft",
            "boom_diameter": 2,
            "boom_unit": "inches",
            "band": "11m_cb"
        }
        
        try:
            response = requests.post(f"{self.base_url}/auto-tune", json=test1_data, timeout=15)
            
            if response.status_code != 200:
                self.log_result("auto_tune", False, 
                              f"Auto-tune 3-element - HTTP {response.status_code}: {response.text}")
            else:
                data = response.json()
                
                # Validate required fields
                required_fields = ["optimized_elements", "predicted_swr", "predicted_gain", "optimization_notes"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_result("auto_tune", False, 
                                  f"Auto-tune 3-element - Missing fields: {missing_fields}")
                else:
                    # Validate optimized_elements structure
                    elements = data["optimized_elements"]
                    if not isinstance(elements, list) or len(elements) != 3:
                        self.log_result("auto_tune", False, 
                                      f"Auto-tune 3-element - Expected 3 elements, got {len(elements) if isinstance(elements, list) else 'non-list'}")
                    else:
                        # Check element types
                        element_types = [elem.get("element_type") for elem in elements]
                        expected_types = ["reflector", "driven", "director"]
                        
                        if set(element_types) != set(expected_types):
                            self.log_result("auto_tune", False, 
                                          f"Auto-tune 3-element - Wrong element types: {element_types}")
                        else:
                            # Validate SWR and gain ranges
                            swr = data["predicted_swr"]
                            gain = data["predicted_gain"]
                            
                            if not (1.0 <= swr <= 1.2):
                                self.log_result("auto_tune", False, 
                                              f"Auto-tune 3-element - SWR {swr} not in expected range 1.0-1.2")
                            elif not (8.0 <= gain <= 12.0):
                                self.log_result("auto_tune", False, 
                                              f"Auto-tune 3-element - Gain {gain} not in expected range 8-12 dBi")
                            else:
                                self.log_result("auto_tune", True, 
                                              f"Auto-tune 3-element - SUCCESS: SWR={swr}, Gain={gain}dBi, {len(elements)} elements")
                
        except requests.exceptions.RequestException as e:
            self.log_result("auto_tune", False, f"Auto-tune 3-element - Network error: {e}")
        except Exception as e:
            self.log_result("auto_tune", False, f"Auto-tune 3-element - Error: {e}")
        
        # Test 2: 5-element auto-tune with different band
        test2_data = {
            "num_elements": 5,
            "height_from_ground": 40,
            "height_unit": "ft",
            "boom_diameter": 2.5,
            "boom_unit": "inches",
            "band": "10m"
        }
        
        try:
            response = requests.post(f"{self.base_url}/auto-tune", json=test2_data, timeout=15)
            
            if response.status_code != 200:
                self.log_result("auto_tune", False, 
                              f"Auto-tune 5-element - HTTP {response.status_code}: {response.text}")
            else:
                data = response.json()
                
                if "optimized_elements" not in data:
                    self.log_result("auto_tune", False, 
                                  f"Auto-tune 5-element - Missing optimized_elements")
                else:
                    elements = data["optimized_elements"]
                    if len(elements) != 5:
                        self.log_result("auto_tune", False, 
                                      f"Auto-tune 5-element - Expected 5 elements, got {len(elements)}")
                    else:
                        # Check for proper director progression
                        directors = [elem for elem in elements if elem.get("element_type") == "director"]
                        if len(directors) != 3:
                            self.log_result("auto_tune", False, 
                                          f"Auto-tune 5-element - Expected 3 directors, got {len(directors)}")
                        else:
                            # Check director lengths are progressively shorter
                            director_lengths = [d["length"] for d in directors]
                            is_progressive = all(director_lengths[i] > director_lengths[i+1] for i in range(len(director_lengths)-1))
                            
                            if not is_progressive:
                                self.log_result("auto_tune", False, 
                                              f"Auto-tune 5-element - Directors not progressively shorter: {director_lengths}")
                            else:
                                self.log_result("auto_tune", True, 
                                              f"Auto-tune 5-element - SUCCESS: 5 elements with progressive directors {director_lengths}")
                
        except requests.exceptions.RequestException as e:
            self.log_result("auto_tune", False, f"Auto-tune 5-element - Network error: {e}")
        except Exception as e:
            self.log_result("auto_tune", False, f"Auto-tune 5-element - Error: {e}")
    
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
        """Run all bug fix tests"""
        print("=" * 70)
        print("ANTENNA CALCULATOR BUG FIX TESTS")
        print("=" * 70)
        
        # Test connectivity first
        if not self.test_backend_connectivity():
            print("\n❌ Backend is not reachable. Stopping tests.")
            return False
        
        # Run specific bug fix tests
        self.test_dynamic_swr_calculation()
        self.test_auto_tune_endpoint()
        
        # Summary
        print("\n" + "=" * 70)
        print("BUG FIX TEST SUMMARY")
        print("=" * 70)
        
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
            print("🎉 All bug fix tests PASSED!")
        else:
            print("⚠️  Some bug fix tests FAILED!")
        
        return all_success

if __name__ == "__main__":
    tester = BugFixTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)