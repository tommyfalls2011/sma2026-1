import React, { useState } from 'react';
import { View, Text, ScrollView, TouchableOpacity, Platform } from 'react-native';

interface DebugItem {
  var: string;
  val: any;
  unit: string;
  formula?: string;
}

interface DebugStep {
  step: number;
  label: string;
  items: DebugItem[];
}

interface Props {
  visible: boolean;
  onClose: () => void;
  debugTrace: DebugStep[];
  smithChartData?: any[];
  centerFreq?: number;
}

const STEP_COLORS: Record<number, string> = {
  1: '#FF6B6B',  // Hardware - red
  2: '#4ECDC4',  // Wavelength - teal
  3: '#45B7D1',  // Capacitance - blue
  4: '#96CEB4',  // Z0 - green
  5: '#FFEAA7',  // K ratio - yellow
  6: '#DDA0DD',  // Stub - plum
  7: '#F0B27A',  // Cap reactance - orange
  8: '#E74C3C',  // Net X - bright red
  9: '#3498DB',  // Impedance - bright blue
  10: '#2ECC71', // SWR - bright green
};

export const PhysicsDebugPanel: React.FC<Props> = ({ visible, onClose, debugTrace, smithChartData, centerFreq }) => {
  const [collapsed, setCollapsed] = useState<Record<number, boolean>>({});

  if (!visible || !debugTrace || debugTrace.length === 0) return null;

  const toggleStep = (step: number) => {
    setCollapsed(prev => ({ ...prev, [step]: !prev[step] }));
  };

  // Find center smith chart point
  const centerPt = smithChartData?.find((p: any) => centerFreq && Math.abs(p.freq - centerFreq) < 0.02);

  return (
    <View style={{
      position: Platform.OS === 'web' ? 'fixed' as any : 'absolute',
      right: 0, top: 0, bottom: 0,
      width: 340,
      backgroundColor: '#0a0a0a',
      borderLeftWidth: 1,
      borderLeftColor: '#333',
      zIndex: 9999,
      ...(Platform.OS === 'web' ? { boxShadow: '-4px 0 20px rgba(0,0,0,0.8)' } : {}),
    }} data-testid="physics-debug-panel">
      {/* Header */}
      <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: 10, borderBottomWidth: 1, borderBottomColor: '#333', backgroundColor: '#111' }}>
        <Text style={{ color: '#4CAF50', fontSize: 13, fontWeight: '700', fontFamily: Platform.OS === 'web' ? 'monospace' : undefined }}>PHYSICS TRACE</Text>
        <TouchableOpacity onPress={onClose} data-testid="debug-panel-close">
          <Text style={{ color: '#888', fontSize: 18, fontWeight: '700' }}>X</Text>
        </TouchableOpacity>
      </View>

      <ScrollView style={{ flex: 1 }} contentContainerStyle={{ paddingBottom: 40 }}>
        {debugTrace.map((step) => {
          const color = STEP_COLORS[step.step] || '#888';
          const isCollapsed = collapsed[step.step];
          return (
            <View key={step.step} style={{ borderBottomWidth: 1, borderBottomColor: '#1a1a1a' }}>
              {/* Step header */}
              <TouchableOpacity
                onPress={() => toggleStep(step.step)}
                style={{ flexDirection: 'row', alignItems: 'center', padding: 8, backgroundColor: '#111' }}
                data-testid={`debug-step-${step.step}`}
              >
                <Text style={{ color, fontSize: 10, fontWeight: '700', fontFamily: Platform.OS === 'web' ? 'monospace' : undefined, width: 18 }}>
                  {step.step}.
                </Text>
                <Text style={{ color, fontSize: 10, fontWeight: '700', fontFamily: Platform.OS === 'web' ? 'monospace' : undefined, flex: 1 }}>
                  {step.label}
                </Text>
                <Text style={{ color: '#555', fontSize: 10 }}>{isCollapsed ? '+' : '-'}</Text>
              </TouchableOpacity>

              {/* Step items */}
              {!isCollapsed && step.items.map((item, idx) => (
                <View key={idx} style={{ flexDirection: 'row', paddingHorizontal: 8, paddingVertical: 3, backgroundColor: idx % 2 === 0 ? '#0d0d0d' : '#0a0a0a' }}>
                  <Text style={{ color: '#888', fontSize: 10, fontFamily: Platform.OS === 'web' ? 'monospace' : undefined, width: 100 }}>
                    {item.var}
                  </Text>
                  <Text style={{ color: '#fff', fontSize: 10, fontFamily: Platform.OS === 'web' ? 'monospace' : undefined, width: 80, textAlign: 'right' }}>
                    {typeof item.val === 'number' ? (Number.isInteger(item.val) ? item.val : item.val.toFixed ? item.val : item.val) : item.val}
                  </Text>
                  <Text style={{ color: '#666', fontSize: 9, fontFamily: Platform.OS === 'web' ? 'monospace' : undefined, width: 30, marginLeft: 2 }}>
                    {item.unit}
                  </Text>
                  {item.formula && (
                    <Text style={{ color: '#555', fontSize: 8, fontFamily: Platform.OS === 'web' ? 'monospace' : undefined, flex: 1, marginLeft: 4 }} numberOfLines={1}>
                      {item.formula}
                    </Text>
                  )}
                </View>
              ))}
            </View>
          );
        })}

        {/* Smith Chart center point */}
        {centerPt && (
          <View style={{ borderTopWidth: 1, borderTopColor: '#333', marginTop: 8 }}>
            <View style={{ padding: 8, backgroundColor: '#111' }}>
              <Text style={{ color: '#FF9800', fontSize: 10, fontWeight: '700', fontFamily: Platform.OS === 'web' ? 'monospace' : undefined }}>
                SMITH CHART @ {centerPt.freq} MHz
              </Text>
            </View>
            {[
              { var: 'Z_real', val: centerPt.z_real?.toFixed(2), unit: 'ohm' },
              { var: 'Z_imag', val: centerPt.z_imag?.toFixed(2), unit: 'ohm' },
              { var: 'Gamma_re', val: centerPt.gamma_real?.toFixed(6), unit: '' },
              { var: 'Gamma_im', val: centerPt.gamma_imag?.toFixed(6), unit: '' },
              { var: 'L', val: centerPt.inductance_nh > 0 ? centerPt.inductance_nh : '--', unit: 'nH' },
              { var: 'C', val: centerPt.capacitance_pf > 0 ? centerPt.capacitance_pf : '--', unit: 'pF' },
            ].map((item, idx) => (
              <View key={idx} style={{ flexDirection: 'row', paddingHorizontal: 8, paddingVertical: 3, backgroundColor: idx % 2 === 0 ? '#0d0d0d' : '#0a0a0a' }}>
                <Text style={{ color: '#888', fontSize: 10, fontFamily: Platform.OS === 'web' ? 'monospace' : undefined, width: 100 }}>{item.var}</Text>
                <Text style={{ color: '#FF9800', fontSize: 10, fontFamily: Platform.OS === 'web' ? 'monospace' : undefined, width: 80, textAlign: 'right' }}>{item.val}</Text>
                <Text style={{ color: '#666', fontSize: 9, fontFamily: Platform.OS === 'web' ? 'monospace' : undefined, width: 30, marginLeft: 2 }}>{item.unit}</Text>
              </View>
            ))}
          </View>
        )}

        {/* SWR at band edges from smith chart */}
        {smithChartData && smithChartData.length > 2 && (
          <View style={{ borderTopWidth: 1, borderTopColor: '#333', marginTop: 4 }}>
            <View style={{ padding: 8, backgroundColor: '#111' }}>
              <Text style={{ color: '#E91E63', fontSize: 10, fontWeight: '700', fontFamily: Platform.OS === 'web' ? 'monospace' : undefined }}>
                BAND EDGE IMPEDANCES
              </Text>
            </View>
            {[smithChartData[0], smithChartData[smithChartData.length - 1]].map((pt, idx) => (
              <View key={idx} style={{ flexDirection: 'row', paddingHorizontal: 8, paddingVertical: 3, backgroundColor: idx % 2 === 0 ? '#0d0d0d' : '#0a0a0a' }}>
                <Text style={{ color: '#888', fontSize: 10, fontFamily: Platform.OS === 'web' ? 'monospace' : undefined, width: 60 }}>{pt.freq} MHz</Text>
                <Text style={{ color: '#E91E63', fontSize: 10, fontFamily: Platform.OS === 'web' ? 'monospace' : undefined, flex: 1, textAlign: 'right' }}>
                  {pt.z_real?.toFixed(1)} {pt.z_imag >= 0 ? '+' : ''}{pt.z_imag?.toFixed(1)}j ohm
                </Text>
              </View>
            ))}
          </View>
        )}
      </ScrollView>
    </View>
  );
};
