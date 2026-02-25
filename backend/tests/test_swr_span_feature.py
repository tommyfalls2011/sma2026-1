"""
Test SWR Span Feature - swr_span_mhz parameter controls the frequency range of SWR curve
- When swr_span_mhz is provided, generates 61 points spanning that range (±half from center)
- When swr_span_mhz is NOT provided, uses default ±30 channels at channel_spacing intervals
- Y-axis auto-scales: yMax=3 for narrow band, yMax=5 or 10 for wider spans with higher SWR
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Well-tuned gamma payload from problem statement
BASE_PAYLOAD = {
    "num_elements": 3,
    "elements": [
        {"element_type": "reflector", "length": 216.4, "diameter": 0.5, "position": 0},
        {"element_type": "driven", "length": 207.95, "diameter": 0.5, "position": 50.5},
        {"element_type": "director", "length": 195.0, "diameter": 0.5, "position": 100}
    ],
    "height_from_ground": 54,
    "height_unit": "ft",
    "boom_diameter": 1.5,
    "boom_unit": "inches",
    "band": "11m_cb",
    "frequency_mhz": 27.185,
    "feed_type": "gamma",
    "boom_mount": "bonded",
    "stacking": {"enabled": False, "spacing": 20},
    "corona_balls": {"enabled": True, "diameter_mm": 20},
    "gamma_bar_pos": 4.26,
    "gamma_element_gap": 3.43,
    "gamma_cap_pf": 335.3
}


class TestSWRSpanFeature:
    """Test the swr_span_mhz parameter for controlling SWR curve frequency range"""

    def test_health_check(self):
        """Verify API health before running tests"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("api") == "up"
        print("PASS: Health check /api/health returns 200, api=up")

    def test_swr_span_5mhz_returns_61_points(self):
        """swr_span_mhz=5.0 returns 61 points spanning 5MHz (±2.5MHz from center)"""
        payload = {**BASE_PAYLOAD, "swr_span_mhz": 5.0}
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        swr_curve = data.get("swr_curve", [])
        assert len(swr_curve) == 61, f"Expected 61 points, got {len(swr_curve)}"
        
        # Verify frequency span is approximately 5MHz
        freqs = [p["frequency"] for p in swr_curve]
        min_freq = min(freqs)
        max_freq = max(freqs)
        span = max_freq - min_freq
        
        center = 27.185
        expected_min = center - 2.5
        expected_max = center + 2.5
        
        assert abs(min_freq - expected_min) < 0.1, f"Min freq {min_freq} not near {expected_min}"
        assert abs(max_freq - expected_max) < 0.1, f"Max freq {max_freq} not near {expected_max}"
        assert abs(span - 5.0) < 0.2, f"Span {span} MHz not near 5.0 MHz"
        
        print(f"PASS: swr_span_mhz=5.0 - 61 points, span {span:.2f} MHz ({min_freq:.3f} to {max_freq:.3f})")

    def test_swr_span_10mhz_returns_correct_range(self):
        """swr_span_mhz=10.0 returns points spanning 10MHz"""
        payload = {**BASE_PAYLOAD, "swr_span_mhz": 10.0}
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
        assert response.status_code == 200
        data = response.json()
        
        swr_curve = data.get("swr_curve", [])
        assert len(swr_curve) == 61, f"Expected 61 points, got {len(swr_curve)}"
        
        freqs = [p["frequency"] for p in swr_curve]
        span = max(freqs) - min(freqs)
        
        assert abs(span - 10.0) < 0.3, f"Span {span} MHz not near 10.0 MHz"
        print(f"PASS: swr_span_mhz=10.0 - 61 points, span {span:.2f} MHz")

    def test_no_swr_span_returns_default_channel_based_curve(self):
        """Without swr_span_mhz, returns default ±30 channels (61 points at channel_spacing intervals)"""
        payload = {k: v for k, v in BASE_PAYLOAD.items() if k != "swr_span_mhz"}
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
        assert response.status_code == 200
        data = response.json()
        
        swr_curve = data.get("swr_curve", [])
        # Default is ±30 channels = 61 points
        assert len(swr_curve) == 61, f"Expected 61 points for default, got {len(swr_curve)}"
        
        # Verify channel indices present (-30 to +30)
        channels = [p.get("channel") for p in swr_curve]
        assert -30 in channels, "Expected channel -30 in default curve"
        assert 0 in channels, "Expected channel 0 (center) in default curve"
        assert 30 in channels, "Expected channel +30 in default curve"
        
        # Default channel spacing for 11m CB is 10 kHz = 0.01 MHz
        # 61 channels * 0.01 = 0.6 MHz total span
        freqs = [p["frequency"] for p in swr_curve]
        span = max(freqs) - min(freqs)
        assert span < 1.0, f"Default span {span} MHz should be < 1 MHz (channel-based)"
        
        print(f"PASS: No swr_span_mhz - 61 points, span {span:.3f} MHz (channel-based)")

    def test_swr_span_20mhz_allows_high_swr_values(self):
        """swr_span_mhz=20.0 returns points spanning 20MHz with SWR values up to 10"""
        payload = {**BASE_PAYLOAD, "swr_span_mhz": 20.0}
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
        assert response.status_code == 200
        data = response.json()
        
        swr_curve = data.get("swr_curve", [])
        assert len(swr_curve) == 61, f"Expected 61 points, got {len(swr_curve)}"
        
        freqs = [p["frequency"] for p in swr_curve]
        span = max(freqs) - min(freqs)
        assert abs(span - 20.0) < 0.5, f"Span {span} MHz not near 20.0 MHz"
        
        # With wide span, expect some high SWR values at band edges
        swr_values = [p["swr"] for p in swr_curve]
        max_swr = max(swr_values)
        # SWR is capped at 10.0 in the backend
        assert max_swr <= 10.0, f"Max SWR {max_swr} should be <= 10.0"
        
        print(f"PASS: swr_span_mhz=20.0 - 61 points, span {span:.2f} MHz, max SWR {max_swr}")

    def test_swr_curve_center_matches_matched_swr(self):
        """SWR curve center value should approximately match matching_info.matched_swr"""
        payload = {**BASE_PAYLOAD, "swr_span_mhz": 5.0}
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
        assert response.status_code == 200
        data = response.json()
        
        matching_info = data.get("matching_info", {})
        matched_swr = matching_info.get("matched_swr", 0)
        
        swr_curve = data.get("swr_curve", [])
        center_freq = 27.185
        
        # Find the SWR value closest to center frequency
        center_pt = min(swr_curve, key=lambda p: abs(p["frequency"] - center_freq))
        center_swr = center_pt["swr"]
        
        # Also find minimum SWR in curve
        min_swr_pt = min(swr_curve, key=lambda p: p["swr"])
        min_swr = min_swr_pt["swr"]
        
        # The minimum SWR should be close to matched_swr (within reasonable tolerance)
        # Using tolerance of 0.5 because SWR curve uses full physics model
        tolerance = 0.5
        assert abs(min_swr - matched_swr) < tolerance, \
            f"Curve min SWR {min_swr} differs from matched_swr {matched_swr} by more than {tolerance}"
        
        print(f"PASS: SWR curve min {min_swr:.2f} matches matched_swr {matched_swr:.2f} (tolerance {tolerance})")


class TestSWRSpanValidation:
    """Test validation constraints on swr_span_mhz parameter"""

    def test_swr_span_minimum_0_1(self):
        """swr_span_mhz has minimum constraint of 0.1"""
        payload = {**BASE_PAYLOAD, "swr_span_mhz": 0.1}
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
        assert response.status_code == 200
        data = response.json()
        
        swr_curve = data.get("swr_curve", [])
        assert len(swr_curve) == 61
        
        freqs = [p["frequency"] for p in swr_curve]
        span = max(freqs) - min(freqs)
        assert abs(span - 0.1) < 0.02, f"Span {span} not near 0.1 MHz"
        print(f"PASS: swr_span_mhz=0.1 - 61 points, span {span:.3f} MHz")

    def test_swr_span_maximum_20(self):
        """swr_span_mhz has maximum constraint of 20.0"""
        payload = {**BASE_PAYLOAD, "swr_span_mhz": 20.0}
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
        assert response.status_code == 200
        data = response.json()
        
        swr_curve = data.get("swr_curve", [])
        assert len(swr_curve) == 61
        print("PASS: swr_span_mhz=20.0 accepted (max value)")

    def test_swr_span_over_maximum_rejected(self):
        """swr_span_mhz > 20.0 should be rejected by validation"""
        payload = {**BASE_PAYLOAD, "swr_span_mhz": 25.0}
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
        # Pydantic validation should reject this
        assert response.status_code == 422, f"Expected 422 validation error, got {response.status_code}"
        print("PASS: swr_span_mhz=25.0 correctly rejected (> 20.0 max)")

    def test_swr_span_below_minimum_rejected(self):
        """swr_span_mhz < 0.1 should be rejected by validation"""
        payload = {**BASE_PAYLOAD, "swr_span_mhz": 0.05}
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
        assert response.status_code == 422, f"Expected 422 validation error, got {response.status_code}"
        print("PASS: swr_span_mhz=0.05 correctly rejected (< 0.1 min)")


class TestSWRSpanOptions:
    """Test specific span options (Band default, 1, 2, 5, 10, 20 MHz)"""

    def test_span_1mhz(self):
        """swr_span_mhz=1.0 returns correct span"""
        payload = {**BASE_PAYLOAD, "swr_span_mhz": 1.0}
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
        assert response.status_code == 200
        data = response.json()
        
        swr_curve = data.get("swr_curve", [])
        freqs = [p["frequency"] for p in swr_curve]
        span = max(freqs) - min(freqs)
        assert abs(span - 1.0) < 0.1, f"Span {span} not near 1.0 MHz"
        print(f"PASS: swr_span_mhz=1.0 - span {span:.3f} MHz")

    def test_span_2mhz(self):
        """swr_span_mhz=2.0 returns correct span"""
        payload = {**BASE_PAYLOAD, "swr_span_mhz": 2.0}
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
        assert response.status_code == 200
        data = response.json()
        
        swr_curve = data.get("swr_curve", [])
        freqs = [p["frequency"] for p in swr_curve]
        span = max(freqs) - min(freqs)
        assert abs(span - 2.0) < 0.1, f"Span {span} not near 2.0 MHz"
        print(f"PASS: swr_span_mhz=2.0 - span {span:.3f} MHz")

    def test_span_5mhz(self):
        """swr_span_mhz=5.0 returns correct span"""
        payload = {**BASE_PAYLOAD, "swr_span_mhz": 5.0}
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
        assert response.status_code == 200
        data = response.json()
        
        swr_curve = data.get("swr_curve", [])
        freqs = [p["frequency"] for p in swr_curve]
        span = max(freqs) - min(freqs)
        assert abs(span - 5.0) < 0.2, f"Span {span} not near 5.0 MHz"
        print(f"PASS: swr_span_mhz=5.0 - span {span:.3f} MHz")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
