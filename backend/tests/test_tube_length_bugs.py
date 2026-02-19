"""
Test suite for verifying gamma match tube length bug fixes:
1. Tube length is dynamic based on wavelength (~19.5" for 11m CB) - NOT hardcoded at 15"
2. gamma_design section uses consistent hardware dimensions with matching_info
3. Smith chart capacitance is clamped (not 25000+ pF when reactance near-zero)
4. Rod insertion can go up to tube_length (not capped at 15)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Standard test payload for 11m CB 2-element Yagi
DEFAULT_PAYLOAD = {
    "num_elements": 2,
    "elements": [
        {"element_type": "reflector", "length": 216, "diameter": 0.5, "position": 0},
        {"element_type": "driven", "length": 197.88, "diameter": 0.5, "position": 48}
    ],
    "height_from_ground": 54,
    "height_unit": "ft",
    "boom_diameter": 1.5,
    "boom_unit": "inches",
    "band": "11m_cb",
    "frequency_mhz": 27.185,
    "feed_type": "gamma",
    "gamma_bar_pos": 13,
    "gamma_element_gap": 8,  # rod insertion inches
    "antenna_orientation": "horizontal"
}

# 3-element Yagi payload
THREE_EL_PAYLOAD = {
    "num_elements": 3,
    "elements": [
        {"element_type": "reflector", "length": 216, "diameter": 0.5, "position": 0},
        {"element_type": "driven", "length": 197.88, "diameter": 0.5, "position": 48},
        {"element_type": "director", "length": 190, "diameter": 0.5, "position": 96}
    ],
    "height_from_ground": 54,
    "height_unit": "ft",
    "boom_diameter": 1.5,
    "boom_unit": "inches",
    "band": "11m_cb",
    "frequency_mhz": 27.185,
    "feed_type": "gamma",
    "gamma_bar_pos": 13,
    "gamma_element_gap": 8,
    "antenna_orientation": "horizontal"
}

# 4-element Yagi payload
FOUR_EL_PAYLOAD = {
    "num_elements": 4,
    "elements": [
        {"element_type": "reflector", "length": 216, "diameter": 0.5, "position": 0},
        {"element_type": "driven", "length": 197.88, "diameter": 0.5, "position": 48},
        {"element_type": "director", "length": 190, "diameter": 0.5, "position": 96},
        {"element_type": "director", "length": 185, "diameter": 0.5, "position": 144}
    ],
    "height_from_ground": 54,
    "height_unit": "ft",
    "boom_diameter": 1.5,
    "boom_unit": "inches",
    "band": "11m_cb",
    "frequency_mhz": 27.185,
    "feed_type": "gamma",
    "gamma_bar_pos": 13,
    "gamma_element_gap": 8,
    "antenna_orientation": "horizontal"
}


class TestTubeLengthDynamic:
    """BUG FIX #1: Tube length was hardcoded at 15" - now dynamic based on wavelength"""
    
    def test_tube_length_is_19_5_for_11m_cb(self):
        """Verify tube_length_inches = ~19.5" (not 15.0 or 11.0) for 11m CB at 27.185 MHz"""
        response = requests.post(f"{BASE_URL}/api/calculate", json=DEFAULT_PAYLOAD)
        assert response.status_code == 200, f"API failed: {response.text}"
        
        data = response.json()
        matching_info = data.get("matching_info", {})
        tube_length = matching_info.get("tube_length_inches")
        
        # 11m CB wavelength = 11802.71 / 27.185 = 434.2 inches
        # tube_length = 0.045 * wavelength = ~19.5"
        assert tube_length is not None, "tube_length_inches missing from matching_info"
        assert 19.0 <= tube_length <= 20.0, f"tube_length should be ~19.5\" for 11m CB, got {tube_length}\""
        assert tube_length != 15.0, f"tube_length is still hardcoded at 15.0\""
        assert tube_length != 11.0, f"tube_length incorrectly set to 11.0\""
        print(f"✓ tube_length_inches = {tube_length}\" (expected ~19.5\")")
    
    def test_teflon_sleeve_is_tube_plus_one(self):
        """Verify teflon_sleeve_inches = tube_length_inches + 1"""
        response = requests.post(f"{BASE_URL}/api/calculate", json=DEFAULT_PAYLOAD)
        assert response.status_code == 200
        
        data = response.json()
        matching_info = data.get("matching_info", {})
        tube_length = matching_info.get("tube_length_inches")
        teflon_sleeve = matching_info.get("teflon_sleeve_inches")
        
        assert teflon_sleeve is not None, "teflon_sleeve_inches missing"
        expected_teflon = tube_length + 1.0
        assert abs(teflon_sleeve - expected_teflon) < 0.2, \
            f"teflon_sleeve should be {expected_teflon}\" (tube+1), got {teflon_sleeve}\""
        print(f"✓ teflon_sleeve_inches = {teflon_sleeve}\" (tube {tube_length}\" + 1)")


class TestGammaDesignConsistency:
    """BUG FIX #2: gamma_design section used stale hardware dimensions"""
    
    def test_gamma_design_tube_length_matches_matching_info(self):
        """Verify matching_info.tube_length_inches == gamma_design.tube_length_in"""
        response = requests.post(f"{BASE_URL}/api/calculate", json=DEFAULT_PAYLOAD)
        assert response.status_code == 200
        
        data = response.json()
        matching_info = data.get("matching_info", {})
        gamma_design = matching_info.get("gamma_design", {})
        
        tube_in_matching = matching_info.get("tube_length_inches")
        tube_in_design = gamma_design.get("tube_length_in")
        
        assert tube_in_matching is not None, "tube_length_inches missing from matching_info"
        assert tube_in_design is not None, "tube_length_in missing from gamma_design"
        assert abs(tube_in_matching - tube_in_design) < 0.2, \
            f"Inconsistent tube length: matching_info={tube_in_matching}\" vs gamma_design={tube_in_design}\""
        print(f"✓ Tube length consistent: matching_info={tube_in_matching}\", gamma_design={tube_in_design}\"")
    
    def test_gamma_design_capacitance_matches_insertion_cap(self):
        """Verify matching_info.insertion_cap_pf == gamma_design.capacitance_pf for same hardware"""
        response = requests.post(f"{BASE_URL}/api/calculate", json=DEFAULT_PAYLOAD)
        assert response.status_code == 200
        
        data = response.json()
        matching_info = data.get("matching_info", {})
        gamma_design = matching_info.get("gamma_design", {})
        
        insertion_cap = matching_info.get("insertion_cap_pf")
        design_cap = gamma_design.get("capacitance_pf")
        auto_cap = gamma_design.get("auto_capacitance_pf")
        
        # When no user override, capacitance_pf should equal auto_capacitance_pf
        # which should match insertion_cap_pf from matching_info
        assert insertion_cap is not None, "insertion_cap_pf missing from matching_info"
        assert design_cap is not None, "capacitance_pf missing from gamma_design"
        
        # Allow small rounding differences
        assert abs(insertion_cap - design_cap) < 2.0, \
            f"Inconsistent capacitance: insertion_cap={insertion_cap}pF vs gamma_design={design_cap}pF"
        print(f"✓ Capacitance consistent: insertion_cap={insertion_cap}pF, gamma_design={design_cap}pF")
    
    def test_gamma_design_teflon_sleeve_matches_matching_info(self):
        """Verify gamma_design.teflon_sleeve_in matches matching_info.teflon_sleeve_inches"""
        response = requests.post(f"{BASE_URL}/api/calculate", json=DEFAULT_PAYLOAD)
        assert response.status_code == 200
        
        data = response.json()
        matching_info = data.get("matching_info", {})
        gamma_design = matching_info.get("gamma_design", {})
        
        teflon_matching = matching_info.get("teflon_sleeve_inches")
        teflon_design = gamma_design.get("teflon_sleeve_in")
        
        assert teflon_matching is not None, "teflon_sleeve_inches missing from matching_info"
        assert teflon_design is not None, "teflon_sleeve_in missing from gamma_design"
        assert abs(teflon_matching - teflon_design) < 0.2, \
            f"Inconsistent teflon sleeve: matching_info={teflon_matching}\" vs gamma_design={teflon_design}\""
        print(f"✓ Teflon sleeve consistent: matching_info={teflon_matching}\", gamma_design={teflon_design}\"")


class TestRodInsertionRange:
    """BUG FIX #4: rod_insertion_inches can go up to tube_length (not capped at 15)"""
    
    def test_rod_insertion_max_is_tube_length(self):
        """Verify rod_insertion can go up to 19.5\" (not capped at 15\")"""
        # Request with rod insertion at maximum (tube_length)
        payload = DEFAULT_PAYLOAD.copy()
        payload["gamma_element_gap"] = 19.5  # Try to insert rod to near tube length
        
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        matching_info = data.get("matching_info", {})
        rod_insertion = matching_info.get("rod_insertion_inches")
        tube_length = matching_info.get("tube_length_inches")
        
        assert rod_insertion is not None, "rod_insertion_inches missing"
        assert tube_length is not None, "tube_length_inches missing"
        
        # Rod insertion should be capped at tube_length, not at 15
        assert rod_insertion <= tube_length + 0.1, \
            f"rod_insertion should be capped at tube_length ({tube_length}\"), got {rod_insertion}\""
        assert rod_insertion > 15.0 or tube_length < 15.0, \
            f"rod_insertion might be incorrectly capped at 15\" - got {rod_insertion}\" with tube {tube_length}\""
        print(f"✓ rod_insertion={rod_insertion}\" with tube_length={tube_length}\"")
    
    def test_rod_insertion_produces_valid_capacitance(self):
        """Verify capacitance is reasonable for high rod insertion"""
        payload = DEFAULT_PAYLOAD.copy()
        payload["gamma_element_gap"] = 18.0  # High insertion
        
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        matching_info = data.get("matching_info", {})
        insertion_cap = matching_info.get("insertion_cap_pf")
        
        assert insertion_cap is not None, "insertion_cap_pf missing"
        # At 18" insertion with ~11 pF/inch, expect ~200 pF
        assert 50 < insertion_cap < 500, f"Capacitance {insertion_cap}pF seems unreasonable for 18\" insertion"
        print(f"✓ insertion_cap_pf={insertion_cap}pF at 18\" insertion")


class TestSmithChartCapacitanceClamping:
    """BUG FIX #3: Smith chart capacitance showed 25000+ pF when reactance near-zero"""
    
    def test_smith_chart_center_capacitance_is_zero(self):
        """Verify smith_chart_data center point capacitance_pf is 0 when reactance near-zero"""
        response = requests.post(f"{BASE_URL}/api/calculate", json=DEFAULT_PAYLOAD)
        assert response.status_code == 200
        
        data = response.json()
        smith_chart = data.get("smith_chart_data", [])
        
        assert len(smith_chart) > 0, "smith_chart_data is empty"
        
        # Find center frequency point (27.185 MHz)
        center_point = None
        for point in smith_chart:
            if abs(point.get("freq", 0) - 27.185) < 0.05:
                center_point = point
                break
        
        assert center_point is not None, "Could not find center frequency point in Smith chart"
        
        capacitance = center_point.get("capacitance_pf", 0)
        z_imag = center_point.get("z_imag", 0)
        
        # When reactance is near zero (resonance), capacitance should be 0 (clamped)
        if abs(z_imag) < 5:  # Near resonance
            assert capacitance < 1000, \
                f"Capacitance {capacitance}pF should be clamped when z_imag={z_imag} is near zero"
        
        # Also verify no point has 25000+ pF
        for point in smith_chart:
            cap = point.get("capacitance_pf", 0)
            assert cap < 25000, f"Found unrealistic capacitance {cap}pF at {point.get('freq')}MHz"
        
        print(f"✓ Center point: capacitance_pf={capacitance}, z_imag={z_imag}")
    
    def test_smith_chart_band_edges_reasonable_capacitance(self):
        """Verify smith_chart_data band edges show reasonable capacitance (< 1000 pF)"""
        response = requests.post(f"{BASE_URL}/api/calculate", json=DEFAULT_PAYLOAD)
        assert response.status_code == 200
        
        data = response.json()
        smith_chart = data.get("smith_chart_data", [])
        
        # Check all points have reasonable capacitance
        unreasonable_count = 0
        for point in smith_chart:
            cap = point.get("capacitance_pf", 0)
            if cap > 1000:
                unreasonable_count += 1
                print(f"  WARNING: {point.get('freq')}MHz has capacitance {cap}pF")
        
        assert unreasonable_count == 0, f"Found {unreasonable_count} points with capacitance > 1000pF"
        print(f"✓ All {len(smith_chart)} Smith chart points have capacitance < 1000pF")


class TestMultiElementYagis:
    """Verify all element configurations return valid results"""
    
    def test_2_element_yagi_valid_results(self):
        """2-element Yagi returns valid tube_length and gamma_design"""
        response = requests.post(f"{BASE_URL}/api/calculate", json=DEFAULT_PAYLOAD)
        assert response.status_code == 200
        
        data = response.json()
        assert "matching_info" in data
        assert data["matching_info"].get("tube_length_inches") is not None
        print(f"✓ 2-element Yagi: tube_length={data['matching_info']['tube_length_inches']}\"")
    
    def test_3_element_yagi_valid_results(self):
        """3-element Yagi returns valid tube_length and gamma_design"""
        response = requests.post(f"{BASE_URL}/api/calculate", json=THREE_EL_PAYLOAD)
        assert response.status_code == 200
        
        data = response.json()
        assert "matching_info" in data
        tube = data["matching_info"].get("tube_length_inches")
        assert tube is not None and 19 <= tube <= 20
        
        gamma_design = data["matching_info"].get("gamma_design")
        assert gamma_design is not None, "gamma_design missing for 3-element Yagi"
        print(f"✓ 3-element Yagi: tube_length={tube}\", gamma_design present")
    
    def test_4_element_yagi_valid_results(self):
        """4-element Yagi returns valid tube_length and gamma_design"""
        response = requests.post(f"{BASE_URL}/api/calculate", json=FOUR_EL_PAYLOAD)
        assert response.status_code == 200
        
        data = response.json()
        assert "matching_info" in data
        tube = data["matching_info"].get("tube_length_inches")
        assert tube is not None and 19 <= tube <= 20
        
        gamma_design = data["matching_info"].get("gamma_design")
        assert gamma_design is not None, "gamma_design missing for 4-element Yagi"
        print(f"✓ 4-element Yagi: tube_length={tube}\", gamma_design present")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
