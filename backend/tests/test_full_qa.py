"""Comprehensive QA Backend Tests for SMA Antenna Calculator.

Tests all API endpoints including:
- POST /api/calculate with various feed types (direct, gamma, hairpin)
- Gamma match with physical model (tube=11", teflon=12", spacing=3.5", default insertion=8")
- Stacking, taper, corona_balls, ground_radials options
- Coax loss calculations
- Pattern data (elevation, far_field, smith_chart, wind_load, reflected_power)
- POST /api/auto-tune and /api/optimize-height
- Auth endpoints (login)
- Subscription tiers and admin pricing with 20 features
- Save/load designs
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# 3-element 11m CB Yagi test data (from request)
YAGI_3_ELEMENT = {
    "num_elements": 3,
    "elements": [
        {"element_type": "reflector", "length": 214.5, "diameter": 0.5, "position": 0},
        {"element_type": "driven", "length": 202.4, "diameter": 0.5, "position": 47},
        {"element_type": "director", "length": 195.0, "diameter": 0.5, "position": 138}
    ],
    "height_from_ground": 54,
    "height_unit": "ft",
    "boom_diameter": 2,
    "boom_unit": "inches",
    "band": "11m_cb",
    "frequency_mhz": 27.185,
    "antenna_orientation": "horizontal",
    "feed_type": "direct"
}


class TestCalculateEndpoint:
    """Tests for POST /api/calculate with various configurations."""

    def test_calculate_direct_feed(self):
        """Test 3-element Yagi with direct feed returns gain, swr, fb_ratio."""
        payload = YAGI_3_ELEMENT.copy()
        payload["feed_type"] = "direct"
        
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "gain_dbi" in data, "Missing gain_dbi"
        assert "swr" in data, "Missing swr"
        assert "fb_ratio" in data, "Missing fb_ratio"
        assert data["gain_dbi"] > 5, f"Gain should be > 5 dBi for 3-element Yagi, got {data['gain_dbi']}"
        assert data["swr"] >= 1.0, f"SWR should be >= 1.0, got {data['swr']}"
        assert data["fb_ratio"] > 10, f"F/B ratio should be > 10 dB, got {data['fb_ratio']}"
        print(f"PASSED: Direct feed - Gain={data['gain_dbi']} dBi, SWR={data['swr']}, F/B={data['fb_ratio']} dB")

    def test_calculate_gamma_feed_defaults(self):
        """Test gamma feed returns gamma_design with correct physical model."""
        payload = YAGI_3_ELEMENT.copy()
        payload["feed_type"] = "gamma"
        
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert "matching_info" in data, "Missing matching_info"
        matching_info = data["matching_info"]
        assert matching_info.get("type") == "Gamma Match", "Should be Gamma Match type"
        
        # Verify gamma_design exists with physical model
        assert "gamma_design" in matching_info, "Missing gamma_design in matching_info"
        gamma_design = matching_info["gamma_design"]
        
        # Check physical model values (spacing=3.5", tube=11", teflon=12")
        assert gamma_design.get("gamma_rod_spacing_in") == 3.5, f"Expected spacing=3.5, got {gamma_design.get('gamma_rod_spacing_in')}"
        assert gamma_design.get("tube_length_in") == 11.0, f"Expected tube=11.0, got {gamma_design.get('tube_length_in')}"
        assert gamma_design.get("teflon_sleeve_in") == 12.0, f"Expected teflon=12.0, got {gamma_design.get('teflon_sleeve_in')}"
        
        # Verify rod length is approximately 32" for 11m CB
        rod_length = gamma_design.get("gamma_rod_length_in", 0)
        assert 30 <= rod_length <= 35, f"Expected rod length ~32\", got {rod_length}"
        
        print(f"PASSED: Gamma feed - spacing={gamma_design['gamma_rod_spacing_in']}\", tube={gamma_design['tube_length_in']}\", teflon={gamma_design['teflon_sleeve_in']}\", rod={rod_length}\"")

    def test_calculate_gamma_with_custom_insertion(self):
        """Test gamma feed with custom rod insertion (gamma_element_gap)."""
        payload = YAGI_3_ELEMENT.copy()
        payload["feed_type"] = "gamma"
        payload["gamma_element_gap"] = 6.0  # 6 inches insertion
        
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        matching_info = data.get("matching_info", {})
        # Check rod insertion is reflected
        rod_insertion = matching_info.get("rod_insertion_inches", 0)
        assert 5.5 <= rod_insertion <= 6.5, f"Expected insertion ~6\", got {rod_insertion}"
        print(f"PASSED: Gamma with custom insertion - rod_insertion={rod_insertion}\"")

    def test_calculate_hairpin_feed(self):
        """Test hairpin feed returns hairpin_design."""
        payload = YAGI_3_ELEMENT.copy()
        payload["feed_type"] = "hairpin"
        
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert "matching_info" in data, "Missing matching_info"
        matching_info = data["matching_info"]
        assert matching_info.get("type") == "Hairpin Match", f"Expected Hairpin Match, got {matching_info.get('type')}"
        
        # Check hairpin_design exists
        assert "hairpin_design" in matching_info, "Missing hairpin_design"
        hairpin = matching_info["hairpin_design"]
        assert "feedpoint_impedance_ohms" in hairpin
        assert "length_inches" in hairpin
        print(f"PASSED: Hairpin feed - feedpoint_Z={hairpin['feedpoint_impedance_ohms']} ohms, length={hairpin['length_inches']}\"")

    def test_calculate_with_stacking(self):
        """Test with stacking enabled returns stacking results."""
        payload = YAGI_3_ELEMENT.copy()
        payload["stacking"] = {
            "enabled": True,
            "orientation": "vertical",
            "layout": "line",
            "num_antennas": 2,
            "spacing": 20,
            "spacing_unit": "ft"
        }
        
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("stacking_enabled") == True, "stacking_enabled should be True"
        assert "stacking_info" in data, "Missing stacking_info"
        assert "stacked_gain_dbi" in data, "Missing stacked_gain_dbi"
        assert "stacked_pattern" in data, "Missing stacked_pattern"
        
        stacking_info = data["stacking_info"]
        assert stacking_info.get("num_antennas") == 2
        print(f"PASSED: Stacking - stacked_gain={data['stacked_gain_dbi']} dBi, {stacking_info}")

    def test_calculate_with_taper(self):
        """Test with taper enabled returns tapered results."""
        payload = YAGI_3_ELEMENT.copy()
        payload["taper"] = {
            "enabled": True,
            "num_tapers": 2,
            "sections": [
                {"length": 48, "start_diameter": 1.0, "end_diameter": 0.75},
                {"length": 48, "start_diameter": 0.75, "end_diameter": 0.5}
            ]
        }
        
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert "taper_info" in data, "Missing taper_info"
        taper_info = data["taper_info"]
        assert taper_info.get("gain_bonus", 0) > 0, "Expected positive gain bonus from taper"
        print(f"PASSED: Taper - taper_info={taper_info}")

    def test_calculate_with_corona_balls(self):
        """Test with corona_balls enabled."""
        payload = YAGI_3_ELEMENT.copy()
        payload["corona_balls"] = {"enabled": True, "diameter": 1.5}
        
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert "corona_info" in data, "Missing corona_info"
        corona_info = data["corona_info"]
        assert corona_info.get("enabled") == True
        print(f"PASSED: Corona balls - corona_info={corona_info}")

    def test_calculate_with_ground_radials(self):
        """Test with ground_radials enabled."""
        payload = YAGI_3_ELEMENT.copy()
        payload["ground_radials"] = {
            "enabled": True,
            "ground_type": "average",
            "wire_diameter": 0.5,
            "num_radials": 8
        }
        
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert "ground_radials_info" in data, "Missing ground_radials_info"
        radials_info = data["ground_radials_info"]
        assert radials_info.get("enabled") == True
        assert radials_info.get("num_radials") == 8
        print(f"PASSED: Ground radials - info={radials_info}")

    def test_calculate_dual_polarity(self):
        """Test with dual_active=true (dual polarity)."""
        payload = YAGI_3_ELEMENT.copy()
        payload["antenna_orientation"] = "dual"
        payload["dual_active"] = True
        payload["dual_selected_beam"] = "horizontal"
        
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert "dual_polarity_info" in data, "Missing dual_polarity_info"
        dual_info = data["dual_polarity_info"]
        assert dual_info.get("both_active") == True, "Expected both_active=True"
        print(f"PASSED: Dual polarity - info={dual_info}")

    def test_calculate_coax_loss(self):
        """Test with coax_type and coax_length_ft set."""
        payload = YAGI_3_ELEMENT.copy()
        payload["coax_type"] = "rg213"
        payload["coax_length_ft"] = 150
        payload["transmit_power_watts"] = 500
        
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert "coax_loss_db" in data, "Missing coax_loss_db"
        assert "coax_info" in data, "Missing coax_info"
        coax_info = data["coax_info"]
        assert coax_info.get("type") == "RG-213/U"
        assert coax_info.get("length_ft") == 150
        assert data["coax_loss_db"] > 0, "Expected positive coax loss"
        print(f"PASSED: Coax loss - loss={data['coax_loss_db']} dB, info={coax_info}")

    def test_calculate_returns_elevation_pattern(self):
        """Test elevation_pattern data is returned with magnitude values."""
        response = requests.post(f"{BASE_URL}/api/calculate", json=YAGI_3_ELEMENT)
        assert response.status_code == 200
        
        data = response.json()
        assert "elevation_pattern" in data, "Missing elevation_pattern"
        elevation = data["elevation_pattern"]
        assert isinstance(elevation, list), "elevation_pattern should be a list"
        assert len(elevation) > 0, "elevation_pattern should not be empty"
        
        # Check first entry has angle and magnitude
        first = elevation[0]
        assert "angle" in first, "elevation_pattern entry missing 'angle'"
        assert "magnitude" in first, "elevation_pattern entry missing 'magnitude'"
        print(f"PASSED: Elevation pattern - {len(elevation)} points, first={first}")

    def test_calculate_returns_far_field_pattern(self):
        """Test far_field_pattern data is returned."""
        response = requests.post(f"{BASE_URL}/api/calculate", json=YAGI_3_ELEMENT)
        assert response.status_code == 200
        
        data = response.json()
        assert "far_field_pattern" in data, "Missing far_field_pattern"
        far_field = data["far_field_pattern"]
        assert isinstance(far_field, list), "far_field_pattern should be a list"
        assert len(far_field) > 0, "far_field_pattern should not be empty"
        print(f"PASSED: Far field pattern - {len(far_field)} points")

    def test_calculate_returns_smith_chart_data(self):
        """Test smith_chart_data is returned."""
        response = requests.post(f"{BASE_URL}/api/calculate", json=YAGI_3_ELEMENT)
        assert response.status_code == 200
        
        data = response.json()
        assert "smith_chart_data" in data, "Missing smith_chart_data"
        smith = data["smith_chart_data"]
        assert isinstance(smith, list), "smith_chart_data should be a list"
        print(f"PASSED: Smith chart data - {len(smith)} points")

    def test_calculate_returns_wind_load(self):
        """Test wind_load data is returned."""
        response = requests.post(f"{BASE_URL}/api/calculate", json=YAGI_3_ELEMENT)
        assert response.status_code == 200
        
        data = response.json()
        assert "wind_load" in data, "Missing wind_load"
        wind = data["wind_load"]
        assert "total_area_sqft" in wind, "Missing total_area_sqft in wind_load"
        assert "wind_ratings" in wind, "Missing wind_ratings in wind_load"
        print(f"PASSED: Wind load - area={wind['total_area_sqft']} sqft, ratings={list(wind['wind_ratings'].keys())}")

    def test_calculate_returns_reflected_power(self):
        """Test reflected_power fields are returned."""
        response = requests.post(f"{BASE_URL}/api/calculate", json=YAGI_3_ELEMENT)
        assert response.status_code == 200
        
        data = response.json()
        assert "reflected_power_100w" in data, "Missing reflected_power_100w"
        assert "forward_power_100w" in data, "Missing forward_power_100w"
        assert "return_loss_db" in data, "Missing return_loss_db"
        print(f"PASSED: Reflected power - reflected_100w={data['reflected_power_100w']}W, forward_100w={data['forward_power_100w']}W, return_loss={data['return_loss_db']}dB")


class TestAutoTuneEndpoint:
    """Tests for POST /api/auto-tune."""

    def test_auto_tune_returns_optimized_elements(self):
        """Test auto-tune returns optimized elements."""
        payload = {
            "num_elements": 3,
            "height_from_ground": 54,
            "height_unit": "ft",
            "boom_diameter": 2,
            "boom_unit": "inches",
            "band": "11m_cb",
            "frequency_mhz": 27.185,
            "use_reflector": True,
            "spacing_mode": "normal",
            "element_diameter": 0.5
        }
        
        response = requests.post(f"{BASE_URL}/api/auto-tune", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "optimized_elements" in data, "Missing optimized_elements"
        assert "predicted_swr" in data, "Missing predicted_swr"
        assert "predicted_gain" in data, "Missing predicted_gain"
        assert "predicted_fb_ratio" in data, "Missing predicted_fb_ratio"
        
        elements = data["optimized_elements"]
        assert len(elements) == 3, f"Expected 3 elements, got {len(elements)}"
        print(f"PASSED: Auto-tune - {len(elements)} elements, SWR={data['predicted_swr']}, Gain={data['predicted_gain']} dBi")


class TestOptimizeHeightEndpoint:
    """Tests for POST /api/optimize-height."""

    def test_optimize_height_returns_results(self):
        """Test height optimization returns optimal height and results."""
        payload = {
            "num_elements": 3,
            "elements": YAGI_3_ELEMENT["elements"],
            "boom_diameter": 2,
            "boom_unit": "inches",
            "band": "11m_cb",
            "frequency_mhz": 27.185,
            "min_height": 30,
            "max_height": 80,
            "step": 5
        }
        
        response = requests.post(f"{BASE_URL}/api/optimize-height", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "optimal_height" in data, "Missing optimal_height"
        assert "optimal_swr" in data, "Missing optimal_swr"
        assert "optimal_gain" in data, "Missing optimal_gain"
        assert "heights_tested" in data, "Missing heights_tested"
        
        heights = data["heights_tested"]
        assert len(heights) > 0, "heights_tested should not be empty"
        print(f"PASSED: Optimize height - optimal={data['optimal_height']}ft, SWR={data['optimal_swr']}, Gain={data['optimal_gain']} dBi, {len(heights)} heights tested")


class TestAuthEndpoints:
    """Tests for auth endpoints."""

    def test_login_admin_success(self):
        """Test login with admin credentials."""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "fallstommy@gmail.com",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "token" in data, "Missing token"
        assert "user" in data, "Missing user"
        user = data["user"]
        assert user["email"] == "fallstommy@gmail.com"
        print(f"PASSED: Admin login - token present, user={user['email']}")
        return data["token"]

    def test_login_invalid_credentials(self):
        """Test login with invalid credentials returns 401."""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "wrong@example.com",
            "password": "wrongpass"
        })
        assert response.status_code == 401, f"Expected 401 for invalid credentials, got {response.status_code}"
        print("PASSED: Invalid credentials returns 401")


class TestSubscriptionEndpoints:
    """Tests for subscription tier endpoints."""

    def test_get_subscription_tiers(self):
        """Test GET /api/subscription/tiers returns tier data with features."""
        response = requests.get(f"{BASE_URL}/api/subscription/tiers")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "tiers" in data, "Missing tiers"
        tiers = data["tiers"]
        
        # Check bronze, silver, gold exist with features
        for tier_key in ["bronze_monthly", "silver_monthly", "gold_monthly"]:
            assert tier_key in tiers, f"Missing {tier_key}"
            tier = tiers[tier_key]
            assert "features" in tier, f"{tier_key} missing features"
            assert isinstance(tier["features"], list), f"{tier_key} features should be list"
        
        # Gold should have 'all' or many features
        gold = tiers["gold_monthly"]
        gold_features = gold["features"]
        assert "all" in gold_features or len(gold_features) >= 10, f"Gold tier should have 'all' or many features"
        
        print(f"PASSED: Subscription tiers - {list(tiers.keys())}")

    def test_app_update_returns_version(self):
        """Test GET /api/app-update returns version info."""
        response = requests.get(f"{BASE_URL}/api/app-update")
        assert response.status_code == 200
        
        data = response.json()
        assert "version" in data, "Missing version"
        print(f"PASSED: App update - version={data.get('version')}")


class TestAdminPricingEndpoints:
    """Tests for admin pricing endpoints (requires auth)."""

    def get_admin_token(self):
        """Helper to get admin token."""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "fallstommy@gmail.com",
            "password": "admin123"
        })
        if response.status_code == 200:
            return response.json().get("token")
        return None

    def test_admin_pricing_requires_auth(self):
        """Test GET /api/admin/pricing returns 403 without auth."""
        response = requests.get(f"{BASE_URL}/api/admin/pricing")
        assert response.status_code == 403, f"Expected 403 without auth, got {response.status_code}"
        print("PASSED: Admin pricing requires auth (403)")

    def test_admin_pricing_returns_tiers_with_features(self):
        """Test GET /api/admin/pricing returns all tiers with features (requires admin)."""
        token = self.get_admin_token()
        if not token:
            pytest.skip("Could not get admin token")
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/admin/pricing", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Check bronze, silver, gold with features
        for tier in ["bronze", "silver", "gold"]:
            assert tier in data, f"Missing {tier} tier"
            tier_data = data[tier]
            assert "features" in tier_data, f"{tier} missing features"
            features = tier_data["features"]
            print(f"  {tier}: {len(features)} features")
        
        print(f"PASSED: Admin pricing - bronze/silver/gold with features")

    def test_admin_pricing_update_features(self):
        """Test PUT /api/admin/pricing updates tier features (requires admin)."""
        token = self.get_admin_token()
        if not token:
            pytest.skip("Could not get admin token")
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # First get current pricing
        get_response = requests.get(f"{BASE_URL}/api/admin/pricing", headers=headers)
        if get_response.status_code != 200:
            pytest.skip("Could not get current pricing")
        
        current = get_response.json()
        
        # Update with same values (non-destructive test)
        update_payload = {
            "bronze_monthly_price": current["bronze"]["monthly_price"],
            "bronze_yearly_price": current["bronze"]["yearly_price"],
            "bronze_max_elements": current["bronze"]["max_elements"],
            "bronze_features": current["bronze"]["features"],
            "silver_monthly_price": current["silver"]["monthly_price"],
            "silver_yearly_price": current["silver"]["yearly_price"],
            "silver_max_elements": current["silver"]["max_elements"],
            "silver_features": current["silver"]["features"],
            "gold_monthly_price": current["gold"]["monthly_price"],
            "gold_yearly_price": current["gold"]["yearly_price"],
            "gold_max_elements": current["gold"]["max_elements"],
            "gold_features": current["gold"]["features"]
        }
        
        response = requests.put(f"{BASE_URL}/api/admin/pricing", json=update_payload, headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") == True, "Expected success=True"
        print("PASSED: Admin pricing update")


class TestSaveLoadDesigns:
    """Tests for save/load designs (requires auth)."""

    def get_user_token(self):
        """Helper to get user token."""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "fallstommy@gmail.com",
            "password": "admin123"
        })
        if response.status_code == 200:
            return response.json().get("token")
        return None

    def test_save_design_with_spacing_state(self):
        """Test POST /api/designs/save saves design with spacing_state."""
        token = self.get_user_token()
        if not token:
            pytest.skip("Could not get user token")
        
        headers = {"Authorization": f"Bearer {token}"}
        
        payload = {
            "name": "TEST_QA_Design_" + str(int(__import__("time").time())),
            "description": "Test design from QA",
            "design_data": YAGI_3_ELEMENT,
            "spacing_state": {
                "level": 1.0,
                "mode": "normal",
                "presets": {"tight": 0.7, "normal": 1.0, "wide": 1.3}
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/designs/save", json=payload, headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "id" in data, "Missing id"
        assert "name" in data, "Missing name"
        print(f"PASSED: Save design - id={data['id']}, name={data['name']}")
        return data["id"]

    def test_get_designs_list(self):
        """Test GET /api/designs lists saved designs."""
        token = self.get_user_token()
        if not token:
            pytest.skip("Could not get user token")
        
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(f"{BASE_URL}/api/designs", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert isinstance(data, list), "Expected list of designs"
        print(f"PASSED: Get designs - {len(data)} designs found")


class TestPublicEndpoints:
    """Tests for public endpoints."""

    def test_get_bands(self):
        """Test GET /api/bands returns band definitions."""
        response = requests.get(f"{BASE_URL}/api/bands")
        assert response.status_code == 200
        
        data = response.json()
        assert "11m_cb" in data, "Missing 11m_cb band"
        assert "10m" in data, "Missing 10m band"
        print(f"PASSED: Get bands - {list(data.keys())}")

    def test_get_tutorial(self):
        """Test GET /api/tutorial returns content."""
        response = requests.get(f"{BASE_URL}/api/tutorial")
        assert response.status_code == 200
        
        data = response.json()
        assert "content" in data, "Missing content"
        assert len(data["content"]) > 100, "Tutorial content too short"
        print(f"PASSED: Get tutorial - {len(data['content'])} chars")

    def test_get_designer_info(self):
        """Test GET /api/designer-info returns content."""
        response = requests.get(f"{BASE_URL}/api/designer-info")
        assert response.status_code == 200
        
        data = response.json()
        assert "content" in data, "Missing content"
        print(f"PASSED: Get designer info - {len(data['content'])} chars")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
