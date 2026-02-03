#!/usr/bin/env python3
"""
Backend Authentication and Subscription API Testing
Tests the new authentication and subscription endpoints
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

class AuthenticationTester:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.test_results = []
        self.token = None
        
    def log_result(self, test_name: str, success: bool, message: str):
        """Log test result"""
        self.test_results.append((test_name, success, message))
        status = "✅" if success else "❌"
        print(f"   {status} {message}")
    
    def test_user_registration(self):
        """Test 1: User Registration"""
        print("\n🧪 Test 1: User Registration")
        
        url = f"{self.base_url}/auth/register"
        payload = {
            "email": "testuser@example.com",
            "password": "testpass123",
            "name": "Test User"
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            print(f"   Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if token is returned
                if not data.get('token'):
                    self.log_result("User Registration", False, "No token returned")
                    return False
                
                # Check if user object is returned
                user = data.get('user', {})
                if not user:
                    self.log_result("User Registration", False, "No user object returned")
                    return False
                
                # Check subscription tier
                if user.get('subscription_tier') != 'trial':
                    self.log_result("User Registration", False, 
                                  f"Expected trial tier, got: {user.get('subscription_tier')}")
                    return False
                
                self.token = data.get('token')
                self.log_result("User Registration", True, 
                              f"Registration successful - Token: {self.token[:20]}..., Tier: {user.get('subscription_tier')}")
                return True
                
            elif response.status_code == 400:
                # Email might already be registered
                error_msg = response.json().get('detail', 'Unknown error')
                if 'already registered' in error_msg:
                    self.log_result("User Registration", True, 
                                  f"Email already registered (acceptable): {error_msg}")
                    return True
                else:
                    self.log_result("User Registration", False, f"Registration failed: {error_msg}")
                    return False
            else:
                self.log_result("User Registration", False, 
                              f"Registration failed - HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("User Registration", False, f"Error: {str(e)}")
            return False

    def test_user_login(self):
        """Test 2: User Login"""
        print("\n🧪 Test 2: User Login")
        
        url = f"{self.base_url}/auth/login"
        payload = {
            "email": "testuser@example.com",
            "password": "testpass123"
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            print(f"   Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if token is returned
                if not data.get('token'):
                    self.log_result("User Login", False, "No token returned")
                    return False
                
                # Check if user info is returned
                user = data.get('user', {})
                if not user:
                    self.log_result("User Login", False, "No user info returned")
                    return False
                
                # Store token for subsequent tests
                if not self.token:
                    self.token = data.get('token')
                
                self.log_result("User Login", True, 
                              f"Login successful - Email: {user.get('email')}, Name: {user.get('name')}")
                return True
            else:
                self.log_result("User Login", False, 
                              f"Login failed - HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("User Login", False, f"Error: {str(e)}")
            return False

    def test_get_current_user(self):
        """Test 3: Get Current User (with auth)"""
        print("\n🧪 Test 3: Get Current User (with auth)")
        
        if not self.token:
            self.log_result("Get Current User", False, "No token available for authentication")
            return False
        
        url = f"{self.base_url}/auth/me"
        headers = {"Authorization": f"Bearer {self.token}"}
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            print(f"   Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                # Check required fields
                required_fields = ['id', 'email', 'name', 'subscription_tier']
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_result("Get Current User", False, 
                                  f"Missing required fields: {missing_fields}")
                    return False
                
                # Check subscription status fields
                if 'is_active' not in data:
                    self.log_result("Get Current User", False, "Missing subscription status (is_active)")
                    return False
                
                self.log_result("Get Current User", True, 
                              f"User info retrieved - ID: {data.get('id')}, Active: {data.get('is_active')}, Tier: {data.get('subscription_tier')}")
                return True
            else:
                self.log_result("Get Current User", False, 
                              f"Failed to get user info - HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Get Current User", False, f"Error: {str(e)}")
            return False

    def test_get_subscription_tiers(self):
        """Test 4: Get Subscription Tiers"""
        print("\n🧪 Test 4: Get Subscription Tiers")
        
        url = f"{self.base_url}/subscription/tiers"
        
        try:
            response = requests.get(url, timeout=10)
            print(f"   Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if tiers are returned
                tiers = data.get('tiers', {})
                if not tiers:
                    self.log_result("Get Subscription Tiers", False, "No tiers returned")
                    return False
                
                # Check for expected tiers
                expected_tiers = ['trial', 'bronze', 'silver', 'gold']
                missing_tiers = [tier for tier in expected_tiers if tier not in tiers]
                
                if missing_tiers:
                    self.log_result("Get Subscription Tiers", False, 
                                  f"Missing expected tiers: {missing_tiers}")
                    return False
                
                # Check payment info
                payment_methods = data.get('payment_methods', {})
                if not payment_methods:
                    self.log_result("Get Subscription Tiers", False, "No payment methods returned")
                    return False
                
                tier_names = list(tiers.keys())
                payment_names = list(payment_methods.keys())
                
                self.log_result("Get Subscription Tiers", True, 
                              f"Tiers retrieved - Available: {tier_names}, Payment methods: {payment_names}")
                return True
            else:
                self.log_result("Get Subscription Tiers", False, 
                              f"Failed to get tiers - HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Get Subscription Tiers", False, f"Error: {str(e)}")
            return False

    def test_admin_registration(self):
        """Test 5: Admin Registration (backdoor email)"""
        print("\n🧪 Test 5: Admin Registration (backdoor email)")
        
        url = f"{self.base_url}/auth/register"
        payload = {
            "email": "fallstommy@gmail.com",
            "password": "admin123",
            "name": "Admin User"
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            print(f"   Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if admin tier is assigned
                user = data.get('user', {})
                if user.get('subscription_tier') != 'admin':
                    self.log_result("Admin Registration", False, 
                                  f"Expected admin tier, got: {user.get('subscription_tier')}")
                    return False
                
                self.log_result("Admin Registration", True, 
                              f"Admin registration successful - Tier: {user.get('subscription_tier')}")
                return True
                
            elif response.status_code == 400:
                # Email might already be registered
                error_msg = response.json().get('detail', 'Unknown error')
                if 'already registered' in error_msg:
                    self.log_result("Admin Registration", True, 
                                  f"Admin email already registered (acceptable): {error_msg}")
                    return True
                else:
                    self.log_result("Admin Registration", False, f"Admin registration failed: {error_msg}")
                    return False
            else:
                self.log_result("Admin Registration", False, 
                              f"Admin registration failed - HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Admin Registration", False, f"Error: {str(e)}")
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
        """Run all authentication and subscription tests"""
        print("=" * 70)
        print("🚀 BACKEND AUTHENTICATION & SUBSCRIPTION API TESTS")
        print("=" * 70)
        print(f"Backend URL: {self.base_url}")
        print(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        
        # Test connectivity first
        if not self.test_backend_connectivity():
            print("\n❌ Backend is not reachable. Stopping tests.")
            return False
        
        # Run all tests
        test_methods = [
            self.test_user_registration,
            self.test_user_login,
            self.test_get_current_user,
            self.test_get_subscription_tiers,
            self.test_admin_registration
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
            print("\n🎉 ALL TESTS PASSED! Authentication system is working correctly.")
            return True
        else:
            print(f"\n⚠️  {total - passed} test(s) failed. Please check the issues above.")
            return False

if __name__ == "__main__":
    tester = AuthenticationTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)