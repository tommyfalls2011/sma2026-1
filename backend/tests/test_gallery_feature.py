"""
Test suite for Product Gallery feature
Tests:
- POST /api/store/admin/products with gallery array
- PUT /api/store/admin/products/{id} with gallery update
- GET /api/store/products returns gallery field
- GET /api/store/products/{id} returns gallery field
"""
import pytest
import requests
import os

BASE_URL = "http://localhost:8001"
ADMIN_EMAIL = "fallstommy@gmail.com"
ADMIN_PASSWORD = "admin123"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin auth token"""
    response = requests.post(f"{BASE_URL}/api/store/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code != 200:
        pytest.skip(f"Admin login failed: {response.status_code} - {response.text}")
    data = response.json()
    return data.get("token")


@pytest.fixture(scope="module")
def auth_headers(admin_token):
    """Headers with auth token"""
    return {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    }


class TestGalleryBackendAPI:
    """Backend API tests for gallery feature"""
    
    created_product_id = None
    
    def test_01_create_product_with_gallery(self, auth_headers):
        """POST /api/store/admin/products should accept 'gallery' array field"""
        product_data = {
            "name": "TEST_Gallery Product",
            "price": 199.99,
            "short_desc": "A test product with gallery images",
            "description": "This is a test product to verify gallery functionality",
            "image_url": "https://images.unsplash.com/photo-1672689933227-2ce1249c46a9?w=600",
            "gallery": [
                "https://images.unsplash.com/photo-1673023239309-ae54f5ef3b04?w=600",
                "https://images.unsplash.com/photo-1727036195443-d2ba0ad73311?w=600"
            ],
            "in_stock": True,
            "specs": ["Spec 1", "Spec 2"]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/store/admin/products",
            headers=auth_headers,
            json=product_data
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Validate response structure
        assert "id" in data, "Response should contain product id"
        assert "gallery" in data, "Response should contain gallery field"
        assert data["gallery"] == product_data["gallery"], f"Gallery mismatch: {data['gallery']}"
        assert len(data["gallery"]) == 2, f"Expected 2 gallery images, got {len(data['gallery'])}"
        
        # Store for subsequent tests
        TestGalleryBackendAPI.created_product_id = data["id"]
        print(f"Created product with ID: {data['id']}, gallery: {data['gallery']}")
    
    def test_02_get_single_product_has_gallery(self, auth_headers):
        """GET /api/store/products/{id} should return gallery field"""
        product_id = TestGalleryBackendAPI.created_product_id
        assert product_id, "No product ID from previous test"
        
        response = requests.get(f"{BASE_URL}/api/store/products/{product_id}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert "gallery" in data, "Product response should contain gallery field"
        assert isinstance(data["gallery"], list), "Gallery should be a list"
        assert len(data["gallery"]) == 2, f"Expected 2 gallery images, got {len(data['gallery'])}"
        print(f"Product {product_id} has gallery: {data['gallery']}")
    
    def test_03_get_products_list_has_gallery(self):
        """GET /api/store/products should return gallery field in product data"""
        response = requests.get(f"{BASE_URL}/api/store/products")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        products = response.json()
        
        assert isinstance(products, list), "Response should be a list"
        
        # Find our test product
        test_product = None
        for p in products:
            if p.get("name") == "TEST_Gallery Product":
                test_product = p
                break
        
        assert test_product, "Test product not found in products list"
        assert "gallery" in test_product, "Product in list should have gallery field"
        assert len(test_product["gallery"]) == 2, f"Expected 2 gallery images"
        print(f"Products list includes gallery data correctly")
    
    def test_04_update_product_gallery(self, auth_headers):
        """PUT /api/store/admin/products/{id} should update 'gallery' field"""
        product_id = TestGalleryBackendAPI.created_product_id
        assert product_id, "No product ID from previous test"
        
        # Add a third gallery image
        update_data = {
            "gallery": [
                "https://images.unsplash.com/photo-1672689933227-2ce1249c46a9?w=600",
                "https://images.unsplash.com/photo-1673023239309-ae54f5ef3b04?w=600",
                "https://images.unsplash.com/photo-1727036195443-d2ba0ad73311?w=600"
            ]
        }
        
        response = requests.put(
            f"{BASE_URL}/api/store/admin/products/{product_id}",
            headers=auth_headers,
            json=update_data
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify the update persisted
        get_response = requests.get(f"{BASE_URL}/api/store/products/{product_id}")
        assert get_response.status_code == 200
        
        data = get_response.json()
        assert "gallery" in data, "Updated product should have gallery field"
        assert len(data["gallery"]) == 3, f"Expected 3 gallery images after update, got {len(data['gallery'])}"
        print(f"Product gallery updated to {len(data['gallery'])} images")
    
    def test_05_update_product_clear_gallery(self, auth_headers):
        """PUT /api/store/admin/products/{id} should allow clearing gallery"""
        product_id = TestGalleryBackendAPI.created_product_id
        assert product_id, "No product ID from previous test"
        
        # Clear gallery
        update_data = {"gallery": []}
        
        response = requests.put(
            f"{BASE_URL}/api/store/admin/products/{product_id}",
            headers=auth_headers,
            json=update_data
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # Verify the update persisted
        get_response = requests.get(f"{BASE_URL}/api/store/products/{product_id}")
        assert get_response.status_code == 200
        
        data = get_response.json()
        assert data["gallery"] == [], f"Expected empty gallery, got {data['gallery']}"
        print(f"Gallery cleared successfully")
    
    def test_06_create_product_without_gallery(self, auth_headers):
        """POST /api/store/admin/products should default gallery to empty array"""
        product_data = {
            "name": "TEST_No Gallery Product",
            "price": 99.99,
            "short_desc": "A product without gallery",
            "description": "Testing default gallery behavior",
            "image_url": "https://images.unsplash.com/photo-1672689933227-2ce1249c46a9?w=600",
            "in_stock": True,
            "specs": []
            # No gallery field provided
        }
        
        response = requests.post(
            f"{BASE_URL}/api/store/admin/products",
            headers=auth_headers,
            json=product_data
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert "gallery" in data, "Response should include gallery field even when not provided"
        assert data["gallery"] == [], f"Default gallery should be empty array, got {data['gallery']}"
        
        # Cleanup
        delete_response = requests.delete(
            f"{BASE_URL}/api/store/admin/products/{data['id']}",
            headers=auth_headers
        )
        assert delete_response.status_code == 200
        print(f"Product created with default empty gallery")
    
    def test_99_cleanup_test_product(self, auth_headers):
        """Cleanup: Delete test product"""
        product_id = TestGalleryBackendAPI.created_product_id
        if product_id:
            response = requests.delete(
                f"{BASE_URL}/api/store/admin/products/{product_id}",
                headers=auth_headers
            )
            assert response.status_code == 200, f"Cleanup failed: {response.status_code}"
            print(f"Cleaned up test product {product_id}")


class TestExistingProductsGallery:
    """Test that existing products work correctly with gallery feature"""
    
    def test_existing_products_have_gallery_field_or_none(self):
        """GET /api/store/products should work for products created before gallery feature"""
        response = requests.get(f"{BASE_URL}/api/store/products")
        
        assert response.status_code == 200
        products = response.json()
        
        # Check all products - they should either have gallery field or not (backward compatible)
        for p in products:
            if "gallery" in p:
                assert isinstance(p["gallery"], list), f"Gallery should be a list for product {p['name']}"
                print(f"Product '{p['name']}' has gallery: {len(p.get('gallery', []))} images")
            else:
                # Existing products might not have gallery field - this is OK
                print(f"Product '{p['name']}' has no gallery field (pre-existing product)")
    
    def test_single_existing_product_accessible(self):
        """GET /api/store/products/{id} should work for existing products"""
        # Get product list first
        response = requests.get(f"{BASE_URL}/api/store/products")
        assert response.status_code == 200
        products = response.json()
        
        if products:
            product_id = products[0]["id"]
            detail_response = requests.get(f"{BASE_URL}/api/store/products/{product_id}")
            assert detail_response.status_code == 200
            data = detail_response.json()
            
            # Existing products may or may not have gallery
            print(f"Existing product '{data['name']}' accessible, gallery: {data.get('gallery', 'not set')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
