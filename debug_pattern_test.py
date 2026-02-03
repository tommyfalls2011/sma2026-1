#!/usr/bin/env python3
"""
Debug test to examine the exact far-field pattern values
"""

import requests
import json

# Get backend URL from frontend environment
def get_backend_url():
    try:
        with open('/app/frontend/.env', 'r') as f:
            for line in f:
                if line.startswith('EXPO_PUBLIC_BACKEND_URL='):
                    base_url = line.split('=', 1)[1].strip().strip('"')
                    return f"{base_url}/api"
    except Exception as e:
        print(f"Error reading frontend .env: {e}")
    return "http://localhost:8001/api"

BACKEND_URL = get_backend_url()

def debug_patterns():
    """Debug the exact pattern values"""
    
    # Test 1: WITH Reflector (3 elements)
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
    
    # Test 2: WITHOUT Reflector (2 elements)
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
    
    print("Testing WITH reflector...")
    response1 = requests.post(f"{BACKEND_URL}/calculate", json=with_reflector_data)
    result1 = response1.json()
    
    print("Testing WITHOUT reflector...")
    response2 = requests.post(f"{BACKEND_URL}/calculate", json=without_reflector_data)
    result2 = response2.json()
    
    print("\n=== WITH REFLECTOR PATTERN ===")
    pattern1 = result1['far_field_pattern']
    key_angles = [0, 45, 90, 135, 180, 225, 270, 315]
    for angle in key_angles:
        magnitude = next((p['magnitude'] for p in pattern1 if p['angle'] == angle), None)
        print(f"Angle {angle:3d}°: {magnitude:5.1f}%")
    
    print("\n=== WITHOUT REFLECTOR PATTERN ===")
    pattern2 = result2['far_field_pattern']
    for angle in key_angles:
        magnitude = next((p['magnitude'] for p in pattern2 if p['angle'] == angle), None)
        print(f"Angle {angle:3d}°: {magnitude:5.1f}%")
    
    print("\n=== COMPARISON ===")
    print(f"Gain: {result1['gain_dbi']:.1f} vs {result2['gain_dbi']:.1f} dBi")
    print(f"F/B:  {result1['fb_ratio']:.1f} vs {result2['fb_ratio']:.1f} dB")
    
    # Check if patterns are actually different
    angles_to_check = [90, 135, 180, 225, 270]
    differences = []
    for angle in angles_to_check:
        mag1 = next((p['magnitude'] for p in pattern1 if p['angle'] == angle), None)
        mag2 = next((p['magnitude'] for p in pattern2 if p['angle'] == angle), None)
        diff = abs(mag1 - mag2)
        differences.append(diff)
        print(f"Angle {angle:3d}°: {mag1:5.1f}% vs {mag2:5.1f}% (diff: {diff:5.1f}%)")
    
    avg_diff = sum(differences) / len(differences)
    print(f"\nAverage difference in back/side angles: {avg_diff:.1f}%")
    
    if avg_diff > 10:
        print("✅ Patterns are significantly different")
    else:
        print("❌ Patterns are too similar")

if __name__ == "__main__":
    debug_patterns()