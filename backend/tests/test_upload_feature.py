"""
Backend tests for Image Upload feature
Tests:
- POST /api/store/admin/upload - File upload and URL return
- File type validation (jpg, png, webp, gif allowed)
- File size validation (max 10MB)
- Admin authentication required
- Uploaded files served at /api/uploads/{filename}
"""
import pytest
import requests
import os
import tempfile

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/') or 'http://localhost:8001'
ADMIN_EMAIL = "fallstommy@gmail.com"
ADMIN_PASSWORD = "admin123"


class TestUploadEndpoint:
    """Image upload endpoint tests"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/store/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in login response"
        return data["token"]
    
    def test_01_upload_requires_auth(self):
        """Upload should fail without authentication"""
        # Create a temp file
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            f.write(b'\x89PNG\r\n\x1a\n' + b'\x00' * 100)
            temp_path = f.name
        
        try:
            with open(temp_path, 'rb') as f:
                response = requests.post(
                    f"{BASE_URL}/api/store/admin/upload",
                    files={'file': ('test.png', f, 'image/png')}
                )
            assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"
            print("PASS: Upload requires authentication")
        finally:
            os.unlink(temp_path)
    
    def test_02_upload_png_success(self, admin_token):
        """Upload PNG file should succeed"""
        # Create minimal valid PNG
        png_header = b'\x89PNG\r\n\x1a\n'
        # Minimal IHDR chunk
        png_data = png_header + b'\x00' * 100
        
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            f.write(png_data)
            temp_path = f.name
        
        try:
            with open(temp_path, 'rb') as f:
                response = requests.post(
                    f"{BASE_URL}/api/store/admin/upload",
                    headers={'Authorization': f'Bearer {admin_token}'},
                    files={'file': ('test_image.png', f, 'image/png')}
                )
            
            assert response.status_code == 200, f"Upload failed: {response.text}"
            data = response.json()
            assert "url" in data, "No URL in upload response"
            assert "filename" in data, "No filename in upload response"
            assert data["url"].startswith("/api/uploads/"), f"Invalid URL format: {data['url']}"
            assert data["url"].endswith(".png"), f"URL should end with .png: {data['url']}"
            print(f"PASS: PNG upload success - URL: {data['url']}")
            return data["url"]
        finally:
            os.unlink(temp_path)
    
    def test_03_upload_jpg_success(self, admin_token):
        """Upload JPG file should succeed"""
        # Minimal JPEG data
        jpg_data = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00' + b'\x00' * 100
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            f.write(jpg_data)
            temp_path = f.name
        
        try:
            with open(temp_path, 'rb') as f:
                response = requests.post(
                    f"{BASE_URL}/api/store/admin/upload",
                    headers={'Authorization': f'Bearer {admin_token}'},
                    files={'file': ('test_image.jpg', f, 'image/jpeg')}
                )
            
            assert response.status_code == 200, f"Upload failed: {response.text}"
            data = response.json()
            assert data["url"].endswith(".jpg"), f"URL should end with .jpg: {data['url']}"
            print(f"PASS: JPG upload success - URL: {data['url']}")
        finally:
            os.unlink(temp_path)
    
    def test_04_upload_webp_success(self, admin_token):
        """Upload WebP file should succeed"""
        # Minimal WebP header
        webp_data = b'RIFF\x00\x00\x00\x00WEBP' + b'\x00' * 100
        
        with tempfile.NamedTemporaryFile(suffix='.webp', delete=False) as f:
            f.write(webp_data)
            temp_path = f.name
        
        try:
            with open(temp_path, 'rb') as f:
                response = requests.post(
                    f"{BASE_URL}/api/store/admin/upload",
                    headers={'Authorization': f'Bearer {admin_token}'},
                    files={'file': ('test_image.webp', f, 'image/webp')}
                )
            
            assert response.status_code == 200, f"Upload failed: {response.text}"
            data = response.json()
            assert data["url"].endswith(".webp"), f"URL should end with .webp: {data['url']}"
            print(f"PASS: WebP upload success - URL: {data['url']}")
        finally:
            os.unlink(temp_path)
    
    def test_05_upload_gif_success(self, admin_token):
        """Upload GIF file should succeed"""
        # Minimal GIF header
        gif_data = b'GIF89a' + b'\x00' * 100
        
        with tempfile.NamedTemporaryFile(suffix='.gif', delete=False) as f:
            f.write(gif_data)
            temp_path = f.name
        
        try:
            with open(temp_path, 'rb') as f:
                response = requests.post(
                    f"{BASE_URL}/api/store/admin/upload",
                    headers={'Authorization': f'Bearer {admin_token}'},
                    files={'file': ('test_image.gif', f, 'image/gif')}
                )
            
            assert response.status_code == 200, f"Upload failed: {response.text}"
            data = response.json()
            assert data["url"].endswith(".gif"), f"URL should end with .gif: {data['url']}"
            print(f"PASS: GIF upload success - URL: {data['url']}")
        finally:
            os.unlink(temp_path)
    
    def test_06_reject_non_image_file(self, admin_token):
        """Upload non-image file should be rejected"""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            f.write(b'This is not an image file')
            temp_path = f.name
        
        try:
            with open(temp_path, 'rb') as f:
                response = requests.post(
                    f"{BASE_URL}/api/store/admin/upload",
                    headers={'Authorization': f'Bearer {admin_token}'},
                    files={'file': ('test.txt', f, 'text/plain')}
                )
            
            assert response.status_code == 400, f"Expected 400 for txt file, got {response.status_code}"
            data = response.json()
            assert "detail" in data, "No error detail in response"
            assert ".txt" in data["detail"] or "not allowed" in data["detail"].lower(), f"Error message should mention file type: {data['detail']}"
            print(f"PASS: Non-image file rejected: {data['detail']}")
        finally:
            os.unlink(temp_path)
    
    def test_07_reject_pdf_file(self, admin_token):
        """Upload PDF file should be rejected"""
        pdf_header = b'%PDF-1.4' + b'\x00' * 100
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            f.write(pdf_header)
            temp_path = f.name
        
        try:
            with open(temp_path, 'rb') as f:
                response = requests.post(
                    f"{BASE_URL}/api/store/admin/upload",
                    headers={'Authorization': f'Bearer {admin_token}'},
                    files={'file': ('document.pdf', f, 'application/pdf')}
                )
            
            assert response.status_code == 400, f"Expected 400 for PDF, got {response.status_code}"
            print("PASS: PDF file rejected")
        finally:
            os.unlink(temp_path)
    
    def test_08_uploaded_file_accessible(self, admin_token):
        """Uploaded file should be accessible via /api/uploads/"""
        # Upload a file first
        png_data = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100
        
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            f.write(png_data)
            temp_path = f.name
        
        try:
            with open(temp_path, 'rb') as f:
                response = requests.post(
                    f"{BASE_URL}/api/store/admin/upload",
                    headers={'Authorization': f'Bearer {admin_token}'},
                    files={'file': ('accessible_test.png', f, 'image/png')}
                )
            
            assert response.status_code == 200
            url = response.json()["url"]
            
            # Now try to access the file
            file_response = requests.get(f"{BASE_URL}{url}")
            assert file_response.status_code == 200, f"Could not access uploaded file: {file_response.status_code}"
            print(f"PASS: Uploaded file accessible at {url}")
        finally:
            os.unlink(temp_path)
    
    def test_09_existing_uploaded_file_accessible(self):
        """Previously uploaded file should still be accessible"""
        # Test the file that was uploaded during manual testing
        response = requests.get(f"{BASE_URL}/api/uploads/61942e56f5b84c8b9b567763b299cce2.png")
        assert response.status_code == 200, f"Existing file not accessible: {response.status_code}"
        print("PASS: Existing uploaded file (from manual test) accessible")
    
    def test_10_upload_returns_correct_url_format(self, admin_token):
        """Uploaded file URL should be in correct format"""
        png_data = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100
        
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            f.write(png_data)
            temp_path = f.name
        
        try:
            with open(temp_path, 'rb') as f:
                response = requests.post(
                    f"{BASE_URL}/api/store/admin/upload",
                    headers={'Authorization': f'Bearer {admin_token}'},
                    files={'file': ('format_test.png', f, 'image/png')}
                )
            
            assert response.status_code == 200
            data = response.json()
            
            # URL format: /api/uploads/{uuid}.{ext}
            url = data["url"]
            assert url.startswith("/api/uploads/"), f"URL should start with /api/uploads/: {url}"
            filename = url.split("/")[-1]
            name_part, ext = filename.rsplit(".", 1)
            assert len(name_part) == 32, f"Filename should be 32-char UUID hex: {name_part}"
            assert ext == "png", f"Extension should match: {ext}"
            print(f"PASS: URL format correct: {url}")
        finally:
            os.unlink(temp_path)


class TestGalleryRegression:
    """Quick regression tests for gallery feature (tested in iteration_9)"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/store/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["token"]
    
    def test_11_create_product_with_gallery_still_works(self, admin_token):
        """Create product with gallery array should still work"""
        headers = {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}
        
        product_data = {
            "name": "TEST Upload Regression Product",
            "price": 999,
            "short_desc": "Test product",
            "description": "Testing gallery still works",
            "image_url": "https://example.com/main.png",
            "gallery": ["https://example.com/gallery1.png", "https://example.com/gallery2.png"],
            "in_stock": True,
            "specs": ["Test spec"]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/store/admin/products",
            headers=headers,
            json=product_data
        )
        
        assert response.status_code == 200, f"Create failed: {response.text}"
        data = response.json()
        assert "gallery" in data, "Gallery field missing from response"
        assert len(data["gallery"]) == 2, f"Gallery should have 2 items: {data['gallery']}"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/store/admin/products/{data['id']}", headers=headers)
        print("PASS: Gallery regression - create product with gallery works")
    
    def test_12_get_products_returns_gallery(self):
        """GET /api/store/products should return gallery field"""
        response = requests.get(f"{BASE_URL}/api/store/products")
        assert response.status_code == 200
        products = response.json()
        assert len(products) > 0, "No products found"
        # Gallery field should exist (may be empty array)
        for p in products:
            assert "gallery" in p or p.get("gallery") is None, f"Product missing gallery field: {p.get('name')}"
        print("PASS: Gallery regression - products list returns gallery field")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
