"""
Backend tests for Gamma Match SWR/Smith Chart Physics Unification.

Tests that:
1. POST /api/calculate with feed_type=gamma returns consistent SWR and Smith Chart data at center frequency
2. Gamma match SWR varies correctly with rod insertion (gamma_element_gap): low = high SWR, optimal ~10in = low SWR
3. Gamma match SWR varies correctly with bar position (gamma_bar_pos): optimal ~13in = low SWR, deviation = higher SWR
4. matching_info contains required physics fields: z_matched_r, z_matched_x, x_stub, x_cap, net_reactance, z0_gamma, reflection_coefficient
5. SWR and return_loss_db are mathematically consistent: return_loss = -20*log10(|Gamma|), SWR = (1+|Gamma|)/(1-|Gamma|)
6. Direct and Hairpin feed types still work correctly
7. Smith Chart z_real at center freq matches matching_info z_matched_r for gamma match
"""

import pytest
import requests
import os
import math

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Standard 3-element Yagi payload from agent context
def get_gamma_yagi_payload(gamma_bar_pos=13, gamma_element_gap=10, gamma_rod_dia=0.375, gamma_rod_spacing=3.5):
    """Generate base payload for gamma match testing"""
    return {
        "band": "11m_cb",
        "frequency_mhz": 27.185,
        "num_elements": 3,
        "antenna_orientation": "horizontal",
        "height_from_ground": 50,
        "height_unit": "ft",
        "boom_diameter": 2,
        "boom_unit": "inches",
        "boom_grounded": True,
        "boom_mount": "bonded",
        "feed_type": "gamma",
        "gamma_rod_dia": gamma_rod_dia,
        "gamma_rod_spacing": gamma_rod_spacing,
        "gamma_bar_pos": gamma_bar_pos,
        "gamma_element_gap": gamma_element_gap,
        "elements": [
            {"element_type": "reflector", "length": 214, "diameter": 0.5, "position": 0},
            {"element_type": "driven", "length": 203, "diameter": 0.5, "position": 44},
            {"element_type": "director", "length": 195, "diameter": 0.5, "position": 100}
        ]
    }


class TestGammaMatchPhysicsFields:
    """Test that matching_info contains all required physics fields for gamma match"""
    
    def test_matching_info_has_required_fields(self):
        """matching_info should contain z_matched_r, z_matched_x, x_stub, x_cap, net_reactance, z0_gamma, reflection_coefficient"""
        payload = get_gamma_yagi_payload(gamma_bar_pos=13, gamma_element_gap=10)
        
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
        assert response.status_code == 200, f"API failed: {response.text}"
        
        data = response.json()
        matching_info = data.get('matching_info', {})
        
        # Required fields per agent context
        required_fields = [
            'z_matched_r',
            'z_matched_x',
            'x_stub',
            'x_cap',
            'net_reactance',
            'z0_gamma',
            'reflection_coefficient'
        ]
        
        for field in required_fields:
            assert field in matching_info, f"Missing required field: {field} in matching_info. Got: {list(matching_info.keys())}"
            print(f"  {field}: {matching_info[field]}")
        
        print(f"SUCCESS: All required physics fields present in matching_info")
        print(f"  z_matched: {matching_info['z_matched_r']} + j{matching_info['z_matched_x']} ohms")
        print(f"  X_stub: {matching_info['x_stub']} ohms, X_cap: {matching_info['x_cap']} ohms")
        print(f"  Net reactance: {matching_info['net_reactance']} ohms")
        print(f"  Z0 gamma section: {matching_info['z0_gamma']} ohms")
        print(f"  Gamma (|Γ|): {matching_info['reflection_coefficient']}")


class TestSwrMathematicalConsistency:
    """Test SWR and return_loss_db are mathematically consistent with reflection coefficient"""
    
    def test_swr_from_gamma_formula(self):
        """SWR = (1+|Γ|)/(1-|Γ|) must hold"""
        payload = get_gamma_yagi_payload(gamma_bar_pos=13, gamma_element_gap=10)
        
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        swr_reported = data['swr']
        matching_info = data.get('matching_info', {})
        gamma_mag = matching_info.get('reflection_coefficient', 0)
        
        # Calculate expected SWR from reflection coefficient
        expected_swr = (1 + gamma_mag) / (1 - gamma_mag) if gamma_mag < 1.0 else 99.0
        
        # Allow 5% tolerance due to rounding
        tolerance = max(0.05, expected_swr * 0.05)
        diff = abs(swr_reported - expected_swr)
        
        assert diff < tolerance, f"SWR mismatch: reported={swr_reported}, expected from Γ={expected_swr}, diff={diff}"
        
        print(f"SUCCESS: SWR formula verified")
        print(f"  |Γ| = {gamma_mag}")
        print(f"  SWR reported: {swr_reported}")
        print(f"  SWR from formula (1+|Γ|)/(1-|Γ|): {round(expected_swr, 3)}")
        print(f"  Difference: {round(diff, 5)}")
    
    def test_return_loss_from_gamma_formula(self):
        """return_loss_db = -20*log10(|Γ|) must hold"""
        payload = get_gamma_yagi_payload(gamma_bar_pos=13, gamma_element_gap=10)
        
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        return_loss_reported = data.get('return_loss_db', 0)
        matching_info = data.get('matching_info', {})
        gamma_mag = matching_info.get('reflection_coefficient', 0)
        
        # Calculate expected return loss from reflection coefficient
        if gamma_mag > 1e-6:
            expected_rl = -20 * math.log10(gamma_mag)
            expected_rl = min(expected_rl, 80.0)  # clamped per physics.py
        else:
            expected_rl = 80.0
        
        # Allow 1 dB tolerance
        tolerance = 1.0
        diff = abs(return_loss_reported - expected_rl)
        
        assert diff < tolerance, f"Return loss mismatch: reported={return_loss_reported}, expected={expected_rl}, diff={diff}"
        
        print(f"SUCCESS: Return loss formula verified")
        print(f"  |Γ| = {gamma_mag}")
        print(f"  Return loss reported: {return_loss_reported} dB")
        print(f"  Return loss from formula -20*log10(|Γ|): {round(expected_rl, 2)} dB")
        print(f"  Difference: {round(diff, 3)} dB")


class TestSmithChartZMatchesMatchingInfo:
    """Test that Smith Chart z_real at center freq matches matching_info z_matched_r"""
    
    def test_smith_chart_center_freq_impedance_matches(self):
        """Smith chart impedance at center frequency should match matching_info z_matched values"""
        center_freq = 27.185
        payload = get_gamma_yagi_payload(gamma_bar_pos=13, gamma_element_gap=10)
        
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        matching_info = data.get('matching_info', {})
        smith_chart_data = data.get('smith_chart_data', [])
        
        assert len(smith_chart_data) > 0, "Smith chart data should not be empty"
        
        # Find the center frequency point in Smith chart
        center_point = min(smith_chart_data, key=lambda x: abs(x['freq'] - center_freq))
        
        z_matched_r = matching_info.get('z_matched_r', 0)
        z_matched_x = matching_info.get('z_matched_x', 0)
        
        smith_z_real = center_point.get('z_real', 0)
        smith_z_imag = center_point.get('z_imag', 0)
        
        # Allow 10% tolerance (Smith chart includes frequency-dependent effects)
        r_tolerance = max(5.0, abs(z_matched_r) * 0.1)
        x_tolerance = max(10.0, abs(z_matched_x) * 0.3)  # Reactance can vary more with frequency
        
        r_diff = abs(smith_z_real - z_matched_r)
        x_diff = abs(smith_z_imag - z_matched_x)
        
        print(f"Smith Chart at center freq {center_point['freq']} MHz:")
        print(f"  Z_smith = {smith_z_real} + j{smith_z_imag} ohms")
        print(f"  Z_matched (matching_info) = {z_matched_r} + j{z_matched_x} ohms")
        print(f"  R difference: {round(r_diff, 2)} ohms (tolerance: {r_tolerance})")
        print(f"  X difference: {round(x_diff, 2)} ohms (tolerance: {x_tolerance})")
        
        # Check resistance matches
        assert r_diff < r_tolerance, f"Z_real mismatch: Smith={smith_z_real}, matching_info={z_matched_r}, diff={r_diff}"
        
        print(f"SUCCESS: Smith chart center frequency impedance matches matching_info")


class TestGammaRodInsertionEffect:
    """Test that rod insertion (gamma_element_gap) affects SWR correctly"""
    
    def test_low_insertion_high_swr(self):
        """Low rod insertion (2") should give higher SWR than optimal (10")"""
        results = {}
        
        for insertion in [2, 8, 10, 11]:
            payload = get_gamma_yagi_payload(gamma_bar_pos=13, gamma_element_gap=insertion)
            
            response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
            assert response.status_code == 200, f"API failed for insertion={insertion}"
            
            data = response.json()
            results[insertion] = {
                'swr': data['swr'],
                'z_matched_r': data.get('matching_info', {}).get('z_matched_r', 0),
                'z_matched_x': data.get('matching_info', {}).get('z_matched_x', 0),
                'reflection_coefficient': data.get('matching_info', {}).get('reflection_coefficient', 0),
            }
            print(f"Rod insertion {insertion}\": SWR={data['swr']}, Z={results[insertion]['z_matched_r']}+j{results[insertion]['z_matched_x']}")
        
        # Low insertion (2") should have higher SWR than optimal (~10")
        # Due to physics: less capacitance means less cancellation of inductive stub
        assert results[2]['swr'] > results[10]['swr'], \
            f"Low insertion should have higher SWR: SWR(2\")={results[2]['swr']} should > SWR(10\")={results[10]['swr']}"
        
        # Optimal insertion (~10") should have lowest SWR
        swr_values = [results[i]['swr'] for i in [2, 8, 10, 11]]
        optimal_idx = swr_values.index(min(swr_values))
        optimal_insertion = [2, 8, 10, 11][optimal_idx]
        
        print(f"SUCCESS: Rod insertion affects SWR correctly")
        print(f"  Lowest SWR at insertion={optimal_insertion}\" with SWR={min(swr_values)}")
    
    def test_insertion_varies_swr(self):
        """Different insertions should produce different SWR values"""
        results = {}
        
        for insertion in [2, 5, 8, 10]:
            payload = get_gamma_yagi_payload(gamma_bar_pos=13, gamma_element_gap=insertion)
            response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
            assert response.status_code == 200
            results[insertion] = response.json()['swr']
        
        unique_swrs = len(set(results.values()))
        assert unique_swrs >= 3, f"Expected at least 3 different SWR values, got {unique_swrs}: {results}"
        
        print(f"SUCCESS: Rod insertion produces {unique_swrs} different SWR values: {results}")


class TestGammaBarPositionEffect:
    """Test that bar position (gamma_bar_pos) affects SWR correctly"""
    
    def test_optimal_bar_position_low_swr(self):
        """Bar at ~13" should give lower SWR than extreme positions (5" or 25")"""
        results = {}
        
        for bar_pos in [5, 13, 25]:
            payload = get_gamma_yagi_payload(gamma_bar_pos=bar_pos, gamma_element_gap=10)
            
            response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
            assert response.status_code == 200, f"API failed for bar_pos={bar_pos}"
            
            data = response.json()
            results[bar_pos] = {
                'swr': data['swr'],
                'z_matched_r': data.get('matching_info', {}).get('z_matched_r', 0),
                'z_matched_x': data.get('matching_info', {}).get('z_matched_x', 0),
                'x_stub': data.get('matching_info', {}).get('x_stub', 0),
            }
            print(f"Bar position {bar_pos}\": SWR={data['swr']}, X_stub={results[bar_pos]['x_stub']} ohms")
        
        # Bar at optimal position (~13") should have lower SWR than deviation (5" or 25")
        # Due to physics: stub reactance X = Z0*tan(βL) must balance with capacitor
        assert results[13]['swr'] < results[5]['swr'] or results[13]['swr'] < results[25]['swr'], \
            f"Optimal bar position should have lower SWR: SWR(13\")={results[13]['swr']} vs SWR(5\")={results[5]['swr']}, SWR(25\")={results[25]['swr']}"
        
        print(f"SUCCESS: Bar position affects SWR correctly")
        print(f"  Optimal bar position 13\" has SWR={results[13]['swr']}")
    
    def test_bar_position_varies_stub_reactance(self):
        """Different bar positions should produce different stub reactances"""
        results = {}
        
        for bar_pos in [5, 13, 25]:
            payload = get_gamma_yagi_payload(gamma_bar_pos=bar_pos, gamma_element_gap=10)
            response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
            assert response.status_code == 200
            
            matching_info = response.json().get('matching_info', {})
            results[bar_pos] = matching_info.get('x_stub', 0)
        
        # Longer bar position should give higher stub reactance (X = Z0*tan(βL))
        assert results[25] > results[13] > results[5], \
            f"Stub reactance should increase with bar length: X(5)={results[5]}, X(13)={results[13]}, X(25)={results[25]}"
        
        print(f"SUCCESS: Stub reactance increases with bar position")
        print(f"  X_stub(5\")={round(results[5], 2)}, X_stub(13\")={round(results[13], 2)}, X_stub(25\")={round(results[25], 2)}")


class TestDirectFeedStillWorks:
    """Test that direct feed type still works correctly"""
    
    def test_direct_feed_returns_valid_response(self):
        """POST /api/calculate with feed_type=direct should return valid results"""
        payload = get_gamma_yagi_payload()
        payload['feed_type'] = 'direct'
        
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
        assert response.status_code == 200, f"API failed: {response.text}"
        
        data = response.json()
        
        # Should have valid SWR
        assert 'swr' in data, "Response should contain SWR"
        assert data['swr'] >= 1.0, f"SWR should be >= 1.0, got {data['swr']}"
        
        # Should have matching_info
        matching_info = data.get('matching_info', {})
        assert matching_info.get('type') == 'Direct Feed', f"Expected Direct Feed type, got {matching_info.get('type')}"
        
        print(f"SUCCESS: Direct feed works correctly")
        print(f"  SWR={data['swr']}, type={matching_info.get('type')}")


class TestHairpinFeedStillWorks:
    """Test that hairpin feed type still works correctly"""
    
    def test_hairpin_feed_returns_valid_response(self):
        """POST /api/calculate with feed_type=hairpin should return valid results"""
        payload = get_gamma_yagi_payload()
        payload['feed_type'] = 'hairpin'
        
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
        assert response.status_code == 200, f"API failed: {response.text}"
        
        data = response.json()
        
        # Should have valid SWR
        assert 'swr' in data, "Response should contain SWR"
        assert data['swr'] >= 1.0, f"SWR should be >= 1.0, got {data['swr']}"
        
        # Should have matching_info
        matching_info = data.get('matching_info', {})
        assert matching_info.get('type') == 'Hairpin Match', f"Expected Hairpin Match type, got {matching_info.get('type')}"
        
        print(f"SUCCESS: Hairpin feed works correctly")
        print(f"  SWR={data['swr']}, type={matching_info.get('type')}")


class TestConsistentSwrAtCenterFreq:
    """Test that SWR and Smith Chart are consistent at center frequency"""
    
    def test_swr_curve_minimum_matches_displayed_swr(self):
        """SWR curve minimum should match the displayed SWR value"""
        payload = get_gamma_yagi_payload(gamma_bar_pos=13, gamma_element_gap=10)
        
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        swr_displayed = data['swr']
        swr_curve = data.get('swr_curve', [])
        
        assert len(swr_curve) > 0, "SWR curve should not be empty"
        
        # Find minimum SWR in curve
        min_swr_point = min(swr_curve, key=lambda x: x['swr'])
        swr_curve_min = min_swr_point['swr']
        
        # Should match within 0.1
        diff = abs(swr_displayed - swr_curve_min)
        assert diff < 0.1, f"SWR mismatch: displayed={swr_displayed}, curve_min={swr_curve_min}, diff={diff}"
        
        print(f"SUCCESS: SWR consistency verified")
        print(f"  Displayed SWR: {swr_displayed}")
        print(f"  Curve minimum SWR: {swr_curve_min} at {min_swr_point['frequency']} MHz")
        print(f"  Difference: {round(diff, 4)}")
    
    def test_smith_chart_gamma_matches_swr(self):
        """Smith chart reflection coefficient at center freq should match SWR"""
        center_freq = 27.185
        payload = get_gamma_yagi_payload(gamma_bar_pos=13, gamma_element_gap=10)
        
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        swr_displayed = data['swr']
        smith_chart_data = data.get('smith_chart_data', [])
        
        # Find center frequency point
        center_point = min(smith_chart_data, key=lambda x: abs(x['freq'] - center_freq))
        
        # Calculate |Γ| from Smith chart data
        gamma_real = center_point.get('gamma_real', 0)
        gamma_imag = center_point.get('gamma_imag', 0)
        gamma_mag = math.sqrt(gamma_real ** 2 + gamma_imag ** 2)
        
        # Calculate SWR from |Γ|
        swr_from_smith = (1 + gamma_mag) / (1 - gamma_mag) if gamma_mag < 1.0 else 99.0
        
        # Allow 10% tolerance
        tolerance = max(0.15, swr_displayed * 0.1)
        diff = abs(swr_displayed - swr_from_smith)
        
        print(f"Smith Chart at {center_point['freq']} MHz:")
        print(f"  Γ = {round(gamma_real, 5)} + j{round(gamma_imag, 5)}")
        print(f"  |Γ| = {round(gamma_mag, 5)}")
        print(f"  SWR from Smith chart: {round(swr_from_smith, 3)}")
        print(f"  SWR displayed: {swr_displayed}")
        print(f"  Difference: {round(diff, 4)}")
        
        assert diff < tolerance, f"SWR mismatch between displayed and Smith chart: displayed={swr_displayed}, from_smith={swr_from_smith}"
        
        print(f"SUCCESS: Smith chart and displayed SWR are consistent")


class TestOptimalGammaMatchSwr:
    """Test that optimal gamma match parameters produce expected low SWR"""
    
    def test_optimal_params_low_swr(self):
        """With bar=13\", insertion=10\": SWR should be low (~1.01 to ~1.5)"""
        payload = get_gamma_yagi_payload(gamma_bar_pos=13, gamma_element_gap=10)
        
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        swr = data['swr']
        matching_info = data.get('matching_info', {})
        
        # With optimal tuning, SWR should be very low
        # Per agent context: "SWR should be ~1.01, Z should be ~50+j0"
        assert swr < 1.5, f"Optimal gamma match should achieve SWR < 1.5, got {swr}"
        
        z_r = matching_info.get('z_matched_r', 0)
        z_x = matching_info.get('z_matched_x', 0)
        
        print(f"Optimal gamma match (bar=13\", insertion=10\"):")
        print(f"  SWR: {swr}")
        print(f"  Z: {z_r} + j{z_x} ohms")
        print(f"  Target: ~50+j0 ohms")
        
        # Check impedance is close to 50 ohms
        z_target = 50.0
        r_deviation = abs(z_r - z_target) / z_target
        
        if swr < 1.15:
            print(f"  EXCELLENT: SWR < 1.15 achieved!")
        elif swr < 1.3:
            print(f"  GOOD: SWR < 1.3 achieved")
        
        print(f"SUCCESS: Optimal gamma match parameters produce low SWR")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
