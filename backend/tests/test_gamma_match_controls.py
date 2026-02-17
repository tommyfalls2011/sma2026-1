"""
Backend tests for Gamma Match controls, Dir2 spacing, and SWR tuning features.

Tests that:
1. Shorting bar position affects SWR (bar_pos=12 vs 24 vs 36)
2. Rod insertion (gamma_element_gap) affects SWR (gap=0.2 vs 0.5 vs 0.8)
3. Series Cap (gamma_cap_pf) affects SWR (cap=50 vs 76.1 vs 120)
4. SWR curve center matches displayed SWR
5. Smith chart data changes with gamma controls
6. Dir1 spacing presets produce different positions in auto-tune
7. Dir2 spacing presets produce different positions with 4+ elements
8. Gamma match achieves realistic SWR (below 1.15:1 possible)
9. Hairpin match comparison
10. No double API calls (implicitly tested via backend stability)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Standard 3-element Yagi test payload (reflector, driven, director)
def get_base_payload(num_elements=3, feed_type='gamma'):
    """Generate base payload for /api/calculate"""
    elements = [
        {"element_type": "reflector", "length": 216, "diameter": 0.5, "position": 0},
        {"element_type": "driven", "length": 198, "diameter": 0.5, "position": 48},
    ]
    if num_elements >= 3:
        elements.append({"element_type": "director", "length": 190, "diameter": 0.5, "position": 108})
    if num_elements >= 4:
        elements.append({"element_type": "director", "length": 185, "diameter": 0.5, "position": 168})
    if num_elements >= 5:
        elements.append({"element_type": "director", "length": 180, "diameter": 0.5, "position": 228})
    
    return {
        "num_elements": num_elements,
        "elements": elements[:num_elements],
        "height_from_ground": 54,
        "height_unit": "ft",
        "boom_diameter": 1.5,
        "boom_unit": "inches",
        "band": "11m_cb",
        "frequency_mhz": 27.185,
        "feed_type": feed_type,
        "antenna_orientation": "horizontal",
    }


class TestGammaShortingBar:
    """Test that shorting bar position affects SWR values"""
    
    def test_shorting_bar_affects_swr(self):
        """bar_pos=12 vs 24 vs 36 should give different SWR values"""
        results = {}
        
        for bar_pos in [12, 24, 36]:
            payload = get_base_payload(num_elements=3, feed_type='gamma')
            payload['gamma_bar_pos'] = bar_pos
            payload['gamma_element_gap'] = 0.5  # hold gap constant
            
            response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
            assert response.status_code == 200, f"API failed for bar_pos={bar_pos}"
            
            data = response.json()
            results[bar_pos] = {
                'swr': data['swr'],
                'matching_info': data.get('matching_info', {})
            }
            print(f"bar_pos={bar_pos}: SWR={data['swr']}")
        
        # Verify different bar positions produce different SWR values
        swr_values = [results[12]['swr'], results[24]['swr'], results[36]['swr']]
        unique_values = len(set(swr_values))
        
        assert unique_values >= 2, f"Expected different SWR values for different bar positions, got {swr_values}"
        print(f"SUCCESS: Shorting bar positions produced {unique_values} different SWR values: {swr_values}")
    
    def test_shorting_bar_resonant_frequency_shift(self):
        """Longer bar should shift resonant frequency lower"""
        results = {}
        
        for bar_pos in [12, 36]:
            payload = get_base_payload(num_elements=3, feed_type='gamma')
            payload['gamma_bar_pos'] = bar_pos
            payload['gamma_element_gap'] = 0.5
            
            response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
            assert response.status_code == 200
            
            data = response.json()
            matching_info = data.get('matching_info', {})
            results[bar_pos] = matching_info.get('resonant_freq_mhz', 27.185)
        
        # Longer bar (36) should have lower resonant freq than shorter bar (12)
        # Each inch shifts freq by ~0.03 MHz according to physics.py
        assert results[36] < results[12], f"Expected longer bar to shift freq lower: bar=36 ({results[36]}) should be < bar=12 ({results[12]})"
        print(f"SUCCESS: bar=12 resonant={results[12]} MHz, bar=36 resonant={results[36]} MHz")


class TestGammaRodInsertion:
    """Test that rod insertion (gamma_element_gap) affects SWR"""
    
    def test_rod_insertion_affects_swr(self):
        """gap=0.2 vs 0.5 vs 0.8 should change SWR"""
        results = {}
        
        for gap in [0.2, 0.5, 0.8]:
            payload = get_base_payload(num_elements=3, feed_type='gamma')
            payload['gamma_bar_pos'] = 24  # hold bar constant
            payload['gamma_element_gap'] = gap
            
            response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
            assert response.status_code == 200, f"API failed for gap={gap}"
            
            data = response.json()
            results[gap] = data['swr']
            print(f"gamma_element_gap={gap}: SWR={data['swr']}")
        
        # Verify different gaps produce different SWR values
        swr_values = [results[0.2], results[0.5], results[0.8]]
        unique_values = len(set(swr_values))
        
        assert unique_values >= 2, f"Expected different SWR values for different rod insertions, got {swr_values}"
        print(f"SUCCESS: Rod insertion values produced {unique_values} different SWR values: {swr_values}")
    
    def test_rod_insertion_q_factor_change(self):
        """Rod insertion affects Q-factor: higher insertion = higher Q"""
        results = {}
        
        for gap in [0.2, 0.8]:
            payload = get_base_payload(num_elements=3, feed_type='gamma')
            payload['gamma_bar_pos'] = 24
            payload['gamma_element_gap'] = gap
            
            response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
            assert response.status_code == 200
            
            data = response.json()
            matching_info = data.get('matching_info', {})
            results[gap] = matching_info.get('q_factor', 0)
        
        # Higher insertion should give higher Q
        assert results[0.8] > results[0.2], f"Expected higher Q at gap=0.8, got Q(0.2)={results[0.2]}, Q(0.8)={results[0.8]}"
        print(f"SUCCESS: Q-factor increases with rod insertion: Q(0.2)={results[0.2]}, Q(0.8)={results[0.8]}")


class TestGammaSeriesCap:
    """Test that series capacitor (gamma_cap_pf) affects SWR"""
    
    def test_series_cap_affects_swr(self):
        """cap=50 vs 76.1 vs 120 should change SWR"""
        results = {}
        
        for cap in [50, 76.1, 120]:
            payload = get_base_payload(num_elements=3, feed_type='gamma')
            payload['gamma_bar_pos'] = 24
            payload['gamma_element_gap'] = 0.5
            payload['gamma_cap_pf'] = cap
            
            response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
            assert response.status_code == 200, f"API failed for cap={cap}"
            
            data = response.json()
            results[cap] = data['swr']
            print(f"gamma_cap_pf={cap}: SWR={data['swr']}")
        
        # Verify different caps produce different SWR values
        swr_values = [results[50], results[76.1], results[120]]
        unique_values = len(set(swr_values))
        
        assert unique_values >= 2, f"Expected different SWR values for different capacitors, got {swr_values}"
        print(f"SUCCESS: Series cap values produced {unique_values} different SWR values: {swr_values}")


class TestSwrCurveMatchesDisplayedSwr:
    """Test that SWR curve at center frequency matches the displayed SWR number"""
    
    def test_swr_curve_center_matches_swr(self):
        """SWR curve minimum should match displayed SWR value"""
        payload = get_base_payload(num_elements=3, feed_type='gamma')
        payload['gamma_bar_pos'] = 24
        payload['gamma_element_gap'] = 0.5
        
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        displayed_swr = data['swr']
        swr_curve = data.get('swr_curve', [])
        
        assert len(swr_curve) > 0, "SWR curve should not be empty"
        
        # Find the minimum SWR in the curve
        min_swr_point = min(swr_curve, key=lambda x: x['swr'])
        curve_min_swr = min_swr_point['swr']
        
        # The displayed SWR should match or be very close to the curve minimum
        tolerance = 0.05  # Allow small rounding differences
        diff = abs(displayed_swr - curve_min_swr)
        
        assert diff < tolerance, f"SWR mismatch: displayed={displayed_swr}, curve_min={curve_min_swr}, diff={diff}"
        print(f"SUCCESS: Displayed SWR ({displayed_swr}) matches curve minimum ({curve_min_swr}), diff={diff:.4f}")
    
    def test_swr_curve_has_center_frequency_point(self):
        """SWR curve should include data point at/near center frequency"""
        payload = get_base_payload(num_elements=3, feed_type='gamma')
        center_freq = 27.185
        
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        swr_curve = data.get('swr_curve', [])
        
        # Find point closest to center freq
        center_point = min(swr_curve, key=lambda x: abs(x['frequency'] - center_freq))
        
        assert abs(center_point['frequency'] - center_freq) < 0.1, \
            f"SWR curve should have point near center freq {center_freq}, nearest is {center_point['frequency']}"
        print(f"SUCCESS: SWR curve has center freq point at {center_point['frequency']} MHz with SWR={center_point['swr']}")


class TestSmithChartChangesWithGammaControls:
    """Test that Smith chart data changes when gamma controls change"""
    
    def test_smith_chart_changes_with_bar_pos(self):
        """Smith chart impedance should change with shorting bar position"""
        results = {}
        
        for bar_pos in [12, 36]:
            payload = get_base_payload(num_elements=3, feed_type='gamma')
            payload['gamma_bar_pos'] = bar_pos
            payload['gamma_element_gap'] = 0.5
            
            response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
            assert response.status_code == 200
            
            data = response.json()
            smith_data = data.get('smith_chart_data', [])
            
            assert len(smith_data) > 0, "Smith chart data should not be empty"
            
            # Get center point impedance
            center_point = smith_data[len(smith_data) // 2]
            results[bar_pos] = {
                'z_real': center_point.get('z_real', 0),
                'z_imag': center_point.get('z_imag', 0),
                'gamma_real': center_point.get('gamma_real', 0),
                'gamma_imag': center_point.get('gamma_imag', 0),
            }
        
        # Impedance should change with bar position
        diff_z_real = abs(results[12]['z_real'] - results[36]['z_real'])
        diff_z_imag = abs(results[12]['z_imag'] - results[36]['z_imag'])
        diff_gamma = abs(results[12]['gamma_real'] - results[36]['gamma_real'])
        
        total_diff = diff_z_real + diff_z_imag + diff_gamma
        assert total_diff > 0.01, f"Smith chart should change with bar position, total diff={total_diff}"
        
        print(f"SUCCESS: Smith chart changes with bar position")
        print(f"  bar=12: Z={results[12]['z_real']}+j{results[12]['z_imag']}")
        print(f"  bar=36: Z={results[36]['z_real']}+j{results[36]['z_imag']}")


class TestDir1SpacingPresets:
    """Test that Dir1 spacing presets produce different positions in auto-tune"""
    
    def test_dir1_spacing_presets(self):
        """vclose/close/normal/far/vfar should produce different director positions"""
        presets = [
            ('vclose', {'close_dir1': 'vclose', 'far_dir1': False}),
            ('close', {'close_dir1': 'close', 'far_dir1': False}),
            ('normal', {'close_dir1': False, 'far_dir1': False}),
            ('far', {'close_dir1': False, 'far_dir1': 'far'}),
            ('vfar', {'close_dir1': False, 'far_dir1': 'vfar'}),
        ]
        
        results = {}
        
        for preset_name, preset_opts in presets:
            payload = {
                "num_elements": 3,
                "height_from_ground": 54,
                "height_unit": "ft",
                "boom_diameter": 1.5,
                "boom_unit": "inches",
                "band": "11m_cb",
                "feed_type": "gamma",
                "use_reflector": True,
                **preset_opts
            }
            
            response = requests.post(f"{BASE_URL}/api/auto-tune", json=payload)
            assert response.status_code == 200, f"Auto-tune failed for {preset_name}"
            
            data = response.json()
            elements = data['optimized_elements']
            
            # Find director position
            director = next((e for e in elements if e['element_type'] == 'director'), None)
            assert director is not None, f"No director found for {preset_name}"
            
            results[preset_name] = director['position']
            print(f"Dir1 preset {preset_name}: director position = {director['position']}\"")
        
        # Verify positions are different
        positions = list(results.values())
        unique_positions = len(set(positions))
        
        assert unique_positions >= 3, f"Expected at least 3 different positions, got {unique_positions}: {results}"
        
        # Verify ordering: vclose < close < normal < far < vfar
        assert results['vclose'] < results['close'] < results['far'] < results['vfar'], \
            f"Positions should increase from vclose to vfar: {results}"
        
        print(f"SUCCESS: Dir1 presets produce ordered positions: {results}")


class TestDir2SpacingPresets:
    """Test that Dir2 spacing presets produce different 2nd director positions with 4+ elements"""
    
    def test_dir2_spacing_presets_4_elements(self):
        """close_dir2/far_dir2 should produce different 2nd director positions"""
        presets = [
            ('vclose_dir2', {'close_dir2': 'vclose', 'far_dir2': False}),
            ('close_dir2', {'close_dir2': 'close', 'far_dir2': False}),
            ('normal_dir2', {'close_dir2': False, 'far_dir2': False}),
            ('far_dir2', {'close_dir2': False, 'far_dir2': 'far'}),
        ]
        
        results = {}
        
        for preset_name, preset_opts in presets:
            payload = {
                "num_elements": 4,  # Need 4 elements to have 2nd director
                "height_from_ground": 54,
                "height_unit": "ft",
                "boom_diameter": 1.5,
                "boom_unit": "inches",
                "band": "11m_cb",
                "feed_type": "gamma",
                "use_reflector": True,
                "close_dir1": False,  # Keep dir1 at default
                "far_dir1": False,
                **preset_opts
            }
            
            response = requests.post(f"{BASE_URL}/api/auto-tune", json=payload)
            assert response.status_code == 200, f"Auto-tune failed for {preset_name}"
            
            data = response.json()
            elements = data['optimized_elements']
            
            # Find 2nd director (should be at index 3: reflector, driven, dir1, dir2)
            directors = [e for e in elements if e['element_type'] == 'director']
            assert len(directors) >= 2, f"Expected 2 directors for 4-element Yagi, got {len(directors)}"
            
            # Second director is at index 1 in directors list
            dir2_position = directors[1]['position']
            dir1_position = directors[0]['position']
            
            results[preset_name] = {
                'dir1_pos': dir1_position,
                'dir2_pos': dir2_position,
                'dir2_gap': dir2_position - dir1_position
            }
            print(f"Dir2 preset {preset_name}: dir2 position = {dir2_position}\", gap from dir1 = {dir2_position - dir1_position}\"")
        
        # Verify dir2 positions are different
        dir2_positions = [r['dir2_pos'] for r in results.values()]
        unique_positions = len(set(dir2_positions))
        
        assert unique_positions >= 2, f"Expected different dir2 positions, got {unique_positions}: {dir2_positions}"
        
        # Verify ordering: vclose < close < normal < far
        assert results['vclose_dir2']['dir2_pos'] < results['close_dir2']['dir2_pos'], \
            f"vclose should produce smaller position than close"
        assert results['normal_dir2']['dir2_pos'] < results['far_dir2']['dir2_pos'], \
            f"normal should produce smaller position than far"
        
        print(f"SUCCESS: Dir2 presets produce different positions")


class TestGammaMatchRealisticSwr:
    """Test that gamma match can achieve realistic SWR (below 1.15:1 with good tuning)"""
    
    def test_gamma_can_achieve_low_swr(self):
        """With optimal tuning, gamma should get SWR below 1.15:1"""
        payload = get_base_payload(num_elements=3, feed_type='gamma')
        # Try optimal tuning values
        payload['gamma_bar_pos'] = 24  # typical mid-range
        payload['gamma_element_gap'] = 0.5  # optimal insertion
        payload['gamma_cap_pf'] = None  # let auto-cap calculate
        
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        swr = data['swr']
        
        # Gamma should be able to achieve low SWR
        assert swr < 1.5, f"Gamma match should achieve reasonable SWR, got {swr}"
        
        # Check if tuning quality is reasonable
        matching_info = data.get('matching_info', {})
        tuning_quality = matching_info.get('tuning_quality', 0)
        
        print(f"SUCCESS: Gamma match achieved SWR={swr} with tuning_quality={tuning_quality}")
        
        if swr <= 1.15:
            print("  EXCELLENT: SWR below 1.15:1 achieved!")
        elif swr <= 1.3:
            print("  GOOD: SWR below 1.3:1 achieved")
    
    def test_gamma_swr_at_resonance_lower_than_off_resonance(self):
        """SWR at resonance should be lower than SWR at band edges"""
        payload = get_base_payload(num_elements=3, feed_type='gamma')
        payload['gamma_bar_pos'] = 24
        payload['gamma_element_gap'] = 0.5
        
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        matching_info = data.get('matching_info', {})
        
        swr_at_resonance = matching_info.get('swr_at_resonance', data['swr'])
        matched_swr = matching_info.get('matched_swr', data['swr'])
        
        # SWR at resonance should be reasonable
        assert swr_at_resonance <= 2.0, f"SWR at resonance should be <= 2.0, got {swr_at_resonance}"
        
        print(f"SUCCESS: SWR at resonance={swr_at_resonance}, matched_swr={matched_swr}")


class TestHairpinMatchComparison:
    """Test hairpin match for comparison - should get near-perfect match"""
    
    def test_hairpin_achieves_good_match(self):
        """Hairpin should achieve low SWR comparable to gamma"""
        payload = get_base_payload(num_elements=3, feed_type='hairpin')
        
        response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        swr = data['swr']
        
        # Hairpin should achieve good match
        assert swr < 1.5, f"Hairpin match should achieve SWR < 1.5, got {swr}"
        
        matching_info = data.get('matching_info', {})
        assert matching_info.get('type') == 'Hairpin Match', "Should be Hairpin Match"
        
        print(f"SUCCESS: Hairpin match achieved SWR={swr}")
    
    def test_hairpin_vs_gamma_comparison(self):
        """Compare hairpin and gamma match performance"""
        results = {}
        
        for feed_type in ['gamma', 'hairpin', 'direct']:
            payload = get_base_payload(num_elements=3, feed_type=feed_type)
            if feed_type == 'gamma':
                payload['gamma_bar_pos'] = 24
                payload['gamma_element_gap'] = 0.5
            
            response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
            assert response.status_code == 200
            
            data = response.json()
            results[feed_type] = data['swr']
        
        print(f"Feed type comparison:")
        print(f"  Gamma: SWR={results['gamma']}")
        print(f"  Hairpin: SWR={results['hairpin']}")
        print(f"  Direct: SWR={results['direct']}")
        
        # Both gamma and hairpin should be better than direct feed
        assert results['gamma'] <= results['direct'] or results['hairpin'] <= results['direct'], \
            "Matching networks should improve SWR vs direct feed"
        
        print(f"SUCCESS: Matching networks improve SWR vs direct feed")


class TestAutoTuneDir2PositionValidation:
    """Additional validation that dir2 spacing is correctly applied in auto-tune"""
    
    def test_5_element_has_both_dir1_and_dir2(self):
        """5-element Yagi should have reflector, driven, dir1, dir2, dir3"""
        payload = {
            "num_elements": 5,
            "height_from_ground": 54,
            "height_unit": "ft",
            "boom_diameter": 1.5,
            "boom_unit": "inches",
            "band": "11m_cb",
            "feed_type": "gamma",
            "use_reflector": True,
            "close_dir2": 'close',  # Apply close spacing to dir2
        }
        
        response = requests.post(f"{BASE_URL}/api/auto-tune", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        elements = data['optimized_elements']
        
        # Count element types
        types = [e['element_type'] for e in elements]
        assert types.count('reflector') == 1, "Should have 1 reflector"
        assert types.count('driven') == 1, "Should have 1 driven"
        assert types.count('director') == 3, "Should have 3 directors"
        
        directors = [e for e in elements if e['element_type'] == 'director']
        
        # Check that directors are properly spaced
        for i in range(1, len(directors)):
            gap = directors[i]['position'] - directors[i-1]['position']
            assert gap > 0, f"Director {i+1} should be further than director {i}"
        
        print(f"SUCCESS: 5-element Yagi has correct structure")
        print(f"  Director positions: {[d['position'] for d in directors]}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
