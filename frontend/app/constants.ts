import appJson from '../app.json';

export const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL || 'https://helpful-adaptation-production.up.railway.app';
export const APP_VERSION = appJson.expo.version;
export const APP_BUILD_DATE = '2026-02-10T12:00:00';
export const UPDATE_CHECK_URL = 'https://gist.githubusercontent.com/tommyfalls2011/3bb5c9e586bfa929d26da16776b0b9c6/raw/';

export const TIER_COLORS: Record<string, string> = {
  trial: '#888',
  bronze: '#CD7F32',
  silver: '#C0C0C0',
  gold: '#FFD700',
  admin: '#9C27B0'
};

export const BANDS = [
  { id: '17m', name: '17m (18.1 MHz)', center: 18.118 },
  { id: '15m', name: '15m (21.2 MHz)', center: 21.225 },
  { id: '12m', name: '12m (24.9 MHz)', center: 24.94 },
  { id: '11m_cb', name: '11m CB (27.1 MHz)', center: 27.185 },
  { id: '10m', name: '10m (28.5 MHz)', center: 28.5 },
  { id: '6m', name: '6m (51 MHz)', center: 51.0 },
  { id: '2m', name: '2m (146 MHz)', center: 146.0 },
  { id: '1.25m', name: '1.25m (223 MHz)', center: 223.5 },
  { id: '70cm', name: '70cm (435 MHz)', center: 435.0 },
];

export const SPACING_OPTIONS = {
  tight: [
    { value: '0.6', label: 'Very Tight (60%)' },
    { value: '0.75', label: 'Tight (75%)' },
    { value: '0.85', label: 'Mod Tight (85%)' },
  ],
  long: [
    { value: '1.15', label: 'Mod Long (115%)' },
    { value: '1.3', label: 'Long (130%)' },
    { value: '1.5', label: 'Very Long (150%)' },
  ],
};

export const DEFAULT_INPUTS = {
  num_elements: 2,
  elements: [
    { element_type: 'reflector' as const, length: '216', diameter: '0.5', position: '0' },
    { element_type: 'driven' as const, length: '204', diameter: '0.5', position: '48' },
  ],
  height_from_ground: '54', height_unit: 'ft' as const, boom_diameter: '1.5', boom_unit: 'inches' as const, band: '11m_cb', frequency_mhz: '27.185',
  stacking: { enabled: false, orientation: 'vertical' as const, layout: 'line' as const, num_antennas: 2, spacing: '20', spacing_unit: 'ft' as const, h_spacing: '20', h_spacing_unit: 'ft' as const },
  taper: { enabled: false, num_tapers: 2, center_length: '36', sections: [{ length: '36', start_diameter: '0.625', end_diameter: '0.5' }, { length: '36', start_diameter: '0.5', end_diameter: '0.375' }] },
  corona_balls: { enabled: false, diameter: '1.0' },
  ground_radials: { enabled: false, ground_type: 'average', wire_diameter: '0.5', num_radials: 8 },
  use_reflector: true,
  antenna_orientation: 'horizontal',
  dual_active: false,
  dual_selected_beam: 'horizontal' as const,
  feed_type: 'gamma',
  boom_grounded: true,
  boom_mount: 'bonded' as const,
};
