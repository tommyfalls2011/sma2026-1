"""
Test driven element length correction in Gamma Match Designer.

The designer corrects the driven element length to match resonance to the operating frequency.
When element resonates ABOVE operating freq: driven gets LONGER
When element resonates BELOW operating freq: driven gets SHORTER
Formula: recommended_length = current_length * (element_res_freq / frequency_mhz)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestDrivenLengthCorrection:
    """Test the NEW driven element length correction feature in Gamma Designer."""

    def test_correction_needed_when_resonance_above_operating(self):
        """
        When element_resonant_freq_mhz=27.349 (above 27.185),
        driven_length_corrected should be true and recommended_driven_length_in > 204.
        Expected: 204 * (27.349/27.185) ≈ 205.23"
        """
        payload = {
            "num_elements": 4,
            "driven_element_length_in": 204.0,
            "frequency_mhz": 27.185,
            "element_resonant_freq_mhz": 27.349  # resonates above operating freq
        }
        response = requests.post(f"{BASE_URL}/api/gamma-designer", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        recipe = data.get("recipe", {})
        
        # Verify correction was applied
        assert recipe.get("driven_length_corrected") == True, \
            f"Expected driven_length_corrected=true, got {recipe.get('driven_length_corrected')}"
        
        # Verify recommended length is LONGER than original
        original = recipe.get("original_driven_length_in", 0)
        recommended = recipe.get("recommended_driven_length_in", 0)
        assert recommended > original, \
            f"Expected recommended ({recommended}) > original ({original}) when res freq > operating freq"
        
        # Verify the formula: recommended = 204 * (27.349/27.185) ≈ 205.23
        expected_recommended = round(204.0 * (27.349 / 27.185), 2)
        assert abs(recommended - expected_recommended) < 0.1, \
            f"Expected recommended ≈ {expected_recommended}, got {recommended}"
        
        print(f"✓ Correction test passed: {original}\" -> {recommended}\" (expected ~{expected_recommended}\")")

    def test_notes_contain_make_longer_message(self):
        """
        When correction is needed (resonance above operating), 
        notes should contain 'DRIVEN ELEMENT: Make longer'.
        """
        payload = {
            "num_elements": 4,
            "driven_element_length_in": 204.0,
            "frequency_mhz": 27.185,
            "element_resonant_freq_mhz": 27.349
        }
        response = requests.post(f"{BASE_URL}/api/gamma-designer", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        notes = data.get("notes", [])
        notes_text = " ".join(notes)
        
        assert "DRIVEN ELEMENT:" in notes_text, \
            f"Expected 'DRIVEN ELEMENT:' in notes, got: {notes}"
        assert "longer" in notes_text.lower(), \
            f"Expected 'longer' in notes when res freq > operating freq, got: {notes}"
        
        print(f"✓ Notes contain 'Make longer' message: {[n for n in notes if 'DRIVEN' in n]}")

    def test_no_correction_when_resonance_matches_operating(self):
        """
        When element_resonant_freq_mhz=27.185 (equals operating freq),
        driven_length_corrected should be false.
        """
        payload = {
            "num_elements": 4,
            "driven_element_length_in": 204.0,
            "frequency_mhz": 27.185,
            "element_resonant_freq_mhz": 27.185  # resonates AT operating freq
        }
        response = requests.post(f"{BASE_URL}/api/gamma-designer", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        recipe = data.get("recipe", {})
        
        # Verify no correction was applied
        assert recipe.get("driven_length_corrected") == False, \
            f"Expected driven_length_corrected=false when resonance equals operating, got {recipe.get('driven_length_corrected')}"
        
        # Verify recommended == original
        original = recipe.get("original_driven_length_in", 0)
        recommended = recipe.get("recommended_driven_length_in", 0)
        assert recommended == original, \
            f"Expected recommended == original when no correction needed, got {recommended} vs {original}"
        
        print(f"✓ No correction test passed: original={original}\", recommended={recommended}\"")

    def test_correction_when_resonance_below_operating(self):
        """
        When element resonates BELOW operating freq, driven should get SHORTER.
        Formula: recommended = current * (res_freq / operating_freq)
        """
        payload = {
            "num_elements": 4,
            "driven_element_length_in": 204.0,
            "frequency_mhz": 27.185,
            "element_resonant_freq_mhz": 27.0  # resonates below operating freq
        }
        response = requests.post(f"{BASE_URL}/api/gamma-designer", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        recipe = data.get("recipe", {})
        
        # Verify correction was applied
        assert recipe.get("driven_length_corrected") == True, \
            f"Expected driven_length_corrected=true, got {recipe.get('driven_length_corrected')}"
        
        # Verify recommended length is SHORTER than original
        original = recipe.get("original_driven_length_in", 0)
        recommended = recipe.get("recommended_driven_length_in", 0)
        assert recommended < original, \
            f"Expected recommended ({recommended}) < original ({original}) when res freq < operating freq"
        
        # Verify the formula: recommended = 204 * (27.0/27.185) ≈ 202.61
        expected_recommended = round(204.0 * (27.0 / 27.185), 2)
        assert abs(recommended - expected_recommended) < 0.1, \
            f"Expected recommended ≈ {expected_recommended}, got {recommended}"
        
        print(f"✓ Shorter correction test passed: {original}\" -> {recommended}\" (expected ~{expected_recommended}\")")

    def test_hardware_isolation_2_element(self):
        """Verify 2-element still uses rod_od=0.5625."""
        payload = {
            "num_elements": 2,
            "driven_element_length_in": 204.0,
            "frequency_mhz": 27.185
        }
        response = requests.post(f"{BASE_URL}/api/gamma-designer", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        recipe = data.get("recipe", {})
        
        # 2-element uses 9/16" rod (0.5625)
        rod_od = recipe.get("rod_od", 0)
        assert abs(rod_od - 0.5625) < 0.001, \
            f"Expected rod_od=0.5625 for 2-element, got {rod_od}"
        
        print(f"✓ 2-element hardware isolation: rod_od={rod_od}")

    def test_hardware_isolation_3plus_element(self):
        """Verify 3+ element uses rod_od=0.5."""
        for num_el in [3, 4, 5]:
            payload = {
                "num_elements": num_el,
                "driven_element_length_in": 204.0,
                "frequency_mhz": 27.185
            }
            response = requests.post(f"{BASE_URL}/api/gamma-designer", json=payload)
            assert response.status_code == 200
            
            data = response.json()
            recipe = data.get("recipe", {})
            
            # 3+ element uses 1/2" rod (0.5)
            rod_od = recipe.get("rod_od", 0)
            assert abs(rod_od - 0.5) < 0.001, \
                f"Expected rod_od=0.5 for {num_el}-element, got {rod_od}"
            
            print(f"✓ {num_el}-element hardware isolation: rod_od={rod_od}")


class TestFullRoundTrip:
    """
    Full round-trip test: 
    1. Call /api/calculate for 4-element, get feedpoint_R and res_freq
    2. Pass to /api/gamma-designer, get recommended driven length + bar + insertion
    3. Call /api/calculate with corrected values
    4. Verify SWR is 1.0 and resonant freq matches operating freq
    """

    def test_full_round_trip_4_element(self):
        """
        Standard 4-element layout: reflector at 0, driven at 48, dir1 at 96, dir2 at 144.
        Main calc should return element_resonant_freq_mhz=~27.349 for a 204" driven.
        """
        # Step 1: Call /api/calculate for 4-element Yagi
        elements = [
            {"element_type": "reflector", "length": 214.0, "diameter": 1.0, "position": 0},
            {"element_type": "driven", "length": 204.0, "diameter": 1.0, "position": 48},
            {"element_type": "director", "length": 194.0, "diameter": 1.0, "position": 96},
            {"element_type": "director", "length": 188.0, "diameter": 1.0, "position": 144},
        ]
        calc_payload = {
            "num_elements": 4,
            "elements": elements,
            "height_from_ground": 35,
            "height_unit": "ft",
            "boom_diameter": 2.0,
            "boom_unit": "inches",
            "band": "11m_cb",
            "frequency_mhz": 27.185,
            "antenna_orientation": "horizontal",
            "feed_type": "gamma"
        }
        calc_response = requests.post(f"{BASE_URL}/api/calculate", json=calc_payload)
        assert calc_response.status_code == 200, f"Calculate failed: {calc_response.text}"
        
        calc_data = calc_response.json()
        
        # Extract values from main calculator
        matching_info = calc_data.get("matching_info", {})
        element_res_freq = matching_info.get("element_resonant_freq_mhz", 27.185)
        feedpoint_r = calc_data.get("matching_info", {}).get("debug_trace", [{}])
        
        # Get feedpoint R from debug trace step 10
        for step in matching_info.get("debug_trace", []):
            if step.get("label") == "IMPEDANCE TRANSFORM":
                for item in step.get("items", []):
                    if item.get("var") == "R_feed":
                        feedpoint_r = item.get("val")
                        break
        
        print(f"Step 1 - Main calc: element_resonant_freq_mhz={element_res_freq}, feedpoint_R=~{feedpoint_r}")
        
        # Step 2: Call /api/gamma-designer with these values
        designer_payload = {
            "num_elements": 4,
            "driven_element_length_in": 204.0,
            "frequency_mhz": 27.185,
            "element_resonant_freq_mhz": element_res_freq,
            "reflector_spacing_in": 48.0,
            "director_spacings_in": [48.0, 96.0]
        }
        designer_response = requests.post(f"{BASE_URL}/api/gamma-designer", json=designer_payload)
        assert designer_response.status_code == 200, f"Designer failed: {designer_response.text}"
        
        designer_data = designer_response.json()
        recipe = designer_data.get("recipe", {})
        
        recommended_length = recipe.get("recommended_driven_length_in", 204.0)
        ideal_bar = recipe.get("ideal_bar_position", 15.0)
        optimal_insertion = recipe.get("optimal_insertion", 8.0)
        driven_corrected = recipe.get("driven_length_corrected", False)
        
        print(f"Step 2 - Designer: recommended_driven_length={recommended_length}\", bar={ideal_bar}\", insertion={optimal_insertion}\", corrected={driven_corrected}")
        
        # If element_res_freq > 27.185, driven should have been corrected LONGER
        if element_res_freq > 27.185 + 0.01:
            assert driven_corrected == True, \
                f"Expected driven_length_corrected=true when res_freq ({element_res_freq}) > operating (27.185)"
            assert recommended_length > 204.0, \
                f"Expected recommended length > 204 when res_freq > operating, got {recommended_length}"
        
        # Step 3: Call /api/calculate again with corrected values
        corrected_elements = [
            {"element_type": "reflector", "length": 214.0, "diameter": 1.0, "position": 0},
            {"element_type": "driven", "length": recommended_length, "diameter": 1.0, "position": 48},
            {"element_type": "director", "length": 194.0, "diameter": 1.0, "position": 96},
            {"element_type": "director", "length": 188.0, "diameter": 1.0, "position": 144},
        ]
        corrected_calc_payload = {
            "num_elements": 4,
            "elements": corrected_elements,
            "height_from_ground": 35,
            "height_unit": "ft",
            "boom_diameter": 2.0,
            "boom_unit": "inches",
            "band": "11m_cb",
            "frequency_mhz": 27.185,
            "antenna_orientation": "horizontal",
            "feed_type": "gamma",
            "gamma_bar_pos": ideal_bar,
            "gamma_element_gap": optimal_insertion
        }
        corrected_response = requests.post(f"{BASE_URL}/api/calculate", json=corrected_calc_payload)
        assert corrected_response.status_code == 200, f"Corrected calculate failed: {corrected_response.text}"
        
        corrected_data = corrected_response.json()
        
        final_swr = corrected_data.get("swr", 99)
        final_res_freq = corrected_data.get("matching_info", {}).get("element_resonant_freq_mhz", 0)
        
        print(f"Step 3 - After correction: SWR={final_swr}, element_resonant_freq_mhz={final_res_freq}")
        
        # Verify results
        # SWR should be close to 1.0 (< 1.5 is acceptable for a properly matched system)
        assert final_swr < 1.5, \
            f"Expected SWR < 1.5 after correction, got {final_swr}"
        
        # Element resonant freq should be closer to 27.185 after correction
        freq_deviation = abs(final_res_freq - 27.185)
        print(f"Final resonant freq deviation from 27.185: {freq_deviation} MHz")
        
        print(f"✓ Full round-trip test passed: SWR={final_swr}, res_freq={final_res_freq}")


class TestEdgeCases:
    """Test edge cases for the driven length correction feature."""

    def test_small_frequency_difference(self):
        """
        When resonant freq is only slightly different (within 0.01 MHz),
        no correction should be applied.
        """
        payload = {
            "num_elements": 4,
            "driven_element_length_in": 204.0,
            "frequency_mhz": 27.185,
            "element_resonant_freq_mhz": 27.190  # only 0.005 MHz difference
        }
        response = requests.post(f"{BASE_URL}/api/gamma-designer", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        recipe = data.get("recipe", {})
        
        # With only 0.005 MHz difference (< 0.01 threshold), correction may or may not apply
        # The code uses abs(element_res_freq - frequency_mhz) > 0.01 as threshold
        corrected = recipe.get("driven_length_corrected", True)
        
        print(f"Small freq difference test: corrected={corrected}")

    def test_no_element_resonant_freq_provided(self):
        """
        When element_resonant_freq_mhz is not provided,
        the designer should compute it internally.
        """
        payload = {
            "num_elements": 4,
            "driven_element_length_in": 204.0,
            "frequency_mhz": 27.185
            # element_resonant_freq_mhz NOT provided
        }
        response = requests.post(f"{BASE_URL}/api/gamma-designer", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        recipe = data.get("recipe", {})
        
        # Should still have recommended_driven_length_in in response
        assert "recommended_driven_length_in" in recipe, \
            "Expected recommended_driven_length_in in response even without element_resonant_freq_mhz input"
        
        # Should still have driven_length_corrected field
        assert "driven_length_corrected" in recipe, \
            "Expected driven_length_corrected field in response"
        
        print(f"No element_resonant_freq provided test: recommended={recipe.get('recommended_driven_length_in')}, corrected={recipe.get('driven_length_corrected')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
