#!/usr/bin/env python3
"""
Backend Testing for Antenna Calculator App - Height Optimizer and Auto-Tune Fixes
Testing specific fixes as requested in the review.
"""

import requests
import json
import sys
from typing import Dict, Any

# Backend URL from frontend/.env
BASE_URL = "https://gamma-match-fix.preview.emergentagent.com/api"

def test_height_optimizer_fix():
    """
    Test the /api/optimize-height endpoint to verify:
    - Tests heights from 10' to 50' (use step=5 to save time)
    - Returns different optimal heights (NOT always 10')
    - Returns optimal_swr, optimal_gain, optimal_fb_ratio
    - The optimal height should have the best combined score (not just lowest SWR)
    """
    print("\n=== TESTING HEIGHT OPTIMIZER FIX ===")
    
    test_data = {
        "num_elements": 3,
        "elements": [
            {"element_type": "reflector", "length": 216, "diameter": 0.5, "position": 0},
            {"element_type": "driven", "length": 204, "diameter": 0.5, "position": 48},
            {"element_type": "director", "length": 195, "diameter": 0.5, "position": 96}
        ],
        "boom_diameter": 2,
        "boom_unit": "inches",
        "band": "11m_cb",
        "min_height": 10,
        "max_height": 50,
        "step": 5
    }
    
    try:
        response = requests.post(f"{BASE_URL}/optimize-height", json=test_data, timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ FAILED: Expected 200, got {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
        result = response.json()
        print(f"Response received: {json.dumps(result, indent=2)}")
        
        # Verify required fields
        required_fields = ["optimal_height", "optimal_swr", "optimal_gain", "optimal_fb_ratio", "heights_tested"]
        for field in required_fields:
            if field not in result:
                print(f"❌ FAILED: Missing required field '{field}'")
                return False
        
        optimal_height = result["optimal_height"]
        optimal_swr = result["optimal_swr"]
        optimal_gain = result["optimal_gain"]
        optimal_fb_ratio = result["optimal_fb_ratio"]
        heights_tested = result["heights_tested"]
        
        print(f"Optimal Height: {optimal_height}' (Expected: around 35', NOT 10')")
        print(f"Optimal SWR: {optimal_swr}")
        print(f"Optimal Gain: {optimal_gain} dBi")
        print(f"Optimal F/B Ratio: {optimal_fb_ratio} dB")
        print(f"Heights tested: {len(heights_tested)} heights")
        
        # Verify heights tested (should be 9 heights: 10, 15, 20, 25, 30, 35, 40, 45, 50)
        expected_heights = list(range(10, 51, 5))  # [10, 15, 20, 25, 30, 35, 40, 45, 50]
        actual_heights = [h["height"] for h in heights_tested]
        
        if len(heights_tested) != len(expected_heights):
            print(f"❌ FAILED: Expected {len(expected_heights)} heights tested, got {len(heights_tested)}")
            return False
            
        if actual_heights != expected_heights:
            print(f"❌ FAILED: Expected heights {expected_heights}, got {actual_heights}")
            return False
            
        # Critical test: Optimal height should NOT always be 10' (this was the bug)
        if optimal_height == 10:
            print(f"❌ CRITICAL ISSUE: Optimal height is 10' - this suggests the bug is NOT fixed!")
            print("The height optimizer should find better heights around 35' for this configuration")
            return False
        
        # Verify optimal height is reasonable (should be around 35' based on expected result)
        if not (25 <= optimal_height <= 45):
            print(f"⚠️  WARNING: Optimal height {optimal_height}' is outside expected range 25-45'")
        
        # Verify each height test has required fields
        for i, height_test in enumerate(heights_tested):
            required_test_fields = ["height", "swr", "gain", "fb_ratio", "score"]
            for field in required_test_fields:
                if field not in height_test:
                    print(f"❌ FAILED: Height test {i} missing field '{field}'")
                    return False
        
        # Verify the optimal height actually has the best score
        best_score_height = max(heights_tested, key=lambda x: x["score"])
        if best_score_height["height"] != optimal_height:
            print(f"❌ FAILED: Optimal height {optimal_height}' doesn't match best score height {best_score_height['height']}'")
            return False
        
        print(f"✅ HEIGHT OPTIMIZER FIX VERIFIED:")
        print(f"   - Tested {len(heights_tested)} heights from 10' to 50' with step=5")
        print(f"   - Optimal height is {optimal_height}' (NOT 10' - bug fixed!)")
        print(f"   - Returns all required performance metrics")
        print(f"   - Uses combined score (SWR + Gain + F/B) for optimization")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ FAILED: Network error - {e}")
        return False
    except Exception as e:
        print(f"❌ FAILED: Unexpected error - {e}")
        return False


def test_auto_tune_no_reflector():
    """
    Test the /api/auto-tune endpoint with use_reflector: false
    Expected: 
    - Should return only driven + directors (NO reflector element)
    - optimized_elements should have 3 elements: 1 driven + 2 directors
    - First element should be "driven" at position 0
    """
    print("\n=== TESTING AUTO-TUNE WITH NO REFLECTOR ===")
    
    test_data = {
        "num_elements": 3,
        "height_from_ground": 35,
        "height_unit": "ft",
        "boom_diameter": 2,
        "boom_unit": "inches",
        "band": "11m_cb",
        "use_reflector": False
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auto-tune", json=test_data, timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ FAILED: Expected 200, got {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
        result = response.json()
        print(f"Response received: {json.dumps(result, indent=2)}")
        
        # Verify required fields
        required_fields = ["optimized_elements", "predicted_swr", "predicted_gain", "predicted_fb_ratio", "optimization_notes"]
        for field in required_fields:
            if field not in result:
                print(f"❌ FAILED: Missing required field '{field}'")
                return False
        
        elements = result["optimized_elements"]
        predicted_swr = result["predicted_swr"]
        predicted_gain = result["predicted_gain"]
        predicted_fb_ratio = result["predicted_fb_ratio"]
        
        print(f"Number of elements: {len(elements)}")
        print(f"Predicted SWR: {predicted_swr}")
        print(f"Predicted Gain: {predicted_gain} dBi")
        print(f"Predicted F/B Ratio: {predicted_fb_ratio} dB")
        
        # Critical test: Should have exactly 3 elements
        if len(elements) != 3:
            print(f"❌ FAILED: Expected 3 elements, got {len(elements)}")
            return False
        
        # Critical test: NO reflector should be present
        element_types = [elem["element_type"] for elem in elements]
        if "reflector" in element_types:
            print(f"❌ CRITICAL ISSUE: Found reflector element when use_reflector=false!")
            print(f"Element types: {element_types}")
            return False
        
        # Critical test: Should have 1 driven + 2 directors
        driven_count = element_types.count("driven")
        director_count = element_types.count("director")
        
        if driven_count != 1:
            print(f"❌ FAILED: Expected 1 driven element, got {driven_count}")
            return False
            
        if director_count != 2:
            print(f"❌ FAILED: Expected 2 director elements, got {director_count}")
            return False
        
        # Critical test: First element should be "driven" at position 0
        first_element = elements[0]
        if first_element["element_type"] != "driven":
            print(f"❌ FAILED: First element should be 'driven', got '{first_element['element_type']}'")
            return False
            
        if first_element["position"] != 0:
            print(f"❌ FAILED: First element (driven) should be at position 0, got {first_element['position']}")
            return False
        
        # Verify element progression (directors should be at increasing positions)
        positions = [elem["position"] for elem in elements]
        if positions != sorted(positions):
            print(f"❌ FAILED: Elements not in position order: {positions}")
            return False
        
        print(f"✅ AUTO-TUNE NO REFLECTOR VERIFIED:")
        print(f"   - Returns 3 elements: 1 driven + 2 directors (NO reflector)")
        print(f"   - First element is 'driven' at position 0")
        print(f"   - Element types: {element_types}")
        print(f"   - Positions: {positions}")
        print(f"   - Predicted performance: SWR={predicted_swr}, Gain={predicted_gain}dBi, F/B={predicted_fb_ratio}dB")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ FAILED: Network error - {e}")
        return False
    except Exception as e:
        print(f"❌ FAILED: Unexpected error - {e}")
        return False


def test_auto_tune_with_reflector():
    """
    Test the /api/auto-tune endpoint without use_reflector (defaults to true)
    Expected:
    - Should return reflector + driven + director
    - First element should be "reflector" at position 0
    """
    print("\n=== TESTING AUTO-TUNE WITH REFLECTOR (DEFAULT) ===")
    
    test_data = {
        "num_elements": 3,
        "height_from_ground": 35,
        "height_unit": "ft",
        "boom_diameter": 2,
        "boom_unit": "inches",
        "band": "11m_cb"
        # Note: use_reflector not specified, should default to True
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auto-tune", json=test_data, timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ FAILED: Expected 200, got {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
        result = response.json()
        print(f"Response received: {json.dumps(result, indent=2)}")
        
        # Verify required fields
        required_fields = ["optimized_elements", "predicted_swr", "predicted_gain", "predicted_fb_ratio", "optimization_notes"]
        for field in required_fields:
            if field not in result:
                print(f"❌ FAILED: Missing required field '{field}'")
                return False
        
        elements = result["optimized_elements"]
        predicted_swr = result["predicted_swr"]
        predicted_gain = result["predicted_gain"]
        predicted_fb_ratio = result["predicted_fb_ratio"]
        
        print(f"Number of elements: {len(elements)}")
        print(f"Predicted SWR: {predicted_swr}")
        print(f"Predicted Gain: {predicted_gain} dBi")
        print(f"Predicted F/B Ratio: {predicted_fb_ratio} dB")
        
        # Critical test: Should have exactly 3 elements
        if len(elements) != 3:
            print(f"❌ FAILED: Expected 3 elements, got {len(elements)}")
            return False
        
        # Critical test: Should have reflector + driven + director
        element_types = [elem["element_type"] for elem in elements]
        expected_types = ["reflector", "driven", "director"]
        
        if sorted(element_types) != sorted(expected_types):
            print(f"❌ FAILED: Expected element types {expected_types}, got {element_types}")
            return False
        
        # Critical test: First element should be "reflector" at position 0
        first_element = elements[0]
        if first_element["element_type"] != "reflector":
            print(f"❌ FAILED: First element should be 'reflector', got '{first_element['element_type']}'")
            return False
            
        if first_element["position"] != 0:
            print(f"❌ FAILED: First element (reflector) should be at position 0, got {first_element['position']}")
            return False
        
        # Verify element progression (should be in position order)
        positions = [elem["position"] for elem in elements]
        if positions != sorted(positions):
            print(f"❌ FAILED: Elements not in position order: {positions}")
            return False
        
        # Verify reflector is longer than driven (typical Yagi design)
        reflector = next(e for e in elements if e["element_type"] == "reflector")
        driven = next(e for e in elements if e["element_type"] == "driven")
        director = next(e for e in elements if e["element_type"] == "director")
        
        if reflector["length"] <= driven["length"]:
            print(f"❌ FAILED: Reflector ({reflector['length']}\") should be longer than driven ({driven['length']}\")")
            return False
            
        if driven["length"] <= director["length"]:
            print(f"❌ FAILED: Driven ({driven['length']}\") should be longer than director ({director['length']}\")")
            return False
        
        print(f"✅ AUTO-TUNE WITH REFLECTOR VERIFIED:")
        print(f"   - Returns 3 elements: reflector + driven + director")
        print(f"   - First element is 'reflector' at position 0")
        print(f"   - Element types: {element_types}")
        print(f"   - Positions: {positions}")
        print(f"   - Element lengths: R={reflector['length']}\", D={driven['length']}\", Dir={director['length']}\"")
        print(f"   - Predicted performance: SWR={predicted_swr}, Gain={predicted_gain}dBi, F/B={predicted_fb_ratio}dB")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ FAILED: Network error - {e}")
        return False
    except Exception as e:
        print(f"❌ FAILED: Unexpected error - {e}")
        return False


def main():
    """Run all tests for the Antenna Calculator fixes"""
    print("🧪 ANTENNA CALCULATOR BACKEND TESTING - SPECIFIC FIXES")
    print(f"Backend URL: {BASE_URL}")
    print("=" * 60)
    
    tests = [
        ("Height Optimizer Fix", test_height_optimizer_fix),
        ("Auto-Tune No Reflector", test_auto_tune_no_reflector),
        ("Auto-Tune With Reflector", test_auto_tune_with_reflector),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} CRASHED: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\nTotal: {passed} passed, {failed} failed")
    
    if failed > 0:
        print("\n🚨 CRITICAL ISSUES FOUND - Some fixes are not working correctly!")
        sys.exit(1)
    else:
        print("\n🎉 ALL TESTS PASSED - All fixes are working correctly!")
        sys.exit(0)


if __name__ == "__main__":
    main()