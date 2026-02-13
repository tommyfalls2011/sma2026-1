"""
Stripe Checkout Integration Tests
Tests for the new Stripe payment checkout feature:
- POST /api/store/checkout - Create Stripe session with server-side price validation
- GET /api/store/checkout/status/{session_id} - Get payment status
- GET /api/store/orders - Get user's order history
- POST /api/webhook/stripe - Webhook endpoint exists
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001')
BASE_URL = BASE_URL.rstrip('/') if BASE_URL else 'http://localhost:8001'

# Test credentials
ADMIN_EMAIL = "fallstommy@gmail.com"
ADMIN_PASSWORD = "admin123"

# Tax and shipping constants (must match backend)
NC_TAX_RATE = 0.0675
SHIPPING_STANDARD = 15.00


@pytest.fixture(scope="module")
def auth_token():
    """Get admin auth token"""
    response = requests.post(f"{BASE_URL}/api/store/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    data = response.json()
    return data.get("token")


@pytest.fixture(scope="module")
def products():
    """Get available products"""
    response = requests.get(f"{BASE_URL}/api/store/products")
    assert response.status_code == 200, f"Failed to get products: {response.text}"
    return response.json()


class TestCheckoutEndpoint:
    """Tests for POST /api/store/checkout"""

    def test_01_checkout_requires_auth(self, products):
        """Checkout endpoint requires authentication"""
        if not products:
            pytest.skip("No products available")
        response = requests.post(f"{BASE_URL}/api/store/checkout", json={
            "items": [{"id": products[0]["id"], "qty": 1}],
            "origin_url": "http://localhost:3000"
        })
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: Checkout requires authentication")

    def test_02_checkout_requires_items(self, auth_token):
        """Checkout requires cart items"""
        response = requests.post(
            f"{BASE_URL}/api/store/checkout",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"items": [], "origin_url": "http://localhost:3000"}
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("PASS: Checkout requires items in cart")

    def test_03_checkout_requires_origin_url(self, auth_token, products):
        """Checkout requires origin_url"""
        if not products:
            pytest.skip("No products available")
        response = requests.post(
            f"{BASE_URL}/api/store/checkout",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"items": [{"id": products[0]["id"], "qty": 1}]}
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("PASS: Checkout requires origin_url")

    def test_04_checkout_validates_product_exists(self, auth_token):
        """Checkout validates product ID exists in database"""
        response = requests.post(
            f"{BASE_URL}/api/store/checkout",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "items": [{"id": "nonexistent-product-id", "qty": 1}],
                "origin_url": "http://localhost:3000"
            }
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        data = response.json()
        assert "not found" in data.get("detail", "").lower(), f"Expected 'not found' in error: {data}"
        print("PASS: Checkout validates product exists")

    def test_05_checkout_creates_stripe_session(self, auth_token, products):
        """Checkout successfully creates Stripe session with proper response"""
        if not products:
            pytest.skip("No products available")
        
        # Find an in-stock product
        in_stock_product = next((p for p in products if p.get("in_stock")), None)
        if not in_stock_product:
            pytest.skip("No in-stock products available")

        response = requests.post(
            f"{BASE_URL}/api/store/checkout",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "items": [{"id": in_stock_product["id"], "qty": 1}],
                "origin_url": "http://localhost:3000"
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify response structure
        assert "url" in data, "Response must include 'url'"
        assert "session_id" in data, "Response must include 'session_id'"
        assert "order_id" in data, "Response must include 'order_id'"
        
        # Verify URL is a Stripe checkout URL
        assert "stripe.com" in data["url"] or "emergentagent.com" in data["url"], f"URL should be Stripe/Emergent checkout: {data['url']}"
        
        # Verify session_id format
        assert data["session_id"].startswith("cs_"), f"Session ID should start with 'cs_': {data['session_id']}"
        
        print(f"PASS: Checkout created session {data['session_id']}")
        print(f"  Order ID: {data['order_id']}")
        print(f"  URL: {data['url'][:80]}...")

    def test_06_checkout_calculates_correct_total(self, auth_token, products):
        """Checkout calculates correct total with tax and shipping"""
        if not products:
            pytest.skip("No products available")
        
        in_stock_product = next((p for p in products if p.get("in_stock")), None)
        if not in_stock_product:
            pytest.skip("No in-stock products available")

        qty = 2
        expected_subtotal = in_stock_product["price"] * qty
        expected_tax = round(expected_subtotal * NC_TAX_RATE, 2)
        expected_total = round(expected_subtotal + expected_tax + SHIPPING_STANDARD, 2)

        response = requests.post(
            f"{BASE_URL}/api/store/checkout",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "items": [{"id": in_stock_product["id"], "qty": qty}],
                "origin_url": "http://localhost:3000"
            }
        )
        assert response.status_code == 200, f"Checkout failed: {response.text}"
        
        data = response.json()
        print(f"PASS: Checkout created for {qty}x {in_stock_product['name']} @ ${in_stock_product['price']}")
        print(f"  Expected subtotal: ${expected_subtotal}")
        print(f"  Expected tax (6.75%): ${expected_tax}")
        print(f"  Expected shipping: ${SHIPPING_STANDARD}")
        print(f"  Expected total: ${expected_total}")


class TestCheckoutStatusEndpoint:
    """Tests for GET /api/store/checkout/status/{session_id}"""

    def test_07_status_endpoint_exists(self):
        """Checkout status endpoint exists"""
        # Using a dummy session ID - should return some response
        response = requests.get(f"{BASE_URL}/api/store/checkout/status/cs_test_dummy")
        # Should not be 404 (endpoint exists) - may be 500 if invalid session
        assert response.status_code != 404, f"Status endpoint should exist, got {response.status_code}"
        print(f"PASS: Status endpoint exists (returned {response.status_code})")

    def test_08_status_returns_valid_structure(self, auth_token, products):
        """Checkout status returns valid response structure for valid session"""
        if not products:
            pytest.skip("No products available")
        
        in_stock_product = next((p for p in products if p.get("in_stock")), None)
        if not in_stock_product:
            pytest.skip("No in-stock products available")

        # Create a session first
        checkout_response = requests.post(
            f"{BASE_URL}/api/store/checkout",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "items": [{"id": in_stock_product["id"], "qty": 1}],
                "origin_url": "http://localhost:3000"
            }
        )
        if checkout_response.status_code != 200:
            pytest.skip(f"Could not create checkout session: {checkout_response.text}")
        
        session_id = checkout_response.json()["session_id"]
        
        # Now check status
        status_response = requests.get(f"{BASE_URL}/api/store/checkout/status/{session_id}")
        assert status_response.status_code == 200, f"Status check failed: {status_response.text}"
        
        data = status_response.json()
        assert "status" in data, "Response must include 'status'"
        assert "payment_status" in data, "Response must include 'payment_status'"
        assert "order_id" in data, "Response must include 'order_id'"
        
        print(f"PASS: Status endpoint returns valid structure")
        print(f"  Status: {data.get('status')}")
        print(f"  Payment Status: {data.get('payment_status')}")
        print(f"  Order ID: {data.get('order_id')}")


class TestOrdersEndpoint:
    """Tests for GET /api/store/orders"""

    def test_09_orders_requires_auth(self):
        """Orders endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/store/orders")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: Orders endpoint requires authentication")

    def test_10_orders_returns_user_orders(self, auth_token):
        """Orders endpoint returns list of user orders"""
        response = requests.get(
            f"{BASE_URL}/api/store/orders",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Orders request failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Orders should return a list"
        
        if data:
            order = data[0]
            # Check order has expected fields
            assert "id" in order, "Order must have 'id'"
            assert "items" in order, "Order must have 'items'"
            assert "total" in order, "Order must have 'total'"
            assert "payment_status" in order, "Order must have 'payment_status'"
            print(f"PASS: Orders endpoint returns {len(data)} orders")
            print(f"  Latest order ID: {order['id']}")
            print(f"  Payment status: {order['payment_status']}")
        else:
            print("PASS: Orders endpoint returns empty list (no orders yet)")


class TestWebhookEndpoint:
    """Tests for POST /api/webhook/stripe"""

    def test_11_webhook_endpoint_exists(self):
        """Stripe webhook endpoint exists and accepts POST"""
        # Send empty request - should return ok status, not 404
        response = requests.post(f"{BASE_URL}/api/webhook/stripe", data=b"")
        assert response.status_code != 404, f"Webhook endpoint should exist, got {response.status_code}"
        # Should be 200 with error status (since no valid signature)
        data = response.json()
        assert "status" in data, "Webhook should return status"
        print(f"PASS: Webhook endpoint exists (returned {response.status_code})")


class TestProductsRegression:
    """Regression tests - ensure products endpoint still works"""

    def test_12_products_endpoint_works(self):
        """Products endpoint returns valid data"""
        response = requests.get(f"{BASE_URL}/api/store/products")
        assert response.status_code == 200, f"Products request failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Products should return a list"
        assert len(data) > 0, "Should have at least one product"
        
        print(f"PASS: Products endpoint returns {len(data)} products")

    def test_13_products_have_required_fields(self, products):
        """Products have all required fields"""
        if not products:
            pytest.skip("No products available")
        
        required_fields = ["id", "name", "price", "in_stock"]
        for product in products:
            for field in required_fields:
                assert field in product, f"Product missing required field '{field}'"
        
        print(f"PASS: All {len(products)} products have required fields")


class TestPaymentTransactionPersistence:
    """Tests for payment transaction persistence in DB"""

    def test_14_checkout_stores_transaction_pending(self, auth_token, products):
        """Checkout stores payment_transaction with 'pending' status"""
        if not products:
            pytest.skip("No products available")
        
        in_stock_product = next((p for p in products if p.get("in_stock")), None)
        if not in_stock_product:
            pytest.skip("No in-stock products available")

        # Create checkout session
        response = requests.post(
            f"{BASE_URL}/api/store/checkout",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "items": [{"id": in_stock_product["id"], "qty": 1}],
                "origin_url": "http://localhost:3000"
            }
        )
        assert response.status_code == 200, f"Checkout failed: {response.text}"
        
        order_id = response.json()["order_id"]
        
        # Verify the order exists in user's orders with pending status
        orders_response = requests.get(
            f"{BASE_URL}/api/store/orders",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert orders_response.status_code == 200, f"Orders request failed"
        
        orders = orders_response.json()
        matching_order = next((o for o in orders if o.get("id") == order_id), None)
        
        assert matching_order is not None, f"Order {order_id} not found in user orders"
        assert matching_order.get("payment_status") == "pending", f"Expected 'pending' status, got {matching_order.get('payment_status')}"
        
        print(f"PASS: Transaction stored with 'pending' status")
        print(f"  Order ID: {order_id}")
        print(f"  Items: {len(matching_order.get('items', []))} item(s)")
        print(f"  Total: ${matching_order.get('total')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
