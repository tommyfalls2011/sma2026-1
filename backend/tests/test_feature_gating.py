"""
Test Feature Gating - Iteration 19
Tests for: Feature enforcement, gamma defaults, subscription tiers, admin pricing
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestGammaDefaults:
    """Test gamma match default parameters in calculate endpoint"""
    
    def test_gamma_defaults_spacing_3_inches(self):
        """Gamma spacing default should be 3.0 inches"""
        response = requests.post(f"{BASE_URL}/api/calculate", json={
            "num_elements": 3,
            "elements": [
                {"element_type": "reflector", "length": 216, "diameter": 0.5, "position": 0},
                {"element_type": "driven", "length": 204, "diameter": 0.5, "position": 48},
                {"element_type": "director", "length": 195, "diameter": 0.5, "position": 96}
            ],
            "height_from_ground": 54, "height_unit": "ft",
            "boom_diameter": 1.5, "boom_unit": "inches",
            "band": "11m_cb", "frequency_mhz": 27.185,
            "feed_type": "gamma"
        })
        assert response.status_code == 200, f"Status: {response.status_code}, Body: {response.text}"
        data = response.json()
        assert "matching_info" in data
        assert "gamma_design" in data["matching_info"]
        gamma_design = data["matching_info"]["gamma_design"]
        assert gamma_design.get("gamma_rod_spacing_in") == 3.0, f"Expected 3.0, got {gamma_design.get('gamma_rod_spacing_in')}"
        print(f"PASS: gamma_rod_spacing_in = {gamma_design.get('gamma_rod_spacing_in')}")

    def test_gamma_defaults_rod_length_around_32(self):
        """Gamma rod length should be ~32 inches for 11m CB"""
        response = requests.post(f"{BASE_URL}/api/calculate", json={
            "num_elements": 3,
            "elements": [
                {"element_type": "reflector", "length": 216, "diameter": 0.5, "position": 0},
                {"element_type": "driven", "length": 204, "diameter": 0.5, "position": 48},
                {"element_type": "director", "length": 195, "diameter": 0.5, "position": 96}
            ],
            "height_from_ground": 54, "height_unit": "ft",
            "boom_diameter": 1.5, "boom_unit": "inches",
            "band": "11m_cb", "frequency_mhz": 27.185,
            "feed_type": "gamma"
        })
        assert response.status_code == 200
        data = response.json()
        rod_length = data["matching_info"]["gamma_design"].get("gamma_rod_length_in", 0)
        assert 30 <= rod_length <= 35, f"Expected ~32, got {rod_length}"
        print(f"PASS: gamma_rod_length_in = {rod_length}")

    def test_gamma_defaults_insertion_0_125(self):
        """Gamma rod insertion default should be 0.125"""
        response = requests.post(f"{BASE_URL}/api/calculate", json={
            "num_elements": 3,
            "elements": [
                {"element_type": "reflector", "length": 216, "diameter": 0.5, "position": 0},
                {"element_type": "driven", "length": 204, "diameter": 0.5, "position": 48},
                {"element_type": "director", "length": 195, "diameter": 0.5, "position": 96}
            ],
            "height_from_ground": 54, "height_unit": "ft",
            "boom_diameter": 1.5, "boom_unit": "inches",
            "band": "11m_cb", "frequency_mhz": 27.185,
            "feed_type": "gamma"
        })
        assert response.status_code == 200
        data = response.json()
        insertion = data["matching_info"].get("rod_insertion", None)
        assert insertion == 0.125, f"Expected 0.125, got {insertion}"
        print(f"PASS: rod_insertion = {insertion}")


class TestSubscriptionTiers:
    """Test subscription tier API returns correct feature lists"""
    
    def test_get_tiers_returns_data(self):
        """GET /api/subscription/tiers should return tier data"""
        response = requests.get(f"{BASE_URL}/api/subscription/tiers")
        assert response.status_code == 200, f"Status: {response.status_code}"
        data = response.json()
        assert "tiers" in data
        print(f"PASS: Got tiers endpoint")
    
    def test_tiers_contain_features_arrays(self):
        """Each tier should have a features array"""
        response = requests.get(f"{BASE_URL}/api/subscription/tiers")
        assert response.status_code == 200
        data = response.json()
        tiers = data.get("tiers", {})
        
        for tier_name in ["bronze", "silver", "gold"]:
            if tier_name in tiers:
                tier = tiers[tier_name]
                assert "features" in tier, f"Tier {tier_name} missing features"
                assert isinstance(tier["features"], list), f"Tier {tier_name} features not a list"
                print(f"PASS: Tier {tier_name} has features array: {tier['features'][:5]}...")
            else:
                print(f"INFO: Tier {tier_name} not present in tiers response")


class TestAdminPricing:
    """Test admin pricing API with authentication"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin token for testing"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "fallstommy@gmail.com",
            "password": "admin123"
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip(f"Admin login failed: {response.status_code}")
    
    def test_admin_pricing_requires_auth(self):
        """GET /api/admin/pricing should require authentication"""
        response = requests.get(f"{BASE_URL}/api/admin/pricing")
        assert response.status_code == 401 or response.status_code == 403, f"Expected 401/403, got {response.status_code}"
        print("PASS: Admin pricing requires auth")
    
    def test_admin_pricing_returns_tiers_with_features(self, admin_token):
        """Authenticated admin should get pricing with features"""
        response = requests.get(f"{BASE_URL}/api/admin/pricing", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200, f"Status: {response.status_code}"
        data = response.json()
        
        for tier in ["bronze", "silver", "gold"]:
            if tier in data:
                assert "features" in data[tier], f"{tier} missing features"
                print(f"PASS: {tier} tier has features: {data[tier].get('features', [])[:3]}...")
    
    def test_admin_pricing_update_features(self, admin_token):
        """Admin can update tier features via PUT"""
        # First get current pricing
        get_response = requests.get(f"{BASE_URL}/api/admin/pricing", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert get_response.status_code == 200
        current = get_response.json()
        
        # Update with 20 features for gold tier
        all_features = ['auto_tune', 'optimize_height', 'save_designs', 'csv_export', 'stacking', 
                        'taper', 'corona_balls', 'ground_radials', 'gamma_match', 'hairpin_match', 
                        'smith_chart', 'polar_pattern', 'elevation_pattern', 'dual_polarity', 
                        'coax_loss', 'wind_load', 'pdf_export', 'spacing_control', 
                        'return_loss_tune', 'reflected_power']
        
        update_response = requests.put(f"{BASE_URL}/api/admin/pricing", headers={
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }, json={
            "bronze_monthly_price": current.get("bronze", {}).get("monthly_price", 9.99),
            "bronze_yearly_price": current.get("bronze", {}).get("yearly_price", 99.99),
            "bronze_max_elements": current.get("bronze", {}).get("max_elements", 5),
            "bronze_features": current.get("bronze", {}).get("features", []),
            "silver_monthly_price": current.get("silver", {}).get("monthly_price", 19.99),
            "silver_yearly_price": current.get("silver", {}).get("yearly_price", 199.99),
            "silver_max_elements": current.get("silver", {}).get("max_elements", 10),
            "silver_features": current.get("silver", {}).get("features", []),
            "gold_monthly_price": current.get("gold", {}).get("monthly_price", 29.99),
            "gold_yearly_price": current.get("gold", {}).get("yearly_price", 299.99),
            "gold_max_elements": current.get("gold", {}).get("max_elements", 20),
            "gold_features": all_features
        })
        assert update_response.status_code == 200, f"Update failed: {update_response.text}"
        print("PASS: Admin pricing update successful")


class TestLoginFlow:
    """Test login functionality"""
    
    def test_login_admin_success(self):
        """Admin login should work with correct credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "fallstommy@gmail.com",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Login failed: {response.status_code}, {response.text}"
        data = response.json()
        assert "token" in data
        assert "user" in data
        print(f"PASS: Admin login successful, tier: {data['user'].get('subscription_tier')}")
    
    def test_login_invalid_credentials(self):
        """Invalid credentials should return 401"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "invalid@email.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: Invalid login returns 401")


class TestCalculateEndpoint:
    """Test calculate endpoint basics"""
    
    def test_calculate_endpoint_works(self):
        """Basic calculate should return results"""
        response = requests.post(f"{BASE_URL}/api/calculate", json={
            "num_elements": 2,
            "elements": [
                {"element_type": "reflector", "length": 216, "diameter": 0.5, "position": 0},
                {"element_type": "driven", "length": 204, "diameter": 0.5, "position": 48}
            ],
            "height_from_ground": 54, "height_unit": "ft",
            "boom_diameter": 1.5, "boom_unit": "inches",
            "band": "11m_cb", "frequency_mhz": 27.185
        })
        assert response.status_code == 200
        data = response.json()
        assert "gain_dbi" in data
        assert "swr" in data
        assert "fb_ratio" in data
        print(f"PASS: Calculate returns gain={data['gain_dbi']}, swr={data['swr']}, fb={data['fb_ratio']}")
    
    def test_calculate_returns_polar_pattern(self):
        """Calculate should include far_field_pattern data"""
        response = requests.post(f"{BASE_URL}/api/calculate", json={
            "num_elements": 3,
            "elements": [
                {"element_type": "reflector", "length": 216, "diameter": 0.5, "position": 0},
                {"element_type": "driven", "length": 204, "diameter": 0.5, "position": 48},
                {"element_type": "director", "length": 195, "diameter": 0.5, "position": 96}
            ],
            "height_from_ground": 54, "height_unit": "ft",
            "boom_diameter": 1.5, "boom_unit": "inches",
            "band": "11m_cb", "frequency_mhz": 27.185
        })
        assert response.status_code == 200
        data = response.json()
        assert "far_field_pattern" in data, "Missing far_field_pattern"
        assert len(data["far_field_pattern"]) > 0, "Empty far_field_pattern"
        print(f"PASS: far_field_pattern has {len(data['far_field_pattern'])} points")
    
    def test_calculate_returns_smith_chart_data(self):
        """Calculate should include smith_chart_data"""
        response = requests.post(f"{BASE_URL}/api/calculate", json={
            "num_elements": 3,
            "elements": [
                {"element_type": "reflector", "length": 216, "diameter": 0.5, "position": 0},
                {"element_type": "driven", "length": 204, "diameter": 0.5, "position": 48},
                {"element_type": "director", "length": 195, "diameter": 0.5, "position": 96}
            ],
            "height_from_ground": 54, "height_unit": "ft",
            "boom_diameter": 1.5, "boom_unit": "inches",
            "band": "11m_cb", "frequency_mhz": 27.185
        })
        assert response.status_code == 200
        data = response.json()
        assert "smith_chart_data" in data, "Missing smith_chart_data"
        print(f"PASS: smith_chart_data present")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
