"""
Test suite for new SMA Antenna Calculator features:
1. Scale Button (Frequency Scaling) - Frontend UI
2. Save/Load gamma settings persistence - Backend API
3. Power Advisory Panel - Frontend (requires gamma results)
4. Backend health check
"""
import pytest
import requests
import os
import json

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test user credentials for save/load testing
TEST_EMAIL = f"test_scale_{os.getpid()}@example.com"
TEST_PASSWORD = "testpass123"
TEST_NAME = "Scale Test User"


class TestHealthCheck:
    """Test backend health endpoint"""
    
    def test_health_endpoint(self):
        """GET /api/health should return API and DB status"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Health check failed: {response.status_code}"
        data = response.json()
        assert "api" in data, "Missing 'api' key in health response"
        assert data["api"] == "up", f"API not up: {data['api']}"
        assert "database" in data, "Missing 'database' key in health response"
        assert data["database"] == "up", f"Database not up: {data['database']}"
        print(f"PASS: Health check - API: {data['api']}, DB: {data['database']}")


class TestSaveLoadGammaSettings:
    """Test Save/Load with new gamma tube settings"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Register test user and get auth token"""
        # Try to register new user
        register_response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
            "name": TEST_NAME
        })
        
        if register_response.status_code == 200:
            token = register_response.json().get("token")
            print(f"PASS: Created test user {TEST_EMAIL}")
            return token
        
        # If user exists, try login
        if register_response.status_code == 400:
            login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD
            })
            if login_response.status_code == 200:
                token = login_response.json().get("token")
                print(f"PASS: Logged in as {TEST_EMAIL}")
                return token
        
        pytest.skip(f"Could not authenticate: {register_response.text}")
    
    def test_save_design_with_gamma_settings(self, auth_token):
        """POST /api/designs/save should accept gamma tube settings in spacing_state"""
        headers = {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
        
        # Design data with full gamma settings
        design_payload = {
            "name": "TEST_Gamma_Full_Settings",
            "description": "Test design with all gamma settings",
            "design_data": {
                "num_elements": 2,
                "elements": [
                    {"element_type": "reflector", "length": "216", "diameter": "0.5", "position": "0"},
                    {"element_type": "driven", "length": "204", "diameter": "0.5", "position": "48"}
                ],
                "height_from_ground": "54",
                "height_unit": "ft",
                "boom_diameter": "1.5",
                "boom_unit": "inches",
                "band": "11m_cb",
                "frequency_mhz": "27.185",
                "feed_type": "gamma"
            },
            "spacing_state": {
                "spacingMode": "normal",
                "spacingLevel": "1.0",
                "spacingNudgeCount": 0,
                "drivenNudgeCount": 0,
                "reflectorNudgeCount": 5,
                "reflectorPreset": "close",
                "gammaTubeOd": "0.875",
                "gammaTubeLength": 22.5,
                "originalDrivenLength": "210",
                "gammaRodDia": "0.5",
                "gammaRodSpacing": "3.5",
                "gammaCapPf": "75",
                "gammaBarPos": 18,
                "gammaRodInsertion": 8.0,
                "coaxType": "ldf5-50a",
                "coaxLengthFt": "100",
                "transmitPowerWatts": "1500",
                "buildStyle": "normal"
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/designs/save", headers=headers, json=design_payload)
        assert response.status_code == 200, f"Save design failed: {response.status_code} - {response.text}"
        
        data = response.json()
        assert "id" in data, "Missing design ID in response"
        assert "name" in data, "Missing design name in response"
        assert data["name"] == "TEST_Gamma_Full_Settings"
        
        print(f"PASS: Saved design with ID: {data['id']}")
        return data["id"]
    
    def test_load_design_with_gamma_settings(self, auth_token):
        """GET /api/designs/<id> should return gamma tube settings in spacing_state"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # First, list designs to find our test design
        list_response = requests.get(f"{BASE_URL}/api/designs", headers=headers)
        assert list_response.status_code == 200, f"List designs failed: {list_response.status_code}"
        
        designs = list_response.json()
        test_design = None
        for d in designs:
            if d["name"] == "TEST_Gamma_Full_Settings":
                test_design = d
                break
        
        if not test_design:
            # Need to create it first
            save_result = self.test_save_design_with_gamma_settings(auth_token)
            list_response = requests.get(f"{BASE_URL}/api/designs", headers=headers)
            designs = list_response.json()
            for d in designs:
                if d["name"] == "TEST_Gamma_Full_Settings":
                    test_design = d
                    break
        
        assert test_design is not None, "Test design not found"
        
        # Load the design
        design_id = test_design["id"]
        response = requests.get(f"{BASE_URL}/api/designs/{design_id}", headers=headers)
        assert response.status_code == 200, f"Load design failed: {response.status_code}"
        
        data = response.json()
        
        # Verify design_data
        assert "design_data" in data, "Missing design_data"
        assert data["design_data"]["feed_type"] == "gamma", "Feed type not gamma"
        
        # Verify spacing_state contains new gamma fields
        assert "spacing_state" in data, "Missing spacing_state"
        ss = data["spacing_state"]
        
        # Check new gamma tube settings
        assert "gammaTubeOd" in ss, "Missing gammaTubeOd in spacing_state"
        assert ss["gammaTubeOd"] == "0.875", f"gammaTubeOd mismatch: {ss.get('gammaTubeOd')}"
        
        assert "gammaTubeLength" in ss, "Missing gammaTubeLength in spacing_state"
        assert ss["gammaTubeLength"] == 22.5, f"gammaTubeLength mismatch: {ss.get('gammaTubeLength')}"
        
        assert "originalDrivenLength" in ss, "Missing originalDrivenLength in spacing_state"
        assert ss["originalDrivenLength"] == "210", f"originalDrivenLength mismatch: {ss.get('originalDrivenLength')}"
        
        # Check reflector settings
        assert "reflectorNudgeCount" in ss, "Missing reflectorNudgeCount"
        assert ss["reflectorNudgeCount"] == 5, f"reflectorNudgeCount mismatch: {ss.get('reflectorNudgeCount')}"
        
        assert "reflectorPreset" in ss, "Missing reflectorPreset"
        assert ss["reflectorPreset"] == "close", f"reflectorPreset mismatch: {ss.get('reflectorPreset')}"
        
        # Check build style
        assert "buildStyle" in ss, "Missing buildStyle"
        assert ss["buildStyle"] == "normal", f"buildStyle mismatch: {ss.get('buildStyle')}"
        
        print(f"PASS: Loaded design with all gamma settings preserved")
        print(f"  gammaTubeOd: {ss.get('gammaTubeOd')}")
        print(f"  gammaTubeLength: {ss.get('gammaTubeLength')}")
        print(f"  originalDrivenLength: {ss.get('originalDrivenLength')}")
        print(f"  reflectorNudgeCount: {ss.get('reflectorNudgeCount')}")
        print(f"  reflectorPreset: {ss.get('reflectorPreset')}")
        
    def test_delete_test_design(self, auth_token):
        """Cleanup: Delete test designs"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # List and delete all TEST_ prefixed designs
        list_response = requests.get(f"{BASE_URL}/api/designs", headers=headers)
        if list_response.status_code == 200:
            designs = list_response.json()
            for d in designs:
                if d["name"].startswith("TEST_"):
                    delete_response = requests.delete(f"{BASE_URL}/api/designs/{d['id']}", headers=headers)
                    if delete_response.status_code == 200:
                        print(f"PASS: Deleted test design: {d['name']}")


class TestCalculateWithGamma:
    """Test /api/calculate with gamma match to verify power advisory data is available"""
    
    def test_calculate_gamma_match_returns_matching_info(self):
        """POST /api/calculate with gamma feed should return matching_info.gamma_design"""
        payload = {
            "num_elements": 2,
            "elements": [
                {"element_type": "reflector", "length": 216, "diameter": 0.5, "position": 0},
                {"element_type": "driven", "length": 204, "diameter": 0.5, "position": 48}
            ],
            "height_from_ground": 54,
            "height_unit": "ft",
            "boom_diameter": 1.5,
            "boom_unit": "inches",
            "band": "11m_cb",
            "frequency_mhz": 27.185,
            "feed_type": "gamma",
            "transmit_power_watts": 500
        }
        
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
        assert response.status_code == 200, f"Calculate failed: {response.status_code} - {response.text}"
        
        data = response.json()
        
        # Verify matching_info exists
        assert "matching_info" in data, "Missing matching_info in response"
        assert data["matching_info"] is not None, "matching_info is null"
        
        # Verify gamma_design exists
        assert "gamma_design" in data["matching_info"], "Missing gamma_design in matching_info"
        gd = data["matching_info"]["gamma_design"]
        
        # Check for fields needed by power advisory
        assert "capacitance_pf" in gd, "Missing capacitance_pf"
        assert gd["capacitance_pf"] > 0, f"Invalid capacitance_pf: {gd['capacitance_pf']}"
        
        print(f"PASS: Gamma design response includes:")
        print(f"  capacitance_pf: {gd.get('capacitance_pf')}")
        print(f"  swr_gamma: {gd.get('swr_gamma')}")
        print(f"  tube_length_inches: {data['matching_info'].get('tube_length_inches')}")
        
    def test_calculate_high_power_gamma(self):
        """POST /api/calculate with 1500W should work for power advisory calculations"""
        payload = {
            "num_elements": 3,
            "elements": [
                {"element_type": "reflector", "length": 216, "diameter": 0.5, "position": 0},
                {"element_type": "driven", "length": 198, "diameter": 0.5, "position": 48},
                {"element_type": "director", "length": 192, "diameter": 0.5, "position": 96}
            ],
            "height_from_ground": 54,
            "height_unit": "ft",
            "boom_diameter": 1.5,
            "boom_unit": "inches",
            "band": "11m_cb",
            "frequency_mhz": 27.185,
            "feed_type": "gamma",
            "transmit_power_watts": 1500,
            "coax_type": "ldf5-50a",
            "coax_length_ft": 100
        }
        
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
        assert response.status_code == 200, f"Calculate failed: {response.status_code}"
        
        data = response.json()
        
        # Basic checks
        assert "swr" in data, "Missing SWR"
        assert "matching_info" in data, "Missing matching_info"
        assert data["matching_info"]["gamma_design"] is not None, "Missing gamma_design"
        
        # Power-related fields
        gd = data["matching_info"]["gamma_design"]
        cap_pf = gd.get("capacitance_pf", 0)
        swr = data.get("swr", 2.0)
        
        # Calculate what power advisory would show (mimicking frontend logic)
        power_w = 1500
        freq_hz = 27.185e6
        v_feed = (power_w * 50 * swr) ** 0.5
        x_cap = 1 / (2 * 3.14159 * freq_hz * cap_pf * 1e-12) if cap_pf > 0 else 0
        i_ant = (power_w / 50) ** 0.5
        v_cap = i_ant * x_cap * (swr ** 0.5)
        rod_current = i_ant * (swr ** 0.5)
        
        print(f"PASS: High power (1500W) gamma calculation:")
        print(f"  SWR: {swr}")
        print(f"  Capacitance: {cap_pf} pF")
        print(f"  Feedpoint voltage: {v_feed:.0f}V RMS")
        print(f"  Capacitor voltage: {v_cap:.0f}V RMS")
        print(f"  Rod current: {rod_current:.1f}A")
        
        # Power advisory should show warnings at these levels
        if v_cap > 500:
            print(f"  -> Cap voltage WARNING would show (>{500}V)")
        if rod_current > 5:
            print(f"  -> Rod current WARNING would show (>{5}A)")
        if v_feed > 300:
            print(f"  -> Feedpoint voltage WARNING would show (>{300}V)")


class TestFrequencyScaling:
    """Test that frequency scaling math works (frontend logic, verified via API)"""
    
    def test_scaled_design_calculates_correctly(self):
        """A scaled design should still calculate successfully"""
        # Original design at 27.185 MHz (CB)
        original_driven_length = 204  # inches
        original_freq = 27.185
        target_freq = 144.0  # 2m band
        
        # Scale ratio
        ratio = original_freq / target_freq
        scaled_driven_length = original_driven_length * ratio
        scaled_position = 48 * ratio  # Reflector-to-driven spacing
        
        payload = {
            "num_elements": 2,
            "elements": [
                {"element_type": "reflector", "length": 216 * ratio, "diameter": 0.5, "position": 0},
                {"element_type": "driven", "length": scaled_driven_length, "diameter": 0.5, "position": scaled_position}
            ],
            "height_from_ground": 54 * ratio,
            "height_unit": "ft",
            "boom_diameter": 1.5,
            "boom_unit": "inches",
            "band": "2m",
            "frequency_mhz": target_freq,
            "feed_type": "gamma"
        }
        
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
        assert response.status_code == 200, f"Scaled design calculate failed: {response.status_code}"
        
        data = response.json()
        assert "swr" in data, "Missing SWR in response"
        assert "gain_dbi" in data, "Missing gain in response"
        
        print(f"PASS: Scaled design ({original_freq} -> {target_freq} MHz)")
        print(f"  Scale ratio: {ratio:.4f}")
        print(f"  Driven length: {original_driven_length}\" -> {scaled_driven_length:.2f}\"")
        print(f"  SWR: {data['swr']}")
        print(f"  Gain: {data['gain_dbi']} dBi")
        
    def test_scale_to_10m_band(self):
        """Scale from CB to 10m and verify calculation works"""
        original_freq = 27.185
        target_freq = 28.5  # 10m band
        ratio = original_freq / target_freq
        
        payload = {
            "num_elements": 3,
            "elements": [
                {"element_type": "reflector", "length": 216 * ratio, "diameter": 0.5, "position": 0},
                {"element_type": "driven", "length": 204 * ratio, "diameter": 0.5, "position": 48 * ratio},
                {"element_type": "director", "length": 195 * ratio, "diameter": 0.5, "position": 96 * ratio}
            ],
            "height_from_ground": 54,
            "height_unit": "ft",
            "boom_diameter": 1.5,
            "boom_unit": "inches",
            "band": "10m",
            "frequency_mhz": target_freq,
            "feed_type": "gamma"
        }
        
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
        assert response.status_code == 200, f"10m scale calculate failed: {response.status_code}"
        
        data = response.json()
        print(f"PASS: Scaled to 10m ({target_freq} MHz)")
        print(f"  SWR: {data['swr']}")
        print(f"  Gain: {data['gain_dbi']} dBi")


class TestSaveDesignModels:
    """Test backend models accept spacing_state with gamma fields"""
    
    def test_spacing_state_model_fields(self):
        """Verify models.py SaveDesignRequest accepts all gamma settings"""
        # This tests the Pydantic model by sending a save request
        # Registration is needed for save
        
        # Try to create a throwaway user for model testing
        test_email = f"model_test_{os.getpid()}@example.com"
        register_response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": test_email,
            "password": "testpass123",
            "name": "Model Tester"
        })
        
        if register_response.status_code != 200:
            # Try login
            login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
                "email": test_email,
                "password": "testpass123"
            })
            if login_response.status_code != 200:
                pytest.skip("Could not create test user for model testing")
            token = login_response.json().get("token")
        else:
            token = register_response.json().get("token")
        
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        
        # Comprehensive spacing_state with ALL fields that should be persisted
        spacing_state = {
            "spacingMode": "normal",
            "spacingLevel": "1.0",
            "spacingNudgeCount": 0,
            "closeDriven": False,
            "farDriven": False,
            "closeDir1": False,
            "farDir1": False,
            "closeDir2": False,
            "farDir2": False,
            "drivenNudgeCount": 0,
            "dir1NudgeCount": 0,
            "dir2NudgeCount": 0,
            "dirPresets": {},
            "dirNudgeCounts": {},
            "boomLockEnabled": False,
            "maxBoomLength": "120",
            "spacingLockEnabled": False,
            "elementUnit": "inches",
            "gainMode": "realworld",
            "coaxType": "ldf5-50a",
            "coaxLengthFt": "100",
            "transmitPowerWatts": "500",
            "gammaRodDia": "0.5",
            "gammaRodSpacing": "3.5",
            "gammaCapPf": None,
            "gammaBarPos": 18,
            "gammaRodInsertion": 8.0,
            "hairpinRodDia": "0.25",
            "hairpinRodSpacing": "1.0",
            "hairpinLengthIn": "",
            "hairpinBoomGap": 1.0,
            # NEW fields that were missing in save/load:
            "gammaTubeOd": "0.75",
            "gammaTubeLength": 22.0,
            "originalDrivenLength": "210.5",
            "reflectorNudgeCount": 3,
            "reflectorPreset": "normal",
            "buildStyle": "tight"
        }
        
        payload = {
            "name": "TEST_Model_All_Fields",
            "description": "Testing all spacing_state fields",
            "design_data": {
                "num_elements": 2,
                "elements": [
                    {"element_type": "reflector", "length": "216", "diameter": "0.5", "position": "0"},
                    {"element_type": "driven", "length": "204", "diameter": "0.5", "position": "48"}
                ],
                "band": "11m_cb",
                "frequency_mhz": "27.185"
            },
            "spacing_state": spacing_state
        }
        
        response = requests.post(f"{BASE_URL}/api/designs/save", headers=headers, json=payload)
        assert response.status_code == 200, f"Save with all fields failed: {response.status_code} - {response.text}"
        
        design_id = response.json().get("id")
        
        # Load and verify
        load_response = requests.get(f"{BASE_URL}/api/designs/{design_id}", headers=headers)
        assert load_response.status_code == 200, f"Load failed: {load_response.status_code}"
        
        loaded = load_response.json()
        ss = loaded.get("spacing_state", {})
        
        # Verify new fields
        new_fields = ["gammaTubeOd", "gammaTubeLength", "originalDrivenLength", "reflectorNudgeCount", "reflectorPreset", "buildStyle"]
        for field in new_fields:
            assert field in ss, f"Missing field: {field}"
            print(f"  {field}: {ss.get(field)}")
        
        print(f"PASS: All spacing_state fields saved and loaded correctly")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/designs/{design_id}", headers=headers)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
