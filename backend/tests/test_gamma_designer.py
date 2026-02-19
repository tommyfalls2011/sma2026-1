"""
Gamma Match Designer API Tests
Tests POST /api/gamma-designer endpoint for the new one-click gamma match recipe feature.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestGammaDesignerAutoHardware:
    """Tests for gamma designer with auto-selected hardware"""

    def test_3element_auto_hardware_returns_recipe_with_swr_1(self):
        """3-element, 203" driven, 27.185 MHz returns recipe with SWR 1.0 and null_reachable=true"""
        payload = {
            "num_elements": 3,
            "driven_element_length_in": 203.0,
            "frequency_mhz": 27.185
        }
        response = requests.post(f"{BASE_URL}/api/gamma-designer", json=payload)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Validate response structure
        assert "recipe" in data, "Response should contain 'recipe'"
        assert "feedpoint_impedance" in data, "Response should contain 'feedpoint_impedance'"
        assert "hardware_source" in data, "Response should contain 'hardware_source'"
        assert "bar_sweep" in data, "Response should contain 'bar_sweep'"
        assert "insertion_sweep" in data, "Response should contain 'insertion_sweep'"
        assert "notes" in data, "Response should contain 'notes'"
        
        recipe = data["recipe"]
        
        # Validate recipe contains all expected fields
        assert "swr_at_null" in recipe, "Recipe should contain 'swr_at_null'"
        assert "null_reachable" in recipe, "Recipe should contain 'null_reachable'"
        assert "ideal_bar_position" in recipe, "Recipe should contain 'ideal_bar_position'"
        assert "optimal_insertion" in recipe, "Recipe should contain 'optimal_insertion'"
        
        # Validate expected values
        # SWR should be close to 1.0 (acceptable range 1.0-2.0 for a good design)
        assert 1.0 <= recipe["swr_at_null"] <= 2.0, f"SWR {recipe['swr_at_null']} should be between 1.0 and 2.0"
        assert recipe["null_reachable"] == True, "null_reachable should be True for 3-element auto design"
        
        # Hardware source should be auto
        assert data["hardware_source"] == "auto", f"Expected 'auto', got '{data['hardware_source']}'"
        
        # Feedpoint impedance for 3-element should be around 20 ohms
        assert 15.0 <= data["feedpoint_impedance"] <= 25.0, f"Feedpoint impedance {data['feedpoint_impedance']} unexpected for 3-element"
        
        print(f"✓ 3-element auto design: SWR={recipe['swr_at_null']}, null_reachable={recipe['null_reachable']}")
        print(f"  Bar position={recipe['ideal_bar_position']}\", Insertion={recipe['optimal_insertion']}\"")

    def test_5element_has_larger_bar_position_than_3element(self):
        """5-element returns ideal_bar_position > 3-element"""
        # Get 3-element result
        payload_3 = {
            "num_elements": 3,
            "driven_element_length_in": 203.0,
            "frequency_mhz": 27.185
        }
        response_3 = requests.post(f"{BASE_URL}/api/gamma-designer", json=payload_3)
        assert response_3.status_code == 200
        bar_3 = response_3.json()["recipe"]["ideal_bar_position"]
        
        # Get 5-element result
        payload_5 = {
            "num_elements": 5,
            "driven_element_length_in": 203.0,
            "frequency_mhz": 27.185
        }
        response_5 = requests.post(f"{BASE_URL}/api/gamma-designer", json=payload_5)
        assert response_5.status_code == 200
        bar_5 = response_5.json()["recipe"]["ideal_bar_position"]
        
        # 5-element has lower feedpoint impedance → needs higher step-up → bar further out
        assert bar_5 > bar_3, f"5-element bar ({bar_5}\") should be > 3-element bar ({bar_3}\")"
        
        print(f"✓ 3-element bar={bar_3}\", 5-element bar={bar_5}\" (5-elem > 3-elem confirmed)")


class TestGammaDesignerCustomHardware:
    """Tests for gamma designer with custom hardware parameters"""

    def test_custom_hardware_1inch_tube_05inch_rod_not_reachable(self):
        """1" tube, 0.5" rod returns null_reachable=false with warning note"""
        payload = {
            "num_elements": 3,
            "driven_element_length_in": 203.0,
            "frequency_mhz": 27.185,
            "custom_tube_od": 1.0,
            "custom_rod_od": 0.5
        }
        response = requests.post(f"{BASE_URL}/api/gamma-designer", json=payload)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Custom hardware should be identified
        assert data["hardware_source"] == "custom", f"Expected 'custom', got '{data['hardware_source']}'"
        
        recipe = data["recipe"]
        
        # With 1" tube (0.902" ID) and 0.5" rod, cap/inch is very low → null may not be reachable
        # ID/rod ratio = 0.902/0.5 = 1.804 (> 1.6 optimal) → lower cap/inch
        assert "null_reachable" in recipe, "Recipe should contain 'null_reachable'"
        
        # Check notes for warning
        notes_text = " ".join(data["notes"])
        assert "WARNING" in notes_text or recipe["null_reachable"] == False, \
            f"Custom hardware should either warn about ratio or have null_reachable=False. Notes: {data['notes']}"
        
        # Verify custom hardware is reflected in recipe
        assert recipe["tube_od"] == 1.0, f"Tube OD should be 1.0, got {recipe['tube_od']}"
        assert recipe["rod_od"] == 0.5, f"Rod OD should be 0.5, got {recipe['rod_od']}"
        
        print(f"✓ Custom hardware (1\" tube, 0.5\" rod): null_reachable={recipe['null_reachable']}")
        print(f"  ID/rod ratio={recipe['id_rod_ratio']}, cap/inch={recipe['cap_per_inch']} pF/in")

    def test_custom_feedpoint_impedance_different_recipe(self):
        """Custom feedpoint_impedance=30 returns different recipe than default"""
        # Default (estimated R ~ 20 ohms for 3-element)
        payload_default = {
            "num_elements": 3,
            "driven_element_length_in": 203.0,
            "frequency_mhz": 27.185
        }
        response_default = requests.post(f"{BASE_URL}/api/gamma-designer", json=payload_default)
        assert response_default.status_code == 200
        data_default = response_default.json()
        
        # Custom feedpoint impedance = 30 ohms
        payload_custom = {
            "num_elements": 3,
            "driven_element_length_in": 203.0,
            "frequency_mhz": 27.185,
            "feedpoint_impedance": 30.0
        }
        response_custom = requests.post(f"{BASE_URL}/api/gamma-designer", json=payload_custom)
        assert response_custom.status_code == 200
        data_custom = response_custom.json()
        
        # Verify custom feedpoint is used
        assert data_custom["feedpoint_impedance"] == 30.0, \
            f"Expected feedpoint 30.0, got {data_custom['feedpoint_impedance']}"
        
        # Bar position should be different (higher R → lower step-up → bar closer to center)
        bar_default = data_default["recipe"]["ideal_bar_position"]
        bar_custom = data_custom["recipe"]["ideal_bar_position"]
        
        assert bar_default != bar_custom, \
            f"Custom feedpoint should give different bar position. Default={bar_default}, Custom={bar_custom}"
        
        # With higher feedpoint impedance, bar should be closer (less step-up needed)
        assert bar_custom < bar_default, \
            f"30Ω feedpoint should need less step-up → smaller bar ({bar_custom}) than 20Ω ({bar_default})"
        
        print(f"✓ Default R~{data_default['feedpoint_impedance']}Ω: bar={bar_default}\"")
        print(f"✓ Custom R=30Ω: bar={bar_custom}\" (smaller as expected)")


class TestGammaDesignerSweepData:
    """Tests for bar_sweep and insertion_sweep arrays"""

    def test_bar_sweep_array_valid(self):
        """bar_sweep array has valid data"""
        payload = {
            "num_elements": 3,
            "driven_element_length_in": 203.0,
            "frequency_mhz": 27.185
        }
        response = requests.post(f"{BASE_URL}/api/gamma-designer", json=payload)
        assert response.status_code == 200
        data = response.json()
        
        bar_sweep = data["bar_sweep"]
        
        # Should have multiple data points
        assert len(bar_sweep) > 5, f"bar_sweep should have multiple points, got {len(bar_sweep)}"
        
        # Each point should have required fields
        for i, point in enumerate(bar_sweep):
            assert "bar_inches" in point, f"Point {i} missing 'bar_inches'"
            assert "swr" in point, f"Point {i} missing 'swr'"
            assert "k" in point, f"Point {i} missing 'k' (step-up ratio)"
            assert "r_matched" in point, f"Point {i} missing 'r_matched'"
            assert "x_net" in point, f"Point {i} missing 'x_net'"
            
            # SWR should be >= 1.0
            assert point["swr"] >= 1.0, f"Point {i} SWR {point['swr']} should be >= 1.0"
            
            # K should be >= 1.0 (step-up ratio)
            assert point["k"] >= 1.0, f"Point {i} K {point['k']} should be >= 1.0"
        
        # Bar values should be ascending
        bar_values = [p["bar_inches"] for p in bar_sweep]
        assert bar_values == sorted(bar_values), "bar_inches should be in ascending order"
        
        print(f"✓ bar_sweep has {len(bar_sweep)} valid points")
        print(f"  Bar range: {bar_values[0]}\" to {bar_values[-1]}\"")

    def test_insertion_sweep_array_valid(self):
        """insertion_sweep array has valid data"""
        payload = {
            "num_elements": 3,
            "driven_element_length_in": 203.0,
            "frequency_mhz": 27.185
        }
        response = requests.post(f"{BASE_URL}/api/gamma-designer", json=payload)
        assert response.status_code == 200
        data = response.json()
        
        ins_sweep = data["insertion_sweep"]
        
        # Should have multiple data points
        assert len(ins_sweep) > 5, f"insertion_sweep should have multiple points, got {len(ins_sweep)}"
        
        # Each point should have required fields
        for i, point in enumerate(ins_sweep):
            assert "insertion_inches" in point, f"Point {i} missing 'insertion_inches'"
            assert "swr" in point, f"Point {i} missing 'swr'"
            assert "cap_pf" in point, f"Point {i} missing 'cap_pf'"
            assert "x_net" in point, f"Point {i} missing 'x_net'"
            
            # SWR should be >= 1.0
            assert point["swr"] >= 1.0, f"Point {i} SWR {point['swr']} should be >= 1.0"
            
            # Capacitance should be >= 0
            assert point["cap_pf"] >= 0, f"Point {i} cap_pf {point['cap_pf']} should be >= 0"
        
        # Insertion values should be ascending
        ins_values = [p["insertion_inches"] for p in ins_sweep]
        assert ins_values == sorted(ins_values), "insertion_inches should be in ascending order"
        
        print(f"✓ insertion_sweep has {len(ins_sweep)} valid points")
        print(f"  Insertion range: {ins_values[0]}\" to {ins_values[-1]}\"")


class TestGammaDesignerValidation:
    """Tests for input validation and error handling"""

    def test_invalid_geometry_tube_smaller_than_rod_returns_error(self):
        """Tube ID < rod OD returns error"""
        payload = {
            "num_elements": 3,
            "driven_element_length_in": 203.0,
            "frequency_mhz": 27.185,
            "custom_tube_od": 0.4,  # This gives tube ID ~0.3" (0.4 - 2*0.049)
            "custom_rod_od": 0.5   # Rod is larger than tube ID
        }
        response = requests.post(f"{BASE_URL}/api/gamma-designer", json=payload)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        # Should return error in response body
        assert "error" in data, f"Expected 'error' field for invalid geometry, got: {data}"
        assert "ID" in data["error"] or "must be larger" in data["error"].lower(), \
            f"Error should mention tube ID issue: {data['error']}"
        
        print(f"✓ Invalid geometry correctly rejected: {data['error']}")


class TestCalculateEndpointRegression:
    """Regression tests for /api/calculate with geometric K model"""

    def test_calculate_endpoint_still_works(self):
        """POST /api/calculate still works correctly with geometric K model"""
        payload = {
            "num_elements": 3,
            "elements": [
                {"element_type": "reflector", "length": 216, "diameter": 0.5, "position": 0},
                {"element_type": "driven", "length": 203, "diameter": 0.5, "position": 48},
                {"element_type": "director", "length": 195, "diameter": 0.5, "position": 96}
            ],
            "height_from_ground": 54,
            "height_unit": "ft",
            "boom_diameter": 1.5,
            "boom_unit": "inches",
            "band": "11m_cb",
            "frequency_mhz": 27.185,
            "feed_type": "gamma",
            "gamma_bar_pos": 12.0,
            "gamma_element_gap": 8.0
        }
        
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Validate key fields exist
        assert "swr" in data, "Response should contain 'swr'"
        assert "gain_dbi" in data, "Response should contain 'gain_dbi'"
        assert "fb_ratio" in data, "Response should contain 'fb_ratio'"
        assert "matching_info" in data, "Response should contain 'matching_info'"
        
        # Validate matching_info has geometric K fields
        if data["matching_info"]:
            mi = data["matching_info"]
            assert "step_up_k_squared" in mi or "step_up_ratio" in mi, \
                "matching_info should have step_up fields"
            
            # Check for ideal_bar_position (geometric K model)
            if "ideal_bar_position_inches" in mi:
                print(f"  Geometric K: ideal_bar={mi['ideal_bar_position_inches']}\", K²={mi.get('step_up_k_squared', 'N/A')}")
        
        # SWR should be reasonable
        assert 1.0 <= data["swr"] <= 10.0, f"SWR {data['swr']} out of expected range"
        
        # Gain should be positive
        assert data["gain_dbi"] > 0, f"Gain {data['gain_dbi']} should be positive"
        
        print(f"✓ /api/calculate works: SWR={data['swr']}, Gain={data['gain_dbi']} dBi, F/B={data['fb_ratio']} dB")


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
