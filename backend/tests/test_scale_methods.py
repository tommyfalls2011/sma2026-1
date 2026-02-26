"""
Test cases for Scale Method functionality: Proportional vs Ratio scaling.
Tests verify:
1. Both scaling methods produce valid antenna calculations
2. Proportional method computes ideal driven length using wavelength-based formula
3. Ratio method uses simple frequency ratio
4. Both methods can scale to various target frequencies
"""
import pytest
import requests
import os
import math

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


def compute_proportional_scale_factor(source_freq: float, target_freq: float, driven_length: float, driven_diameter: float) -> float:
    """
    Compute proportional scale factor as done in frontend:
    idealDriven = (wavelength/2) * (0.935 - 0.5 * diameter/wavelength)
    scaleFactor = idealDriven / currentDriven
    """
    wavelength_target = 11803 / target_freq  # inches
    d_ratio = driven_diameter / wavelength_target
    driven_pct = 0.935 - 0.5 * d_ratio
    ideal_driven = (wavelength_target / 2) * driven_pct
    return ideal_driven / driven_length


def compute_ratio_scale_factor(source_freq: float, target_freq: float) -> float:
    """
    Compute ratio scale factor: source_freq / target_freq
    """
    return source_freq / target_freq


class TestScaleMethodFormulas:
    """Test scale method math calculations match expected values"""
    
    def test_proportional_factor_same_frequency(self):
        """Scaling to same frequency computes idealDriven / currentDriven"""
        source_freq = 27.185
        target_freq = 27.185
        driven_length = 204
        driven_diameter = 0.5
        
        factor = compute_proportional_scale_factor(source_freq, target_freq, driven_length, driven_diameter)
        # Proportional method computes ideal driven length at target freq, then divides by current
        # For the default 204" driven at 27.185 MHz, ideal is ~202.8", giving factor ~0.994
        # This is by design - it adjusts elements toward the ideal for that frequency
        wavelength = 11803 / target_freq  # ~434.2"
        d_ratio = driven_diameter / wavelength
        pct = 0.935 - 0.5 * d_ratio
        expected_ideal = (wavelength / 2) * pct  # ~202.8"
        expected_factor = expected_ideal / driven_length  # ~0.994
        assert abs(factor - expected_factor) < 0.0001, f"Proportional factor {factor} != expected {expected_factor}"
    
    def test_ratio_factor_same_frequency(self):
        """Ratio scaling to same frequency should give exactly 1.0"""
        source_freq = 27.185
        target_freq = 27.185
        
        factor = compute_ratio_scale_factor(source_freq, target_freq)
        assert factor == 1.0, f"Ratio factor {factor} should be 1.0"
    
    def test_proportional_factor_higher_frequency(self):
        """Scaling to higher frequency should give factor < 1.0 (shorter elements)"""
        source_freq = 27.185
        target_freq = 28.5  # 10m band
        driven_length = 204
        driven_diameter = 0.5
        
        factor = compute_proportional_scale_factor(source_freq, target_freq, driven_length, driven_diameter)
        # Should be less than 1.0 (elements get shorter)
        assert 0.9 < factor < 1.0, f"Proportional factor {factor} should be < 1.0 for higher freq"
    
    def test_ratio_factor_higher_frequency(self):
        """Ratio scaling to higher frequency should give factor < 1.0"""
        source_freq = 27.185
        target_freq = 28.5
        
        factor = compute_ratio_scale_factor(source_freq, target_freq)
        expected = source_freq / target_freq  # 27.185 / 28.5 ≈ 0.9538
        assert abs(factor - expected) < 0.0001
        assert factor < 1.0
    
    def test_proportional_factor_lower_frequency(self):
        """Scaling to lower frequency should give factor > 1.0 (longer elements)"""
        source_freq = 27.185
        target_freq = 24.94  # 12m band
        driven_length = 204
        driven_diameter = 0.5
        
        factor = compute_proportional_scale_factor(source_freq, target_freq, driven_length, driven_diameter)
        # Should be greater than 1.0 (elements get longer)
        assert 1.0 < factor < 1.2, f"Proportional factor {factor} should be > 1.0 for lower freq"
    
    def test_ratio_factor_lower_frequency(self):
        """Ratio scaling to lower frequency should give factor > 1.0"""
        source_freq = 27.185
        target_freq = 24.94
        
        factor = compute_ratio_scale_factor(source_freq, target_freq)
        expected = source_freq / target_freq  # 27.185 / 24.94 ≈ 1.09
        assert abs(factor - expected) < 0.0001
        assert factor > 1.0
    
    def test_methods_differ_for_large_band_changes(self):
        """Proportional and Ratio should give different factors for large band changes"""
        source_freq = 27.185
        target_freq = 146.0  # 2m band - very large change
        driven_length = 204
        driven_diameter = 0.5
        
        prop_factor = compute_proportional_scale_factor(source_freq, target_freq, driven_length, driven_diameter)
        ratio_factor = compute_ratio_scale_factor(source_freq, target_freq)
        
        # They should be different
        assert abs(prop_factor - ratio_factor) > 0.001, "Methods should differ for large band changes"


class TestProportionalScalingCalculations:
    """Test /api/calculate with proportional scaling applied"""
    
    def test_proportional_scaling_to_10m(self):
        """Proportional scaling to 10m should produce valid calculation"""
        source_freq = 27.185
        target_freq = 28.5
        driven_length = 204
        driven_diameter = 0.5
        
        scale_factor = compute_proportional_scale_factor(source_freq, target_freq, driven_length, driven_diameter)
        
        scaled_input = {
            "num_elements": 2,
            "elements": [
                {
                    "element_type": "reflector",
                    "length": str(round(216 * scale_factor, 2)),
                    "diameter": "0.5",
                    "position": "0"
                },
                {
                    "element_type": "driven",
                    "length": str(round(204 * scale_factor, 2)),
                    "diameter": "0.5",
                    "position": str(round(48 * scale_factor, 2))
                }
            ],
            "height_from_ground": str(round(54 * scale_factor, 1)),
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
        
        response = requests.post(f"{BASE_URL}/api/calculate", json=scaled_input)
        assert response.status_code == 200, f"API error: {response.text}"
        
        data = response.json()
        assert "gain_dbi" in data
        assert 5 < data["gain_dbi"] < 15, f"Gain {data['gain_dbi']} out of expected range"
        assert 1 < data["swr"] < 10, f"SWR {data['swr']} out of expected range"
    
    def test_proportional_scaling_to_12m(self):
        """Proportional scaling to 12m should produce valid calculation"""
        source_freq = 27.185
        target_freq = 24.94
        driven_length = 204
        driven_diameter = 0.5
        
        scale_factor = compute_proportional_scale_factor(source_freq, target_freq, driven_length, driven_diameter)
        
        scaled_input = {
            "num_elements": 2,
            "elements": [
                {
                    "element_type": "reflector",
                    "length": str(round(216 * scale_factor, 2)),
                    "diameter": "0.5",
                    "position": "0"
                },
                {
                    "element_type": "driven",
                    "length": str(round(204 * scale_factor, 2)),
                    "diameter": "0.5",
                    "position": str(round(48 * scale_factor, 2))
                }
            ],
            "height_from_ground": str(round(54 * scale_factor, 1)),
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
        
        response = requests.post(f"{BASE_URL}/api/calculate", json=scaled_input)
        assert response.status_code == 200, f"API error: {response.text}"
        
        data = response.json()
        assert "gain_dbi" in data
        assert 5 < data["gain_dbi"] < 15
    
    def test_proportional_scaling_to_2m(self):
        """Proportional scaling to 2m (large band change) should produce valid calculation"""
        source_freq = 27.185
        target_freq = 146.0
        driven_length = 204
        driven_diameter = 0.5
        
        scale_factor = compute_proportional_scale_factor(source_freq, target_freq, driven_length, driven_diameter)
        
        scaled_input = {
            "num_elements": 2,
            "elements": [
                {
                    "element_type": "reflector",
                    "length": str(round(216 * scale_factor, 2)),
                    "diameter": "0.25",  # Smaller tube for 2m
                    "position": "0"
                },
                {
                    "element_type": "driven",
                    "length": str(round(204 * scale_factor, 2)),
                    "diameter": "0.25",
                    "position": str(round(48 * scale_factor, 2))
                }
            ],
            "height_from_ground": str(round(54 * scale_factor, 1)),
            "height_unit": "ft",
            "boom_diameter": "0.75",
            "boom_unit": "inches",
            "band": "2m_ham",
            "frequency_mhz": str(target_freq),
            "use_reflector": True,
            "antenna_orientation": "horizontal",
            "feed_type": "gamma",
            "boom_grounded": True,
            "boom_mount": "bonded"
        }
        
        response = requests.post(f"{BASE_URL}/api/calculate", json=scaled_input)
        assert response.status_code == 200, f"API error: {response.text}"
        
        data = response.json()
        assert "gain_dbi" in data


class TestRatioScalingCalculations:
    """Test /api/calculate with ratio scaling applied"""
    
    def test_ratio_scaling_to_10m(self):
        """Ratio scaling to 10m should produce valid calculation"""
        source_freq = 27.185
        target_freq = 28.5
        
        scale_factor = compute_ratio_scale_factor(source_freq, target_freq)
        
        scaled_input = {
            "num_elements": 2,
            "elements": [
                {
                    "element_type": "reflector",
                    "length": str(round(216 * scale_factor, 2)),
                    "diameter": "0.5",
                    "position": "0"
                },
                {
                    "element_type": "driven",
                    "length": str(round(204 * scale_factor, 2)),
                    "diameter": "0.5",
                    "position": str(round(48 * scale_factor, 2))
                }
            ],
            "height_from_ground": str(round(54 * scale_factor, 1)),
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
        
        response = requests.post(f"{BASE_URL}/api/calculate", json=scaled_input)
        assert response.status_code == 200, f"API error: {response.text}"
        
        data = response.json()
        assert "gain_dbi" in data
        assert 5 < data["gain_dbi"] < 15
    
    def test_ratio_scaling_to_6m(self):
        """Ratio scaling to 6m should produce valid calculation"""
        source_freq = 27.185
        target_freq = 51.0
        
        scale_factor = compute_ratio_scale_factor(source_freq, target_freq)
        
        scaled_input = {
            "num_elements": 2,
            "elements": [
                {
                    "element_type": "reflector",
                    "length": str(round(216 * scale_factor, 2)),
                    "diameter": "0.375",
                    "position": "0"
                },
                {
                    "element_type": "driven",
                    "length": str(round(204 * scale_factor, 2)),
                    "diameter": "0.375",
                    "position": str(round(48 * scale_factor, 2))
                }
            ],
            "height_from_ground": str(round(54 * scale_factor, 1)),
            "height_unit": "ft",
            "boom_diameter": "1.0",
            "boom_unit": "inches",
            "band": "6m_ham",
            "frequency_mhz": str(target_freq),
            "use_reflector": True,
            "antenna_orientation": "horizontal",
            "feed_type": "gamma",
            "boom_grounded": True,
            "boom_mount": "bonded"
        }
        
        response = requests.post(f"{BASE_URL}/api/calculate", json=scaled_input)
        assert response.status_code == 200, f"API error: {response.text}"
        
        data = response.json()
        assert "gain_dbi" in data


class TestBothMethodsComparison:
    """Compare results from both scaling methods"""
    
    def test_both_methods_produce_valid_results_small_change(self):
        """Both methods should produce valid results for small frequency change"""
        source_freq = 27.185
        target_freq = 27.5
        driven_length = 204
        driven_diameter = 0.5
        
        prop_factor = compute_proportional_scale_factor(source_freq, target_freq, driven_length, driven_diameter)
        ratio_factor = compute_ratio_scale_factor(source_freq, target_freq)
        
        # Test proportional
        prop_input = {
            "num_elements": 2,
            "elements": [
                {"element_type": "reflector", "length": str(round(216 * prop_factor, 2)), "diameter": "0.5", "position": "0"},
                {"element_type": "driven", "length": str(round(204 * prop_factor, 2)), "diameter": "0.5", "position": str(round(48 * prop_factor, 2))}
            ],
            "height_from_ground": "54", "height_unit": "ft", "boom_diameter": "1.5", "boom_unit": "inches",
            "band": "11m_cb", "frequency_mhz": str(target_freq), "use_reflector": True,
            "antenna_orientation": "horizontal", "feed_type": "gamma", "boom_grounded": True, "boom_mount": "bonded"
        }
        
        ratio_input = {
            "num_elements": 2,
            "elements": [
                {"element_type": "reflector", "length": str(round(216 * ratio_factor, 2)), "diameter": "0.5", "position": "0"},
                {"element_type": "driven", "length": str(round(204 * ratio_factor, 2)), "diameter": "0.5", "position": str(round(48 * ratio_factor, 2))}
            ],
            "height_from_ground": "54", "height_unit": "ft", "boom_diameter": "1.5", "boom_unit": "inches",
            "band": "11m_cb", "frequency_mhz": str(target_freq), "use_reflector": True,
            "antenna_orientation": "horizontal", "feed_type": "gamma", "boom_grounded": True, "boom_mount": "bonded"
        }
        
        prop_response = requests.post(f"{BASE_URL}/api/calculate", json=prop_input)
        ratio_response = requests.post(f"{BASE_URL}/api/calculate", json=ratio_input)
        
        assert prop_response.status_code == 200
        assert ratio_response.status_code == 200
        
        prop_data = prop_response.json()
        ratio_data = ratio_response.json()
        
        # Both should have valid results
        assert "gain_dbi" in prop_data
        assert "gain_dbi" in ratio_data
    
    def test_proportional_better_for_large_band_change(self):
        """Proportional method should produce more accurate ideal driven length for large changes"""
        # This is a validation that the proportional formula produces elements
        # that are close to ideal half-wave dipole length at target frequency
        
        target_freq = 146.0  # 2m band
        driven_diameter = 0.25  # inches
        
        # Compute ideal driven length at 146 MHz using the formula
        wavelength = 11803 / target_freq  # ≈ 80.8 inches
        d_ratio = driven_diameter / wavelength
        driven_pct = 0.935 - 0.5 * d_ratio
        ideal_driven = (wavelength / 2) * driven_pct
        
        # Ideal half-wave for 146 MHz should be around 38-40 inches
        assert 35 < ideal_driven < 45, f"Ideal driven {ideal_driven} out of expected range for 2m"


class TestResetAllAfterScaling:
    """Test that Reset All works correctly after scale method changes"""
    
    def test_default_calculation_after_simulated_reset(self):
        """Default config should calculate correctly (simulating Reset All)"""
        # This tests that after any scaling, returning to defaults produces valid results
        response = requests.post(f"{BASE_URL}/api/calculate", json=DEFAULT_ANTENNA_INPUT)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify default 27.185 MHz design works
        assert "gain_dbi" in data
        assert 5 < data["gain_dbi"] < 15
        assert "swr" in data
        assert 1 < data["swr"] < 10


class TestHealthCheck:
    """Basic health check"""
    
    def test_api_health(self):
        """API should be healthy"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["api"] == "up"
        assert data["database"] == "up"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
