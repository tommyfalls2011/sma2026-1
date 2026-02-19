"""
Test P0 Bug Fix: SWR Curve and Smith Chart Physics
---------------------------------------------------
Tests the fix for the bug where applying gamma match designer recipe caused
the main SWR meter to show antenna tuned to a higher frequency than 27.185 MHz.

Root cause was:
1. Hardcoded rod dimensions (3.5/0.375) in Smith Chart code
2. SWR curve used parabolic approximation instead of full physics

Fix:
1. Smith Chart now uses z0_gamma from matching_info (actual hardware)
2. SWR curve is derived from Smith Chart reflection coefficients
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Standard 3-element Yagi payload for 27.185 MHz
YAGI_3EL_BASE = {
    "num_elements": 3,
    "elements": [
        {"element_type": "reflector", "length": 213.5, "diameter": 0.5, "position": 0},
        {"element_type": "driven", "length": 203.0, "diameter": 0.5, "position": 36},
        {"element_type": "director", "length": 194.0, "diameter": 0.5, "position": 78}
    ],
    "height_from_ground": 35,
    "height_unit": "ft",
    "boom_diameter": 2.0,
    "boom_unit": "inches",
    "band": "11m_cb",
    "frequency_mhz": 27.185
}


class TestSWRCurvePhysics:
    """Tests that SWR curve minimum is at/near operating frequency for all feed types."""

    def test_gamma_feed_swr_minimum_at_operating_freq(self):
        """P0 BUG FIX: Gamma feed SWR curve minimum should be at/near 27.185 MHz, not higher."""
        payload = {**YAGI_3EL_BASE,
                   "feed_type": "gamma",
                   "gamma_rod_dia": 0.375,
                   "gamma_rod_spacing": 3.5,
                   "gamma_bar_pos": 12.27,
                   "gamma_element_gap": 10.66,
                   "gamma_tube_od": 0.625}
        
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
        assert response.status_code == 200, f"API returned {response.status_code}: {response.text}"
        
        data = response.json()
        swr_curve = data.get("swr_curve", [])
        assert len(swr_curve) > 0, "SWR curve should not be empty"
        
        # Find minimum SWR point
        min_point = min(swr_curve, key=lambda p: p["swr"])
        min_freq = min_point["frequency"]
        min_swr = min_point["swr"]
        operating_freq = 27.185
        
        # The minimum should be within ±0.3 MHz of operating frequency (not ~27.5 MHz as before bug)
        freq_deviation = abs(min_freq - operating_freq)
        print(f"SWR curve minimum: {min_swr:.3f} at {min_freq:.3f} MHz (deviation: {freq_deviation:.3f} MHz)")
        
        assert freq_deviation < 0.3, f"SWR minimum at {min_freq} MHz is too far from operating freq {operating_freq} MHz (deviation: {freq_deviation:.3f} MHz > 0.3 MHz allowed)"
        assert min_swr < 2.5, f"Minimum SWR {min_swr} is too high for a matched gamma antenna"

    def test_direct_feed_swr_curve(self):
        """Direct feed SWR curve should be valid and physics-based."""
        payload = {**YAGI_3EL_BASE, "feed_type": "direct"}
        
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        swr_curve = data.get("swr_curve", [])
        assert len(swr_curve) > 0
        
        # Direct feed without matching will have higher SWR (feedpoint ~25Ω vs 50Ω cable)
        min_point = min(swr_curve, key=lambda p: p["swr"])
        print(f"Direct feed SWR minimum: {min_point['swr']:.3f} at {min_point['frequency']:.3f} MHz")
        
        # SWR curve should span the operating frequency range
        freqs = [p["frequency"] for p in swr_curve]
        assert min(freqs) < 27.0, "SWR curve should include frequencies below 27 MHz"
        assert max(freqs) > 27.3, "SWR curve should include frequencies above 27.3 MHz"

    def test_hairpin_feed_swr_curve(self):
        """Hairpin feed SWR curve should be valid."""
        payload = {**YAGI_3EL_BASE, "feed_type": "hairpin"}
        
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        swr_curve = data.get("swr_curve", [])
        assert len(swr_curve) > 0
        
        min_point = min(swr_curve, key=lambda p: p["swr"])
        print(f"Hairpin feed SWR minimum: {min_point['swr']:.3f} at {min_point['frequency']:.3f} MHz")
        
        # Hairpin should achieve good match
        assert min_point["swr"] < 3.0, "Hairpin feed should achieve reasonable SWR"


class TestGammaDesignerConsistency:
    """Tests that gamma designer recipe produces consistent SWR with main calculator."""

    def test_designer_recipe_null_reachable_for_3el(self):
        """Gamma designer should return null_reachable=true for standard 3-element Yagi."""
        payload = {
            "num_elements": 3,
            "driven_element_length_in": 203.0,
            "frequency_mhz": 27.185
        }
        
        response = requests.post(f"{BASE_URL}/api/gamma-designer", json=payload)
        assert response.status_code == 200, f"API returned {response.status_code}: {response.text}"
        
        data = response.json()
        assert "error" not in data, f"Designer returned error: {data.get('error')}"
        assert data.get("null_reachable") == True, f"3-element Yagi should have null_reachable=true, got {data.get('null_reachable')}"
        
        # Check recipe has valid tuning settings
        assert "ideal_bar_position_inches" in data, "Recipe should include ideal_bar_position_inches"
        assert "optimal_insertion_inches" in data, "Recipe should include optimal_insertion_inches"
        assert data["ideal_bar_position_inches"] > 0, "Bar position should be positive"
        
        print(f"Designer recipe: bar={data['ideal_bar_position_inches']:.2f}\", insertion={data['optimal_insertion_inches']:.2f}\", SWR={data.get('swr_at_null', 'N/A')}")

    def test_designer_recipe_applied_to_calculator_swr_matches(self):
        """Applying designer recipe values to /api/calculate should give consistent SWR."""
        # Step 1: Get designer recipe
        designer_payload = {
            "num_elements": 3,
            "driven_element_length_in": 203.0,
            "frequency_mhz": 27.185
        }
        designer_response = requests.post(f"{BASE_URL}/api/gamma-designer", json=designer_payload)
        assert designer_response.status_code == 200
        recipe = designer_response.json()
        assert "error" not in recipe
        
        bar_pos = recipe["ideal_bar_position_inches"]
        insertion = recipe["optimal_insertion_inches"]
        rod_od = recipe.get("rod_od_inches", 0.375)
        tube_od = recipe.get("tube_od_inches", 0.625)
        rod_spacing = recipe.get("rod_spacing_inches", 3.5)
        designer_swr = recipe.get("swr_at_null", 1.0)
        
        print(f"Designer recipe: bar={bar_pos:.2f}\", insertion={insertion:.2f}\", rod={rod_od:.3f}\", tube={tube_od:.3f}\", SWR={designer_swr:.3f}")
        
        # Step 2: Apply recipe to calculator
        calc_payload = {
            **YAGI_3EL_BASE,
            "feed_type": "gamma",
            "gamma_rod_dia": rod_od,
            "gamma_rod_spacing": rod_spacing,
            "gamma_bar_pos": bar_pos,
            "gamma_element_gap": insertion,
            "gamma_tube_od": tube_od
        }
        calc_response = requests.post(f"{BASE_URL}/api/calculate", json=calc_payload)
        assert calc_response.status_code == 200
        calc_data = calc_response.json()
        
        main_swr = calc_data["swr"]
        
        # Step 3: Check SWR curve minimum is at/near operating frequency
        swr_curve = calc_data.get("swr_curve", [])
        if swr_curve:
            min_point = min(swr_curve, key=lambda p: p["swr"])
            min_freq = min_point["frequency"]
            operating_freq = 27.185
            freq_deviation = abs(min_freq - operating_freq)
            
            print(f"Calculator main SWR: {main_swr:.3f}")
            print(f"SWR curve minimum: {min_point['swr']:.3f} at {min_freq:.3f} MHz (deviation: {freq_deviation:.3f} MHz)")
            
            # KEY TEST: SWR at minimum should be close to main SWR
            swr_diff = abs(min_point["swr"] - main_swr)
            assert swr_diff < 0.5, f"SWR curve minimum ({min_point['swr']:.3f}) differs too much from main SWR ({main_swr:.3f})"
            
            # KEY TEST: Minimum should be at/near operating frequency
            assert freq_deviation < 0.3, f"SWR minimum at {min_freq:.3f} MHz, expected near {operating_freq} MHz"


class TestSmithChartPhysics:
    """Tests that Smith Chart uses actual hardware z0_gamma, not hardcoded defaults."""

    def test_smith_chart_uses_actual_z0_gamma(self):
        """Smith Chart should use z0_gamma from matching_info (actual hardware dimensions)."""
        # Use custom hardware with different z0_gamma than default 3.5"/0.375"
        # Larger rod spacing = higher z0_gamma
        payload = {
            **YAGI_3EL_BASE,
            "feed_type": "gamma",
            "gamma_rod_dia": 0.5,        # Larger rod
            "gamma_rod_spacing": 5.0,    # Wider spacing = higher z0_gamma
            "gamma_bar_pos": 12.0,
            "gamma_element_gap": 8.0,
            "gamma_tube_od": 0.75
        }
        
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
        assert response.status_code == 200
        data = response.json()
        
        # Check matching_info contains z0_gamma
        matching_info = data.get("matching_info", {})
        z0_gamma = matching_info.get("z0_gamma")
        
        assert z0_gamma is not None, "matching_info should include z0_gamma"
        
        # z0_gamma = 276 * log10(2 * spacing / rod_dia)
        # For spacing=5.0, rod=0.5: z0 = 276 * log10(2*5.0/0.5) = 276 * log10(20) ≈ 359 ohms
        # This should be different from default (spacing=3.5, rod=0.375): z0 ≈ 276 * log10(18.67) ≈ 351 ohms
        expected_z0 = 276 * 1.301  # log10(20) ≈ 1.301
        
        print(f"Custom hardware z0_gamma: {z0_gamma:.1f} ohms (expected ~{expected_z0:.1f} ohms)")
        
        # z0_gamma should reflect the custom hardware, not hardcoded 300 ohms
        assert 340 < z0_gamma < 380, f"z0_gamma {z0_gamma} should be ~359 ohms for spacing=5.0, rod=0.5"

    def test_smith_chart_data_has_valid_structure(self):
        """Smith Chart data should have proper impedance sweep structure."""
        payload = {**YAGI_3EL_BASE, "feed_type": "gamma",
                   "gamma_rod_dia": 0.375, "gamma_rod_spacing": 3.5,
                   "gamma_bar_pos": 12.0, "gamma_element_gap": 10.0, "gamma_tube_od": 0.625}
        
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
        assert response.status_code == 200
        data = response.json()
        
        smith_chart = data.get("smith_chart_data", [])
        assert len(smith_chart) > 0, "Smith chart data should not be empty"
        
        # Check structure
        first_point = smith_chart[0]
        assert "freq" in first_point, "Smith chart points should have 'freq'"
        assert "z_real" in first_point, "Smith chart points should have 'z_real'"
        assert "z_imag" in first_point, "Smith chart points should have 'z_imag'"
        assert "gamma_real" in first_point, "Smith chart points should have 'gamma_real'"
        assert "gamma_imag" in first_point, "Smith chart points should have 'gamma_imag'"
        
        # Check frequencies span around operating frequency
        freqs = [p["freq"] for p in smith_chart]
        assert min(freqs) < 27.0, "Smith chart should include frequencies below 27 MHz"
        assert max(freqs) > 27.3, "Smith chart should include frequencies above 27.3 MHz"
        
        print(f"Smith chart: {len(smith_chart)} points from {min(freqs):.3f} to {max(freqs):.3f} MHz")


class TestSWRCurveDerivedFromSmithChart:
    """Tests that SWR curve is properly derived from Smith Chart reflection coefficients."""

    def test_swr_curve_matches_smith_chart_gamma(self):
        """SWR curve values should match |Γ| from Smith Chart data."""
        payload = {**YAGI_3EL_BASE, "feed_type": "gamma",
                   "gamma_rod_dia": 0.375, "gamma_rod_spacing": 3.5,
                   "gamma_bar_pos": 12.0, "gamma_element_gap": 10.0, "gamma_tube_od": 0.625}
        
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
        assert response.status_code == 200
        data = response.json()
        
        swr_curve = data.get("swr_curve", [])
        smith_chart = data.get("smith_chart_data", [])
        
        assert len(swr_curve) == len(smith_chart), "SWR curve and Smith chart should have same number of points"
        
        # Verify SWR = (1+|Γ|)/(1-|Γ|) for each point
        import math
        mismatches = []
        for i, (swr_pt, sc_pt) in enumerate(zip(swr_curve, smith_chart)):
            gamma_mag = math.sqrt(sc_pt["gamma_real"]**2 + sc_pt["gamma_imag"]**2)
            gamma_mag = min(gamma_mag, 0.999)
            expected_swr = (1 + gamma_mag) / (1 - gamma_mag) if gamma_mag < 1.0 else 99.0
            expected_swr = max(1.0, min(expected_swr, 10.0))
            
            if abs(swr_pt["swr"] - expected_swr) > 0.1:
                mismatches.append(f"Point {i}: freq={swr_pt['frequency']:.3f}, SWR={swr_pt['swr']:.2f}, expected={expected_swr:.2f}")
        
        if mismatches:
            print(f"Mismatches found: {len(mismatches)}")
            for m in mismatches[:5]:
                print(f"  {m}")
        
        assert len(mismatches) == 0, f"SWR curve should match Smith Chart Γ: {len(mismatches)} mismatches"


class TestFeedTypeComparison:
    """Compare SWR behavior across different feed types."""

    def test_gamma_vs_direct_feed_swr(self):
        """Gamma feed should achieve better SWR than direct feed for 3-element Yagi."""
        # Direct feed (unmatched)
        direct_payload = {**YAGI_3EL_BASE, "feed_type": "direct"}
        direct_response = requests.post(f"{BASE_URL}/api/calculate", json=direct_payload)
        assert direct_response.status_code == 200
        direct_swr = direct_response.json()["swr"]
        
        # Gamma feed with designer recipe
        designer_response = requests.post(f"{BASE_URL}/api/gamma-designer", json={
            "num_elements": 3,
            "driven_element_length_in": 203.0,
            "frequency_mhz": 27.185
        })
        recipe = designer_response.json()
        
        gamma_payload = {
            **YAGI_3EL_BASE,
            "feed_type": "gamma",
            "gamma_rod_dia": recipe.get("rod_od_inches", 0.375),
            "gamma_rod_spacing": recipe.get("rod_spacing_inches", 3.5),
            "gamma_bar_pos": recipe["ideal_bar_position_inches"],
            "gamma_element_gap": recipe["optimal_insertion_inches"],
            "gamma_tube_od": recipe.get("tube_od_inches", 0.625)
        }
        gamma_response = requests.post(f"{BASE_URL}/api/calculate", json=gamma_payload)
        assert gamma_response.status_code == 200
        gamma_swr = gamma_response.json()["swr"]
        
        print(f"Direct feed SWR: {direct_swr:.3f}")
        print(f"Gamma feed SWR (with designer recipe): {gamma_swr:.3f}")
        
        # Gamma should be better (lower SWR)
        assert gamma_swr < direct_swr, f"Gamma SWR ({gamma_swr}) should be lower than direct SWR ({direct_swr})"
        assert gamma_swr < 2.0, f"Gamma with designer recipe should achieve SWR < 2.0, got {gamma_swr}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
