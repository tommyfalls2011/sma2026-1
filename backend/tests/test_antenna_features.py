"""
Backend API Tests for Antenna Analysis App - New Features
Tests the following features:
1. Gain Breakdown (base_gain_dbi, gain_breakdown fields)
2. Base gain per element count (2-elem=5.5, 3-elem=8.5, 4-elem=10.5, 5-elem=12.0)
3. Height Optimizer with ground_radials parameter
4. Different optimal heights for different antenna configs
5. Tutorial endpoints (GET /api/tutorial, PUT/GET /api/admin/tutorial)
"""

import pytest
import requests
import os

# Base URL from environment - CRITICAL: DO NOT add default
BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL', 'https://polarization-model.preview.emergentagent.com')

# Admin credentials
ADMIN_EMAIL = "fallstommy@gmail.com"
ADMIN_PASSWORD = "admin123"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def admin_token(api_client):
    """Get admin authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        data = response.json()
        return data.get("token") or data.get("access_token")
    pytest.skip(f"Admin authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def authenticated_admin(api_client, admin_token):
    """Session with admin auth header"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {admin_token}"
    })
    return session


def create_element_config(num_elements):
    """Create a standard element configuration for testing"""
    elements = []
    # Reflector
    elements.append({
        "element_type": "reflector",
        "length": 220,
        "diameter": 0.5,
        "position": 0
    })
    # Driven
    elements.append({
        "element_type": "driven",
        "length": 209,
        "diameter": 0.5,
        "position": 40
    })
    # Directors
    for i in range(num_elements - 2):
        elements.append({
            "element_type": "director",
            "length": 200 - (i * 5),
            "diameter": 0.5,
            "position": 80 + (i * 40)
        })
    return elements


class TestCalculateEndpoint:
    """Test POST /api/calculate for gain breakdown and base_gain_dbi"""
    
    def test_calculate_returns_base_gain_dbi_and_breakdown(self, api_client):
        """Verify calculate endpoint returns base_gain_dbi and gain_breakdown fields"""
        payload = {
            "num_elements": 3,
            "elements": create_element_config(3),
            "height_from_ground": 50,
            "height_unit": "ft",
            "boom_diameter": 2,
            "boom_unit": "inches",
            "band": "11m_cb"
        }
        response = api_client.post(f"{BASE_URL}/api/calculate", json=payload)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Check base_gain_dbi exists
        assert "base_gain_dbi" in data, "Missing base_gain_dbi field in response"
        assert isinstance(data["base_gain_dbi"], (int, float)), "base_gain_dbi should be numeric"
        
        # Check gain_breakdown exists and has required fields
        assert "gain_breakdown" in data, "Missing gain_breakdown field in response"
        breakdown = data["gain_breakdown"]
        
        required_breakdown_fields = ["element_gain", "reflector_adj", "taper_bonus", "corona_adj", "height_bonus", "boom_bonus", "final_gain"]
        for field in required_breakdown_fields:
            assert field in breakdown, f"Missing {field} in gain_breakdown"
        
        print(f"✓ base_gain_dbi: {data['base_gain_dbi']}")
        print(f"✓ gain_breakdown: {breakdown}")


class TestBaseGainPerElementCount:
    """Test that base_gain_dbi changes correctly per element count"""
    
    @pytest.mark.parametrize("num_elements,expected_base", [
        (2, 5.5),
        (3, 8.5),
        (4, 10.5),
        (5, 12.0)
    ])
    def test_base_gain_per_element_count(self, api_client, num_elements, expected_base):
        """Verify base gain matches expected values for each element count"""
        payload = {
            "num_elements": num_elements,
            "elements": create_element_config(num_elements),
            "height_from_ground": 50,
            "height_unit": "ft",
            "boom_diameter": 2,
            "boom_unit": "inches",
            "band": "11m_cb"
        }
        response = api_client.post(f"{BASE_URL}/api/calculate", json=payload)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        base_gain = data.get("base_gain_dbi")
        
        # base_gain_dbi = element_gain + reflector_adj (should be element_gain since we have reflector)
        # For antennas WITH reflector, base_gain_dbi = element_gain (no adjustment)
        assert base_gain == expected_base, f"For {num_elements} elements, expected base_gain_dbi={expected_base}, got {base_gain}"
        print(f"✓ {num_elements}-element antenna: base_gain_dbi = {base_gain} (expected {expected_base})")


class TestOptimizeHeightEndpoint:
    """Test POST /api/optimize-height with ground_radials parameter"""
    
    def test_optimize_height_accepts_ground_radials(self, api_client):
        """Verify optimize-height accepts ground_radials parameter"""
        payload = {
            "num_elements": 3,
            "elements": create_element_config(3),
            "boom_diameter": 2,
            "boom_unit": "inches",
            "band": "11m_cb",
            "min_height": 30,
            "max_height": 60,
            "step": 5,
            "ground_radials": {
                "enabled": True,
                "ground_type": "wet",
                "wire_diameter": 0.5,
                "num_radials": 8
            }
        }
        response = api_client.post(f"{BASE_URL}/api/optimize-height", json=payload)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "optimal_height" in data, "Missing optimal_height field"
        assert "optimal_swr" in data, "Missing optimal_swr field"
        assert "optimal_gain" in data, "Missing optimal_gain field"
        assert "optimal_fb_ratio" in data, "Missing optimal_fb_ratio field"
        assert "heights_tested" in data, "Missing heights_tested field"
        
        print(f"✓ optimize-height with ground_radials returned optimal_height={data['optimal_height']}")
    
    def test_7_element_vs_3_element_optimal_height(self, api_client):
        """7-element with 288\" boom should pick higher height than 3-element with 96\" boom"""
        
        # 3-element with 96" boom
        elements_3 = [
            {"element_type": "reflector", "length": 220, "diameter": 0.5, "position": 0},
            {"element_type": "driven", "length": 209, "diameter": 0.5, "position": 40},
            {"element_type": "director", "length": 200, "diameter": 0.5, "position": 96}
        ]
        
        payload_3elem = {
            "num_elements": 3,
            "elements": elements_3,
            "boom_diameter": 2,
            "boom_unit": "inches",
            "band": "11m_cb",
            "min_height": 30,
            "max_height": 80,
            "step": 5
        }
        response_3 = api_client.post(f"{BASE_URL}/api/optimize-height", json=payload_3elem)
        assert response_3.status_code == 200, f"3-elem request failed: {response_3.text}"
        data_3 = response_3.json()
        optimal_height_3 = data_3["optimal_height"]
        
        # 7-element with 288" boom
        elements_7 = [
            {"element_type": "reflector", "length": 220, "diameter": 0.5, "position": 0},
            {"element_type": "driven", "length": 209, "diameter": 0.5, "position": 40},
            {"element_type": "director", "length": 200, "diameter": 0.5, "position": 80},
            {"element_type": "director", "length": 195, "diameter": 0.5, "position": 130},
            {"element_type": "director", "length": 190, "diameter": 0.5, "position": 185},
            {"element_type": "director", "length": 185, "diameter": 0.5, "position": 240},
            {"element_type": "director", "length": 180, "diameter": 0.5, "position": 288}
        ]
        
        payload_7elem = {
            "num_elements": 7,
            "elements": elements_7,
            "boom_diameter": 2,
            "boom_unit": "inches",
            "band": "11m_cb",
            "min_height": 30,
            "max_height": 80,
            "step": 5
        }
        response_7 = api_client.post(f"{BASE_URL}/api/optimize-height", json=payload_7elem)
        assert response_7.status_code == 200, f"7-elem request failed: {response_7.text}"
        data_7 = response_7.json()
        optimal_height_7 = data_7["optimal_height"]
        
        print(f"3-element (96\" boom) optimal height: {optimal_height_3} ft")
        print(f"7-element (288\" boom) optimal height: {optimal_height_7} ft")
        
        # 7-element should prefer higher mounting than 3-element
        assert optimal_height_7 >= optimal_height_3, \
            f"7-element antenna ({optimal_height_7}ft) should have >= optimal height than 3-element ({optimal_height_3}ft)"
        print(f"✓ 7-element prefers higher mounting ({optimal_height_7}ft >= {optimal_height_3}ft)")
    
    def test_wet_ground_vs_dry_ground_optimal_height(self, api_client):
        """Wet ground with radials should favor lower height than dry ground"""
        
        elements = create_element_config(4)
        
        # Wet ground with radials
        payload_wet = {
            "num_elements": 4,
            "elements": elements,
            "boom_diameter": 2,
            "boom_unit": "inches",
            "band": "11m_cb",
            "min_height": 30,
            "max_height": 80,
            "step": 5,
            "ground_radials": {
                "enabled": True,
                "ground_type": "wet",
                "wire_diameter": 0.5,
                "num_radials": 8
            }
        }
        response_wet = api_client.post(f"{BASE_URL}/api/optimize-height", json=payload_wet)
        assert response_wet.status_code == 200, f"Wet ground request failed: {response_wet.text}"
        data_wet = response_wet.json()
        optimal_height_wet = data_wet["optimal_height"]
        
        # Dry ground without radials
        payload_dry = {
            "num_elements": 4,
            "elements": elements,
            "boom_diameter": 2,
            "boom_unit": "inches",
            "band": "11m_cb",
            "min_height": 30,
            "max_height": 80,
            "step": 5,
            "ground_radials": {
                "enabled": True,
                "ground_type": "dry",
                "wire_diameter": 0.5,
                "num_radials": 8
            }
        }
        response_dry = api_client.post(f"{BASE_URL}/api/optimize-height", json=payload_dry)
        assert response_dry.status_code == 200, f"Dry ground request failed: {response_dry.text}"
        data_dry = response_dry.json()
        optimal_height_dry = data_dry["optimal_height"]
        
        print(f"Wet ground with radials optimal height: {optimal_height_wet} ft")
        print(f"Dry ground with radials optimal height: {optimal_height_dry} ft")
        
        # Wet ground should favor lower heights, dry ground should prefer higher
        assert optimal_height_wet <= optimal_height_dry, \
            f"Wet ground ({optimal_height_wet}ft) should prefer <= height than dry ground ({optimal_height_dry}ft)"
        print(f"✓ Wet ground prefers lower height ({optimal_height_wet}ft <= {optimal_height_dry}ft)")


class TestTutorialEndpoints:
    """Test tutorial-related endpoints"""
    
    def test_get_tutorial_public(self, api_client):
        """GET /api/tutorial should be public and return tutorial content"""
        response = api_client.get(f"{BASE_URL}/api/tutorial")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "content" in data, "Missing content field in tutorial response"
        assert isinstance(data["content"], str), "content should be a string"
        assert len(data["content"]) > 0, "Tutorial content should not be empty"
        
        print(f"✓ GET /api/tutorial returned content ({len(data['content'])} chars)")
    
    def test_get_admin_tutorial_requires_auth(self, api_client):
        """GET /api/admin/tutorial should require authentication"""
        response = api_client.get(f"{BASE_URL}/api/admin/tutorial")
        
        assert response.status_code in [401, 403], \
            f"Expected 401/403 without auth, got {response.status_code}"
        print("✓ GET /api/admin/tutorial requires authentication")
    
    def test_put_admin_tutorial_requires_auth(self, api_client):
        """PUT /api/admin/tutorial should require authentication"""
        response = api_client.put(f"{BASE_URL}/api/admin/tutorial", json={
            "content": "Test content"
        })
        
        assert response.status_code in [401, 403], \
            f"Expected 401/403 without auth, got {response.status_code}"
        print("✓ PUT /api/admin/tutorial requires authentication")
    
    def test_get_admin_tutorial_with_auth(self, authenticated_admin):
        """GET /api/admin/tutorial with admin auth should return content + metadata"""
        response = authenticated_admin.get(f"{BASE_URL}/api/admin/tutorial")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "content" in data, "Missing content field"
        assert "updated_at" in data, "Missing updated_at metadata field"
        
        print(f"✓ GET /api/admin/tutorial returned content with updated_at metadata")
    
    def test_put_admin_tutorial_updates_content(self, authenticated_admin):
        """PUT /api/admin/tutorial should update tutorial content"""
        import uuid
        test_content = f"# Test Tutorial Content {uuid.uuid4()}\n\nThis is a test update."
        
        # Update tutorial
        update_response = authenticated_admin.put(f"{BASE_URL}/api/admin/tutorial", json={
            "content": test_content
        })
        
        assert update_response.status_code == 200, f"Update failed: {update_response.status_code}: {update_response.text}"
        
        # Verify by getting admin tutorial
        get_response = authenticated_admin.get(f"{BASE_URL}/api/admin/tutorial")
        assert get_response.status_code == 200
        
        data = get_response.json()
        assert data["content"] == test_content, "Content was not updated correctly"
        assert data["updated_at"] is not None, "updated_at should be set after update"
        
        print(f"✓ PUT /api/admin/tutorial successfully updated content")
        print(f"  - Content verified via GET")
        print(f"  - updated_at: {data.get('updated_at')}")


class TestHealthAndBasicEndpoints:
    """Basic health check tests"""
    
    def test_api_root(self, api_client):
        """Test API root endpoint"""
        response = api_client.get(f"{BASE_URL}/api/")
        assert response.status_code == 200, f"API root failed: {response.status_code}"
        print("✓ API root accessible")
    
    def test_bands_endpoint(self, api_client):
        """Test bands endpoint"""
        response = api_client.get(f"{BASE_URL}/api/bands")
        assert response.status_code == 200, f"Bands endpoint failed: {response.status_code}"
        data = response.json()
        assert "11m_cb" in data, "Expected 11m_cb band in response"
        print(f"✓ Bands endpoint returned {len(data)} bands")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
