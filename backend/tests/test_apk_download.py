"""
Tests for APK Download Feature
- GET /api/store/latest-apk endpoint
- GitHub releases integration
- store_settings caching
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001').rstrip('/')


class TestAPKDownloadFeature:
    """APK download endpoint tests"""

    def test_01_latest_apk_returns_200(self):
        """GET /api/store/latest-apk returns 200 OK"""
        response = requests.get(f"{BASE_URL}/api/store/latest-apk", timeout=30)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print(f"PASS: latest-apk endpoint returns 200")

    def test_02_apk_response_has_version(self):
        """Response includes version field"""
        response = requests.get(f"{BASE_URL}/api/store/latest-apk", timeout=30)
        data = response.json()
        assert "version" in data, f"Missing 'version' field. Keys: {data.keys()}"
        assert data["version"].startswith("v"), f"Version should start with 'v': {data['version']}"
        print(f"PASS: version = {data['version']}")

    def test_03_apk_response_has_download_url(self):
        """Response includes download_url pointing to GitHub"""
        response = requests.get(f"{BASE_URL}/api/store/latest-apk", timeout=30)
        data = response.json()
        assert "download_url" in data, f"Missing 'download_url' field"
        assert "github.com" in data["download_url"], f"download_url should contain github.com"
        assert ".apk" in data["download_url"], f"download_url should contain .apk"
        print(f"PASS: download_url = {data['download_url'][:80]}...")

    def test_04_apk_response_has_filename(self):
        """Response includes filename field"""
        response = requests.get(f"{BASE_URL}/api/store/latest-apk", timeout=30)
        data = response.json()
        assert "filename" in data, f"Missing 'filename' field"
        assert data["filename"].endswith(".apk"), f"filename should end with .apk: {data['filename']}"
        print(f"PASS: filename = {data['filename']}")

    def test_05_apk_response_has_size_mb(self):
        """Response includes size_mb field (numeric)"""
        response = requests.get(f"{BASE_URL}/api/store/latest-apk", timeout=30)
        data = response.json()
        assert "size_mb" in data, f"Missing 'size_mb' field"
        assert isinstance(data["size_mb"], (int, float)), f"size_mb should be numeric: {data['size_mb']}"
        assert data["size_mb"] > 0, f"size_mb should be positive: {data['size_mb']}"
        print(f"PASS: size_mb = {data['size_mb']}")

    def test_06_apk_response_has_published_at(self):
        """Response includes published_at field"""
        response = requests.get(f"{BASE_URL}/api/store/latest-apk", timeout=30)
        data = response.json()
        assert "published_at" in data, f"Missing 'published_at' field"
        assert len(data["published_at"]) > 0, f"published_at should not be empty"
        print(f"PASS: published_at = {data['published_at']}")

    def test_07_apk_response_has_release_name(self):
        """Response includes release_name field"""
        response = requests.get(f"{BASE_URL}/api/store/latest-apk", timeout=30)
        data = response.json()
        assert "release_name" in data, f"Missing 'release_name' field"
        print(f"PASS: release_name = {data['release_name']}")

    def test_08_apk_version_is_v4_0_4_or_newer(self):
        """Version should be v4.0.4 or newer (as per requirements)"""
        response = requests.get(f"{BASE_URL}/api/store/latest-apk", timeout=30)
        data = response.json()
        version = data.get("version", "")
        # Extract version numbers
        import re
        match = re.search(r'v?(\d+)\.(\d+)\.(\d+)', version)
        if match:
            major, minor, patch = int(match.group(1)), int(match.group(2)), int(match.group(3))
            # Should be >= 4.0.4
            version_tuple = (major, minor, patch)
            assert version_tuple >= (4, 0, 4), f"Version should be >= v4.0.4, got {version}"
            print(f"PASS: version {version} >= v4.0.4")
        else:
            print(f"WARNING: Could not parse version {version}")

    def test_09_download_url_is_accessible(self):
        """The download_url should be accessible (HEAD request)"""
        response = requests.get(f"{BASE_URL}/api/store/latest-apk", timeout=30)
        data = response.json()
        download_url = data.get("download_url", "")
        if download_url:
            # Check HEAD request to GitHub (don't download the full APK)
            head_response = requests.head(download_url, timeout=30, allow_redirects=True)
            assert head_response.status_code in [200, 302], f"download_url not accessible: {head_response.status_code}"
            print(f"PASS: download_url is accessible (status {head_response.status_code})")
        else:
            pytest.skip("No download_url to test")


class TestRegressionProducts:
    """Regression tests for existing store functionality"""

    def test_10_products_endpoint_works(self):
        """GET /api/store/products still returns products"""
        response = requests.get(f"{BASE_URL}/api/store/products", timeout=30)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        assert len(data) > 0, f"Expected products, got empty list"
        print(f"PASS: /api/store/products returns {len(data)} products")

    def test_11_product_has_required_fields(self):
        """Products have required fields (id, name, price, image_url)"""
        response = requests.get(f"{BASE_URL}/api/store/products", timeout=30)
        data = response.json()
        product = data[0]
        required_fields = ["id", "name", "price", "image_url"]
        for field in required_fields:
            assert field in product, f"Product missing '{field}' field"
        print(f"PASS: Product has all required fields: {required_fields}")


class TestRegressionImageUpload:
    """Quick regression test for image upload from iteration_10"""

    def test_12_upload_endpoint_requires_auth(self):
        """POST /api/store/admin/upload returns 401 without auth"""
        response = requests.post(f"{BASE_URL}/api/store/admin/upload", timeout=30)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print(f"PASS: /api/store/admin/upload requires auth (401)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
