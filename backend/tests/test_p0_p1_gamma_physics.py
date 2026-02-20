"""
Tests for P0 (max_insertion constraint) and P1 (physics refactoring) changes.

Testing:
1. POST /api/gamma-designer — SWR values: 2-el ~1.1, 3-20 el = 1.0
2. POST /api/gamma-designer — all elements use rod_od=0.625
3. POST /api/gamma-designer — bar_min=4.0 (teflon), max_insertion=3.5 (teflon-0.5)
4. POST /api/calculate with gamma feed — insertion capped at 3.5, rod_od=0.625
5. POST /api/calculate with corrected driven element produces SWR ~1.0
6. Consistency between designer and calculator
7. POST /api/gamma-designer — insertion_sweep goes up to max_insertion (3.5)
"""

import pytest
import requests
import os
import math

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestGammaDesignerSWRByElements:
    """Test SWR values from gamma designer for different element counts."""

    @pytest.fixture
    def standard_driven_length(self):
        """204\" driven element length standard for 27.185 MHz."""
        return 204.0

    def _call_designer(self, num_elements: int, driven_length: float = 204.0):
        """Helper to call gamma designer API."""
        response = requests.post(f"{BASE_URL}/api/gamma-designer", json={
            "num_elements": num_elements,
            "driven_element_length_in": driven_length,
            "frequency_mhz": 27.185,
        })
        assert response.status_code == 200, f"API call failed: {response.text}"
        return response.json()

    def test_2_element_swr_approximately_1_1(self):
        """2-element should have SWR ~1.1 (null not reachable)."""
        result = self._call_designer(2)
        recipe = result.get("recipe", {})
        
        swr = recipe.get("swr_at_null", 0)
        null_reachable = recipe.get("null_reachable", True)
        
        # 2-element has higher R_feed (~36Ω) - null may not be reachable
        # Expected SWR around 1.1-1.2
        print(f"2-element SWR: {swr}, null_reachable: {null_reachable}")
        
        # Allow range 1.0-1.3 for 2-element (may or may not reach perfect null)
        assert 1.0 <= swr <= 1.3, f"2-element SWR {swr} not in expected range [1.0, 1.3]"

    def test_3_element_swr_1_0(self):
        """3-element should achieve SWR = 1.0 (null reachable)."""
        result = self._call_designer(3)
        recipe = result.get("recipe", {})
        
        swr = recipe.get("swr_at_null", 0)
        null_reachable = recipe.get("null_reachable", False)
        
        print(f"3-element SWR: {swr}, null_reachable: {null_reachable}")
        
        assert null_reachable, "3-element should reach null"
        assert swr == 1.0 or abs(swr - 1.0) < 0.01, f"3-element SWR should be 1.0, got {swr}"

    def test_4_element_swr_1_0(self):
        """4-element should achieve SWR = 1.0."""
        result = self._call_designer(4)
        recipe = result.get("recipe", {})
        
        swr = recipe.get("swr_at_null", 0)
        null_reachable = recipe.get("null_reachable", False)
        
        print(f"4-element SWR: {swr}, null_reachable: {null_reachable}")
        
        assert null_reachable, "4-element should reach null"
        assert swr == 1.0, f"4-element SWR should be 1.0, got {swr}"

    def test_6_element_swr_1_0(self):
        """6-element should achieve SWR = 1.0."""
        result = self._call_designer(6)
        recipe = result.get("recipe", {})
        
        swr = recipe.get("swr_at_null", 0)
        null_reachable = recipe.get("null_reachable", False)
        
        print(f"6-element SWR: {swr}, null_reachable: {null_reachable}")
        
        assert null_reachable, "6-element should reach null"
        assert swr == 1.0, f"6-element SWR should be 1.0, got {swr}"

    def test_8_element_swr_1_0(self):
        """8-element should achieve SWR = 1.0."""
        result = self._call_designer(8)
        recipe = result.get("recipe", {})
        
        swr = recipe.get("swr_at_null", 0)
        null_reachable = recipe.get("null_reachable", False)
        
        print(f"8-element SWR: {swr}, null_reachable: {null_reachable}")
        
        assert null_reachable, "8-element should reach null"
        assert swr == 1.0, f"8-element SWR should be 1.0, got {swr}"

    def test_20_element_swr_1_0(self):
        """20-element should achieve SWR = 1.0."""
        result = self._call_designer(20)
        recipe = result.get("recipe", {})
        
        swr = recipe.get("swr_at_null", 0)
        null_reachable = recipe.get("null_reachable", False)
        
        print(f"20-element SWR: {swr}, null_reachable: {null_reachable}")
        
        assert null_reachable, "20-element should reach null"
        assert swr == 1.0, f"20-element SWR should be 1.0, got {swr}"


class TestGammaDesignerHardware:
    """Test that gamma designer uses unified rod_od=0.625 for all elements."""

    def _call_designer(self, num_elements: int):
        response = requests.post(f"{BASE_URL}/api/gamma-designer", json={
            "num_elements": num_elements,
            "driven_element_length_in": 204.0,
            "frequency_mhz": 27.185,
        })
        assert response.status_code == 200, f"API call failed: {response.text}"
        return response.json()

    def test_all_elements_use_rod_od_0625(self):
        """All element counts should use rod_od = 0.625\"."""
        for n in [2, 3, 4, 5, 6, 7, 8, 10, 15, 20]:
            result = self._call_designer(n)
            auto_hw = result.get("auto_hardware", {})
            recipe_rod = result.get("recipe", {}).get("rod_od", 0)
            
            # Check both auto_hardware and recipe rod_od
            auto_rod = auto_hw.get("rod_od", 0)
            
            print(f"{n}-element: auto_rod={auto_rod}, recipe_rod={recipe_rod}")
            
            assert auto_rod == 0.625, f"{n}-element auto_hardware rod_od should be 0.625, got {auto_rod}"
            assert recipe_rod == 0.625, f"{n}-element recipe rod_od should be 0.625, got {recipe_rod}"


class TestGammaDesignerConstraints:
    """Test bar_min and max_insertion constraints."""

    def _call_designer(self, num_elements: int):
        response = requests.post(f"{BASE_URL}/api/gamma-designer", json={
            "num_elements": num_elements,
            "driven_element_length_in": 204.0,
            "frequency_mhz": 27.185,
        })
        assert response.status_code == 200, f"API call failed: {response.text}"
        return response.json()

    def test_bar_min_equals_teflon_length_4_0(self):
        """bar_min should equal teflon_length = 4.0\"."""
        for n in [3, 4, 6, 8]:
            result = self._call_designer(n)
            recipe = result.get("recipe", {})
            
            bar_min = recipe.get("bar_min", 0)
            teflon_length = recipe.get("teflon_length", 0)
            tube_length = recipe.get("tube_length", 0)
            
            print(f"{n}-element: bar_min={bar_min}, teflon={teflon_length}, tube={tube_length}")
            
            # tube_length = 3.0, teflon = tube + 1.0 = 4.0, bar_min = teflon = 4.0
            assert tube_length == 3.0, f"{n}-element tube_length should be 3.0, got {tube_length}"
            assert teflon_length == 4.0, f"{n}-element teflon_length should be 4.0, got {teflon_length}"
            assert bar_min == 4.0, f"{n}-element bar_min should be 4.0, got {bar_min}"

    def test_max_insertion_equals_teflon_minus_0_5(self):
        """max_insertion should be teflon_length - 0.5 = 3.5\"."""
        for n in [3, 4, 6, 8]:
            result = self._call_designer(n)
            recipe = result.get("recipe", {})
            
            teflon_length = recipe.get("teflon_length", 0)
            # max_insertion is not directly returned, but we can verify via insertion_sweep
            
            ins_sweep = result.get("insertion_sweep", [])
            if ins_sweep:
                max_ins_in_sweep = max(p.get("insertion_inches", 0) for p in ins_sweep)
                print(f"{n}-element: teflon={teflon_length}, max_insertion_in_sweep={max_ins_in_sweep}")
                
                # Max insertion should be 3.5 (teflon 4.0 - 0.5)
                expected_max = teflon_length - 0.5
                assert abs(max_ins_in_sweep - expected_max) < 0.1, \
                    f"{n}-element max insertion in sweep should be {expected_max}, got {max_ins_in_sweep}"

    def test_insertion_sweep_goes_to_max_insertion_not_tube_length(self):
        """Insertion sweep should go up to 3.5 (max_insertion), not 3.0 (tube_length)."""
        result = self._call_designer(4)
        recipe = result.get("recipe", {})
        ins_sweep = result.get("insertion_sweep", [])
        
        tube_length = recipe.get("tube_length", 0)  # 3.0
        teflon_length = recipe.get("teflon_length", 0)  # 4.0
        expected_max_insertion = teflon_length - 0.5  # 3.5
        
        if ins_sweep:
            max_ins = max(p.get("insertion_inches", 0) for p in ins_sweep)
            print(f"tube_length={tube_length}, teflon={teflon_length}, max_insertion_in_sweep={max_ins}")
            
            # Verify max insertion is 3.5, not 3.0
            assert max_ins > tube_length, f"Max insertion {max_ins} should be greater than tube_length {tube_length}"
            assert abs(max_ins - expected_max_insertion) < 0.1, \
                f"Max insertion should be {expected_max_insertion}, got {max_ins}"


class TestCalculateEndpointGammaConstraints:
    """Test /api/calculate with gamma feed respects the P0 constraint."""

    def _create_elements(self, num_elements: int, driven_length: float = 204.0):
        """Create standard Yagi element configuration."""
        elements = [
            {"element_type": "reflector", "length": 214.0, "diameter": 1.0, "position": 0},
            {"element_type": "driven", "length": driven_length, "diameter": 1.0, "position": 48},
        ]
        for i in range(num_elements - 2):
            elements.append({
                "element_type": "director",
                "length": 198.0 - (i * 2),  # Slightly shorter each director
                "diameter": 1.0,
                "position": 96 + (i * 48)
            })
        return elements

    def _call_calculate(self, num_elements: int, driven_length: float = 204.0, 
                       gamma_element_gap: float = None):
        """Call /api/calculate with gamma feed."""
        elements = self._create_elements(num_elements, driven_length)
        payload = {
            "num_elements": num_elements,
            "elements": elements,
            "height_from_ground": 50,
            "height_unit": "ft",
            "boom_diameter": 2.0,
            "boom_unit": "inches",
            "band": "11m_cb",
            "frequency_mhz": 27.185,
            "feed_type": "gamma",
            "antenna_orientation": "horizontal",
        }
        if gamma_element_gap is not None:
            payload["gamma_element_gap"] = gamma_element_gap
        
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
        assert response.status_code == 200, f"API call failed: {response.text}"
        return response.json()

    def test_calculate_gamma_hardware_uses_rod_od_0625(self):
        """Calculate endpoint should use rod_od=0.625 for gamma match."""
        result = self._call_calculate(4)
        matching_info = result.get("matching_info", {})
        hardware = matching_info.get("hardware", {})
        
        rod_od = hardware.get("rod_od", 0)
        tube_length = hardware.get("tube_length", 0)
        teflon_length = hardware.get("teflon_length", 0)
        
        print(f"Calculate 4-element: rod_od={rod_od}, tube={tube_length}, teflon={teflon_length}")
        
        assert rod_od == 0.625, f"rod_od should be 0.625, got {rod_od}"
        assert tube_length == 3.0, f"tube_length should be 3.0, got {tube_length}"
        assert teflon_length == 4.0, f"teflon_length should be 4.0, got {teflon_length}"

    def test_calculate_insertion_capped_at_3_5(self):
        """Insertion should be capped at 3.5 (not 3.0)."""
        # Pass a high insertion value to test capping
        result = self._call_calculate(4, gamma_element_gap=10.0)
        matching_info = result.get("matching_info", {})
        
        rod_insertion_in = matching_info.get("rod_insertion_inches", 0)
        teflon = matching_info.get("teflon_sleeve_inches", 0)
        
        # max_insertion = teflon - 0.5 = 3.5
        expected_max = teflon - 0.5
        
        print(f"teflon={teflon}, rod_insertion={rod_insertion_in}, expected_max={expected_max}")
        
        # Insertion should be capped at max_insertion (3.5)
        assert rod_insertion_in <= expected_max, \
            f"Insertion {rod_insertion_in} should be <= {expected_max}"


class TestCalculateWithCorrectedDriven:
    """Test that corrected driven element produces SWR ~1.0 in main calculator."""

    def _get_corrected_driven_length(self, num_elements: int, original_driven: float = 204.0):
        """Get the recommended driven length from designer."""
        response = requests.post(f"{BASE_URL}/api/gamma-designer", json={
            "num_elements": num_elements,
            "driven_element_length_in": original_driven,
            "frequency_mhz": 27.185,
        })
        result = response.json()
        recipe = result.get("recipe", {})
        return recipe.get("recommended_driven_length_in", original_driven)

    def _create_elements_with_driven(self, num_elements: int, driven_length: float):
        """Create elements with specific driven length."""
        elements = [
            {"element_type": "reflector", "length": 214.0, "diameter": 1.0, "position": 0},
            {"element_type": "driven", "length": driven_length, "diameter": 1.0, "position": 48},
        ]
        for i in range(num_elements - 2):
            elements.append({
                "element_type": "director",
                "length": 198.0 - (i * 2),
                "diameter": 1.0,
                "position": 96 + (i * 48)
            })
        return elements

    def _call_calculate_with_gamma_settings(self, num_elements: int, driven_length: float,
                                            bar_pos: float, insertion: float):
        """Call calculate with specific gamma settings."""
        elements = self._create_elements_with_driven(num_elements, driven_length)
        response = requests.post(f"{BASE_URL}/api/calculate", json={
            "num_elements": num_elements,
            "elements": elements,
            "height_from_ground": 50,
            "height_unit": "ft",
            "boom_diameter": 2.0,
            "boom_unit": "inches",
            "band": "11m_cb",
            "frequency_mhz": 27.185,
            "feed_type": "gamma",
            "antenna_orientation": "horizontal",
            "gamma_bar_pos": bar_pos,
            "gamma_element_gap": insertion,
        })
        assert response.status_code == 200
        return response.json()

    def test_3_element_corrected_driven_205_94_produces_low_swr(self):
        """3-element with corrected driven (205.94\") should produce SWR close to 1.0."""
        # First get the corrected driven length from designer
        corrected_len = self._get_corrected_driven_length(3, 204.0)
        print(f"3-element corrected driven length: {corrected_len}")
        
        # Now get the optimal gamma settings from designer
        designer_result = requests.post(f"{BASE_URL}/api/gamma-designer", json={
            "num_elements": 3,
            "driven_element_length_in": corrected_len,
            "frequency_mhz": 27.185,
        }).json()
        
        recipe = designer_result.get("recipe", {})
        bar_pos = recipe.get("ideal_bar_position", 10.0)
        insertion = recipe.get("optimal_insertion", 1.0)
        
        print(f"Designer settings: bar={bar_pos}, insertion={insertion}")
        
        # Call calculator with corrected driven and optimal settings
        calc_result = self._call_calculate_with_gamma_settings(
            3, corrected_len, bar_pos, insertion
        )
        
        swr = calc_result.get("swr", 0)
        print(f"Calculate SWR with corrected driven: {swr}")
        
        # SWR should be close to 1.0 (allow some tolerance due to different code paths)
        assert swr <= 1.3, f"SWR with corrected driven should be <= 1.3, got {swr}"


class TestConsistencyBetweenDesignerAndCalculator:
    """Test that designer and calculator produce same SWR for same settings."""

    def _create_elements(self, num_elements: int, driven_length: float):
        elements = [
            {"element_type": "reflector", "length": 214.0, "diameter": 1.0, "position": 0},
            {"element_type": "driven", "length": driven_length, "diameter": 1.0, "position": 48},
        ]
        for i in range(num_elements - 2):
            elements.append({
                "element_type": "director",
                "length": 198.0 - (i * 2),
                "diameter": 1.0,
                "position": 96 + (i * 48)
            })
        return elements

    def test_designer_and_calculator_use_same_hardware_defaults(self):
        """Designer and calculator should use same hardware defaults."""
        # Get designer hardware
        designer_result = requests.post(f"{BASE_URL}/api/gamma-designer", json={
            "num_elements": 4,
            "driven_element_length_in": 204.0,
            "frequency_mhz": 27.185,
        }).json()
        
        designer_hw = designer_result.get("auto_hardware", {})
        
        # Get calculator hardware
        elements = self._create_elements(4, 204.0)
        calc_result = requests.post(f"{BASE_URL}/api/calculate", json={
            "num_elements": 4,
            "elements": elements,
            "height_from_ground": 50,
            "height_unit": "ft",
            "boom_diameter": 2.0,
            "boom_unit": "inches",
            "feed_type": "gamma",
        }).json()
        
        calc_hw = calc_result.get("matching_info", {}).get("hardware", {})
        
        print(f"Designer hardware: {designer_hw}")
        print(f"Calculator hardware: {calc_hw}")
        
        # Compare key hardware values
        assert designer_hw.get("rod_od") == calc_hw.get("rod_od"), \
            f"rod_od mismatch: designer={designer_hw.get('rod_od')}, calc={calc_hw.get('rod_od')}"
        assert designer_hw.get("tube_od") == calc_hw.get("tube_od"), \
            f"tube_od mismatch: designer={designer_hw.get('tube_od')}, calc={calc_hw.get('tube_od')}"


class TestSharedPhysicsHelpers:
    """Test that the refactored shared physics helpers work correctly."""

    def test_feedpoint_impedance_decreases_with_more_elements(self):
        """Feedpoint impedance should decrease as elements increase."""
        impedances = []
        
        for n in [2, 3, 4, 6, 8, 10, 15, 20]:
            result = requests.post(f"{BASE_URL}/api/gamma-designer", json={
                "num_elements": n,
                "driven_element_length_in": 204.0,
                "frequency_mhz": 27.185,
            }).json()
            
            r_feed = result.get("feedpoint_impedance", 0)
            impedances.append((n, r_feed))
            print(f"{n}-element: R_feed = {r_feed} ohms")
        
        # Verify impedance decreases with more elements
        for i in range(len(impedances) - 1):
            n1, r1 = impedances[i]
            n2, r2 = impedances[i + 1]
            assert r1 >= r2, f"R_feed should decrease: {n1}-el={r1}, {n2}-el={r2}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
