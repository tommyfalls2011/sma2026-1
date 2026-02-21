"""
Hairpin Match Designer API Tests - Full Coverage
Tests: POST /api/hairpin-designer and POST /api/calculate with feed_type=hairpin
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = "https://monthly-billing-5.preview.emergentagent.com"


class TestHairpinDesignerRecipe:
    """Tests for POST /api/hairpin-designer recipe fields"""
    
    def test_hairpin_recipe_standard_4element(self):
        """Test hairpin designer returns recipe with all required fields for 4-element Yagi"""
        response = requests.post(f"{BASE_URL}/api/hairpin-designer", json={
            "num_elements": 4,
            "frequency_mhz": 27.185,
            "driven_element_length_in": 198,
            "reflector_spacing_in": 48,
            "director_spacings_in": [58, 56]
        })
        assert response.status_code == 200
        data = response.json()
        
        # Verify recipe object exists
        assert "recipe" in data
        recipe = data["recipe"]
        
        # Verify all required recipe fields
        assert "rod_dia" in recipe
        assert "rod_spacing" in recipe
        assert "z0" in recipe
        assert "ideal_hairpin_length_in" in recipe
        assert "swr_at_best" in recipe
        assert "shorten_per_side_in" in recipe
        assert "shortened_total_length_in" in recipe
        
        # Verify data types and ranges
        assert isinstance(recipe["rod_dia"], (int, float))
        assert recipe["rod_dia"] > 0
        assert isinstance(recipe["rod_spacing"], (int, float))
        assert recipe["rod_spacing"] > 0
        assert isinstance(recipe["z0"], (int, float))
        assert recipe["z0"] > 0
        assert isinstance(recipe["ideal_hairpin_length_in"], (int, float))
        assert recipe["ideal_hairpin_length_in"] > 0
        assert isinstance(recipe["swr_at_best"], (int, float))
        assert recipe["swr_at_best"] >= 1.0
        
        print(f"✓ Recipe: rod_dia={recipe['rod_dia']}\", rod_spacing={recipe['rod_spacing']}\", z0={recipe['z0']}Ω")
        print(f"✓ Ideal hairpin length: {recipe['ideal_hairpin_length_in']}\"")
        print(f"✓ SWR at best: {recipe['swr_at_best']}")
        print(f"✓ Shorten per side: {recipe['shorten_per_side_in']}\"")
        print(f"✓ Shortened total length: {recipe['shortened_total_length_in']}\"")


class TestHairpinDesignerLengthSweep:
    """Tests for length_sweep array with SWR and power data"""
    
    def test_length_sweep_data_structure(self):
        """Test that length_sweep contains swr, gamma, p_reflected_w, z_in_r, z_in_x for each point"""
        response = requests.post(f"{BASE_URL}/api/hairpin-designer", json={
            "num_elements": 4,
            "frequency_mhz": 27.185,
            "driven_element_length_in": 198,
            "reflector_spacing_in": 48,
            "director_spacings_in": [58, 56]
        })
        assert response.status_code == 200
        data = response.json()
        
        assert "length_sweep" in data
        sweep = data["length_sweep"]
        assert isinstance(sweep, list)
        assert len(sweep) > 0
        
        # Check first point has all required fields
        pt = sweep[0]
        required_fields = ["swr", "gamma", "p_reflected_w", "z_in_r", "z_in_x"]
        for field in required_fields:
            assert field in pt, f"Missing field: {field}"
        
        # Check data types
        assert isinstance(pt["swr"], (int, float))
        assert isinstance(pt["gamma"], (int, float))
        assert isinstance(pt["p_reflected_w"], (int, float))
        assert isinstance(pt["z_in_r"], (int, float))
        assert isinstance(pt["z_in_x"], (int, float))
        
        # Verify SWR minimum is close to 1.0 (best match)
        swrs = [p["swr"] for p in sweep]
        min_swr = min(swrs)
        assert min_swr < 1.5, f"Best SWR should be < 1.5, got {min_swr}"
        
        print(f"✓ Length sweep has {len(sweep)} points")
        print(f"✓ Best SWR in sweep: {min_swr:.3f}")
        print(f"✓ Sample point: SWR={pt['swr']}, gamma={pt['gamma']}, z_in={pt['z_in_r']}+{pt['z_in_x']}j")


class TestHairpinAutoHardwareSelection:
    """Tests for automatic hardware selection giving SWR close to 1.0"""
    
    def test_auto_hardware_selects_best_match(self):
        """Test that auto hardware selection gives SWR close to 1.0"""
        response = requests.post(f"{BASE_URL}/api/hairpin-designer", json={
            "num_elements": 4,
            "frequency_mhz": 27.185,
            "driven_element_length_in": 198,
            "reflector_spacing_in": 48,
            "director_spacings_in": [58, 56]
        })
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("hardware_source") == "auto"
        recipe = data["recipe"]
        
        # SWR at best should be close to 1.0 for auto-selected hardware
        assert recipe["swr_at_best"] < 1.2, f"Auto-selected hardware should give SWR < 1.2, got {recipe['swr_at_best']}"
        
        print(f"✓ Hardware source: auto")
        print(f"✓ Auto-selected: rod_dia={recipe['rod_dia']}\", rod_spacing={recipe['rod_spacing']}\"")
        print(f"✓ SWR at best: {recipe['swr_at_best']} (close to 1.0)")


class TestHairpinCustomHardware:
    """Tests for custom_rod_dia and custom_rod_spacing parameters"""
    
    def test_custom_hardware_override(self):
        """Test that custom_rod_dia and custom_rod_spacing override auto-selection"""
        custom_rod_dia = 0.375
        custom_rod_spacing = 1.5
        
        response = requests.post(f"{BASE_URL}/api/hairpin-designer", json={
            "num_elements": 4,
            "frequency_mhz": 27.185,
            "driven_element_length_in": 198,
            "reflector_spacing_in": 48,
            "director_spacings_in": [58, 56],
            "custom_rod_dia": custom_rod_dia,
            "custom_rod_spacing": custom_rod_spacing
        })
        assert response.status_code == 200
        data = response.json()
        
        # Verify custom hardware is used
        assert data.get("hardware_source") == "custom"
        recipe = data["recipe"]
        assert recipe["rod_dia"] == custom_rod_dia
        assert recipe["rod_spacing"] == custom_rod_spacing
        
        # Verify Z0 is calculated for custom hardware
        # Z0 = 276 * log10(2 * spacing / dia)
        import math
        expected_z0 = 276.0 * math.log10(2.0 * custom_rod_spacing / custom_rod_dia)
        assert abs(recipe["z0"] - expected_z0) < 1.0, f"Z0 mismatch: expected ~{expected_z0:.1f}, got {recipe['z0']}"
        
        print(f"✓ Hardware source: custom")
        print(f"✓ Custom hardware used: rod_dia={recipe['rod_dia']}\", rod_spacing={recipe['rod_spacing']}\"")
        print(f"✓ Z0 calculated: {recipe['z0']}Ω (expected ~{expected_z0:.1f}Ω)")


class TestHairpinTopologyNote:
    """Tests for 2-element Yagi with R>=50 returning topology_note"""
    
    def test_topology_note_for_high_impedance(self):
        """Test that feedpoint R >= 50 returns topology_note suggesting Gamma match"""
        response = requests.post(f"{BASE_URL}/api/hairpin-designer", json={
            "num_elements": 2,
            "frequency_mhz": 27.185,
            "driven_element_length_in": 198,
            "reflector_spacing_in": 120,
            "feedpoint_impedance": 55  # Force R >= 50
        })
        assert response.status_code == 200
        data = response.json()
        
        # Should have topology_note
        assert "topology_note" in data
        assert "Hairpin cannot step down" in data["topology_note"] or ">= 50" in data["topology_note"]
        assert "Gamma match" in data["topology_note"]
        
        # Should NOT have recipe (no valid hairpin design)
        assert "recipe" not in data or data.get("recipe") is None
        
        print(f"✓ topology_note: {data['topology_note']}")
        print(f"✓ Feedpoint impedance: {data.get('feedpoint_impedance')}Ω")


class TestCalculateWithHairpin:
    """Tests for POST /api/calculate with feed_type=hairpin showing reflection coefficient physics"""
    
    def test_calculate_hairpin_reflection_fields(self):
        """Test that /api/calculate with feed_type=hairpin shows z_in_r, z_in_x, gamma_mag, p_forward_w, p_reflected_w, p_net_w"""
        response = requests.post(f"{BASE_URL}/api/calculate", json={
            "num_elements": 4,
            "elements": [
                {"element_type": "reflector", "length": 216, "diameter": 0.5, "position": 0},
                {"element_type": "driven", "length": 198, "diameter": 0.5, "position": 48},
                {"element_type": "director", "length": 192, "diameter": 0.5, "position": 106},
                {"element_type": "director", "length": 186, "diameter": 0.5, "position": 162}
            ],
            "height_from_ground": 54,
            "height_unit": "ft",
            "boom_diameter": 1.5,
            "boom_unit": "inches",
            "band": "11m_cb",
            "frequency_mhz": 27.185,
            "feed_type": "hairpin"
        })
        assert response.status_code == 200
        data = response.json()
        
        # Verify matching_info exists
        assert "matching_info" in data
        mi = data["matching_info"]
        
        # Verify reflection coefficient physics fields
        required_fields = ["z_in_r", "z_in_x", "gamma_mag", "p_forward_w", "p_reflected_w", "p_net_w"]
        for field in required_fields:
            assert field in mi, f"Missing field in matching_info: {field}"
        
        # Verify data types
        assert isinstance(mi["z_in_r"], (int, float))
        assert isinstance(mi["z_in_x"], (int, float))
        assert isinstance(mi["gamma_mag"], (int, float))
        assert isinstance(mi["p_forward_w"], (int, float))
        assert isinstance(mi["p_reflected_w"], (int, float))
        assert isinstance(mi["p_net_w"], (int, float))
        
        # Verify physics sanity
        assert mi["gamma_mag"] >= 0 and mi["gamma_mag"] < 1, f"Gamma should be 0-1, got {mi['gamma_mag']}"
        assert mi["p_forward_w"] > 0
        assert mi["p_reflected_w"] >= 0
        assert mi["p_net_w"] <= mi["p_forward_w"]
        
        print(f"✓ Matching type: {mi.get('type')}")
        print(f"✓ Z_in: {mi['z_in_r']}+{mi['z_in_x']}j Ω")
        print(f"✓ Gamma magnitude: {mi['gamma_mag']}")
        print(f"✓ Power: Forward={mi['p_forward_w']}W, Reflected={mi['p_reflected_w']}W, Net={mi['p_net_w']}W")
    
    def test_calculate_hairpin_design_section(self):
        """Test that hairpin_design section is included in matching_info"""
        response = requests.post(f"{BASE_URL}/api/calculate", json={
            "num_elements": 4,
            "elements": [
                {"element_type": "reflector", "length": 216, "diameter": 0.5, "position": 0},
                {"element_type": "driven", "length": 198, "diameter": 0.5, "position": 48},
                {"element_type": "director", "length": 192, "diameter": 0.5, "position": 106},
                {"element_type": "director", "length": 186, "diameter": 0.5, "position": 162}
            ],
            "height_from_ground": 54,
            "height_unit": "ft",
            "boom_diameter": 1.5,
            "boom_unit": "inches",
            "band": "11m_cb",
            "frequency_mhz": 27.185,
            "feed_type": "hairpin"
        })
        assert response.status_code == 200
        data = response.json()
        
        mi = data.get("matching_info", {})
        assert "hairpin_design" in mi
        hd = mi["hairpin_design"]
        
        # Verify hairpin design fields
        expected_fields = [
            "feedpoint_impedance_ohms",
            "target_impedance_ohms",
            "q_match",
            "required_xl_ohms",
            "required_xc_ohms",
            "ideal_hairpin_length_in",
            "actual_hairpin_length_in",
            "shorten_per_side_in",
            "shortened_total_length_in"
        ]
        for field in expected_fields:
            assert field in hd, f"Missing field in hairpin_design: {field}"
        
        print(f"✓ Hairpin design fields present")
        print(f"✓ Feedpoint R: {hd['feedpoint_impedance_ohms']}Ω → Target: {hd['target_impedance_ohms']}Ω")
        print(f"✓ Q match: {hd['q_match']}")
        print(f"✓ X_L required: {hd['required_xl_ohms']}Ω")
        print(f"✓ Ideal hairpin length: {hd['ideal_hairpin_length_in']}\"")


class TestHairpinDrivenElementShortening:
    """Tests for driven element shortening guidance"""
    
    def test_shortening_guidance(self):
        """Test that shortening guidance is provided"""
        response = requests.post(f"{BASE_URL}/api/hairpin-designer", json={
            "num_elements": 4,
            "frequency_mhz": 27.185,
            "driven_element_length_in": 198,
            "reflector_spacing_in": 48,
            "director_spacings_in": [58, 56]
        })
        assert response.status_code == 200
        data = response.json()
        recipe = data["recipe"]
        
        # Verify shortening guidance fields
        assert "shorten_per_side_in" in recipe
        assert "shortened_total_length_in" in recipe
        assert recipe["shorten_per_side_in"] > 0
        
        # Note: shortened_total_length_in is based on the CORRECTED driven length (recommended_driven_length)
        # If element was corrected LONGER first, then shortened for X_C, the final could be > or < original
        # The important thing is that shorten_per_side_in is > 0 (element shortening is needed)
        if recipe.get("driven_length_corrected") and recipe.get("recommended_driven_length_in"):
            # Shortened total should be less than recommended (after length correction)
            assert recipe["shortened_total_length_in"] < recipe["recommended_driven_length_in"]
        else:
            # No length correction - shortened total should be less than original
            assert recipe["shortened_total_length_in"] < recipe.get("original_driven_length_in", 198)
        
        # Verify notes contain shortening info
        assert "notes" in data
        shortening_notes = [n for n in data["notes"] if "Shorten" in n or "shorten" in n]
        assert len(shortening_notes) > 0, "Should have shortening guidance in notes"
        
        print(f"✓ Shorten per side: {recipe['shorten_per_side_in']}\"")
        print(f"✓ New total length: {recipe['shortened_total_length_in']}\"")
        print(f"✓ Driven length corrected: {recipe.get('driven_length_corrected')}")
        print(f"✓ Recommended driven: {recipe.get('recommended_driven_length_in')}\"")
        print(f"✓ Notes: {shortening_notes[0]}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
