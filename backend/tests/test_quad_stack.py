"""
Backend tests for 2x2 Quad Stack feature

Tests the following endpoints and features:
- POST /api/calculate with stacking layout='quad', num_antennas=4, h_spacing
- POST /api/calculate with stacking layout='line' (should NOT return quad_notes)
- POST /api/calculate without stacking (stacking_enabled=false)
- Wind load calculation with num_stacked=4 for quad
- Power splitter with 4:1 type for quad layout
- Gain increase ~5dB for quad
- Beamwidth narrowing for both H and V
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL', os.environ.get('REACT_APP_BACKEND_URL'))
if not BASE_URL:
    BASE_URL = "https://cb-amp-hub.preview.emergentagent.com"


class TestQuadStackCalculation:
    """Test 2x2 Quad Stack feature in /api/calculate"""

    @pytest.fixture
    def base_antenna_input(self):
        """Base antenna configuration for testing"""
        return {
            "num_elements": 3,
            "elements": [
                {"element_type": "reflector", "length": 216, "diameter": 0.5, "position": 0},
                {"element_type": "driven", "length": 204, "diameter": 0.5, "position": 48},
                {"element_type": "director", "length": 195, "diameter": 0.5, "position": 96}
            ],
            "height_from_ground": 54,
            "height_unit": "ft",
            "boom_diameter": 1.5,
            "boom_unit": "inches",
            "band": "11m_cb",
            "frequency_mhz": 27.185
        }

    def test_quad_stack_basic(self, base_antenna_input):
        """Test POST /api/calculate with quad layout returns quad_notes"""
        payload = {
            **base_antenna_input,
            "stacking": {
                "enabled": True,
                "orientation": "vertical",
                "layout": "quad",
                "num_antennas": 4,
                "spacing": 20,
                "spacing_unit": "ft",
                "h_spacing": 20,
                "h_spacing_unit": "ft"
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify stacking is enabled
        assert data.get("stacking_enabled") == True, "stacking_enabled should be True"
        
        # Verify stacking_info exists
        assert "stacking_info" in data, "stacking_info should be present in response"
        stacking_info = data["stacking_info"]
        
        # Verify quad_notes exists for quad layout
        assert "quad_notes" in stacking_info, "quad_notes should be present for quad layout"
        quad_notes = stacking_info["quad_notes"]
        
        # Verify quad_notes content
        assert "layout" in quad_notes, "quad_notes should have layout"
        assert "2x2" in quad_notes["layout"].lower() or "h-frame" in quad_notes["layout"].lower(), f"quad_notes layout should mention 2x2 or H-frame, got: {quad_notes['layout']}"
        assert "effect" in quad_notes, "quad_notes should have effect"
        assert "v_spacing" in quad_notes, "quad_notes should have v_spacing"
        assert "h_spacing" in quad_notes, "quad_notes should have h_spacing"
        
        print(f"✓ Quad stack basic test passed - quad_notes present with layout: {quad_notes['layout']}")

    def test_quad_stack_gain_increase(self, base_antenna_input):
        """Test quad stack returns ~5dB gain increase"""
        payload = {
            **base_antenna_input,
            "stacking": {
                "enabled": True,
                "orientation": "vertical",
                "layout": "quad",
                "num_antennas": 4,
                "spacing": 20,
                "spacing_unit": "ft",
                "h_spacing": 20,
                "h_spacing_unit": "ft"
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        stacking_info = data.get("stacking_info", {})
        
        # Gain increase should be ~5dB (4.5-6dB range typical for quad)
        gain_increase = stacking_info.get("gain_increase_db", 0)
        assert 4.0 <= gain_increase <= 7.0, f"Quad gain increase should be ~5dB (4-7dB range), got {gain_increase}dB"
        
        # Stacked gain should be present
        stacked_gain = data.get("stacked_gain_dbi")
        base_gain = data.get("gain_dbi")
        assert stacked_gain is not None, "stacked_gain_dbi should be present"
        assert stacked_gain > base_gain, f"Stacked gain ({stacked_gain}) should be greater than base gain ({base_gain})"
        
        print(f"✓ Quad gain test passed - increase: {gain_increase}dB, stacked: {stacked_gain}dBi")

    def test_quad_stack_beamwidth_narrowing(self, base_antenna_input):
        """Test quad stack narrows both H and V beamwidths"""
        # First get base beamwidth without stacking
        base_response = requests.post(f"{BASE_URL}/api/calculate", json=base_antenna_input)
        assert base_response.status_code == 200
        base_data = base_response.json()
        base_h = base_data.get("beamwidth_h")
        base_v = base_data.get("beamwidth_v")
        
        # Now test with quad stacking
        payload = {
            **base_antenna_input,
            "stacking": {
                "enabled": True,
                "orientation": "vertical",
                "layout": "quad",
                "num_antennas": 4,
                "spacing": 20,
                "spacing_unit": "ft",
                "h_spacing": 20,
                "h_spacing_unit": "ft"
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
        assert response.status_code == 200
        data = response.json()
        
        stacking_info = data.get("stacking_info", {})
        new_h = stacking_info.get("new_beamwidth_h")
        new_v = stacking_info.get("new_beamwidth_v")
        
        # Both beamwidths should be narrower
        assert new_h < base_h, f"Quad H beamwidth ({new_h}) should be narrower than base ({base_h})"
        assert new_v < base_v, f"Quad V beamwidth ({new_v}) should be narrower than base ({base_v})"
        
        print(f"✓ Beamwidth narrowing test passed - H: {base_h}→{new_h}, V: {base_v}→{new_v}")

    def test_quad_stack_power_splitter_type(self, base_antenna_input):
        """Test quad stack returns 4:1 power splitter type"""
        payload = {
            **base_antenna_input,
            "stacking": {
                "enabled": True,
                "orientation": "vertical",
                "layout": "quad",
                "num_antennas": 4,
                "spacing": 20,
                "spacing_unit": "ft",
                "h_spacing": 20,
                "h_spacing_unit": "ft"
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
        assert response.status_code == 200
        data = response.json()
        
        stacking_info = data.get("stacking_info", {})
        power_splitter = stacking_info.get("power_splitter", {})
        
        assert "type" in power_splitter, "power_splitter should have type field"
        splitter_type = power_splitter["type"]
        
        # For quad (4 antennas), should be 4:1 splitter
        assert "4:1" in splitter_type, f"Quad should use 4:1 splitter, got: {splitter_type}"
        
        # Verify power per antenna is 25W for 100W input
        power_per = power_splitter.get("power_per_antenna_100w")
        assert power_per == 25.0, f"Power per antenna @ 100W should be 25W for 4-way split, got {power_per}"
        
        print(f"✓ Power splitter test passed - type: {splitter_type}, power/ant: {power_per}W")

    def test_quad_stack_wind_load(self, base_antenna_input):
        """Test quad stack multiplies wind load by 4"""
        payload = {
            **base_antenna_input,
            "stacking": {
                "enabled": True,
                "orientation": "vertical",
                "layout": "quad",
                "num_antennas": 4,
                "spacing": 20,
                "spacing_unit": "ft",
                "h_spacing": 20,
                "h_spacing_unit": "ft"
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
        assert response.status_code == 200
        data = response.json()
        
        wind_load = data.get("wind_load", {})
        num_stacked = wind_load.get("num_stacked")
        
        assert num_stacked == 4, f"Wind load num_stacked should be 4 for quad, got {num_stacked}"
        
        print(f"✓ Wind load test passed - num_stacked: {num_stacked}")

    def test_quad_stack_num_antennas(self, base_antenna_input):
        """Test quad layout forces num_antennas to 4"""
        payload = {
            **base_antenna_input,
            "stacking": {
                "enabled": True,
                "orientation": "vertical",
                "layout": "quad",
                "num_antennas": 2,  # Intentionally set to 2, should be overridden to 4
                "spacing": 20,
                "spacing_unit": "ft",
                "h_spacing": 20,
                "h_spacing_unit": "ft"
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
        assert response.status_code == 200
        data = response.json()
        
        stacking_info = data.get("stacking_info", {})
        num_antennas = stacking_info.get("num_antennas")
        
        assert num_antennas == 4, f"Quad layout should have 4 antennas, got {num_antennas}"
        
        print(f"✓ Quad num_antennas test passed - forced to {num_antennas}")


class TestLineStackCalculation:
    """Test line stacking (should NOT return quad_notes)"""

    @pytest.fixture
    def base_antenna_input(self):
        """Base antenna configuration for testing"""
        return {
            "num_elements": 3,
            "elements": [
                {"element_type": "reflector", "length": 216, "diameter": 0.5, "position": 0},
                {"element_type": "driven", "length": 204, "diameter": 0.5, "position": 48},
                {"element_type": "director", "length": 195, "diameter": 0.5, "position": 96}
            ],
            "height_from_ground": 54,
            "height_unit": "ft",
            "boom_diameter": 1.5,
            "boom_unit": "inches",
            "band": "11m_cb",
            "frequency_mhz": 27.185
        }

    def test_line_stack_no_quad_notes(self, base_antenna_input):
        """Test POST /api/calculate with line layout should NOT return quad_notes"""
        payload = {
            **base_antenna_input,
            "stacking": {
                "enabled": True,
                "orientation": "vertical",
                "layout": "line",
                "num_antennas": 2,
                "spacing": 20,
                "spacing_unit": "ft"
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
        assert response.status_code == 200
        data = response.json()
        
        stacking_info = data.get("stacking_info", {})
        
        # Line layout should NOT have quad_notes
        assert "quad_notes" not in stacking_info, "Line layout should NOT have quad_notes"
        
        # Should have vertical_notes for vertical line stacking
        assert "vertical_notes" in stacking_info, "Vertical line stacking should have vertical_notes"
        
        print(f"✓ Line stack test passed - no quad_notes, has vertical_notes")

    def test_horizontal_line_stack(self, base_antenna_input):
        """Test horizontal line stacking"""
        payload = {
            **base_antenna_input,
            "stacking": {
                "enabled": True,
                "orientation": "horizontal",
                "layout": "line",
                "num_antennas": 2,
                "spacing": 20,
                "spacing_unit": "ft"
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
        assert response.status_code == 200
        data = response.json()
        
        stacking_info = data.get("stacking_info", {})
        
        # Should NOT have quad_notes or vertical_notes
        assert "quad_notes" not in stacking_info, "Horizontal line should NOT have quad_notes"
        assert "vertical_notes" not in stacking_info, "Horizontal line should NOT have vertical_notes"
        
        # Should have layout = line and orientation = horizontal
        assert stacking_info.get("layout") == "line", "Layout should be 'line'"
        assert stacking_info.get("orientation") == "horizontal", "Orientation should be 'horizontal'"
        
        print(f"✓ Horizontal line stack test passed")


class TestNoStackingCalculation:
    """Test calculation without stacking"""

    @pytest.fixture
    def base_antenna_input(self):
        """Base antenna configuration for testing"""
        return {
            "num_elements": 3,
            "elements": [
                {"element_type": "reflector", "length": 216, "diameter": 0.5, "position": 0},
                {"element_type": "driven", "length": 204, "diameter": 0.5, "position": 48},
                {"element_type": "director", "length": 195, "diameter": 0.5, "position": 96}
            ],
            "height_from_ground": 54,
            "height_unit": "ft",
            "boom_diameter": 1.5,
            "boom_unit": "inches",
            "band": "11m_cb",
            "frequency_mhz": 27.185
        }

    def test_no_stacking(self, base_antenna_input):
        """Test POST /api/calculate without stacking returns stacking_enabled=false"""
        response = requests.post(f"{BASE_URL}/api/calculate", json=base_antenna_input)
        assert response.status_code == 200
        data = response.json()
        
        # stacking_enabled should be False
        assert data.get("stacking_enabled") == False, "stacking_enabled should be False when no stacking"
        
        # stacking_info should be None or not present
        stacking_info = data.get("stacking_info")
        assert stacking_info is None, f"stacking_info should be None, got {stacking_info}"
        
        # Should still have valid results
        assert "gain_dbi" in data, "Should have gain_dbi"
        assert "swr" in data, "Should have swr"
        assert "beamwidth_h" in data, "Should have beamwidth_h"
        
        print(f"✓ No stacking test passed - gain: {data['gain_dbi']}dBi, SWR: {data['swr']}")

    def test_stacking_disabled(self, base_antenna_input):
        """Test POST /api/calculate with stacking.enabled=false"""
        payload = {
            **base_antenna_input,
            "stacking": {
                "enabled": False,
                "orientation": "vertical",
                "layout": "line",
                "num_antennas": 2,
                "spacing": 20,
                "spacing_unit": "ft"
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("stacking_enabled") == False, "stacking_enabled should be False when disabled"
        
        print(f"✓ Stacking disabled test passed")


class TestQuadStackHSpacing:
    """Test H spacing handling for quad stack"""

    @pytest.fixture
    def base_antenna_input(self):
        """Base antenna configuration for testing"""
        return {
            "num_elements": 3,
            "elements": [
                {"element_type": "reflector", "length": 216, "diameter": 0.5, "position": 0},
                {"element_type": "driven", "length": 204, "diameter": 0.5, "position": 48},
                {"element_type": "director", "length": 195, "diameter": 0.5, "position": 96}
            ],
            "height_from_ground": 54,
            "height_unit": "ft",
            "boom_diameter": 1.5,
            "boom_unit": "inches",
            "band": "11m_cb",
            "frequency_mhz": 27.185
        }

    def test_quad_with_different_h_spacing(self, base_antenna_input):
        """Test quad stack with different V and H spacing values"""
        payload = {
            **base_antenna_input,
            "stacking": {
                "enabled": True,
                "orientation": "vertical",
                "layout": "quad",
                "num_antennas": 4,
                "spacing": 20,  # V spacing
                "spacing_unit": "ft",
                "h_spacing": 15,  # Different H spacing
                "h_spacing_unit": "ft"
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
        assert response.status_code == 200
        data = response.json()
        
        quad_notes = data.get("stacking_info", {}).get("quad_notes", {})
        
        # Verify both spacings are reflected in quad_notes
        v_spacing_str = quad_notes.get("v_spacing", "")
        h_spacing_str = quad_notes.get("h_spacing", "")
        
        assert "20" in v_spacing_str, f"V spacing should contain 20, got: {v_spacing_str}"
        assert "15" in h_spacing_str, f"H spacing should contain 15, got: {h_spacing_str}"
        
        print(f"✓ Different H/V spacing test passed - V: {v_spacing_str}, H: {h_spacing_str}")

    def test_quad_with_null_h_spacing_uses_v_spacing(self, base_antenna_input):
        """Test quad stack with null h_spacing falls back to v spacing"""
        payload = {
            **base_antenna_input,
            "stacking": {
                "enabled": True,
                "orientation": "vertical",
                "layout": "quad",
                "num_antennas": 4,
                "spacing": 20,
                "spacing_unit": "ft",
                "h_spacing": None,  # Null H spacing
                "h_spacing_unit": "ft"
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
        assert response.status_code == 200
        data = response.json()
        
        quad_notes = data.get("stacking_info", {}).get("quad_notes", {})
        h_spacing_str = quad_notes.get("h_spacing", "")
        
        # Should fall back to v spacing (20)
        assert "20" in h_spacing_str, f"H spacing should default to V spacing (20), got: {h_spacing_str}"
        
        print(f"✓ Null h_spacing fallback test passed - H: {h_spacing_str}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
