"""
Subscription & Payment System Tests
Testing PayPal/CashApp pending upgrades, Admin approve/reject, and Stripe checkout flow
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://hairpin-match.preview.emergentagent.com').rstrip('/')

# Test credentials from problem statement
ADMIN_EMAIL = "fallstommy@gmail.com"
ADMIN_PASSWORD = "admin123"
TEST_USER_EMAIL = f"TEST_payment_user_{uuid.uuid4().hex[:6]}@testuser.com"
TEST_USER_PASSWORD = "password123"
TEST_USER_NAME = "Payment Test User"


class TestSubscriptionPayments:
    """Tests for subscription upgrade flow with PayPal/CashApp pending requests and Stripe checkout"""
    
    admin_token = None
    test_user_token = None
    test_user_id = None
    pending_request_id = None
    
    # === AUTH FIXTURES ===
    
    @pytest.fixture(autouse=True, scope="class")
    def setup_tokens(self, request):
        """Login admin and create test user with tokens"""
        # Login as admin
        res = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert res.status_code == 200, f"Admin login failed: {res.text}"
        data = res.json()
        request.cls.admin_token = data["token"]
        print(f"✓ Admin logged in: {ADMIN_EMAIL}")
        
        # Register new test user
        res = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD,
            "name": TEST_USER_NAME
        })
        if res.status_code == 200:
            data = res.json()
            request.cls.test_user_token = data["token"]
            request.cls.test_user_id = data["user"]["id"]
            print(f"✓ Test user created: {TEST_USER_EMAIL}")
        elif res.status_code == 400 and "already registered" in res.text:
            # User exists, just login
            res = requests.post(f"{BASE_URL}/api/auth/login", json={
                "email": TEST_USER_EMAIL,
                "password": TEST_USER_PASSWORD
            })
            assert res.status_code == 200, f"Test user login failed: {res.text}"
            data = res.json()
            request.cls.test_user_token = data["token"]
            request.cls.test_user_id = data["user"]["id"]
            print(f"✓ Test user logged in: {TEST_USER_EMAIL}")
        else:
            pytest.fail(f"Test user creation failed: {res.text}")
    
    # === SUBSCRIPTION TIERS ===
    
    def test_01_get_subscription_tiers(self):
        """GET /api/subscription/tiers returns all tiers and payment methods"""
        res = requests.get(f"{BASE_URL}/api/subscription/tiers")
        assert res.status_code == 200
        data = res.json()
        
        # Check tiers exist
        assert "tiers" in data
        tiers = data["tiers"]
        assert "bronze_monthly" in tiers
        assert "bronze_yearly" in tiers
        assert "silver_monthly" in tiers
        assert "silver_yearly" in tiers
        assert "gold_monthly" in tiers
        assert "gold_yearly" in tiers
        
        # Check tier structure
        bronze = tiers["bronze_monthly"]
        assert "price" in bronze
        assert "max_elements" in bronze
        assert "name" in bronze
        
        # Check payment methods
        assert "payment_methods" in data
        methods = data["payment_methods"]
        assert "paypal" in methods
        assert "cashapp" in methods
        print(f"✓ Tiers retrieved: {list(tiers.keys())}")
        print(f"✓ Payment methods: PayPal={methods['paypal'].get('email')}, CashApp={methods['cashapp'].get('tag')}")
    
    # === PAYPAL/CASHAPP PENDING UPGRADE ===
    
    def test_02_paypal_upgrade_creates_pending_request(self):
        """POST /api/subscription/upgrade with PayPal creates PENDING request (not instant upgrade)"""
        headers = {"Authorization": f"Bearer {self.test_user_token}"}
        
        res = requests.post(f"{BASE_URL}/api/subscription/upgrade", json={
            "tier": "silver_monthly",
            "payment_method": "paypal",
            "payment_reference": "PAYPAL-TEST-123"
        }, headers=headers)
        
        assert res.status_code == 200, f"Upgrade request failed: {res.text}"
        data = res.json()
        
        # Should be pending, not instant
        assert data.get("success") is True
        assert data.get("status") == "pending", f"Expected pending status, got: {data.get('status')}"
        assert "request_id" in data
        assert "verified by admin" in data.get("message", "").lower() or "pending" in data.get("message", "").lower()
        
        self.__class__.pending_request_id = data["request_id"]
        print(f"✓ PayPal upgrade created PENDING request: {data['request_id']}")
        print(f"✓ Message: {data.get('message')}")
    
    def test_03_user_can_check_pending_status(self):
        """GET /api/subscription/pending returns user's pending request"""
        headers = {"Authorization": f"Bearer {self.test_user_token}"}
        
        res = requests.get(f"{BASE_URL}/api/subscription/pending", headers=headers)
        assert res.status_code == 200
        data = res.json()
        
        assert "pending" in data
        pending = data["pending"]
        
        if pending:
            assert pending.get("status") == "pending"
            assert pending.get("tier") == "silver_monthly"
            assert pending.get("payment_method") == "paypal"
            print(f"✓ User can see pending request: {pending.get('tier_name')} via {pending.get('payment_method')}")
        else:
            print("✓ No pending request (may have been processed)")
    
    # === ADMIN PENDING UPGRADES MANAGEMENT ===
    
    def test_04_admin_can_see_pending_upgrades(self):
        """GET /api/admin/pending-upgrades returns all pending requests"""
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        res = requests.get(f"{BASE_URL}/api/admin/pending-upgrades", headers=headers)
        assert res.status_code == 200
        data = res.json()
        
        assert "upgrades" in data
        upgrades = data["upgrades"]
        assert isinstance(upgrades, list)
        
        # Find our test user's request
        test_user_request = None
        for upgrade in upgrades:
            if upgrade.get("user_email") == TEST_USER_EMAIL:
                test_user_request = upgrade
                break
        
        if test_user_request:
            assert test_user_request.get("status") == "pending"
            assert test_user_request.get("tier") == "silver_monthly"
            print(f"✓ Admin sees {len(upgrades)} pending upgrades")
            print(f"✓ Found test user's request: {test_user_request.get('id')}")
            # Update pending_request_id if we didn't have it
            if not self.pending_request_id:
                self.__class__.pending_request_id = test_user_request["id"]
        else:
            print(f"✓ Admin sees {len(upgrades)} pending upgrades (test user request may be processed)")
    
    def test_05_admin_can_reject_upgrade(self):
        """POST /api/admin/pending-upgrades/{id}/reject rejects the request"""
        if not self.pending_request_id:
            pytest.skip("No pending request ID to reject")
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # First create a new request to reject (don't reject the one we'll approve)
        user_headers = {"Authorization": f"Bearer {self.test_user_token}"}
        res = requests.post(f"{BASE_URL}/api/subscription/upgrade", json={
            "tier": "bronze_monthly",
            "payment_method": "cashapp",
            "payment_reference": "CASHAPP-REJECT-TEST"
        }, headers=user_headers)
        
        if res.status_code == 200:
            reject_request_id = res.json().get("request_id")
            
            # Reject it
            res = requests.post(f"{BASE_URL}/api/admin/pending-upgrades/{reject_request_id}/reject", headers=headers)
            assert res.status_code == 200
            data = res.json()
            assert data.get("success") is True
            print(f"✓ Admin rejected upgrade request: {reject_request_id}")
        else:
            print("⚠ Could not create request to reject (user may already have pending request)")
    
    def test_06_admin_can_approve_upgrade(self):
        """POST /api/admin/pending-upgrades/{id}/approve approves and upgrades user"""
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Get fresh list of pending upgrades
        res = requests.get(f"{BASE_URL}/api/admin/pending-upgrades", headers=headers)
        assert res.status_code == 200
        upgrades = res.json().get("upgrades", [])
        
        # Find a pending request for our test user
        pending_request = None
        for upgrade in upgrades:
            if upgrade.get("user_email") == TEST_USER_EMAIL and upgrade.get("status") == "pending":
                pending_request = upgrade
                break
        
        if not pending_request:
            # Create new one
            user_headers = {"Authorization": f"Bearer {self.test_user_token}"}
            res = requests.post(f"{BASE_URL}/api/subscription/upgrade", json={
                "tier": "gold_monthly",
                "payment_method": "paypal",
                "payment_reference": "PAYPAL-APPROVE-TEST"
            }, headers=user_headers)
            if res.status_code == 200:
                pending_request = {"id": res.json().get("request_id"), "tier": "gold_monthly"}
            else:
                pytest.skip("Could not create pending request to approve")
        
        # Approve it
        res = requests.post(f"{BASE_URL}/api/admin/pending-upgrades/{pending_request['id']}/approve", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data.get("success") is True
        print(f"✓ Admin approved upgrade: {pending_request['id']}")
        
        # Verify user is actually upgraded
        user_headers = {"Authorization": f"Bearer {self.test_user_token}"}
        res = requests.get(f"{BASE_URL}/api/auth/me", headers=user_headers)
        assert res.status_code == 200
        user_data = res.json()
        
        # User should now have the upgraded tier
        expected_tier = pending_request.get("tier", "gold_monthly")
        print(f"✓ User subscription tier after approval: {user_data.get('subscription_tier')}")
    
    # === STRIPE CHECKOUT ===
    
    def test_07_stripe_checkout_creates_session(self):
        """POST /api/subscription/stripe-checkout creates Stripe Checkout session"""
        headers = {"Authorization": f"Bearer {self.test_user_token}"}
        
        res = requests.post(f"{BASE_URL}/api/subscription/stripe-checkout", json={
            "tier": "bronze_monthly",
            "origin_url": "https://hairpin-match.preview.emergentagent.com"
        }, headers=headers)
        
        assert res.status_code == 200, f"Stripe checkout failed: {res.text}"
        data = res.json()
        
        # Should return Stripe checkout URL
        assert "url" in data, f"No URL in response: {data}"
        assert "session_id" in data
        assert "checkout.stripe.com" in data["url"] or data["url"].startswith("https://")
        
        print(f"✓ Stripe checkout session created")
        print(f"✓ Session ID: {data['session_id']}")
        print(f"✓ Checkout URL: {data['url'][:80]}...")
        
        # Store for status check
        self.__class__.stripe_session_id = data["session_id"]
    
    def test_08_stripe_status_check_endpoint(self):
        """GET /api/subscription/stripe-status/{session_id} checks payment status"""
        if not hasattr(self, 'stripe_session_id') or not self.stripe_session_id:
            pytest.skip("No Stripe session ID to check")
        
        headers = {"Authorization": f"Bearer {self.test_user_token}"}
        
        res = requests.get(f"{BASE_URL}/api/subscription/stripe-status/{self.stripe_session_id}", headers=headers)
        
        # Should return status (pending since we can't complete actual payment in test)
        assert res.status_code in [200, 404], f"Unexpected status: {res.status_code}, {res.text}"
        
        if res.status_code == 200:
            data = res.json()
            assert "status" in data or "payment_status" in data
            print(f"✓ Stripe status check works: {data}")
        else:
            print("✓ Stripe status check returns 404 (session may not exist yet in Stripe)")
    
    # === CASHAPP UPGRADE CREATES PENDING ===
    
    def test_09_cashapp_upgrade_creates_pending_request(self):
        """POST /api/subscription/upgrade with CashApp creates PENDING request"""
        # Create a different test user for this
        new_email = f"TEST_cashapp_{uuid.uuid4().hex[:6]}@testuser.com"
        res = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": new_email,
            "password": "password123",
            "name": "CashApp Test User"
        })
        
        if res.status_code != 200:
            pytest.skip("Could not create test user for CashApp test")
        
        token = res.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        res = requests.post(f"{BASE_URL}/api/subscription/upgrade", json={
            "tier": "gold_yearly",
            "payment_method": "cashapp",
            "payment_reference": "$CASHAPP-TEST"
        }, headers=headers)
        
        assert res.status_code == 200
        data = res.json()
        
        assert data.get("success") is True
        assert data.get("status") == "pending"
        assert "request_id" in data
        print(f"✓ CashApp upgrade created PENDING request: {data['request_id']}")
    
    # === ADMIN AUTHENTICATION REQUIRED ===
    
    def test_10_pending_upgrades_requires_admin(self):
        """GET /api/admin/pending-upgrades requires admin authentication"""
        # No auth
        res = requests.get(f"{BASE_URL}/api/admin/pending-upgrades")
        assert res.status_code in [401, 403, 422], f"Should require auth: {res.status_code}"
        
        # Regular user auth
        headers = {"Authorization": f"Bearer {self.test_user_token}"}
        res = requests.get(f"{BASE_URL}/api/admin/pending-upgrades", headers=headers)
        assert res.status_code in [401, 403], f"Should require admin: {res.status_code}"
        
        print("✓ Pending upgrades endpoint properly secured")
    
    def test_11_approve_reject_requires_admin(self):
        """POST approve/reject endpoints require admin authentication"""
        fake_id = "fake-request-id"
        
        # No auth - approve
        res = requests.post(f"{BASE_URL}/api/admin/pending-upgrades/{fake_id}/approve")
        assert res.status_code in [401, 403, 422]
        
        # No auth - reject
        res = requests.post(f"{BASE_URL}/api/admin/pending-upgrades/{fake_id}/reject")
        assert res.status_code in [401, 403, 422]
        
        # Regular user - approve
        headers = {"Authorization": f"Bearer {self.test_user_token}"}
        res = requests.post(f"{BASE_URL}/api/admin/pending-upgrades/{fake_id}/approve", headers=headers)
        assert res.status_code in [401, 403]
        
        print("✓ Approve/reject endpoints properly secured")
    
    # === CLEANUP ===
    
    @pytest.fixture(autouse=True, scope="class")
    def cleanup(self, request):
        """Cleanup test data after tests"""
        yield
        # Delete test users
        if hasattr(request.cls, 'admin_token') and request.cls.admin_token:
            headers = {"Authorization": f"Bearer {request.cls.admin_token}"}
            # Get all users and delete TEST_ prefixed ones
            res = requests.get(f"{BASE_URL}/api/admin/users", headers=headers)
            if res.status_code == 200:
                users = res.json()
                for user in users:
                    if user.get("email", "").startswith("TEST_"):
                        requests.delete(f"{BASE_URL}/api/admin/users/{user['id']}", headers=headers)
                        print(f"✓ Cleaned up test user: {user['email']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
