#!/usr/bin/env python3
"""
Backend Testing for Antenna Calculator - No Reflector Mode Fixes
Testing specific scenarios requested in the review.
"""

import requests
import json
import sys
from typing import Dict, Any

# Backend URL from frontend .env
BACKEND_URL = "https://swr-optimizer.preview.emergentagent.com/api"

def test_calculate_no_reflector():
    """Test 1: Calculate with 3 elements WITHOUT reflector"""
    print("\n=== Test 1: Calculate with 3 elements WITHOUT reflector ===")
    
    payload = {
        "num_elements": 3,
        "elements": [
            {"element_type": "driven", "length": 204, "diameter": 0.5, "position": 0},
            {"element_type": "director", "length": 195, "diameter": 0.5, "position": 48},
            {"element_type": "director", "length": 190, "diameter": 0.5, "position": 96}
        ],
        "height_from_ground": 35,
        "height_unit": "ft",
        "boom_diameter": 2,
        "boom_unit": "inches",
        "band": "11m_cb"
    }
    
    try:
        response = requests.post(f"{BACKEND_URL}/calculate", json=payload, timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 500:
            print("❌ FAILED: Returned 500 error")
            print(f"Error: {response.text}")
            return False
        
        if response.status_code != 200:
            print(f"❌ FAILED: Unexpected status code {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
        data = response.json()
        
        # Check expected values
        gain = data.get("gain_dbi", 0)
        fb_ratio = data.get("fb_ratio", 0)
        far_field = data.get("far_field_pattern", [])
        
        print(f"✅ SUCCESS: No 500 error")
        print(f"Gain: {gain} dBi (expected ~9-10 dBi)")
        print(f"F/B Ratio: {fb_ratio} dB (expected ~8 dB)")
        
        # Check far-field pattern at specific angles
        pattern_90 = next((p["magnitude"] for p in far_field if p["angle"] == 90), None)
        pattern_180 = next((p["magnitude"] for p in far_field if p["angle"] == 180), None)
        
        if pattern_90 is not None:
            print(f"Far-field at 90°: {pattern_90}% (expected ~25%)")
        if pattern_180 is not None:
            print(f"Far-field at 180°: {pattern_180}% (expected ~40%)")
        
        # Validate ranges
        gain_ok = 8.5 <= gain <= 10.5
        fb_ok = 6 <= fb_ratio <= 10
        
        print(f"Gain in range (8.5-10.5): {'✅' if gain_ok else '❌'}")
        print(f"F/B in range (6-10): {'✅' if fb_ok else '❌'}")
        
        return gain_ok and fb_ok
        
    except Exception as e:
        print(f"❌ FAILED: Exception occurred: {e}")
        return False

def test_optimize_height_no_reflector():
    """Test 2: Optimize Height with 3 elements WITHOUT reflector"""
    print("\n=== Test 2: Optimize Height with 3 elements WITHOUT reflector ===")
    
    payload = {
        "num_elements": 3,
        "elements": [
            {"element_type": "driven", "length": 204, "diameter": 0.5, "position": 0},
            {"element_type": "director", "length": 195, "diameter": 0.5, "position": 48},
            {"element_type": "director", "length": 190, "diameter": 0.5, "position": 96}
        ],
        "boom_diameter": 2,
        "boom_unit": "inches",
        "band": "11m_cb",
        "min_height": 10,
        "max_height": 50,
        "step": 10
    }
    
    try:
        response = requests.post(f"{BACKEND_URL}/optimize-height", json=payload, timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 500:
            print("❌ FAILED: Returned 500 error")
            print(f"Error: {response.text}")
            return False
        
        if response.status_code != 200:
            print(f"❌ FAILED: Unexpected status code {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
        data = response.json()
        
        # Check required fields
        optimal_height = data.get("optimal_height")
        optimal_gain = data.get("optimal_gain")
        optimal_swr = data.get("optimal_swr")
        optimal_fb = data.get("optimal_fb_ratio")
        heights_tested = data.get("heights_tested", [])
        
        print(f"✅ SUCCESS: No 500 error")
        print(f"Optimal Height: {optimal_height}' (should not always be 10')")
        print(f"Optimal Gain: {optimal_gain} dBi")
        print(f"Optimal SWR: {optimal_swr}")
        print(f"Optimal F/B: {optimal_fb} dB")
        print(f"Heights tested: {len(heights_tested)}")
        
        # Check that optimal height is not always 10'
        height_not_always_10 = optimal_height != 10
        
        # Check that SWR values vary at different heights
        swr_values = [h.get("swr", 0) for h in heights_tested]
        swr_varies = len(set(swr_values)) > 1
        
        print(f"Optimal height not 10': {'✅' if height_not_always_10 else '❌'}")
        print(f"SWR varies across heights: {'✅' if swr_varies else '❌'}")
        
        if heights_tested:
            print("Heights tested details:")
            for h in heights_tested:
                print(f"  {h.get('height', 'N/A')}': SWR={h.get('swr', 'N/A')}, Gain={h.get('gain', 'N/A')}")
        
        return height_not_always_10 and swr_varies
        
    except Exception as e:
        print(f"❌ FAILED: Exception occurred: {e}")
        return False

def test_calculate_with_reflector():
    """Test 3: Compare WITH reflector to confirm difference"""
    print("\n=== Test 3: Calculate WITH reflector for comparison ===")
    
    payload = {
        "num_elements": 3,
        "elements": [
            {"element_type": "reflector", "length": 214, "diameter": 0.5, "position": 0},
            {"element_type": "driven", "length": 204, "diameter": 0.5, "position": 48},
            {"element_type": "director", "length": 195, "diameter": 0.5, "position": 96}
        ],
        "height_from_ground": 35,
        "height_unit": "ft",
        "boom_diameter": 2,
        "boom_unit": "inches",
        "band": "11m_cb"
    }
    
    try:
        response = requests.post(f"{BACKEND_URL}/calculate", json=payload, timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ FAILED: Status code {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
        data = response.json()
        
        gain = data.get("gain_dbi", 0)
        fb_ratio = data.get("fb_ratio", 0)
        
        print(f"✅ SUCCESS: With reflector calculation")
        print(f"Gain: {gain} dBi (expected ~11 dBi)")
        print(f"F/B Ratio: {fb_ratio} dB (expected ~20 dB)")
        
        # Validate ranges for with-reflector case
        gain_ok = 10.5 <= gain <= 12.0
        fb_ok = 18 <= fb_ratio <= 22
        
        print(f"Gain in range (10.5-12.0): {'✅' if gain_ok else '❌'}")
        print(f"F/B in range (18-22): {'✅' if fb_ok else '❌'}")
        
        return gain_ok and fb_ok
        
    except Exception as e:
        print(f"❌ FAILED: Exception occurred: {e}")
        return False

def test_backend_health():
    """Test basic backend connectivity"""
    print("\n=== Backend Health Check ===")
    
    try:
        response = requests.get(f"{BACKEND_URL}/", timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Backend is accessible")
            return True
        else:
            print(f"❌ Backend returned {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Backend not accessible: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing Antenna Calculator - No Reflector Mode Fixes")
    print(f"Backend URL: {BACKEND_URL}")
    
    results = []
    
    # Test backend connectivity first
    results.append(("Backend Health", test_backend_health()))
    
    # Run the specific tests requested
    results.append(("Calculate No Reflector", test_calculate_no_reflector()))
    results.append(("Optimize Height No Reflector", test_optimize_height_no_reflector()))
    results.append(("Calculate With Reflector", test_calculate_with_reflector()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())