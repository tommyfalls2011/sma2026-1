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

export const COAX_OPTIONS = [
  { key: 'ldf5-50a', label: '7/8" Heliax' },
  { key: 'ldf4-50a', label: '1/2" Heliax' },
  { key: 'rg213', label: 'RG-213' },
  { key: 'rg8', label: 'RG-8' },
  { key: 'rg8x', label: 'RG-8X' },
  { key: 'rg58', label: 'RG-58' },
];
