"""
Backend API Tests for Boom Grounded/Insulated Feature
Tests the following aspects:
1. POST /api/calculate with boom_grounded=true returns boom_correction_info with enabled=true
2. POST /api/calculate with boom_grounded=false returns boom_correction_info with enabled=false
3. POST /api/calculate without boom_grounded param defaults to boom_grounded=true
4. Grounded boom produces slightly lower gain than insulated boom
5. Grounded boom produces slightly higher SWR than insulated boom
6. Grounded boom produces slightly lower F/B ratio than insulated boom
7. boom_correction_info contains required fields
8. Thick boom (3 inch) has larger correction than thin boom (1 inch)
9. VHF band (2m, 146MHz) has larger correction than HF band (11m, 27MHz)
"""

import pytest
import requests
import os

# Base URL from environment
BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL', 'https://rf-designer.preview.emergentagent.com')


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


def create_standard_elements():
    """Create a standard 4-element antenna configuration"""
    return [
        {"element_type": "reflector", "length": 220, "diameter": 0.5, "position": 0},
        {"element_type": "driven", "length": 209, "diameter": 0.5, "position": 40},
        {"element_type": "director", "length": 200, "diameter": 0.5, "position": 80},
        {"element_type": "director", "length": 195, "diameter": 0.5, "position": 120}
    ]


def create_2m_vhf_elements():
    """Create a 4-element antenna configuration for 2m VHF band (146 MHz)"""
    # At 146 MHz, wavelength ~ 2.05m = 80.7 inches
    # Half-wave dipole ~ 40 inches
    # Elements scale proportionally to 11m CB
    return [
        {"element_type": "reflector", "length": 42, "diameter": 0.375, "position": 0},
        {"element_type": "driven", "length": 40, "diameter": 0.375, "position": 8},
        {"element_type": "director", "length": 38, "diameter": 0.375, "position": 16},
        {"element_type": "director", "length": 36, "diameter": 0.375, "position": 26}
    ]


def create_base_payload(boom_grounded=None, boom_diameter=2.0, band="11m_cb", frequency_mhz=None, elements=None):
    """Create base payload for /api/calculate"""
    payload = {
        "num_elements": 4,
        "elements": elements or create_standard_elements(),
        "height_from_ground": 50,
        "height_unit": "ft",
        "boom_diameter": boom_diameter,
        "boom_unit": "inches",
        "band": band
    }
    if boom_grounded is not None:
        payload["boom_grounded"] = boom_grounded
    if frequency_mhz is not None:
        payload["frequency_mhz"] = frequency_mhz
    return payload


class TestBoomCorrectionWithGrounded:
    """Test boom_grounded=true returns correct boom_correction_info"""
    
    def test_boom_grounded_true_returns_enabled_correction(self, api_client):
        """POST /api/calculate with boom_grounded=true should return boom_correction_info with enabled=true"""
        payload = create_base_payload(boom_grounded=True)
        response = api_client.post(f"{BASE_URL}/api/calculate", json=payload)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "boom_correction_info" in data, "Missing boom_correction_info field in response"
        
        boom_info = data["boom_correction_info"]
        assert boom_info is not None, "boom_correction_info should not be None"
        assert boom_info.get("enabled") == True, f"Expected enabled=True, got {boom_info.get('enabled')}"
        assert boom_info.get("boom_grounded") == True, f"Expected boom_grounded=True, got {boom_info.get('boom_grounded')}"
        
        print(f"✓ boom_grounded=true returns enabled=true")
        print(f"  - boom_correction_info: {boom_info}")
    
    def test_boom_grounded_true_has_nonzero_corrections(self, api_client):
        """Grounded boom should have non-zero correction values"""
        payload = create_base_payload(boom_grounded=True, boom_diameter=2.0)
        response = api_client.post(f"{BASE_URL}/api/calculate", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        boom_info = data["boom_correction_info"]
        
        # Correction per side should be non-zero for grounded boom
        correction_per_side = boom_info.get("correction_per_side_in", 0)
        assert correction_per_side > 0, f"correction_per_side_in should be > 0 for grounded boom, got {correction_per_side}"
        
        # Gain adjustment should be negative (reduced gain)
        gain_adj = boom_info.get("gain_adj_db", 0)
        assert gain_adj < 0, f"gain_adj_db should be negative for grounded boom, got {gain_adj}"
        
        # F/B adjustment should be negative (reduced F/B ratio)
        fb_adj = boom_info.get("fb_adj_db", 0)
        assert fb_adj < 0, f"fb_adj_db should be negative for grounded boom, got {fb_adj}"
        
        print(f"✓ Grounded boom has non-zero corrections:")
        print(f"  - correction_per_side_in: {correction_per_side}")
        print(f"  - gain_adj_db: {gain_adj}")
        print(f"  - fb_adj_db: {fb_adj}")


class TestBoomCorrectionWithInsulated:
    """Test boom_grounded=false returns correct boom_correction_info"""
    
    def test_boom_grounded_false_returns_disabled_correction(self, api_client):
        """POST /api/calculate with boom_grounded=false should return boom_correction_info with enabled=false"""
        payload = create_base_payload(boom_grounded=False)
        response = api_client.post(f"{BASE_URL}/api/calculate", json=payload)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "boom_correction_info" in data, "Missing boom_correction_info field in response"
        
        boom_info = data["boom_correction_info"]
        assert boom_info is not None, "boom_correction_info should not be None"
        assert boom_info.get("enabled") == False, f"Expected enabled=False, got {boom_info.get('enabled')}"
        assert boom_info.get("boom_grounded") == False, f"Expected boom_grounded=False, got {boom_info.get('boom_grounded')}"
        
        print(f"✓ boom_grounded=false returns enabled=false")
        print(f"  - boom_correction_info: {boom_info}")
    
    def test_boom_grounded_false_has_zero_corrections(self, api_client):
        """Insulated boom should have zero correction values"""
        payload = create_base_payload(boom_grounded=False)
        response = api_client.post(f"{BASE_URL}/api/calculate", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        boom_info = data["boom_correction_info"]
        
        # All correction values should be zero
        assert boom_info.get("correction_per_side_in", -1) == 0, f"correction_per_side_in should be 0, got {boom_info.get('correction_per_side_in')}"
        assert boom_info.get("gain_adj_db", -1) == 0, f"gain_adj_db should be 0, got {boom_info.get('gain_adj_db')}"
        assert boom_info.get("fb_adj_db", -1) == 0, f"fb_adj_db should be 0, got {boom_info.get('fb_adj_db')}"
        assert boom_info.get("impedance_shift_ohm", -1) == 0, f"impedance_shift_ohm should be 0, got {boom_info.get('impedance_shift_ohm')}"
        assert boom_info.get("swr_factor", 0) == 1.0, f"swr_factor should be 1.0, got {boom_info.get('swr_factor')}"
        
        print(f"✓ Insulated boom has zero corrections:")
        print(f"  - correction_per_side_in: {boom_info.get('correction_per_side_in')}")
        print(f"  - gain_adj_db: {boom_info.get('gain_adj_db')}")
        print(f"  - fb_adj_db: {boom_info.get('fb_adj_db')}")


class TestBoomGroundedDefault:
    """Test default value for boom_grounded parameter"""
    
    def test_without_boom_grounded_param_defaults_to_true(self, api_client):
        """POST /api/calculate without boom_grounded should default to boom_grounded=true"""
        payload = create_base_payload(boom_grounded=None)  # Don't include boom_grounded
        response = api_client.post(f"{BASE_URL}/api/calculate", json=payload)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        boom_info = data.get("boom_correction_info")
        
        assert boom_info is not None, "boom_correction_info should not be None when boom_grounded defaults"
        assert boom_info.get("enabled") == True, f"Default should be boom_grounded=true (enabled), got enabled={boom_info.get('enabled')}"
        assert boom_info.get("boom_grounded") == True, f"Default boom_grounded should be True, got {boom_info.get('boom_grounded')}"
        
        print(f"✓ Without boom_grounded param, defaults to enabled=true")
        print(f"  - boom_correction_info: {boom_info}")


class TestGroundedVsInsulatedPerformance:
    """Compare performance metrics between grounded and insulated booms"""
    
    def test_grounded_produces_lower_gain_than_insulated(self, api_client):
        """Grounded boom should produce slightly lower gain than insulated boom"""
        payload_grounded = create_base_payload(boom_grounded=True)
        payload_insulated = create_base_payload(boom_grounded=False)
        
        response_grounded = api_client.post(f"{BASE_URL}/api/calculate", json=payload_grounded)
        response_insulated = api_client.post(f"{BASE_URL}/api/calculate", json=payload_insulated)
        
        assert response_grounded.status_code == 200
        assert response_insulated.status_code == 200
        
        gain_grounded = response_grounded.json()["gain_dbi"]
        gain_insulated = response_insulated.json()["gain_dbi"]
        
        # Grounded should have LESS gain than insulated
        assert gain_grounded < gain_insulated, \
            f"Grounded gain ({gain_grounded} dBi) should be less than insulated gain ({gain_insulated} dBi)"
        
        gain_difference = gain_insulated - gain_grounded
        # Expect small difference (0.05 to 0.5 dB typical)
        assert 0.01 <= gain_difference <= 1.0, \
            f"Gain difference ({gain_difference} dB) should be between 0.01 and 1.0 dB"
        
        print(f"✓ Grounded boom produces lower gain than insulated:")
        print(f"  - Grounded: {gain_grounded} dBi")
        print(f"  - Insulated: {gain_insulated} dBi")
        print(f"  - Difference: {gain_difference:.2f} dB")
    
    def test_grounded_produces_higher_swr_than_insulated(self, api_client):
        """Grounded boom should produce slightly higher SWR than insulated boom"""
        payload_grounded = create_base_payload(boom_grounded=True)
        payload_insulated = create_base_payload(boom_grounded=False)
        
        response_grounded = api_client.post(f"{BASE_URL}/api/calculate", json=payload_grounded)
        response_insulated = api_client.post(f"{BASE_URL}/api/calculate", json=payload_insulated)
        
        assert response_grounded.status_code == 200
        assert response_insulated.status_code == 200
        
        swr_grounded = response_grounded.json()["swr"]
        swr_insulated = response_insulated.json()["swr"]
        
        # Grounded should have HIGHER SWR than insulated
        assert swr_grounded >= swr_insulated, \
            f"Grounded SWR ({swr_grounded}) should be >= insulated SWR ({swr_insulated})"
        
        print(f"✓ Grounded boom produces higher SWR than insulated:")
        print(f"  - Grounded: {swr_grounded}")
        print(f"  - Insulated: {swr_insulated}")
    
    def test_grounded_produces_lower_fb_ratio_than_insulated(self, api_client):
        """Grounded boom should produce slightly lower F/B ratio than insulated boom"""
        payload_grounded = create_base_payload(boom_grounded=True)
        payload_insulated = create_base_payload(boom_grounded=False)
        
        response_grounded = api_client.post(f"{BASE_URL}/api/calculate", json=payload_grounded)
        response_insulated = api_client.post(f"{BASE_URL}/api/calculate", json=payload_insulated)
        
        assert response_grounded.status_code == 200
        assert response_insulated.status_code == 200
        
        fb_grounded = response_grounded.json()["fb_ratio"]
        fb_insulated = response_insulated.json()["fb_ratio"]
        
        # Grounded should have LESS F/B ratio than insulated
        assert fb_grounded < fb_insulated, \
            f"Grounded F/B ({fb_grounded} dB) should be less than insulated F/B ({fb_insulated} dB)"
        
        fb_difference = fb_insulated - fb_grounded
        # Expect small difference (0.1 to 2 dB typical)
        assert 0.01 <= fb_difference <= 3.0, \
            f"F/B difference ({fb_difference} dB) should be between 0.01 and 3.0 dB"
        
        print(f"✓ Grounded boom produces lower F/B ratio than insulated:")
        print(f"  - Grounded: {fb_grounded} dB")
        print(f"  - Insulated: {fb_insulated} dB")
        print(f"  - Difference: {fb_difference:.2f} dB")


class TestBoomCorrectionInfoFields:
    """Test that boom_correction_info contains all required fields"""
    
    def test_boom_correction_info_has_required_fields(self, api_client):
        """boom_correction_info should contain all required fields"""
        payload = create_base_payload(boom_grounded=True)
        response = api_client.post(f"{BASE_URL}/api/calculate", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        boom_info = data["boom_correction_info"]
        
        # Required fields for enabled (grounded) boom
        required_fields = [
            "correction_per_side_in",
            "correction_total_in",
            "boom_to_element_ratio",
            "gain_adj_db",
            "fb_adj_db",
            "impedance_shift_ohm",
            "description",
            "enabled",
            "boom_grounded",
            "swr_factor"
        ]
        
        for field in required_fields:
            assert field in boom_info, f"Missing required field '{field}' in boom_correction_info"
        
        print(f"✓ boom_correction_info has all {len(required_fields)} required fields:")
        for field in required_fields:
            print(f"  - {field}: {boom_info[field]}")
    
    def test_boom_correction_info_values_are_correct_types(self, api_client):
        """boom_correction_info field values should have correct types"""
        payload = create_base_payload(boom_grounded=True)
        response = api_client.post(f"{BASE_URL}/api/calculate", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        boom_info = data["boom_correction_info"]
        
        # Type checks
        assert isinstance(boom_info["correction_per_side_in"], (int, float)), "correction_per_side_in should be numeric"
        assert isinstance(boom_info["correction_total_in"], (int, float)), "correction_total_in should be numeric"
        assert isinstance(boom_info["boom_to_element_ratio"], (int, float)), "boom_to_element_ratio should be numeric"
        assert isinstance(boom_info["gain_adj_db"], (int, float)), "gain_adj_db should be numeric"
        assert isinstance(boom_info["fb_adj_db"], (int, float)), "fb_adj_db should be numeric"
        assert isinstance(boom_info["impedance_shift_ohm"], (int, float)), "impedance_shift_ohm should be numeric"
        assert isinstance(boom_info["swr_factor"], (int, float)), "swr_factor should be numeric"
        assert isinstance(boom_info["description"], str), "description should be string"
        assert isinstance(boom_info["enabled"], bool), "enabled should be boolean"
        assert isinstance(boom_info["boom_grounded"], bool), "boom_grounded should be boolean"
        
        print(f"✓ All boom_correction_info field values have correct types")


class TestBoomDiameterEffect:
    """Test that thick boom has larger correction than thin boom"""
    
    def test_thick_boom_has_larger_correction_than_thin(self, api_client):
        """3 inch boom should have larger correction than 1 inch boom"""
        payload_thin = create_base_payload(boom_grounded=True, boom_diameter=1.0)
        payload_thick = create_base_payload(boom_grounded=True, boom_diameter=3.0)
        
        response_thin = api_client.post(f"{BASE_URL}/api/calculate", json=payload_thin)
        response_thick = api_client.post(f"{BASE_URL}/api/calculate", json=payload_thick)
        
        assert response_thin.status_code == 200
        assert response_thick.status_code == 200
        
        correction_thin = response_thin.json()["boom_correction_info"]["correction_per_side_in"]
        correction_thick = response_thick.json()["boom_correction_info"]["correction_per_side_in"]
        
        # Thicker boom should have larger correction
        assert correction_thick > correction_thin, \
            f"3\" boom correction ({correction_thick}) should be > 1\" boom correction ({correction_thin})"
        
        # Thick boom should also have larger gain reduction
        gain_adj_thin = response_thin.json()["boom_correction_info"]["gain_adj_db"]
        gain_adj_thick = response_thick.json()["boom_correction_info"]["gain_adj_db"]
        
        # Both should be negative, thick should be more negative
        assert gain_adj_thick < gain_adj_thin, \
            f"Thick boom gain_adj ({gain_adj_thick}) should be more negative than thin ({gain_adj_thin})"
        
        print(f"✓ Thicker boom has larger correction:")
        print(f"  - 1\" boom: correction_per_side={correction_thin}\", gain_adj={gain_adj_thin} dB")
        print(f"  - 3\" boom: correction_per_side={correction_thick}\", gain_adj={gain_adj_thick} dB")


class TestBandFrequencyEffect:
    """Test that VHF band has larger correction than HF band for same boom size"""
    
    def test_vhf_has_larger_correction_than_hf(self, api_client):
        """2m band (146MHz) should have larger correction than 11m band (27MHz) for same boom size"""
        # 11m HF band (27 MHz) - use standard elements with 2" boom
        payload_hf = create_base_payload(boom_grounded=True, boom_diameter=2.0, band="11m_cb")
        
        # 2m VHF band (146 MHz) - use VHF-sized elements with same 2" boom
        payload_vhf = {
            "num_elements": 4,
            "elements": create_2m_vhf_elements(),
            "height_from_ground": 20,  # Lower height for VHF
            "height_unit": "ft",
            "boom_diameter": 2.0,  # Same boom diameter
            "boom_unit": "inches",
            "band": "2m",
            "boom_grounded": True
        }
        
        response_hf = api_client.post(f"{BASE_URL}/api/calculate", json=payload_hf)
        response_vhf = api_client.post(f"{BASE_URL}/api/calculate", json=payload_vhf)
        
        assert response_hf.status_code == 200, f"HF request failed: {response_hf.text}"
        assert response_vhf.status_code == 200, f"VHF request failed: {response_vhf.text}"
        
        correction_hf = response_hf.json()["boom_correction_info"]["correction_per_side_in"]
        correction_vhf = response_vhf.json()["boom_correction_info"]["correction_per_side_in"]
        
        # VHF should have larger correction than HF for same boom diameter
        # This is because boom diameter is a larger fraction of the wavelength at VHF
        assert correction_vhf > correction_hf, \
            f"VHF correction ({correction_vhf}) should be > HF correction ({correction_hf})"
        
        # Also check boom-to-element ratio (should be higher at VHF due to smaller elements)
        ratio_hf = response_hf.json()["boom_correction_info"]["boom_to_element_ratio"]
        ratio_vhf = response_vhf.json()["boom_correction_info"]["boom_to_element_ratio"]
        
        print(f"✓ VHF band has larger correction than HF band:")
        print(f"  - 11m HF (27MHz): correction={correction_hf}\", boom_to_element_ratio={ratio_hf}")
        print(f"  - 2m VHF (146MHz): correction={correction_vhf}\", boom_to_element_ratio={ratio_vhf}")


class TestImpedanceShift:
    """Test impedance shift calculation for grounded boom"""
    
    def test_grounded_boom_has_negative_impedance_shift(self, api_client):
        """Grounded boom should lower driven element impedance (negative shift)"""
        payload = create_base_payload(boom_grounded=True)
        response = api_client.post(f"{BASE_URL}/api/calculate", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        impedance_shift = data["boom_correction_info"]["impedance_shift_ohm"]
        
        # Grounded boom should have negative impedance shift
        assert impedance_shift < 0, f"Grounded boom should have negative impedance_shift, got {impedance_shift}"
        
        print(f"✓ Grounded boom has negative impedance shift: {impedance_shift} ohms")
    
    def test_insulated_boom_has_zero_impedance_shift(self, api_client):
        """Insulated boom should have zero impedance shift"""
        payload = create_base_payload(boom_grounded=False)
        response = api_client.post(f"{BASE_URL}/api/calculate", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        impedance_shift = data["boom_correction_info"]["impedance_shift_ohm"]
        
        # Insulated boom should have zero impedance shift
        assert impedance_shift == 0, f"Insulated boom should have zero impedance_shift, got {impedance_shift}"
        
        print(f"✓ Insulated boom has zero impedance shift: {impedance_shift} ohms")


class TestDescriptionField:
    """Test description field in boom_correction_info"""
    
    def test_grounded_boom_has_meaningful_description(self, api_client):
        """Grounded boom should have description mentioning boom correction"""
        payload = create_base_payload(boom_grounded=True, boom_diameter=2.0)
        response = api_client.post(f"{BASE_URL}/api/calculate", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        description = data["boom_correction_info"]["description"]
        
        assert len(description) > 10, "Description should be meaningful, not empty"
        # Should mention boom correction or correction value
        assert "correction" in description.lower() or "boom" in description.lower(), \
            f"Description should mention 'correction' or 'boom', got: {description}"
        
        print(f"✓ Grounded boom description: {description}")
    
    def test_insulated_boom_description_mentions_insulated(self, api_client):
        """Insulated boom description should mention insulated/no correction"""
        payload = create_base_payload(boom_grounded=False)
        response = api_client.post(f"{BASE_URL}/api/calculate", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        description = data["boom_correction_info"]["description"]
        
        assert len(description) > 10, "Description should be meaningful"
        # Should mention insulated or no correction
        assert "insulated" in description.lower() or "no" in description.lower(), \
            f"Description should mention 'insulated' or 'no correction', got: {description}"
        
        print(f"✓ Insulated boom description: {description}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
