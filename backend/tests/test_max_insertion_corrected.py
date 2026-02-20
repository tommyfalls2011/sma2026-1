"""
Test max_insertion constraint correction: max_insertion = tube_length - 0.5 (NOT teflon - 0.5)

Physical constraint explanation:
- Rod physically slides into the 3" tube
- Must stop 0.5" before the far end of the tube
- So max_insertion = 3.0 - 0.5 = 2.5"
- Teflon (4.0") extends 1" past the tube open end for RF arc prevention

Previous iteration_30 used max_insertion = teflon_length - 0.5 = 3.5" (WRONG)
Now corrected to max_insertion = tube_length - 0.5 = 2.5" (CORRECT)

Expected behavior:
- 2-element: null NOT reachable, SWR ~1.23, optimal_insertion = 2.5 (maxed)
- 3-element: null NOT reachable, SWR ~1.09, optimal_insertion = 2.5 (maxed)
- 4-element: null BARELY reachable, SWR ~1.01, optimal_insertion ~2.49
- 6,8,20-element: null reachable, SWR = 1.0
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestMaxInsertionCorrection:
    """Verify max_insertion = tube_length - 0.5 = 2.5 inches (not teflon - 0.5 = 3.5)"""

    def test_gamma_designer_max_insertion_is_2_5(self):
        """Designer should report max_insertion = 2.5 (tube 3.0 - 0.5)"""
        response = requests.post(f"{BASE_URL}/api/gamma-designer", json={
            "num_elements": 3,
            "driven_element_length_in": 204.0,
            "frequency_mhz": 27.185
        })
        assert response.status_code == 200, f"API failed: {response.text}"
        data = response.json()
        
        # Check recipe has correct hardware
        recipe = data.get("recipe", {})
        assert recipe.get("tube_length") == 3.0, f"tube_length should be 3.0, got {recipe.get('tube_length')}"
        assert recipe.get("teflon_length") == 4.0, f"teflon_length should be 4.0, got {recipe.get('teflon_length')}"
        assert recipe.get("rod_od") == 0.625, f"rod_od should be 0.625, got {recipe.get('rod_od')}"
        
        # Verify insertion_sweep max is 2.5 (not 3.0 or 3.5)
        ins_sweep = data.get("insertion_sweep", [])
        assert len(ins_sweep) > 0, "insertion_sweep should not be empty"
        max_insertion_in_sweep = max(p.get("insertion_inches", 0) for p in ins_sweep)
        # The sweep goes from 0% to 100% of max_insertion, so max should be 2.5
        assert 2.4 <= max_insertion_in_sweep <= 2.6, f"max insertion in sweep should be ~2.5, got {max_insertion_in_sweep}"
        print(f"✓ Insertion sweep max: {max_insertion_in_sweep}")
        
    def test_2_element_null_not_reachable_swr_approx_1_23(self):
        """2-element: null NOT reachable, SWR ~1.23, optimal_insertion maxed at 2.5"""
        response = requests.post(f"{BASE_URL}/api/gamma-designer", json={
            "num_elements": 2,
            "driven_element_length_in": 208.0,
            "frequency_mhz": 27.185
        })
        assert response.status_code == 200, f"API failed: {response.text}"
        data = response.json()
        
        recipe = data.get("recipe", {})
        null_reachable = recipe.get("null_reachable", True)
        optimal_insertion = recipe.get("optimal_insertion", 0)
        swr = recipe.get("swr_at_null", 99.0)
        
        # 2-element: R_feed is higher (~36Ω), null not reachable with standard hardware
        assert null_reachable == False, f"2-element should have null_reachable=False, got {null_reachable}"
        # Since null not reachable, optimal_insertion should be maxed at 2.5
        assert 2.4 <= optimal_insertion <= 2.5, f"optimal_insertion should be ~2.5 (maxed), got {optimal_insertion}"
        # SWR should be > 1.0 since null not reachable (expect ~1.23)
        assert 1.1 <= swr <= 1.4, f"2-element SWR should be ~1.23, got {swr}"
        print(f"✓ 2-element: SWR={swr}, null_reachable={null_reachable}, optimal_insertion={optimal_insertion}")

    def test_3_element_null_not_reachable_swr_approx_1_09(self):
        """3-element: null NOT reachable, SWR ~1.09, optimal_insertion maxed at 2.5"""
        response = requests.post(f"{BASE_URL}/api/gamma-designer", json={
            "num_elements": 3,
            "driven_element_length_in": 204.0,
            "frequency_mhz": 27.185
        })
        assert response.status_code == 200, f"API failed: {response.text}"
        data = response.json()
        
        recipe = data.get("recipe", {})
        null_reachable = recipe.get("null_reachable", True)
        optimal_insertion = recipe.get("optimal_insertion", 0)
        swr = recipe.get("swr_at_null", 99.0)
        
        # 3-element should NOT reach null with max 2.5" insertion
        assert null_reachable == False, f"3-element should have null_reachable=False, got {null_reachable}"
        # Insertion should be maxed at 2.5
        assert 2.4 <= optimal_insertion <= 2.5, f"optimal_insertion should be ~2.5 (maxed), got {optimal_insertion}"
        # SWR should be close to 1.0 but not exactly (expect ~1.09)
        assert 1.0 <= swr <= 1.2, f"3-element SWR should be ~1.09, got {swr}"
        print(f"✓ 3-element: SWR={swr}, null_reachable={null_reachable}, optimal_insertion={optimal_insertion}")

    def test_4_element_barely_reaches_null_swr_1_01(self):
        """4-element: null BARELY reachable, SWR ~1.01, optimal_insertion ~2.49"""
        response = requests.post(f"{BASE_URL}/api/gamma-designer", json={
            "num_elements": 4,
            "driven_element_length_in": 203.0,
            "frequency_mhz": 27.185
        })
        assert response.status_code == 200, f"API failed: {response.text}"
        data = response.json()
        
        recipe = data.get("recipe", {})
        null_reachable = recipe.get("null_reachable", False)
        optimal_insertion = recipe.get("optimal_insertion", 0)
        swr = recipe.get("swr_at_null", 99.0)
        
        # 4-element should BARELY reach null
        assert null_reachable == True, f"4-element should have null_reachable=True (barely), got {null_reachable}"
        # Insertion should be very close to max (2.49 or 2.5)
        assert 2.4 <= optimal_insertion <= 2.5, f"optimal_insertion should be ~2.49, got {optimal_insertion}"
        # SWR should be very close to 1.0 (expect ~1.01)
        assert 1.0 <= swr <= 1.05, f"4-element SWR should be ~1.01, got {swr}"
        print(f"✓ 4-element: SWR={swr}, null_reachable={null_reachable}, optimal_insertion={optimal_insertion}")

    def test_6_element_null_reachable_swr_1_0(self):
        """6-element: null reachable, SWR = 1.0"""
        response = requests.post(f"{BASE_URL}/api/gamma-designer", json={
            "num_elements": 6,
            "driven_element_length_in": 203.0,
            "frequency_mhz": 27.185
        })
        assert response.status_code == 200, f"API failed: {response.text}"
        data = response.json()
        
        recipe = data.get("recipe", {})
        null_reachable = recipe.get("null_reachable", False)
        optimal_insertion = recipe.get("optimal_insertion", 0)
        swr = recipe.get("swr_at_null", 99.0)
        
        # 6-element has lower R_feed, should reach null within 2.5" insertion
        assert null_reachable == True, f"6-element should have null_reachable=True, got {null_reachable}"
        assert swr == 1.0, f"6-element SWR should be 1.0, got {swr}"
        # Insertion should be < 2.5 (null found before max)
        assert optimal_insertion < 2.5, f"6-element insertion should be < 2.5 (null found before max), got {optimal_insertion}"
        print(f"✓ 6-element: SWR={swr}, null_reachable={null_reachable}, optimal_insertion={optimal_insertion}")

    def test_8_element_null_reachable_swr_1_0(self):
        """8-element: null reachable, SWR = 1.0"""
        response = requests.post(f"{BASE_URL}/api/gamma-designer", json={
            "num_elements": 8,
            "driven_element_length_in": 203.0,
            "frequency_mhz": 27.185
        })
        assert response.status_code == 200, f"API failed: {response.text}"
        data = response.json()
        
        recipe = data.get("recipe", {})
        null_reachable = recipe.get("null_reachable", False)
        optimal_insertion = recipe.get("optimal_insertion", 0)
        swr = recipe.get("swr_at_null", 99.0)
        
        assert null_reachable == True, f"8-element should have null_reachable=True, got {null_reachable}"
        assert swr == 1.0, f"8-element SWR should be 1.0, got {swr}"
        print(f"✓ 8-element: SWR={swr}, null_reachable={null_reachable}, optimal_insertion={optimal_insertion}")

    def test_20_element_null_reachable_swr_1_0(self):
        """20-element: null reachable, SWR = 1.0"""
        response = requests.post(f"{BASE_URL}/api/gamma-designer", json={
            "num_elements": 20,
            "driven_element_length_in": 203.0,
            "frequency_mhz": 27.185
        })
        assert response.status_code == 200, f"API failed: {response.text}"
        data = response.json()
        
        recipe = data.get("recipe", {})
        null_reachable = recipe.get("null_reachable", False)
        optimal_insertion = recipe.get("optimal_insertion", 0)
        swr = recipe.get("swr_at_null", 99.0)
        
        assert null_reachable == True, f"20-element should have null_reachable=True, got {null_reachable}"
        assert swr == 1.0, f"20-element SWR should be 1.0, got {swr}"
        print(f"✓ 20-element: SWR={swr}, null_reachable={null_reachable}, optimal_insertion={optimal_insertion}")


class TestCalculateInsertionCapping:
    """Verify /api/calculate caps insertion at 2.5 (max_insertion)"""

    def test_insertion_3_5_capped_to_2_5(self):
        """Insertion value of 3.5 should be capped to 2.5"""
        response = requests.post(f"{BASE_URL}/api/calculate", json={
            "num_elements": 3,
            "band": "11m_cb",
            "frequency_mhz": 27.185,
            "height_from_ground": 30,
            "height_unit": "ft",
            "boom_diameter": 2.0,
            "boom_unit": "inches",
            "antenna_orientation": "horizontal",
            "boom_grounded": True,
            "boom_mount": "bonded",
            "feed_type": "gamma",
            "gamma_element_gap": 3.5,  # Request 3.5" insertion (beyond max)
            "elements": [
                {"element_type": "reflector", "position": 0, "length": 214.0, "diameter": 0.75},
                {"element_type": "driven", "position": 48, "length": 204.0, "diameter": 0.75},
                {"element_type": "director", "position": 96, "length": 194.0, "diameter": 0.75}
            ]
        })
        assert response.status_code == 200, f"API failed: {response.text}"
        data = response.json()
        
        matching_info = data.get("matching_info", {})
        rod_insertion = matching_info.get("rod_insertion_inches", 99)
        
        # rod_insertion should be capped at 2.5, not 3.5
        assert rod_insertion <= 2.5, f"rod_insertion should be capped to 2.5, got {rod_insertion}"
        print(f"✓ Requested insertion=3.5, actual capped to: {rod_insertion}")
        
        # Verify hardware shows correct values
        hardware = matching_info.get("hardware", {})
        assert hardware.get("tube_length") == 3.0, f"tube_length should be 3.0, got {hardware.get('tube_length')}"
        assert hardware.get("teflon_length") == 4.0, f"teflon_length should be 4.0, got {hardware.get('teflon_length')}"
        assert hardware.get("rod_od") == 0.625, f"rod_od should be 0.625, got {hardware.get('rod_od')}"

    def test_insertion_within_limit_not_capped(self):
        """Insertion value of 2.0 should NOT be capped (within 2.5 limit)"""
        response = requests.post(f"{BASE_URL}/api/calculate", json={
            "num_elements": 3,
            "band": "11m_cb",
            "frequency_mhz": 27.185,
            "height_from_ground": 30,
            "height_unit": "ft",
            "boom_diameter": 2.0,
            "boom_unit": "inches",
            "antenna_orientation": "horizontal",
            "boom_grounded": True,
            "boom_mount": "bonded",
            "feed_type": "gamma",
            "gamma_element_gap": 2.0,  # Request 2.0" insertion (within limit)
            "elements": [
                {"element_type": "reflector", "position": 0, "length": 214.0, "diameter": 0.75},
                {"element_type": "driven", "position": 48, "length": 204.0, "diameter": 0.75},
                {"element_type": "director", "position": 96, "length": 194.0, "diameter": 0.75}
            ]
        })
        assert response.status_code == 200, f"API failed: {response.text}"
        data = response.json()
        
        matching_info = data.get("matching_info", {})
        rod_insertion = matching_info.get("rod_insertion_inches", 99)
        
        # rod_insertion should be 2.0 (not capped since within limit)
        assert rod_insertion == 2.0, f"rod_insertion should be 2.0, got {rod_insertion}"
        print(f"✓ Requested insertion=2.0, actual: {rod_insertion}")


class TestInsertionSweepRange:
    """Verify insertion_sweep shows data points from 0 to 2.5 (not 3.0 or 3.5)"""

    def test_insertion_sweep_max_is_2_5(self):
        """Insertion sweep should have max value of 2.5, not 3.0 or 3.5"""
        response = requests.post(f"{BASE_URL}/api/gamma-designer", json={
            "num_elements": 4,
            "driven_element_length_in": 203.0,
            "frequency_mhz": 27.185
        })
        assert response.status_code == 200, f"API failed: {response.text}"
        data = response.json()
        
        ins_sweep = data.get("insertion_sweep", [])
        assert len(ins_sweep) > 0, "insertion_sweep should not be empty"
        
        max_ins = max(p.get("insertion_inches", 0) for p in ins_sweep)
        min_ins = min(p.get("insertion_inches", 0) for p in ins_sweep)
        
        print(f"Insertion sweep range: {min_ins} to {max_ins}")
        
        # Max should be ~2.5 (100% of max_insertion)
        assert 2.4 <= max_ins <= 2.6, f"max insertion in sweep should be ~2.5, got {max_ins}"
        # Min should be ~0
        assert min_ins < 0.1, f"min insertion in sweep should be ~0, got {min_ins}"
        
        # Verify no points exceed 2.5
        for point in ins_sweep:
            ins_val = point.get("insertion_inches", 0)
            assert ins_val <= 2.51, f"insertion point {ins_val} exceeds max 2.5"


class TestAutoHardwareRodOd:
    """Verify auto_hardware.rod_od = 0.625 for all element counts"""

    @pytest.mark.parametrize("num_elements", [2, 3, 4, 6, 8, 20])
    def test_rod_od_is_0_625_for_all_elements(self, num_elements):
        """rod_od should be 0.625 for all element counts"""
        response = requests.post(f"{BASE_URL}/api/gamma-designer", json={
            "num_elements": num_elements,
            "driven_element_length_in": 204.0,
            "frequency_mhz": 27.185
        })
        assert response.status_code == 200, f"API failed: {response.text}"
        data = response.json()
        
        recipe = data.get("recipe", {})
        rod_od = recipe.get("rod_od")
        
        assert rod_od == 0.625, f"{num_elements}-element: rod_od should be 0.625, got {rod_od}"
        print(f"✓ {num_elements}-element: rod_od={rod_od}")


class TestHardwareConsistency:
    """Verify hardware defaults are consistent between designer and calculator"""

    def test_hardware_tube_3_teflon_4_rod_0625(self):
        """Both APIs should use tube=3.0, teflon=4.0, rod_od=0.625"""
        # Test designer
        designer_resp = requests.post(f"{BASE_URL}/api/gamma-designer", json={
            "num_elements": 3,
            "driven_element_length_in": 204.0,
            "frequency_mhz": 27.185
        })
        assert designer_resp.status_code == 200
        designer_data = designer_resp.json()
        recipe = designer_data.get("recipe", {})
        
        # Test calculator
        calc_resp = requests.post(f"{BASE_URL}/api/calculate", json={
            "num_elements": 3,
            "band": "11m_cb",
            "frequency_mhz": 27.185,
            "height_from_ground": 30,
            "height_unit": "ft",
            "boom_diameter": 2.0,
            "boom_unit": "inches",
            "antenna_orientation": "horizontal",
            "boom_grounded": True,
            "boom_mount": "bonded",
            "feed_type": "gamma",
            "elements": [
                {"element_type": "reflector", "position": 0, "length": 214.0, "diameter": 0.75},
                {"element_type": "driven", "position": 48, "length": 204.0, "diameter": 0.75},
                {"element_type": "director", "position": 96, "length": 194.0, "diameter": 0.75}
            ]
        })
        assert calc_resp.status_code == 200
        calc_data = calc_resp.json()
        hardware = calc_data.get("matching_info", {}).get("hardware", {})
        
        # Verify both use the same values
        assert recipe.get("tube_length") == 3.0, f"Designer tube_length should be 3.0, got {recipe.get('tube_length')}"
        assert recipe.get("teflon_length") == 4.0, f"Designer teflon_length should be 4.0, got {recipe.get('teflon_length')}"
        assert recipe.get("rod_od") == 0.625, f"Designer rod_od should be 0.625, got {recipe.get('rod_od')}"
        
        assert hardware.get("tube_length") == 3.0, f"Calculator tube_length should be 3.0, got {hardware.get('tube_length')}"
        assert hardware.get("teflon_length") == 4.0, f"Calculator teflon_length should be 4.0, got {hardware.get('teflon_length')}"
        assert hardware.get("rod_od") == 0.625, f"Calculator rod_od should be 0.625, got {hardware.get('rod_od')}"
        
        print("✓ Hardware consistency verified: tube=3.0, teflon=4.0, rod_od=0.625")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
