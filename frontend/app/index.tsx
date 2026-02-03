import React, { useState, useCallback, useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TextInput,
  TouchableOpacity,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Dimensions,
  Switch,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import Svg, { Circle, Line, Path, Text as SvgText, Rect, G } from 'react-native-svg';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL || '';
const { width: screenWidth } = Dimensions.get('window');

const BANDS = [
  { id: '11m_cb', name: '11m CB Band', center: 27.185 },
  { id: '10m', name: '10m Ham Band', center: 28.5 },
  { id: '12m', name: '12m Ham Band', center: 24.94 },
  { id: '15m', name: '15m Ham Band', center: 21.225 },
  { id: '17m', name: '17m Ham Band', center: 18.118 },
  { id: '20m', name: '20m Ham Band', center: 14.175 },
  { id: '40m', name: '40m Ham Band', center: 7.15 },
  { id: '6m', name: '6m Ham Band', center: 51.0 },
  { id: '2m', name: '2m Ham Band', center: 146.0 },
  { id: '70cm', name: '70cm Ham Band', center: 435.0 },
];

interface ElementDimension {
  element_type: 'reflector' | 'driven' | 'director';
  length: string;
  diameter: string;
  position: string;
}

interface TaperSection {
  length: string;
  start_diameter: string;
  end_diameter: string;
}

interface TaperConfig {
  enabled: boolean;
  num_tapers: number;
  sections: TaperSection[];
}

interface CoronaBallConfig {
  enabled: boolean;
  diameter: string;
}

interface StackingConfig {
  enabled: boolean;
  orientation: 'vertical' | 'horizontal';
  num_antennas: number;
  spacing: string;
  spacing_unit: 'ft' | 'inches';
}

interface AntennaInput {
  num_elements: number;
  elements: ElementDimension[];
  height_from_ground: string;
  height_unit: 'ft' | 'inches';
  boom_diameter: string;
  boom_unit: 'mm' | 'inches';
  band: string;
  frequency_mhz: string;
  stacking: StackingConfig;
  taper: TaperConfig;
  corona_balls: CoronaBallConfig;
}

interface AntennaOutput {
  swr: number;
  swr_description: string;
  fb_ratio: number;
  fb_ratio_description: string;
  fs_ratio: number;
  fs_ratio_description: string;
  beamwidth_h: number;
  beamwidth_v: number;
  beamwidth_description: string;
  bandwidth: number;
  bandwidth_description: string;
  gain_dbi: number;
  gain_description: string;
  multiplication_factor: number;
  multiplication_description: string;
  antenna_efficiency: number;
  efficiency_description: string;
  far_field_pattern: { angle: number; magnitude: number }[];
  swr_curve: { frequency: number; swr: number; channel: number }[];
  usable_bandwidth_1_5: number;
  usable_bandwidth_2_0: number;
  center_frequency: number;
  band_info: any;
  input_summary: any;
  stacking_enabled: boolean;
  stacking_info?: any;
  stacked_gain_dbi?: number;
  stacked_pattern?: { angle: number; magnitude: number }[];
  taper_info?: any;
  corona_info?: any;
}

const ResultCard = ({ title, value, description, icon, color }: { title: string; value: string; description: string; icon: keyof typeof Ionicons.glyphMap; color: string; }) => (
  <View style={[styles.resultCard, { borderLeftColor: color }]}>
    <View style={styles.resultHeader}>
      <Ionicons name={icon} size={18} color={color} />
      <Text style={styles.resultTitle}>{title}</Text>
    </View>
    <Text style={[styles.resultValue, { color }]}>{value}</Text>
    <Text style={styles.resultDescription}>{description}</Text>
  </View>
);

const SwrMeter = ({ data, centerFreq, usable15, usable20, channelSpacing }: { data: any[]; centerFreq: number; usable15: number; usable20: number; channelSpacing: number; }) => {
  const width = Math.min(screenWidth - 32, 400);
  const height = 200;
  const padding = { top: 20, right: 15, bottom: 45, left: 40 };
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;
  if (!data || data.length === 0) return null;
  const minFreq = Math.min(...data.map(d => d.frequency));
  const maxFreq = Math.max(...data.map(d => d.frequency));
  const freqRange = maxFreq - minFreq;
  const xScale = (freq: number) => padding.left + ((freq - minFreq) / freqRange) * chartWidth;
  const yScale = (swr: number) => padding.top + chartHeight - ((Math.min(swr, 3) - 1) / 2) * chartHeight;
  const createSwrPath = () => { let p = ''; data.forEach((pt, i) => { const x = xScale(pt.frequency); const y = yScale(pt.swr); p += i === 0 ? `M ${x} ${y}` : ` L ${x} ${y}`; }); return p; };
  const getUsableZone = (threshold: number) => { const pts = data.filter(p => p.swr <= threshold); if (!pts.length) return null; return { start: xScale(Math.min(...pts.map(p => p.frequency))), end: xScale(Math.max(...pts.map(p => p.frequency))) }; };
  const zone20 = getUsableZone(2.0); const zone15 = getUsableZone(1.5);
  const markers = data.filter(p => p.channel % 10 === 0);
  return (
    <View style={styles.swrContainer}>
      <Text style={styles.swrTitle}>SWR Bandwidth Meter</Text>
      <Text style={styles.swrSubtitle}>30 CH below / 30 CH above ({channelSpacing} kHz/CH)</Text>
      <Svg width={width} height={height}>
        <Rect x={padding.left} y={padding.top} width={chartWidth} height={chartHeight} fill="#1a1a1a" />
        {zone20 && <Rect x={zone20.start} y={padding.top} width={zone20.end - zone20.start} height={chartHeight} fill="rgba(255, 193, 7, 0.15)" />}
        {zone15 && <Rect x={zone15.start} y={padding.top} width={zone15.end - zone15.start} height={chartHeight} fill="rgba(76, 175, 80, 0.2)" />}
        {[1.0, 1.5, 2.0, 2.5, 3.0].map((swr) => (<G key={swr}><Line x1={padding.left} y1={yScale(swr)} x2={width - padding.right} y2={yScale(swr)} stroke={swr === 1.0 ? '#00BCD4' : swr === 1.5 ? '#4CAF50' : swr === 2.0 ? '#FFC107' : '#333'} strokeWidth={swr <= 2.0 ? 1.5 : 1} strokeDasharray={swr <= 2.0 ? '0' : '3,3'} /><SvgText x={padding.left - 5} y={yScale(swr) + 3} fill={swr === 1.0 ? '#00BCD4' : swr === 1.5 ? '#4CAF50' : swr === 2.0 ? '#FFC107' : '#666'} fontSize="9" textAnchor="end">{swr.toFixed(1)}</SvgText></G>))}
        {markers.map((pt) => (<G key={pt.channel}><Line x1={xScale(pt.frequency)} y1={height - padding.bottom} x2={xScale(pt.frequency)} y2={height - padding.bottom + 4} stroke={pt.channel === 0 ? '#2196F3' : '#555'} strokeWidth={pt.channel === 0 ? 2 : 1} /><SvgText x={xScale(pt.frequency)} y={height - padding.bottom + 14} fill={pt.channel === 0 ? '#2196F3' : '#666'} fontSize="8" textAnchor="middle">{pt.channel === 0 ? 'CTR' : pt.channel > 0 ? `+${pt.channel}` : pt.channel}</SvgText></G>))}
        <Line x1={xScale(centerFreq)} y1={padding.top} x2={xScale(centerFreq)} y2={height - padding.bottom} stroke="#2196F3" strokeWidth="2" strokeDasharray="4,4" />
        <Path d={createSwrPath()} fill="none" stroke="#FF5722" strokeWidth="2" />
        <SvgText x={padding.left} y={height - 3} fill="#888" fontSize="8" textAnchor="start">{minFreq.toFixed(3)}</SvgText>
        <SvgText x={xScale(centerFreq)} y={height - 28} fill="#2196F3" fontSize="8" textAnchor="middle">{centerFreq.toFixed(3)} MHz</SvgText>
        <SvgText x={width - padding.right} y={height - 3} fill="#888" fontSize="8" textAnchor="end">{maxFreq.toFixed(3)}</SvgText>
      </Svg>
      <View style={styles.swrLegend}>
        <View style={styles.legendItem}><View style={[styles.legendColor, { backgroundColor: '#00BCD4' }]} /><Text style={styles.legendText}>1.0:1</Text></View>
        <View style={styles.legendItem}><View style={[styles.legendColor, { backgroundColor: 'rgba(76, 175, 80, 0.6)' }]} /><Text style={styles.legendText}>≤1.5 ({usable15.toFixed(2)})</Text></View>
        <View style={styles.legendItem}><View style={[styles.legendColor, { backgroundColor: 'rgba(255, 193, 7, 0.6)' }]} /><Text style={styles.legendText}>≤2.0 ({usable20.toFixed(2)})</Text></View>
      </View>
    </View>
  );
};

const PolarPattern = ({ data, stackedData, isStacked }: { data: { angle: number; magnitude: number }[]; stackedData?: { angle: number; magnitude: number }[]; isStacked: boolean; }) => {
  const size = Math.min(screenWidth - 48, 280);
  const center = size / 2; const maxRadius = center - 25;
  const createPath = (d: any[]) => { if (!d?.length) return ''; let p = ''; d.forEach((pt, i) => { const r = (pt.magnitude / 100) * maxRadius; const a = (pt.angle - 90) * Math.PI / 180; const x = center + r * Math.cos(a); const y = center + r * Math.sin(a); p += i === 0 ? `M ${x} ${y}` : ` L ${x} ${y}`; }); return p + ' Z'; };
  return (
    <View style={styles.polarContainer}>
      <Text style={styles.polarTitle}>{isStacked ? 'Stacked Pattern' : 'Far Field Pattern'}</Text>
      <Svg width={size} height={size}>
        {[0.25, 0.5, 0.75, 1].map(s => <Circle key={s} cx={center} cy={center} r={maxRadius * s} stroke="#333" strokeWidth="1" fill="none" />)}
        <Line x1={center} y1={25} x2={center} y2={size - 25} stroke="#333" strokeWidth="1" />
        <Line x1={25} y1={center} x2={size - 25} y2={center} stroke="#333" strokeWidth="1" />
        <SvgText x={center} y={14} fill="#888" fontSize="9" textAnchor="middle">0°</SvgText>
        <SvgText x={size - 6} y={center + 3} fill="#888" fontSize="9" textAnchor="middle">90°</SvgText>
        <SvgText x={center} y={size - 5} fill="#888" fontSize="9" textAnchor="middle">180°</SvgText>
        <SvgText x={8} y={center + 3} fill="#888" fontSize="9" textAnchor="middle">270°</SvgText>
        <Path d={createPath(data)} fill={isStacked ? 'rgba(100,100,100,0.1)' : 'rgba(76,175,80,0.3)'} stroke={isStacked ? '#555' : '#4CAF50'} strokeWidth={isStacked ? 1 : 2} strokeDasharray={isStacked ? '4,4' : '0'} />
        {isStacked && stackedData && <Path d={createPath(stackedData)} fill="rgba(33,150,243,0.3)" stroke="#2196F3" strokeWidth="2" />}
        <Circle cx={center} cy={center} r={3} fill={isStacked ? '#2196F3' : '#4CAF50'} />
      </Svg>
    </View>
  );
};

const Dropdown = ({ label, value, options, onChange }: { label: string; value: string; options: { value: string; label: string }[]; onChange: (v: string) => void; }) => {
  const [open, setOpen] = useState(false);
  const sel = options.find(o => o.value === value);
  return (
    <View style={styles.dropdownContainer}>
      <Text style={styles.inputLabel}>{label}</Text>
      <TouchableOpacity style={styles.dropdownButton} onPress={() => setOpen(!open)}>
        <Text style={styles.dropdownButtonText}>{sel?.label || 'Select...'}</Text>
        <Ionicons name={open ? 'chevron-up' : 'chevron-down'} size={16} color="#888" />
      </TouchableOpacity>
      {open && <View style={styles.dropdownList}><ScrollView style={styles.dropdownScroll} nestedScrollEnabled>{options.map(o => (<TouchableOpacity key={o.value} style={[styles.dropdownItem, value === o.value && styles.dropdownItemSelected]} onPress={() => { onChange(o.value); setOpen(false); }}><Text style={[styles.dropdownItemText, value === o.value && styles.dropdownItemTextSelected]}>{o.label}</Text></TouchableOpacity>))}</ScrollView></View>}
    </View>
  );
};

const ElementInput = ({ element, index, onChange }: { element: ElementDimension; index: number; onChange: (i: number, f: keyof ElementDimension, v: string) => void; }) => {
  const title = element.element_type === 'reflector' ? 'Reflector' : element.element_type === 'driven' ? 'Driven Element' : `Director ${index - 1}`;
  const color = element.element_type === 'reflector' ? '#FF9800' : element.element_type === 'driven' ? '#4CAF50' : '#2196F3';
  return (
    <View style={[styles.elementCard, { borderLeftColor: color }]}>
      <Text style={[styles.elementTitle, { color }]}>{title}</Text>
      <View style={styles.elementRow}>
        <View style={styles.elementField}><Text style={styles.elementLabel}>Length (in)</Text><TextInput style={styles.elementInput} value={element.length} onChangeText={v => onChange(index, 'length', v)} keyboardType="decimal-pad" placeholder="216" placeholderTextColor="#555" /></View>
        <View style={styles.elementField}><Text style={styles.elementLabel}>Dia (in)</Text><TextInput style={styles.elementInput} value={element.diameter} onChangeText={v => onChange(index, 'diameter', v)} keyboardType="decimal-pad" placeholder="0.5" placeholderTextColor="#555" /></View>
      </View>
      {element.element_type !== 'reflector' && <View style={styles.elementField}><Text style={styles.elementLabel}>Position from Reflector (in)</Text><TextInput style={styles.elementInput} value={element.position} onChangeText={v => onChange(index, 'position', v)} keyboardType="decimal-pad" placeholder="48" placeholderTextColor="#555" /></View>}
    </View>
  );
};

const TaperCard = ({ taper, onChange }: { taper: TaperConfig; onChange: (f: string, v: any) => void; }) => {
  const updateSection = (idx: number, field: keyof TaperSection, value: string) => {
    const newSections = [...taper.sections];
    newSections[idx] = { ...newSections[idx], [field]: value };
    onChange('sections', newSections);
  };
  const updateNumTapers = (num: number) => {
    const sections: TaperSection[] = [];
    for (let i = 0; i < num; i++) {
      sections.push(taper.sections[i] || { length: (12 - i * 2).toString(), start_diameter: (0.5 - i * 0.05).toFixed(3), end_diameter: (0.375 - i * 0.05).toFixed(3) });
    }
    onChange('num_tapers', num);
    onChange('sections', sections);
  };
  return (
    <View style={styles.section}>
      <View style={styles.sectionHeaderRow}>
        <Text style={styles.sectionTitle}><Ionicons name="git-merge-outline" size={14} color="#E91E63" /> Tapered Elements</Text>
        <Switch value={taper.enabled} onValueChange={v => onChange('enabled', v)} trackColor={{ false: '#333', true: '#E91E63' }} thumbColor={taper.enabled ? '#fff' : '#888'} />
      </View>
      {taper.enabled && (
        <>
          <Text style={styles.taperHint}>Tapered elements provide higher gain and more broadband performance</Text>
          <Dropdown label="Number of Tapers (per side)" value={taper.num_tapers.toString()} options={[1,2,3,4,5].map(n => ({ value: n.toString(), label: `${n} Taper${n > 1 ? 's' : ''}` }))} onChange={v => updateNumTapers(parseInt(v))} />
          {taper.sections.map((sec, idx) => (
            <View key={idx} style={styles.taperSection}>
              <Text style={styles.taperSectionTitle}>Taper {idx + 1}</Text>
              <View style={styles.taperRow}>
                <View style={styles.taperField}><Text style={styles.elementLabel}>Length (in)</Text><TextInput style={styles.elementInput} value={sec.length} onChangeText={v => updateSection(idx, 'length', v)} keyboardType="decimal-pad" placeholder="12" placeholderTextColor="#555" /></View>
                <View style={styles.taperField}><Text style={styles.elementLabel}>Start Ø (in)</Text><TextInput style={styles.elementInput} value={sec.start_diameter} onChangeText={v => updateSection(idx, 'start_diameter', v)} keyboardType="decimal-pad" placeholder="0.5" placeholderTextColor="#555" /></View>
                <View style={styles.taperField}><Text style={styles.elementLabel}>End Ø (in)</Text><TextInput style={styles.elementInput} value={sec.end_diameter} onChangeText={v => updateSection(idx, 'end_diameter', v)} keyboardType="decimal-pad" placeholder="0.375" placeholderTextColor="#555" /></View>
              </View>
            </View>
          ))}
        </>
      )}
    </View>
  );
};

const CoronaCard = ({ corona, onChange }: { corona: CoronaBallConfig; onChange: (f: string, v: any) => void; }) => (
  <View style={styles.section}>
    <View style={styles.sectionHeaderRow}>
      <Text style={styles.sectionTitle}><Ionicons name="ellipse-outline" size={14} color="#00BCD4" /> Corona Balls</Text>
      <Switch value={corona.enabled} onValueChange={v => onChange('enabled', v)} trackColor={{ false: '#333', true: '#00BCD4' }} thumbColor={corona.enabled ? '#fff' : '#888'} />
    </View>
    {corona.enabled && (
      <View style={styles.inputGroup}>
        <Text style={styles.inputLabel}>Ball Diameter (inches)</Text>
        <TextInput style={styles.input} value={corona.diameter} onChangeText={v => onChange('diameter', v)} keyboardType="decimal-pad" placeholder="1.0" placeholderTextColor="#555" />
        <Text style={styles.coronaHint}>Corona balls reduce static discharge and can slightly improve bandwidth</Text>
      </View>
    )}
  </View>
);

const StackingCard = ({ stacking, onChange }: { stacking: StackingConfig; onChange: (f: keyof StackingConfig, v: any) => void; }) => (
  <View style={styles.section}>
    <View style={styles.sectionHeaderRow}>
      <Text style={styles.sectionTitle}><Ionicons name="layers-outline" size={14} color="#9C27B0" /> Antenna Stacking</Text>
      <Switch value={stacking.enabled} onValueChange={v => onChange('enabled', v)} trackColor={{ false: '#333', true: '#9C27B0' }} thumbColor={stacking.enabled ? '#fff' : '#888'} />
    </View>
    {stacking.enabled && (
      <>
        <View style={styles.orientationToggle}>
          <TouchableOpacity style={[styles.orientBtn, stacking.orientation === 'vertical' && styles.orientBtnActive]} onPress={() => onChange('orientation', 'vertical')}><Ionicons name="swap-vertical" size={18} color={stacking.orientation === 'vertical' ? '#fff' : '#888'} /><Text style={[styles.orientBtnText, stacking.orientation === 'vertical' && styles.orientBtnTextActive]}>Vertical</Text></TouchableOpacity>
          <TouchableOpacity style={[styles.orientBtn, stacking.orientation === 'horizontal' && styles.orientBtnActive]} onPress={() => onChange('orientation', 'horizontal')}><Ionicons name="swap-horizontal" size={18} color={stacking.orientation === 'horizontal' ? '#fff' : '#888'} /><Text style={[styles.orientBtnText, stacking.orientation === 'horizontal' && styles.orientBtnTextActive]}>Horizontal</Text></TouchableOpacity>
        </View>
        <Dropdown label="Number of Antennas" value={stacking.num_antennas.toString()} options={[2,3,4,5,6,7,8].map(n => ({ value: n.toString(), label: `${n} Antennas` }))} onChange={v => onChange('num_antennas', parseInt(v))} />
        <View style={styles.rowInput}>
          <View style={styles.flexInput}><Text style={styles.inputLabel}>Spacing</Text><TextInput style={styles.input} value={stacking.spacing} onChangeText={v => onChange('spacing', v)} keyboardType="decimal-pad" placeholder="20" placeholderTextColor="#555" /></View>
          <View style={styles.unitToggle}>
            <TouchableOpacity style={[styles.unitBtn, stacking.spacing_unit === 'ft' && styles.unitBtnActive]} onPress={() => onChange('spacing_unit', 'ft')}><Text style={[styles.unitBtnText, stacking.spacing_unit === 'ft' && styles.unitBtnTextActive]}>ft</Text></TouchableOpacity>
            <TouchableOpacity style={[styles.unitBtn, stacking.spacing_unit === 'inches' && styles.unitBtnActive]} onPress={() => onChange('spacing_unit', 'inches')}><Text style={[styles.unitBtnText, stacking.spacing_unit === 'inches' && styles.unitBtnTextActive]}>in</Text></TouchableOpacity>
          </View>
        </View>
      </>
    )}
  </View>
);

export default function AntennaCalculator() {
  const [inputs, setInputs] = useState<AntennaInput>({
    num_elements: 3,
    elements: [
      { element_type: 'reflector', length: '216', diameter: '0.5', position: '0' },
      { element_type: 'driven', length: '204', diameter: '0.5', position: '48' },
      { element_type: 'director', length: '195', diameter: '0.5', position: '96' },
    ],
    height_from_ground: '35', height_unit: 'ft', boom_diameter: '2', boom_unit: 'inches', band: '11m_cb', frequency_mhz: '27.185',
    stacking: { enabled: false, orientation: 'vertical', num_antennas: 2, spacing: '20', spacing_unit: 'ft' },
    taper: { enabled: false, num_tapers: 2, sections: [{ length: '12', start_diameter: '0.5', end_diameter: '0.375' }, { length: '10', start_diameter: '0.375', end_diameter: '0.25' }] },
    corona_balls: { enabled: false, diameter: '1.0' },
  });
  const [results, setResults] = useState<AntennaOutput | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [autoUpdate, setAutoUpdate] = useState(true);
  const debounceRef = useRef<NodeJS.Timeout | null>(null);

  const calculateAntenna = useCallback(async (showLoading = true) => {
    for (const elem of inputs.elements) { if (!elem.length || parseFloat(elem.length) <= 0 || !elem.diameter || parseFloat(elem.diameter) <= 0) return; }
    if (!inputs.height_from_ground || parseFloat(inputs.height_from_ground) <= 0 || !inputs.boom_diameter || parseFloat(inputs.boom_diameter) <= 0) return;
    if (inputs.stacking.enabled && (!inputs.stacking.spacing || parseFloat(inputs.stacking.spacing) <= 0)) return;
    if (showLoading) setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${BACKEND_URL}/api/calculate`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          num_elements: inputs.num_elements,
          elements: inputs.elements.map(e => ({ element_type: e.element_type, length: parseFloat(e.length) || 0, diameter: parseFloat(e.diameter) || 0, position: parseFloat(e.position) || 0 })),
          height_from_ground: parseFloat(inputs.height_from_ground) || 0, height_unit: inputs.height_unit,
          boom_diameter: parseFloat(inputs.boom_diameter) || 0, boom_unit: inputs.boom_unit,
          band: inputs.band, frequency_mhz: parseFloat(inputs.frequency_mhz) || null,
          stacking: inputs.stacking.enabled ? { enabled: true, orientation: inputs.stacking.orientation, num_antennas: inputs.stacking.num_antennas, spacing: parseFloat(inputs.stacking.spacing) || 0, spacing_unit: inputs.stacking.spacing_unit } : null,
          taper: inputs.taper.enabled ? { enabled: true, num_tapers: inputs.taper.num_tapers, sections: inputs.taper.sections.map(s => ({ length: parseFloat(s.length) || 0, start_diameter: parseFloat(s.start_diameter) || 0, end_diameter: parseFloat(s.end_diameter) || 0 })) } : null,
          corona_balls: inputs.corona_balls.enabled ? { enabled: true, diameter: parseFloat(inputs.corona_balls.diameter) || 1.0 } : null,
        }),
      });
      if (!response.ok) throw new Error((await response.json().catch(() => ({}))).detail || 'Calculation failed');
      setResults(await response.json());
    } catch (err) { if (showLoading) setError(err instanceof Error ? err.message : 'Error'); }
    finally { if (showLoading) setLoading(false); }
  }, [inputs]);

  useEffect(() => { if (!autoUpdate) return; if (debounceRef.current) clearTimeout(debounceRef.current); debounceRef.current = setTimeout(() => calculateAntenna(false), 400); return () => { if (debounceRef.current) clearTimeout(debounceRef.current); }; }, [inputs, autoUpdate]);
  useEffect(() => { calculateAntenna(true); }, []);

  const updateElementCount = (count: number) => {
    const c = Math.max(2, Math.min(20, count));
    const newElements: ElementDimension[] = [inputs.elements.find(e => e.element_type === 'reflector') || { element_type: 'reflector', length: '216', diameter: '0.5', position: '0' }, inputs.elements.find(e => e.element_type === 'driven') || { element_type: 'driven', length: '204', diameter: '0.5', position: '48' }];
    const dirs = inputs.elements.filter(e => e.element_type === 'director');
    for (let i = 0; i < c - 2; i++) newElements.push(dirs[i] || { element_type: 'director', length: (195 - i * 3).toString(), diameter: '0.5', position: (96 + i * 48).toString() });
    setInputs(prev => ({ ...prev, num_elements: c, elements: newElements }));
  };
  const updateElement = (idx: number, field: keyof ElementDimension, value: string) => setInputs(prev => { const e = [...prev.elements]; e[idx] = { ...e[idx], [field]: value }; return { ...prev, elements: e }; });
  const handleBandChange = (id: string) => { const b = BANDS.find(x => x.id === id); setInputs(prev => ({ ...prev, band: id, frequency_mhz: b ? b.center.toString() : prev.frequency_mhz })); };

  const elementOptions = Array.from({ length: 19 }, (_, i) => ({ value: (i + 2).toString(), label: `${i + 2} Elements` }));
  const bandOptions = BANDS.map(b => ({ value: b.id, label: b.name }));

  return (
    <SafeAreaView style={styles.container}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={styles.flex}>
        <ScrollView style={styles.scrollView} contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
          <View style={styles.header}>
            <Ionicons name="radio-outline" size={28} color="#4CAF50" />
            <Text style={styles.headerTitle}>Antenna Calculator</Text>
          </View>
          <View style={styles.autoUpdateRow}><Text style={styles.autoUpdateLabel}><Ionicons name="sync" size={14} color="#4CAF50" /> Live Update</Text><Switch value={autoUpdate} onValueChange={setAutoUpdate} trackColor={{ false: '#333', true: '#4CAF50' }} thumbColor={autoUpdate ? '#fff' : '#888'} /></View>
          <View style={styles.section}>
            <Text style={styles.sectionTitle}><Ionicons name="radio" size={14} color="#4CAF50" /> Band</Text>
            <Dropdown label="Operating Band" value={inputs.band} options={bandOptions} onChange={handleBandChange} />
            <View style={styles.inputGroup}><Text style={styles.inputLabel}>Center Frequency (MHz)</Text><TextInput style={styles.input} value={inputs.frequency_mhz} onChangeText={v => setInputs(p => ({ ...p, frequency_mhz: v }))} keyboardType="decimal-pad" placeholder="27.185" placeholderTextColor="#555" /></View>
          </View>
          <View style={styles.section}>
            <Text style={styles.sectionTitle}><Ionicons name="git-branch-outline" size={14} color="#4CAF50" /> Elements</Text>
            <Dropdown label="Number of Elements" value={inputs.num_elements.toString()} options={elementOptions} onChange={v => updateElementCount(parseInt(v))} />
            {inputs.elements.map((elem, idx) => <ElementInput key={`${elem.element_type}-${idx}`} element={elem} index={idx} onChange={updateElement} />)}
          </View>
          <View style={styles.section}>
            <Text style={styles.sectionTitle}><Ionicons name="construct-outline" size={14} color="#4CAF50" /> Physical Setup</Text>
            <View style={styles.rowInput}><View style={styles.flexInput}><Text style={styles.inputLabel}>Height from Ground</Text><TextInput style={styles.input} value={inputs.height_from_ground} onChangeText={v => setInputs(p => ({ ...p, height_from_ground: v }))} keyboardType="decimal-pad" placeholder="35" placeholderTextColor="#555" /></View><View style={styles.unitToggle}><TouchableOpacity style={[styles.unitBtn, inputs.height_unit === 'ft' && styles.unitBtnActive]} onPress={() => setInputs(p => ({ ...p, height_unit: 'ft' }))}><Text style={[styles.unitBtnText, inputs.height_unit === 'ft' && styles.unitBtnTextActive]}>ft</Text></TouchableOpacity><TouchableOpacity style={[styles.unitBtn, inputs.height_unit === 'inches' && styles.unitBtnActive]} onPress={() => setInputs(p => ({ ...p, height_unit: 'inches' }))}><Text style={[styles.unitBtnText, inputs.height_unit === 'inches' && styles.unitBtnTextActive]}>in</Text></TouchableOpacity></View></View>
            <View style={styles.rowInput}><View style={styles.flexInput}><Text style={styles.inputLabel}>Boom Diameter</Text><TextInput style={styles.input} value={inputs.boom_diameter} onChangeText={v => setInputs(p => ({ ...p, boom_diameter: v }))} keyboardType="decimal-pad" placeholder="2" placeholderTextColor="#555" /></View><View style={styles.unitToggle}><TouchableOpacity style={[styles.unitBtn, inputs.boom_unit === 'mm' && styles.unitBtnActive]} onPress={() => setInputs(p => ({ ...p, boom_unit: 'mm' }))}><Text style={[styles.unitBtnText, inputs.boom_unit === 'mm' && styles.unitBtnTextActive]}>mm</Text></TouchableOpacity><TouchableOpacity style={[styles.unitBtn, inputs.boom_unit === 'inches' && styles.unitBtnActive]} onPress={() => setInputs(p => ({ ...p, boom_unit: 'inches' }))}><Text style={[styles.unitBtnText, inputs.boom_unit === 'inches' && styles.unitBtnTextActive]}>in</Text></TouchableOpacity></View></View>
          </View>
          <TaperCard taper={inputs.taper} onChange={(f, v) => setInputs(p => ({ ...p, taper: { ...p.taper, [f]: v } }))} />
          <CoronaCard corona={inputs.corona_balls} onChange={(f, v) => setInputs(p => ({ ...p, corona_balls: { ...p.corona_balls, [f]: v } }))} />
          <StackingCard stacking={inputs.stacking} onChange={(f, v) => setInputs(p => ({ ...p, stacking: { ...p.stacking, [f]: v } }))} />
          {error && <View style={styles.errorContainer}><Ionicons name="alert-circle" size={16} color="#f44336" /><Text style={styles.errorText}>{error}</Text></View>}
          {loading && autoUpdate && <View style={styles.loadingRow}><ActivityIndicator color="#4CAF50" size="small" /><Text style={styles.loadingText}>Calculating...</Text></View>}
          {results && (
            <View style={styles.resultsSection}>
              <Text style={styles.sectionTitle}><Ionicons name="analytics" size={14} color="#4CAF50" /> Results</Text>
              <View style={styles.bandInfoCard}><Text style={styles.bandInfoTitle}>{results.band_info.name}</Text><Text style={styles.bandInfoText}>{results.center_frequency.toFixed(3)} MHz</Text></View>
              {results.taper_info && <View style={styles.taperResults}><Text style={styles.taperResultsTitle}><Ionicons name="git-merge" size={14} color="#E91E63" /> Taper Bonus</Text><Text style={styles.taperResultsText}>+{results.taper_info.gain_bonus} dB gain | +{results.taper_info.bandwidth_improvement} bandwidth</Text></View>}
              {results.corona_info && <View style={styles.coronaResults}><Text style={styles.coronaResultsTitle}><Ionicons name="ellipse" size={14} color="#00BCD4" /> Corona Protection</Text><Text style={styles.coronaResultsText}>{results.corona_info.corona_reduction}% discharge reduction</Text></View>}
              {results.stacking_enabled && results.stacking_info && <View style={styles.stackingResults}><Text style={styles.stackingResultsTitle}><Ionicons name="layers" size={14} color="#9C27B0" /> Stacked ({results.stacking_info.num_antennas}x)</Text><Text style={styles.stackingResultsText}>{results.gain_dbi} → {results.stacked_gain_dbi} dBi (+{results.stacking_info.gain_increase_db} dB)</Text></View>}
              <SwrMeter data={results.swr_curve} centerFreq={results.center_frequency} usable15={results.usable_bandwidth_1_5} usable20={results.usable_bandwidth_2_0} channelSpacing={results.band_info.channel_spacing_khz} />
              <ResultCard title="Gain" value={`${results.stacking_enabled ? results.stacked_gain_dbi : results.gain_dbi} dBi`} description={results.gain_description} icon="trending-up" color="#4CAF50" />
              <ResultCard title="SWR" value={`${results.swr}:1`} description={results.swr_description} icon="pulse" color={results.swr <= 1.1 ? '#00BCD4' : results.swr <= 1.5 ? '#4CAF50' : '#FFC107'} />
              <View style={styles.ratioRow}>
                <View style={styles.ratioCard}><Text style={styles.ratioLabel}>F/B Ratio</Text><Text style={styles.ratioValue}>{results.fb_ratio} dB</Text></View>
                <View style={styles.ratioCard}><Text style={styles.ratioLabel}>F/S Ratio</Text><Text style={styles.ratioValue}>{results.fs_ratio} dB</Text></View>
              </View>
              <ResultCard title="Beamwidth" value={`H: ${results.beamwidth_h}° / V: ${results.beamwidth_v}°`} description={results.beamwidth_description} icon="radio-button-on" color="#FF9800" />
              <ResultCard title="Usable BW (≤1.5:1)" value={`${results.usable_bandwidth_1_5.toFixed(3)} MHz`} description={`At 2:1: ${results.usable_bandwidth_2_0.toFixed(3)} MHz`} icon="resize" color="#00BCD4" />
              <ResultCard title="Efficiency" value={`${results.antenna_efficiency}%`} description={results.efficiency_description} icon="speedometer" color="#8BC34A" />
              <PolarPattern data={results.far_field_pattern} stackedData={results.stacked_pattern} isStacked={results.stacking_enabled} />
            </View>
          )}
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#121212' }, flex: { flex: 1 }, scrollView: { flex: 1 }, scrollContent: { padding: 12, paddingBottom: 40 },
  header: { alignItems: 'center', marginBottom: 8, paddingVertical: 6 }, headerTitle: { fontSize: 22, fontWeight: 'bold', color: '#fff', marginTop: 4 },
  autoUpdateRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', backgroundColor: '#1a1a1a', borderRadius: 10, padding: 10, marginBottom: 10 }, autoUpdateLabel: { fontSize: 13, color: '#4CAF50', fontWeight: '500' },
  section: { backgroundColor: '#1a1a1a', borderRadius: 10, padding: 10, marginBottom: 10 }, sectionTitle: { fontSize: 14, fontWeight: '600', color: '#fff', marginBottom: 8 }, sectionHeaderRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
  inputGroup: { marginBottom: 8 }, inputLabel: { fontSize: 11, color: '#aaa', marginBottom: 4 }, input: { backgroundColor: '#252525', borderRadius: 8, padding: 10, fontSize: 13, color: '#fff', borderWidth: 1, borderColor: '#333' },
  rowInput: { flexDirection: 'row', alignItems: 'flex-end', marginBottom: 8, gap: 8 }, flexInput: { flex: 1 },
  unitToggle: { flexDirection: 'row', backgroundColor: '#252525', borderRadius: 8, overflow: 'hidden' }, unitBtn: { paddingVertical: 10, paddingHorizontal: 10, minWidth: 36 }, unitBtnActive: { backgroundColor: '#4CAF50' }, unitBtnText: { fontSize: 12, color: '#888', textAlign: 'center' }, unitBtnTextActive: { color: '#fff', fontWeight: '600' },
  orientationToggle: { flexDirection: 'row', gap: 8, marginBottom: 10 }, orientBtn: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', backgroundColor: '#252525', borderRadius: 8, padding: 10, gap: 5 }, orientBtnActive: { backgroundColor: '#9C27B0' }, orientBtnText: { fontSize: 12, color: '#888' }, orientBtnTextActive: { color: '#fff', fontWeight: '600' },
  dropdownContainer: { marginBottom: 8 }, dropdownButton: { backgroundColor: '#252525', borderRadius: 8, padding: 10, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', borderWidth: 1, borderColor: '#333' }, dropdownButtonText: { fontSize: 13, color: '#fff' }, dropdownList: { backgroundColor: '#2a2a2a', borderRadius: 8, marginTop: 4, maxHeight: 160, borderWidth: 1, borderColor: '#333' }, dropdownScroll: { maxHeight: 160 }, dropdownItem: { padding: 10, borderBottomWidth: 1, borderBottomColor: '#333' }, dropdownItemSelected: { backgroundColor: '#333' }, dropdownItemText: { fontSize: 12, color: '#ccc' }, dropdownItemTextSelected: { color: '#4CAF50', fontWeight: '500' },
  elementCard: { backgroundColor: '#222', borderRadius: 8, padding: 8, marginTop: 6, borderLeftWidth: 3 }, elementTitle: { fontSize: 12, fontWeight: '600', marginBottom: 6 }, elementRow: { flexDirection: 'row', gap: 8 }, elementField: { flex: 1, marginBottom: 4 }, elementLabel: { fontSize: 10, color: '#888', marginBottom: 2 }, elementInput: { backgroundColor: '#1a1a1a', borderRadius: 6, padding: 8, fontSize: 12, color: '#fff', borderWidth: 1, borderColor: '#333' },
  taperHint: { fontSize: 10, color: '#E91E63', marginBottom: 8, fontStyle: 'italic' }, taperSection: { backgroundColor: '#222', borderRadius: 8, padding: 8, marginTop: 6 }, taperSectionTitle: { fontSize: 11, color: '#E91E63', fontWeight: '600', marginBottom: 6 }, taperRow: { flexDirection: 'row', gap: 6 }, taperField: { flex: 1 },
  coronaHint: { fontSize: 10, color: '#00BCD4', marginTop: 6, fontStyle: 'italic' },
  errorContainer: { flexDirection: 'row', alignItems: 'center', backgroundColor: 'rgba(244, 67, 54, 0.1)', padding: 8, borderRadius: 8, marginBottom: 10 }, errorText: { color: '#f44336', marginLeft: 6, flex: 1, fontSize: 11 },
  loadingRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', padding: 8, gap: 8 }, loadingText: { color: '#4CAF50', fontSize: 12 },
  resultsSection: { marginBottom: 10 }, bandInfoCard: { backgroundColor: '#1a1a1a', borderRadius: 10, padding: 8, marginBottom: 8, alignItems: 'center' }, bandInfoTitle: { fontSize: 14, fontWeight: '600', color: '#4CAF50' }, bandInfoText: { fontSize: 11, color: '#888', marginTop: 2 },
  taperResults: { backgroundColor: '#1a1a1a', borderRadius: 8, padding: 8, marginBottom: 8, borderWidth: 1, borderColor: '#E91E63' }, taperResultsTitle: { fontSize: 12, fontWeight: '600', color: '#E91E63' }, taperResultsText: { fontSize: 11, color: '#ccc', marginTop: 4 },
  coronaResults: { backgroundColor: '#1a1a1a', borderRadius: 8, padding: 8, marginBottom: 8, borderWidth: 1, borderColor: '#00BCD4' }, coronaResultsTitle: { fontSize: 12, fontWeight: '600', color: '#00BCD4' }, coronaResultsText: { fontSize: 11, color: '#ccc', marginTop: 4 },
  stackingResults: { backgroundColor: '#1a1a1a', borderRadius: 8, padding: 8, marginBottom: 8, borderWidth: 1, borderColor: '#9C27B0' }, stackingResultsTitle: { fontSize: 12, fontWeight: '600', color: '#9C27B0' }, stackingResultsText: { fontSize: 11, color: '#ccc', marginTop: 4 },
  resultCard: { backgroundColor: '#1a1a1a', borderRadius: 10, padding: 10, marginBottom: 6, borderLeftWidth: 3 }, resultHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 3, gap: 5 }, resultTitle: { fontSize: 10, color: '#888', textTransform: 'uppercase', letterSpacing: 0.5 }, resultValue: { fontSize: 22, fontWeight: 'bold', marginBottom: 2 }, resultDescription: { fontSize: 10, color: '#888' },
  ratioRow: { flexDirection: 'row', gap: 8, marginBottom: 6 }, ratioCard: { flex: 1, backgroundColor: '#1a1a1a', borderRadius: 10, padding: 10, alignItems: 'center' }, ratioLabel: { fontSize: 10, color: '#888', marginBottom: 4 }, ratioValue: { fontSize: 18, fontWeight: 'bold', color: '#9C27B0' },
  swrContainer: { backgroundColor: '#1a1a1a', borderRadius: 10, padding: 10, marginBottom: 8, alignItems: 'center' }, swrTitle: { fontSize: 13, fontWeight: '600', color: '#fff', marginBottom: 2 }, swrSubtitle: { fontSize: 9, color: '#666', marginBottom: 8 }, swrLegend: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'center', marginTop: 6, gap: 8 }, legendItem: { flexDirection: 'row', alignItems: 'center', gap: 4 }, legendColor: { width: 10, height: 10, borderRadius: 2 }, legendText: { fontSize: 9, color: '#888' },
  polarContainer: { backgroundColor: '#1a1a1a', borderRadius: 10, padding: 10, alignItems: 'center', marginTop: 4 }, polarTitle: { fontSize: 13, fontWeight: '600', color: '#fff', marginBottom: 8 },
});
