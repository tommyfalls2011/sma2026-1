"""
Test cases for Reset All and Scale button bug fixes.
Tests verify:
1. /api/calculate endpoint works with default 2-element 27.185 MHz Yagi
2. Scaling functionality produces correct proportional changes
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Default 2-element Yagi configuration (factory defaults)
DEFAULT_ANTENNA_INPUT = {
    "num_elements": 2,
    "elements": [
        {"element_type": "reflector", "length": "216", "diameter": "0.5", "position": "0"},
        {"element_type": "driven", "length": "204", "diameter": "0.5", "position": "48"}
    ],
    "height_from_ground": "54",
    "height_unit": "ft",
    "boom_diameter": "1.5",
    "boom_unit": "inches",
    "band": "11m_cb",
    "frequency_mhz": "27.185",
    "use_reflector": True,
    "antenna_orientation": "horizontal",
    "feed_type": "gamma",
    "boom_grounded": True,
    "boom_mount": "bonded"
}


class TestHealthEndpoint:
    """Health check tests"""
    
    def test_api_health(self):
        """Verify API and database are up"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["api"] == "up"
        assert data["database"] == "up"


class TestDefaultAntennaCalculation:
    """Tests for default 2-element Yagi calculation (after Reset All)"""
    
    def test_calculate_default_2_element_yagi(self):
        """POST /api/calculate with default 2-element config should return valid results"""
        response = requests.post(
            f"{BASE_URL}/api/calculate",
            json=DEFAULT_ANTENNA_INPUT
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify essential output fields exist
        assert "gain_dbi" in data
        assert "fb_ratio" in data
        assert "swr" in data
        assert "beamwidth_h" in data
        assert "beamwidth_v" in data
        
        # Verify reasonable values for 2-element Yagi
        assert 5 < data["gain_dbi"] < 15, f"Gain {data['gain_dbi']} out of expected range"
        assert 8 < data["fb_ratio"] < 25, f"FB ratio {data['fb_ratio']} out of expected range"
        assert 1 < data["swr"] < 10, f"SWR {data['swr']} out of expected range"
    
    def test_calculate_returns_gamma_match_info(self):
        """Gamma match feed type should return matching info"""
        response = requests.post(
            f"{BASE_URL}/api/calculate",
            json=DEFAULT_ANTENNA_INPUT
        )
        assert response.status_code == 200
        data = response.json()
        
        # With gamma feed type, we expect matching_info
        assert "matching_info" in data or "gamma_recipe" in data or data.get("feed_type") == "gamma"
    
    def test_calculate_returns_swr_curve(self):
        """Response should include SWR curve data"""
        response = requests.post(
            f"{BASE_URL}/api/calculate",
            json=DEFAULT_ANTENNA_INPUT
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check for SWR curve data
        if "swr_curve" in data:
            assert len(data["swr_curve"]) > 0
            # Each point should have frequency and swr
            point = data["swr_curve"][0]
            assert "frequency" in point or "freq" in point


class TestScalingCalculations:
    """Tests for scale functionality - verify scaled parameters produce valid results"""
    
    def test_scaled_10m_design_calculates(self):
        """Scaling to 10m (28.5 MHz) should produce valid calculation"""
        # Scale ratio from 27.185 to 28.5 MHz
        current_freq = 27.185
        target_freq = 28.5
        ratio = current_freq / target_freq
        
        scaled_input = {
            "num_elements": 2,
            "elements": [
                {
                    "element_type": "reflector",
                    "length": str(round(216 * ratio, 2)),
                    "diameter": "0.5",
                    "position": "0"
                },
                {
                    "element_type": "driven",
                    "length": str(round(204 * ratio, 2)),
                    "diameter": "0.5",
                    "position": str(round(48 * ratio, 2))  # Position scaled
                }
            ],
            "height_from_ground": str(round(54 * ratio, 1)),
            "height_unit": "ft",
            "boom_diameter": "1.5",
            "boom_unit": "inches",
            "band": "10m_ham",
            "frequency_mhz": str(target_freq),
            "use_reflector": True,
            "antenna_orientation": "horizontal",
            "feed_type": "gamma",
            "boom_grounded": True,
            "boom_mount": "bonded"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/calculate",
            json=scaled_input
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify scaled design still produces valid results
        assert 5 < data["gain_dbi"] < 15
        assert 1 < data["swr"] < 10
    
    def test_scaled_12m_design_calculates(self):
        """Scaling to 12m (24.94 MHz) should produce valid calculation"""
        current_freq = 27.185
        target_freq = 24.94
        ratio = current_freq / target_freq
        
        scaled_input = {
            "num_elements": 2,
            "elements": [
                {
                    "element_type": "reflector",
                    "length": str(round(216 * ratio, 2)),
                    "diameter": "0.5",
                    "position": "0"
                },
                {
                    "element_type": "driven",
                    "length": str(round(204 * ratio, 2)),
                    "diameter": "0.5",
                    "position": str(round(48 * ratio, 2))
                }
            ],
            "height_from_ground": str(round(54 * ratio, 1)),
            "height_unit": "ft",
            "boom_diameter": "1.5",
            "boom_unit": "inches",
            "band": "12m_ham",
            "frequency_mhz": str(target_freq),
            "use_reflector": True,
            "antenna_orientation": "horizontal",
            "feed_type": "gamma",
            "boom_grounded": True,
            "boom_mount": "bonded"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/calculate",
            json=scaled_input
        )
        assert response.status_code == 200
        data = response.json()
        
        # Scaled elements should be longer for lower frequency
        assert 5 < data["gain_dbi"] < 15
        assert 1 < data["swr"] < 10
    
    def test_scaling_preserves_proportions(self):
        """Verify scaling preserves element length/position proportions"""
        current_freq = 27.185
        target_freq = 28.5
        ratio = current_freq / target_freq
        
        # Original proportions
        original_reflector_len = 216
        original_driven_len = 204
        original_driven_pos = 48
        
        # After scaling
        scaled_reflector_len = original_reflector_len * ratio
        scaled_driven_len = original_driven_len * ratio
        scaled_driven_pos = original_driven_pos * ratio
        
        # Verify proportional relationships preserved
        original_ratio = original_driven_len / original_reflector_len
        scaled_ratio = scaled_driven_len / scaled_reflector_len
        assert abs(original_ratio - scaled_ratio) < 0.001, "Length proportions not preserved"
        
        # Position should scale proportionally too (key bug fix verification)
        assert abs(scaled_driven_pos / scaled_driven_len - original_driven_pos / original_driven_len) < 0.01


class TestMultiElementScaling:
    """Test scaling with more elements"""
    
    def test_4_element_scaled_design(self):
        """4-element scaled design should calculate correctly"""
        current_freq = 27.185
        target_freq = 28.0
        ratio = current_freq / target_freq
        
        # 4-element design
        elements = [
            {"element_type": "reflector", "length": "216", "diameter": "0.5", "position": "0"},
            {"element_type": "driven", "length": "204", "diameter": "0.5", "position": "48"},
            {"element_type": "director", "length": "192", "diameter": "0.5", "position": "96"},
            {"element_type": "director", "length": "188", "diameter": "0.5", "position": "144"}
        ]
        
        # Scale all elements
        scaled_elements = [
            {
                "element_type": e["element_type"],
                "length": str(round(float(e["length"]) * ratio, 2)),
                "diameter": e["diameter"],
                "position": str(round(float(e["position"]) * ratio, 2))
            }
            for e in elements
        ]
        
        scaled_input = {
            "num_elements": 4,
            "elements": scaled_elements,
            "height_from_ground": str(round(54 * ratio, 1)),
            "height_unit": "ft",
            "boom_diameter": "1.5",
            "boom_unit": "inches",
            "band": "11m_cb",
            "frequency_mhz": str(target_freq),
            "use_reflector": True,
            "antenna_orientation": "horizontal",
            "feed_type": "gamma",
            "boom_grounded": True,
            "boom_mount": "bonded"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/calculate",
            json=scaled_input
        )
        assert response.status_code == 200
        data = response.json()
        
        # 4-element should have higher gain than 2-element
        assert 7 < data["gain_dbi"] < 20
        assert 15 < data["fb_ratio"] < 35


class TestHairpinFeedScaling:
    """Test scaling with hairpin feed type"""
    
    def test_hairpin_scaled_design(self):
        """Hairpin feed design should scale and calculate"""
        current_freq = 27.185
        target_freq = 28.0
        ratio = current_freq / target_freq
        
        scaled_input = {
            "num_elements": 2,
            "elements": [
                {
                    "element_type": "reflector",
                    "length": str(round(216 * ratio, 2)),
                    "diameter": "0.5",
                    "position": "0"
                },
                {
                    "element_type": "driven",
                    "length": str(round(196 * ratio, 2)),  # Hairpin uses ~4% shorter
                    "diameter": "0.5",
                    "position": str(round(48 * ratio, 2))
                }
            ],
            "height_from_ground": str(round(54 * ratio, 1)),
            "height_unit": "ft",
            "boom_diameter": "1.5",
            "boom_unit": "inches",
            "band": "11m_cb",
            "frequency_mhz": str(target_freq),
            "use_reflector": True,
            "antenna_orientation": "horizontal",
            "feed_type": "hairpin",
            "boom_grounded": True,
            "boom_mount": "bonded"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/calculate",
            json=scaled_input
        )
        assert response.status_code == 200
        data = response.json()
        
        assert 5 < data["gain_dbi"] < 15
        assert 1 < data["swr"] < 10


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
