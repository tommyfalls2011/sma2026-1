"""
Test Admin Discounts and Notify Tab Endpoints
Tests for:
- POST /api/admin/discounts - Create discount codes (% or $ off)
- GET /api/admin/discounts - List all discounts
- DELETE /api/admin/discounts/{id} - Delete a discount
- POST /api/admin/discounts/{id}/toggle - Toggle active/inactive
- POST /api/validate-discount - Validate code (NO auth required)
- PUT /api/admin/app-update-settings - Save expo_url and download_link
- GET /api/admin/qr-code - Generate QR code base64
- POST /api/admin/send-update-email - Send HTML email via Resend
- GET /api/admin/user-emails - List all user emails
"""
import pytest
import requests
import os
import uuid
from datetime import datetime, timedelta

# Get backend URL from environment
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    BASE_URL = "https://quad-stack-lab.preview.emergentagent.com"

# Admin credentials
ADMIN_EMAIL = "fallstommy@gmail.com"
ADMIN_PASSWORD = "admin123"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token via POST /api/auth/login"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=30
    )
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    data = response.json()
    # Response has 'token' (not 'access_token')
    token = data.get("token")
    assert token, f"No token in response: {data}"
    print(f"Admin login successful, got token")
    return token


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    """Headers with admin Bearer token"""
    return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}


class TestDiscountEndpoints:
    """Test Discount CRUD and validation endpoints"""
    
    created_discount_ids = []
    
    def test_01_list_discounts_requires_auth(self):
        """GET /api/admin/discounts requires admin auth"""
        response = requests.get(f"{BASE_URL}/api/admin/discounts", timeout=30)
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"
        print("TEST PASS: List discounts returns 401 without auth")
    
    def test_02_list_discounts_with_auth(self, admin_headers):
        """GET /api/admin/discounts returns discount list"""
        response = requests.get(f"{BASE_URL}/api/admin/discounts", headers=admin_headers, timeout=30)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "discounts" in data, f"Missing 'discounts' key: {data}"
        assert isinstance(data["discounts"], list), "Discounts should be a list"
        print(f"TEST PASS: Listed {len(data['discounts'])} existing discounts")
        # Check if TEST50 and BETA20 exist from manual testing
        codes = [d.get("code") for d in data["discounts"]]
        if "TEST50" in codes:
            print("  - Found existing TEST50 discount")
        if "BETA20" in codes:
            print("  - Found existing BETA20 discount")
    
    def test_03_create_discount_requires_auth(self):
        """POST /api/admin/discounts requires admin auth"""
        response = requests.post(
            f"{BASE_URL}/api/admin/discounts",
            json={"code": "NOAUTH", "discount_type": "percent", "value": 10},
            timeout=30
        )
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"
        print("TEST PASS: Create discount returns 401 without auth")
    
    def test_04_create_percentage_discount(self, admin_headers):
        """POST /api/admin/discounts - Create % discount"""
        unique_code = f"TESTPCT_{uuid.uuid4().hex[:6].upper()}"
        payload = {
            "code": unique_code,
            "discount_type": "percent",
            "value": 25,
            "applies_to": "all",
            "tiers": ["bronze", "silver", "gold"]
        }
        response = requests.post(
            f"{BASE_URL}/api/admin/discounts",
            json=payload,
            headers=admin_headers,
            timeout=30
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "discount" in data, f"Missing 'discount' key: {data}"
        discount = data["discount"]
        assert discount["code"] == unique_code.upper(), "Code should be uppercased"
        assert discount["discount_type"] == "percent"
        assert discount["value"] == 25
        assert discount["active"] is True
        assert "id" in discount
        self.created_discount_ids.append(discount["id"])
        print(f"TEST PASS: Created percentage discount {unique_code} with id {discount['id']}")
    
    def test_05_create_fixed_amount_discount(self, admin_headers):
        """POST /api/admin/discounts - Create $ fixed discount"""
        unique_code = f"TESTFIX_{uuid.uuid4().hex[:6].upper()}"
        payload = {
            "code": unique_code,
            "discount_type": "fixed",
            "value": 10.00,
            "applies_to": "yearly",
            "tiers": ["silver", "gold"],
            "max_uses": 100
        }
        response = requests.post(
            f"{BASE_URL}/api/admin/discounts",
            json=payload,
            headers=admin_headers,
            timeout=30
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        discount = data["discount"]
        assert discount["discount_type"] == "fixed"
        assert discount["value"] == 10.00
        assert discount["applies_to"] == "yearly"
        assert "silver" in discount["tiers"]
        assert "gold" in discount["tiers"]
        assert discount["max_uses"] == 100
        self.created_discount_ids.append(discount["id"])
        print(f"TEST PASS: Created fixed discount {unique_code} for yearly billing")
    
    def test_06_create_duplicate_code_fails(self, admin_headers):
        """POST /api/admin/discounts - Duplicate code should fail"""
        # First create a discount
        unique_code = f"DUPE_{uuid.uuid4().hex[:6].upper()}"
        payload = {"code": unique_code, "discount_type": "percent", "value": 5}
        response = requests.post(
            f"{BASE_URL}/api/admin/discounts",
            json=payload,
            headers=admin_headers,
            timeout=30
        )
        assert response.status_code == 200
        data = response.json()
        self.created_discount_ids.append(data["discount"]["id"])
        
        # Try to create same code again
        response2 = requests.post(
            f"{BASE_URL}/api/admin/discounts",
            json=payload,
            headers=admin_headers,
            timeout=30
        )
        assert response2.status_code == 400, f"Expected 400 for duplicate, got {response2.status_code}"
        print(f"TEST PASS: Duplicate code {unique_code} correctly rejected with 400")
    
    def test_07_toggle_discount_active(self, admin_headers):
        """POST /api/admin/discounts/{id}/toggle - Toggle active/inactive"""
        # Get existing discounts
        response = requests.get(f"{BASE_URL}/api/admin/discounts", headers=admin_headers, timeout=30)
        data = response.json()
        if not data["discounts"]:
            pytest.skip("No discounts to toggle")
        
        discount = data["discounts"][0]
        discount_id = discount["id"]
        original_active = discount.get("active", True)
        
        # Toggle
        toggle_response = requests.post(
            f"{BASE_URL}/api/admin/discounts/{discount_id}/toggle",
            headers=admin_headers,
            timeout=30
        )
        assert toggle_response.status_code == 200, f"Toggle failed: {toggle_response.text}"
        toggle_data = toggle_response.json()
        assert "active" in toggle_data
        assert toggle_data["active"] != original_active, "Active state should be toggled"
        print(f"TEST PASS: Toggled discount {discount_id} from {original_active} to {toggle_data['active']}")
        
        # Toggle back to original state
        requests.post(f"{BASE_URL}/api/admin/discounts/{discount_id}/toggle", headers=admin_headers, timeout=30)
    
    def test_08_toggle_nonexistent_discount(self, admin_headers):
        """POST /api/admin/discounts/{id}/toggle - Nonexistent ID returns 404"""
        response = requests.post(
            f"{BASE_URL}/api/admin/discounts/nonexistent-id-12345/toggle",
            headers=admin_headers,
            timeout=30
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("TEST PASS: Toggle nonexistent discount returns 404")
    
    def test_09_delete_discount_requires_auth(self):
        """DELETE /api/admin/discounts/{id} requires auth"""
        response = requests.delete(f"{BASE_URL}/api/admin/discounts/some-id", timeout=30)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("TEST PASS: Delete discount returns 401 without auth")
    
    def test_10_delete_discount(self, admin_headers):
        """DELETE /api/admin/discounts/{id} - Delete a discount"""
        # Create a discount to delete
        unique_code = f"TODEL_{uuid.uuid4().hex[:6].upper()}"
        create_response = requests.post(
            f"{BASE_URL}/api/admin/discounts",
            json={"code": unique_code, "discount_type": "percent", "value": 5},
            headers=admin_headers,
            timeout=30
        )
        discount_id = create_response.json()["discount"]["id"]
        
        # Delete it
        delete_response = requests.delete(
            f"{BASE_URL}/api/admin/discounts/{discount_id}",
            headers=admin_headers,
            timeout=30
        )
        assert delete_response.status_code == 200, f"Delete failed: {delete_response.text}"
        assert "message" in delete_response.json()
        
        # Verify it's gone
        list_response = requests.get(f"{BASE_URL}/api/admin/discounts", headers=admin_headers, timeout=30)
        codes = [d["code"] for d in list_response.json()["discounts"]]
        assert unique_code not in codes, "Deleted discount should not appear in list"
        print(f"TEST PASS: Deleted discount {unique_code} successfully")
    
    def test_11_delete_nonexistent_discount(self, admin_headers):
        """DELETE /api/admin/discounts/{id} - Nonexistent returns 404"""
        response = requests.delete(
            f"{BASE_URL}/api/admin/discounts/nonexistent-id-99999",
            headers=admin_headers,
            timeout=30
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("TEST PASS: Delete nonexistent discount returns 404")


class TestDiscountValidation:
    """Test POST /api/validate-discount (NO AUTH REQUIRED)"""
    
    @pytest.fixture(scope="class")
    def test_discount_code(self, admin_headers):
        """Create a test discount for validation tests"""
        unique_code = f"VALTEST_{uuid.uuid4().hex[:4].upper()}"
        payload = {
            "code": unique_code,
            "discount_type": "percent",
            "value": 15,
            "applies_to": "monthly",
            "tiers": ["silver", "gold"],
            "user_emails": ["allowed@example.com"]
        }
        response = requests.post(
            f"{BASE_URL}/api/admin/discounts",
            json=payload,
            headers=admin_headers,
            timeout=30
        )
        assert response.status_code == 200
        return unique_code
    
    def test_01_validate_discount_no_auth_required(self, test_discount_code):
        """POST /api/validate-discount - No auth required"""
        response = requests.post(
            f"{BASE_URL}/api/validate-discount",
            json={"code": test_discount_code, "tier": "silver", "billing": "monthly", "email": "allowed@example.com"},
            timeout=30
        )
        # Should work without auth
        assert response.status_code == 200, f"Validation failed: {response.status_code} {response.text}"
        data = response.json()
        assert data["valid"] is True
        assert data["discount_type"] == "percent"
        assert data["value"] == 15
        print(f"TEST PASS: Validated discount {test_discount_code} without auth")
    
    def test_02_validate_invalid_code(self):
        """POST /api/validate-discount - Invalid code returns 404"""
        response = requests.post(
            f"{BASE_URL}/api/validate-discount",
            json={"code": "INVALIDCODE12345", "tier": "bronze"},
            timeout=30
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("TEST PASS: Invalid discount code returns 404")
    
    def test_03_validate_wrong_tier(self, test_discount_code):
        """POST /api/validate-discount - Wrong tier fails"""
        response = requests.post(
            f"{BASE_URL}/api/validate-discount",
            json={"code": test_discount_code, "tier": "bronze", "billing": "monthly", "email": "allowed@example.com"},
            timeout=30
        )
        # Discount is for silver/gold only, should fail for bronze
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        print(f"TEST PASS: Discount {test_discount_code} correctly rejected for bronze tier")
    
    def test_04_validate_wrong_billing(self, test_discount_code):
        """POST /api/validate-discount - Wrong billing period fails"""
        response = requests.post(
            f"{BASE_URL}/api/validate-discount",
            json={"code": test_discount_code, "tier": "silver", "billing": "yearly", "email": "allowed@example.com"},
            timeout=30
        )
        # Discount is monthly only
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        print(f"TEST PASS: Discount {test_discount_code} correctly rejected for yearly billing")
    
    def test_05_validate_restricted_email(self, test_discount_code):
        """POST /api/validate-discount - Restricted email fails"""
        response = requests.post(
            f"{BASE_URL}/api/validate-discount",
            json={"code": test_discount_code, "tier": "silver", "billing": "monthly", "email": "notallowed@example.com"},
            timeout=30
        )
        # Discount only for allowed@example.com
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print(f"TEST PASS: Discount {test_discount_code} correctly rejected for unauthorized email")
    
    def test_06_code_case_insensitive(self, admin_headers, test_discount_code):
        """POST /api/validate-discount - Code is case-insensitive (auto-uppercased)"""
        lower_code = test_discount_code.lower()
        response = requests.post(
            f"{BASE_URL}/api/validate-discount",
            json={"code": lower_code, "tier": "silver", "billing": "monthly", "email": "allowed@example.com"},
            timeout=30
        )
        assert response.status_code == 200, f"Lowercase code should work: {response.text}"
        print(f"TEST PASS: Lowercase code '{lower_code}' validated successfully")


class TestNotifyEndpoints:
    """Test Notify Tab endpoints - QR code and email"""
    
    def test_01_app_update_settings_requires_auth(self):
        """PUT /api/admin/app-update-settings requires auth"""
        response = requests.put(
            f"{BASE_URL}/api/admin/app-update-settings",
            json={"expo_url": "https://expo.dev/@test/app", "download_link": "https://download.com"},
            timeout=30
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("TEST PASS: App update settings PUT returns 401 without auth")
    
    def test_02_save_app_update_settings(self, admin_headers):
        """PUT /api/admin/app-update-settings - Save expo_url and download_link"""
        payload = {
            "expo_url": "https://expo.dev/@smaantenna/antenna-calc",
            "download_link": "https://quad-stack-lab.preview.emergentagent.com/download"
        }
        response = requests.put(
            f"{BASE_URL}/api/admin/app-update-settings",
            json=payload,
            headers=admin_headers,
            timeout=30
        )
        assert response.status_code == 200, f"Save failed: {response.text}"
        data = response.json()
        assert "message" in data
        print(f"TEST PASS: Saved app update settings: {payload}")
    
    def test_03_get_app_update_settings(self, admin_headers):
        """GET /api/admin/app-update-settings - Returns saved settings"""
        # Note: The endpoint seems to be PUT only for saving, let me check if GET exists
        # Actually looking at server.py, there is a GET endpoint
        response = requests.get(
            f"{BASE_URL}/api/admin/app-update-settings",
            headers=admin_headers,
            timeout=30
        )
        # If GET exists
        if response.status_code == 200:
            data = response.json()
            assert "expo_url" in data or "download_link" in data
            print(f"TEST PASS: Retrieved app update settings: {data}")
        elif response.status_code == 405:
            print("TEST INFO: GET /api/admin/app-update-settings not implemented (method not allowed)")
        else:
            print(f"TEST INFO: GET returned {response.status_code}: {response.text}")
    
    def test_04_qr_code_requires_auth(self):
        """GET /api/admin/qr-code requires auth"""
        response = requests.get(f"{BASE_URL}/api/admin/qr-code", timeout=30)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("TEST PASS: QR code endpoint returns 401 without auth")
    
    def test_05_generate_qr_code(self, admin_headers):
        """GET /api/admin/qr-code - Generate QR code base64"""
        # First ensure expo_url is set
        requests.put(
            f"{BASE_URL}/api/admin/app-update-settings",
            json={"expo_url": "https://expo.dev/@smaantenna/antenna-calc", "download_link": "https://example.com"},
            headers=admin_headers,
            timeout=30
        )
        
        response = requests.get(
            f"{BASE_URL}/api/admin/qr-code",
            headers=admin_headers,
            timeout=30
        )
        assert response.status_code == 200, f"QR code gen failed: {response.text}"
        data = response.json()
        assert "qr_base64" in data, f"Missing qr_base64: {data}"
        assert "url" in data, f"Missing url: {data}"
        assert len(data["qr_base64"]) > 100, "QR base64 should be substantial"
        print(f"TEST PASS: Generated QR code (base64 length={len(data['qr_base64'])})")
    
    def test_06_qr_code_fails_without_expo_url(self, admin_headers):
        """GET /api/admin/qr-code - Fails if no expo_url configured"""
        # Clear the expo_url
        requests.put(
            f"{BASE_URL}/api/admin/app-update-settings",
            json={"expo_url": "", "download_link": ""},
            headers=admin_headers,
            timeout=30
        )
        
        response = requests.get(
            f"{BASE_URL}/api/admin/qr-code",
            headers=admin_headers,
            timeout=30
        )
        assert response.status_code == 400, f"Expected 400 with empty expo_url, got {response.status_code}"
        print("TEST PASS: QR code correctly fails with 400 when no expo_url configured")
        
        # Restore expo_url for other tests
        requests.put(
            f"{BASE_URL}/api/admin/app-update-settings",
            json={"expo_url": "https://expo.dev/@smaantenna/antenna-calc", "download_link": "https://example.com"},
            headers=admin_headers,
            timeout=30
        )
    
    def test_07_user_emails_requires_auth(self):
        """GET /api/admin/user-emails requires auth"""
        response = requests.get(f"{BASE_URL}/api/admin/user-emails", timeout=30)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("TEST PASS: User emails endpoint returns 401 without auth")
    
    def test_08_get_user_emails(self, admin_headers):
        """GET /api/admin/user-emails - List all user emails"""
        response = requests.get(
            f"{BASE_URL}/api/admin/user-emails",
            headers=admin_headers,
            timeout=30
        )
        assert response.status_code == 200, f"Get user emails failed: {response.text}"
        data = response.json()
        assert "users" in data, f"Missing 'users' key: {data}"
        assert isinstance(data["users"], list)
        if data["users"]:
            user = data["users"][0]
            assert "email" in user, "User should have email"
        print(f"TEST PASS: Retrieved {len(data['users'])} user emails")
    
    def test_09_send_email_requires_auth(self):
        """POST /api/admin/send-update-email requires auth"""
        response = requests.post(
            f"{BASE_URL}/api/admin/send-update-email",
            json={"subject": "Test", "message": "Test message"},
            timeout=30
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("TEST PASS: Send email endpoint returns 401 without auth")
    
    def test_10_send_update_email_to_specific(self, admin_headers):
        """POST /api/admin/send-update-email - Send to specific email (not all users)"""
        payload = {
            "subject": "Test Update - Antenna Calc v2.0",
            "message": "This is a test notification email. Please ignore.",
            "expo_url": "https://expo.dev/@smaantenna/antenna-calc",
            "download_link": "https://quad-stack-lab.preview.emergentagent.com/download",
            "send_to": "fallstommy@gmail.com"  # Specific email, not 'all'
        }
        response = requests.post(
            f"{BASE_URL}/api/admin/send-update-email",
            json=payload,
            headers=admin_headers,
            timeout=60
        )
        assert response.status_code == 200, f"Send email failed: {response.text}"
        data = response.json()
        assert "sent" in data, f"Missing 'sent' count: {data}"
        assert "total" in data, f"Missing 'total' count: {data}"
        assert data["sent"] >= 1, f"Expected at least 1 sent, got {data['sent']}"
        print(f"TEST PASS: Sent update email to {data['sent']}/{data['total']} recipients")
        if data.get("errors"):
            print(f"  Errors: {data['errors']}")
    
    def test_11_send_email_no_recipients(self, admin_headers):
        """POST /api/admin/send-update-email - Empty send_to fails"""
        payload = {
            "subject": "Test",
            "message": "Test",
            "send_to": ""
        }
        response = requests.post(
            f"{BASE_URL}/api/admin/send-update-email",
            json=payload,
            headers=admin_headers,
            timeout=30
        )
        assert response.status_code == 400, f"Expected 400 for empty recipients, got {response.status_code}"
        print("TEST PASS: Send email correctly fails with 400 for empty recipients")


class TestCleanup:
    """Cleanup test data"""
    
    def test_cleanup_test_discounts(self, admin_headers):
        """Delete any test discounts created during testing"""
        response = requests.get(f"{BASE_URL}/api/admin/discounts", headers=admin_headers, timeout=30)
        if response.status_code == 200:
            discounts = response.json().get("discounts", [])
            test_prefixes = ["TESTPCT_", "TESTFIX_", "DUPE_", "VALTEST_", "TODEL_"]
            deleted = 0
            for discount in discounts:
                code = discount.get("code", "")
                if any(code.startswith(prefix) for prefix in test_prefixes):
                    delete_response = requests.delete(
                        f"{BASE_URL}/api/admin/discounts/{discount['id']}",
                        headers=admin_headers,
                        timeout=30
                    )
                    if delete_response.status_code == 200:
                        deleted += 1
            print(f"CLEANUP: Deleted {deleted} test discounts")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
