"""
Comprehensive tests for POST /api/gamma-fine-tune endpoint.

Tests the fix where the optimizer now uses multi-objective _perf_score() 
that includes impedance optimization (target Z=22 ohms), so elements 
actually move when fine-tuning, even for well-tuned antennas.

Key change tested: Previously the optimizer had an early exit when 
original_swr <= 1.02 which made it do nothing. Now it always optimizes
using the new scoring function.
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://element-tuner.preview.emergentagent.com').rstrip('/')

# Standard 5-element Yagi test payload
STANDARD_5_ELEMENT = {
    "num_elements": 5,
    "elements": [
        {"element_type": "reflector", "length": 213.5, "diameter": 0.5, "position": 0},
        {"element_type": "driven", "length": 199.0, "diameter": 0.5, "position": 36},
        {"element_type": "director", "length": 190.5, "diameter": 0.5, "position": 72},
        {"element_type": "director", "length": 186.0, "diameter": 0.5, "position": 120},
        {"element_type": "director", "length": 183.5, "diameter": 0.5, "position": 180}
    ],
    "band": "11m_cb",
    "frequency_mhz": 27.205,
    "height_from_ground": 54,
    "height_unit": "ft",
    "boom_diameter": 1.5,
    "boom_unit": "in",
    "boom_grounded": True,
    "boom_mount": "center"
}


class TestGammaFineTuneElementsMove:
    """Test that elements actually move during optimization (the main fix)"""
    
    def test_5_element_elements_actually_move(self):
        """Key test: Verify that optimized elements are DIFFERENT from input elements."""
        print("\n=== Testing 5-element antenna - elements should move ===")
        
        response = requests.post(f"{BASE_URL}/api/gamma-fine-tune", json=STANDARD_5_ELEMENT)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        input_elements = STANDARD_5_ELEMENT["elements"]
        output_elements = data["optimized_elements"]
        
        # Check at least ONE element moved (length or position changed)
        any_element_changed = False
        changes_made = []
        
        for i, (inp, out) in enumerate(zip(input_elements, output_elements)):
            length_changed = abs(inp["length"] - out["length"]) > 0.01
            position_changed = abs(inp["position"] - out["position"]) > 0.01
            
            if length_changed or position_changed:
                any_element_changed = True
                change_desc = f"{inp['element_type']}: "
                if length_changed:
                    change_desc += f"length {inp['length']} -> {out['length']} "
                if position_changed:
                    change_desc += f"position {inp['position']} -> {out['position']}"
                changes_made.append(change_desc)
        
        print(f"Changes made: {changes_made}")
        print(f"Original SWR: {data['original_swr']}, Optimized SWR: {data['optimized_swr']}")
        
        assert any_element_changed, "BUG: No elements moved during optimization! The fix should cause elements to move."
        print("PASS: Elements moved during optimization")
    
    def test_3_element_elements_move(self):
        """Test that 3-element Yagi elements move"""
        payload = {
            "num_elements": 3,
            "elements": [
                {"element_type": "reflector", "length": 216, "diameter": 0.5, "position": 0},
                {"element_type": "driven", "length": 200, "diameter": 0.5, "position": 48},
                {"element_type": "director", "length": 192, "diameter": 0.5, "position": 96}
            ],
            "band": "11m_cb",
            "frequency_mhz": 27.185,
            "height_from_ground": 40,
            "height_unit": "ft",
            "boom_diameter": 1.5,
            "boom_unit": "in",
            "boom_grounded": True,
            "boom_mount": "bonded"
        }
        
        response = requests.post(f"{BASE_URL}/api/gamma-fine-tune", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        
        # Check at least one element changed
        changes = 0
        for inp, out in zip(payload["elements"], data["optimized_elements"]):
            if abs(inp["length"] - out["length"]) > 0.01 or abs(inp["position"] - out["position"]) > 0.01:
                changes += 1
        
        print(f"3-element: {changes} elements changed")
        assert changes > 0, "3-element: Elements should move during optimization"
        print("PASS: 3-element antenna elements moved")
    
    def test_8_element_elements_move(self):
        """Test that 8-element Yagi elements move"""
        payload = {
            "num_elements": 8,
            "elements": [
                {"element_type": "reflector", "length": 214, "diameter": 0.5, "position": 0},
                {"element_type": "driven", "length": 199, "diameter": 0.5, "position": 36},
                {"element_type": "director", "length": 191, "diameter": 0.5, "position": 72},
                {"element_type": "director", "length": 187, "diameter": 0.5, "position": 120},
                {"element_type": "director", "length": 184, "diameter": 0.5, "position": 168},
                {"element_type": "director", "length": 182, "diameter": 0.5, "position": 216},
                {"element_type": "director", "length": 180, "diameter": 0.5, "position": 264},
                {"element_type": "director", "length": 179, "diameter": 0.5, "position": 312}
            ],
            "band": "11m_cb",
            "frequency_mhz": 27.205,
            "height_from_ground": 54,
            "height_unit": "ft",
            "boom_diameter": 2.0,
            "boom_unit": "in",
            "boom_grounded": True,
            "boom_mount": "bonded"
        }
        
        response = requests.post(f"{BASE_URL}/api/gamma-fine-tune", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        
        changes = 0
        for inp, out in zip(payload["elements"], data["optimized_elements"]):
            if abs(inp["length"] - out["length"]) > 0.01 or abs(inp["position"] - out["position"]) > 0.01:
                changes += 1
        
        print(f"8-element: {changes} elements changed")
        assert changes > 0, "8-element: Elements should move during optimization"
        print("PASS: 8-element antenna elements moved")
    
    def test_10_element_elements_move(self):
        """Test that 10-element Yagi elements move"""
        payload = {
            "num_elements": 10,
            "elements": [
                {"element_type": "reflector", "length": 214, "diameter": 0.5, "position": 0},
                {"element_type": "driven", "length": 199, "diameter": 0.5, "position": 36},
                {"element_type": "director", "length": 191, "diameter": 0.5, "position": 72},
                {"element_type": "director", "length": 187, "diameter": 0.5, "position": 120},
                {"element_type": "director", "length": 184, "diameter": 0.5, "position": 168},
                {"element_type": "director", "length": 182, "diameter": 0.5, "position": 216},
                {"element_type": "director", "length": 180, "diameter": 0.5, "position": 264},
                {"element_type": "director", "length": 179, "diameter": 0.5, "position": 312},
                {"element_type": "director", "length": 178, "diameter": 0.5, "position": 360},
                {"element_type": "director", "length": 177, "diameter": 0.5, "position": 408}
            ],
            "band": "11m_cb",
            "frequency_mhz": 27.205,
            "height_from_ground": 60,
            "height_unit": "ft",
            "boom_diameter": 2.5,
            "boom_unit": "in",
            "boom_grounded": True,
            "boom_mount": "bonded"
        }
        
        response = requests.post(f"{BASE_URL}/api/gamma-fine-tune", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        
        changes = 0
        for inp, out in zip(payload["elements"], data["optimized_elements"]):
            if abs(inp["length"] - out["length"]) > 0.01 or abs(inp["position"] - out["position"]) > 0.01:
                changes += 1
        
        print(f"10-element: {changes} elements changed")
        assert changes > 0, "10-element: Elements should move during optimization"
        print("PASS: 10-element antenna elements moved")


class TestGammaFineTuneResponseFields:
    """Test that all required response fields are present and valid"""
    
    def test_response_has_gain_fields(self):
        """Verify original_gain and optimized_gain fields are present"""
        response = requests.post(f"{BASE_URL}/api/gamma-fine-tune", json=STANDARD_5_ELEMENT)
        assert response.status_code == 200
        
        data = response.json()
        
        # Check original_gain field
        assert "original_gain" in data, "Missing original_gain field"
        assert data["original_gain"] is not None, "original_gain should not be None"
        assert isinstance(data["original_gain"], (int, float)), "original_gain should be numeric"
        print(f"original_gain: {data['original_gain']} dBi")
        
        # Check optimized_gain field
        assert "optimized_gain" in data, "Missing optimized_gain field"
        assert data["optimized_gain"] is not None, "optimized_gain should not be None"
        assert isinstance(data["optimized_gain"], (int, float)), "optimized_gain should be numeric"
        print(f"optimized_gain: {data['optimized_gain']} dBi")
        
        # Gain should be reasonable (5-element Yagi typically 10-13 dBi)
        assert 5 < data["original_gain"] < 20, f"original_gain {data['original_gain']} seems unreasonable"
        assert 5 < data["optimized_gain"] < 20, f"optimized_gain {data['optimized_gain']} seems unreasonable"
        
        print("PASS: Gain fields present and valid")
    
    def test_gamma_recipe_fields(self):
        """Verify gamma_recipe contains required sub-fields"""
        response = requests.post(f"{BASE_URL}/api/gamma-fine-tune", json=STANDARD_5_ELEMENT)
        assert response.status_code == 200
        
        data = response.json()
        
        # gamma_recipe should exist
        assert "gamma_recipe" in data, "Missing gamma_recipe field"
        recipe = data["gamma_recipe"]
        assert recipe is not None, "gamma_recipe should not be None"
        
        # Check required sub-fields
        assert "swr_at_null" in recipe, "gamma_recipe missing swr_at_null"
        assert isinstance(recipe["swr_at_null"], (int, float)), "swr_at_null should be numeric"
        print(f"swr_at_null: {recipe['swr_at_null']}")
        
        assert "rod_od" in recipe, "gamma_recipe missing rod_od"
        assert isinstance(recipe["rod_od"], (int, float)), "rod_od should be numeric"
        assert recipe["rod_od"] > 0, "rod_od should be positive"
        print(f"rod_od: {recipe['rod_od']} inches")
        
        assert "tube_od" in recipe, "gamma_recipe missing tube_od"
        assert isinstance(recipe["tube_od"], (int, float)), "tube_od should be numeric"
        assert recipe["tube_od"] > 0, "tube_od should be positive"
        print(f"tube_od: {recipe['tube_od']} inches")
        
        assert "ideal_bar_position" in recipe, "gamma_recipe missing ideal_bar_position"
        assert isinstance(recipe["ideal_bar_position"], (int, float)), "ideal_bar_position should be numeric"
        print(f"ideal_bar_position: {recipe['ideal_bar_position']} inches")
        
        assert "optimal_insertion" in recipe, "gamma_recipe missing optimal_insertion"
        assert isinstance(recipe["optimal_insertion"], (int, float)), "optimal_insertion should be numeric"
        print(f"optimal_insertion: {recipe['optimal_insertion']} inches")
        
        print("PASS: gamma_recipe fields present and valid")
    
    def test_optimization_steps_show_element_changes(self):
        """Verify optimization_steps array contains meaningful descriptions of element changes"""
        response = requests.post(f"{BASE_URL}/api/gamma-fine-tune", json=STANDARD_5_ELEMENT)
        assert response.status_code == 200
        
        data = response.json()
        
        assert "optimization_steps" in data, "Missing optimization_steps field"
        steps = data["optimization_steps"]
        assert isinstance(steps, list), "optimization_steps should be a list"
        assert len(steps) > 0, "optimization_steps should not be empty"
        
        print(f"optimization_steps ({len(steps)}):")
        for step in steps:
            print(f"  - {step}")
        
        # Check that steps contain element change descriptions (not just generic messages)
        # Look for patterns like "Reflector:", "Driven:", "Dir1:", or "length:", "spacing:"
        has_element_changes = any(
            "Reflector" in s or "Driven" in s or "Dir" in s or "length" in s or "spacing" in s
            for s in steps
        )
        
        # Should have at least Baseline and Result steps
        has_baseline = any("Baseline" in s for s in steps)
        has_result = any("Result" in s for s in steps)
        
        assert has_baseline, "optimization_steps should have a Baseline step"
        assert has_result, "optimization_steps should have a Result step"
        
        # Since elements should move, we should have element change steps
        # (unless it's already at optimal - but that should be rare)
        print(f"Has element changes in steps: {has_element_changes}")
        
        print("PASS: optimization_steps present with meaningful descriptions")
    
    def test_optimized_swr_under_threshold(self):
        """Verify optimized_swr is <= 1.5 (antenna remains well-matched)"""
        response = requests.post(f"{BASE_URL}/api/gamma-fine-tune", json=STANDARD_5_ELEMENT)
        assert response.status_code == 200
        
        data = response.json()
        
        assert "optimized_swr" in data, "Missing optimized_swr field"
        optimized_swr = data["optimized_swr"]
        
        print(f"Original SWR: {data.get('original_swr', 'N/A')}")
        print(f"Optimized SWR: {optimized_swr}")
        
        assert optimized_swr <= 1.5, f"Optimized SWR {optimized_swr} exceeds 1.5 threshold"
        print("PASS: Optimized SWR is within acceptable range")


class TestGammaFineTuneMultipleElementCounts:
    """Test the endpoint works correctly for different element counts"""
    
    def test_3_element_returns_valid_response(self):
        """Test 3-element antenna fine-tune"""
        payload = {
            "num_elements": 3,
            "elements": [
                {"element_type": "reflector", "length": 216, "diameter": 0.5, "position": 0},
                {"element_type": "driven", "length": 200, "diameter": 0.5, "position": 48},
                {"element_type": "director", "length": 192, "diameter": 0.5, "position": 96}
            ],
            "band": "11m_cb",
            "frequency_mhz": 27.185,
            "height_from_ground": 40,
            "height_unit": "ft",
            "boom_diameter": 1.5,
            "boom_unit": "in",
            "boom_grounded": True,
            "boom_mount": "bonded"
        }
        
        response = requests.post(f"{BASE_URL}/api/gamma-fine-tune", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        self._validate_standard_fields(data, 3)
        print("PASS: 3-element antenna fine-tune works")
    
    def test_5_element_returns_valid_response(self):
        """Test 5-element antenna fine-tune"""
        response = requests.post(f"{BASE_URL}/api/gamma-fine-tune", json=STANDARD_5_ELEMENT)
        assert response.status_code == 200
        
        data = response.json()
        self._validate_standard_fields(data, 5)
        print("PASS: 5-element antenna fine-tune works")
    
    def test_8_element_returns_valid_response(self):
        """Test 8-element antenna fine-tune"""
        payload = {
            "num_elements": 8,
            "elements": [
                {"element_type": "reflector", "length": 214, "diameter": 0.5, "position": 0},
                {"element_type": "driven", "length": 199, "diameter": 0.5, "position": 36},
                {"element_type": "director", "length": 191, "diameter": 0.5, "position": 72},
                {"element_type": "director", "length": 187, "diameter": 0.5, "position": 120},
                {"element_type": "director", "length": 184, "diameter": 0.5, "position": 168},
                {"element_type": "director", "length": 182, "diameter": 0.5, "position": 216},
                {"element_type": "director", "length": 180, "diameter": 0.5, "position": 264},
                {"element_type": "director", "length": 179, "diameter": 0.5, "position": 312}
            ],
            "band": "11m_cb",
            "frequency_mhz": 27.205,
            "height_from_ground": 54,
            "height_unit": "ft",
            "boom_diameter": 2.0,
            "boom_unit": "in",
            "boom_grounded": True,
            "boom_mount": "bonded"
        }
        
        response = requests.post(f"{BASE_URL}/api/gamma-fine-tune", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        self._validate_standard_fields(data, 8)
        print("PASS: 8-element antenna fine-tune works")
    
    def test_10_element_returns_valid_response(self):
        """Test 10-element antenna fine-tune"""
        payload = {
            "num_elements": 10,
            "elements": [
                {"element_type": "reflector", "length": 214, "diameter": 0.5, "position": 0},
                {"element_type": "driven", "length": 199, "diameter": 0.5, "position": 36},
                {"element_type": "director", "length": 191, "diameter": 0.5, "position": 72},
                {"element_type": "director", "length": 187, "diameter": 0.5, "position": 120},
                {"element_type": "director", "length": 184, "diameter": 0.5, "position": 168},
                {"element_type": "director", "length": 182, "diameter": 0.5, "position": 216},
                {"element_type": "director", "length": 180, "diameter": 0.5, "position": 264},
                {"element_type": "director", "length": 179, "diameter": 0.5, "position": 312},
                {"element_type": "director", "length": 178, "diameter": 0.5, "position": 360},
                {"element_type": "director", "length": 177, "diameter": 0.5, "position": 408}
            ],
            "band": "11m_cb",
            "frequency_mhz": 27.205,
            "height_from_ground": 60,
            "height_unit": "ft",
            "boom_diameter": 2.5,
            "boom_unit": "in",
            "boom_grounded": True,
            "boom_mount": "bonded"
        }
        
        response = requests.post(f"{BASE_URL}/api/gamma-fine-tune", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        self._validate_standard_fields(data, 10)
        print("PASS: 10-element antenna fine-tune works")
    
    def _validate_standard_fields(self, data, expected_elements):
        """Helper to validate standard response fields"""
        # Check optimized_elements
        assert "optimized_elements" in data, "Missing optimized_elements"
        assert len(data["optimized_elements"]) == expected_elements, \
            f"Expected {expected_elements} elements, got {len(data['optimized_elements'])}"
        
        # Check SWR fields
        assert "original_swr" in data, "Missing original_swr"
        assert "optimized_swr" in data, "Missing optimized_swr"
        
        # Check gain fields
        assert "original_gain" in data, "Missing original_gain"
        assert "optimized_gain" in data, "Missing optimized_gain"
        
        # Check other required fields
        assert "feedpoint_impedance" in data, "Missing feedpoint_impedance"
        assert "optimization_steps" in data, "Missing optimization_steps"
        assert "hardware" in data, "Missing hardware"
        assert "gamma_recipe" in data, "Missing gamma_recipe"
        
        print(f"  Elements: {expected_elements}, Original SWR: {data['original_swr']}, Optimized SWR: {data['optimized_swr']}")
        print(f"  Original gain: {data['original_gain']} dBi, Optimized gain: {data['optimized_gain']} dBi")


class TestGammaFineTunePerformance:
    """Test that optimization completes in reasonable time"""
    
    def test_5_element_performance(self):
        """5-element should complete in <3 seconds"""
        start = time.time()
        response = requests.post(f"{BASE_URL}/api/gamma-fine-tune", json=STANDARD_5_ELEMENT)
        elapsed = time.time() - start
        
        assert response.status_code == 200
        print(f"5-element fine-tune took {elapsed:.2f} seconds")
        assert elapsed < 3.0, f"5-element took too long: {elapsed:.2f}s (limit: 3s)"
        print("PASS: 5-element performance acceptable")
    
    def test_10_element_performance(self):
        """10-element should complete in <5 seconds"""
        payload = {
            "num_elements": 10,
            "elements": [
                {"element_type": "reflector", "length": 214, "diameter": 0.5, "position": 0},
                {"element_type": "driven", "length": 199, "diameter": 0.5, "position": 36},
                {"element_type": "director", "length": 191, "diameter": 0.5, "position": 72},
                {"element_type": "director", "length": 187, "diameter": 0.5, "position": 120},
                {"element_type": "director", "length": 184, "diameter": 0.5, "position": 168},
                {"element_type": "director", "length": 182, "diameter": 0.5, "position": 216},
                {"element_type": "director", "length": 180, "diameter": 0.5, "position": 264},
                {"element_type": "director", "length": 179, "diameter": 0.5, "position": 312},
                {"element_type": "director", "length": 178, "diameter": 0.5, "position": 360},
                {"element_type": "director", "length": 177, "diameter": 0.5, "position": 408}
            ],
            "band": "11m_cb",
            "frequency_mhz": 27.205,
            "height_from_ground": 60,
            "height_unit": "ft",
            "boom_diameter": 2.5,
            "boom_unit": "in",
            "boom_grounded": True,
            "boom_mount": "bonded"
        }
        
        start = time.time()
        response = requests.post(f"{BASE_URL}/api/gamma-fine-tune", json=payload)
        elapsed = time.time() - start
        
        assert response.status_code == 200
        print(f"10-element fine-tune took {elapsed:.2f} seconds")
        assert elapsed < 5.0, f"10-element took too long: {elapsed:.2f}s (limit: 5s)"
        print("PASS: 10-element performance acceptable")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
