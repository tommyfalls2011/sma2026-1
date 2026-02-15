"""
Tests for refactored SMA Antenna Calculator API
Testing: modular backend routes after refactoring from monolithic server.py
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://pdf-download-feature.preview.emergentagent.com').rstrip('/')

# Test user credentials
TEST_USER_EMAIL = f"TEST_refactor_{uuid.uuid4().hex[:8]}@example.com"
TEST_USER_PASSWORD = "testpass123"
TEST_USER_NAME = "Test Refactor User"


class TestPublicEndpoints:
    """Test public routes: /, bands, subscription/tiers, tutorial, designer-info"""

    def test_root_endpoint(self):
        """GET /api/ - should return 'Antenna Calculator API'"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "message" in data
        assert data["message"] == "Antenna Calculator API"
        print(f"✓ Root endpoint: {data['message']}")

    def test_bands_endpoint(self):
        """GET /api/bands - should return 9 band definitions"""
        response = requests.get(f"{BASE_URL}/api/bands")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        expected_bands = ["17m", "15m", "12m", "11m_cb", "10m", "6m", "2m", "1.25m", "70cm"]
        assert len(data) == 9, f"Expected 9 bands, got {len(data)}"
        for band in expected_bands:
            assert band in data, f"Missing band: {band}"
        print(f"✓ Bands endpoint: {len(data)} bands returned")

    def test_subscription_tiers_endpoint(self):
        """GET /api/subscription/tiers - should return subscription tier list"""
        response = requests.get(f"{BASE_URL}/api/subscription/tiers")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "tiers" in data
        tiers = data["tiers"]
        expected_tiers = ["trial", "bronze_monthly", "bronze_yearly", "silver_monthly", "silver_yearly", "gold_monthly", "gold_yearly"]
        for tier in expected_tiers:
            assert tier in tiers, f"Missing tier: {tier}"
        # Verify tier structure
        assert tiers["trial"]["max_elements"] == 3
        assert "payment_methods" in data
        print(f"✓ Subscription tiers: {len(tiers)} tiers returned")

    def test_tutorial_endpoint(self):
        """GET /api/tutorial - should return tutorial content"""
        response = requests.get(f"{BASE_URL}/api/tutorial")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "content" in data
        assert len(data["content"]) > 100, "Tutorial content seems too short"
        print(f"✓ Tutorial endpoint: {len(data['content'])} chars of content")

    def test_designer_info_endpoint(self):
        """GET /api/designer-info - should return designer info"""
        response = requests.get(f"{BASE_URL}/api/designer-info")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "content" in data
        assert "Tommy Falls" in data["content"]
        print(f"✓ Designer info endpoint: {len(data['content'])} chars of content")


class TestAntennaCalculation:
    """Test antenna calculation routes"""

    def test_auto_tune_5_element(self):
        """POST /api/auto-tune - should return optimized element dimensions"""
        payload = {
            "num_elements": 5,
            "height_from_ground": 35,
            "height_unit": "ft",
            "boom_diameter": 2,
            "boom_unit": "inches",
            "band": "11m_cb",
            "frequency_mhz": 27.185,
            "use_reflector": True,
            "boom_lock_enabled": False,
            "spacing_mode": "normal",
            "spacing_level": 1.0
        }
        response = requests.post(f"{BASE_URL}/api/auto-tune", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "optimized_elements" in data
        assert "predicted_swr" in data
        assert "predicted_gain" in data
        assert "predicted_fb_ratio" in data
        assert "optimization_notes" in data
        
        # Verify 5 elements returned (reflector + driven + 3 directors)
        elements = data["optimized_elements"]
        assert len(elements) == 5, f"Expected 5 elements, got {len(elements)}"
        
        # Verify element types
        types = [e["element_type"] for e in elements]
        assert "reflector" in types
        assert "driven" in types
        assert types.count("director") == 3
        
        # Verify reasonable values
        assert 1.0 <= data["predicted_swr"] <= 2.5, f"SWR out of range: {data['predicted_swr']}"
        assert data["predicted_gain"] >= 8.0, f"Gain too low: {data['predicted_gain']}"
        
        print(f"✓ Auto-tune: {len(elements)} elements, SWR={data['predicted_swr']}, Gain={data['predicted_gain']} dBi")

    def test_calculate_full_antenna(self):
        """POST /api/calculate - should return full antenna calculation results"""
        # First get auto-tuned elements
        auto_tune_payload = {
            "num_elements": 5,
            "height_from_ground": 35,
            "height_unit": "ft",
            "boom_diameter": 2,
            "boom_unit": "inches",
            "band": "11m_cb",
            "frequency_mhz": 27.185,
            "use_reflector": True,
            "boom_lock_enabled": False,
            "spacing_mode": "normal",
            "spacing_level": 1.0
        }
        auto_tune_resp = requests.post(f"{BASE_URL}/api/auto-tune", json=auto_tune_payload)
        assert auto_tune_resp.status_code == 200
        auto_tune_data = auto_tune_resp.json()
        elements = auto_tune_data["optimized_elements"]
        
        # Use auto-tuned elements for calculation
        calc_payload = {
            "num_elements": 5,
            "elements": elements,
            "height_from_ground": 35,
            "height_unit": "ft",
            "boom_diameter": 2,
            "boom_unit": "inches",
            "band": "11m_cb",
            "frequency_mhz": 27.185,
            "antenna_orientation": "horizontal",
            "feed_type": "gamma"
        }
        response = requests.post(f"{BASE_URL}/api/calculate", json=calc_payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify key metrics are present
        assert "swr" in data
        assert "gain_dbi" in data
        assert "fb_ratio" in data
        assert "beamwidth_h" in data
        assert "beamwidth_v" in data
        assert "takeoff_angle" in data
        assert "far_field_pattern" in data
        assert "swr_curve" in data
        
        # Verify reasonable values
        assert 1.0 <= data["swr"] <= 3.0, f"SWR out of range: {data['swr']}"
        assert data["gain_dbi"] >= 8.0, f"Gain too low: {data['gain_dbi']}"
        assert data["fb_ratio"] >= 15.0, f"F/B ratio too low: {data['fb_ratio']}"
        assert 0 < data["takeoff_angle"] <= 90, f"Takeoff angle invalid: {data['takeoff_angle']}"
        
        # Verify far field pattern has data
        assert len(data["far_field_pattern"]) > 0
        assert len(data["swr_curve"]) > 0
        
        print(f"✓ Calculate: SWR={data['swr']}, Gain={data['gain_dbi']} dBi, F/B={data['fb_ratio']} dB, Takeoff={data['takeoff_angle']}°")
        return data


class TestAuthEndpoints:
    """Test authentication routes"""
    
    def test_register_new_user(self):
        """POST /api/auth/register - should register a new user"""
        payload = {
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD,
            "name": TEST_USER_NAME
        }
        response = requests.post(f"{BASE_URL}/api/auth/register", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == TEST_USER_EMAIL.lower()
        assert data["user"]["name"] == TEST_USER_NAME
        assert data["user"]["subscription_tier"] == "trial"
        assert data["user"]["is_trial"] == True
        
        print(f"✓ Register: User {data['user']['email']} registered with {data['user']['subscription_tier']} tier")
        return data["token"]

    def test_register_duplicate_email(self):
        """POST /api/auth/register - should reject duplicate email"""
        payload = {
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD,
            "name": "Duplicate User"
        }
        response = requests.post(f"{BASE_URL}/api/auth/register", json=payload)
        assert response.status_code == 400, f"Expected 400 for duplicate, got {response.status_code}"
        print(f"✓ Register duplicate: Correctly rejected with 400")

    def test_login_user(self):
        """POST /api/auth/login - should authenticate user"""
        payload = {
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        }
        response = requests.post(f"{BASE_URL}/api/auth/login", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == TEST_USER_EMAIL.lower()
        assert "is_active" in data["user"]
        
        print(f"✓ Login: User {data['user']['email']} logged in, active={data['user']['is_active']}")
        return data["token"]

    def test_login_invalid_credentials(self):
        """POST /api/auth/login - should reject invalid credentials"""
        payload = {
            "email": TEST_USER_EMAIL,
            "password": "wrongpassword"
        }
        response = requests.post(f"{BASE_URL}/api/auth/login", json=payload)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print(f"✓ Login invalid: Correctly rejected with 401")

    def test_get_current_user(self):
        """GET /api/auth/me - should return current user info"""
        # First login
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        token = login_resp.json()["token"]
        
        # Get user info
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert data["email"] == TEST_USER_EMAIL.lower()
        assert "subscription_tier" in data
        assert "max_elements" in data
        
        print(f"✓ Get me: {data['email']}, tier={data['subscription_tier']}, max_elements={data['max_elements']}")


class TestUserRoutes:
    """Test user routes: subscription, designs"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get token before each test"""
        # Try to login, if fails, register first
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        if login_resp.status_code != 200:
            # Register the user
            requests.post(f"{BASE_URL}/api/auth/register", json={
                "email": TEST_USER_EMAIL,
                "password": TEST_USER_PASSWORD,
                "name": TEST_USER_NAME
            })
            login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
                "email": TEST_USER_EMAIL,
                "password": TEST_USER_PASSWORD
            })
        
        self.token = login_resp.json().get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def test_get_subscription_status(self):
        """GET /api/subscription/status - should return subscription status"""
        response = requests.get(f"{BASE_URL}/api/subscription/status", headers=self.headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert "is_active" in data
        assert "tier" in data
        assert "max_elements" in data
        
        print(f"✓ Subscription status: tier={data['tier']}, active={data['is_active']}, max_elements={data['max_elements']}")


class TestCalculationHistory:
    """Test calculation history routes"""

    def test_get_history(self):
        """GET /api/history - should return calculation history"""
        response = requests.get(f"{BASE_URL}/api/history")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        # Should be a list
        assert isinstance(data, list), "History should be a list"
        
        if len(data) > 0:
            # Verify structure of first record
            record = data[0]
            assert "id" in record
            assert "timestamp" in record
            assert "inputs" in record
            assert "outputs" in record
        
        print(f"✓ History: {len(data)} records returned")


class TestAppUpdate:
    """Test app update routes"""

    def test_get_app_update(self):
        """GET /api/app-update - should return app update info"""
        response = requests.get(f"{BASE_URL}/api/app-update")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert "version" in data
        assert "releaseNotes" in data or "release_notes" in data
        
        print(f"✓ App update: version={data.get('version')}")


class TestChangelog:
    """Test changelog routes"""

    def test_get_changelog(self):
        """GET /api/changelog - should return changelog"""
        response = requests.get(f"{BASE_URL}/api/changelog")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert "changes" in data
        
        print(f"✓ Changelog: {len(data.get('changes', []))} entries")


# Cleanup fixture to delete test user after all tests
@pytest.fixture(scope="session", autouse=True)
def cleanup_test_data():
    """Cleanup test data after all tests"""
    yield
    # Try to get admin token and delete test user
    admin_login = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "fallstommy@gmail.com",
        "password": "admin123"
    })
    if admin_login.status_code == 200:
        admin_token = admin_login.json()["token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get all users and find our test user
        users_resp = requests.get(f"{BASE_URL}/api/admin/users", headers=admin_headers)
        if users_resp.status_code == 200:
            for user in users_resp.json():
                if user["email"].startswith("test_refactor_"):
                    requests.delete(f"{BASE_URL}/api/admin/users/{user['id']}", headers=admin_headers)
                    print(f"🧹 Cleaned up test user: {user['email']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
