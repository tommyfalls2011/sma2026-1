#!/usr/bin/env python3
"""
Far-Field Pattern Fix Testing for Antenna Calculator
Tests the specific fix for far-field radiation patterns with/without reflector
"""

import requests
import json
import sys
from typing import Dict, List

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

def test_far_field_pattern_fix():
    """Test the far-field pattern changes based on reflector presence"""
    print("=" * 80)
    print("TESTING FAR-FIELD PATTERN FIX")
    print("=" * 80)
    
    # Test 1: WITH Reflector (3 elements)
    print("\n🔍 TEST 1: WITH REFLECTOR (3 elements)")
    print("-" * 50)
    
    with_reflector_data = {
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
    
    try:
        response1 = requests.post(f"{BACKEND_URL}/calculate", json=with_reflector_data, timeout=30)
        if response1.status_code != 200:
            print(f"❌ FAILED: HTTP {response1.status_code}")
            print(f"Response: {response1.text}")
            return False
            
        result1 = response1.json()
        
        print(f"✅ Request successful")
        print(f"📊 Gain: {result1['gain_dbi']} dBi (Expected: ~11 dBi)")
        print(f"📊 F/B Ratio: {result1['fb_ratio']} dB (Expected: ~20 dB)")
        print(f"📊 SWR: {result1['swr']}:1")
        
        # Check far-field pattern at key angles
        pattern1 = result1['far_field_pattern']
        pattern_180 = next((p['magnitude'] for p in pattern1 if p['angle'] == 180), None)
        pattern_90 = next((p['magnitude'] for p in pattern1 if p['angle'] == 90), None)
        pattern_0 = next((p['magnitude'] for p in pattern1 if p['angle'] == 0), None)
        
        print(f"📊 Far-field at 0°: {pattern_0}% (Forward direction)")
        print(f"📊 Far-field at 90°: {pattern_90}% (Expected: ~1%)")
        print(f"📊 Far-field at 180°: {pattern_180}% (Expected: ~10%)")
        
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        return False
    
    # Test 2: WITHOUT Reflector (2 elements)
    print("\n🔍 TEST 2: WITHOUT REFLECTOR (2 elements)")
    print("-" * 50)
    
    without_reflector_data = {
        "num_elements": 2,
        "elements": [
            {"element_type": "driven", "length": 204, "diameter": 0.5, "position": 0},
            {"element_type": "director", "length": 195, "diameter": 0.5, "position": 48}
        ],
        "height_from_ground": 35,
        "height_unit": "ft",
        "boom_diameter": 2,
        "boom_unit": "inches",
        "band": "11m_cb"
    }
    
    try:
        response2 = requests.post(f"{BACKEND_URL}/calculate", json=without_reflector_data, timeout=30)
        if response2.status_code != 200:
            print(f"❌ FAILED: HTTP {response2.status_code}")
            print(f"Response: {response2.text}")
            return False
            
        result2 = response2.json()
        
        print(f"✅ Request successful")
        print(f"📊 Gain: {result2['gain_dbi']} dBi (Expected: ~6-7 dBi, LESS than with reflector)")
        print(f"📊 F/B Ratio: {result2['fb_ratio']} dB (Expected: ~6 dB, MUCH WORSE than with reflector)")
        print(f"📊 SWR: {result2['swr']}:1")
        
        # Check far-field pattern at key angles
        pattern2 = result2['far_field_pattern']
        pattern2_180 = next((p['magnitude'] for p in pattern2 if p['angle'] == 180), None)
        pattern2_90 = next((p['magnitude'] for p in pattern2 if p['angle'] == 90), None)
        pattern2_0 = next((p['magnitude'] for p in pattern2 if p['angle'] == 0), None)
        
        print(f"📊 Far-field at 0°: {pattern2_0}% (Forward direction)")
        print(f"📊 Far-field at 90°: {pattern2_90}% (Expected: HIGHER than with reflector)")
        print(f"📊 Far-field at 180°: {pattern2_180}%")
        
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        return False
    
    # Compare Results
    print("\n🔍 COMPARISON ANALYSIS")
    print("-" * 50)
    
    gain_diff = result1['gain_dbi'] - result2['gain_dbi']
    fb_diff = result1['fb_ratio'] - result2['fb_ratio']
    pattern_90_diff = pattern2_90 - pattern_90
    pattern_180_diff = pattern_180 - pattern2_180
    
    print(f"📈 Gain difference: {gain_diff:.1f} dB (With reflector should be higher)")
    print(f"📈 F/B difference: {fb_diff:.1f} dB (With reflector should be much better)")
    print(f"📈 90° pattern difference: {pattern_90_diff:.1f}% (Without reflector should be higher)")
    print(f"📈 180° pattern difference: {pattern_180_diff:.1f}% (With reflector should have better back rejection)")
    
    # Validation
    success = True
    issues = []
    
    # Check gain expectations
    if result1['gain_dbi'] < 9 or result1['gain_dbi'] > 13:
        issues.append(f"With reflector gain {result1['gain_dbi']} dBi not in expected range 9-13 dBi")
        
    if result2['gain_dbi'] < 5 or result2['gain_dbi'] > 8:
        issues.append(f"Without reflector gain {result2['gain_dbi']} dBi not in expected range 5-8 dBi")
        
    if gain_diff < 1:
        issues.append(f"Gain difference {gain_diff:.1f} dB too small - reflector should provide significant gain boost")
    
    # Check F/B expectations  
    if result1['fb_ratio'] < 15 or result1['fb_ratio'] > 25:
        issues.append(f"With reflector F/B {result1['fb_ratio']} dB not in expected range 15-25 dB")
        
    if result2['fb_ratio'] < 4 or result2['fb_ratio'] > 10:
        issues.append(f"Without reflector F/B {result2['fb_ratio']} dB not in expected range 4-10 dB")
        
    if fb_diff < 8:
        issues.append(f"F/B difference {fb_diff:.1f} dB too small - reflector should dramatically improve F/B")
    
    # Check pattern differences - key validation for the fix
    if pattern_90_diff < 5:
        issues.append(f"90° pattern difference {pattern_90_diff:.1f}% too small - without reflector should be more omnidirectional")
    
    # Check that patterns are actually different
    if abs(pattern_180_diff) < 5:
        issues.append(f"180° patterns too similar ({pattern_180}% vs {pattern2_180}%) - should be significantly different")
    
    # Check specific pattern expectations
    if pattern_90 > 5:  # With reflector, side lobes should be very low
        issues.append(f"With reflector, 90° pattern {pattern_90}% too high - should be ~1%")
        
    if pattern2_90 < 15:  # Without reflector, should be more omnidirectional
        issues.append(f"Without reflector, 90° pattern {pattern2_90}% too low - should be higher (more omnidirectional)")
    
    # Check back rejection with reflector
    if pattern_180 > 15:  # With reflector, back should be well suppressed
        issues.append(f"With reflector, 180° pattern {pattern_180}% too high - should be ~10% or less")
    
    if issues:
        print(f"\n❌ VALIDATION ISSUES FOUND:")
        for issue in issues:
            print(f"   • {issue}")
        success = False
    else:
        print(f"\n✅ ALL VALIDATIONS PASSED")
        print(f"   • Patterns are significantly different")
        print(f"   • Reflector provides expected performance boost")
        print(f"   • Far-field pattern fix is working correctly")
        print(f"   • With reflector: Cardioid pattern (good F/B, low side lobes)")
        print(f"   • Without reflector: More omnidirectional (higher side lobes, poor F/B)")
    
    return success

def test_basic_api_connectivity():
    """Test basic API connectivity"""
    print("🔍 Testing API connectivity...")
    
    try:
        response = requests.get(f"{BACKEND_URL}/", timeout=10)
        if response.status_code == 200:
            print("✅ API is accessible")
            return True
        else:
            print(f"❌ API returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API connectivity failed: {str(e)}")
        return False

def main():
    """Main test runner"""
    print("🚀 Starting Far-Field Pattern Fix Testing")
    print(f"🌐 Backend URL: {BACKEND_URL}")
    
    # Test API connectivity first
    if not test_basic_api_connectivity():
        print("❌ Cannot proceed - API not accessible")
        sys.exit(1)
    
    # Run the main test
    success = test_far_field_pattern_fix()
    
    if success:
        print("\n🎉 ALL TESTS PASSED - Far-field pattern fix is working correctly!")
        print("   The antenna patterns are properly differentiated based on reflector presence.")
        sys.exit(0)
    else:
        print("\n💥 TESTS FAILED - Issues found with far-field pattern fix")
        print("   The patterns may not be sufficiently different or outside expected ranges.")
        sys.exit(1)

if __name__ == "__main__":
    main()