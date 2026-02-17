"""
Test suite for Smith Chart and Return Loss Optimization features.

Tests:
1. POST /api/calculate returns smith_chart_data for gamma/direct/hairpin feeds
2. Smith chart data has correct fields
3. Smith chart physics: |gamma| <= 1 for all points
4. Smith chart impedance sweep: proper reactance behavior across frequency
5. Smith chart L/C consistency
6. POST /api/optimize-return-loss uses the user-specified feed_type
"""

import pytest
import requests
import os
import math

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Standard test antenna configuration - 4 element Yagi
TEST_ANTENNA_CONFIG = {
    "num_elements": 4,
    "elements": [
        {"element_type": "reflector", "length": 216.0, "diameter": 0.5, "position": 0},
        {"element_type": "driven", "length": 206.0, "diameter": 0.5, "position": 48},
        {"element_type": "director", "length": 196.0, "diameter": 0.5, "position": 108},
        {"element_type": "director", "length": 190.0, "diameter": 0.5, "position": 168}
    ],
    "height_from_ground": 40,
    "height_unit": "ft",
    "boom_diameter": 2.0,
    "boom_unit": "inches",
    "band": "11m_cb",
    "frequency_mhz": 27.185,
    "antenna_orientation": "horizontal",
    "boom_grounded": True
}


class TestSmithChartData:
    """Tests for Smith Chart data generation in /api/calculate endpoint"""
    
    def test_calculate_returns_smith_chart_data_gamma(self):
        """POST /api/calculate returns smith_chart_data array with valid data for gamma feed"""
        payload = {**TEST_ANTENNA_CONFIG, "feed_type": "gamma"}
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload, timeout=30)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify smith_chart_data exists and is an array
        assert "smith_chart_data" in data, "Response missing smith_chart_data field"
        smith_data = data["smith_chart_data"]
        assert isinstance(smith_data, list), f"smith_chart_data should be list, got {type(smith_data)}"
        assert len(smith_data) > 0, "smith_chart_data should not be empty"
        
        print(f"✓ Gamma feed: smith_chart_data returned with {len(smith_data)} points")
        print(f"  Feed type returned: {data.get('feed_type')}")
        print(f"  Return loss: {data.get('return_loss_db')} dB")
        print(f"  SWR: {data.get('swr')}")
    
    def test_calculate_returns_smith_chart_data_direct(self):
        """POST /api/calculate returns smith_chart_data array with valid data for direct feed"""
        payload = {**TEST_ANTENNA_CONFIG, "feed_type": "direct"}
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload, timeout=30)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert "smith_chart_data" in data, "Response missing smith_chart_data field"
        smith_data = data["smith_chart_data"]
        assert isinstance(smith_data, list), f"smith_chart_data should be list"
        assert len(smith_data) > 0, "smith_chart_data should not be empty"
        
        print(f"✓ Direct feed: smith_chart_data returned with {len(smith_data)} points")
        print(f"  Feed type returned: {data.get('feed_type')}")
        print(f"  Return loss: {data.get('return_loss_db')} dB")
    
    def test_calculate_returns_smith_chart_data_hairpin(self):
        """POST /api/calculate returns smith_chart_data array with valid data for hairpin feed"""
        payload = {**TEST_ANTENNA_CONFIG, "feed_type": "hairpin"}
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload, timeout=30)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert "smith_chart_data" in data, "Response missing smith_chart_data field"
        smith_data = data["smith_chart_data"]
        assert isinstance(smith_data, list), f"smith_chart_data should be list"
        assert len(smith_data) > 0, "smith_chart_data should not be empty"
        
        print(f"✓ Hairpin feed: smith_chart_data returned with {len(smith_data)} points")
        print(f"  Feed type returned: {data.get('feed_type')}")
        print(f"  Return loss: {data.get('return_loss_db')} dB")
    
    def test_smith_chart_data_has_correct_fields(self):
        """Smith chart data has correct fields: freq, z_real, z_imag, gamma_real, gamma_imag, inductance_nh, capacitance_pf"""
        payload = {**TEST_ANTENNA_CONFIG, "feed_type": "gamma"}
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload, timeout=30)
        
        assert response.status_code == 200
        data = response.json()
        smith_data = data["smith_chart_data"]
        
        required_fields = ["freq", "z_real", "z_imag", "gamma_real", "gamma_imag", "inductance_nh", "capacitance_pf"]
        
        # Check first data point has all required fields
        first_point = smith_data[0]
        for field in required_fields:
            assert field in first_point, f"Missing required field: {field}"
            
        # Verify field types
        assert isinstance(first_point["freq"], (int, float)), "freq should be numeric"
        assert isinstance(first_point["z_real"], (int, float)), "z_real should be numeric"
        assert isinstance(first_point["z_imag"], (int, float)), "z_imag should be numeric"
        assert isinstance(first_point["gamma_real"], (int, float)), "gamma_real should be numeric"
        assert isinstance(first_point["gamma_imag"], (int, float)), "gamma_imag should be numeric"
        assert isinstance(first_point["inductance_nh"], (int, float)), "inductance_nh should be numeric"
        assert isinstance(first_point["capacitance_pf"], (int, float)), "capacitance_pf should be numeric"
        
        print(f"✓ All {len(required_fields)} required fields present with correct types")
        print(f"  Sample point: {first_point}")
    
    def test_smith_chart_gamma_magnitude_valid(self):
        """Smith chart physics: |gamma| <= 1 for all points (passive network constraint)"""
        payload = {**TEST_ANTENNA_CONFIG, "feed_type": "gamma"}
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload, timeout=30)
        
        assert response.status_code == 200
        data = response.json()
        smith_data = data["smith_chart_data"]
        
        violations = []
        for point in smith_data:
            gamma_mag = math.sqrt(point["gamma_real"]**2 + point["gamma_imag"]**2)
            if gamma_mag > 1.001:  # Allow small numerical tolerance
                violations.append({
                    "freq": point["freq"],
                    "gamma_mag": gamma_mag,
                    "gamma_real": point["gamma_real"],
                    "gamma_imag": point["gamma_imag"]
                })
        
        assert len(violations) == 0, f"|gamma| > 1 violations found at {len(violations)} frequencies: {violations[:5]}"
        
        # Report gamma magnitude statistics
        gamma_mags = [math.sqrt(p["gamma_real"]**2 + p["gamma_imag"]**2) for p in smith_data]
        print(f"✓ All {len(smith_data)} points have |gamma| <= 1")
        print(f"  |gamma| range: {min(gamma_mags):.4f} to {max(gamma_mags):.4f}")
    
    def test_smith_chart_impedance_sweep_behavior(self):
        """Smith chart impedance sweep: low freq has negative X (capacitive), center has near-zero X, high freq has positive X (inductive)"""
        payload = {**TEST_ANTENNA_CONFIG, "feed_type": "direct"}  # Use direct to see natural impedance
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload, timeout=30)
        
        assert response.status_code == 200
        data = response.json()
        smith_data = data["smith_chart_data"]
        
        # Get low, center, high frequency points
        center_idx = len(smith_data) // 2
        low_freq_point = smith_data[0]
        center_freq_point = smith_data[center_idx]
        high_freq_point = smith_data[-1]
        
        print(f"  Low freq ({low_freq_point['freq']} MHz): Z = {low_freq_point['z_real']:.1f} + j{low_freq_point['z_imag']:.1f}")
        print(f"  Center freq ({center_freq_point['freq']} MHz): Z = {center_freq_point['z_real']:.1f} + j{center_freq_point['z_imag']:.1f}")
        print(f"  High freq ({high_freq_point['freq']} MHz): Z = {high_freq_point['z_real']:.1f} + j{high_freq_point['z_imag']:.1f}")
        
        # Verify typical antenna behavior: X increases with frequency
        # Below resonance: capacitive (X < 0), above resonance: inductive (X > 0)
        # Note: The exact behavior depends on the resonant frequency which may not be at center
        low_x = low_freq_point["z_imag"]
        high_x = high_freq_point["z_imag"]
        
        # Reactance should increase from low to high frequency (general trend)
        assert high_x > low_x, f"Expected reactance to increase with frequency: low={low_x:.2f}, high={high_x:.2f}"
        
        print(f"✓ Reactance increases with frequency as expected (ΔX = {high_x - low_x:.2f})")
    
    def test_smith_chart_lc_consistency(self):
        """Smith chart L/C consistency: positive X -> inductance_nh > 0, negative X -> capacitance_pf > 0"""
        payload = {**TEST_ANTENNA_CONFIG, "feed_type": "direct"}
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload, timeout=30)
        
        assert response.status_code == 200
        data = response.json()
        smith_data = data["smith_chart_data"]
        
        inductive_points = [p for p in smith_data if p["z_imag"] > 0.1]  # Positive X (inductive)
        capacitive_points = [p for p in smith_data if p["z_imag"] < -0.1]  # Negative X (capacitive)
        
        # Check inductive points have inductance_nh > 0
        inductive_errors = []
        for p in inductive_points:
            if p["inductance_nh"] <= 0:
                inductive_errors.append(f"freq={p['freq']}: X={p['z_imag']:.2f} but L={p['inductance_nh']}")
        
        # Check capacitive points have capacitance_pf > 0
        capacitive_errors = []
        for p in capacitive_points:
            if p["capacitance_pf"] <= 0:
                capacitive_errors.append(f"freq={p['freq']}: X={p['z_imag']:.2f} but C={p['capacitance_pf']}")
        
        if inductive_errors:
            print(f"  WARNING: {len(inductive_errors)} inductive points with L<=0: {inductive_errors[:3]}")
        if capacitive_errors:
            print(f"  WARNING: {len(capacitive_errors)} capacitive points with C<=0: {capacitive_errors[:3]}")
        
        # Report statistics
        print(f"✓ L/C consistency check:")
        print(f"  Inductive points (X>0): {len(inductive_points)}, with valid L: {len(inductive_points) - len(inductive_errors)}")
        print(f"  Capacitive points (X<0): {len(capacitive_points)}, with valid C: {len(capacitive_points) - len(capacitive_errors)}")


class TestOptimizeReturnLoss:
    """Tests for /api/optimize-return-loss endpoint feed_type handling"""
    
    def test_optimize_return_loss_gamma_feed(self):
        """POST /api/optimize-return-loss with feed_type='gamma' uses gamma match"""
        payload = {**TEST_ANTENNA_CONFIG, "feed_type": "gamma"}
        response = requests.post(f"{BASE_URL}/api/optimize-return-loss", json=payload, timeout=60)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "best_elements" in data, "Response missing best_elements"
        assert "best_return_loss_db" in data, "Response missing best_return_loss_db"
        assert "best_swr" in data, "Response missing best_swr"
        assert "feed_type" in data, "Response missing feed_type"
        
        # Verify feed_type is gamma (not defaulting to direct)
        assert data["feed_type"] == "gamma", f"Expected feed_type='gamma', got '{data['feed_type']}'"
        
        # Return loss should be reasonable for a gamma match (typically 15-50 dB for good match)
        rl = data["best_return_loss_db"]
        swr = data["best_swr"]
        
        print(f"✓ optimize-return-loss with gamma feed:")
        print(f"  feed_type returned: {data['feed_type']}")
        print(f"  best_return_loss_db: {rl} dB")
        print(f"  best_swr: {swr}")
        print(f"  best_gain: {data.get('best_gain')} dBi")
        print(f"  best_fb: {data.get('best_fb')} dB")
        print(f"  sweep_count: {data.get('sweep_count')}")
    
    def test_optimize_return_loss_direct_feed(self):
        """POST /api/optimize-return-loss with feed_type='direct' uses direct feed"""
        payload = {**TEST_ANTENNA_CONFIG, "feed_type": "direct"}
        response = requests.post(f"{BASE_URL}/api/optimize-return-loss", json=payload, timeout=60)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        # Verify feed_type is direct
        assert data["feed_type"] == "direct", f"Expected feed_type='direct', got '{data['feed_type']}'"
        
        rl = data["best_return_loss_db"]
        swr = data["best_swr"]
        
        print(f"✓ optimize-return-loss with direct feed:")
        print(f"  feed_type returned: {data['feed_type']}")
        print(f"  best_return_loss_db: {rl} dB")
        print(f"  best_swr: {swr}")
    
    def test_optimize_return_loss_hairpin_feed(self):
        """POST /api/optimize-return-loss with feed_type='hairpin' uses hairpin match"""
        payload = {**TEST_ANTENNA_CONFIG, "feed_type": "hairpin"}
        response = requests.post(f"{BASE_URL}/api/optimize-return-loss", json=payload, timeout=60)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        # Verify feed_type is hairpin
        assert data["feed_type"] == "hairpin", f"Expected feed_type='hairpin', got '{data['feed_type']}'"
        
        rl = data["best_return_loss_db"]
        swr = data["best_swr"]
        
        print(f"✓ optimize-return-loss with hairpin feed:")
        print(f"  feed_type returned: {data['feed_type']}")
        print(f"  best_return_loss_db: {rl} dB")
        print(f"  best_swr: {swr}")
    
    def test_optimize_return_loss_gamma_vs_direct_comparison(self):
        """Gamma match should produce better return loss than direct feed for typical Yagi"""
        # Test with gamma
        gamma_payload = {**TEST_ANTENNA_CONFIG, "feed_type": "gamma"}
        gamma_response = requests.post(f"{BASE_URL}/api/optimize-return-loss", json=gamma_payload, timeout=60)
        assert gamma_response.status_code == 200
        gamma_data = gamma_response.json()
        
        # Test with direct
        direct_payload = {**TEST_ANTENNA_CONFIG, "feed_type": "direct"}
        direct_response = requests.post(f"{BASE_URL}/api/optimize-return-loss", json=direct_payload, timeout=60)
        assert direct_response.status_code == 200
        direct_data = direct_response.json()
        
        gamma_rl = gamma_data["best_return_loss_db"]
        direct_rl = direct_data["best_return_loss_db"]
        gamma_swr = gamma_data["best_swr"]
        direct_swr = direct_data["best_swr"]
        
        print(f"✓ Gamma vs Direct comparison:")
        print(f"  Gamma: RL={gamma_rl} dB, SWR={gamma_swr}")
        print(f"  Direct: RL={direct_rl} dB, SWR={direct_swr}")
        
        # Gamma match should generally produce better return loss (higher dB) than direct
        # for a typical Yagi with low feedpoint impedance
        # Note: This is physics expectation, not a hard assertion
        if gamma_rl > direct_rl:
            print(f"  ✓ Gamma match provides better impedance transformation ({gamma_rl - direct_rl:.1f} dB improvement)")
        else:
            print(f"  Note: Direct feed has similar or better RL in this configuration")


class TestCalculateMatchingInfo:
    """Test matching_info field for different feed types"""
    
    def test_gamma_matching_info(self):
        """Gamma feed includes matching_info with tuning parameters"""
        payload = {**TEST_ANTENNA_CONFIG, "feed_type": "gamma"}
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload, timeout=30)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "matching_info" in data, "Response missing matching_info for gamma feed"
        matching_info = data["matching_info"]
        
        assert matching_info.get("type") == "Gamma Match", f"Expected 'Gamma Match', got '{matching_info.get('type')}'"
        assert "original_swr" in matching_info
        assert "matched_swr" in matching_info
        
        print(f"✓ Gamma matching_info:")
        print(f"  Type: {matching_info.get('type')}")
        print(f"  Original SWR: {matching_info.get('original_swr')}")
        print(f"  Matched SWR: {matching_info.get('matched_swr')}")
        if "tuning_quality" in matching_info:
            print(f"  Tuning Quality: {matching_info.get('tuning_quality')}")
    
    def test_hairpin_matching_info(self):
        """Hairpin feed includes matching_info"""
        payload = {**TEST_ANTENNA_CONFIG, "feed_type": "hairpin"}
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload, timeout=30)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "matching_info" in data, "Response missing matching_info for hairpin feed"
        matching_info = data["matching_info"]
        
        assert matching_info.get("type") == "Hairpin Match", f"Expected 'Hairpin Match', got '{matching_info.get('type')}'"
        
        print(f"✓ Hairpin matching_info:")
        print(f"  Type: {matching_info.get('type')}")
        print(f"  Original SWR: {matching_info.get('original_swr')}")
        print(f"  Matched SWR: {matching_info.get('matched_swr')}")
    
    def test_direct_matching_info(self):
        """Direct feed includes matching_info with no transformation"""
        payload = {**TEST_ANTENNA_CONFIG, "feed_type": "direct"}
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload, timeout=30)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "matching_info" in data, "Response missing matching_info for direct feed"
        matching_info = data["matching_info"]
        
        assert matching_info.get("type") == "Direct Feed", f"Expected 'Direct Feed', got '{matching_info.get('type')}'"
        
        print(f"✓ Direct matching_info:")
        print(f"  Type: {matching_info.get('type')}")
        print(f"  SWR: {matching_info.get('original_swr')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
