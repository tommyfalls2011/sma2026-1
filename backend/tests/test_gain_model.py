"""
Backend tests for the free-space gain model and boom doubling behavior.

Test Coverage:
1. POST /api/calculate - Free-space gain model verification for element counts 2-20
2. POST /api/calculate - Boom doubling/halving tests (~2.5 dB per doubling)
3. POST /api/calculate - No reflector mode (reflector_adj=-1.5)
4. POST /api/auto-tune - Predicted gain using same free-space model
5. POST /api/calculate - gain_breakdown field verification
"""

import pytest
import requests
import os
import math

BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL', 'https://antenna-calc.preview.emergentagent.com').rstrip('/')

# Standard element dimensions for 27.185 MHz (from review request)
STANDARD_ELEMENTS = {
    "reflector": {"length": 214, "diameter": 0.5},
    "driven": {"length": 205, "diameter": 0.5},
    "director": {"length": 195, "diameter": 0.5}
}

# Standard boom lengths in inches (from review request)
STANDARD_BOOM_LENGTHS = {
    2: 77,
    3: 159,
    5: 270,
    8: 394,
    10: 433
}

# Expected free-space gains from lookup table (from review request)
EXPECTED_FREE_SPACE_GAINS = {
    2: 6.2,    # 6.0-6.5 dBi range
    3: 8.2,    # 8.0-8.5 dBi range
    5: 10.8,   # 10.0-11.5 dBi range (4-5 elements)
    8: 13.0,   # 12.0-13.5 dBi range (6-8 elements)
    10: 14.0,  # 14.0-15.0 dBi range (10-12 elements)
    15: 16.0,  # 16.0-17.5 dBi range (15-20 elements)
    20: 17.2   # 16.0-17.5 dBi range (15-20 elements)
}


def build_element_list(num_elements, boom_length_in, has_reflector=True):
    """Build element list for a Yagi antenna configuration.
    
    IMPORTANT: boom_length_in is the TOTAL boom length (max position - min position).
    The API calculates boom length from: max(positions) - min(positions).
    So for a given boom_length_in, we place elements from 0 to boom_length_in.
    """
    elements = []
    
    if has_reflector:
        # Reflector at position 0
        elements.append({
            "element_type": "reflector",
            "length": STANDARD_ELEMENTS["reflector"]["length"],
            "diameter": STANDARD_ELEMENTS["reflector"]["diameter"],
            "position": 0
        })
        
        if num_elements == 2:
            # Just reflector + driven: driven at boom_length_in
            elements.append({
                "element_type": "driven",
                "length": STANDARD_ELEMENTS["driven"]["length"],
                "diameter": STANDARD_ELEMENTS["driven"]["diameter"],
                "position": boom_length_in  # Full boom length
            })
        else:
            # Driven element at ~15% of boom from reflector
            driven_pos = round(boom_length_in * 0.15, 1)
            elements.append({
                "element_type": "driven",
                "length": STANDARD_ELEMENTS["driven"]["length"],
                "diameter": STANDARD_ELEMENTS["driven"]["diameter"],
                "position": driven_pos
            })
            # Directors evenly spaced from driven to end of boom
            num_directors = num_elements - 2
            if num_directors > 0:
                remaining_boom = boom_length_in - driven_pos
                director_spacing = remaining_boom / num_directors
                for i in range(num_directors):
                    dir_pos = round(driven_pos + director_spacing * (i + 1), 1)
                    elements.append({
                        "element_type": "director",
                        "length": STANDARD_ELEMENTS["director"]["length"] - (i * 2),  # Progressive shortening
                        "diameter": STANDARD_ELEMENTS["director"]["diameter"],
                        "position": dir_pos
                    })
    else:
        # No reflector mode: driven at position 0
        elements.append({
            "element_type": "driven",
            "length": STANDARD_ELEMENTS["driven"]["length"],
            "diameter": STANDARD_ELEMENTS["driven"]["diameter"],
            "position": 0
        })
        # Directors evenly spaced
        num_directors = num_elements - 1
        if num_directors > 0:
            director_spacing = boom_length_in / num_directors
            for i in range(num_directors):
                dir_pos = round(director_spacing * (i + 1), 1)
                elements.append({
                    "element_type": "director",
                    "length": STANDARD_ELEMENTS["director"]["length"] - (i * 2),
                    "diameter": STANDARD_ELEMENTS["director"]["diameter"],
                    "position": dir_pos
                })
    
    return elements


def make_calculate_request(num_elements, boom_length_in, has_reflector=True):
    """Make a POST /api/calculate request."""
    elements = build_element_list(num_elements, boom_length_in, has_reflector)
    
    payload = {
        "num_elements": num_elements,
        "frequency_mhz": 27.185,
        "band": "11m_cb",
        "height_from_ground": 35,
        "height_unit": "ft",
        "boom_diameter": 2.0,
        "boom_unit": "inches",
        "elements": elements
    }
    
    response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
    return response


class TestFreeSpaceGainModel:
    """Test free-space gain model returns expected values for different element counts."""
    
    def test_2_elements_base_gain(self):
        """2 elements should give base ~6.2 dBi"""
        response = make_calculate_request(2, STANDARD_BOOM_LENGTHS[2])
        assert response.status_code == 200, f"API returned {response.status_code}: {response.text}"
        
        data = response.json()
        base_gain = data.get("base_gain_dbi")
        
        # base_gain_dbi should be close to 6.2 (free-space gain for 2 elements)
        assert base_gain is not None, "base_gain_dbi field missing"
        print(f"2 elements base_gain_dbi: {base_gain} (expected ~6.2)")
        
        # Allow for boom adjustment tolerance (within +/- 0.5 dB)
        assert 5.5 <= base_gain <= 7.0, f"2-element base gain {base_gain} out of expected range 5.5-7.0 dBi"
    
    def test_3_elements_base_gain(self):
        """3 elements should give base ~8.2 dBi"""
        response = make_calculate_request(3, STANDARD_BOOM_LENGTHS[3])
        assert response.status_code == 200, f"API returned {response.status_code}: {response.text}"
        
        data = response.json()
        base_gain = data.get("base_gain_dbi")
        
        print(f"3 elements base_gain_dbi: {base_gain} (expected ~8.2)")
        assert base_gain is not None, "base_gain_dbi field missing"
        assert 7.5 <= base_gain <= 9.0, f"3-element base gain {base_gain} out of expected range 7.5-9.0 dBi"
    
    def test_5_elements_base_gain(self):
        """5 elements should give base ~10.8 dBi"""
        response = make_calculate_request(5, STANDARD_BOOM_LENGTHS[5])
        assert response.status_code == 200, f"API returned {response.status_code}: {response.text}"
        
        data = response.json()
        base_gain = data.get("base_gain_dbi")
        
        print(f"5 elements base_gain_dbi: {base_gain} (expected ~10.8)")
        assert base_gain is not None, "base_gain_dbi field missing"
        assert 10.0 <= base_gain <= 11.5, f"5-element base gain {base_gain} out of expected range 10.0-11.5 dBi"
    
    def test_8_elements_base_gain(self):
        """8 elements should give base ~13.0 dBi"""
        response = make_calculate_request(8, STANDARD_BOOM_LENGTHS[8])
        assert response.status_code == 200, f"API returned {response.status_code}: {response.text}"
        
        data = response.json()
        base_gain = data.get("base_gain_dbi")
        
        print(f"8 elements base_gain_dbi: {base_gain} (expected ~13.0)")
        assert base_gain is not None, "base_gain_dbi field missing"
        assert 12.0 <= base_gain <= 14.0, f"8-element base gain {base_gain} out of expected range 12.0-14.0 dBi"
    
    def test_10_elements_base_gain(self):
        """10 elements should give base ~14.0 dBi"""
        response = make_calculate_request(10, STANDARD_BOOM_LENGTHS[10])
        assert response.status_code == 200, f"API returned {response.status_code}: {response.text}"
        
        data = response.json()
        base_gain = data.get("base_gain_dbi")
        
        print(f"10 elements base_gain_dbi: {base_gain} (expected ~14.0)")
        assert base_gain is not None, "base_gain_dbi field missing"
        assert 13.0 <= base_gain <= 15.0, f"10-element base gain {base_gain} out of expected range 13.0-15.0 dBi"


class TestBoomDoublingEffect:
    """Test that doubling boom length yields ~2.5 dB more gain (boom_adj in gain_breakdown)."""
    
    def test_5_elements_boom_doubling(self):
        """5 elements with doubled boom should give ~2.5 dB more in base_gain_dbi."""
        standard_boom = STANDARD_BOOM_LENGTHS[5]  # 270 inches
        doubled_boom = standard_boom * 2          # 540 inches
        
        # Calculate with standard boom
        response_standard = make_calculate_request(5, standard_boom)
        assert response_standard.status_code == 200
        data_standard = response_standard.json()
        base_gain_standard = data_standard.get("base_gain_dbi")
        breakdown_standard = data_standard.get("gain_breakdown", {})
        boom_adj_standard = breakdown_standard.get("boom_adj", 0)
        
        print(f"5 elem @ {standard_boom}\" boom: base_gain={base_gain_standard}, boom_adj={boom_adj_standard}")
        
        # Calculate with doubled boom
        response_doubled = make_calculate_request(5, doubled_boom)
        assert response_doubled.status_code == 200
        data_doubled = response_doubled.json()
        base_gain_doubled = data_doubled.get("base_gain_dbi")
        breakdown_doubled = data_doubled.get("gain_breakdown", {})
        boom_adj_doubled = breakdown_doubled.get("boom_adj", 0)
        
        print(f"5 elem @ {doubled_boom}\" boom: base_gain={base_gain_doubled}, boom_adj={boom_adj_doubled}")
        
        # Gain difference should be ~2.5 dB
        gain_diff = base_gain_doubled - base_gain_standard
        print(f"Gain difference: {gain_diff} dB (expected ~2.5 dB)")
        
        # Allow tolerance of +/- 0.5 dB
        assert 2.0 <= gain_diff <= 3.0, f"Boom doubling gave {gain_diff} dB increase, expected 2.0-3.0 dB"
    
    def test_5_elements_boom_halving(self):
        """5 elements with halved boom should give ~2.5 dB less in base_gain_dbi."""
        standard_boom = STANDARD_BOOM_LENGTHS[5]  # 270 inches
        halved_boom = standard_boom / 2           # 135 inches
        
        # Calculate with standard boom
        response_standard = make_calculate_request(5, standard_boom)
        assert response_standard.status_code == 200
        data_standard = response_standard.json()
        base_gain_standard = data_standard.get("base_gain_dbi")
        
        print(f"5 elem @ {standard_boom}\" boom: base_gain={base_gain_standard}")
        
        # Calculate with halved boom
        response_halved = make_calculate_request(5, halved_boom)
        assert response_halved.status_code == 200
        data_halved = response_halved.json()
        base_gain_halved = data_halved.get("base_gain_dbi")
        
        print(f"5 elem @ {halved_boom}\" boom: base_gain={base_gain_halved}")
        
        # Gain difference should be ~2.5 dB less
        gain_diff = base_gain_standard - base_gain_halved
        print(f"Gain difference: {gain_diff} dB (expected ~2.5 dB)")
        
        # Allow tolerance of +/- 0.5 dB
        assert 2.0 <= gain_diff <= 3.0, f"Boom halving gave {gain_diff} dB decrease, expected 2.0-3.0 dB"
    
    def test_boom_adj_positive_for_longer_boom(self):
        """Verify boom_adj is positive when boom is longer than standard."""
        standard_boom = STANDARD_BOOM_LENGTHS[5]  # 270 inches
        longer_boom = standard_boom * 1.5         # 405 inches
        
        response = make_calculate_request(5, longer_boom)
        assert response.status_code == 200
        data = response.json()
        breakdown = data.get("gain_breakdown", {})
        boom_adj = breakdown.get("boom_adj", 0)
        
        print(f"5 elem @ {longer_boom}\" boom: boom_adj={boom_adj} (should be positive)")
        assert boom_adj > 0, f"boom_adj should be positive for longer boom, got {boom_adj}"
    
    def test_boom_adj_negative_for_shorter_boom(self):
        """Verify boom_adj is negative when boom is shorter than standard."""
        standard_boom = STANDARD_BOOM_LENGTHS[5]  # 270 inches
        shorter_boom = standard_boom * 0.5        # 135 inches
        
        response = make_calculate_request(5, shorter_boom)
        assert response.status_code == 200
        data = response.json()
        breakdown = data.get("gain_breakdown", {})
        boom_adj = breakdown.get("boom_adj", 0)
        
        print(f"5 elem @ {shorter_boom}\" boom: boom_adj={boom_adj} (should be negative)")
        assert boom_adj < 0, f"boom_adj should be negative for shorter boom, got {boom_adj}"


class TestNoReflectorMode:
    """Test that no reflector mode reduces gain by 1.5 dB (reflector_adj=-1.5)."""
    
    def test_no_reflector_reduces_gain(self):
        """Without reflector, gain should be ~1.5 dB less."""
        boom_length = 200  # Use a reasonable boom length
        
        # With reflector (3 elements = reflector + driven + director)
        response_with = make_calculate_request(3, boom_length, has_reflector=True)
        assert response_with.status_code == 200
        data_with = response_with.json()
        base_gain_with = data_with.get("base_gain_dbi")
        breakdown_with = data_with.get("gain_breakdown", {})
        
        print(f"WITH reflector: base_gain={base_gain_with}, breakdown={breakdown_with}")
        
        # Without reflector (3 elements = driven + 2 directors)
        response_without = make_calculate_request(3, boom_length, has_reflector=False)
        assert response_without.status_code == 200
        data_without = response_without.json()
        base_gain_without = data_without.get("base_gain_dbi")
        breakdown_without = data_without.get("gain_breakdown", {})
        reflector_adj = breakdown_without.get("reflector_adj", 0)
        
        print(f"WITHOUT reflector: base_gain={base_gain_without}, reflector_adj={reflector_adj}")
        
        # reflector_adj should be -1.5
        assert reflector_adj == -1.5, f"reflector_adj should be -1.5, got {reflector_adj}"
        
        # Gain difference should be ~1.5 dB
        gain_diff = base_gain_with - base_gain_without
        print(f"Gain difference: {gain_diff} dB (expected ~1.5 dB)")
        
        assert 1.0 <= gain_diff <= 2.0, f"No-reflector gain reduction was {gain_diff} dB, expected 1.0-2.0 dB"
    
    def test_reflector_adj_is_zero_with_reflector(self):
        """With reflector, reflector_adj should be 0."""
        response = make_calculate_request(3, 159, has_reflector=True)
        assert response.status_code == 200
        data = response.json()
        breakdown = data.get("gain_breakdown", {})
        reflector_adj = breakdown.get("reflector_adj", None)
        
        print(f"WITH reflector: reflector_adj={reflector_adj}")
        assert reflector_adj == 0, f"reflector_adj should be 0 with reflector, got {reflector_adj}"


class TestAutoTunePredictedGain:
    """Test that auto-tune uses the same free-space gain model."""
    
    def make_auto_tune_request(self, num_elements, use_reflector=True):
        """Make a POST /api/auto-tune request."""
        payload = {
            "num_elements": num_elements,
            "frequency_mhz": 27.185,
            "band": "11m_cb",
            "height_from_ground": 35,
            "height_unit": "ft",
            "boom_diameter": 2.0,
            "boom_unit": "inches",
            "use_reflector": use_reflector
        }
        response = requests.post(f"{BASE_URL}/api/auto-tune", json=payload)
        return response
    
    def test_auto_tune_3_elements_predicted_gain(self):
        """3 elements auto-tune should predict ~10.2 dBi (8.2 base + 2.0 height estimate)."""
        response = self.make_auto_tune_request(3)
        assert response.status_code == 200, f"API returned {response.status_code}: {response.text}"
        
        data = response.json()
        predicted_gain = data.get("predicted_gain")
        
        print(f"Auto-tune 3 elements: predicted_gain={predicted_gain} (expected ~10.2)")
        
        # Expected: 8.2 (base) + 2.0 (height) = 10.2 dBi
        assert predicted_gain is not None, "predicted_gain field missing"
        assert 9.5 <= predicted_gain <= 11.0, f"3-element predicted gain {predicted_gain} out of expected range"
    
    def test_auto_tune_10_elements_predicted_gain(self):
        """10 elements auto-tune should predict ~16.0 dBi (14.0 base + 2.0 height estimate)."""
        response = self.make_auto_tune_request(10)
        assert response.status_code == 200, f"API returned {response.status_code}: {response.text}"
        
        data = response.json()
        predicted_gain = data.get("predicted_gain")
        
        print(f"Auto-tune 10 elements: predicted_gain={predicted_gain} (expected ~16.0)")
        
        # Expected: 14.0 (base) + 2.0 (height) = 16.0 dBi
        assert predicted_gain is not None, "predicted_gain field missing"
        assert 15.0 <= predicted_gain <= 17.0, f"10-element predicted gain {predicted_gain} out of expected range"
    
    def test_auto_tune_20_elements_predicted_gain(self):
        """20 elements auto-tune should predict ~19.2 dBi (17.2 base + 2.0 height estimate)."""
        response = self.make_auto_tune_request(20)
        assert response.status_code == 200, f"API returned {response.status_code}: {response.text}"
        
        data = response.json()
        predicted_gain = data.get("predicted_gain")
        
        print(f"Auto-tune 20 elements: predicted_gain={predicted_gain} (expected ~19.2)")
        
        # Expected: 17.2 (base) + 2.0 (height) = 19.2 dBi
        assert predicted_gain is not None, "predicted_gain field missing"
        assert 18.0 <= predicted_gain <= 20.0, f"20-element predicted gain {predicted_gain} out of expected range"
    
    def test_auto_tune_no_reflector_reduces_predicted_gain(self):
        """Auto-tune without reflector should reduce predicted gain by 1.5 dB."""
        response_with = self.make_auto_tune_request(5, use_reflector=True)
        response_without = self.make_auto_tune_request(5, use_reflector=False)
        
        assert response_with.status_code == 200
        assert response_without.status_code == 200
        
        gain_with = response_with.json().get("predicted_gain")
        gain_without = response_without.json().get("predicted_gain")
        
        print(f"Auto-tune 5 elem WITH reflector: {gain_with}")
        print(f"Auto-tune 5 elem WITHOUT reflector: {gain_without}")
        
        gain_diff = gain_with - gain_without
        print(f"Gain difference: {gain_diff} dB (expected ~1.5 dB)")
        
        assert 1.0 <= gain_diff <= 2.0, f"No-reflector auto-tune gave {gain_diff} dB less, expected 1.0-2.0 dB"


class TestGainBreakdownFields:
    """Test that gain_breakdown contains all required fields."""
    
    def test_gain_breakdown_contains_all_fields(self):
        """Verify gain_breakdown contains: standard_gain, boom_adj, reflector_adj, taper_bonus, corona_adj, height_bonus, boom_bonus, final_gain."""
        response = make_calculate_request(5, STANDARD_BOOM_LENGTHS[5])
        assert response.status_code == 200
        
        data = response.json()
        breakdown = data.get("gain_breakdown")
        
        assert breakdown is not None, "gain_breakdown field missing"
        
        # Required fields
        required_fields = [
            "standard_gain", "boom_adj", "reflector_adj", "taper_bonus", 
            "corona_adj", "height_bonus", "boom_bonus", "final_gain"
        ]
        
        print(f"Gain breakdown: {breakdown}")
        
        for field in required_fields:
            assert field in breakdown, f"gain_breakdown missing required field: {field}"
            print(f"  {field}: {breakdown[field]}")
    
    def test_final_gain_equals_gain_dbi(self):
        """Verify final_gain in breakdown equals gain_dbi in response."""
        response = make_calculate_request(5, STANDARD_BOOM_LENGTHS[5])
        assert response.status_code == 200
        
        data = response.json()
        gain_dbi = data.get("gain_dbi")
        breakdown = data.get("gain_breakdown", {})
        final_gain = breakdown.get("final_gain")
        
        print(f"gain_dbi: {gain_dbi}, final_gain: {final_gain}")
        
        # Should be equal (allowing for rounding)
        assert abs(gain_dbi - final_gain) < 0.1, f"gain_dbi ({gain_dbi}) != final_gain ({final_gain})"
    
    def test_gain_breakdown_math_adds_up(self):
        """Verify the gain breakdown components add up to final_gain."""
        response = make_calculate_request(5, STANDARD_BOOM_LENGTHS[5])
        assert response.status_code == 200
        
        data = response.json()
        breakdown = data.get("gain_breakdown", {})
        
        # Calculate expected final gain from components
        calculated_final = (
            breakdown.get("standard_gain", 0) +
            breakdown.get("boom_adj", 0) +
            breakdown.get("reflector_adj", 0) +
            breakdown.get("taper_bonus", 0) +
            breakdown.get("corona_adj", 0) +
            breakdown.get("height_bonus", 0) +
            breakdown.get("boom_bonus", 0)
        )
        
        final_gain = breakdown.get("final_gain", 0)
        
        print(f"Calculated sum: {calculated_final}, final_gain: {final_gain}")
        print(f"Components: standard_gain={breakdown.get('standard_gain')}, boom_adj={breakdown.get('boom_adj')}, "
              f"reflector_adj={breakdown.get('reflector_adj')}, height_bonus={breakdown.get('height_bonus')}, "
              f"boom_bonus={breakdown.get('boom_bonus')}")
        
        # Allow for rounding errors
        assert abs(calculated_final - final_gain) < 0.2, f"Components sum ({calculated_final}) != final_gain ({final_gain})"


class TestAPIHealth:
    """Basic health checks for endpoints."""
    
    def test_calculate_endpoint_accessible(self):
        """Verify /api/calculate endpoint is accessible."""
        response = make_calculate_request(3, 159)
        assert response.status_code == 200, f"API returned {response.status_code}"
    
    def test_auto_tune_endpoint_accessible(self):
        """Verify /api/auto-tune endpoint is accessible."""
        payload = {
            "num_elements": 3,
            "frequency_mhz": 27.185,
            "band": "11m_cb",
            "height_from_ground": 35,
            "height_unit": "ft",
            "boom_diameter": 2.0,
            "boom_unit": "inches"
        }
        response = requests.post(f"{BASE_URL}/api/auto-tune", json=payload)
        assert response.status_code == 200, f"API returned {response.status_code}: {response.text}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
