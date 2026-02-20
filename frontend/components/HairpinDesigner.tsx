import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, Modal, ScrollView, ActivityIndicator, Pressable } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import Svg, { Line, Circle, Rect, Text as SvgText, G } from 'react-native-svg';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL || '';

interface HairpinDesignerProps {
  visible: boolean;
  onClose: () => void;
  numElements: number;
  drivenLength: number;
  frequencyMhz: number;
  calculatedFeedpointR?: number;
  calculatedResonantFreq?: number;
  reflectorSpacingIn?: number;
  directorSpacingsIn?: number[];
  elementDiameter?: number;
  onApply?: (hairpinLength: number, rodDia: number, rodSpacing: number, recommendedDrivenLength?: number) => void;
}

interface Recipe {
  rod_dia: number; rod_spacing: number; z0: number;
  ideal_hairpin_length_in: number;
  xl_needed: number; xc_needed: number; q_match: number;
  swr_at_best: number; feedpoint_r: number;
  shorten_per_side_in: number; shortened_total_length_in: number;
  original_driven_length_in: number;
  recommended_driven_length_in: number | null;
  driven_length_corrected: boolean;
}

interface DesignerResult {
  recipe: Recipe;
  feedpoint_impedance: number;
  hardware_source: string;
  auto_hardware: { rod_dia: number; rod_spacing: number; z0: number };
  length_sweep: { length_in: number; swr: number; xl_actual: number; z_in_r: number; z_in_x: number; gamma: number; p_reflected_w: number }[];
  notes: string[];
  error: string | null;
  topology_note?: string;
}

export const HairpinDesigner: React.FC<HairpinDesignerProps> = ({
  visible, onClose, numElements, drivenLength, frequencyMhz,
  calculatedFeedpointR, calculatedResonantFreq,
  reflectorSpacingIn, directorSpacingsIn, elementDiameter,
  onApply,
}) => {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<DesignerResult | null>(null);
  const [showCustom, setShowCustom] = useState(false);
  const [customRodDia, setCustomRodDia] = useState('');
  const [customRodSpacing, setCustomRodSpacing] = useState('');

  const runDesign = async () => {
    setLoading(true);
    setResult(null);
    const body: any = {
      num_elements: numElements,
      frequency_mhz: frequencyMhz,
      driven_element_length_in: drivenLength,
      reflector_spacing_in: reflectorSpacingIn,
      director_spacings_in: directorSpacingsIn,
      element_diameter: elementDiameter || 0.5,
    };
    if (calculatedFeedpointR && calculatedFeedpointR > 0) body.feedpoint_impedance = calculatedFeedpointR;
    if (calculatedResonantFreq && calculatedResonantFreq > 0) body.element_resonant_freq_mhz = calculatedResonantFreq;
    if (showCustom) {
      if (customRodDia) body.custom_rod_dia = parseFloat(customRodDia);
      if (customRodSpacing) body.custom_rod_spacing = parseFloat(customRodSpacing);
    }
    const res = await fetch(`${BACKEND_URL}/api/hairpin-designer`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    const data = await res.json();
    setResult(data);
    setLoading(false);
  };

  const recipe = result?.recipe;

  const renderSwrChart = (data: { swr: number }[], xKey: string, xLabel: string) => {
    if (!data || data.length === 0) return null;
    const W = 400, H = 120, PAD = 30;
    const xs = data.map(d => (d as any)[xKey]);
    const ys = data.map(d => d.swr);
    const xMin = Math.min(...xs), xMax = Math.max(...xs);
    const yMin = Math.min(1.0, ...ys), yMax = Math.max(2.5, Math.min(10, ...ys));
    const scaleX = (v: number) => PAD + ((v - xMin) / (xMax - xMin || 1)) * (W - 2 * PAD);
    const scaleY = (v: number) => PAD + ((yMax - Math.min(v, yMax)) / (yMax - yMin || 1)) * (H - 2 * PAD);
    const bestIdx = ys.indexOf(Math.min(...ys));

    return (
      <Svg width={W} height={H + 15}>
        <Line x1={PAD} y1={PAD} x2={PAD} y2={H - PAD} stroke="#444" strokeWidth={1} />
        <Line x1={PAD} y1={H - PAD} x2={W - PAD} y2={H - PAD} stroke="#444" strokeWidth={1} />
        <Line x1={PAD} y1={scaleY(1.5)} x2={W - PAD} y2={scaleY(1.5)} stroke="#333" strokeWidth={0.5} strokeDasharray="4,4" />
        {data.map((d, i) => i > 0 ? (
          <Line key={i} x1={scaleX(xs[i - 1])} y1={scaleY(ys[i - 1])} x2={scaleX(xs[i])} y2={scaleY(ys[i])} stroke="#2196F3" strokeWidth={1.5} />
        ) : null)}
        {bestIdx >= 0 && <Circle cx={scaleX(xs[bestIdx])} cy={scaleY(ys[bestIdx])} r={4} fill="#4CAF50" />}
        <SvgText x={W / 2} y={H + 10} fill="#888" fontSize={9} textAnchor="middle">{xLabel}</SvgText>
        <SvgText x={PAD - 4} y={PAD + 3} fill="#888" fontSize={8} textAnchor="end">{yMax.toFixed(1)}</SvgText>
        <SvgText x={PAD - 4} y={H - PAD + 3} fill="#888" fontSize={8} textAnchor="end">{yMin.toFixed(1)}</SvgText>
      </Svg>
    );
  };

  return (
    <Modal visible={visible} animationType="slide" transparent={false}>
      <View style={{ flex: 1, backgroundColor: '#0a0a1a' }}>
        <View style={{ flexDirection: 'row', alignItems: 'center', padding: 12, borderBottomWidth: 2, borderBottomColor: '#2196F3' }}>
          <Pressable onPress={onClose} data-testid="hairpin-designer-close" style={{ marginRight: 12, padding: 4 }}>
            <Ionicons name="close" size={22} color="#888" />
          </Pressable>
          <Ionicons name="hardware-chip-outline" size={18} color="#2196F3" />
          <Text style={{ fontSize: 16, color: '#2196F3', fontWeight: '700', marginLeft: 8 }}>Hairpin Match Designer</Text>
        </View>

        <ScrollView style={{ flex: 1, padding: 12 }}>
          <View style={{ backgroundColor: '#151530', borderRadius: 8, padding: 10, marginBottom: 10, borderWidth: 1, borderColor: '#333' }}>
            <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
              <View><Text style={{ fontSize: 9, color: '#888' }}>DESIGNING FOR</Text><Text style={{ fontSize: 10, color: '#888' }}>Elements</Text><Text style={{ fontSize: 18, color: '#fff', fontWeight: '700' }}>{numElements}</Text></View>
              <View style={{ alignItems: 'center' }}><Text style={{ fontSize: 9, color: '#888' }}>Driven Length</Text><Text style={{ fontSize: 18, color: '#fff', fontWeight: '700' }}>{drivenLength}"</Text></View>
              <View style={{ alignItems: 'flex-end' }}><Text style={{ fontSize: 9, color: '#888' }}>Frequency</Text><Text style={{ fontSize: 18, color: '#fff', fontWeight: '700' }}>{frequencyMhz} MHz</Text></View>
            </View>
          </View>

          <Pressable onPress={() => setShowCustom(!showCustom)} style={{ marginBottom: 8 }}>
            <Text style={{ fontSize: 11, color: '#888' }}>{showCustom ? '▼' : '▶'} Custom Hardware / Known Feedpoint R</Text>
          </Pressable>
          {showCustom && (
            <View style={{ flexDirection: 'row', gap: 8, marginBottom: 8 }}>
              <View style={{ flex: 1 }}>
                <Text style={{ fontSize: 9, color: '#888', marginBottom: 2 }}>Rod Dia (in)</Text>
                <TextInput style={{ backgroundColor: '#252525', color: '#fff', borderRadius: 6, padding: 8, fontSize: 13, borderWidth: 1, borderColor: '#333' }} value={customRodDia} onChangeText={setCustomRodDia} keyboardType="decimal-pad" placeholder="Auto" placeholderTextColor="#555" />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={{ fontSize: 9, color: '#888', marginBottom: 2 }}>Rod Spacing (in)</Text>
                <TextInput style={{ backgroundColor: '#252525', color: '#fff', borderRadius: 6, padding: 8, fontSize: 13, borderWidth: 1, borderColor: '#333' }} value={customRodSpacing} onChangeText={setCustomRodSpacing} keyboardType="decimal-pad" placeholder="Auto" placeholderTextColor="#555" />
              </View>
            </View>
          )}

          <TouchableOpacity onPress={runDesign} disabled={loading} style={{ backgroundColor: '#FF9800', borderRadius: 8, padding: 14, alignItems: 'center', marginBottom: 14 }} data-testid="hairpin-auto-design-btn">
            {loading ? <ActivityIndicator color="#fff" /> : <Text style={{ fontSize: 14, color: '#000', fontWeight: '700' }}><Ionicons name="flash" size={14} /> Auto Design</Text>}
          </TouchableOpacity>

          {result?.topology_note && (
            <View style={{ backgroundColor: '#2a1a00', borderRadius: 8, padding: 12, marginBottom: 10, borderWidth: 1, borderColor: '#FF9800' }}>
              <Text style={{ fontSize: 13, color: '#FF9800', fontWeight: '700' }}>{result.topology_note}</Text>
              <Text style={{ fontSize: 11, color: '#888', marginTop: 4 }}>Feedpoint R: {result.feedpoint_impedance} ohms</Text>
            </View>
          )}

          {recipe && (
            <>
              <View style={{ backgroundColor: '#151530', borderRadius: 8, padding: 10, marginBottom: 10, borderWidth: 1, borderColor: recipe.swr_at_best <= 1.1 ? '#4CAF50' : recipe.swr_at_best <= 1.5 ? '#FF9800' : '#f44336' }}>
                <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <Text style={{ fontSize: 12, color: recipe.swr_at_best <= 1.1 ? '#4CAF50' : '#FF9800', fontWeight: '700' }}>
                    {recipe.swr_at_best <= 1.1 ? 'EXCELLENT MATCH' : recipe.swr_at_best <= 1.5 ? 'GOOD MATCH' : 'FAIR MATCH'}
                  </Text>
                  <Text style={{ fontSize: 10, color: '#888' }}>HW: {result.hardware_source === 'auto' ? 'Auto-Selected' : 'Custom Hardware'}</Text>
                </View>
                <View style={{ flexDirection: 'row', justifyContent: 'space-around', backgroundColor: '#0d1117', borderRadius: 6, padding: 8 }}>
                  <View style={{ alignItems: 'center' }}><Text style={{ fontSize: 9, color: '#888' }}>SWR</Text><Text style={{ fontSize: 20, color: recipe.swr_at_best <= 1.1 ? '#4CAF50' : '#FF9800', fontWeight: '700' }}>{recipe.swr_at_best}</Text></View>
                  <View style={{ alignItems: 'center' }}><Text style={{ fontSize: 9, color: '#888' }}>Q Match</Text><Text style={{ fontSize: 20, color: '#FF9800', fontWeight: '700' }}>{recipe.q_match}</Text></View>
                  <View style={{ alignItems: 'center' }}><Text style={{ fontSize: 9, color: '#888' }}>Feedpoint R</Text><Text style={{ fontSize: 20, color: '#2196F3', fontWeight: '700' }}>{recipe.feedpoint_r}</Text></View>
                </View>
              </View>

              <View style={{ height: 1, backgroundColor: '#333', marginBottom: 8 }} />
              <Text style={{ fontSize: 10, color: '#2196F3', fontWeight: '700', marginBottom: 6 }}>HARDWARE</Text>
              <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 4, marginBottom: 8 }}>
                <HpItem label="Rod Dia" value={`${recipe.rod_dia}"`} />
                <HpItem label="Rod Spacing" value={`${recipe.rod_spacing}"`} />
                <HpItem label="Hairpin Z0" value={`${recipe.z0} ohms`} />
              </View>

              <View style={{ height: 1, backgroundColor: '#333', marginBottom: 8 }} />
              <Text style={{ fontSize: 10, color: '#FF9800', fontWeight: '700', marginBottom: 6 }}>L-NETWORK DESIGN</Text>
              <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 4, marginBottom: 8 }}>
                <HpItem label="X_L (hairpin)" value={`${recipe.xl_needed} ohms`} accent />
                <HpItem label="X_C (element)" value={`${recipe.xc_needed} ohms`} />
                <HpItem label="Hairpin Length" value={`${recipe.ideal_hairpin_length_in}"`} accent />
              </View>

              {recipe.driven_length_corrected && recipe.recommended_driven_length_in && (
                <>
                  <View style={{ height: 1, backgroundColor: '#333', marginBottom: 8 }} />
                  <Text style={{ fontSize: 10, color: '#4CAF50', fontWeight: '700', marginBottom: 6 }}>DRIVEN ELEMENT CORRECTION</Text>
                  <View style={{ backgroundColor: '#0a2a0a', borderRadius: 6, padding: 8, marginBottom: 8, borderWidth: 1, borderColor: '#4CAF50' }}>
                    <Text style={{ fontSize: 11, color: '#4CAF50', fontWeight: '700', marginBottom: 4 }}>
                      Make driven element {recipe.recommended_driven_length_in > recipe.original_driven_length_in ? 'LONGER' : 'SHORTER'}
                    </Text>
                    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                      <View><Text style={{ fontSize: 9, color: '#888' }}>Current</Text><Text style={{ fontSize: 14, color: '#888', fontWeight: '600' }}>{recipe.original_driven_length_in}"</Text></View>
                      <Ionicons name="arrow-forward" size={16} color="#4CAF50" />
                      <View><Text style={{ fontSize: 9, color: '#4CAF50' }}>Recommended</Text><Text style={{ fontSize: 14, color: '#4CAF50', fontWeight: '700' }}>{recipe.recommended_driven_length_in}"</Text></View>
                      <View style={{ marginLeft: 'auto' }}>
                        <Text style={{ fontSize: 9, color: '#888' }}>Change</Text>
                        <Text style={{ fontSize: 14, color: '#FF9800', fontWeight: '600' }}>
                          {recipe.recommended_driven_length_in > recipe.original_driven_length_in ? '+' : ''}{(recipe.recommended_driven_length_in - recipe.original_driven_length_in).toFixed(2)}"
                        </Text>
                      </View>
                    </View>
                  </View>
                </>
              )}

              <View style={{ height: 1, backgroundColor: '#333', marginBottom: 8 }} />
              <View style={{ backgroundColor: '#1a2332', borderRadius: 6, padding: 8, marginBottom: 8, borderWidth: 1, borderColor: '#FF9800' }}>
                <Text style={{ fontSize: 11, color: '#FF9800', fontWeight: '700', marginBottom: 4 }}>DRIVEN ELEMENT SHORTENING</Text>
                <Text style={{ fontSize: 11, color: '#ccc' }}>
                  Shorten each half by <Text style={{ color: '#FF9800', fontWeight: '700' }}>{recipe.shorten_per_side_in}"</Text> to provide {recipe.xc_needed} ohms capacitive reactance
                </Text>
                <Text style={{ fontSize: 13, color: '#4CAF50', fontWeight: '700', marginTop: 4 }}>
                  New driven element total: {recipe.shortened_total_length_in}"
                </Text>
              </View>

              {/* SWR Sweep Chart */}
              <View style={{ backgroundColor: '#151530', borderRadius: 8, padding: 10, marginBottom: 10, borderWidth: 1, borderColor: '#333' }}>
                <Text style={{ fontSize: 10, color: '#2196F3', fontWeight: '700', marginBottom: 6 }}>
                  SWR vs HAIRPIN LENGTH (Best: {recipe.ideal_hairpin_length_in}" = {recipe.swr_at_best} SWR)
                </Text>
                <View style={{ alignItems: 'center' }}>
                  {renderSwrChart(result.length_sweep, 'length_in', 'Hairpin Length (inches)')}
                </View>
              </View>

              {/* Power Analysis */}
              {result.length_sweep.length > 0 && (() => {
                const bestPt = result.length_sweep.reduce((a, b) => a.swr < b.swr ? a : b);
                return (
                  <View style={{ backgroundColor: '#151530', borderRadius: 8, padding: 10, marginBottom: 10, borderWidth: 1, borderColor: '#333' }}>
                    <Text style={{ fontSize: 10, color: '#4CAF50', fontWeight: '700', marginBottom: 6 }}>POWER ANALYSIS (5W Reference)</Text>
                    <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 4 }}>
                      <HpItem label="Forward" value="5.00 W" />
                      <HpItem label="Reflected" value={`${bestPt.p_reflected_w.toFixed(3)} W`} />
                      <HpItem label="Net to Antenna" value={`${(5.0 - bestPt.p_reflected_w).toFixed(2)} W`} accent />
                      <HpItem label="Gamma" value={bestPt.gamma.toFixed(4)} />
                      <HpItem label="Z_in" value={`${bestPt.z_in_r.toFixed(1)}${bestPt.z_in_x >= 0 ? '+' : ''}${bestPt.z_in_x.toFixed(1)}j`} />
                    </View>
                  </View>
                );
              })()}

              {result.notes.length > 0 && (
                <View style={{ backgroundColor: '#151530', borderRadius: 8, padding: 10, marginBottom: 10, borderWidth: 1, borderColor: '#333' }}>
                  <Text style={{ fontSize: 10, color: '#888', fontWeight: '700', marginBottom: 4 }}>NOTES</Text>
                  {result.notes.map((note, i) => (
                    <Text key={i} style={{ fontSize: 10, color: note.includes('Shorten') ? '#FF9800' : note.includes('LONGER') || note.includes('SHORTER') ? '#4CAF50' : '#aaa', marginBottom: 2 }}>{note}</Text>
                  ))}
                </View>
              )}

              {recipe.swr_at_best <= 2.0 && onApply && (
                <TouchableOpacity
                  onPress={() => { onApply(recipe.ideal_hairpin_length_in, recipe.rod_dia, recipe.rod_spacing, recipe.driven_length_corrected ? recipe.recommended_driven_length_in ?? undefined : undefined); onClose(); }}
                  style={{ backgroundColor: '#4CAF50', borderRadius: 8, padding: 14, alignItems: 'center', marginBottom: 20 }}
                  data-testid="hairpin-apply-recipe-btn"
                >
                  <Text style={{ fontSize: 14, color: '#fff', fontWeight: '700' }}>Apply Recipe to Calculator</Text>
                  <Text style={{ fontSize: 10, color: '#c8e6c9', marginTop: 2 }}>
                    Set hairpin to {recipe.ideal_hairpin_length_in}", rod {recipe.rod_dia}" dia @ {recipe.rod_spacing}" spacing
                  </Text>
                </TouchableOpacity>
              )}
            </>
          )}

          <View style={{ height: 40 }} />
        </ScrollView>
      </View>
    </Modal>
  );
};

function HpItem({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <View style={{ backgroundColor: '#0a0a1a', borderRadius: 4, paddingHorizontal: 8, paddingVertical: 4, minWidth: 80 }}>
      <Text style={{ fontSize: 8, color: '#666' }}>{label}</Text>
      <Text style={{ fontSize: 12, color: accent ? '#2196F3' : '#fff', fontWeight: '600' }}>{value}</Text>
    </View>
  );
}
