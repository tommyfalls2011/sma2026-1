import React from 'react';
import { View, Text, Dimensions } from 'react-native';
import Svg, { Circle, Line, Path, Text as SvgText, G } from 'react-native-svg';
import { Ionicons } from '@expo/vector-icons';
import { styles } from './styles';

const screenWidth = typeof window !== 'undefined' ? Dimensions.get('window').width : 400;

export const SmithChart = ({ data, centerFreq }: { data: any[], centerFreq: number }) => {
  const size = Math.max(200, Math.min(screenWidth - 48, 340));
  const cx = size / 2;
  const cy = size / 2;
  const R = (size - 44) / 2;

  const rValues = [0, 0.2, 0.5, 1, 2, 5];
  const xValues = [0.2, 0.5, 1, 2, 5];

  const gToX = (gr: number) => cx + gr * R;
  const gToY = (gi: number) => cy - gi * R;

  const rCircles = rValues.map(r => {
    const cxN = r / (r + 1);
    const rN = 1 / (r + 1);
    return { cx: gToX(cxN), cy: cy, r: rN * R, label: r === 0 ? '0' : String(r) };
  });

  const buildXArc = (x: number, positive: boolean) => {
    const rN = 1 / Math.abs(x);
    const cxN = 1;
    const cyN = positive ? 1 / x : -1 / x;
    const steps = 60;
    let pts: string[] = [];
    for (let i = 0; i <= steps; i++) {
      const t = (i / steps) * Math.PI * 2;
      const gx = cxN + rN * Math.cos(t);
      const gy = cyN + rN * Math.sin(t);
      if (gx * gx + gy * gy <= 1.01) {
        pts.push(`${gToX(gx).toFixed(1)},${gToY(gy).toFixed(1)}`);
      }
    }
    if (pts.length < 2) return '';
    return 'M ' + pts.join(' L ');
  };

  const buildTrace = () => {
    if (!data || data.length === 0) return '';
    let path = '';
    data.forEach((pt: any, i: number) => {
      const px = gToX(pt.gamma_real);
      const py = gToY(pt.gamma_imag);
      path += i === 0 ? `M ${px} ${py}` : ` L ${px} ${py}`;
    });
    return path;
  };

  const centerPt = data?.find((p: any) => Math.abs(p.freq - centerFreq) < 0.001) || (data && data[Math.floor(data.length / 2)]);
  const lowPt = data?.[0];
  const highPt = data?.[data.length - 1];

  return (
    <View style={styles.smithContainer} data-testid="smith-chart">
      <Text style={styles.smithTitle}>
        <Ionicons name="globe-outline" size={12} color="#00BCD4" /> Smith Chart (Impedance)
      </Text>
      <Svg width={size} height={size}>
        <Circle cx={cx} cy={cy} r={R} fill="#0a1520" stroke="#1a3a4a" strokeWidth="1.5" />
        {rCircles.map((c, i) => (
          <G key={`r${i}`}>
            <Circle cx={c.cx} cy={c.cy} r={c.r} fill="none" stroke="#1a2d3d" strokeWidth="0.6" />
          </G>
        ))}
        <Line x1={cx - R} y1={cy} x2={cx + R} y2={cy} stroke="#2a4a5a" strokeWidth="0.8" />
        {xValues.map((x, i) => (
          <G key={`x${i}`}>
            <Path d={buildXArc(x, true)} fill="none" stroke="#1a2d3d" strokeWidth="0.5" />
            <Path d={buildXArc(x, false)} fill="none" stroke="#1a2d3d" strokeWidth="0.5" />
          </G>
        ))}
        <Circle cx={cx} cy={cy} r={3} fill="#2a4a5a" stroke="#4a6a7a" strokeWidth="0.5" />
        {data && <Path d={buildTrace()} fill="none" stroke="#00BCD4" strokeWidth="2" />}
        {lowPt && (
          <G>
            <Circle cx={gToX(lowPt.gamma_real)} cy={gToY(lowPt.gamma_imag)} r={4} fill="#FF9800" stroke="#fff" strokeWidth="0.5" />
            <SvgText x={gToX(lowPt.gamma_real) - 12} y={gToY(lowPt.gamma_imag) + 12} fill="#FF9800" fontSize="7">Lo</SvgText>
          </G>
        )}
        {highPt && (
          <G>
            <Circle cx={gToX(highPt.gamma_real)} cy={gToY(highPt.gamma_imag)} r={4} fill="#E91E63" stroke="#fff" strokeWidth="0.5" />
            <SvgText x={gToX(highPt.gamma_real) + 5} y={gToY(highPt.gamma_imag) + 3} fill="#E91E63" fontSize="7">Hi</SvgText>
          </G>
        )}
        {centerPt && (
          <G>
            <Circle cx={gToX(centerPt.gamma_real)} cy={gToY(centerPt.gamma_imag)} r={5} fill="#4CAF50" stroke="#fff" strokeWidth="1" />
            <SvgText x={gToX(centerPt.gamma_real) + 7} y={gToY(centerPt.gamma_imag) - 5} fill="#4CAF50" fontSize="8" fontWeight="bold">f0</SvgText>
          </G>
        )}
        {rValues.filter(r => r > 0).map(r => (
          <SvgText key={`rl${r}`} x={gToX(r / (r + 1)) - (r < 1 ? 3 : 5)} y={cy + 10} fill="#4a6a7a" fontSize="7">{r}</SvgText>
        ))}
        {[0.5, 1, 2].map(x => (
          <G key={`xl${x}`}>
            <SvgText x={cx + R - 14} y={gToY(1 / (x + 1)) - 2} fill="#3a5a4a" fontSize="6">+j{x}</SvgText>
            <SvgText x={cx + R - 14} y={gToY(-1 / (x + 1)) + 7} fill="#5a3a4a" fontSize="6">-j{x}</SvgText>
          </G>
        ))}
        <SvgText x={cx + R + 2} y={cy + 3} fill="#4a6a7a" fontSize="7">Z=inf</SvgText>
        <SvgText x={cx - R - 18} y={cy + 3} fill="#4a6a7a" fontSize="7">Z=0</SvgText>
      </Svg>
      {centerPt && (
        <View style={styles.smithReadout}>
          <View style={styles.smithReadoutRow}>
            <View style={styles.smithReadoutItem}>
              <Text style={styles.smithReadoutLabel}>R (Resistance)</Text>
              <Text style={[styles.smithReadoutValue, { color: '#00BCD4' }]}>{centerPt.z_real} Ohm</Text>
            </View>
            <View style={styles.smithReadoutItem}>
              <Text style={styles.smithReadoutLabel}>X (Reactance)</Text>
              <Text style={[styles.smithReadoutValue, { color: centerPt.z_imag >= 0 ? '#4CAF50' : '#FF9800' }]}>
                {centerPt.z_imag >= 0 ? '+' : ''}{centerPt.z_imag} Ohm
              </Text>
            </View>
          </View>
          <View style={styles.smithReadoutRow}>
            <View style={styles.smithReadoutItem}>
              <Text style={styles.smithReadoutLabel}>L (Inductance)</Text>
              <Text style={[styles.smithReadoutValue, { color: '#4CAF50' }]}>
                {centerPt.inductance_nh > 0 ? `${centerPt.inductance_nh} nH` : '--'}
              </Text>
            </View>
            <View style={styles.smithReadoutItem}>
              <Text style={styles.smithReadoutLabel}>C (Capacitance)</Text>
              <Text style={[styles.smithReadoutValue, { color: '#FF9800' }]}>
                {centerPt.capacitance_pf > 0 ? `${centerPt.capacitance_pf} pF` : '--'}
              </Text>
            </View>
          </View>
          <View style={styles.smithReadoutRow}>
            <View style={styles.smithReadoutItem}>
              <Text style={styles.smithReadoutLabel}>|Gamma| (Reflection)</Text>
              <Text style={[styles.smithReadoutValue, { color: '#9C27B0' }]}>
                {Math.sqrt(centerPt.gamma_real ** 2 + centerPt.gamma_imag ** 2).toFixed(4)}
              </Text>
            </View>
            <View style={styles.smithReadoutItem}>
              <Text style={styles.smithReadoutLabel}>Freq</Text>
              <Text style={[styles.smithReadoutValue, { color: '#fff' }]}>{centerPt.freq} MHz</Text>
            </View>
          </View>
          {lowPt && highPt && (
            <View style={styles.smithBandEdges}>
              <Text style={styles.smithBandEdgeText}>
                <Text style={{ color: '#FF9800' }}>Lo {lowPt.freq}:</Text> {lowPt.z_real}{lowPt.z_imag >= 0 ? '+' : ''}{lowPt.z_imag}j Ohm
                {lowPt.inductance_nh > 0 ? ` | L=${lowPt.inductance_nh}nH` : ''}
                {lowPt.capacitance_pf > 0 ? ` | C=${lowPt.capacitance_pf}pF` : ''}
              </Text>
              <Text style={styles.smithBandEdgeText}>
                <Text style={{ color: '#E91E63' }}>Hi {highPt.freq}:</Text> {highPt.z_real}{highPt.z_imag >= 0 ? '+' : ''}{highPt.z_imag}j Ohm
                {highPt.inductance_nh > 0 ? ` | L=${highPt.inductance_nh}nH` : ''}
                {highPt.capacitance_pf > 0 ? ` | C=${highPt.capacitance_pf}pF` : ''}
              </Text>
            </View>
          )}
        </View>
      )}
    </View>
  );
};
