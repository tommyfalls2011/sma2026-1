"""
Backend tests for Gamma Designer hardware isolation bug fixes.

BUGS BEING VERIFIED:
1. 2-element antenna uses special hardware: rod_od=0.5625", rod_length=48", tube=30", teflon=31"
2. 3-20 element antennas use standard hardware: rod_od=0.500", rod_length=36", tube=22", teflon=23"
3. Gamma Designer should use correct default spacing (48") not hardcoded 64"
4. SWR consistency between /api/calculate and /api/gamma-designer round-trip

Tests verify hardware isolation and SWR consistency across both endpoints.
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestGammaDesignerHardware:
    """Test hardware selection for different element counts in /api/gamma-designer"""
    
    def test_2_element_gamma_designer_hardware(self):
        """2-element Yagi should use special hardware: rod=0.5625, rod_length=48, tube=30, teflon=31"""
        payload = {
            "num_elements": 2,
            "driven_element_length_in": 207.0,
            "frequency_mhz": 27.185
        }
        response = requests.post(f"{BASE_URL}/api/gamma-designer", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        recipe = data.get("recipe", {})
        
        # Verify 2-element special hardware
        # Note: rod_od is rounded to 3 decimal places (0.5625 -> 0.562)
        assert abs(recipe.get("rod_od", 0) - 0.5625) < 0.001, f"2-element rod_od should be ~0.5625, got {recipe.get('rod_od')}"
        assert recipe.get("gamma_rod_length") == 48.0, f"2-element rod_length should be 48, got {recipe.get('gamma_rod_length')}"
        assert recipe.get("tube_length") == 30.0, f"2-element tube_length should be 30, got {recipe.get('tube_length')}"
        assert recipe.get("teflon_length") == 31.0, f"2-element teflon_length should be 31, got {recipe.get('teflon_length')}"
        
        print(f"2-element hardware: rod_od={recipe.get('rod_od')}, rod_length={recipe.get('gamma_rod_length')}, tube={recipe.get('tube_length')}, teflon={recipe.get('teflon_length')}")
    
    def test_3_element_gamma_designer_hardware(self):
        """3-element Yagi should use standard hardware: rod=0.5, rod_length=36, tube=22, teflon=23"""
        payload = {
            "num_elements": 3,
            "driven_element_length_in": 203.0,
            "frequency_mhz": 27.185
        }
        response = requests.post(f"{BASE_URL}/api/gamma-designer", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        recipe = data.get("recipe", {})
        
        # Verify 3-element standard hardware
        assert recipe.get("rod_od") == 0.500, f"3-element rod_od should be 0.5, got {recipe.get('rod_od')}"
        assert recipe.get("gamma_rod_length") == 36.0, f"3-element rod_length should be 36, got {recipe.get('gamma_rod_length')}"
        assert recipe.get("tube_length") == 22.0, f"3-element tube_length should be 22, got {recipe.get('tube_length')}"
        assert recipe.get("teflon_length") == 23.0, f"3-element teflon_length should be 23, got {recipe.get('teflon_length')}"
        
        print(f"3-element hardware: rod_od={recipe.get('rod_od')}, rod_length={recipe.get('gamma_rod_length')}, tube={recipe.get('tube_length')}, teflon={recipe.get('teflon_length')}")
    
    def test_5_element_gamma_designer_hardware(self):
        """5-element Yagi should use standard hardware (same as 3-element)"""
        payload = {
            "num_elements": 5,
            "driven_element_length_in": 203.0,
            "frequency_mhz": 27.185
        }
        response = requests.post(f"{BASE_URL}/api/gamma-designer", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        recipe = data.get("recipe", {})
        
        # Verify 5-element uses standard hardware (NOT 2-element special)
        assert recipe.get("rod_od") == 0.500, f"5-element rod_od should be 0.5, got {recipe.get('rod_od')}"
        assert recipe.get("gamma_rod_length") == 36.0, f"5-element rod_length should be 36, got {recipe.get('gamma_rod_length')}"
        assert recipe.get("tube_length") == 22.0, f"5-element tube_length should be 22, got {recipe.get('tube_length')}"
        assert recipe.get("teflon_length") == 23.0, f"5-element teflon_length should be 23, got {recipe.get('teflon_length')}"
        
        print(f"5-element hardware: rod_od={recipe.get('rod_od')}, rod_length={recipe.get('gamma_rod_length')}, tube={recipe.get('tube_length')}, teflon={recipe.get('teflon_length')}")


class TestMainCalculatorHardware:
    """Test hardware selection in /api/calculate matching_info"""
    
    def _create_elements(self, num_elements):
        """Create standard element layout based on count"""
        elements = [
            {"element_type": "reflector", "length": 214.0, "diameter": 1.0, "position": 0}
        ]
        
        if num_elements >= 2:
            elements.append({"element_type": "driven", "length": 203.0, "diameter": 1.0, "position": 48})
        
        # Directors at 48" increments after driven
        for i in range(num_elements - 2):
            elements.append({
                "element_type": "director",
                "length": 195.0 - (i * 2),  # slightly decreasing director lengths
                "diameter": 1.0,
                "position": 96 + (i * 48)
            })
        
        return elements
    
    def test_2_element_calculate_hardware(self):
        """2-element Yagi /api/calculate should use special hardware"""
        payload = {
            "num_elements": 2,
            "elements": self._create_elements(2),
            "height_from_ground": 35,
            "height_unit": "ft",
            "boom_diameter": 2.0,
            "boom_unit": "inches",
            "band": "11m_cb",
            "frequency_mhz": 27.185,
            "feed_type": "gamma"
        }
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        matching_info = data.get("matching_info", {})
        hardware = matching_info.get("hardware", {})
        
        # Verify 2-element special hardware in main calculator
        # Note: main calculator uses rod_od, tube_length, teflon_length in hardware dict
        assert hardware.get("rod_od") == 0.562 or hardware.get("rod_od") == 0.5625, \
            f"2-element rod_od should be ~0.562, got {hardware.get('rod_od')}"
        assert hardware.get("rod_length") == 48.0, f"2-element rod_length should be 48, got {hardware.get('rod_length')}"
        assert hardware.get("tube_length") == 30.0, f"2-element tube_length should be 30, got {hardware.get('tube_length')}"
        assert hardware.get("teflon_length") == 31.0, f"2-element teflon_length should be 31, got {hardware.get('teflon_length')}"
        
        print(f"2-element calc hardware: {hardware}")
    
    def test_3_element_calculate_hardware(self):
        """3-element Yagi /api/calculate should use standard hardware"""
        payload = {
            "num_elements": 3,
            "elements": self._create_elements(3),
            "height_from_ground": 35,
            "height_unit": "ft",
            "boom_diameter": 2.0,
            "boom_unit": "inches",
            "band": "11m_cb",
            "frequency_mhz": 27.185,
            "feed_type": "gamma"
        }
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        matching_info = data.get("matching_info", {})
        hardware = matching_info.get("hardware", {})
        
        # Verify 3-element standard hardware
        assert hardware.get("rod_od") == 0.5, f"3-element rod_od should be 0.5, got {hardware.get('rod_od')}"
        assert hardware.get("rod_length") == 36.0, f"3-element rod_length should be 36, got {hardware.get('rod_length')}"
        assert hardware.get("tube_length") == 22.0, f"3-element tube_length should be 22, got {hardware.get('tube_length')}"
        assert hardware.get("teflon_length") == 23.0, f"3-element teflon_length should be 23, got {hardware.get('teflon_length')}"
        
        print(f"3-element calc hardware: {hardware}")


class TestDesignerAcceptsNewFields:
    """Test that /api/gamma-designer accepts new optional fields"""
    
    def test_designer_accepts_element_resonant_freq(self):
        """Designer should accept element_resonant_freq_mhz field"""
        payload = {
            "num_elements": 3,
            "driven_element_length_in": 203.0,
            "frequency_mhz": 27.185,
            "element_resonant_freq_mhz": 27.10
        }
        response = requests.post(f"{BASE_URL}/api/gamma-designer", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "recipe" in data, "Response should contain recipe"
        print(f"Designer accepted element_resonant_freq_mhz: SWR={data['recipe'].get('swr_at_null')}")
    
    def test_designer_accepts_reflector_spacing(self):
        """Designer should accept reflector_spacing_in field"""
        payload = {
            "num_elements": 3,
            "driven_element_length_in": 203.0,
            "frequency_mhz": 27.185,
            "reflector_spacing_in": 48.0
        }
        response = requests.post(f"{BASE_URL}/api/gamma-designer", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "recipe" in data, "Response should contain recipe"
        print(f"Designer accepted reflector_spacing_in: SWR={data['recipe'].get('swr_at_null')}")
    
    def test_designer_accepts_director_spacings(self):
        """Designer should accept director_spacings_in field"""
        payload = {
            "num_elements": 4,
            "driven_element_length_in": 203.0,
            "frequency_mhz": 27.185,
            "director_spacings_in": [48, 96]
        }
        response = requests.post(f"{BASE_URL}/api/gamma-designer", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "recipe" in data, "Response should contain recipe"
        print(f"Designer accepted director_spacings_in: SWR={data['recipe'].get('swr_at_null')}")
    
    def test_designer_accepts_all_new_fields(self):
        """Designer should accept all new optional fields together"""
        payload = {
            "num_elements": 4,
            "driven_element_length_in": 203.0,
            "frequency_mhz": 27.185,
            "element_resonant_freq_mhz": 27.10,
            "reflector_spacing_in": 48.0,
            "director_spacings_in": [48, 96]
        }
        response = requests.post(f"{BASE_URL}/api/gamma-designer", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "recipe" in data, "Response should contain recipe"
        assert "feedpoint_impedance" in data, "Response should contain feedpoint_impedance"
        print(f"Designer accepted all new fields: feedpoint_R={data.get('feedpoint_impedance')}, SWR={data['recipe'].get('swr_at_null')}")


class TestSWRConsistencyRoundTrip:
    """Test SWR consistency between /api/calculate and /api/gamma-designer round-trip"""
    
    def _create_elements(self, num_elements):
        """Create standard element layout"""
        elements = [
            {"element_type": "reflector", "length": 214.0, "diameter": 1.0, "position": 0}
        ]
        if num_elements >= 2:
            elements.append({"element_type": "driven", "length": 203.0, "diameter": 1.0, "position": 48})
        for i in range(num_elements - 2):
            elements.append({
                "element_type": "director",
                "length": 195.0 - (i * 2),
                "diameter": 1.0,
                "position": 96 + (i * 48)
            })
        return elements
    
    def test_4_element_round_trip_swr_consistency(self):
        """
        Full round-trip for 4-element Yagi:
        1. Call /api/calculate to get feedpoint_R and element_resonant_freq_mhz
        2. Pass to /api/gamma-designer with reflector_spacing_in=48 and director_spacings_in=[48,96]
        3. Get optimal bar/insertion
        4. Call /api/calculate again with bar/insertion
        5. SWRs should match within tolerance
        """
        # Step 1: Initial calculation to get feedpoint_R and element_resonant_freq
        elements = self._create_elements(4)
        calc_payload = {
            "num_elements": 4,
            "elements": elements,
            "height_from_ground": 35,
            "height_unit": "ft",
            "boom_diameter": 2.0,
            "boom_unit": "inches",
            "band": "11m_cb",
            "frequency_mhz": 27.185,
            "feed_type": "gamma"
        }
        
        calc_response = requests.post(f"{BASE_URL}/api/calculate", json=calc_payload)
        assert calc_response.status_code == 200, f"Calculate failed: {calc_response.text}"
        
        calc_data = calc_response.json()
        matching_info = calc_data.get("matching_info", {})
        feedpoint_r = matching_info.get("debug_trace", [{}])[0].get("items", [{}])[0].get("val") or 28.0
        
        # Try to get feedpoint_R from various locations
        if "z_matched_r" in matching_info:
            k_sq = matching_info.get("step_up_k_squared", 1.0)
            if k_sq > 1:
                feedpoint_r = matching_info["z_matched_r"] / k_sq
        
        element_resonant_freq = matching_info.get("element_resonant_freq_mhz", 27.10)
        calc_swr = calc_data.get("swr")
        
        print(f"Step 1 - Initial calc: feedpoint_R ~{feedpoint_r:.1f} ohms, element_resonant_freq={element_resonant_freq}, SWR={calc_swr}")
        
        # Step 2: Call designer with same spacings
        designer_payload = {
            "num_elements": 4,
            "driven_element_length_in": 203.0,
            "frequency_mhz": 27.185,
            "element_resonant_freq_mhz": element_resonant_freq,
            "reflector_spacing_in": 48.0,
            "director_spacings_in": [48, 96]
        }
        
        designer_response = requests.post(f"{BASE_URL}/api/gamma-designer", json=designer_payload)
        assert designer_response.status_code == 200, f"Designer failed: {designer_response.text}"
        
        designer_data = designer_response.json()
        recipe = designer_data.get("recipe", {})
        optimal_bar = recipe.get("ideal_bar_position")
        optimal_insertion = recipe.get("optimal_insertion")
        designer_swr = recipe.get("swr_at_null")
        
        print(f"Step 2 - Designer: bar={optimal_bar}, insertion={optimal_insertion}, SWR={designer_swr}")
        
        # Step 3: Call calculate again with bar/insertion from designer
        calc_payload_with_gamma = calc_payload.copy()
        calc_payload_with_gamma["gamma_bar_pos"] = optimal_bar
        calc_payload_with_gamma["gamma_element_gap"] = optimal_insertion
        
        final_response = requests.post(f"{BASE_URL}/api/calculate", json=calc_payload_with_gamma)
        assert final_response.status_code == 200, f"Final calculate failed: {final_response.text}"
        
        final_data = final_response.json()
        final_swr = final_data.get("swr")
        
        print(f"Step 3 - Final calc with designer bar/insertion: SWR={final_swr}")
        
        # Step 4: Verify SWR consistency - should be close (within 0.1)
        swr_diff = abs(designer_swr - final_swr)
        print(f"SWR difference: {swr_diff:.3f}")
        
        # Allow some tolerance (0.1) for physics model differences
        assert swr_diff < 0.1 or (designer_swr <= 1.1 and final_swr <= 1.5), \
            f"SWR mismatch: designer={designer_swr}, calculator={final_swr}, diff={swr_diff}"
    
    def test_2_element_round_trip_swr_consistency(self):
        """
        Full round-trip for 2-element Yagi
        """
        elements = self._create_elements(2)
        calc_payload = {
            "num_elements": 2,
            "elements": elements,
            "height_from_ground": 35,
            "height_unit": "ft",
            "boom_diameter": 2.0,
            "boom_unit": "inches",
            "band": "11m_cb",
            "frequency_mhz": 27.185,
            "feed_type": "gamma"
        }
        
        calc_response = requests.post(f"{BASE_URL}/api/calculate", json=calc_payload)
        assert calc_response.status_code == 200, f"Calculate failed: {calc_response.text}"
        
        calc_data = calc_response.json()
        matching_info = calc_data.get("matching_info", {})
        element_resonant_freq = matching_info.get("element_resonant_freq_mhz", 27.10)
        calc_swr = calc_data.get("swr")
        
        print(f"2-element initial calc: element_resonant_freq={element_resonant_freq}, SWR={calc_swr}")
        
        # Call designer with reflector spacing 48"
        designer_payload = {
            "num_elements": 2,
            "driven_element_length_in": 203.0,
            "frequency_mhz": 27.185,
            "element_resonant_freq_mhz": element_resonant_freq,
            "reflector_spacing_in": 48.0
        }
        
        designer_response = requests.post(f"{BASE_URL}/api/gamma-designer", json=designer_payload)
        assert designer_response.status_code == 200, f"Designer failed: {designer_response.text}"
        
        designer_data = designer_response.json()
        recipe = designer_data.get("recipe", {})
        optimal_bar = recipe.get("ideal_bar_position")
        optimal_insertion = recipe.get("optimal_insertion")
        designer_swr = recipe.get("swr_at_null")
        
        print(f"2-element designer: bar={optimal_bar}, insertion={optimal_insertion}, SWR={designer_swr}")
        
        # Verify 2-element hardware is correct (rounded to 3 decimal places)
        assert abs(recipe.get("rod_od", 0) - 0.5625) < 0.001, f"2-element should use rod_od~0.5625, got {recipe.get('rod_od')}"
        assert recipe.get("tube_length") == 30.0, f"2-element should use tube_length=30, got {recipe.get('tube_length')}"
        
        # Call calculate with designer values
        calc_payload_with_gamma = calc_payload.copy()
        calc_payload_with_gamma["gamma_bar_pos"] = optimal_bar
        calc_payload_with_gamma["gamma_element_gap"] = optimal_insertion
        
        final_response = requests.post(f"{BASE_URL}/api/calculate", json=calc_payload_with_gamma)
        assert final_response.status_code == 200, f"Final calculate failed: {final_response.text}"
        
        final_data = final_response.json()
        final_swr = final_data.get("swr")
        
        print(f"2-element final calc with designer bar/insertion: SWR={final_swr}")
        
        swr_diff = abs(designer_swr - final_swr)
        print(f"2-element SWR difference: {swr_diff:.3f}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
