"""
Backend API tests for antenna calculator after frontend refactoring.
Verifies all core API endpoints still work correctly.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://element-spacing-v5.preview.emergentagent.com').rstrip('/')


class TestCalculateAPI:
    """Tests for /api/calculate endpoint - core antenna calculation"""
    
    def test_calculate_2_element_yagi(self):
        """Test basic 2-element Yagi calculation"""
        response = requests.post(f"{BASE_URL}/api/calculate", json={
            "num_elements": 2,
            "elements": [
                {"element_type": "reflector", "length": 216, "diameter": 0.5, "position": 0},
                {"element_type": "driven", "length": 204, "diameter": 0.5, "position": 48}
            ],
            "height_from_ground": 54,
            "height_unit": "ft",
            "boom_diameter": 1.5,
            "boom_unit": "inches",
            "band": "11m_cb",
            "frequency_mhz": 27.185
        })
        assert response.status_code == 200
        data = response.json()
        
        # Verify core fields exist
        assert "swr" in data
        assert "gain_dbi" in data
        assert "fb_ratio" in data
        assert "bandwidth" in data
        assert "far_field_pattern" in data
        assert "swr_curve" in data
        assert "smith_chart_data" in data
        
        # Verify SWR is reasonable
        assert 1.0 <= data["swr"] <= 5.0
        
        # Verify gain is positive
        assert data["gain_dbi"] > 0
        
        print(f"✓ 2-element Yagi: SWR={data['swr']:.2f}, Gain={data['gain_dbi']:.2f} dBi, F/B={data['fb_ratio']:.1f} dB")
    
    def test_calculate_3_element_yagi(self):
        """Test 3-element Yagi calculation"""
        response = requests.post(f"{BASE_URL}/api/calculate", json={
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
        })
        assert response.status_code == 200
        data = response.json()
        
        # 3-element should have higher gain than 2-element
        assert data["gain_dbi"] > 10.0
        assert data["fb_ratio"] > 10.0
        
        print(f"✓ 3-element Yagi: SWR={data['swr']:.2f}, Gain={data['gain_dbi']:.2f} dBi, F/B={data['fb_ratio']:.1f} dB")
    
    def test_calculate_with_gamma_match(self):
        """Test calculation with Gamma feed match"""
        response = requests.post(f"{BASE_URL}/api/calculate", json={
            "num_elements": 2,
            "elements": [
                {"element_type": "reflector", "length": 216, "diameter": 0.5, "position": 0},
                {"element_type": "driven", "length": 204, "diameter": 0.5, "position": 48}
            ],
            "height_from_ground": 54,
            "height_unit": "ft",
            "boom_diameter": 1.5,
            "boom_unit": "inches",
            "band": "11m_cb",
            "frequency_mhz": 27.185,
            "feed_type": "gamma",
            "gamma_bar_pos": 24,
            "gamma_element_gap": 0.5
        })
        assert response.status_code == 200
        data = response.json()
        
        # Verify gamma match info is present
        assert "matching_info" in data
        assert data["feed_type"] == "gamma"
        
        print(f"✓ Gamma match: SWR={data['swr']:.2f}, Feed Type={data['feed_type']}")
    
    def test_calculate_with_hairpin_match(self):
        """Test calculation with Hairpin feed match"""
        response = requests.post(f"{BASE_URL}/api/calculate", json={
            "num_elements": 2,
            "elements": [
                {"element_type": "reflector", "length": 216, "diameter": 0.5, "position": 0},
                {"element_type": "driven", "length": 204, "diameter": 0.5, "position": 48}
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
        
        assert data["feed_type"] == "hairpin"
        print(f"✓ Hairpin match: SWR={data['swr']:.2f}, Feed Type={data['feed_type']}")
    
    def test_calculate_swr_curve_data(self):
        """Test that SWR curve data is returned correctly"""
        response = requests.post(f"{BASE_URL}/api/calculate", json={
            "num_elements": 2,
            "elements": [
                {"element_type": "reflector", "length": 216, "diameter": 0.5, "position": 0},
                {"element_type": "driven", "length": 204, "diameter": 0.5, "position": 48}
            ],
            "height_from_ground": 54,
            "height_unit": "ft",
            "boom_diameter": 1.5,
            "boom_unit": "inches",
            "band": "11m_cb",
            "frequency_mhz": 27.185
        })
        assert response.status_code == 200
        data = response.json()
        
        # Verify SWR curve data
        assert "swr_curve" in data
        assert len(data["swr_curve"]) > 0
        
        # Check first point has required fields
        first_point = data["swr_curve"][0]
        assert "frequency" in first_point
        assert "swr" in first_point
        assert "channel" in first_point
        
        print(f"✓ SWR curve: {len(data['swr_curve'])} data points")
    
    def test_calculate_smith_chart_data(self):
        """Test that Smith chart data is returned correctly"""
        response = requests.post(f"{BASE_URL}/api/calculate", json={
            "num_elements": 2,
            "elements": [
                {"element_type": "reflector", "length": 216, "diameter": 0.5, "position": 0},
                {"element_type": "driven", "length": 204, "diameter": 0.5, "position": 48}
            ],
            "height_from_ground": 54,
            "height_unit": "ft",
            "boom_diameter": 1.5,
            "boom_unit": "inches",
            "band": "11m_cb",
            "frequency_mhz": 27.185
        })
        assert response.status_code == 200
        data = response.json()
        
        # Verify Smith chart data
        assert "smith_chart_data" in data
        assert len(data["smith_chart_data"]) > 0
        
        # Check first point has required fields
        first_point = data["smith_chart_data"][0]
        assert "freq" in first_point
        assert "z_real" in first_point
        assert "z_imag" in first_point
        assert "gamma_real" in first_point
        assert "gamma_imag" in first_point
        
        print(f"✓ Smith chart: {len(data['smith_chart_data'])} data points")
    
    def test_calculate_far_field_pattern(self):
        """Test that far field pattern data is returned correctly"""
        response = requests.post(f"{BASE_URL}/api/calculate", json={
            "num_elements": 2,
            "elements": [
                {"element_type": "reflector", "length": 216, "diameter": 0.5, "position": 0},
                {"element_type": "driven", "length": 204, "diameter": 0.5, "position": 48}
            ],
            "height_from_ground": 54,
            "height_unit": "ft",
            "boom_diameter": 1.5,
            "boom_unit": "inches",
            "band": "11m_cb",
            "frequency_mhz": 27.185
        })
        assert response.status_code == 200
        data = response.json()
        
        # Verify far field pattern
        assert "far_field_pattern" in data
        assert len(data["far_field_pattern"]) > 0
        
        # Check points have angle and magnitude
        first_point = data["far_field_pattern"][0]
        assert "angle" in first_point
        assert "magnitude" in first_point
        
        # Forward should be 100%
        forward_point = next((p for p in data["far_field_pattern"] if p["angle"] == 0), None)
        assert forward_point is not None
        assert forward_point["magnitude"] == 100.0
        
        print(f"✓ Far field pattern: {len(data['far_field_pattern'])} data points")


class TestAutoTuneAPI:
    """Tests for /api/auto-tune endpoint"""
    
    def test_auto_tune_2_elements(self):
        """Test auto-tune for 2-element Yagi"""
        response = requests.post(f"{BASE_URL}/api/auto-tune", json={
            "num_elements": 2,
            "height_from_ground": 54,
            "height_unit": "ft",
            "boom_diameter": 1.5,
            "boom_unit": "inches",
            "band": "11m_cb"
        })
        assert response.status_code == 200
        data = response.json()
        
        # Verify optimized elements returned
        assert "optimized_elements" in data
        assert len(data["optimized_elements"]) == 2
        
        # Verify predictions
        assert "predicted_swr" in data
        assert "predicted_gain" in data
        
        print(f"✓ Auto-tune 2-elem: SWR={data['predicted_swr']}, Gain={data['predicted_gain']} dBi")
    
    def test_auto_tune_3_elements(self):
        """Test auto-tune for 3-element Yagi"""
        response = requests.post(f"{BASE_URL}/api/auto-tune", json={
            "num_elements": 3,
            "height_from_ground": 54,
            "height_unit": "ft",
            "boom_diameter": 1.5,
            "boom_unit": "inches",
            "band": "11m_cb"
        })
        assert response.status_code == 200
        data = response.json()
        
        # Verify 3 elements returned
        assert len(data["optimized_elements"]) == 3
        
        # Check element types
        types = [e["element_type"] for e in data["optimized_elements"]]
        assert "reflector" in types
        assert "driven" in types
        assert "director" in types
        
        print(f"✓ Auto-tune 3-elem: SWR={data['predicted_swr']}, Gain={data['predicted_gain']} dBi")
    
    def test_auto_tune_with_spacing_mode(self):
        """Test auto-tune with different spacing modes"""
        for mode in ["normal", "tight", "long"]:
            response = requests.post(f"{BASE_URL}/api/auto-tune", json={
                "num_elements": 3,
                "height_from_ground": 54,
                "height_unit": "ft",
                "boom_diameter": 1.5,
                "boom_unit": "inches",
                "band": "11m_cb",
                "spacing_mode": mode
            })
            assert response.status_code == 200
            data = response.json()
            assert "optimized_elements" in data
            print(f"✓ Auto-tune spacing mode '{mode}': Gain={data['predicted_gain']} dBi")


class TestOtherEndpoints:
    """Tests for other API endpoints"""
    
    def test_subscription_tiers(self):
        """Test subscription tiers endpoint"""
        response = requests.get(f"{BASE_URL}/api/subscription/tiers")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Subscription tiers: {len(data)} tiers available")
    
    def test_app_update_check(self):
        """Test app update check endpoint"""
        response = requests.get(f"{BASE_URL}/api/app-update")
        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        print(f"✓ App update: version={data['version']}")


class TestBandSupport:
    """Test calculations for different bands"""
    
    def test_various_bands(self):
        """Test calculations work for different bands"""
        bands = [
            ("11m_cb", 27.185),
            ("10m", 28.5),
            ("6m", 51.0),
            ("2m", 146.0)
        ]
        
        for band_id, freq in bands:
            response = requests.post(f"{BASE_URL}/api/calculate", json={
                "num_elements": 2,
                "elements": [
                    {"element_type": "reflector", "length": 216, "diameter": 0.5, "position": 0},
                    {"element_type": "driven", "length": 204, "diameter": 0.5, "position": 48}
                ],
                "height_from_ground": 54,
                "height_unit": "ft",
                "boom_diameter": 1.5,
                "boom_unit": "inches",
                "band": band_id,
                "frequency_mhz": freq
            })
            assert response.status_code == 200
            data = response.json()
            assert "swr" in data
            print(f"✓ Band {band_id}: SWR={data['swr']:.2f}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
