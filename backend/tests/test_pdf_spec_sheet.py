"""
Test suite for PDF Spec Sheet API endpoint.
Tests the new POST /api/spec-sheet/pdf endpoint added for PDF export feature.
"""
import pytest
import requests
import os

# Use the preview URL from environment or default
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://pdf-download-feature.preview.emergentagent.com').rstrip('/')

# Sample valid payload with full inputs and results
VALID_PAYLOAD = {
    "inputs": {
        "num_elements": 3,
        "elements": [
            {"element_type": "reflector", "length": "216", "diameter": "0.5", "position": "0"},
            {"element_type": "driven", "length": "204", "diameter": "0.5", "position": "48"},
            {"element_type": "director", "length": "195", "diameter": "0.5", "position": "96"}
        ],
        "height_from_ground": "54",
        "height_unit": "ft",
        "boom_diameter": "1.5",
        "boom_unit": "inches",
        "band": "11m_cb",
        "frequency_mhz": "27.185",
        "antenna_orientation": "horizontal",
        "feed_type": "gamma",
        "boom_mount": "bonded"
    },
    "results": {
        "swr": 1.1,
        "swr_description": "Perfect match - 1.1:1",
        "fb_ratio": 13.9,
        "fs_ratio": 8.0,
        "gain_dbi": 11.77,
        "base_gain_dbi": 6.28,
        "multiplication_factor": 15.0,
        "antenna_efficiency": 95,
        "takeoff_angle": 9.6,
        "takeoff_angle_description": "Excellent",
        "beamwidth_h": 120.0,
        "beamwidth_v": 61.8,
        "bandwidth": 1.95,
        "usable_bandwidth_1_5": 1.5,
        "usable_bandwidth_2_0": 2.0,
        "impedance_low": 45,
        "impedance_high": 55,
        "return_loss_db": 20,
        "mismatch_loss_db": 0.1,
        "height_performance": "Optimal",
        "noise_level": "Low",
        "band_info": {"name": "11m CB (27.1 MHz)"},
        "gain_breakdown": {
            "standard_gain": 6.2,
            "boom_adj": 0.08,
            "reflector_adj": 0,
            "taper_bonus": 0,
            "height_bonus": 5.49,
            "boom_bonus": 0,
            "final_gain": 11.77
        }
    },
    "user_email": "test@example.com",
    "gain_mode": "realworld"
}


class TestPDFSpecSheet:
    """Tests for POST /api/spec-sheet/pdf endpoint"""
    
    def test_pdf_endpoint_returns_200_with_valid_payload(self):
        """Test that valid payload returns 200 with PDF content"""
        response = requests.post(
            f"{BASE_URL}/api/spec-sheet/pdf",
            json=VALID_PAYLOAD,
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
    def test_pdf_content_type_is_pdf(self):
        """Test that response Content-Type is application/pdf"""
        response = requests.post(
            f"{BASE_URL}/api/spec-sheet/pdf",
            json=VALID_PAYLOAD,
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200
        assert "application/pdf" in response.headers.get("Content-Type", ""), \
            f"Expected application/pdf, got {response.headers.get('Content-Type')}"
            
    def test_pdf_starts_with_pdf_magic_bytes(self):
        """Test that response starts with %PDF- (valid PDF)"""
        response = requests.post(
            f"{BASE_URL}/api/spec-sheet/pdf",
            json=VALID_PAYLOAD,
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200
        content = response.content
        assert content.startswith(b"%PDF-"), f"PDF should start with %PDF-, got: {content[:20]}"
        
    def test_pdf_has_content_disposition_header(self):
        """Test that response has Content-Disposition header for download"""
        response = requests.post(
            f"{BASE_URL}/api/spec-sheet/pdf",
            json=VALID_PAYLOAD,
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200
        cd = response.headers.get("Content-Disposition", "")
        assert "attachment" in cd or "filename" in cd, \
            f"Expected Content-Disposition with attachment/filename, got: {cd}"
            
    def test_pdf_with_empty_payload(self):
        """Test that empty payload returns 200 (uses defaults)"""
        response = requests.post(
            f"{BASE_URL}/api/spec-sheet/pdf",
            json={},
            headers={"Content-Type": "application/json"}
        )
        # The endpoint accepts empty payload and uses defaults
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        assert response.content.startswith(b"%PDF-"), "Should still generate valid PDF"
        
    def test_pdf_with_no_body_returns_422(self):
        """Test that missing body returns 422 validation error"""
        response = requests.post(
            f"{BASE_URL}/api/spec-sheet/pdf",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        
    def test_pdf_with_stacking_info(self):
        """Test PDF generation with stacking configuration"""
        payload = VALID_PAYLOAD.copy()
        payload["results"] = VALID_PAYLOAD["results"].copy()
        payload["results"]["stacking_enabled"] = True
        payload["results"]["stacking_info"] = {
            "num_antennas": 2,
            "orientation": "vertical",
            "layout": "line",
            "spacing": 20,
            "spacing_unit": "ft",
            "spacing_wavelengths": 0.55,
            "spacing_status": "Good",
            "gain_increase_db": 2.8,
            "isolation_db": 25,
            "optimal_spacing_ft": 25,
            "min_spacing_ft": 15,
            "power_splitter": {
                "type": "2-way",
                "input_impedance": "50 ohm",
                "combined_load": "25 ohm",
                "matching_method": "Quarter-wave transformer",
                "quarter_wave_ft": "8.5",
                "quarter_wave_in": "102",
                "power_per_antenna_100w": "50",
                "power_per_antenna_1kw": "500",
                "min_power_rating": "500W"
            }
        }
        payload["results"]["stacked_gain_dbi"] = 14.5
        
        response = requests.post(
            f"{BASE_URL}/api/spec-sheet/pdf",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200
        assert response.content.startswith(b"%PDF-")
        
    def test_pdf_with_taper_info(self):
        """Test PDF generation with element taper configuration"""
        payload = VALID_PAYLOAD.copy()
        payload["results"] = VALID_PAYLOAD["results"].copy()
        payload["results"]["taper_info"] = {
            "enabled": True,
            "num_tapers": 2,
            "gain_bonus": 0.3,
            "bandwidth_improvement": "+15%"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/spec-sheet/pdf",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200
        assert response.content.startswith(b"%PDF-")
        
    def test_pdf_with_corona_balls(self):
        """Test PDF generation with corona ball tips"""
        payload = VALID_PAYLOAD.copy()
        payload["results"] = VALID_PAYLOAD["results"].copy()
        payload["results"]["corona_info"] = {
            "enabled": True,
            "diameter": "1.0",
            "corona_reduction": 85,
            "bandwidth_effect": 1.1
        }
        
        response = requests.post(
            f"{BASE_URL}/api/spec-sheet/pdf",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200
        assert response.content.startswith(b"%PDF-")
        
    def test_pdf_with_wind_load(self):
        """Test PDF generation with wind load data"""
        payload = VALID_PAYLOAD.copy()
        payload["results"] = VALID_PAYLOAD["results"].copy()
        payload["results"]["wind_load"] = {
            "total_area_sqft": 2.5,
            "total_weight_lbs": 8,
            "element_weight_lbs": 3,
            "boom_weight_lbs": 4,
            "hardware_weight_lbs": 1,
            "boom_length_ft": 8,
            "turn_radius_ft": 5,
            "turn_radius_in": 60,
            "survival_mph": 90,
            "wind_ratings": {
                "50": {"force_lbs": 5, "torque_ft_lbs": 25},
                "70": {"force_lbs": 10, "torque_ft_lbs": 50},
                "90": {"force_lbs": 16, "torque_ft_lbs": 80}
            }
        }
        
        response = requests.post(
            f"{BASE_URL}/api/spec-sheet/pdf",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200
        assert response.content.startswith(b"%PDF-")
        
    def test_pdf_with_dual_polarity(self):
        """Test PDF generation with dual polarity configuration"""
        payload = VALID_PAYLOAD.copy()
        payload["inputs"] = VALID_PAYLOAD["inputs"].copy()
        payload["inputs"]["antenna_orientation"] = "dual"
        payload["results"] = VALID_PAYLOAD["results"].copy()
        payload["results"]["dual_polarity_info"] = {
            "description": "Dual H+V Polarity Yagi",
            "gain_per_polarization_dbi": 11.77,
            "coupling_bonus_db": 1.5,
            "fb_bonus_db": 2.0
        }
        
        response = requests.post(
            f"{BASE_URL}/api/spec-sheet/pdf",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200
        assert response.content.startswith(b"%PDF-")
        
    def test_pdf_with_boom_correction(self):
        """Test PDF generation with boom correction info"""
        payload = VALID_PAYLOAD.copy()
        payload["results"] = VALID_PAYLOAD["results"].copy()
        payload["results"]["boom_correction_info"] = {
            "enabled": True,
            "boom_mount": "bonded",
            "correction_multiplier": 0.5,
            "boom_to_element_ratio": "3:1",
            "correction_total_in": "0.25",
            "correction_per_side_in": "0.125",
            "gain_adj_db": -0.1,
            "fb_adj_db": 0,
            "impedance_shift_ohm": 2,
            "description": "Boom correction applied",
            "corrected_elements": [
                {"type": "reflector", "original_length": "216", "corrected_length": "215.75", "correction": "0.25"},
                {"type": "driven", "original_length": "204", "corrected_length": "203.75", "correction": "0.25"}
            ]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/spec-sheet/pdf",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200
        assert response.content.startswith(b"%PDF-")
        
    def test_pdf_with_ground_radials(self):
        """Test PDF generation with ground radials info"""
        payload = VALID_PAYLOAD.copy()
        payload["results"] = VALID_PAYLOAD["results"].copy()
        payload["results"]["ground_radials_info"] = {
            "ground_type": "average",
            "num_radials": 8,
            "radial_length_ft": 10,
            "radial_length_in": 120,
            "total_wire_length_ft": 80,
            "estimated_improvements": {
                "swr_improvement": "Improved",
                "efficiency_bonus_percent": 5
            }
        }
        
        response = requests.post(
            f"{BASE_URL}/api/spec-sheet/pdf",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200
        assert response.content.startswith(b"%PDF-")


class TestCalculateEndpointRegression:
    """Regression tests for /api/calculate to ensure it still works"""
    
    def test_calculate_returns_200(self):
        """Test that /api/calculate still works after PDF feature addition"""
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
            "frequency_mhz": 27.185
        }
        response = requests.post(
            f"{BASE_URL}/api/calculate",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
    def test_calculate_returns_expected_fields(self):
        """Test that /api/calculate returns all expected fields"""
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
            "frequency_mhz": 27.185
        }
        response = requests.post(
            f"{BASE_URL}/api/calculate",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check essential fields exist
        assert "swr" in data, "Missing 'swr' field"
        assert "gain_dbi" in data, "Missing 'gain_dbi' field"
        assert "fb_ratio" in data, "Missing 'fb_ratio' field"
        assert "beamwidth_h" in data, "Missing 'beamwidth_h' field"
        assert "beamwidth_v" in data, "Missing 'beamwidth_v' field"
        assert "bandwidth" in data, "Missing 'bandwidth' field"
        
        # Check values are reasonable
        assert 1.0 <= data["swr"] <= 10.0, f"SWR {data['swr']} out of expected range"
        assert 0 <= data["gain_dbi"] <= 30, f"Gain {data['gain_dbi']} out of expected range"
        assert 0 <= data["fb_ratio"] <= 50, f"F/B ratio {data['fb_ratio']} out of expected range"


class TestAutoTuneEndpointRegression:
    """Regression tests for /api/auto-tune endpoint"""
    
    def test_auto_tune_returns_200(self):
        """Test that /api/auto-tune still works"""
        payload = {
            "num_elements": 3,
            "height_from_ground": 54,
            "height_unit": "ft",
            "boom_diameter": 1.5,
            "boom_unit": "inches",
            "band": "11m_cb",
            "frequency_mhz": 27.185
        }
        response = requests.post(
            f"{BASE_URL}/api/auto-tune",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
    def test_auto_tune_returns_optimized_elements(self):
        """Test that auto-tune returns optimized elements"""
        payload = {
            "num_elements": 3,
            "height_from_ground": 54,
            "height_unit": "ft",
            "boom_diameter": 1.5,
            "boom_unit": "inches",
            "band": "11m_cb",
            "frequency_mhz": 27.185
        }
        response = requests.post(
            f"{BASE_URL}/api/auto-tune",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "optimized_elements" in data, "Missing 'optimized_elements' field"
        assert "predicted_swr" in data, "Missing 'predicted_swr' field"
        assert "predicted_gain" in data, "Missing 'predicted_gain' field"
        assert len(data["optimized_elements"]) == 3, f"Expected 3 elements, got {len(data['optimized_elements'])}"


class TestHealthEndpoints:
    """Basic health checks"""
    
    def test_api_root_returns_200(self):
        """Test that API root is accessible"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        
    def test_bands_endpoint_returns_200(self):
        """Test that bands endpoint is accessible"""
        response = requests.get(f"{BASE_URL}/api/bands")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 5, "Expected at least 5 bands"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
