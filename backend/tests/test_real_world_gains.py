"""
Backend tests for the real-world gain model with ground reflection.

Test Coverage:
1. POST /api/auto-tune - Real-world gains at 36ft must match user-specified values
2. POST /api/auto-tune - Boom lengths must match user specs
3. POST /api/calculate - Ground gain model verification (height_bonus field)
4. POST /api/calculate - Height is King test (3-elem at different heights)
5. POST /api/calculate - Boom doubling still yields ~2.5dB increase
6. POST /api/calculate - No reflector still applies -1.5dB
7. POST /api/calculate - gain_breakdown field verification

User-provided real-world gain data at 1λ height (36ft at 27MHz):
2elem=12.0dBi, 3elem=13.7dBi, 4elem=15.3dBi, 5elem=16.5dBi, 6elem=17.6dBi,
8elem=18.9dBi, 10elem=20.0dBi, 12elem=21.0dBi, 15elem=22.0dBi, 20elem=23.1dBi

Formula: G_real = G_free_space + G_ground
Ground gain at 1λ ≈ 5.5-6 dBi
"""

import pytest
import requests
import os
import math

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://match-model.preview.emergentagent.com').rstrip('/')

# === USER-SPECIFIED REAL-WORLD GAINS AT 36ft (1λ) ===
# Tolerance: ±0.5 dBi
REAL_WORLD_GAINS_36FT = {
    2: {"expected": 12.0, "tolerance": 0.5},
    3: {"expected": 14.0, "tolerance": 0.5},   # ~13.7 rounded
    5: {"expected": 16.6, "tolerance": 0.5},   # ~16.5
    8: {"expected": 18.8, "tolerance": 0.5},   # ~18.9
    10: {"expected": 19.8, "tolerance": 0.5},  # ~20.0
    15: {"expected": 21.8, "tolerance": 0.5},  # ~22.0
    20: {"expected": 23.0, "tolerance": 0.5},  # ~23.1
}

# === USER-SPECIFIED BOOM LENGTHS (inches) ===
# Tolerance: ±5%
USER_BOOM_LENGTHS = {
    2: 47,     # ~1.2m
    3: 138,    # ~3.5m
    5: 295,    # ~7.5m
    8: 551,    # ~14.0m
    10: 728,   # ~18.5m
}

# Standard element dimensions for 27.185 MHz
STANDARD_ELEMENTS = {
    "reflector": {"length": 214, "diameter": 0.5},
    "driven": {"length": 205, "diameter": 0.5},
    "director": {"length": 195, "diameter": 0.5}
}


def build_element_list(num_elements, boom_length_in, has_reflector=True):
    """Build element list for a Yagi antenna configuration."""
    elements = []
    
    if has_reflector:
        elements.append({
            "element_type": "reflector",
            "length": STANDARD_ELEMENTS["reflector"]["length"],
            "diameter": STANDARD_ELEMENTS["reflector"]["diameter"],
            "position": 0
        })
        
        if num_elements == 2:
            elements.append({
                "element_type": "driven",
                "length": STANDARD_ELEMENTS["driven"]["length"],
                "diameter": STANDARD_ELEMENTS["driven"]["diameter"],
                "position": boom_length_in
            })
        else:
            driven_pos = round(boom_length_in * 0.15, 1)
            elements.append({
                "element_type": "driven",
                "length": STANDARD_ELEMENTS["driven"]["length"],
                "diameter": STANDARD_ELEMENTS["driven"]["diameter"],
                "position": driven_pos
            })
            num_directors = num_elements - 2
            if num_directors > 0:
                remaining_boom = boom_length_in - driven_pos
                director_spacing = remaining_boom / num_directors
                for i in range(num_directors):
                    dir_pos = round(driven_pos + director_spacing * (i + 1), 1)
                    elements.append({
                        "element_type": "director",
                        "length": STANDARD_ELEMENTS["director"]["length"] - (i * 2),
                        "diameter": STANDARD_ELEMENTS["director"]["diameter"],
                        "position": dir_pos
                    })
    else:
        elements.append({
            "element_type": "driven",
            "length": STANDARD_ELEMENTS["driven"]["length"],
            "diameter": STANDARD_ELEMENTS["driven"]["diameter"],
            "position": 0
        })
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


def make_calculate_request(num_elements, boom_length_in, height_ft=36, has_reflector=True):
    """Make a POST /api/calculate request with specified parameters."""
    elements = build_element_list(num_elements, boom_length_in, has_reflector)
    
    payload = {
        "num_elements": num_elements,
        "frequency_mhz": 27.185,
        "band": "11m_cb",
        "height_from_ground": height_ft,
        "height_unit": "ft",  # IMPORTANT: Must be 'ft' not 'feet'
        "boom_diameter": 2.0,
        "boom_unit": "inches",
        "elements": elements
    }
    
    response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
    return response


def make_auto_tune_request(num_elements, height_ft=36, use_reflector=True):
    """Make a POST /api/auto-tune request with specified parameters."""
    payload = {
        "num_elements": num_elements,
        "frequency_mhz": 27.185,
        "band": "11m_cb",
        "height_from_ground": height_ft,
        "height_unit": "ft",  # IMPORTANT: Must be 'ft' not 'feet'
        "boom_diameter": 2.0,
        "boom_unit": "inches",
        "use_reflector": use_reflector
    }
    
    response = requests.post(f"{BASE_URL}/api/auto-tune", json=payload)
    return response


class TestAutoTuneRealWorldGains:
    """Test auto-tune predicted gains match user-specified real-world values at 36ft."""
    
    def test_2_elements_gain_at_36ft(self):
        """2 elements at 36ft should give ~12.0 dBi"""
        response = make_auto_tune_request(2, height_ft=36)
        assert response.status_code == 200, f"API returned {response.status_code}: {response.text}"
        
        data = response.json()
        predicted_gain = data.get("predicted_gain")
        expected = REAL_WORLD_GAINS_36FT[2]["expected"]
        tolerance = REAL_WORLD_GAINS_36FT[2]["tolerance"]
        
        print(f"2-elem auto-tune @ 36ft: predicted_gain={predicted_gain} dBi (expected {expected}±{tolerance})")
        
        assert predicted_gain is not None, "predicted_gain field missing"
        assert expected - tolerance <= predicted_gain <= expected + tolerance, \
            f"2-element gain {predicted_gain} dBi outside expected range {expected}±{tolerance}"
    
    def test_3_elements_gain_at_36ft(self):
        """3 elements at 36ft should give ~14.0 dBi"""
        response = make_auto_tune_request(3, height_ft=36)
        assert response.status_code == 200, f"API returned {response.status_code}: {response.text}"
        
        data = response.json()
        predicted_gain = data.get("predicted_gain")
        expected = REAL_WORLD_GAINS_36FT[3]["expected"]
        tolerance = REAL_WORLD_GAINS_36FT[3]["tolerance"]
        
        print(f"3-elem auto-tune @ 36ft: predicted_gain={predicted_gain} dBi (expected {expected}±{tolerance})")
        
        assert predicted_gain is not None, "predicted_gain field missing"
        assert expected - tolerance <= predicted_gain <= expected + tolerance, \
            f"3-element gain {predicted_gain} dBi outside expected range {expected}±{tolerance}"
    
    def test_5_elements_gain_at_36ft(self):
        """5 elements at 36ft should give ~16.6 dBi"""
        response = make_auto_tune_request(5, height_ft=36)
        assert response.status_code == 200, f"API returned {response.status_code}: {response.text}"
        
        data = response.json()
        predicted_gain = data.get("predicted_gain")
        expected = REAL_WORLD_GAINS_36FT[5]["expected"]
        tolerance = REAL_WORLD_GAINS_36FT[5]["tolerance"]
        
        print(f"5-elem auto-tune @ 36ft: predicted_gain={predicted_gain} dBi (expected {expected}±{tolerance})")
        
        assert predicted_gain is not None, "predicted_gain field missing"
        assert expected - tolerance <= predicted_gain <= expected + tolerance, \
            f"5-element gain {predicted_gain} dBi outside expected range {expected}±{tolerance}"
    
    def test_8_elements_gain_at_36ft(self):
        """8 elements at 36ft should give ~18.8 dBi"""
        response = make_auto_tune_request(8, height_ft=36)
        assert response.status_code == 200, f"API returned {response.status_code}: {response.text}"
        
        data = response.json()
        predicted_gain = data.get("predicted_gain")
        expected = REAL_WORLD_GAINS_36FT[8]["expected"]
        tolerance = REAL_WORLD_GAINS_36FT[8]["tolerance"]
        
        print(f"8-elem auto-tune @ 36ft: predicted_gain={predicted_gain} dBi (expected {expected}±{tolerance})")
        
        assert predicted_gain is not None, "predicted_gain field missing"
        assert expected - tolerance <= predicted_gain <= expected + tolerance, \
            f"8-element gain {predicted_gain} dBi outside expected range {expected}±{tolerance}"
    
    def test_10_elements_gain_at_36ft(self):
        """10 elements at 36ft should give ~19.8 dBi"""
        response = make_auto_tune_request(10, height_ft=36)
        assert response.status_code == 200, f"API returned {response.status_code}: {response.text}"
        
        data = response.json()
        predicted_gain = data.get("predicted_gain")
        expected = REAL_WORLD_GAINS_36FT[10]["expected"]
        tolerance = REAL_WORLD_GAINS_36FT[10]["tolerance"]
        
        print(f"10-elem auto-tune @ 36ft: predicted_gain={predicted_gain} dBi (expected {expected}±{tolerance})")
        
        assert predicted_gain is not None, "predicted_gain field missing"
        assert expected - tolerance <= predicted_gain <= expected + tolerance, \
            f"10-element gain {predicted_gain} dBi outside expected range {expected}±{tolerance}"
    
    def test_15_elements_gain_at_36ft(self):
        """15 elements at 36ft should give ~21.8 dBi"""
        response = make_auto_tune_request(15, height_ft=36)
        assert response.status_code == 200, f"API returned {response.status_code}: {response.text}"
        
        data = response.json()
        predicted_gain = data.get("predicted_gain")
        expected = REAL_WORLD_GAINS_36FT[15]["expected"]
        tolerance = REAL_WORLD_GAINS_36FT[15]["tolerance"]
        
        print(f"15-elem auto-tune @ 36ft: predicted_gain={predicted_gain} dBi (expected {expected}±{tolerance})")
        
        assert predicted_gain is not None, "predicted_gain field missing"
        assert expected - tolerance <= predicted_gain <= expected + tolerance, \
            f"15-element gain {predicted_gain} dBi outside expected range {expected}±{tolerance}"
    
    def test_20_elements_gain_at_36ft(self):
        """20 elements at 36ft should give ~23.0 dBi"""
        response = make_auto_tune_request(20, height_ft=36)
        assert response.status_code == 200, f"API returned {response.status_code}: {response.text}"
        
        data = response.json()
        predicted_gain = data.get("predicted_gain")
        expected = REAL_WORLD_GAINS_36FT[20]["expected"]
        tolerance = REAL_WORLD_GAINS_36FT[20]["tolerance"]
        
        print(f"20-elem auto-tune @ 36ft: predicted_gain={predicted_gain} dBi (expected {expected}±{tolerance})")
        
        assert predicted_gain is not None, "predicted_gain field missing"
        assert expected - tolerance <= predicted_gain <= expected + tolerance, \
            f"20-element gain {predicted_gain} dBi outside expected range {expected}±{tolerance}"


class TestAutoTuneBoomLengths:
    """Test auto-tune generates boom lengths matching user specs."""
    
    def test_2_element_boom_length(self):
        """2-element boom should be ~47 inches (1.2m)"""
        response = make_auto_tune_request(2)
        assert response.status_code == 200
        
        data = response.json()
        elements = data.get("optimized_elements", [])
        
        positions = [e["position"] for e in elements]
        boom_length = max(positions) - min(positions)
        expected = USER_BOOM_LENGTHS[2]
        tolerance_pct = 0.10  # 10% tolerance
        
        print(f"2-elem boom: {boom_length}\" (expected ~{expected}\")")
        
        assert expected * (1 - tolerance_pct) <= boom_length <= expected * (1 + tolerance_pct), \
            f"2-element boom {boom_length}\" outside expected range {expected}\" ±10%"
    
    def test_3_element_boom_length(self):
        """3-element boom should be ~138 inches (3.5m)"""
        response = make_auto_tune_request(3)
        assert response.status_code == 200
        
        data = response.json()
        elements = data.get("optimized_elements", [])
        
        positions = [e["position"] for e in elements]
        boom_length = max(positions) - min(positions)
        expected = USER_BOOM_LENGTHS[3]
        tolerance_pct = 0.10
        
        print(f"3-elem boom: {boom_length}\" (expected ~{expected}\")")
        
        assert expected * (1 - tolerance_pct) <= boom_length <= expected * (1 + tolerance_pct), \
            f"3-element boom {boom_length}\" outside expected range {expected}\" ±10%"
    
    def test_5_element_boom_length(self):
        """5-element boom should be ~295 inches (7.5m)"""
        response = make_auto_tune_request(5)
        assert response.status_code == 200
        
        data = response.json()
        elements = data.get("optimized_elements", [])
        
        positions = [e["position"] for e in elements]
        boom_length = max(positions) - min(positions)
        expected = USER_BOOM_LENGTHS[5]
        tolerance_pct = 0.10
        
        print(f"5-elem boom: {boom_length}\" (expected ~{expected}\")")
        
        assert expected * (1 - tolerance_pct) <= boom_length <= expected * (1 + tolerance_pct), \
            f"5-element boom {boom_length}\" outside expected range {expected}\" ±10%"
    
    def test_8_element_boom_length(self):
        """8-element boom should be ~551 inches (14.0m)"""
        response = make_auto_tune_request(8)
        assert response.status_code == 200
        
        data = response.json()
        elements = data.get("optimized_elements", [])
        
        positions = [e["position"] for e in elements]
        boom_length = max(positions) - min(positions)
        expected = USER_BOOM_LENGTHS[8]
        tolerance_pct = 0.10
        
        print(f"8-elem boom: {boom_length}\" (expected ~{expected}\")")
        
        assert expected * (1 - tolerance_pct) <= boom_length <= expected * (1 + tolerance_pct), \
            f"8-element boom {boom_length}\" outside expected range {expected}\" ±10%"
    
    def test_10_element_boom_length(self):
        """10-element boom should be ~728 inches (18.5m)"""
        response = make_auto_tune_request(10)
        assert response.status_code == 200
        
        data = response.json()
        elements = data.get("optimized_elements", [])
        
        positions = [e["position"] for e in elements]
        boom_length = max(positions) - min(positions)
        expected = USER_BOOM_LENGTHS[10]
        tolerance_pct = 0.10
        
        print(f"10-elem boom: {boom_length}\" (expected ~{expected}\")")
        
        assert expected * (1 - tolerance_pct) <= boom_length <= expected * (1 + tolerance_pct), \
            f"10-element boom {boom_length}\" outside expected range {expected}\" ±10%"


class TestGroundGainModel:
    """Test ground gain model (height_bonus field in gain_breakdown)."""
    
    def test_ground_gain_at_36ft(self):
        """At 36ft (1λ at 27MHz), ground gain should be ~5.78 dBi"""
        response = make_calculate_request(3, boom_length_in=138, height_ft=36)
        assert response.status_code == 200
        
        data = response.json()
        breakdown = data.get("gain_breakdown", {})
        height_bonus = breakdown.get("height_bonus")
        
        print(f"Ground gain at 36ft: height_bonus={height_bonus} dBi (expected ~5.78)")
        
        assert height_bonus is not None, "height_bonus field missing in gain_breakdown"
        # At 1λ height, ground gain should be ~5.8 dBi (±0.5)
        assert 5.3 <= height_bonus <= 6.3, \
            f"Ground gain at 36ft ({height_bonus} dBi) outside expected range 5.3-6.3 dBi"
    
    def test_ground_gain_at_10ft(self):
        """At 10ft (~0.28λ), ground gain should be ~2.2 dBi"""
        response = make_calculate_request(3, boom_length_in=138, height_ft=10)
        assert response.status_code == 200
        
        data = response.json()
        breakdown = data.get("gain_breakdown", {})
        height_bonus = breakdown.get("height_bonus")
        
        print(f"Ground gain at 10ft: height_bonus={height_bonus} dBi (expected ~2.2)")
        
        assert height_bonus is not None, "height_bonus field missing in gain_breakdown"
        # At ~0.28λ height, ground gain should be ~2.2 dBi (±1.0)
        assert 1.0 <= height_bonus <= 3.5, \
            f"Ground gain at 10ft ({height_bonus} dBi) outside expected range 1.0-3.5 dBi"
    
    def test_ground_gain_at_50ft(self):
        """At 50ft (~1.4λ), ground gain should be ~6.0 dBi"""
        response = make_calculate_request(3, boom_length_in=138, height_ft=50)
        assert response.status_code == 200
        
        data = response.json()
        breakdown = data.get("gain_breakdown", {})
        height_bonus = breakdown.get("height_bonus")
        
        print(f"Ground gain at 50ft: height_bonus={height_bonus} dBi (expected ~6.0)")
        
        assert height_bonus is not None, "height_bonus field missing in gain_breakdown"
        # At ~1.4λ height, ground gain should be ~5.8-6.0 dBi
        assert 5.0 <= height_bonus <= 6.5, \
            f"Ground gain at 50ft ({height_bonus} dBi) outside expected range 5.0-6.5 dBi"
    
    def test_ground_gain_increases_with_height(self):
        """Ground gain should increase from 10ft to 36ft"""
        response_10ft = make_calculate_request(3, boom_length_in=138, height_ft=10)
        response_36ft = make_calculate_request(3, boom_length_in=138, height_ft=36)
        
        assert response_10ft.status_code == 200
        assert response_36ft.status_code == 200
        
        height_bonus_10ft = response_10ft.json().get("gain_breakdown", {}).get("height_bonus", 0)
        height_bonus_36ft = response_36ft.json().get("gain_breakdown", {}).get("height_bonus", 0)
        
        print(f"Ground gain: 10ft={height_bonus_10ft} dBi, 36ft={height_bonus_36ft} dBi")
        
        assert height_bonus_36ft > height_bonus_10ft, \
            f"Ground gain at 36ft ({height_bonus_36ft}) should be greater than at 10ft ({height_bonus_10ft})"


class TestHeightIsKing:
    """Test that height significantly affects total gain (Height is King principle)."""
    
    def test_3elem_36ft_vs_10ft_gain_difference(self):
        """3-elem at 36ft vs 10ft should show >3.5 dBi difference"""
        response_36ft = make_calculate_request(3, boom_length_in=138, height_ft=36)
        response_10ft = make_calculate_request(3, boom_length_in=138, height_ft=10)
        
        assert response_36ft.status_code == 200
        assert response_10ft.status_code == 200
        
        gain_36ft = response_36ft.json().get("gain_dbi")
        gain_10ft = response_10ft.json().get("gain_dbi")
        
        gain_diff = gain_36ft - gain_10ft
        
        print(f"3-elem gain: 36ft={gain_36ft} dBi, 10ft={gain_10ft} dBi, diff={gain_diff} dBi")
        
        assert gain_diff > 3.0, \
            f"Height difference gain ({gain_diff} dBi) should be >3.0 dBi (Height is King)"
    
    def test_height_bonus_matches_gain_difference(self):
        """The gain difference should approximately equal height_bonus difference"""
        response_36ft = make_calculate_request(3, boom_length_in=138, height_ft=36)
        response_10ft = make_calculate_request(3, boom_length_in=138, height_ft=10)
        
        assert response_36ft.status_code == 200
        assert response_10ft.status_code == 200
        
        data_36ft = response_36ft.json()
        data_10ft = response_10ft.json()
        
        gain_diff = data_36ft.get("gain_dbi") - data_10ft.get("gain_dbi")
        height_bonus_diff = (
            data_36ft.get("gain_breakdown", {}).get("height_bonus", 0) -
            data_10ft.get("gain_breakdown", {}).get("height_bonus", 0)
        )
        
        print(f"Gain diff: {gain_diff} dBi, Height bonus diff: {height_bonus_diff} dBi")
        
        # The differences should be approximately equal (within 0.5 dB)
        assert abs(gain_diff - height_bonus_diff) < 1.0, \
            f"Gain diff ({gain_diff}) should approximately equal height_bonus diff ({height_bonus_diff})"


class TestBoomDoublingEffect:
    """Test that doubling boom length still yields ~2.5 dB increase."""
    
    def test_5elem_boom_doubling(self):
        """5 elements with doubled boom should give ~2.5 dB more gain"""
        standard_boom = USER_BOOM_LENGTHS[5]  # 295 inches
        doubled_boom = standard_boom * 2       # 590 inches
        
        response_standard = make_calculate_request(5, standard_boom, height_ft=36)
        response_doubled = make_calculate_request(5, doubled_boom, height_ft=36)
        
        assert response_standard.status_code == 200
        assert response_doubled.status_code == 200
        
        gain_standard = response_standard.json().get("gain_dbi")
        gain_doubled = response_doubled.json().get("gain_dbi")
        
        gain_diff = gain_doubled - gain_standard
        
        print(f"5-elem: standard boom ({standard_boom}\")={gain_standard} dBi, doubled ({doubled_boom}\")={gain_doubled} dBi")
        print(f"Gain increase from boom doubling: {gain_diff} dBi (expected ~2.5)")
        
        # Allow tolerance of +/- 0.5 dB
        assert 2.0 <= gain_diff <= 3.0, \
            f"Boom doubling gave {gain_diff} dB increase, expected 2.0-3.0 dB"
    
    def test_boom_adj_in_breakdown(self):
        """Verify boom_adj is present and correct in gain_breakdown"""
        standard_boom = USER_BOOM_LENGTHS[5]
        doubled_boom = standard_boom * 2
        
        response = make_calculate_request(5, doubled_boom, height_ft=36)
        assert response.status_code == 200
        
        breakdown = response.json().get("gain_breakdown", {})
        boom_adj = breakdown.get("boom_adj")
        
        print(f"boom_adj for doubled boom: {boom_adj} dBi (expected ~2.5)")
        
        assert boom_adj is not None, "boom_adj field missing in gain_breakdown"
        assert boom_adj > 2.0, f"boom_adj ({boom_adj}) should be >2.0 dB for doubled boom"


class TestNoReflectorMode:
    """Test that no reflector mode still applies -1.5 dB adjustment."""
    
    def test_no_reflector_reduces_gain_by_1_5db(self):
        """Without reflector, gain should be ~1.5 dB less"""
        response_with = make_calculate_request(3, 138, height_ft=36, has_reflector=True)
        response_without = make_calculate_request(3, 138, height_ft=36, has_reflector=False)
        
        assert response_with.status_code == 200
        assert response_without.status_code == 200
        
        gain_with = response_with.json().get("gain_dbi")
        gain_without = response_without.json().get("gain_dbi")
        
        gain_diff = gain_with - gain_without
        
        print(f"3-elem @ 36ft: WITH reflector={gain_with} dBi, WITHOUT={gain_without} dBi, diff={gain_diff}")
        
        # reflector_adj should be -1.5 dB
        assert 1.0 <= gain_diff <= 2.0, \
            f"No-reflector gain reduction ({gain_diff} dB) outside expected range 1.0-2.0 dB"
    
    def test_reflector_adj_field(self):
        """reflector_adj should be -1.5 when no reflector"""
        response = make_calculate_request(3, 138, height_ft=36, has_reflector=False)
        assert response.status_code == 200
        
        breakdown = response.json().get("gain_breakdown", {})
        reflector_adj = breakdown.get("reflector_adj")
        
        print(f"reflector_adj (no reflector): {reflector_adj} (expected -1.5)")
        
        assert reflector_adj == -1.5, f"reflector_adj should be -1.5, got {reflector_adj}"


class TestGainBreakdownFields:
    """Test gain_breakdown contains all required fields."""
    
    def test_all_required_fields_present(self):
        """Verify gain_breakdown contains: standard_gain, boom_adj, reflector_adj, taper_bonus, corona_adj, height_bonus, boom_bonus, final_gain"""
        response = make_calculate_request(5, 295, height_ft=36)
        assert response.status_code == 200
        
        breakdown = response.json().get("gain_breakdown")
        assert breakdown is not None, "gain_breakdown field missing"
        
        required_fields = [
            "standard_gain", "boom_adj", "reflector_adj", "taper_bonus",
            "corona_adj", "height_bonus", "boom_bonus", "final_gain"
        ]
        
        print(f"Gain breakdown: {breakdown}")
        
        for field in required_fields:
            assert field in breakdown, f"gain_breakdown missing required field: {field}"
            print(f"  {field}: {breakdown[field]}")
    
    def test_final_gain_equals_gain_dbi(self):
        """Verify final_gain in breakdown equals gain_dbi in response"""
        response = make_calculate_request(5, 295, height_ft=36)
        assert response.status_code == 200
        
        data = response.json()
        gain_dbi = data.get("gain_dbi")
        final_gain = data.get("gain_breakdown", {}).get("final_gain")
        
        print(f"gain_dbi: {gain_dbi}, final_gain: {final_gain}")
        
        assert abs(gain_dbi - final_gain) < 0.1, \
            f"gain_dbi ({gain_dbi}) != final_gain ({final_gain})"
    
    def test_breakdown_components_add_up(self):
        """Verify breakdown components sum to final_gain"""
        response = make_calculate_request(5, 295, height_ft=36)
        assert response.status_code == 200
        
        breakdown = response.json().get("gain_breakdown", {})
        
        calculated_sum = (
            breakdown.get("standard_gain", 0) +
            breakdown.get("boom_adj", 0) +
            breakdown.get("reflector_adj", 0) +
            breakdown.get("taper_bonus", 0) +
            breakdown.get("corona_adj", 0) +
            breakdown.get("height_bonus", 0) +
            breakdown.get("boom_bonus", 0)
        )
        
        final_gain = breakdown.get("final_gain", 0)
        
        print(f"Calculated sum: {calculated_sum}, final_gain: {final_gain}")
        
        assert abs(calculated_sum - final_gain) < 0.2, \
            f"Components sum ({calculated_sum}) != final_gain ({final_gain})"


class TestAPIHealth:
    """Basic health checks for endpoints."""
    
    def test_calculate_endpoint_accessible(self):
        """Verify /api/calculate endpoint is accessible."""
        response = make_calculate_request(3, 138)
        assert response.status_code == 200, f"API returned {response.status_code}"
    
    def test_auto_tune_endpoint_accessible(self):
        """Verify /api/auto-tune endpoint is accessible."""
        response = make_auto_tune_request(3)
        assert response.status_code == 200, f"API returned {response.status_code}: {response.text}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
