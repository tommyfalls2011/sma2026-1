import React, { useState, useCallback, useEffect, useRef } from 'react';
import { View, Text, StyleSheet, ScrollView, TextInput, TouchableOpacity, ActivityIndicator, KeyboardAvoidingView, Platform, Dimensions, Switch, Alert } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import Svg, { Circle, Line, Path, Text as SvgText, Rect, G } from 'react-native-svg';
import { useRouter } from 'expo-router';
import { useAuth } from './context/AuthContext';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL || '';
const { width: screenWidth } = Dimensions.get('window');

const TIER_COLORS: Record<string, string> = {
  trial: '#888',
  bronze: '#CD7F32',
  silver: '#C0C0C0',
  gold: '#FFD700',
  admin: '#9C27B0'
};

const BANDS = [
  { id: '11m_cb', name: '11m CB Band', center: 27.185 },
  { id: '10m', name: '10m Ham', center: 28.5 },
  { id: '12m', name: '12m Ham', center: 24.94 },
  { id: '15m', name: '15m Ham', center: 21.225 },
  { id: '17m', name: '17m Ham', center: 18.118 },
  { id: '20m', name: '20m Ham', center: 14.175 },
  { id: '6m', name: '6m Ham', center: 51.0 },
  { id: '2m', name: '2m Ham', center: 146.0 },
];

interface ElementDimension { element_type: 'reflector' | 'driven' | 'director'; length: string; diameter: string; position: string; }
interface TaperSection { length: string; start_diameter: string; end_diameter: string; }
interface TaperConfig { enabled: boolean; num_tapers: number; sections: TaperSection[]; }
interface CoronaBallConfig { enabled: boolean; diameter: string; }
interface StackingConfig { enabled: boolean; orientation: 'vertical' | 'horizontal'; num_antennas: number; spacing: string; spacing_unit: 'ft' | 'inches'; }
interface AntennaInput { num_elements: number; elements: ElementDimension[]; height_from_ground: string; height_unit: 'ft' | 'inches'; boom_diameter: string; boom_unit: 'mm' | 'inches'; band: string; frequency_mhz: string; stacking: StackingConfig; taper: TaperConfig; corona_balls: CoronaBallConfig; }
interface AntennaOutput { swr: number; swr_description: string; fb_ratio: number; fs_ratio: number; beamwidth_h: number; beamwidth_v: number; bandwidth: number; gain_dbi: number; gain_description: string; multiplication_factor: number; antenna_efficiency: number; far_field_pattern: any[]; swr_curve: any[]; usable_bandwidth_1_5: number; usable_bandwidth_2_0: number; center_frequency: number; band_info: any; stacking_enabled: boolean; stacking_info?: any; stacked_gain_dbi?: number; stacked_pattern?: any[]; taper_info?: any; corona_info?: any; }

const ResultCard = ({ title, value, description, icon, color }: any) => (
  <View style={[styles.resultCard, { borderLeftColor: color }]}>
    <View style={styles.resultHeader}><Ionicons name={icon} size={16} color={color} /><Text style={styles.resultTitle}>{title}</Text></View>
    <Text style={[styles.resultValue, { color }]}>{value}</Text>
    {description && <Text style={styles.resultDescription}>{description}</Text>}
  </View>
);

const SwrMeter = ({ data, centerFreq, usable15, usable20, channelSpacing }: any) => {
  const width = Math.min(screenWidth - 32, 380); const height = 180;
  const padding = { top: 18, right: 12, bottom: 42, left: 36 };
  const chartWidth = width - padding.left - padding.right; const chartHeight = height - padding.top - padding.bottom;
  if (!data?.length) return null;
  const minFreq = Math.min(...data.map((d: any) => d.frequency)); const maxFreq = Math.max(...data.map((d: any) => d.frequency)); const freqRange = maxFreq - minFreq;
  const xScale = (freq: number) => padding.left + ((freq - minFreq) / freqRange) * chartWidth;
  const yScale = (swr: number) => padding.top + chartHeight - ((Math.min(swr, 3) - 1) / 2) * chartHeight;
  const createSwrPath = () => { let p = ''; data.forEach((pt: any, i: number) => { p += i === 0 ? `M ${xScale(pt.frequency)} ${yScale(pt.swr)}` : ` L ${xScale(pt.frequency)} ${yScale(pt.swr)}`; }); return p; };
  const getUsableZone = (threshold: number) => { const pts = data.filter((p: any) => p.swr <= threshold); if (!pts.length) return null; return { start: xScale(Math.min(...pts.map((p: any) => p.frequency))), end: xScale(Math.max(...pts.map((p: any) => p.frequency))) }; };
  const zone20 = getUsableZone(2.0); const zone15 = getUsableZone(1.5); const markers = data.filter((p: any) => p.channel % 10 === 0);
  return (
    <View style={styles.swrContainer}>
      <Text style={styles.swrTitle}>SWR Bandwidth</Text>
      <Svg width={width} height={height}>
        <Rect x={padding.left} y={padding.top} width={chartWidth} height={chartHeight} fill="#1a1a1a" />
        {zone20 && <Rect x={zone20.start} y={padding.top} width={zone20.end - zone20.start} height={chartHeight} fill="rgba(255,193,7,0.15)" />}
        {zone15 && <Rect x={zone15.start} y={padding.top} width={zone15.end - zone15.start} height={chartHeight} fill="rgba(76,175,80,0.2)" />}
        {[1.0, 1.5, 2.0, 3.0].map(swr => (<G key={swr}><Line x1={padding.left} y1={yScale(swr)} x2={width - padding.right} y2={yScale(swr)} stroke={swr === 1.0 ? '#00BCD4' : swr === 1.5 ? '#4CAF50' : swr === 2.0 ? '#FFC107' : '#333'} strokeWidth={swr <= 2.0 ? 1.2 : 0.8} strokeDasharray={swr > 2.0 ? '3,3' : '0'} /><SvgText x={padding.left - 4} y={yScale(swr) + 3} fill={swr === 1.0 ? '#00BCD4' : swr === 1.5 ? '#4CAF50' : swr === 2.0 ? '#FFC107' : '#555'} fontSize="8" textAnchor="end">{swr.toFixed(1)}</SvgText></G>))}
        {markers.map((pt: any) => (<G key={pt.channel}><Line x1={xScale(pt.frequency)} y1={height - padding.bottom} x2={xScale(pt.frequency)} y2={height - padding.bottom + 3} stroke={pt.channel === 0 ? '#2196F3' : '#444'} strokeWidth={pt.channel === 0 ? 1.5 : 0.8} /><SvgText x={xScale(pt.frequency)} y={height - padding.bottom + 12} fill={pt.channel === 0 ? '#2196F3' : '#555'} fontSize="7" textAnchor="middle">{pt.channel === 0 ? 'CTR' : pt.channel > 0 ? `+${pt.channel}` : pt.channel}</SvgText></G>))}
        <Line x1={xScale(centerFreq)} y1={padding.top} x2={xScale(centerFreq)} y2={height - padding.bottom} stroke="#2196F3" strokeWidth="1.5" strokeDasharray="3,3" />
        <Path d={createSwrPath()} fill="none" stroke="#FF5722" strokeWidth="2" />
        <SvgText x={width / 2} y={height - 3} fill="#2196F3" fontSize="8" textAnchor="middle">{centerFreq.toFixed(3)} MHz</SvgText>
      </Svg>
      <View style={styles.swrLegend}>
        <View style={styles.legendItem}><View style={[styles.legendColor, { backgroundColor: '#4CAF50' }]} /><Text style={styles.legendText}>≤1.5 ({usable15?.toFixed(2)})</Text></View>
        <View style={styles.legendItem}><View style={[styles.legendColor, { backgroundColor: '#FFC107' }]} /><Text style={styles.legendText}>≤2.0 ({usable20?.toFixed(2)})</Text></View>
      </View>
    </View>
  );
};

const PolarPattern = ({ data, stackedData, isStacked }: any) => {
  const size = Math.min(screenWidth - 48, 260); const center = size / 2; const maxRadius = center - 22;
  const createPath = (d: any[]) => { if (!d?.length) return ''; let p = ''; d.forEach((pt, i) => { const r = (pt.magnitude / 100) * maxRadius; const a = (pt.angle - 90) * Math.PI / 180; p += i === 0 ? `M ${center + r * Math.cos(a)} ${center + r * Math.sin(a)}` : ` L ${center + r * Math.cos(a)} ${center + r * Math.sin(a)}`; }); return p + ' Z'; };
  return (
    <View style={styles.polarContainer}>
      <Text style={styles.polarTitle}>Radiation Pattern</Text>
      <Svg width={size} height={size}>
        {[0.25, 0.5, 0.75, 1].map(s => <Circle key={s} cx={center} cy={center} r={maxRadius * s} stroke="#333" strokeWidth="0.8" fill="none" />)}
        <Line x1={center} y1={22} x2={center} y2={size - 22} stroke="#333" strokeWidth="0.8" />
        <Line x1={22} y1={center} x2={size - 22} y2={center} stroke="#333" strokeWidth="0.8" />
        <Path d={createPath(data)} fill={isStacked ? 'rgba(100,100,100,0.1)' : 'rgba(76,175,80,0.3)'} stroke={isStacked ? '#555' : '#4CAF50'} strokeWidth={isStacked ? 0.8 : 1.5} strokeDasharray={isStacked ? '3,3' : '0'} />
        {isStacked && stackedData && <Path d={createPath(stackedData)} fill="rgba(33,150,243,0.3)" stroke="#2196F3" strokeWidth="1.5" />}
        <Circle cx={center} cy={center} r={2.5} fill={isStacked ? '#2196F3' : '#4CAF50'} />
      </Svg>
    </View>
  );
};

const Dropdown = ({ label, value, options, onChange }: any) => {
  const [open, setOpen] = useState(false);
  return (
    <View style={styles.dropdownContainer}>
      {label && <Text style={styles.inputLabel}>{label}</Text>}
      <TouchableOpacity style={styles.dropdownButton} onPress={() => setOpen(!open)}>
        <Text style={styles.dropdownButtonText}>{options.find((o: any) => o.value === value)?.label || 'Select'}</Text>
        <Ionicons name={open ? 'chevron-up' : 'chevron-down'} size={14} color="#888" />
      </TouchableOpacity>
      {open && <View style={styles.dropdownList}><ScrollView style={{ maxHeight: 150 }} nestedScrollEnabled>{options.map((o: any) => (<TouchableOpacity key={o.value} style={[styles.dropdownItem, value === o.value && styles.dropdownItemSelected]} onPress={() => { onChange(o.value); setOpen(false); }}><Text style={[styles.dropdownItemText, value === o.value && styles.dropdownItemTextSelected]}>{o.label}</Text></TouchableOpacity>))}</ScrollView></View>}
    </View>
  );
};

const ElementInput = ({ element, index, onChange }: any) => {
  const title = element.element_type === 'reflector' ? 'Reflector' : element.element_type === 'driven' ? 'Driven' : `Dir ${index - 1}`;
  const color = element.element_type === 'reflector' ? '#FF9800' : element.element_type === 'driven' ? '#4CAF50' : '#2196F3';
  return (
    <View style={[styles.elementCard, { borderLeftColor: color }]}>
      <Text style={[styles.elementTitle, { color }]}>{title}</Text>
      <View style={styles.elementRow}>
        <View style={styles.elementField}><Text style={styles.elementLabel}>Length"</Text><TextInput style={styles.elementInput} value={element.length} onChangeText={v => onChange(index, 'length', v)} keyboardType="decimal-pad" placeholder="0" placeholderTextColor="#555" /></View>
        <View style={styles.elementField}><Text style={styles.elementLabel}>Dia"</Text><TextInput style={styles.elementInput} value={element.diameter} onChangeText={v => onChange(index, 'diameter', v)} keyboardType="decimal-pad" placeholder="0.5" placeholderTextColor="#555" /></View>
        <View style={styles.elementField}><Text style={styles.elementLabel}>Pos"</Text><TextInput style={styles.elementInput} value={element.position} onChangeText={v => onChange(index, 'position', v)} keyboardType="decimal-pad" placeholder="0" placeholderTextColor="#555" /></View>
      </View>
    </View>
  );
};

export default function AntennaCalculator() {
  const router = useRouter();
  const { user, loading: authLoading, getMaxElements, isFeatureAvailable, tiers } = useAuth();
  
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
  const [tuning, setTuning] = useState(false);
  const debounceRef = useRef<NodeJS.Timeout | null>(null);

  // Get max elements based on subscription
  const maxElements = user ? getMaxElements() : 3;

  // Calculate on ANY input change
  const calculateAntenna = useCallback(async () => {
    for (const elem of inputs.elements) {
      if (!elem.length || parseFloat(elem.length) <= 0 || !elem.diameter || parseFloat(elem.diameter) <= 0) return;
    }
    if (!inputs.height_from_ground || parseFloat(inputs.height_from_ground) <= 0 || !inputs.boom_diameter || parseFloat(inputs.boom_diameter) <= 0) return;
    
    try {
      const response = await fetch(`${BACKEND_URL}/api/calculate`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          num_elements: inputs.num_elements,
          elements: inputs.elements.map(e => ({ element_type: e.element_type, length: parseFloat(e.length) || 0, diameter: parseFloat(e.diameter) || 0, position: parseFloat(e.position) || 0 })),
          height_from_ground: parseFloat(inputs.height_from_ground) || 0, height_unit: inputs.height_unit,
          boom_diameter: parseFloat(inputs.boom_diameter) || 0, boom_unit: inputs.boom_unit,
          band: inputs.band, frequency_mhz: parseFloat(inputs.frequency_mhz) || null,
          stacking: inputs.stacking.enabled ? { ...inputs.stacking, spacing: parseFloat(inputs.stacking.spacing) || 0 } : null,
          taper: inputs.taper.enabled ? { ...inputs.taper, sections: inputs.taper.sections.map(s => ({ length: parseFloat(s.length) || 0, start_diameter: parseFloat(s.start_diameter) || 0, end_diameter: parseFloat(s.end_diameter) || 0 })) } : null,
          corona_balls: inputs.corona_balls.enabled ? { ...inputs.corona_balls, diameter: parseFloat(inputs.corona_balls.diameter) || 1.0 } : null,
        }),
      });
      if (response.ok) setResults(await response.json());
    } catch (err) { console.error(err); }
  }, [inputs]);

  // Debounced auto-calculate on every change
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => calculateAntenna(), 300);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [inputs]);

  useEffect(() => { calculateAntenna(); }, []);

  const autoTune = async () => {
    setTuning(true);
    try {
      const response = await fetch(`${BACKEND_URL}/api/auto-tune`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          num_elements: inputs.num_elements,
          height_from_ground: parseFloat(inputs.height_from_ground) || 35,
          height_unit: inputs.height_unit,
          boom_diameter: parseFloat(inputs.boom_diameter) || 2,
          boom_unit: inputs.boom_unit,
          band: inputs.band,
          frequency_mhz: parseFloat(inputs.frequency_mhz) || null,
          taper: inputs.taper.enabled ? inputs.taper : null,
          corona_balls: inputs.corona_balls.enabled ? inputs.corona_balls : null,
        }),
      });
      if (response.ok) {
        const data = await response.json();
        // Apply optimized elements
        const newElements = data.optimized_elements.map((e: any) => ({
          element_type: e.element_type,
          length: e.length.toString(),
          diameter: e.diameter.toString(),
          position: e.position.toString(),
        }));
        setInputs(prev => ({ ...prev, elements: newElements }));
        Alert.alert('Auto-Tune Complete', `Predicted SWR: ${data.predicted_swr}:1\nPredicted Gain: ${data.predicted_gain} dBi\n\n${data.optimization_notes.slice(0, 3).join('\n')}`);
      }
    } catch (err) { Alert.alert('Error', 'Auto-tune failed'); }
    setTuning(false);
  };

  const updateElementCount = (count: number) => {
    const c = Math.max(2, Math.min(maxElements, count));
    if (count > maxElements) {
      Alert.alert('Upgrade Required', `Your ${user?.subscription_tier || 'trial'} plan allows up to ${maxElements} elements. Upgrade to unlock more!`, [
        { text: 'Cancel', style: 'cancel' },
        { text: 'Upgrade', onPress: () => router.push('/subscription') }
      ]);
      return;
    }
    const newElements: ElementDimension[] = [
      inputs.elements.find(e => e.element_type === 'reflector') || { element_type: 'reflector', length: '216', diameter: '0.5', position: '0' },
      inputs.elements.find(e => e.element_type === 'driven') || { element_type: 'driven', length: '204', diameter: '0.5', position: '48' }
    ];
    const dirs = inputs.elements.filter(e => e.element_type === 'director');
    for (let i = 0; i < c - 2; i++) newElements.push(dirs[i] || { element_type: 'director', length: (195 - i * 3).toString(), diameter: '0.5', position: (96 + i * 48).toString() });
    setInputs(prev => ({ ...prev, num_elements: c, elements: newElements }));
  };

  const updateElement = (idx: number, field: keyof ElementDimension, value: string) => {
    setInputs(prev => { const e = [...prev.elements]; e[idx] = { ...e[idx], [field]: value }; return { ...prev, elements: e }; });
  };

  const handleBandChange = (id: string) => {
    const b = BANDS.find(x => x.id === id);
    setInputs(prev => ({ ...prev, band: id, frequency_mhz: b ? b.center.toString() : prev.frequency_mhz }));
  };

  const updateTaperCount = (num: number) => {
    const sections: TaperSection[] = [];
    for (let i = 0; i < num; i++) sections.push(inputs.taper.sections[i] || { length: (12 - i * 2).toString(), start_diameter: (0.5 - i * 0.05).toFixed(3), end_diameter: (0.375 - i * 0.05).toFixed(3) });
    setInputs(prev => ({ ...prev, taper: { ...prev.taper, num_tapers: num, sections } }));
  };

  const updateTaperSection = (idx: number, field: keyof TaperSection, value: string) => {
    setInputs(prev => { const s = [...prev.taper.sections]; s[idx] = { ...s[idx], [field]: value }; return { ...prev, taper: { ...prev.taper, sections: s } }; });
  };

  // Generate element count options based on subscription
  const elementOptions = [];
  for (let i = 2; i <= 8; i++) {
    const isLocked = i > maxElements;
    elementOptions.push({
      value: i.toString(),
      label: isLocked ? `${i} Elements 🔒` : `${i} Elements`
    });
  }

  return (
    <SafeAreaView style={styles.container}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={styles.flex}>
        <ScrollView style={styles.scrollView} contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false} keyboardShouldPersistTaps="handled">
          
          {/* User Header */}
          <TouchableOpacity style={styles.userHeader} onPress={() => user ? router.push('/subscription') : router.push('/login')}>
            <View style={styles.userHeaderLeft}>
              <Ionicons name="radio-outline" size={24} color="#4CAF50" />
              <Text style={styles.headerTitle}>Antenna Calculator</Text>
            </View>
            {user ? (
              <View style={styles.userBadge}>
                <View style={[styles.tierDot, { backgroundColor: TIER_COLORS[user.subscription_tier] || '#888' }]} />
                <Text style={styles.userBadgeText}>{user.subscription_tier}</Text>
                <Ionicons name="chevron-forward" size={14} color="#888" />
              </View>
            ) : (
              <TouchableOpacity style={styles.loginBadge} onPress={() => router.push('/login')}>
                <Text style={styles.loginBadgeText}>Login</Text>
                <Ionicons name="log-in-outline" size={16} color="#4CAF50" />
              </TouchableOpacity>
            )}
          </TouchableOpacity>
          
          {/* Band & Frequency */}
          <View style={styles.section}>
            <View style={styles.rowSpaced}>
              <View style={{ flex: 1 }}><Dropdown label="Band" value={inputs.band} options={BANDS.map(b => ({ value: b.id, label: b.name }))} onChange={handleBandChange} /></View>
              <View style={{ flex: 1, marginLeft: 8 }}><Text style={styles.inputLabel}>Freq (MHz)</Text><TextInput style={styles.input} value={inputs.frequency_mhz} onChangeText={v => setInputs(p => ({ ...p, frequency_mhz: v }))} keyboardType="decimal-pad" /></View>
            </View>
          </View>

          {/* Elements */}
          <View style={styles.section}>
            <View style={styles.rowSpaced}>
              <Text style={styles.sectionTitle}><Ionicons name="git-branch-outline" size={14} color="#4CAF50" /> Elements</Text>
              <TouchableOpacity style={styles.autoTuneBtn} onPress={autoTune} disabled={tuning}>
                {tuning ? <ActivityIndicator size="small" color="#fff" /> : <><Ionicons name="flash" size={14} color="#fff" /><Text style={styles.autoTuneBtnText}>Auto-Tune</Text></>}
              </TouchableOpacity>
            </View>
            <View style={{ zIndex: 999 }}>
              <Dropdown value={inputs.num_elements.toString()} options={[2,3,4,5,6,7,8].map(n => ({ value: n.toString(), label: `${n} Elements` }))} onChange={(v: string) => updateElementCount(parseInt(v))} />
            </View>
            <View style={{ zIndex: 1 }}>
              {inputs.elements.map((elem, idx) => <ElementInput key={`${elem.element_type}-${idx}`} element={elem} index={idx} onChange={updateElement} />)}
            </View>
          </View>

          {/* Physical Setup */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}><Ionicons name="construct-outline" size={14} color="#4CAF50" /> Setup</Text>
            <View style={styles.rowSpaced}>
              <View style={{ flex: 1 }}><Text style={styles.inputLabel}>Height</Text><TextInput style={styles.input} value={inputs.height_from_ground} onChangeText={v => setInputs(p => ({ ...p, height_from_ground: v }))} keyboardType="decimal-pad" /></View>
              <View style={styles.unitToggle}><TouchableOpacity style={[styles.unitBtn, inputs.height_unit === 'ft' && styles.unitBtnActive]} onPress={() => setInputs(p => ({ ...p, height_unit: 'ft' }))}><Text style={[styles.unitBtnText, inputs.height_unit === 'ft' && styles.unitBtnTextActive]}>ft</Text></TouchableOpacity><TouchableOpacity style={[styles.unitBtn, inputs.height_unit === 'inches' && styles.unitBtnActive]} onPress={() => setInputs(p => ({ ...p, height_unit: 'inches' }))}><Text style={[styles.unitBtnText, inputs.height_unit === 'inches' && styles.unitBtnTextActive]}>in</Text></TouchableOpacity></View>
              <View style={{ flex: 1, marginLeft: 8 }}><Text style={styles.inputLabel}>Boom Ø</Text><TextInput style={styles.input} value={inputs.boom_diameter} onChangeText={v => setInputs(p => ({ ...p, boom_diameter: v }))} keyboardType="decimal-pad" /></View>
              <View style={styles.unitToggle}><TouchableOpacity style={[styles.unitBtn, inputs.boom_unit === 'mm' && styles.unitBtnActive]} onPress={() => setInputs(p => ({ ...p, boom_unit: 'mm' }))}><Text style={[styles.unitBtnText, inputs.boom_unit === 'mm' && styles.unitBtnTextActive]}>mm</Text></TouchableOpacity><TouchableOpacity style={[styles.unitBtn, inputs.boom_unit === 'inches' && styles.unitBtnActive]} onPress={() => setInputs(p => ({ ...p, boom_unit: 'inches' }))}><Text style={[styles.unitBtnText, inputs.boom_unit === 'inches' && styles.unitBtnTextActive]}>in</Text></TouchableOpacity></View>
            </View>
          </View>

          {/* Taper */}
          <View style={styles.section}>
            <View style={styles.sectionHeaderRow}><Text style={styles.sectionTitle}><Ionicons name="git-merge-outline" size={14} color="#E91E63" /> Tapered</Text><Switch value={inputs.taper.enabled} onValueChange={v => setInputs(p => ({ ...p, taper: { ...p.taper, enabled: v } }))} trackColor={{ false: '#333', true: '#E91E63' }} thumbColor="#fff" /></View>
            {inputs.taper.enabled && (
              <><Dropdown value={inputs.taper.num_tapers.toString()} options={[1,2,3,4,5].map(n => ({ value: n.toString(), label: `${n} Taper${n > 1 ? 's' : ''}` }))} onChange={(v: string) => updateTaperCount(parseInt(v))} />
              {inputs.taper.sections.map((sec, idx) => (<View key={idx} style={styles.taperSection}><Text style={styles.taperSectionTitle}>T{idx + 1}</Text><View style={styles.elementRow}><View style={styles.elementField}><Text style={styles.elementLabel}>Len"</Text><TextInput style={styles.elementInput} value={sec.length} onChangeText={v => updateTaperSection(idx, 'length', v)} keyboardType="decimal-pad" /></View><View style={styles.elementField}><Text style={styles.elementLabel}>StartØ</Text><TextInput style={styles.elementInput} value={sec.start_diameter} onChangeText={v => updateTaperSection(idx, 'start_diameter', v)} keyboardType="decimal-pad" /></View><View style={styles.elementField}><Text style={styles.elementLabel}>EndØ</Text><TextInput style={styles.elementInput} value={sec.end_diameter} onChangeText={v => updateTaperSection(idx, 'end_diameter', v)} keyboardType="decimal-pad" /></View></View></View>))}</>
            )}
          </View>

          {/* Corona */}
          <View style={styles.section}>
            <View style={styles.sectionHeaderRow}><Text style={styles.sectionTitle}><Ionicons name="ellipse-outline" size={14} color="#00BCD4" /> Corona Balls</Text><Switch value={inputs.corona_balls.enabled} onValueChange={v => setInputs(p => ({ ...p, corona_balls: { ...p.corona_balls, enabled: v } }))} trackColor={{ false: '#333', true: '#00BCD4' }} thumbColor="#fff" /></View>
            {inputs.corona_balls.enabled && <View style={{ marginTop: 8 }}><Text style={styles.inputLabel}>Diameter (in)</Text><TextInput style={styles.input} value={inputs.corona_balls.diameter} onChangeText={v => setInputs(p => ({ ...p, corona_balls: { ...p.corona_balls, diameter: v } }))} keyboardType="decimal-pad" /></View>}
          </View>

          {/* Stacking */}
          <View style={styles.section}>
            <View style={styles.sectionHeaderRow}><Text style={styles.sectionTitle}><Ionicons name="layers-outline" size={14} color="#9C27B0" /> Stacking</Text><Switch value={inputs.stacking.enabled} onValueChange={v => setInputs(p => ({ ...p, stacking: { ...p.stacking, enabled: v } }))} trackColor={{ false: '#333', true: '#9C27B0' }} thumbColor="#fff" /></View>
            {inputs.stacking.enabled && (
              <><View style={styles.orientationToggle}><TouchableOpacity style={[styles.orientBtn, inputs.stacking.orientation === 'vertical' && styles.orientBtnActive]} onPress={() => setInputs(p => ({ ...p, stacking: { ...p.stacking, orientation: 'vertical' } }))}><Ionicons name="swap-vertical" size={16} color={inputs.stacking.orientation === 'vertical' ? '#fff' : '#888'} /><Text style={[styles.orientBtnText, inputs.stacking.orientation === 'vertical' && styles.orientBtnTextActive]}>V</Text></TouchableOpacity><TouchableOpacity style={[styles.orientBtn, inputs.stacking.orientation === 'horizontal' && styles.orientBtnActive]} onPress={() => setInputs(p => ({ ...p, stacking: { ...p.stacking, orientation: 'horizontal' } }))}><Ionicons name="swap-horizontal" size={16} color={inputs.stacking.orientation === 'horizontal' ? '#fff' : '#888'} /><Text style={[styles.orientBtnText, inputs.stacking.orientation === 'horizontal' && styles.orientBtnTextActive]}>H</Text></TouchableOpacity></View>
              <View style={styles.rowSpaced}><View style={{ flex: 1 }}><Dropdown value={inputs.stacking.num_antennas.toString()} options={[2,3,4].map(n => ({ value: n.toString(), label: `${n}x` }))} onChange={(v: string) => setInputs(p => ({ ...p, stacking: { ...p.stacking, num_antennas: parseInt(v) } }))} /></View><View style={{ flex: 1, marginLeft: 8 }}><Text style={styles.inputLabel}>Spacing</Text><TextInput style={styles.input} value={inputs.stacking.spacing} onChangeText={v => setInputs(p => ({ ...p, stacking: { ...p.stacking, spacing: v } }))} keyboardType="decimal-pad" /></View><View style={styles.unitToggle}><TouchableOpacity style={[styles.unitBtn, inputs.stacking.spacing_unit === 'ft' && styles.unitBtnActive]} onPress={() => setInputs(p => ({ ...p, stacking: { ...p.stacking, spacing_unit: 'ft' } }))}><Text style={[styles.unitBtnText, inputs.stacking.spacing_unit === 'ft' && styles.unitBtnTextActive]}>ft</Text></TouchableOpacity><TouchableOpacity style={[styles.unitBtn, inputs.stacking.spacing_unit === 'inches' && styles.unitBtnActive]} onPress={() => setInputs(p => ({ ...p, stacking: { ...p.stacking, spacing_unit: 'inches' } }))}><Text style={[styles.unitBtnText, inputs.stacking.spacing_unit === 'inches' && styles.unitBtnTextActive]}>in</Text></TouchableOpacity></View></View></>
            )}
          </View>

          {/* Results */}
          {results && (
            <View style={styles.resultsSection}>
              <Text style={styles.sectionTitle}><Ionicons name="analytics" size={14} color="#4CAF50" /> Results</Text>
              
              {/* Bonuses */}
              {results.taper_info && <View style={styles.bonusCard}><Text style={styles.bonusText}><Ionicons name="git-merge" size={12} color="#E91E63" /> Taper: +{results.taper_info.gain_bonus}dB, +{results.taper_info.bandwidth_improvement} BW</Text></View>}
              {results.corona_info && <View style={styles.bonusCard}><Text style={styles.bonusText}><Ionicons name="ellipse" size={12} color="#00BCD4" /> Corona: {results.corona_info.corona_reduction}% reduction</Text></View>}
              {results.stacking_enabled && results.stacking_info && <View style={styles.bonusCard}><Text style={styles.bonusText}><Ionicons name="layers" size={12} color="#9C27B0" /> Stacked: +{results.stacking_info.gain_increase_db}dB ({results.gain_dbi}→{results.stacked_gain_dbi})</Text></View>}
              
              <SwrMeter data={results.swr_curve} centerFreq={results.center_frequency} usable15={results.usable_bandwidth_1_5} usable20={results.usable_bandwidth_2_0} channelSpacing={results.band_info?.channel_spacing_khz} />
              
              <View style={styles.mainResults}>
                <View style={styles.mainResultItem}><Text style={styles.mainResultLabel}>Gain</Text><Text style={[styles.mainResultValue, { color: '#4CAF50' }]}>{results.stacking_enabled ? results.stacked_gain_dbi : results.gain_dbi} dBi</Text></View>
                <View style={styles.mainResultItem}><Text style={styles.mainResultLabel}>SWR</Text><Text style={[styles.mainResultValue, { color: results.swr <= 1.5 ? '#4CAF50' : results.swr <= 2.0 ? '#FFC107' : '#f44336' }]}>{results.swr}:1</Text></View>
                <View style={styles.mainResultItem}><Text style={styles.mainResultLabel}>F/B</Text><Text style={styles.mainResultValue}>{results.fb_ratio}dB</Text></View>
                <View style={styles.mainResultItem}><Text style={styles.mainResultLabel}>F/S</Text><Text style={styles.mainResultValue}>{results.fs_ratio}dB</Text></View>
              </View>
              
              <View style={styles.secondaryResults}>
                <View style={styles.secondaryResultItem}><Text style={styles.secondaryLabel}>Beamwidth</Text><Text style={styles.secondaryValue}>H:{results.beamwidth_h}° V:{results.beamwidth_v}°</Text></View>
                <View style={styles.secondaryResultItem}><Text style={styles.secondaryLabel}>Efficiency</Text><Text style={styles.secondaryValue}>{results.antenna_efficiency}%</Text></View>
                <View style={styles.secondaryResultItem}><Text style={styles.secondaryLabel}>BW @1.5</Text><Text style={styles.secondaryValue}>{results.usable_bandwidth_1_5?.toFixed(2)} MHz</Text></View>
                <View style={styles.secondaryResultItem}><Text style={styles.secondaryLabel}>Mult</Text><Text style={styles.secondaryValue}>{results.multiplication_factor}x</Text></View>
              </View>
              
              <PolarPattern data={results.far_field_pattern} stackedData={results.stacked_pattern} isStacked={results.stacking_enabled} />
            </View>
          )}
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#121212' }, flex: { flex: 1 }, scrollView: { flex: 1 }, scrollContent: { padding: 10, paddingBottom: 40 },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', marginBottom: 10, paddingVertical: 6, gap: 8 }, headerTitle: { fontSize: 20, fontWeight: 'bold', color: '#fff' },
  section: { backgroundColor: '#1a1a1a', borderRadius: 10, padding: 10, marginBottom: 8 }, sectionTitle: { fontSize: 13, fontWeight: '600', color: '#fff', marginBottom: 6 }, sectionHeaderRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  rowSpaced: { flexDirection: 'row', alignItems: 'flex-end', gap: 6 },
  inputLabel: { fontSize: 10, color: '#aaa', marginBottom: 3 }, input: { backgroundColor: '#252525', borderRadius: 6, padding: 8, fontSize: 13, color: '#fff', borderWidth: 1, borderColor: '#333' },
  unitToggle: { flexDirection: 'row', backgroundColor: '#252525', borderRadius: 6, overflow: 'hidden', marginLeft: 4 }, unitBtn: { paddingVertical: 8, paddingHorizontal: 8 }, unitBtnActive: { backgroundColor: '#4CAF50' }, unitBtnText: { fontSize: 11, color: '#888' }, unitBtnTextActive: { color: '#fff', fontWeight: '600' },
  dropdownContainer: { marginBottom: 6, zIndex: 1000, position: 'relative' }, dropdownButton: { backgroundColor: '#252525', borderRadius: 6, padding: 8, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', borderWidth: 1, borderColor: '#333' }, dropdownButtonText: { fontSize: 12, color: '#fff' }, dropdownList: { backgroundColor: '#2a2a2a', borderRadius: 6, marginTop: 2, borderWidth: 1, borderColor: '#333', position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 9999, elevation: 10 }, dropdownItem: { padding: 8, borderBottomWidth: 1, borderBottomColor: '#333' }, dropdownItemSelected: { backgroundColor: '#333' }, dropdownItemText: { fontSize: 11, color: '#ccc' }, dropdownItemTextSelected: { color: '#4CAF50', fontWeight: '500' },
  elementCard: { backgroundColor: '#222', borderRadius: 6, padding: 6, marginTop: 4, borderLeftWidth: 3 }, elementTitle: { fontSize: 11, fontWeight: '600', marginBottom: 4 }, elementRow: { flexDirection: 'row', gap: 6 }, elementField: { flex: 1 }, elementLabel: { fontSize: 9, color: '#888', marginBottom: 2 }, elementInput: { backgroundColor: '#1a1a1a', borderRadius: 4, padding: 6, fontSize: 12, color: '#fff', borderWidth: 1, borderColor: '#333' },
  taperSection: { backgroundColor: '#222', borderRadius: 6, padding: 6, marginTop: 4 }, taperSectionTitle: { fontSize: 10, color: '#E91E63', fontWeight: '600', marginBottom: 4 },
  orientationToggle: { flexDirection: 'row', gap: 6, marginVertical: 6 }, orientBtn: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', backgroundColor: '#252525', borderRadius: 6, padding: 8, gap: 4 }, orientBtnActive: { backgroundColor: '#9C27B0' }, orientBtnText: { fontSize: 11, color: '#888' }, orientBtnTextActive: { color: '#fff', fontWeight: '600' },
  autoTuneBtn: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#FF9800', borderRadius: 6, paddingVertical: 6, paddingHorizontal: 10, gap: 4 }, autoTuneBtnText: { color: '#fff', fontSize: 11, fontWeight: '600' },
  resultsSection: { marginTop: 4 },
  bonusCard: { backgroundColor: '#1a1a1a', borderRadius: 6, padding: 6, marginBottom: 4 }, bonusText: { fontSize: 11, color: '#ccc' },
  swrContainer: { backgroundColor: '#1a1a1a', borderRadius: 8, padding: 8, marginBottom: 6, alignItems: 'center' }, swrTitle: { fontSize: 12, fontWeight: '600', color: '#fff', marginBottom: 4 }, swrLegend: { flexDirection: 'row', gap: 12, marginTop: 4 }, legendItem: { flexDirection: 'row', alignItems: 'center', gap: 4 }, legendColor: { width: 10, height: 10, borderRadius: 2 }, legendText: { fontSize: 9, color: '#888' },
  mainResults: { flexDirection: 'row', justifyContent: 'space-around', backgroundColor: '#1a1a1a', borderRadius: 8, padding: 10, marginBottom: 6 }, mainResultItem: { alignItems: 'center' }, mainResultLabel: { fontSize: 9, color: '#888', marginBottom: 2 }, mainResultValue: { fontSize: 16, fontWeight: 'bold', color: '#fff' },
  secondaryResults: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between', backgroundColor: '#1a1a1a', borderRadius: 8, padding: 8, marginBottom: 6 }, secondaryResultItem: { width: '48%', flexDirection: 'row', justifyContent: 'space-between', marginBottom: 4 }, secondaryLabel: { fontSize: 10, color: '#888' }, secondaryValue: { fontSize: 10, color: '#fff', fontWeight: '500' },
  polarContainer: { backgroundColor: '#1a1a1a', borderRadius: 8, padding: 8, alignItems: 'center' }, polarTitle: { fontSize: 12, fontWeight: '600', color: '#fff', marginBottom: 6 },
});
