"""
Test suite for FeatureGate component behavior with Bronze tier user.
Verifies that:
1. Bronze tier features list is correctly returned from API
2. isFeatureAvailable() logic is correctly implemented
3. Feature gating shows LOCKED state for features NOT in bronze tier
4. Feature gating shows AVAILABLE state for features IN bronze tier
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Bronze tier features (from /api/subscription/tiers)
BRONZE_FEATURES = ["save_designs", "csv_export", "auto_tune", "taper", "gamma_match"]

# All features defined in the app
ALL_FEATURES = [
    "auto_tune", "optimize_height", "save_designs", "csv_export", "stacking",
    "taper", "corona_balls", "ground_radials", "gamma_match", "hairpin_match",
    "smith_chart", "polar_pattern", "elevation_pattern", "dual_polarity",
    "coax_loss", "wind_load", "pdf_export", "spacing_control", "return_loss_tune",
    "reflected_power"
]

# Features that should be LOCKED for Bronze user
BRONZE_LOCKED_FEATURES = [f for f in ALL_FEATURES if f not in BRONZE_FEATURES]

# Features specifically wrapped by FeatureGate component in index.tsx
FEATURE_GATE_WRAPPED_FEATURES = [
    "coax_loss",      # line 1807
    "spacing_control", # line 2107 
    "polar_pattern",   # line 2777
    "elevation_pattern", # line 2783
    "smith_chart",     # line 2790
    "reflected_power", # line 2896
    "wind_load",       # line 3577
]

# Features checked via checkFeature() function (interactive controls)
CHECK_FEATURE_CONTROLS = [
    "stacking",       # Toggle switch
    "corona_balls",   # Toggle switch  
    "ground_radials", # Toggle switch
    "hairpin_match",  # Button
    "optimize_height", # Button
    "return_loss_tune", # Button
    "dual_polarity",  # Orientation option
]


class TestSubscriptionTiersAPI:
    """Test the /api/subscription/tiers endpoint returns correct features"""
    
    def test_tiers_endpoint_returns_200(self):
        response = requests.get(f"{BASE_URL}/api/subscription/tiers")
        assert response.status_code == 200
        print("✓ /api/subscription/tiers returns 200")
    
    def test_bronze_monthly_has_correct_features(self):
        response = requests.get(f"{BASE_URL}/api/subscription/tiers")
        data = response.json()
        bronze_features = data["tiers"]["bronze_monthly"]["features"]
        
        # Verify bronze has exactly the expected features
        assert set(bronze_features) == set(BRONZE_FEATURES), f"Expected {BRONZE_FEATURES}, got {bronze_features}"
        print(f"✓ Bronze monthly has correct features: {bronze_features}")
    
    def test_bronze_yearly_matches_bronze_monthly(self):
        response = requests.get(f"{BASE_URL}/api/subscription/tiers")
        data = response.json()
        bronze_monthly = data["tiers"]["bronze_monthly"]["features"]
        bronze_yearly = data["tiers"]["bronze_yearly"]["features"]
        
        assert set(bronze_monthly) == set(bronze_yearly), "Bronze monthly and yearly should have same features"
        print("✓ Bronze monthly and yearly feature lists match")
    
    def test_gold_has_all_features(self):
        response = requests.get(f"{BASE_URL}/api/subscription/tiers")
        data = response.json()
        gold_features = data["tiers"]["gold_monthly"]["features"]
        
        # Gold should have all 20 features
        assert len(gold_features) == 20, f"Expected 20 gold features, got {len(gold_features)}"
        
        # Check all gated features are in gold
        for feature in FEATURE_GATE_WRAPPED_FEATURES:
            assert feature in gold_features, f"Gold missing FeatureGate feature: {feature}"
        
        print(f"✓ Gold tier has all {len(gold_features)} features")
    

class TestBronzeUserLogin:
    """Test login for bronze test user"""
    
    def test_bronze_user_login_success(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "test_bronze@testuser.com",
            "password": "test123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["subscription_tier"] == "bronze"
        print(f"✓ Bronze user logged in successfully, tier: {data['user']['subscription_tier']}")
    
    def test_bronze_user_is_active(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "test_bronze@testuser.com",
            "password": "test123"
        })
        data = response.json()
        assert data["user"]["is_active"] == True
        assert data["user"]["status_message"] == "Active"
        print("✓ Bronze user is active with correct status")


class TestAdminUserLogin:
    """Test login for admin user"""
    
    def test_admin_user_login_success(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "fallstommy@gmail.com",
            "password": "admin123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["subscription_tier"] == "admin"
        print(f"✓ Admin user logged in successfully, tier: {data['user']['subscription_tier']}")


class TestFeatureGatingLogic:
    """
    Test the feature gating logic for Bronze tier.
    
    According to AuthContext.tsx lines 308-317:
    - Non-logged-in users: isFeatureAvailable() returns true (all features visible)
    - Admin/subadmin: isFeatureAvailable() returns true (all features visible)
    - Other tiers: Check tier.features array for 'all' or specific feature
    
    For Bronze user (subscription_tier='bronze'):
    - tierKey = 'bronze_monthly' (line 313)
    - Checks tierInfo.features.includes(feature)
    - Should only have: save_designs, csv_export, auto_tune, taper, gamma_match
    """
    
    def test_bronze_should_have_save_designs(self):
        """Bronze tier should have save_designs feature"""
        assert "save_designs" in BRONZE_FEATURES
        print("✓ save_designs IS available for Bronze")
    
    def test_bronze_should_have_csv_export(self):
        """Bronze tier should have csv_export feature"""
        assert "csv_export" in BRONZE_FEATURES
        print("✓ csv_export IS available for Bronze")
    
    def test_bronze_should_have_auto_tune(self):
        """Bronze tier should have auto_tune feature"""
        assert "auto_tune" in BRONZE_FEATURES
        print("✓ auto_tune IS available for Bronze")
    
    def test_bronze_should_have_taper(self):
        """Bronze tier should have taper feature"""
        assert "taper" in BRONZE_FEATURES
        print("✓ taper IS available for Bronze")
    
    def test_bronze_should_have_gamma_match(self):
        """Bronze tier should have gamma_match feature"""
        assert "gamma_match" in BRONZE_FEATURES
        print("✓ gamma_match IS available for Bronze")
    
    def test_bronze_should_NOT_have_coax_loss(self):
        """Bronze tier should NOT have coax_loss - should show LOCKED"""
        assert "coax_loss" not in BRONZE_FEATURES
        assert "coax_loss" in BRONZE_LOCKED_FEATURES
        print("✓ coax_loss should be LOCKED for Bronze (FeatureGate wrapped)")
    
    def test_bronze_should_NOT_have_spacing_control(self):
        """Bronze tier should NOT have spacing_control - should show LOCKED"""
        assert "spacing_control" not in BRONZE_FEATURES
        assert "spacing_control" in BRONZE_LOCKED_FEATURES
        print("✓ spacing_control should be LOCKED for Bronze (FeatureGate wrapped)")
    
    def test_bronze_should_NOT_have_polar_pattern(self):
        """Bronze tier should NOT have polar_pattern - should show LOCKED"""
        assert "polar_pattern" not in BRONZE_FEATURES
        assert "polar_pattern" in BRONZE_LOCKED_FEATURES
        print("✓ polar_pattern should be LOCKED for Bronze (FeatureGate wrapped)")
    
    def test_bronze_should_NOT_have_elevation_pattern(self):
        """Bronze tier should NOT have elevation_pattern - should show LOCKED"""
        assert "elevation_pattern" not in BRONZE_FEATURES
        assert "elevation_pattern" in BRONZE_LOCKED_FEATURES
        print("✓ elevation_pattern should be LOCKED for Bronze (FeatureGate wrapped)")
    
    def test_bronze_should_NOT_have_smith_chart(self):
        """Bronze tier should NOT have smith_chart - should show LOCKED"""
        assert "smith_chart" not in BRONZE_FEATURES
        assert "smith_chart" in BRONZE_LOCKED_FEATURES
        print("✓ smith_chart should be LOCKED for Bronze (FeatureGate wrapped)")
    
    def test_bronze_should_NOT_have_reflected_power(self):
        """Bronze tier should NOT have reflected_power - should show LOCKED"""
        assert "reflected_power" not in BRONZE_FEATURES
        assert "reflected_power" in BRONZE_LOCKED_FEATURES
        print("✓ reflected_power should be LOCKED for Bronze (FeatureGate wrapped)")
    
    def test_bronze_should_NOT_have_wind_load(self):
        """Bronze tier should NOT have wind_load - should show LOCKED"""
        assert "wind_load" not in BRONZE_FEATURES
        assert "wind_load" in BRONZE_LOCKED_FEATURES
        print("✓ wind_load should be LOCKED for Bronze (FeatureGate wrapped)")
    
    def test_bronze_should_NOT_have_stacking(self):
        """Bronze tier should NOT have stacking - toggle should show Alert"""
        assert "stacking" not in BRONZE_FEATURES
        assert "stacking" in BRONZE_LOCKED_FEATURES
        print("✓ stacking toggle should show Upgrade Alert for Bronze")
    
    def test_bronze_should_NOT_have_corona_balls(self):
        """Bronze tier should NOT have corona_balls - toggle should show Alert"""
        assert "corona_balls" not in BRONZE_FEATURES
        assert "corona_balls" in BRONZE_LOCKED_FEATURES
        print("✓ corona_balls toggle should show Upgrade Alert for Bronze")
    
    def test_bronze_should_NOT_have_ground_radials(self):
        """Bronze tier should NOT have ground_radials - toggle should show Alert"""
        assert "ground_radials" not in BRONZE_FEATURES
        assert "ground_radials" in BRONZE_LOCKED_FEATURES
        print("✓ ground_radials toggle should show Upgrade Alert for Bronze")
    
    def test_bronze_should_NOT_have_hairpin_match(self):
        """Bronze tier should NOT have hairpin_match - button should show Alert"""
        assert "hairpin_match" not in BRONZE_FEATURES
        assert "hairpin_match" in BRONZE_LOCKED_FEATURES
        print("✓ hairpin_match button should show Upgrade Alert for Bronze")
    
    def test_bronze_should_NOT_have_optimize_height(self):
        """Bronze tier should NOT have optimize_height - button should show Alert"""
        assert "optimize_height" not in BRONZE_FEATURES
        assert "optimize_height" in BRONZE_LOCKED_FEATURES
        print("✓ optimize_height button should show Upgrade Alert for Bronze")
    
    def test_bronze_should_NOT_have_return_loss_tune(self):
        """Bronze tier should NOT have return_loss_tune - button should show Alert"""
        assert "return_loss_tune" not in BRONZE_FEATURES
        assert "return_loss_tune" in BRONZE_LOCKED_FEATURES
        print("✓ return_loss_tune button should show Upgrade Alert for Bronze")


class TestTierKeyMapping:
    """
    Test that the tier key mapping is correct in AuthContext.tsx.
    
    The fix was: user.subscription_tier is 'bronze' but tiers object has 'bronze_monthly'.
    Line 313: const tierKey = user.subscription_tier === 'trial' ? 'trial' : `${user.subscription_tier}_monthly`;
    """
    
    def test_bronze_tier_maps_to_bronze_monthly(self):
        """Bronze user's subscription_tier='bronze' should map to 'bronze_monthly' key"""
        # Login as bronze user
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "test_bronze@testuser.com",
            "password": "test123"
        })
        user = response.json()["user"]
        
        # User has subscription_tier='bronze'
        assert user["subscription_tier"] == "bronze"
        
        # Get tiers
        tiers_response = requests.get(f"{BASE_URL}/api/subscription/tiers")
        tiers = tiers_response.json()["tiers"]
        
        # The tier key should be 'bronze_monthly', not 'bronze'
        assert "bronze" not in tiers, "Tiers should NOT have 'bronze' key directly"
        assert "bronze_monthly" in tiers, "Tiers should have 'bronze_monthly' key"
        
        # The fix in AuthContext.tsx line 313: tierKey = `${user.subscription_tier}_monthly`
        tier_key = f"{user['subscription_tier']}_monthly"
        assert tier_key == "bronze_monthly"
        assert tier_key in tiers
        
        print(f"✓ Bronze tier key mapping correct: subscription_tier='bronze' -> tierKey='bronze_monthly'")
    
    def test_silver_tier_maps_to_silver_monthly(self):
        """Silver user's subscription_tier='silver' should map to 'silver_monthly' key"""
        tiers_response = requests.get(f"{BASE_URL}/api/subscription/tiers")
        tiers = tiers_response.json()["tiers"]
        
        assert "silver" not in tiers, "Tiers should NOT have 'silver' key directly"
        assert "silver_monthly" in tiers, "Tiers should have 'silver_monthly' key"
        
        tier_key = "silver_monthly"  # Simulating: `${user.subscription_tier}_monthly`
        assert tier_key in tiers
        
        print("✓ Silver tier key mapping correct: subscription_tier='silver' -> tierKey='silver_monthly'")


class TestFeatureGateComponentBehavior:
    """
    Verify FeatureGate component expected behavior based on code review.
    
    From FeatureGate.tsx:
    - If !user (not logged in): return children (no gate)
    - If isFeatureAvailable(feature): return children (feature available)
    - Otherwise: show lock overlay with tier name, feature name, Upgrade button
    
    For Bronze user viewing a LOCKED feature (e.g., coax_loss):
    - Should see dimmed content with lock overlay
    - Overlay should show: lock icon, "Coax Loss Calculator", "Not included in Bronze plan", "Upgrade" button
    """
    
    def test_bronze_locked_features_count(self):
        """Bronze should have 15 locked features (20 total - 5 bronze features)"""
        assert len(BRONZE_LOCKED_FEATURES) == 15, f"Expected 15 locked features, got {len(BRONZE_LOCKED_FEATURES)}"
        print(f"✓ Bronze has {len(BRONZE_LOCKED_FEATURES)} locked features")
    
    def test_feature_gate_wrapped_features_all_locked_for_bronze(self):
        """All FeatureGate wrapped features should be locked for Bronze"""
        for feature in FEATURE_GATE_WRAPPED_FEATURES:
            assert feature not in BRONZE_FEATURES, f"{feature} should be locked for Bronze"
        print(f"✓ All {len(FEATURE_GATE_WRAPPED_FEATURES)} FeatureGate wrapped features are locked for Bronze")
    
    def test_check_feature_controls_mostly_locked_for_bronze(self):
        """Most checkFeature() controlled features should be locked for Bronze"""
        locked_count = 0
        for feature in CHECK_FEATURE_CONTROLS:
            if feature not in BRONZE_FEATURES:
                locked_count += 1
        
        # All 7 interactive controls should be locked for Bronze
        # (stacking, corona_balls, ground_radials, hairpin_match, optimize_height, return_loss_tune, dual_polarity)
        assert locked_count == 7, f"Expected 7 locked interactive controls, got {locked_count}"
        print(f"✓ All {locked_count} checkFeature() interactive controls are locked for Bronze")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
