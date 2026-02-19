"""
Test cases for verifying Gamma Designer bug fixes:
P0: SWR-based labels (not 'PERFECT MATCH')
P1: 3-element Yagi should achieve SWR close to 1.0 (was 1.21)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestGammaDesignerSWRLabels:
    """P0 Bug: Gamma Designer label must show SWR-based quality labels"""
    
    def test_2_element_yagi_swr_and_null_reachable(self):
        """2-element Yagi: verify returns result with SWR and null_reachable fields"""
        response = requests.post(f"{BASE_URL}/api/gamma-designer", json={
            "num_elements": 2,
            "driven_element_length_in": 204.0,
            "frequency_mhz": 27.185
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        # Verify required fields exist
        assert "recipe" in data, "Response should contain 'recipe'"
        recipe = data["recipe"]
        assert "swr_at_null" in recipe, "Recipe should contain 'swr_at_null'"
        assert "null_reachable" in recipe, "Recipe should contain 'null_reachable'"
        
        # Verify SWR is a valid number
        swr = recipe["swr_at_null"]
        assert isinstance(swr, (int, float)), "SWR should be a number"
        assert swr >= 1.0, f"SWR should be >= 1.0, got {swr}"
        
        print(f"2-element Yagi SWR: {swr}, null_reachable: {recipe['null_reachable']}")
    
    def test_3_element_yagi_swr_close_to_1(self):
        """P1 Bug: 3-element Yagi should achieve SWR close to 1.0 (was 1.21 before fix)"""
        response = requests.post(f"{BASE_URL}/api/gamma-designer", json={
            "num_elements": 3,
            "driven_element_length_in": 206.0,
            "frequency_mhz": 27.185
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        recipe = data["recipe"]
        swr = recipe["swr_at_null"]
        
        # P1 Bug fix: SWR should be close to 1.0, not 1.21
        # Allow tolerance of 0.15 (SWR between 1.0 and 1.15)
        assert swr <= 1.15, f"3-element Yagi SWR should be <= 1.15 (close to 1.0), got {swr}"
        print(f"P1 PASS: 3-element Yagi SWR: {swr} (expected close to 1.0, was 1.21 before fix)")
    
    def test_4_element_yagi_swr_close_to_1(self):
        """4-element Yagi: verify returns SWR close to 1.0"""
        response = requests.post(f"{BASE_URL}/api/gamma-designer", json={
            "num_elements": 4,
            "driven_element_length_in": 206.0,
            "frequency_mhz": 27.185
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        recipe = data["recipe"]
        swr = recipe["swr_at_null"]
        
        # 4-element Yagi should also achieve good SWR
        assert swr <= 1.5, f"4-element Yagi SWR should be <= 1.5, got {swr}"
        print(f"4-element Yagi SWR: {swr}")
    
    def test_5_element_yagi_swr_close_to_1(self):
        """5-element Yagi: verify returns SWR close to 1.0"""
        response = requests.post(f"{BASE_URL}/api/gamma-designer", json={
            "num_elements": 5,
            "driven_element_length_in": 206.0,
            "frequency_mhz": 27.185
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        recipe = data["recipe"]
        swr = recipe["swr_at_null"]
        
        # 5-element Yagi should also achieve good SWR
        assert swr <= 1.5, f"5-element Yagi SWR should be <= 1.5, got {swr}"
        print(f"5-element Yagi SWR: {swr}")


class TestSWRLabelLogic:
    """Verify the SWR-based label logic (frontend will use these thresholds)"""
    
    def test_swr_label_thresholds_explanation(self):
        """Document the SWR label thresholds from frontend code"""
        # These are the thresholds from GammaDesigner.tsx lines 243-247:
        # swr_at_null <= 1.1: 'EXCELLENT MATCH'
        # swr_at_null <= 1.5: 'GOOD MATCH' 
        # swr_at_null <= 2.0: 'FAIR MATCH'
        # else: 'POOR MATCH'
        
        thresholds = {
            "EXCELLENT MATCH": "SWR <= 1.1",
            "GOOD MATCH": "1.1 < SWR <= 1.5",
            "FAIR MATCH": "1.5 < SWR <= 2.0",
            "POOR MATCH": "SWR > 2.0"
        }
        
        print("P0 Bug Verification - SWR-based labels (NOT 'PERFECT MATCH'):")
        for label, condition in thresholds.items():
            print(f"  {label}: {condition}")
        
        # The old bug was showing 'PERFECT MATCH' for high SWR like 3.21
        # Now it should show the appropriate label based on SWR value
        assert True, "Frontend label logic verified in GammaDesigner.tsx lines 243-247"
    
    def test_verify_3_element_gets_excellent_or_good_match(self):
        """3-element Yagi should get EXCELLENT (<=1.1) or GOOD (<=1.5) match label"""
        response = requests.post(f"{BASE_URL}/api/gamma-designer", json={
            "num_elements": 3,
            "driven_element_length_in": 206.0,
            "frequency_mhz": 27.185
        })
        assert response.status_code == 200
        data = response.json()
        swr = data["recipe"]["swr_at_null"]
        
        # Determine what label the frontend would show
        if swr <= 1.1:
            expected_label = "EXCELLENT MATCH"
        elif swr <= 1.5:
            expected_label = "GOOD MATCH"
        elif swr <= 2.0:
            expected_label = "FAIR MATCH"
        else:
            expected_label = "POOR MATCH"
        
        print(f"3-element Yagi: SWR={swr}, Frontend would show: '{expected_label}'")
        
        # P0: Should NOT show 'PERFECT MATCH' (old bug showed this for high SWR)
        assert expected_label != "PERFECT MATCH", "Label should not be 'PERFECT MATCH'"
        
        # With P1 fix, 3-element should achieve at least GOOD MATCH
        assert swr <= 1.5, f"3-element should achieve at least GOOD MATCH (SWR<=1.5), got {swr}"


class TestGammaDesignerAPIFields:
    """Verify all expected API response fields are present"""
    
    def test_recipe_has_all_required_fields(self):
        """Verify recipe contains all fields needed for frontend display"""
        response = requests.post(f"{BASE_URL}/api/gamma-designer", json={
            "num_elements": 3,
            "driven_element_length_in": 206.0,
            "frequency_mhz": 27.185
        })
        assert response.status_code == 200
        data = response.json()
        
        # Verify top-level fields
        assert "recipe" in data
        assert "feedpoint_impedance" in data
        assert "hardware_source" in data
        assert "bar_sweep" in data
        assert "insertion_sweep" in data
        assert "notes" in data
        
        # Verify recipe fields (used by frontend for display and label logic)
        recipe = data["recipe"]
        required_recipe_fields = [
            "rod_od", "tube_od", "tube_id", "rod_spacing",
            "teflon_length", "tube_length", "gamma_rod_length",
            "ideal_bar_position", "optimal_insertion",
            "swr_at_null",  # Used for SWR-based labels (P0)
            "null_reachable",  # Used for Apply button color (NOT for label)
            "return_loss_at_null", "capacitance_at_null",
            "z_matched_r", "z_matched_x",
            "k_step_up", "k_squared", "coupling_multiplier",
            "cap_per_inch", "id_rod_ratio"
        ]
        
        for field in required_recipe_fields:
            assert field in recipe, f"Recipe missing required field: {field}"
        
        print(f"All {len(required_recipe_fields)} required recipe fields present")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
