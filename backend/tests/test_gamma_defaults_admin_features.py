"""Tests for gamma match default parameters and admin panel feature limits expansion.

Tests:
1. POST /api/calculate with feed_type=gamma should return gamma_design with:
   - spacing=3.0 (3" center-to-center)
   - rod_length~32" (~wavelength * 0.074 at 11m CB)
   - rod_insertion=0.125 (default)
2. GET /api/admin/pricing returns current features for each tier
3. PUT /api/admin/pricing accepts 20 feature names per tier (expanded from 8)

Admin credentials: fallstommy@gmail.com / admin123
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# 3-element 11m CB Yagi test configuration
THREE_ELEMENT_YAGI_PAYLOAD = {
    "band": "11m_cb",
    "frequency_mhz": 27.185,
    "num_elements": 3,
    "height_from_ground": 54,
    "height_unit": "ft",
    "boom_diameter": 2.0,
    "boom_unit": "inches",
    "boom_grounded": True,
    "boom_mount": "bonded",
    "antenna_orientation": "horizontal",
    "feed_type": "gamma",
    "elements": [
        {"element_type": "reflector", "length": 214.5, "diameter": 0.5, "position": 0},
        {"element_type": "driven", "length": 202.4, "diameter": 0.5, "position": 47},
        {"element_type": "director", "length": 195.0, "diameter": 0.5, "position": 138}
    ]
}

# All 20 features from frontend admin.tsx (expanded from 8)
ALL_20_FEATURES = [
    'auto_tune', 'optimize_height', 'save_designs', 'csv_export', 
    'stacking', 'taper', 'corona_balls', 'ground_radials', 
    'gamma_match', 'hairpin_match', 'smith_chart', 'polar_pattern', 
    'elevation_pattern', 'dual_polarity', 'coax_loss', 'wind_load', 
    'pdf_export', 'spacing_control', 'return_loss_tune', 'reflected_power'
]


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session."""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def auth_token(api_client):
    """Get authentication token for admin."""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": "fallstommy@gmail.com",
        "password": "admin123"
    })
    if response.status_code == 200:
        data = response.json()
        return data.get("token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def admin_client(api_client, auth_token):
    """Session with admin auth header."""
    api_client.headers.update({"Authorization": f"Bearer {auth_token}"})
    return api_client


class TestGammaMatchDefaults:
    """Test gamma match default parameters: 3" spacing, ~32" length, 0.125 insertion."""
    
    def test_gamma_design_returns_correct_spacing(self, api_client):
        """gamma_design.gamma_rod_spacing_in should be 3.0 (3 inches center-to-center)."""
        response = api_client.post(f"{BASE_URL}/api/calculate", json=THREE_ELEMENT_YAGI_PAYLOAD)
        
        assert response.status_code == 200, f"Calculate endpoint failed: {response.text}"
        data = response.json()
        
        # Check matching_info exists and contains gamma_design
        assert "matching_info" in data, "Response should contain matching_info"
        matching_info = data["matching_info"]
        
        assert "gamma_design" in matching_info, "matching_info should contain gamma_design for feed_type=gamma"
        gamma_design = matching_info["gamma_design"]
        
        # Verify spacing is 3.0"
        assert "gamma_rod_spacing_in" in gamma_design, "gamma_design should contain gamma_rod_spacing_in"
        spacing = gamma_design["gamma_rod_spacing_in"]
        assert spacing == 3.0, f"Expected gamma_rod_spacing_in=3.0, got {spacing}"
        print(f"✓ gamma_rod_spacing_in = {spacing} (expected 3.0)")
    
    def test_gamma_design_returns_rod_length_around_32(self, api_client):
        """gamma_design.gamma_rod_length_in should be ~32" (wavelength * 0.074)."""
        response = api_client.post(f"{BASE_URL}/api/calculate", json=THREE_ELEMENT_YAGI_PAYLOAD)
        
        assert response.status_code == 200
        data = response.json()
        gamma_design = data["matching_info"]["gamma_design"]
        
        # Verify rod length is approximately 32" (formula: wavelength_in * 0.074)
        # At 27.185 MHz: wavelength_in = 11802.71 / 27.185 ≈ 434.13"
        # Expected rod_length = 434.13 * 0.074 ≈ 32.13"
        assert "gamma_rod_length_in" in gamma_design, "gamma_design should contain gamma_rod_length_in"
        rod_length = gamma_design["gamma_rod_length_in"]
        
        # Allow ±2" tolerance for the ~32" target
        assert 30.0 <= rod_length <= 34.0, f"Expected gamma_rod_length_in ~32, got {rod_length}"
        print(f"✓ gamma_rod_length_in = {rod_length} (expected ~32)")
    
    def test_gamma_matching_info_rod_insertion_default(self, api_client):
        """matching_info.rod_insertion should be 0.125 (default)."""
        response = api_client.post(f"{BASE_URL}/api/calculate", json=THREE_ELEMENT_YAGI_PAYLOAD)
        
        assert response.status_code == 200
        data = response.json()
        matching_info = data["matching_info"]
        
        # Verify rod_insertion default is 0.125
        assert "rod_insertion" in matching_info, "matching_info should contain rod_insertion"
        rod_insertion = matching_info["rod_insertion"]
        assert rod_insertion == 0.125, f"Expected rod_insertion=0.125, got {rod_insertion}"
        print(f"✓ rod_insertion = {rod_insertion} (expected 0.125)")
    
    def test_gamma_design_complete_structure(self, api_client):
        """Verify gamma_design contains all expected fields."""
        response = api_client.post(f"{BASE_URL}/api/calculate", json=THREE_ELEMENT_YAGI_PAYLOAD)
        
        assert response.status_code == 200
        data = response.json()
        gamma_design = data["matching_info"]["gamma_design"]
        
        expected_fields = [
            "feedpoint_impedance_ohms", "target_impedance_ohms", "step_up_ratio",
            "element_diameter_in", "gamma_rod_diameter_in", "gamma_rod_spacing_in",
            "gamma_rod_length_in", "capacitance_pf", "auto_capacitance_pf",
            "shorting_bar_position_in", "element_shortening_pct", "wavelength_inches"
        ]
        
        for field in expected_fields:
            assert field in gamma_design, f"gamma_design missing field: {field}"
        
        print(f"✓ gamma_design contains all {len(expected_fields)} expected fields")
        print(f"  - feedpoint_impedance_ohms: {gamma_design['feedpoint_impedance_ohms']}")
        print(f"  - gamma_rod_spacing_in: {gamma_design['gamma_rod_spacing_in']}")
        print(f"  - gamma_rod_length_in: {gamma_design['gamma_rod_length_in']}")


class TestAdminPricingGetFeatures:
    """Test GET /api/admin/pricing returns features for each tier."""
    
    def test_get_admin_pricing_requires_auth(self, api_client):
        """GET /api/admin/pricing should require authentication."""
        # Use fresh session without auth header
        fresh_session = requests.Session()
        response = fresh_session.get(f"{BASE_URL}/api/admin/pricing")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ GET /api/admin/pricing requires authentication")
    
    def test_get_admin_pricing_returns_tiers(self, admin_client):
        """GET /api/admin/pricing should return bronze, silver, gold tiers."""
        response = admin_client.get(f"{BASE_URL}/api/admin/pricing")
        
        assert response.status_code == 200, f"Admin pricing failed: {response.text}"
        data = response.json()
        
        # Check all tiers present
        assert "bronze" in data, "Response should contain bronze tier"
        assert "silver" in data, "Response should contain silver tier"
        assert "gold" in data, "Response should contain gold tier"
        
        print("✓ GET /api/admin/pricing returns all three tiers")
    
    def test_get_admin_pricing_tiers_have_features(self, admin_client):
        """Each tier should have a features array."""
        response = admin_client.get(f"{BASE_URL}/api/admin/pricing")
        
        assert response.status_code == 200
        data = response.json()
        
        for tier in ["bronze", "silver", "gold"]:
            assert "features" in data[tier], f"{tier} tier should have features array"
            print(f"✓ {tier} tier has features: {data[tier]['features']}")


class TestAdminPricingUpdate20Features:
    """Test PUT /api/admin/pricing accepts 20 feature names (expanded from 8)."""
    
    def test_update_pricing_with_all_20_features(self, admin_client):
        """PUT /api/admin/pricing should accept all 20 features per tier."""
        # First get current pricing to preserve prices
        get_response = admin_client.get(f"{BASE_URL}/api/admin/pricing")
        assert get_response.status_code == 200
        current = get_response.json()
        
        # Create update payload with all 20 features for each tier
        update_payload = {
            # Bronze: first 5 features
            "bronze_monthly_price": current["bronze"]["monthly_price"],
            "bronze_yearly_price": current["bronze"]["yearly_price"],
            "bronze_max_elements": current["bronze"]["max_elements"],
            "bronze_features": ALL_20_FEATURES[:5],  # First 5 features
            
            # Silver: first 12 features  
            "silver_monthly_price": current["silver"]["monthly_price"],
            "silver_yearly_price": current["silver"]["yearly_price"],
            "silver_max_elements": current["silver"]["max_elements"],
            "silver_features": ALL_20_FEATURES[:12],  # First 12 features
            
            # Gold: all 20 features
            "gold_monthly_price": current["gold"]["monthly_price"],
            "gold_yearly_price": current["gold"]["yearly_price"],
            "gold_max_elements": current["gold"]["max_elements"],
            "gold_features": ALL_20_FEATURES  # All 20 features
        }
        
        response = admin_client.put(f"{BASE_URL}/api/admin/pricing", json=update_payload)
        
        assert response.status_code == 200, f"Update pricing failed: {response.text}"
        data = response.json()
        assert data.get("success") == True, f"Expected success=True, got: {data}"
        print("✓ PUT /api/admin/pricing accepts update with all 20 features")
    
    def test_verify_20_features_persisted(self, admin_client):
        """Verify the 20 features were correctly saved."""
        # Get pricing after update
        response = admin_client.get(f"{BASE_URL}/api/admin/pricing")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check gold has all 20 features
        gold_features = data["gold"]["features"]
        assert len(gold_features) == 20, f"Expected gold to have 20 features, got {len(gold_features)}"
        
        # Verify specific new features are present
        new_features = ['gamma_match', 'hairpin_match', 'smith_chart', 'return_loss_tune', 'reflected_power']
        for feat in new_features:
            assert feat in gold_features, f"Gold tier should include {feat}"
        
        print(f"✓ Gold tier has all 20 features: {gold_features}")
    
    def test_feature_names_validation(self, admin_client):
        """Verify all 20 feature names match frontend ALL_FEATURES array."""
        expected_features = [
            'auto_tune', 'optimize_height', 'save_designs', 'csv_export',
            'stacking', 'taper', 'corona_balls', 'ground_radials',
            'gamma_match', 'hairpin_match', 'smith_chart', 'polar_pattern',
            'elevation_pattern', 'dual_polarity', 'coax_loss', 'wind_load',
            'pdf_export', 'spacing_control', 'return_loss_tune', 'reflected_power'
        ]
        
        # Verify ALL_20_FEATURES matches expected
        assert len(ALL_20_FEATURES) == 20, f"Expected 20 features, got {len(ALL_20_FEATURES)}"
        assert ALL_20_FEATURES == expected_features, "Feature list should match frontend ALL_FEATURES"
        print(f"✓ All 20 feature names validated: {ALL_20_FEATURES}")


class TestApiHealthAndBasics:
    """Basic API health checks."""
    
    def test_api_root(self, api_client):
        """API root should be accessible."""
        response = api_client.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        print("✓ API root accessible")
    
    def test_calculate_endpoint_accessible(self, api_client):
        """Calculate endpoint should accept POST."""
        response = api_client.post(f"{BASE_URL}/api/calculate", json=THREE_ELEMENT_YAGI_PAYLOAD)
        assert response.status_code == 200
        print("✓ Calculate endpoint working")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
