"""
Comprehensive backend tests for the refactored Swing Master Amps antenna calculator & store API.
Tests all major endpoints across the modular routers.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://element-nudge-demo.preview.emergentagent.com')

# Test credentials
ADMIN_EMAIL = "fallstommy@gmail.com"
ADMIN_PASSWORD = "admin123"


class TestPublicEndpoints:
    """Test public endpoints (no auth required) - /api/public.py"""
    
    def test_01_root_endpoint(self):
        """GET /api/ returns welcome message"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Antenna Calculator API" in data["message"]
        print(f"✓ Root endpoint returns: {data['message']}")
    
    def test_02_get_bands_returns_9_bands(self):
        """GET /api/bands returns 9 frequency bands"""
        response = requests.get(f"{BASE_URL}/api/bands")
        assert response.status_code == 200
        data = response.json()
        # Should have 9 bands: 17m, 15m, 12m, 11m_cb, 10m, 6m, 2m, 1.25m, 70cm
        assert len(data) == 9
        expected_bands = ["17m", "15m", "12m", "11m_cb", "10m", "6m", "2m", "1.25m", "70cm"]
        for band in expected_bands:
            assert band in data
            assert "name" in data[band]
            assert "center" in data[band]
            assert "start" in data[band]
            assert "end" in data[band]
        print(f"✓ Bands endpoint returns {len(data)} bands: {list(data.keys())}")
    
    def test_03_get_subscription_tiers_returns_8_plus_tiers(self):
        """GET /api/subscription/tiers returns 8+ tiers"""
        response = requests.get(f"{BASE_URL}/api/subscription/tiers")
        assert response.status_code == 200
        data = response.json()
        assert "tiers" in data
        assert "payment_methods" in data
        tiers = data["tiers"]
        # Should have at least 8 tiers (trial, bronze_monthly, bronze_yearly, etc.)
        assert len(tiers) >= 8
        # Verify key tiers exist
        expected_tiers = ["trial", "bronze_monthly", "bronze_yearly", "silver_monthly", 
                         "silver_yearly", "gold_monthly", "gold_yearly", "subadmin"]
        for tier in expected_tiers:
            assert tier in tiers, f"Missing tier: {tier}"
        print(f"✓ Subscription tiers endpoint returns {len(tiers)} tiers")


class TestAuthEndpoints:
    """Test authentication endpoints - /api/user.py"""
    
    def test_04_admin_login_success(self):
        """POST /api/auth/login - admin login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == ADMIN_EMAIL
        assert data["user"]["subscription_tier"] == "admin"
        assert data["user"]["is_active"] == True
        print(f"✓ Admin login successful, tier: {data['user']['subscription_tier']}")
    
    def test_05_login_invalid_credentials(self):
        """POST /api/auth/login - invalid credentials returns 401"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "wrong@example.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401
        print("✓ Invalid credentials correctly rejected with 401")
    
    def test_06_get_current_user_with_token(self):
        """GET /api/auth/me - returns authenticated user info"""
        # First login
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        token = login_resp.json()["token"]
        
        # Get user info
        response = requests.get(f"{BASE_URL}/api/auth/me", 
                               headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == ADMIN_EMAIL
        assert "subscription_tier" in data
        assert "tier_info" in data
        assert "max_elements" in data
        print(f"✓ Auth/me returns user with max_elements: {data['max_elements']}")
    
    def test_07_auth_me_without_token_returns_401(self):
        """GET /api/auth/me - without token returns 401"""
        response = requests.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 401
        print("✓ Auth/me without token correctly returns 401")


class TestAntennaEndpoints:
    """Test antenna calculation endpoints - /api/antenna.py"""
    
    def test_08_auto_tune_3_elements(self):
        """POST /api/auto-tune - calculates optimal antenna"""
        response = requests.post(f"{BASE_URL}/api/auto-tune", json={
            "num_elements": 3,
            "height_from_ground": 54,
            "height_unit": "ft",
            "boom_diameter": 2,
            "boom_unit": "inches",
            "band": "11m_cb"
        })
        assert response.status_code == 200
        data = response.json()
        assert "optimized_elements" in data
        assert len(data["optimized_elements"]) == 3
        assert "predicted_swr" in data
        assert "predicted_gain" in data
        assert "predicted_fb_ratio" in data
        assert "optimization_notes" in data
        # Verify predicted values are reasonable
        assert data["predicted_swr"] < 2.0
        assert data["predicted_gain"] > 8.0
        print(f"✓ Auto-tune: SWR={data['predicted_swr']}, Gain={data['predicted_gain']} dBi")
    
    def test_09_calculate_antenna(self):
        """POST /api/calculate - calculates antenna parameters"""
        response = requests.post(f"{BASE_URL}/api/calculate", json={
            "num_elements": 3,
            "elements": [
                {"element_type": "reflector", "length": 213.2, "diameter": 0.5, "position": 0},
                {"element_type": "driven", "length": 203.5, "diameter": 0.5, "position": 48.3},
                {"element_type": "director", "length": 193.6, "diameter": 0.5, "position": 138}
            ],
            "height_from_ground": 54,
            "height_unit": "ft",
            "boom_diameter": 2,
            "boom_unit": "inches",
            "band": "11m_cb"
        })
        assert response.status_code == 200
        data = response.json()
        # Verify all expected fields
        expected_fields = ["swr", "gain_dbi", "fb_ratio", "beamwidth_h", "beamwidth_v", 
                          "bandwidth", "far_field_pattern", "swr_curve", "band_info"]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"
        # Verify reasonable values
        assert data["swr"] < 2.0
        assert data["gain_dbi"] > 8.0
        assert len(data["far_field_pattern"]) > 0
        print(f"✓ Calculate: SWR={data['swr']}, Gain={data['gain_dbi']} dBi, FB={data['fb_ratio']} dB")


class TestAdminEndpoints:
    """Test admin endpoints - /api/admin.py"""
    
    @pytest.fixture(autouse=True)
    def setup_admin_token(self):
        """Get admin token for authenticated tests"""
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        self.admin_token = login_resp.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.admin_token}"}
    
    def test_10_admin_check(self):
        """GET /api/admin/check - returns admin status"""
        response = requests.get(f"{BASE_URL}/api/admin/check", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert data["is_admin"] == True
        assert data["can_edit_settings"] == True
        assert data["has_full_access"] == True
        print(f"✓ Admin check: is_admin={data['is_admin']}, can_edit={data['can_edit_settings']}")
    
    def test_11_admin_get_users(self):
        """GET /api/admin/users - returns all users"""
        response = requests.get(f"{BASE_URL}/api/admin/users", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        # Verify user structure
        user = data[0]
        assert "id" in user
        assert "email" in user
        assert "subscription_tier" in user
        print(f"✓ Admin users: found {len(data)} users")
    
    def test_12_admin_get_pricing(self):
        """GET /api/admin/pricing - returns pricing config"""
        response = requests.get(f"{BASE_URL}/api/admin/pricing", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert "bronze" in data
        assert "silver" in data
        assert "gold" in data
        assert "payment" in data
        # Verify pricing structure
        assert "monthly_price" in data["bronze"]
        assert "yearly_price" in data["bronze"]
        print(f"✓ Admin pricing: Bronze=${data['bronze']['monthly_price']}/mo, Gold=${data['gold']['monthly_price']}/mo")
    
    def test_13_admin_endpoints_require_auth(self):
        """Admin endpoints require authentication"""
        endpoints = ["/api/admin/users", "/api/admin/pricing", "/api/admin/discounts"]
        for endpoint in endpoints:
            response = requests.get(f"{BASE_URL}{endpoint}")
            assert response.status_code == 401, f"{endpoint} should require auth"
        print("✓ All admin endpoints correctly require authentication")


class TestStoreEndpoints:
    """Test e-commerce store endpoints - /api/store.py"""
    
    def test_14_store_products_returns_3_products(self):
        """GET /api/store/products - returns products"""
        response = requests.get(f"{BASE_URL}/api/store/products")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 3  # 2-pill, 4-pill, 6-pill amplifiers
        # Verify product structure
        product = data[0]
        assert "id" in product
        assert "name" in product
        assert "price" in product
        assert "in_stock" in product
        print(f"✓ Store products: found {len(data)} products")
    
    def test_15_store_latest_apk(self):
        """GET /api/store/latest-apk - returns APK info"""
        response = requests.get(f"{BASE_URL}/api/store/latest-apk")
        assert response.status_code == 200
        data = response.json()
        # May have version or error
        if "version" in data:
            assert "download_url" in data
            assert "filename" in data
            print(f"✓ Latest APK: version={data['version']}, size={data.get('size_mb', 'N/A')} MB")
        else:
            print(f"✓ Latest APK: {data.get('error', 'No release info')}")
    
    def test_16_store_login(self):
        """POST /api/store/login - store login"""
        response = requests.post(f"{BASE_URL}/api/store/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["is_admin"] == True
        print(f"✓ Store login: admin={data['user']['is_admin']}")
    
    def test_17_store_login_invalid(self):
        """POST /api/store/login - invalid credentials"""
        response = requests.post(f"{BASE_URL}/api/store/login", json={
            "email": "wrong@example.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401
        print("✓ Store invalid login correctly returns 401")
    
    def test_18_store_admin_orders(self):
        """GET /api/store/admin/orders - returns orders (requires store admin)"""
        # First login to store
        login_resp = requests.post(f"{BASE_URL}/api/store/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        token = login_resp.json()["token"]
        
        # Get orders
        response = requests.get(f"{BASE_URL}/api/store/admin/orders",
                               headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Store admin orders: found {len(data)} orders")


class TestUserRegistration:
    """Test user registration flow - /api/user.py"""
    
    def test_19_register_new_user(self):
        """POST /api/auth/register - registers new user"""
        import uuid
        test_email = f"test_{uuid.uuid4().hex[:8]}@test.com"
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": test_email,
            "password": "testpass123",
            "name": "Test User"
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == test_email
        assert data["user"]["subscription_tier"] == "trial"
        assert data["user"]["is_trial"] == True
        print(f"✓ User registration: email={test_email}, tier={data['user']['subscription_tier']}")
    
    def test_20_register_duplicate_email_fails(self):
        """POST /api/auth/register - duplicate email returns 400"""
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": ADMIN_EMAIL,  # Already exists
            "password": "testpass123",
            "name": "Duplicate User"
        })
        assert response.status_code == 400
        print("✓ Duplicate registration correctly returns 400")


class TestSubscriptionEndpoints:
    """Test subscription endpoints - /api/user.py"""
    
    @pytest.fixture(autouse=True)
    def setup_user_token(self):
        """Get user token for authenticated tests"""
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        self.token = login_resp.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_21_get_subscription_status(self):
        """GET /api/subscription/status - returns user subscription status"""
        response = requests.get(f"{BASE_URL}/api/subscription/status", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert "is_active" in data
        assert "tier" in data
        assert "max_elements" in data
        print(f"✓ Subscription status: tier={data['tier']}, active={data['is_active']}")


class TestPublicContentEndpoints:
    """Test public content endpoints - /api/public.py"""
    
    def test_22_get_tutorial(self):
        """GET /api/tutorial - returns tutorial content"""
        response = requests.get(f"{BASE_URL}/api/tutorial")
        assert response.status_code == 200
        data = response.json()
        assert "content" in data
        assert len(data["content"]) > 10  # Content can be any length
        print(f"✓ Tutorial content: {len(data['content'])} chars")
    
    def test_23_get_designer_info(self):
        """GET /api/designer-info - returns designer info"""
        response = requests.get(f"{BASE_URL}/api/designer-info")
        assert response.status_code == 200
        data = response.json()
        assert "content" in data
        assert "Tommy Falls" in data["content"]  # Designer name should be in content
        print(f"✓ Designer info: {len(data['content'])} chars")
    
    def test_24_get_app_update(self):
        """GET /api/app-update - returns app update info"""
        response = requests.get(f"{BASE_URL}/api/app-update")
        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        print(f"✓ App update: version={data['version']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
