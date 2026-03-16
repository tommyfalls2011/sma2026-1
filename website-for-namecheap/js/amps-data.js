// SMA Amp Configurator — Data & Calculations
// Ported from ~/sma-ai/frontend/src/data/ampDefaults.js

const TRANSISTORS = {
  '2SC2879': {
    name: '2SC2879', wattsPerPill: 100, costPerPill: 250, costPerPillUsed: 200, shippingFlat: 14.95, source: 'China', tier: 'standard',
    specs: { type: 'NPN Silicon', manufacturer: 'Toshiba / HG Semi', package: '4L FLG (Flange Mount)', freqRange: '2-30 MHz', maxVce: 25, maxVcb: 45, maxVeb: 4.5, maxIc: 25, powerDissipation: 250, hfeMin: 10, hfeMax: 150, hfeCondition: 'Vce=5V, Ic=10A', fT: 120, outputPower: 100, outputCondition: 'Vcc=12.5V, 28 MHz PEP', powerGain: 13, efficiency: 35, cob: 720, cobCondition: 'Vcb=12.5V, 1 MHz', thermalResistance: null, tjMax: 175, notes: 'The most common "over-volted" transistor. Large die makes it a workhorse. Original Toshiba production ended; HG Semi clones common.' },
    voltagePerformance: { '13.8': { carrierW: [120,140], pepW: [240,280], risk: 'low', inputRatio: '4:1', outputRatio: '1:2' }, '18': { carrierW: [220,250], pepW: [450,550], risk: 'medium', inputRatio: '5:1', outputRatio: '1:3' }, '20': { carrierW: [260,300], pepW: [550,600], risk: 'high', inputRatio: '5:1', outputRatio: '1:3' } },
    hvNotes: 'At 18V, a pair can produce 220W-250W Carrier and 450W-550W PEP. At 20V, they can approach 600W PEP, but heat becomes the primary failure point.',
    hvTuning: { inputTune: '470 pF - 680 pF', outputTune: '820 pF - 1200 pF', notes: 'At 18V, extremely "hot" gain. Use heavy shunt on input to swamp gain or radio will see massive mismatch. Output: start with 820pF and add 100pF at a time.' },
  },
  'HG2879': {
    name: 'HG2879', wattsPerPill: 100, costPerPill: 34.50, shippingFlat: 13.00, source: 'Jersey', tier: 'premium',
    specs: { type: 'NPN Silicon', manufacturer: 'HG Semiconductor', package: '4L FLG (Flange Mount)', freqRange: '2-30 MHz', maxVce: 25, maxVcb: 45, maxVeb: 4.5, maxIc: 25, powerDissipation: 250, hfeMin: 10, hfeMax: 150, hfeCondition: 'Vce=5V, Ic=10A', fT: 120, outputPower: 100, outputCondition: 'Vcc=12.5V, 28 MHz PEP', powerGain: 13, efficiency: 35, cob: 720, cobCondition: 'Vcb=12.5V, 1 MHz', thermalResistance: null, tjMax: 175, notes: 'HG Semi equivalent of 2SC2879. Tighter binning and matched parameters for push-pull applications.' },
    voltagePerformance: { '13.8': { carrierW: [120,140], pepW: [240,280], risk: 'low', inputRatio: '4:1', outputRatio: '1:2' }, '18': { carrierW: [220,250], pepW: [450,550], risk: 'medium', inputRatio: '5:1', outputRatio: '1:3' }, '20': { carrierW: [260,300], pepW: [550,600], risk: 'high', inputRatio: '5:1', outputRatio: '1:3' } },
    hvNotes: 'Same performance envelope as 2SC2879. Tighter matching helps in push-pull pairs.',
    hvTuning: { inputTune: '470 pF - 680 pF', outputTune: '820 pF - 1200 pF', notes: 'Same tuning values as 2SC2879. Tighter matching means less variance between pairs.' },
  },
  '2SC3240': {
    name: '2SC3240', wattsPerPill: 110, costPerPill: 50, shippingFlat: 14.95, source: 'China', tier: 'premium',
    specs: { type: 'NPN Epitaxial Planar', manufacturer: 'Mitsubishi', package: 'X92', freqRange: '2-30 MHz', maxVce: 20, maxVcb: 50, maxVeb: 5, maxIc: 25, powerDissipation: 270, hfeMin: 40, hfeMax: null, hfeCondition: 'Vce=5V, Ic=5A', fT: 30, outputPower: 110, outputCondition: 'Vcc=13.8V, 28 MHz', powerGain: 11.5, efficiency: 40, cob: null, cobCondition: null, thermalResistance: null, tjMax: 175, notes: 'Thrives on current. Higher breakdown voltage (20V) and power dissipation (270W). Requires massive cooling due to high amperage draw.' },
    voltagePerformance: { '13.8': { carrierW: [130,150], pepW: [260,300], risk: 'low', inputRatio: '4:1', outputRatio: '1:2' }, '18': { carrierW: [240,260], pepW: [480,520], risk: 'medium', inputRatio: '5:1', outputRatio: '1:3' }, '20': { carrierW: [270,300], pepW: [500,550], risk: 'medium-high', inputRatio: '5:1', outputRatio: '1:3' } },
    hvNotes: 'A beast for PEP. At 18V, it can swing 240W Carrier and easily 500W+ PEP. Requires massive cooling.',
    hvTuning: { inputTune: '560 pF - 820 pF', outputTune: '1200 pF - 1500 pF', notes: 'Largest caps in the lineup due to huge die and high current draw.' },
  },
  'MRF454': {
    name: 'MRF454', wattsPerPill: 90, costPerPill: 24.95, shippingFlat: 14.95, source: 'China', tier: 'premium',
    specs: { type: 'NPN Silicon', manufacturer: 'Motorola / MACOM', package: 'Case 211-11 (Stud Mount)', freqRange: '2-30 MHz', maxVce: 25, maxVcb: 45, maxVeb: 4, maxIc: 20, powerDissipation: 275, hfeMin: 40, hfeMax: 150, hfeCondition: 'Vce=5V, Ic=5A', fT: 100, outputPower: 80, outputCondition: 'Vcc=12.5V, 30 MHz', powerGain: 12, efficiency: 50, cob: 250, cobCondition: 'Vcb=15V, 1 MHz', thermalResistance: 0.7, tjMax: 175, notes: 'Best voltage headroom for high-voltage experimentation. 25V VCEO handles 100% modulation peaks better than SD1446.' },
    voltagePerformance: { '13.8': { carrierW: [100,120], pepW: [200,240], risk: 'low', inputRatio: '3:1', outputRatio: '1:2' }, '18': { carrierW: [200,220], pepW: [400,450], risk: 'low', inputRatio: '4:1', outputRatio: '1:3' }, '20': { carrierW: [220,250], pepW: [440,500], risk: 'medium', inputRatio: '4:1', outputRatio: '1:3' } },
    hvNotes: 'Very stable at high voltage. At 18V, expect 200W-220W Carrier and 400W-450W PEP.',
    hvTuning: { inputTune: '330 pF - 470 pF', outputTune: '680 pF - 1000 pF', notes: 'Best voltage headroom. Lower output cap due to lower output capacitance (250pF vs 720pF).' },
  },
  'HG454': {
    name: 'HG454', wattsPerPill: 85, costPerPill: 24.95, shippingFlat: 13.00, source: 'Jersey', tier: 'standard',
    specs: { type: 'NPN Silicon', manufacturer: 'HG Semiconductor', package: 'Case 211-11 (Stud Mount)', freqRange: '2-30 MHz', maxVce: 25, maxVcb: 45, maxVeb: 4, maxIc: 25, powerDissipation: 275, hfeMin: 40, hfeMax: 150, hfeCondition: 'Vce=5V, Ic=5A', fT: 100, outputPower: 85, outputCondition: 'Vcc=12.5V, 30 MHz', powerGain: 12, efficiency: 48, cob: 250, cobCondition: 'Vcb=15V, 1 MHz', thermalResistance: 0.7, tjMax: 175, notes: 'HG Semi equivalent of MRF454. Same 25V Vce and 275W dissipation. Budget-friendly.' },
    voltagePerformance: { '13.8': { carrierW: [95,110], pepW: [190,220], risk: 'low', inputRatio: '3:1', outputRatio: '1:2' }, '18': { carrierW: [190,210], pepW: [380,430], risk: 'low', inputRatio: '4:1', outputRatio: '1:3' }, '20': { carrierW: [210,240], pepW: [420,480], risk: 'medium', inputRatio: '4:1', outputRatio: '1:3' } },
    hvNotes: 'Same voltage headroom as MRF454. Budget-friendly alternative for high-voltage builds.',
    hvTuning: { inputTune: '330 pF - 470 pF', outputTune: '680 pF - 1000 pF', notes: 'Same tuning profile as MRF454.' },
  },
  'HG1446': {
    name: 'HG1446', wattsPerPill: 70, costPerPill: 23.95, shippingFlat: 13.00, source: 'Jersey', tier: 'economy',
    specs: { type: 'NPN Silicon', manufacturer: 'HG Semiconductor', package: 'TO-60 (Stud Mount)', freqRange: '2-30 MHz', maxVce: 18, maxVcb: 36, maxVeb: 4, maxIc: 12, powerDissipation: 183, hfeMin: 30, hfeMax: 150, hfeCondition: 'Vce=5V, Ic=3A', fT: 80, outputPower: 70, outputCondition: 'Vcc=12.5V, 30 MHz', powerGain: 10, efficiency: 45, cob: 200, cobCondition: 'Vcb=12.5V, 1 MHz', thermalResistance: 0.8, tjMax: 175, notes: 'Smaller die. Much more sensitive to voltage spikes. 18V is the absolute limit.' },
    voltagePerformance: { '13.8': { carrierW: [80,95], pepW: [160,190], risk: 'low', inputRatio: '3:1', outputRatio: '1:2' }, '18': { carrierW: [150,180], pepW: [300,350], risk: 'high', inputRatio: '4:1', outputRatio: '1:3' }, '20': { carrierW: null, pepW: null, risk: 'extreme', inputRatio: '-', outputRatio: '-' } },
    hvNotes: 'HIGH RISK at 18V — absolute limit. 20V will cause instant breakdown.',
    hvTuning: { inputTune: '220 pF - 330 pF', outputTune: '470 pF - 680 pF', notes: 'Smallest caps — small die, low capacitance. Very sensitive to voltage spikes.' },
  },
  'SD1446': {
    name: 'SD1446', wattsPerPill: 70, costPerPill: 23.95, shippingFlat: 14.95, source: 'China', tier: 'economy',
    specs: { type: 'NPN Silicon', manufacturer: 'STMicroelectronics', package: 'TO-60 (Stud Mount)', freqRange: '2-30 MHz', maxVce: 18, maxVcb: 36, maxVeb: 4, maxIc: 12, powerDissipation: 183, hfeMin: 30, hfeMax: 150, hfeCondition: 'Vce=5V, Ic=3A', fT: 80, outputPower: 70, outputCondition: 'Vcc=12.5V, 30 MHz', powerGain: 10, efficiency: 45, cob: 200, cobCondition: 'Vcb=12.5V, 1 MHz', thermalResistance: 0.8, tjMax: 175, notes: 'Smaller die. Popular for Boomer-style builds. 18V is the absolute limit.' },
    voltagePerformance: { '13.8': { carrierW: [80,95], pepW: [160,190], risk: 'low', inputRatio: '3:1', outputRatio: '1:2' }, '18': { carrierW: [150,180], pepW: [300,350], risk: 'high', inputRatio: '4:1', outputRatio: '1:3' }, '20': { carrierW: null, pepW: null, risk: 'extreme', inputRatio: '-', outputRatio: '-' } },
    hvNotes: 'HIGH RISK at 18V — absolute limit. 20V will cause instant breakdown.',
    hvTuning: { inputTune: '220 pF - 330 pF', outputTune: '470 pF - 680 pF', notes: 'Same tuning as HG1446. Popular for Boomer-style builds at safe voltages.' },
  },
};

const AMP_CONFIGS = [
  { id: '1pill', name: '1-Pill', pills: 1, type: 'straight', basePrice: 275, description: 'Single transistor amp - compact everyday driver' },
  { id: '2pill', name: '2-Pill', pills: 2, type: 'straight', basePrice: 350, description: 'Dual transistor - solid mid-range power' },
  { id: '3pill', name: '3-Pill', pills: 3, type: 'driver', basePrice: 425, description: '1 pill driving 2 pills - same box, extra punch' },
  { id: '4pill', name: '4-Pill', pills: 4, type: 'straight', basePrice: 575, description: '4 transistors in line - serious power' },
  { id: '1x4box', name: '1x4 Box', pills: 4, type: 'box', basePrice: 650, description: '4-pill box configuration - clean and compact' },
  { id: '2x4box', name: '2x4 Box', pills: 8, type: 'box', basePrice: 1050, description: 'Two 4-pill amps in one box - 8 pills total' },
  { id: '6str', name: '6-Pill Straight', pills: 6, type: 'straight', basePrice: 800, description: '6 transistors in line - high output' },
  { id: '2x6box', name: '2x6 Box', pills: 12, type: 'box', basePrice: 1400, description: 'Two 6-pill amps in one box - 12 pills total' },
  { id: '8str', name: '8-Pill Straight', pills: 8, type: 'straight', basePrice: 1050, description: '8 transistors in line - brute force' },
  { id: '2x8box', name: '2x8 Box', pills: 16, type: 'box', basePrice: 1800, description: 'Two 8-pill amps in one box - 16 pills total' },
  { id: '3x8box', name: '3x8 Box', pills: 24, type: 'box', basePrice: 2500, description: 'Three 8-pill amps in one box - 24 pills total' },
  { id: '12pill', name: '12-Pill', pills: 12, type: 'straight', basePrice: 1400, description: '12 transistors - wall of power' },
  { id: '4x12box', name: '4x12 Box', pills: 48, type: 'box', basePrice: 4500, description: 'Four 12-pill amps in one box - 48 pills total' },
  { id: '16pill', name: '16-Pill', pills: 16, type: 'straight', basePrice: 1800, description: '16 transistors - maximum straight config' },
  { id: '4x16box', name: '4x16 Box', pills: 64, type: 'box', basePrice: 6000, description: 'Four 16-pill amps in one box - 64 pills, ultimate power' },
];

const VOLTAGE_MODES = [
  { id: '13.8', label: '13.8V', sublabel: 'Standard Mobile', color: '#22c55e' },
  { id: '18', label: '18V', sublabel: 'High Voltage', color: '#eab308' },
  { id: '20', label: '20V', sublabel: 'Maximum', color: '#ef4444' },
];

const RISK_STYLES = {
  low: { bg: 'rgba(34,197,94,0.12)', color: '#22c55e', label: 'LOW RISK' },
  medium: { bg: 'rgba(234,179,8,0.12)', color: '#eab308', label: 'MEDIUM RISK' },
  'medium-high': { bg: 'rgba(249,115,22,0.12)', color: '#f97316', label: 'MED-HIGH RISK' },
  high: { bg: 'rgba(239,68,68,0.12)', color: '#ef4444', label: 'HIGH RISK' },
  extreme: { bg: 'rgba(239,68,68,0.25)', color: '#ef4444', label: 'WILL DESTROY' },
};

function calcPower(config, transistor, voltageMode) {
  voltageMode = voltageMode || '13.8';
  const vp = transistor.voltagePerformance && transistor.voltagePerformance[voltageMode];
  if (vp && vp.carrierW) {
    const pairCarrierAvg = (vp.carrierW[0] + vp.carrierW[1]) / 2;
    const perPill = pairCarrierAvg / 2;
    const pills = config.pills;
    if (config.type === 'driver') return Math.round(perPill * (pills - 1) * 0.90);
    if (config.type === 'box') { const e = pills <= 8 ? 0.88 : pills <= 16 ? 0.85 : pills <= 32 ? 0.82 : 0.80; return Math.round(perPill * pills * e); }
    const e = pills <= 2 ? 0.95 : pills <= 4 ? 0.90 : pills <= 8 ? 0.87 : 0.85;
    return Math.round(perPill * pills * e);
  }
  const wpill = transistor.wattsPerPill;
  const pills = config.pills;
  if (config.type === 'driver') return Math.round(wpill * (pills - 1) * 0.90);
  if (config.type === 'box') { const e = pills <= 8 ? 0.88 : pills <= 16 ? 0.85 : pills <= 32 ? 0.82 : 0.80; return Math.round(wpill * pills * e); }
  const e = pills <= 2 ? 0.95 : pills <= 4 ? 0.90 : pills <= 8 ? 0.87 : 0.85;
  return Math.round(wpill * pills * e);
}

function calcPEP(config, transistor, voltageMode) {
  voltageMode = voltageMode || '13.8';
  const vp = transistor.voltagePerformance && transistor.voltagePerformance[voltageMode];
  if (vp && vp.pepW) {
    const pairPepAvg = (vp.pepW[0] + vp.pepW[1]) / 2;
    const perPill = pairPepAvg / 2;
    const pills = config.pills;
    if (config.type === 'driver') return Math.round(perPill * (pills - 1) * 0.90);
    if (config.type === 'box') { const e = pills <= 8 ? 0.88 : pills <= 16 ? 0.85 : pills <= 32 ? 0.82 : 0.80; return Math.round(perPill * pills * e); }
    const e = pills <= 2 ? 0.95 : pills <= 4 ? 0.90 : pills <= 8 ? 0.87 : 0.85;
    return Math.round(perPill * pills * e);
  }
  return Math.round(calcPower(config, transistor, voltageMode) * 2);
}

function calcPrice(config, transistor) {
  return Math.round(config.basePrice + (config.pills * transistor.costPerPill) + (transistor.shippingFlat || 0));
}

function calcCurrentDraw(totalWatts, voltageMode) {
  const voltage = parseFloat(voltageMode || '13.8');
  return Math.round((totalWatts / 0.50) / voltage);
}

function calcHeatDissipation(totalWatts) { return Math.round(totalWatts); }

const GALLERY_FILTERS = [
  { id: 'all', label: 'All Builds' },
  { id: '2pill', label: '2-Pill' },
  { id: '4pill', label: '4-Pill' },
  { id: '6pill', label: '6-Pill' },
  { id: 'box', label: 'Box Amps' },
];

const GALLERY_IMAGES = [
  { id: 'g1', src: 'https://placehold.co/600x450/111118/d4a853?text=2-Pill+Build', alt: '2-Pill Build', label: '2-Pill with 2SC2879', description: 'Compact dual transistor amp — 13.8V mobile setup', configType: '2pill' },
  { id: 'g2', src: 'https://placehold.co/600x450/111118/d4a853?text=2-Pill+Internals', alt: '2-Pill Internals', label: '2-Pill Internal View', description: 'Copper heatsink and hand-wound transformers', configType: '2pill' },
  { id: 'g3', src: 'https://placehold.co/600x450/111118/d4a853?text=4-Pill+Build', alt: '4-Pill Build', label: '4-Pill Straight with MRF454', description: 'Four transistors in line — serious power', configType: '4pill' },
  { id: 'g4', src: 'https://placehold.co/600x450/111118/d4a853?text=4-Pill+Chassis', alt: '4-Pill Chassis', label: '4-Pill Chassis Layout', description: 'Heavy copper with bolted flange mounts', configType: '4pill' },
  { id: 'g5', src: 'https://placehold.co/600x450/111118/d4a853?text=6-Pill+Build', alt: '6-Pill Build', label: '6-Pill Straight with HG2879', description: 'Six matched transistors — high output monster', configType: '6pill' },
  { id: 'g6', src: 'https://placehold.co/600x450/111118/d4a853?text=6-Pill+Wiring', alt: '6-Pill Wiring', label: '6-Pill Wiring Detail', description: 'Hand-soldered output combiner network', configType: '6pill' },
  { id: 'g7', src: 'https://placehold.co/600x450/111118/d4a853?text=2x4+Box+Amp', alt: '2x4 Box', label: '2x4 Box Amp', description: 'Two 4-pill amps combined in one enclosure', configType: 'box' },
  { id: 'g8', src: 'https://placehold.co/600x450/111118/d4a853?text=2x8+Box+Amp', alt: '2x8 Box', label: '2x8 Box — 16 Pills', description: 'Dual 8-pill configuration — brute force in a box', configType: 'box' },
  { id: 'g9', src: 'https://placehold.co/600x450/111118/d4a853?text=Transformer+Winding', alt: 'Transformer', label: 'Hand-Wound Transformers', description: 'Binocular core input and output transformers', configType: '2pill' },
];
