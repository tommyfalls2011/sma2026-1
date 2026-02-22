"""
Test PayPal Checkout Integration + other payment/admin endpoints
Tests: PayPal checkout, PayPal capture, Stripe checkout, manual upgrade (CashApp), 
       admin pending upgrades, health check, system notifications, railway status
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials
ADMIN_EMAIL = "fallstommy@gmail.com"
ADMIN_PASSWORD = "admin123"
TEST_USER_EMAIL = f"paypaltest_{uuid.uuid4().hex[:8]}@test.com"
TEST_USER_PASSWORD = "password123"
TEST_USER_NAME = "PayPal Test User"


@pytest.fixture(scope="module")
def admin_token():
    """Login as admin to get token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    if response.status_code != 200:
        pytest.skip(f"Admin login failed: {response.text}")
    return response.json()["token"]


@pytest.fixture(scope="module")
def test_user_token():
    """Register and login test user"""
    # Register new user
    reg_response = requests.post(
        f"{BASE_URL}/api/auth/register",
        json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD,
            "name": TEST_USER_NAME
        }
    )
    # If already exists, try login
    if reg_response.status_code == 400:
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
        )
        if login_response.status_code != 200:
            pytest.skip(f"Test user login failed: {login_response.text}")
        return login_response.json()["token"]
    
    if reg_response.status_code != 200:
        pytest.skip(f"Test user registration failed: {reg_response.text}")
    return reg_response.json()["token"]


class TestHealthCheck:
    """Test health check endpoint"""
    
    def test_health_endpoint(self):
        """GET /api/health - check API and database status"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        
        assert data["api"] == "up"
        assert data["database"] == "up"
        assert "overall" in data
        assert "checked_at" in data
        print(f"✓ Health check passed: api={data['api']}, db={data['database']}, overall={data['overall']}")


class TestPayPalCheckout:
    """Test PayPal checkout flow"""
    
    def test_paypal_checkout_creates_order(self, test_user_token):
        """POST /api/subscription/paypal-checkout - creates real PayPal order with approval URL"""
        response = requests.post(
            f"{BASE_URL}/api/subscription/paypal-checkout",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={
                "tier": "bronze_monthly",
                "origin_url": "https://element-tuner.preview.emergentagent.com"
            }
        )
        
        assert response.status_code == 200, f"PayPal checkout failed: {response.text}"
        data = response.json()
        
        # Verify response contains PayPal order ID and approval URL
        assert "order_id" in data, "Response should contain PayPal order_id"
        assert "url" in data, "Response should contain approval URL"
        assert data["url"].startswith("https://www.paypal.com/"), f"URL should be PayPal URL, got: {data['url']}"
        
        print(f"✓ PayPal checkout created order: {data['order_id']}")
        print(f"✓ Approval URL: {data['url'][:80]}...")
        
        return data["order_id"]
    
    def test_paypal_checkout_requires_auth(self):
        """POST /api/subscription/paypal-checkout - requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/subscription/paypal-checkout",
            json={"tier": "bronze_monthly", "origin_url": "https://example.com"}
        )
        assert response.status_code in [401, 403], "Should require authentication"
        print("✓ PayPal checkout correctly requires authentication")
    
    def test_paypal_checkout_invalid_tier(self, test_user_token):
        """POST /api/subscription/paypal-checkout - rejects invalid tier"""
        response = requests.post(
            f"{BASE_URL}/api/subscription/paypal-checkout",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={"tier": "invalid_tier", "origin_url": "https://example.com"}
        )
        assert response.status_code == 400
        print("✓ PayPal checkout correctly rejects invalid tier")


class TestPayPalCapture:
    """Test PayPal capture endpoint"""
    
    def test_paypal_capture_unapproved_order(self, test_user_token):
        """POST /api/subscription/paypal-capture/{order_id} - returns error for unapproved order"""
        # First create an order
        checkout_response = requests.post(
            f"{BASE_URL}/api/subscription/paypal-checkout",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={
                "tier": "silver_monthly",
                "origin_url": "https://element-tuner.preview.emergentagent.com"
            }
        )
        
        if checkout_response.status_code != 200:
            pytest.skip("Could not create PayPal order for capture test")
        
        order_id = checkout_response.json()["order_id"]
        
        # Try to capture without user approval (should fail gracefully)
        capture_response = requests.post(
            f"{BASE_URL}/api/subscription/paypal-capture/{order_id}",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        
        # Should return 200 but with success=False (order not approved yet)
        assert capture_response.status_code == 200, f"Capture endpoint error: {capture_response.text}"
        data = capture_response.json()
        
        # Payment not completed because user hasn't approved on PayPal
        assert data.get("success") == False or data.get("status") != "COMPLETED"
        print(f"✓ PayPal capture correctly handles unapproved order: {data}")
    
    def test_paypal_capture_requires_auth(self):
        """POST /api/subscription/paypal-capture/{order_id} - requires authentication"""
        response = requests.post(f"{BASE_URL}/api/subscription/paypal-capture/fake_order_id")
        assert response.status_code in [401, 403], "Should require authentication"
        print("✓ PayPal capture correctly requires authentication")


class TestStripeCheckout:
    """Test Stripe checkout still works"""
    
    def test_stripe_checkout_creates_session(self, test_user_token):
        """POST /api/subscription/stripe-checkout - creates Stripe checkout session"""
        response = requests.post(
            f"{BASE_URL}/api/subscription/stripe-checkout",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={
                "tier": "bronze_monthly",
                "origin_url": "https://element-tuner.preview.emergentagent.com"
            }
        )
        
        assert response.status_code == 200, f"Stripe checkout failed: {response.text}"
        data = response.json()
        
        assert "url" in data, "Response should contain checkout URL"
        assert "session_id" in data, "Response should contain session_id"
        assert "checkout.stripe.com" in data["url"] or "stripe" in data["url"].lower(), f"URL should be Stripe URL"
        
        print(f"✓ Stripe checkout session created: {data['session_id'][:20]}...")
        print(f"✓ Checkout URL: {data['url'][:60]}...")


class TestManualUpgrade:
    """Test manual upgrade (CashApp) - creates pending request"""
    
    def test_cashapp_creates_pending_request(self, test_user_token):
        """POST /api/subscription/upgrade - creates pending request for manual payment"""
        response = requests.post(
            f"{BASE_URL}/api/subscription/upgrade",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={
                "tier": "bronze_monthly",
                "payment_method": "cashapp",
                "payment_reference": "TEST_PAYMENT_REF_123"
            }
        )
        
        assert response.status_code == 200, f"Manual upgrade failed: {response.text}"
        data = response.json()
        
        assert data["success"] == True
        assert data["status"] == "pending"
        assert "request_id" in data
        
        print(f"✓ CashApp pending request created: {data['request_id']}")
        return data["request_id"]


class TestAdminPendingUpgrades:
    """Test admin pending upgrades endpoint"""
    
    def test_get_pending_upgrades(self, admin_token):
        """GET /api/admin/pending-upgrades - admin can view all pending requests"""
        response = requests.get(
            f"{BASE_URL}/api/admin/pending-upgrades",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200, f"Get pending upgrades failed: {response.text}"
        data = response.json()
        
        assert "upgrades" in data
        assert isinstance(data["upgrades"], list)
        
        print(f"✓ Admin can view pending upgrades: {len(data['upgrades'])} pending requests")
    
    def test_pending_upgrades_requires_admin(self, test_user_token):
        """GET /api/admin/pending-upgrades - requires admin access"""
        response = requests.get(
            f"{BASE_URL}/api/admin/pending-upgrades",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code in [401, 403], "Should require admin access"
        print("✓ Pending upgrades correctly requires admin access")


class TestSystemNotifications:
    """Test system notification endpoints"""
    
    def test_get_public_notification(self):
        """GET /api/system-notification - public endpoint"""
        response = requests.get(f"{BASE_URL}/api/system-notification")
        assert response.status_code == 200
        data = response.json()
        assert "notification" in data
        print(f"✓ Public system notification endpoint works: notification={data['notification']}")
    
    def test_create_system_notification(self, admin_token):
        """POST /api/admin/system-notification - admin can create notification"""
        response = requests.post(
            f"{BASE_URL}/api/admin/system-notification",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"message": "Test notification from pytest", "type": "info"}
        )
        
        assert response.status_code == 200, f"Create notification failed: {response.text}"
        data = response.json()
        assert data["success"] == True
        print("✓ Admin can create system notification")
    
    def test_delete_system_notification(self, admin_token):
        """DELETE /api/admin/system-notification - admin can clear notification"""
        response = requests.delete(
            f"{BASE_URL}/api/admin/system-notification",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200, f"Delete notification failed: {response.text}"
        data = response.json()
        assert data["success"] == True
        print("✓ Admin can clear system notification")


class TestRailwayStatus:
    """Test Railway redeploy status endpoint"""
    
    def test_railway_status(self, admin_token):
        """GET /api/admin/railway/status - admin can check deployment status"""
        response = requests.get(
            f"{BASE_URL}/api/admin/railway/status",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200, f"Railway status failed: {response.text}"
        data = response.json()
        
        # Should indicate whether Railway is configured or not
        assert "configured" in data
        print(f"✓ Railway status endpoint works: configured={data.get('configured')}")


class TestSubscriptionTiers:
    """Test subscription tier information"""
    
    def test_get_tiers(self):
        """GET /api/subscription/tiers - returns available subscription tiers"""
        response = requests.get(f"{BASE_URL}/api/subscription/tiers")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "tiers" in data
        assert "payment_methods" in data
        
        tiers = data["tiers"]
        expected_tiers = ["bronze_monthly", "bronze_yearly", "silver_monthly", "silver_yearly", "gold_monthly", "gold_yearly"]
        
        for tier in expected_tiers:
            assert tier in tiers, f"Missing tier: {tier}"
        
        print(f"✓ Subscription tiers available: {list(tiers.keys())}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
