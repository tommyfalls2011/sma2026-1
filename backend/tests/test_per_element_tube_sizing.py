"""
Test per-element tube sizing in get_gamma_hardware_defaults() and global optimizer sweep.

Changes verified:
1. get_gamma_hardware_defaults now returns:
   - 2-el: tube=4.0", teflon=5.0", max_insertion=3.5"
   - 3-el: tube=3.5", teflon=4.5", max_insertion=3.0"
   - 4+ el: tube=3.0", teflon=4.0", max_insertion=2.5"

2. Optimizer ALWAYS sweeps full bar range from bar_min to rod_length to find global best SWR
   (was only sweeping when null wasn't reachable)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Expected tube sizing per element count
EXPECTED_TUBE_SIZING = {
    2: {"tube": 4.0, "teflon": 5.0, "max_insertion": 3.5},
    3: {"tube": 3.5, "teflon": 4.5, "max_insertion": 3.0},
    4: {"tube": 3.0, "teflon": 4.0, "max_insertion": 2.5},
    5: {"tube": 3.0, "teflon": 4.0, "max_insertion": 2.5},
    6: {"tube": 3.0, "teflon": 4.0, "max_insertion": 2.5},
    8: {"tube": 3.0, "teflon": 4.0, "max_insertion": 2.5},
    20: {"tube": 3.0, "teflon": 4.0, "max_insertion": 2.5},
}


def get_standard_elements(num_elements: int, driven_length: float = 203.0):
    """Generate standard Yagi element layout for testing."""
    elements = []
    # Reflector at position 0
    elements.append({
        "element_type": "reflector",
        "position": 0,
        "length": 214.0,
        "diameter": 0.5
    })
    # Driven at position 48
    elements.append({
        "element_type": "driven",
        "position": 48,
        "length": driven_length,
        "diameter": 0.5
    })
    # Directors at 48" spacing
    for i in range(num_elements - 2):
        elements.append({
            "element_type": "director",
            "position": 96 + i * 48,
            "length": 192.0 - i * 2,
            "diameter": 0.5
        })
    return elements


class TestGammaDesignerPerElementTubeSizing:
    """Test tube sizing defaults from /api/gamma-designer for different element counts."""

    def test_2_element_tube_4_inches(self):
        """2-element: tube=4.0", teflon=5.0", max_insertion=3.5"."""
        response = requests.post(f"{BASE_URL}/api/gamma-designer", json={
            "num_elements": 2,
            "driven_element_length_in": 203.0,
            "frequency_mhz": 27.185,
            "elements": get_standard_elements(2)
        })
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        recipe = data.get("recipe", {})
        expected = EXPECTED_TUBE_SIZING[2]
        
        assert recipe.get("tube_length") == expected["tube"], \
            f"2-el tube should be {expected['tube']}, got {recipe.get('tube_length')}"
        assert recipe.get("teflon_length") == expected["teflon"], \
            f"2-el teflon should be {expected['teflon']}, got {recipe.get('teflon_length')}"
        assert recipe.get("max_insertion") == expected["max_insertion"], \
            f"2-el max_insertion should be {expected['max_insertion']}, got {recipe.get('max_insertion')}"
        
        # Check SWR is reasonable for 2-element (~1.1 expected)
        swr = data.get("swr_at_null", data.get("swr", 99))
        assert 1.0 <= swr <= 1.2, f"2-el SWR should be ~1.1, got {swr}"
        print(f"✓ 2-el: tube={recipe.get('tube_length')}, teflon={recipe.get('teflon_length')}, max_ins={recipe.get('max_insertion')}, SWR={swr}")

    def test_3_element_tube_3_5_inches(self):
        """3-element: tube=3.5", teflon=4.5", max_insertion=3.0"."""
        response = requests.post(f"{BASE_URL}/api/gamma-designer", json={
            "num_elements": 3,
            "driven_element_length_in": 203.0,
            "frequency_mhz": 27.185,
            "elements": get_standard_elements(3)
        })
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        recipe = data.get("recipe", {})
        expected = EXPECTED_TUBE_SIZING[3]
        
        assert recipe.get("tube_length") == expected["tube"], \
            f"3-el tube should be {expected['tube']}, got {recipe.get('tube_length')}"
        assert recipe.get("teflon_length") == expected["teflon"], \
            f"3-el teflon should be {expected['teflon']}, got {recipe.get('teflon_length')}"
        assert recipe.get("max_insertion") == expected["max_insertion"], \
            f"3-el max_insertion should be {expected['max_insertion']}, got {recipe.get('max_insertion')}"
        
        # Check SWR is ~1.02 for 3-element (closer to null)
        swr = data.get("swr_at_null", data.get("swr", 99))
        assert 1.0 <= swr <= 1.1, f"3-el SWR should be ~1.02, got {swr}"
        print(f"✓ 3-el: tube={recipe.get('tube_length')}, teflon={recipe.get('teflon_length')}, max_ins={recipe.get('max_insertion')}, SWR={swr}")

    def test_4_element_tube_3_inches(self):
        """4-element: tube=3.0", teflon=4.0", max_insertion=2.5"."""
        response = requests.post(f"{BASE_URL}/api/gamma-designer", json={
            "num_elements": 4,
            "driven_element_length_in": 203.0,
            "frequency_mhz": 27.185,
            "elements": get_standard_elements(4)
        })
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        recipe = data.get("recipe", {})
        expected = EXPECTED_TUBE_SIZING[4]
        
        assert recipe.get("tube_length") == expected["tube"], \
            f"4-el tube should be {expected['tube']}, got {recipe.get('tube_length')}"
        assert recipe.get("teflon_length") == expected["teflon"], \
            f"4-el teflon should be {expected['teflon']}, got {recipe.get('teflon_length')}"
        assert recipe.get("max_insertion") == expected["max_insertion"], \
            f"4-el max_insertion should be {expected['max_insertion']}, got {recipe.get('max_insertion')}"
        
        # Check SWR is ~1.01 or better
        swr = data.get("swr_at_null", data.get("swr", 99))
        assert 1.0 <= swr <= 1.05, f"4-el SWR should be ~1.01, got {swr}"
        null_reachable = data.get("null_reachable", None)
        print(f"✓ 4-el: tube={recipe.get('tube_length')}, teflon={recipe.get('teflon_length')}, max_ins={recipe.get('max_insertion')}, SWR={swr}, null_reachable={null_reachable}")

    def test_6_element_tube_3_inches(self):
        """6-element: tube=3.0", teflon=4.0", max_insertion=2.5", SWR≈1.0."""
        response = requests.post(f"{BASE_URL}/api/gamma-designer", json={
            "num_elements": 6,
            "driven_element_length_in": 203.0,
            "frequency_mhz": 27.185,
            "elements": get_standard_elements(6)
        })
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        recipe = data.get("recipe", {})
        expected = EXPECTED_TUBE_SIZING[6]
        
        assert recipe.get("tube_length") == expected["tube"], \
            f"6-el tube should be {expected['tube']}, got {recipe.get('tube_length')}"
        assert recipe.get("teflon_length") == expected["teflon"], \
            f"6-el teflon should be {expected['teflon']}, got {recipe.get('teflon_length')}"
        
        # 6+ elements should reach null with SWR≈1.0
        swr = data.get("swr_at_null", data.get("swr", 99))
        assert 1.0 <= swr <= 1.03, f"6-el SWR should be ≈1.0, got {swr}"
        null_reachable = data.get("null_reachable", False)
        assert null_reachable == True, f"6-el should have null_reachable=True, got {null_reachable}"
        print(f"✓ 6-el: tube={recipe.get('tube_length')}, SWR={swr}, null_reachable={null_reachable}")

    def test_8_element_tube_3_inches(self):
        """8-element: tube=3.0", SWR≈1.0, null_reachable=True."""
        response = requests.post(f"{BASE_URL}/api/gamma-designer", json={
            "num_elements": 8,
            "driven_element_length_in": 203.0,
            "frequency_mhz": 27.185,
            "elements": get_standard_elements(8)
        })
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        recipe = data.get("recipe", {})
        expected = EXPECTED_TUBE_SIZING[8]
        
        assert recipe.get("tube_length") == expected["tube"]
        
        swr = data.get("swr_at_null", data.get("swr", 99))
        assert 1.0 <= swr <= 1.02, f"8-el SWR should be ≈1.0, got {swr}"
        null_reachable = data.get("null_reachable", False)
        assert null_reachable == True, f"8-el should have null_reachable=True"
        print(f"✓ 8-el: tube={recipe.get('tube_length')}, SWR={swr}, null_reachable={null_reachable}")

    def test_20_element_tube_3_inches(self):
        """20-element: tube=3.0", SWR≈1.0, null_reachable=True."""
        response = requests.post(f"{BASE_URL}/api/gamma-designer", json={
            "num_elements": 20,
            "driven_element_length_in": 203.0,
            "frequency_mhz": 27.185,
            "elements": get_standard_elements(20)
        })
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        recipe = data.get("recipe", {})
        expected = EXPECTED_TUBE_SIZING[20]
        
        assert recipe.get("tube_length") == expected["tube"]
        
        swr = data.get("swr_at_null", data.get("swr", 99))
        assert 1.0 <= swr <= 1.02, f"20-el SWR should be ≈1.0, got {swr}"
        null_reachable = data.get("null_reachable", False)
        assert null_reachable == True, f"20-el should have null_reachable=True"
        print(f"✓ 20-el: tube={recipe.get('tube_length')}, SWR={swr}, null_reachable={null_reachable}")


class TestCalculateEndpointPerElementTubeSizing:
    """Test tube sizing in /api/calculate hardware defaults."""

    def test_calculate_2_element_hardware(self):
        """2-element: hardware.tube_length=4.0", teflon=5.0", max_insertion=3.5"."""
        response = requests.post(f"{BASE_URL}/api/calculate", json={
            "num_elements": 2,
            "frequency_mhz": 27.185,
            "height_from_ground": 35,
            "height_unit": "ft",
            "boom_diameter": 2.0,
            "boom_unit": "inches",
            "boom_grounded": True,
            "feed_type": "gamma",
            "elements": get_standard_elements(2)
        })
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        matching = data.get("matching", {})
        hardware = matching.get("hardware", {})
        
        expected = EXPECTED_TUBE_SIZING[2]
        assert hardware.get("tube_length") == expected["tube"], \
            f"2-el hardware.tube_length should be {expected['tube']}, got {hardware.get('tube_length')}"
        assert hardware.get("teflon_length") == expected["teflon"], \
            f"2-el hardware.teflon_length should be {expected['teflon']}, got {hardware.get('teflon_length')}"
        print(f"✓ /api/calculate 2-el: tube={hardware.get('tube_length')}, teflon={hardware.get('teflon_length')}")

    def test_calculate_3_element_hardware(self):
        """3-element: hardware.tube_length=3.5", teflon=4.5"."""
        response = requests.post(f"{BASE_URL}/api/calculate", json={
            "num_elements": 3,
            "frequency_mhz": 27.185,
            "height_from_ground": 35,
            "height_unit": "ft",
            "boom_diameter": 2.0,
            "boom_unit": "inches",
            "boom_grounded": True,
            "feed_type": "gamma",
            "elements": get_standard_elements(3)
        })
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        matching = data.get("matching", {})
        hardware = matching.get("hardware", {})
        
        expected = EXPECTED_TUBE_SIZING[3]
        assert hardware.get("tube_length") == expected["tube"], \
            f"3-el hardware.tube_length should be {expected['tube']}, got {hardware.get('tube_length')}"
        assert hardware.get("teflon_length") == expected["teflon"], \
            f"3-el hardware.teflon_length should be {expected['teflon']}, got {hardware.get('teflon_length')}"
        print(f"✓ /api/calculate 3-el: tube={hardware.get('tube_length')}, teflon={hardware.get('teflon_length')}")

    def test_calculate_6_element_hardware(self):
        """6-element: hardware.tube_length=3.0", teflon=4.0"."""
        response = requests.post(f"{BASE_URL}/api/calculate", json={
            "num_elements": 6,
            "frequency_mhz": 27.185,
            "height_from_ground": 35,
            "height_unit": "ft",
            "boom_diameter": 2.0,
            "boom_unit": "inches",
            "boom_grounded": True,
            "feed_type": "gamma",
            "elements": get_standard_elements(6)
        })
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        matching = data.get("matching", {})
        hardware = matching.get("hardware", {})
        
        expected = EXPECTED_TUBE_SIZING[6]
        assert hardware.get("tube_length") == expected["tube"], \
            f"6-el hardware.tube_length should be {expected['tube']}, got {hardware.get('tube_length')}"
        assert hardware.get("teflon_length") == expected["teflon"], \
            f"6-el hardware.teflon_length should be {expected['teflon']}, got {hardware.get('teflon_length')}"
        print(f"✓ /api/calculate 6-el: tube={hardware.get('tube_length')}, teflon={hardware.get('teflon_length')}")


class TestCustomTubeLengthOverride:
    """Test custom_tube_length override in gamma designer."""

    def test_custom_tube_matches_default_for_2_el(self):
        """custom_tube_length=4.0 for 2-el should match default (both tube=4.0)."""
        # First get default
        default_response = requests.post(f"{BASE_URL}/api/gamma-designer", json={
            "num_elements": 2,
            "driven_element_length_in": 203.0,
            "frequency_mhz": 27.185,
            "elements": get_standard_elements(2)
        })
        assert default_response.status_code == 200
        default_data = default_response.json()
        default_swr = default_data.get("swr_at_null", default_data.get("swr", 99))
        
        # Now with explicit custom_tube_length=4.0 (same as default)
        custom_response = requests.post(f"{BASE_URL}/api/gamma-designer", json={
            "num_elements": 2,
            "driven_element_length_in": 203.0,
            "frequency_mhz": 27.185,
            "custom_tube_length": 4.0,
            "elements": get_standard_elements(2)
        })
        assert custom_response.status_code == 200
        custom_data = custom_response.json()
        custom_swr = custom_data.get("swr_at_null", custom_data.get("swr", 99))
        
        # Both should have tube=4.0
        assert default_data.get("recipe", {}).get("tube_length") == 4.0
        assert custom_data.get("recipe", {}).get("tube_length") == 4.0
        
        # SWR should be similar (within 0.01)
        assert abs(default_swr - custom_swr) < 0.01, \
            f"Default SWR {default_swr} should match custom SWR {custom_swr}"
        print(f"✓ Custom tube=4.0 matches default for 2-el: default_swr={default_swr}, custom_swr={custom_swr}")


class TestOptimizerSweepConsistency:
    """Test that optimizer sweeps full bar range and finds best global SWR."""

    def test_optimizer_finds_best_swr_2_element(self):
        """2-element: optimizer finds best SWR even if null not reachable."""
        response = requests.post(f"{BASE_URL}/api/gamma-designer", json={
            "num_elements": 2,
            "driven_element_length_in": 203.0,
            "frequency_mhz": 27.185,
            "elements": get_standard_elements(2)
        })
        assert response.status_code == 200
        data = response.json()
        
        swr = data.get("swr_at_null", data.get("swr", 99))
        null_reachable = data.get("null_reachable", None)
        bar_position = data.get("bar_position", data.get("recipe", {}).get("bar_position"))
        insertion = data.get("optimal_insertion", data.get("insertion_inches"))
        
        # For 2-element, null may not be reachable but SWR should still be ~1.1
        print(f"2-el optimizer result: SWR={swr}, null_reachable={null_reachable}, bar={bar_position}, ins={insertion}")
        
        # SWR should be reasonable (optimizer found good solution)
        assert swr <= 1.2, f"2-el SWR should be ≤1.2, got {swr}"
        
        # Check bar_sweep exists (optimizer ran)
        bar_sweep = data.get("bar_sweep", [])
        assert len(bar_sweep) > 0, "bar_sweep should be populated"
        
        # Check insertion_sweep exists
        ins_sweep = data.get("insertion_sweep", [])
        assert len(ins_sweep) > 0, "insertion_sweep should be populated"
        print(f"✓ 2-el optimizer sweep: {len(bar_sweep)} bar points, {len(ins_sweep)} insertion points")

    def test_no_swr_jumps_when_tube_changes(self):
        """Verify SWR scales smoothly when tube length changes between element counts."""
        swr_values = {}
        
        for n in [2, 3, 4, 5, 6]:
            response = requests.post(f"{BASE_URL}/api/gamma-designer", json={
                "num_elements": n,
                "driven_element_length_in": 203.0,
                "frequency_mhz": 27.185,
                "elements": get_standard_elements(n)
            })
            assert response.status_code == 200
            data = response.json()
            swr = data.get("swr_at_null", data.get("swr", 99))
            swr_values[n] = swr
            print(f"  {n}-el: SWR={swr}")
        
        # Check no sudden jumps > 0.2 between adjacent element counts
        for i in range(2, 6):
            delta = abs(swr_values[i] - swr_values[i+1])
            assert delta <= 0.2, f"SWR jump from {i}-el to {i+1}-el is {delta}, should be ≤0.2"
        
        # SWR should generally decrease as elements increase (better match)
        assert swr_values[6] <= swr_values[2], \
            f"6-el SWR ({swr_values[6]}) should be ≤ 2-el SWR ({swr_values[2]})"
        print(f"✓ No SWR jumps: {swr_values}")


class TestExpectedSWRValues:
    """Test expected SWR values per element count as specified."""

    def test_expected_swr_ranges(self):
        """Verify expected SWR ranges:
        - 2-el: SWR≈1.106 (or ~1.1)
        - 3-el: SWR≈1.024 (or ~1.02)
        - 4-el: SWR≈1.008 (or ~1.01)
        - 5+ el: SWR≈1.0-1.005
        """
        expected_ranges = {
            2: (1.05, 1.15),  # ~1.106
            3: (1.0, 1.05),   # ~1.024
            4: (1.0, 1.02),   # ~1.008
            5: (1.0, 1.01),   # ~1.0-1.005
            6: (1.0, 1.01),   # ~1.0
        }
        
        for n, (min_swr, max_swr) in expected_ranges.items():
            response = requests.post(f"{BASE_URL}/api/gamma-designer", json={
                "num_elements": n,
                "driven_element_length_in": 203.0,
                "frequency_mhz": 27.185,
                "elements": get_standard_elements(n)
            })
            assert response.status_code == 200, f"{n}-el request failed: {response.text}"
            data = response.json()
            swr = data.get("swr_at_null", data.get("swr", 99))
            
            assert min_swr <= swr <= max_swr, \
                f"{n}-el SWR={swr} not in expected range [{min_swr}, {max_swr}]"
            print(f"✓ {n}-el SWR={swr} in range [{min_swr}, {max_swr}]")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
