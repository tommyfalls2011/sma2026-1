#!/usr/bin/env python3
"""
Admin Endpoints Testing
Tests all admin-specific endpoints including authentication, pricing, and user management
"""

import requests
import json
import sys
from datetime import datetime

# Get backend URL from frontend environment
def get_backend_url():
    """Get the backend URL from frontend .env file"""
    try:
        with open('/app/frontend/.env', 'r') as f:
            for line in f:
                if line.startswith('EXPO_PUBLIC_BACKEND_URL='):
                    base_url = line.split('=', 1)[1].strip().strip('"')
                    return f"{base_url}/api"
    except Exception as e:
        print(f"Error reading frontend .env: {e}")
    
    # Fallback
    return "http://localhost:8001/api"

BACKEND_URL = get_backend_url()

class AdminEndpointTester:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.test_results = []
        self.admin_token = None
        
    def log_result(self, test_name: str, success: bool, message: str):
        """Log test result"""
        self.test_results.append((test_name, success, message))
        status = "✅" if success else "❌"
        print(f"   {status} {message}")
    
    def test_admin_login(self):
        """Test 1: Login as admin and get token"""
        print("\n🧪 Test 1: Admin Login")
        
        # First try to register admin if not exists
        register_url = f"{self.base_url}/auth/register"
        register_payload = {
            "email": "fallstommy@gmail.com",
            "password": "testpass123",
            "name": "Admin User"
        }
        
        try:
            # Try registration first (might already exist)
            requests.post(register_url, json=register_payload, timeout=10)
        except:
            pass  # Ignore registration errors
        
        # Now try login
        login_url = f"{self.base_url}/auth/login"
        login_payload = {
            "email": "fallstommy@gmail.com",
            "password": "testpass123"
        }
        
        try:
            response = requests.post(login_url, json=login_payload, timeout=10)
            print(f"   Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if token is returned
                if not data.get('token'):
                    self.log_result("Admin Login", False, "No token returned")
                    return False
                
                # Check if user has admin privileges
                user = data.get('user', {})
                if user.get('subscription_tier') != 'admin':
                    self.log_result("Admin Login", False, 
                                  f"Expected admin tier, got: {user.get('subscription_tier')}")
                    return False
                
                self.admin_token = data.get('token')
                self.log_result("Admin Login", True, 
                              f"Admin login successful - Token obtained, Tier: {user.get('subscription_tier')}")
                return True
            else:
                self.log_result("Admin Login", False, 
                              f"Login failed - HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Admin Login", False, f"Error: {str(e)}")
            return False

    def test_admin_check(self):
        """Test 2: Check admin status"""
        print("\n🧪 Test 2: Check Admin Status")
        
        if not self.admin_token:
            self.log_result("Admin Check", False, "No admin token available")
            return False
        
        url = f"{self.base_url}/admin/check"
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            print(f"   Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                # Check admin status fields
                required_fields = ['is_admin', 'can_edit_settings', 'has_full_access']
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_result("Admin Check", False, 
                                  f"Missing required fields: {missing_fields}")
                    return False
                
                if not data.get('is_admin'):
                    self.log_result("Admin Check", False, "User is not recognized as admin")
                    return False
                
                self.log_result("Admin Check", True, 
                              f"Admin status confirmed - Can edit: {data.get('can_edit_settings')}, Full access: {data.get('has_full_access')}")
                return True
            else:
                self.log_result("Admin Check", False, 
                              f"Admin check failed - HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Admin Check", False, f"Error: {str(e)}")
            return False

    def test_get_pricing_settings(self):
        """Test 3: Get pricing settings (admin only)"""
        print("\n🧪 Test 3: Get Pricing Settings")
        
        if not self.admin_token:
            self.log_result("Get Pricing", False, "No admin token available")
            return False
        
        url = f"{self.base_url}/admin/pricing"
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            print(f"   Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                # Check for expected pricing tiers
                expected_tiers = ['bronze', 'silver', 'gold']
                missing_tiers = [tier for tier in expected_tiers if tier not in data]
                
                if missing_tiers:
                    self.log_result("Get Pricing", False, 
                                  f"Missing pricing tiers: {missing_tiers}")
                    return False
                
                # Check tier structure
                for tier in expected_tiers:
                    tier_data = data.get(tier, {})
                    if 'price' not in tier_data or 'max_elements' not in tier_data:
                        self.log_result("Get Pricing", False, 
                                      f"Tier {tier} missing price or max_elements")
                        return False
                
                # Check payment config
                payment = data.get('payment', {})
                if 'paypal_email' not in payment or 'cashapp_tag' not in payment:
                    self.log_result("Get Pricing", False, "Missing payment configuration")
                    return False
                
                self.log_result("Get Pricing", True, 
                              f"Pricing retrieved - Bronze: ${data['bronze']['price']}, Silver: ${data['silver']['price']}, Gold: ${data['gold']['price']}")
                return True
            else:
                self.log_result("Get Pricing", False, 
                              f"Get pricing failed - HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Get Pricing", False, f"Error: {str(e)}")
            return False

    def test_get_all_users(self):
        """Test 4: Get all users (admin only)"""
        print("\n🧪 Test 4: Get All Users")
        
        if not self.admin_token:
            self.log_result("Get All Users", False, "No admin token available")
            return False
        
        url = f"{self.base_url}/admin/users"
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            print(f"   Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                if not isinstance(data, list):
                    self.log_result("Get All Users", False, "Response is not a list of users")
                    return False
                
                # Check if we have at least the admin user
                if len(data) == 0:
                    self.log_result("Get All Users", False, "No users returned")
                    return False
                
                # Check user structure
                for user in data:
                    required_fields = ['id', 'email', 'name', 'subscription_tier']
                    missing_fields = [field for field in required_fields if field not in user]
                    if missing_fields:
                        self.log_result("Get All Users", False, 
                                      f"User missing fields: {missing_fields}")
                        return False
                
                # Find admin user
                admin_users = [u for u in data if u.get('subscription_tier') == 'admin']
                
                self.log_result("Get All Users", True, 
                              f"Users retrieved - Total: {len(data)}, Admin users: {len(admin_users)}")
                return True
            else:
                self.log_result("Get All Users", False, 
                              f"Get users failed - HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Get All Users", False, f"Error: {str(e)}")
            return False

    def test_update_pricing(self):
        """Test 5: Update pricing"""
        print("\n🧪 Test 5: Update Pricing")
        
        if not self.admin_token:
            self.log_result("Update Pricing", False, "No admin token available")
            return False
        
        url = f"{self.base_url}/admin/pricing"
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # New pricing data
        pricing_data = {
            "bronze_price": 25.99,
            "bronze_max_elements": 4,
            "silver_price": 45.99,
            "silver_max_elements": 8,
            "gold_price": 65.99,
            "gold_max_elements": 20
        }
        
        try:
            response = requests.put(url, json=pricing_data, headers=headers, timeout=10)
            print(f"   Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                if not data.get('success'):
                    self.log_result("Update Pricing", False, "Update not successful")
                    return False
                
                self.log_result("Update Pricing", True, 
                              f"Pricing updated - Bronze: ${pricing_data['bronze_price']}, Silver: ${pricing_data['silver_price']}, Gold: ${pricing_data['gold_price']}")
                return True
            else:
                self.log_result("Update Pricing", False, 
                              f"Update pricing failed - HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Update Pricing", False, f"Error: {str(e)}")
            return False

    def test_verify_pricing_updated(self):
        """Test 6: Verify pricing updated in public endpoint"""
        print("\n🧪 Test 6: Verify Pricing Updated")
        
        url = f"{self.base_url}/subscription/tiers"
        
        try:
            response = requests.get(url, timeout=10)
            print(f"   Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                tiers = data.get('tiers', {})
                if not tiers:
                    self.log_result("Verify Pricing", False, "No tiers returned")
                    return False
                
                # Check if new prices are reflected
                bronze = tiers.get('bronze', {})
                silver = tiers.get('silver', {})
                gold = tiers.get('gold', {})
                
                expected_prices = {
                    'bronze': 25.99,
                    'silver': 45.99,
                    'gold': 65.99
                }
                
                for tier_name, expected_price in expected_prices.items():
                    tier_data = tiers.get(tier_name, {})
                    actual_price = tier_data.get('price')
                    
                    if actual_price != expected_price:
                        self.log_result("Verify Pricing", False, 
                                      f"Price mismatch for {tier_name}: expected ${expected_price}, got ${actual_price}")
                        return False
                
                self.log_result("Verify Pricing", True, 
                              f"Pricing verified - Bronze: ${bronze.get('price')}, Silver: ${silver.get('price')}, Gold: ${gold.get('price')}")
                return True
            else:
                self.log_result("Verify Pricing", False, 
                              f"Verify pricing failed - HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Verify Pricing", False, f"Error: {str(e)}")
            return False

    def test_backend_connectivity(self):
        """Test basic backend connectivity"""
        try:
            response = requests.get(f"{self.base_url}/", timeout=10)
            if response.status_code == 200:
                print(f"✅ Backend connectivity - API is reachable at {self.base_url}")
                return True
            else:
                print(f"❌ Backend connectivity - HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Backend connectivity - Error: {e}")
            return False

    def run_all_tests(self):
        """Run all admin endpoint tests"""
        print("=" * 70)
        print("🚀 ADMIN ENDPOINTS API TESTS")
        print("=" * 70)
        print(f"Backend URL: {self.base_url}")
        print(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        
        # Test connectivity first
        if not self.test_backend_connectivity():
            print("\n❌ Backend is not reachable. Stopping tests.")
            return False
        
        # Run all tests in sequence
        test_methods = [
            self.test_admin_login,
            self.test_admin_check,
            self.test_get_pricing_settings,
            self.test_get_all_users,
            self.test_update_pricing,
            self.test_verify_pricing_updated
        ]
        
        for test_method in test_methods:
            test_method()
        
        # Summary
        print("\n" + "=" * 70)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 70)
        
        passed = sum(1 for _, success, _ in self.test_results if success)
        total = len(self.test_results)
        
        for test_name, success, message in self.test_results:
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{test_name:<30} {status}")
            if not success:
                print(f"   └─ {message}")
        
        print("-" * 70)
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        if passed == total:
            print("\n🎉 ALL ADMIN TESTS PASSED! Admin endpoints are working correctly.")
            return True
        else:
            print(f"\n⚠️  {total - passed} test(s) failed. Please check the issues above.")
            return False

if __name__ == "__main__":
    tester = AdminEndpointTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)