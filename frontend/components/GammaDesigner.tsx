import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, Modal, ScrollView, ActivityIndicator, Pressable } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import Svg, { Line, Circle, Rect, Text as SvgText, G } from 'react-native-svg';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL || '';

interface GammaDesignerProps {
  visible: boolean;
  onClose: () => void;
  numElements: number;
  drivenLength: number;
  frequencyMhz: number;
  calculatedFeedpointR?: number;
  currentRodDia?: number;
  currentRodSpacing?: number;
  onApply?: (barPos: number, insertion: number) => void;
}

interface Recipe {
  rod_od: number; tube_od: number; tube_id: number; rod_spacing: number;
  teflon_length: number; tube_length: number; gamma_rod_length: number;
  ideal_bar_position: number; optimal_insertion: number;
  swr_at_null: number; return_loss_at_null: number; capacitance_at_null: number;
  z_matched_r: number; z_matched_x: number;
  k_step_up: number; k_squared: number; coupling_multiplier: number;
  cap_per_inch: number; id_rod_ratio: number; null_reachable: boolean;
}

interface DesignerResult {
  recipe: Recipe;
  feedpoint_impedance: number;
  hardware_source: string;
  auto_hardware: { rod_od: number; tube_od: number; spacing: number };
  bar_sweep: { bar_inches: number; k: number; r_matched: number; x_net: number; swr: number }[];
  insertion_sweep: { insertion_inches: number; cap_pf: number; x_net: number; swr: number }[];
  notes: string[];
  error?: string;
}

export function GammaDesigner({ visible, onClose, numElements, drivenLength, frequencyMhz, calculatedFeedpointR, currentRodDia, currentRodSpacing, onApply }: GammaDesignerProps) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<DesignerResult | null>(null);
  const [showCustom, setShowCustom] = useState(false);
  const [customTubeOd, setCustomTubeOd] = useState('');
  const [customRodOd, setCustomRodOd] = useState('');
  const [customSpacing, setCustomSpacing] = useState('');
  const [customTeflon, setCustomTeflon] = useState('');
  const [customFeedpointR, setCustomFeedpointR] = useState('');

  const runDesigner = async (useCustom: boolean) => {
    setLoading(true);
    setResult(null);
    try {
      const body: any = {
        num_elements: numElements,
        driven_element_length_in: drivenLength,
        frequency_mhz: frequencyMhz,
      };
      if (useCustom) {
        if (customTubeOd) body.custom_tube_od = parseFloat(customTubeOd);
        if (customRodOd) body.custom_rod_od = parseFloat(customRodOd);
        if (customSpacing) body.custom_rod_spacing = parseFloat(customSpacing);
        if (customTeflon) body.custom_teflon_length = parseFloat(customTeflon);
        if (customFeedpointR) body.feedpoint_impedance = parseFloat(customFeedpointR);
      }
      const res = await fetch(`${BACKEND_URL}/api/gamma-designer`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
      });
      const data = await res.json();
      setResult(data);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  const chartWidth = 280;
  const chartHeight = 100;
  const pad = { l: 28, r: 8, t: 8, b: 20 };

  const renderSwrChart = (data: { swr: number }[], xKey: string, xLabel: string) => {
    if (!data || data.length === 0) return null;
    const xVals = data.map((d: any) => d[xKey]);
    const yVals = data.map(d => Math.min(d.swr, 10));
    const xMin = Math.min(...xVals); const xMax = Math.max(...xVals);
    const yMin = 1; const yMax = Math.max(5, Math.min(10, Math.max(...yVals) * 1.1));
    const w = chartWidth - pad.l - pad.r;
    const h = chartHeight - pad.t - pad.b;
    const toX = (v: number) => pad.l + ((v - xMin) / (xMax - xMin || 1)) * w;
    const toY = (v: number) => pad.t + h - ((Math.min(v, yMax) - yMin) / (yMax - yMin)) * h;

    const points = data.map((d: any) => `${toX(d[xKey]).toFixed(1)},${toY(Math.min(d.swr, yMax)).toFixed(1)}`).join(' ');
    const bestIdx = yVals.indexOf(Math.min(...yVals));

    return (
      <Svg width={chartWidth} height={chartHeight}>
        <Rect x={pad.l} y={pad.t} width={w} height={h} fill="#1a1a2e" rx={4} />
        {/* Grid lines at SWR 1, 2, 3, 5 */}
        {[1, 2, 3, 5].filter(v => v <= yMax).map(v => (
          <G key={v}>
            <Line x1={pad.l} y1={toY(v)} x2={pad.l + w} y2={toY(v)} stroke="#333" strokeWidth={0.5} />
            <SvgText x={pad.l - 3} y={toY(v) + 3} fill="#666" fontSize={8} textAnchor="end">{v}</SvgText>
          </G>
        ))}
        {/* SWR line */}
        <Line x1={pad.l} y1={toY(1)} x2={pad.l + w} y2={toY(1)} stroke="#4CAF50" strokeWidth={0.5} strokeDasharray="3,3" />
        {data.length > 1 && <Svg><Rect x={0} y={0} width={0} height={0} />{
          data.slice(0, -1).map((d: any, i: number) => {
            const next: any = data[i + 1];
            return <Line key={i} x1={toX(d[xKey])} y1={toY(Math.min(d.swr, yMax))} x2={toX(next[xKey])} y2={toY(Math.min(next.swr, yMax))} stroke="#FF9800" strokeWidth={1.5} />;
          })
        }</Svg>}
        {/* Best point */}
        {bestIdx >= 0 && <Circle cx={toX(xVals[bestIdx])} cy={toY(yVals[bestIdx])} r={3} fill="#4CAF50" />}
        <SvgText x={pad.l + w / 2} y={chartHeight - 2} fill="#888" fontSize={8} textAnchor="middle">{xLabel}</SvgText>
      </Svg>
    );
  };

  const recipe = result?.recipe;

  return (
    <Modal visible={visible} animationType="slide" presentationStyle="fullScreen" onRequestClose={onClose}>
      <View style={{ flex: 1, backgroundColor: '#0a0a1a' }}>
        {/* Header */}
        <View style={{ flexDirection: 'row', alignItems: 'center', padding: 12, paddingTop: 48, backgroundColor: '#111', borderBottomWidth: 1, borderBottomColor: '#FF9800' }}>
          <Pressable onPress={onClose} style={{ padding: 4, marginRight: 10 }} data-testid="gamma-designer-close">
            <Ionicons name="close" size={24} color="#FF9800" />
          </Pressable>
          <Ionicons name="construct" size={18} color="#FF9800" />
          <Text style={{ fontSize: 16, color: '#FF9800', fontWeight: '700', marginLeft: 6 }}>Gamma Match Designer</Text>
        </View>

        <ScrollView style={{ flex: 1, padding: 12 }} showsVerticalScrollIndicator={false}>
          {/* Antenna Info */}
          <View style={{ backgroundColor: '#151530', borderRadius: 8, padding: 10, marginBottom: 10, borderWidth: 1, borderColor: '#333' }}>
            <Text style={{ fontSize: 10, color: '#888', marginBottom: 6 }}>DESIGNING FOR</Text>
            <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
              <View>
                <Text style={{ fontSize: 10, color: '#666' }}>Elements</Text>
                <Text style={{ fontSize: 18, color: '#fff', fontWeight: '700' }}>{numElements}</Text>
              </View>
              <View style={{ alignItems: 'center' }}>
                <Text style={{ fontSize: 10, color: '#666' }}>Driven Length</Text>
                <Text style={{ fontSize: 18, color: '#fff', fontWeight: '700' }}>{drivenLength}"</Text>
              </View>
              <View style={{ alignItems: 'flex-end' }}>
                <Text style={{ fontSize: 10, color: '#666' }}>Frequency</Text>
                <Text style={{ fontSize: 18, color: '#fff', fontWeight: '700' }}>{frequencyMhz} MHz</Text>
              </View>
            </View>
          </View>

          {/* Custom Hardware Toggle */}
          <Pressable onPress={() => setShowCustom(!showCustom)} style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 8 }} data-testid="toggle-custom-hardware">
            <Ionicons name={showCustom ? 'chevron-down' : 'chevron-forward'} size={14} color="#888" />
            <Text style={{ fontSize: 11, color: '#888', marginLeft: 4 }}>Custom Hardware / Known Feedpoint R</Text>
          </Pressable>

          {showCustom && (
            <View style={{ backgroundColor: '#151530', borderRadius: 8, padding: 10, marginBottom: 10, borderWidth: 1, borderColor: '#444' }}>
              <View style={{ flexDirection: 'row', gap: 8, marginBottom: 8 }}>
                <View style={{ flex: 1 }}>
                  <Text style={{ fontSize: 9, color: '#888', marginBottom: 2 }}>Tube OD (in)</Text>
                  <TextInput style={inputStyle} value={customTubeOd} onChangeText={setCustomTubeOd} placeholder="auto" placeholderTextColor="#555" keyboardType="decimal-pad" data-testid="custom-tube-od-input" />
                </View>
                <View style={{ flex: 1 }}>
                  <Text style={{ fontSize: 9, color: '#888', marginBottom: 2 }}>Rod OD (in)</Text>
                  <TextInput style={inputStyle} value={customRodOd} onChangeText={setCustomRodOd} placeholder="auto" placeholderTextColor="#555" keyboardType="decimal-pad" data-testid="custom-rod-od-input" />
                </View>
                <View style={{ flex: 1 }}>
                  <Text style={{ fontSize: 9, color: '#888', marginBottom: 2 }}>Spacing (in)</Text>
                  <TextInput style={inputStyle} value={customSpacing} onChangeText={setCustomSpacing} placeholder="auto" placeholderTextColor="#555" keyboardType="decimal-pad" data-testid="custom-spacing-input" />
                </View>
              </View>
              <View style={{ flexDirection: 'row', gap: 8 }}>
                <View style={{ flex: 1 }}>
                  <Text style={{ fontSize: 9, color: '#888', marginBottom: 2 }}>Teflon Length (in)</Text>
                  <TextInput style={inputStyle} value={customTeflon} onChangeText={setCustomTeflon} placeholder="16" placeholderTextColor="#555" keyboardType="decimal-pad" data-testid="custom-teflon-input" />
                </View>
                <View style={{ flex: 1 }}>
                  <Text style={{ fontSize: 9, color: '#888', marginBottom: 2 }}>Feedpoint R (ohms)</Text>
                  <TextInput style={inputStyle} value={customFeedpointR} onChangeText={setCustomFeedpointR} placeholder="estimated" placeholderTextColor="#555" keyboardType="decimal-pad" data-testid="custom-feedpoint-input" />
                </View>
                <View style={{ flex: 1 }} />
              </View>
            </View>
          )}

          {/* Design Buttons */}
          <View style={{ flexDirection: 'row', gap: 8, marginBottom: 12 }}>
            <TouchableOpacity
              onPress={() => runDesigner(false)}
              disabled={loading}
              style={{ flex: 1, backgroundColor: '#FF9800', borderRadius: 8, padding: 12, alignItems: 'center', flexDirection: 'row', justifyContent: 'center', opacity: loading ? 0.6 : 1 }}
              data-testid="design-auto-btn"
            >
              {loading ? <ActivityIndicator size="small" color="#000" /> : <>
                <Ionicons name="flash" size={16} color="#000" />
                <Text style={{ fontSize: 13, color: '#000', fontWeight: '700', marginLeft: 4 }}>Auto Design</Text>
              </>}
            </TouchableOpacity>
            {showCustom && (
              <TouchableOpacity
                onPress={() => runDesigner(true)}
                disabled={loading}
                style={{ flex: 1, backgroundColor: '#333', borderRadius: 8, padding: 12, alignItems: 'center', flexDirection: 'row', justifyContent: 'center', borderWidth: 1, borderColor: '#FF9800', opacity: loading ? 0.6 : 1 }}
                data-testid="design-custom-btn"
              >
                {loading ? <ActivityIndicator size="small" color="#FF9800" /> : <>
                  <Ionicons name="build" size={16} color="#FF9800" />
                  <Text style={{ fontSize: 13, color: '#FF9800', fontWeight: '700', marginLeft: 4 }}>Custom HW</Text>
                </>}
              </TouchableOpacity>
            )}
          </View>

          {/* Error */}
          {result?.error && (
            <View style={{ backgroundColor: '#3a1111', borderRadius: 8, padding: 10, marginBottom: 10, borderWidth: 1, borderColor: '#f44336' }}>
              <Text style={{ fontSize: 12, color: '#f44336', fontWeight: '700' }}>{result.error}</Text>
            </View>
          )}

          {/* Results */}
          {recipe && !result?.error && (
            <>
              {/* Recipe Card */}
              <View style={{ backgroundColor: '#151530', borderRadius: 8, padding: 12, marginBottom: 10, borderWidth: 1, borderColor: recipe.null_reachable ? '#4CAF50' : '#f44336' }}>
                <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <Text style={{ fontSize: 13, color: recipe.null_reachable ? '#4CAF50' : '#f44336', fontWeight: '700' }}>
                    {recipe.null_reachable ? 'MATCH ACHIEVABLE' : 'NULL NOT REACHABLE'}
                  </Text>
                  <Text style={{ fontSize: 10, color: '#888' }}>{result.hardware_source === 'auto' ? 'Auto Hardware' : 'Custom Hardware'}</Text>
                </View>

                {/* Main metrics */}
                <View style={{ flexDirection: 'row', justifyContent: 'space-around', marginBottom: 10, paddingVertical: 8, backgroundColor: '#0a0a1a', borderRadius: 6 }}>
                  <View style={{ alignItems: 'center' }}>
                    <Text style={{ fontSize: 9, color: '#888' }}>SWR</Text>
                    <Text style={{ fontSize: 22, color: recipe.swr_at_null <= 1.5 ? '#4CAF50' : '#FF9800', fontWeight: '700' }}>{recipe.swr_at_null.toFixed(2)}</Text>
                  </View>
                  <View style={{ alignItems: 'center' }}>
                    <Text style={{ fontSize: 9, color: '#888' }}>Return Loss</Text>
                    <Text style={{ fontSize: 22, color: '#2196F3', fontWeight: '700' }}>{recipe.return_loss_at_null} dB</Text>
                  </View>
                  <View style={{ alignItems: 'center' }}>
                    <Text style={{ fontSize: 9, color: '#888' }}>Z Matched</Text>
                    <Text style={{ fontSize: 14, color: '#fff', fontWeight: '700' }}>{recipe.z_matched_r.toFixed(1)}{recipe.z_matched_x >= 0 ? '+' : ''}{recipe.z_matched_x.toFixed(1)}j</Text>
                  </View>
                </View>

                <View style={{ height: 1, backgroundColor: '#333', marginBottom: 8 }} />

                {/* Hardware Recipe */}
                <Text style={{ fontSize: 10, color: '#FF9800', fontWeight: '700', marginBottom: 6 }}>HARDWARE</Text>
                <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 4 }}>
                  <RecipeItem label="Rod OD" value={`${recipe.rod_od}"` } />
                  <RecipeItem label="Tube OD" value={`${recipe.tube_od}"`} />
                  <RecipeItem label="Tube ID" value={`${recipe.tube_id}"`} />
                  <RecipeItem label="Spacing" value={`${recipe.rod_spacing}"`} />
                  <RecipeItem label="Rod Length" value={`${recipe.gamma_rod_length}"`} />
                  <RecipeItem label="Tube Length" value={`${recipe.tube_length}"`} />
                  <RecipeItem label="Teflon" value={`${recipe.teflon_length}"`} />
                  <RecipeItem label="Cap/inch" value={`${recipe.cap_per_inch} pF`} />
                  <RecipeItem label="ID/Rod" value={`${recipe.id_rod_ratio}:1`} />
                </View>

                <View style={{ height: 1, backgroundColor: '#333', marginVertical: 8 }} />

                {/* Tuning Recipe */}
                <Text style={{ fontSize: 10, color: '#2196F3', fontWeight: '700', marginBottom: 6 }}>TUNING SETTINGS</Text>
                <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 4 }}>
                  <RecipeItem label="Bar Position" value={`${recipe.ideal_bar_position}"`} accent />
                  <RecipeItem label="Rod Insertion" value={`${recipe.optimal_insertion}"`} accent />
                  <RecipeItem label="Capacitance" value={`${recipe.capacitance_at_null} pF`} />
                  <RecipeItem label="K Step-Up" value={recipe.k_step_up.toFixed(3)} />
                  <RecipeItem label="K Squared" value={recipe.k_squared.toFixed(3)} />
                  <RecipeItem label="Coupling" value={recipe.coupling_multiplier.toFixed(3)} />
                  <RecipeItem label="Feedpoint R" value={`${result.feedpoint_impedance} ohms`} />
                </View>
              </View>

              {/* Sweep Charts */}
              <View style={{ backgroundColor: '#151530', borderRadius: 8, padding: 10, marginBottom: 10, borderWidth: 1, borderColor: '#333' }}>
                <Text style={{ fontSize: 10, color: '#FF9800', fontWeight: '700', marginBottom: 6 }}>BAR POSITION vs SWR (at {recipe.optimal_insertion}" insertion)</Text>
                <View style={{ alignItems: 'center' }}>
                  {renderSwrChart(result.bar_sweep, 'bar_inches', 'Bar Position (inches)')}
                </View>
              </View>

              <View style={{ backgroundColor: '#151530', borderRadius: 8, padding: 10, marginBottom: 10, borderWidth: 1, borderColor: '#333' }}>
                <Text style={{ fontSize: 10, color: '#2196F3', fontWeight: '700', marginBottom: 6 }}>ROD INSERTION vs SWR (at {recipe.ideal_bar_position}" bar)</Text>
                <View style={{ alignItems: 'center' }}>
                  {renderSwrChart(result.insertion_sweep, 'insertion_inches', 'Insertion (inches)')}
                </View>
              </View>

              {/* Notes */}
              {result.notes.length > 0 && (
                <View style={{ backgroundColor: '#151530', borderRadius: 8, padding: 10, marginBottom: 10, borderWidth: 1, borderColor: '#333' }}>
                  <Text style={{ fontSize: 10, color: '#888', fontWeight: '700', marginBottom: 4 }}>NOTES</Text>
                  {result.notes.map((note, i) => (
                    <Text key={i} style={{ fontSize: 10, color: note.includes('WARNING') || note.includes('NOT REACHABLE') ? '#f44336' : '#aaa', marginBottom: 2 }}>{note}</Text>
                  ))}
                </View>
              )}

              {/* Apply button */}
              {recipe.null_reachable && onApply && (
                <TouchableOpacity
                  onPress={() => { onApply(recipe.ideal_bar_position, recipe.optimal_insertion); onClose(); }}
                  style={{ backgroundColor: '#4CAF50', borderRadius: 8, padding: 14, alignItems: 'center', marginBottom: 20 }}
                  data-testid="apply-recipe-btn"
                >
                  <Text style={{ fontSize: 14, color: '#fff', fontWeight: '700' }}>Apply Recipe to Calculator</Text>
                  <Text style={{ fontSize: 10, color: '#c8e6c9', marginTop: 2 }}>Set bar to {recipe.ideal_bar_position}" and insertion to {recipe.optimal_insertion}"</Text>
                </TouchableOpacity>
              )}
            </>
          )}

          <View style={{ height: 40 }} />
        </ScrollView>
      </View>
    </Modal>
  );
}

function RecipeItem({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <View style={{ backgroundColor: '#0a0a1a', borderRadius: 4, paddingHorizontal: 8, paddingVertical: 4, minWidth: 80 }}>
      <Text style={{ fontSize: 8, color: '#666' }}>{label}</Text>
      <Text style={{ fontSize: 12, color: accent ? '#FF9800' : '#fff', fontWeight: '600' }}>{value}</Text>
    </View>
  );
}

const inputStyle = {
  backgroundColor: '#1a1a2e',
  color: '#fff',
  borderRadius: 6,
  padding: 8,
  fontSize: 12,
  borderWidth: 1,
  borderColor: '#333',
} as const;
