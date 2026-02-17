import React from 'react';
import { View, Text, Dimensions } from 'react-native';
import Svg, { Circle, Line, Path, Text as SvgText, Rect, G } from 'react-native-svg';
import { styles } from './styles';

const screenWidth = typeof window !== 'undefined' ? Dimensions.get('window').width : 400;

export const SwrMeter = ({ data, centerFreq, resonantFreq, usable15, usable20, channelSpacing }: any) => {
  const width = Math.max(200, Math.min(screenWidth - 32, 380)); const height = 195;
  const padding = { top: 18, right: 12, bottom: 52, left: 36 };
  const chartWidth = width - padding.left - padding.right; const chartHeight = height - padding.top - padding.bottom;
  if (!data?.length) return null;
  const minFreq = Math.min(...data.map((d: any) => d.frequency)); const maxFreq = Math.max(...data.map((d: any) => d.frequency)); const freqRange = maxFreq - minFreq;
  const xScale = (freq: number) => padding.left + ((freq - minFreq) / freqRange) * chartWidth;
  const yScale = (swr: number) => padding.top + chartHeight - ((Math.min(swr, 3) - 1) / 2) * chartHeight;
  const createSwrPath = () => { let p = ''; data.forEach((pt: any, i: number) => { p += i === 0 ? `M ${xScale(pt.frequency)} ${yScale(pt.swr)}` : ` L ${xScale(pt.frequency)} ${yScale(pt.swr)}`; }); return p; };
  const getUsableZone = (threshold: number) => { const pts = data.filter((p: any) => p.swr <= threshold); if (!pts.length) return null; return { start: xScale(Math.min(...pts.map((p: any) => p.frequency))), end: xScale(Math.max(...pts.map((p: any) => p.frequency))) }; };
  const zone20 = getUsableZone(2.0); const zone15 = getUsableZone(1.5); const markers = data.filter((p: any) => p.channel % 10 === 0);
  const showResonant = resonantFreq && Math.abs(resonantFreq - centerFreq) > 0.01 && resonantFreq >= minFreq && resonantFreq <= maxFreq;
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
        {showResonant && <Line x1={xScale(resonantFreq)} y1={padding.top} x2={xScale(resonantFreq)} y2={height - padding.bottom} stroke="#FF9800" strokeWidth="1.5" strokeDasharray="5,3" />}
        {showResonant && <SvgText x={xScale(resonantFreq)} y={padding.top - 3} fill="#FF9800" fontSize="7" textAnchor="middle">RES</SvgText>}
        <Path d={createSwrPath()} fill="none" stroke="#FF5722" strokeWidth="2" />
        <SvgText x={width / 2} y={height - 2} fill="#2196F3" fontSize="13" fontWeight="bold" textAnchor="middle">{centerFreq.toFixed(3)} MHz{showResonant ? `  |  Res: ${resonantFreq.toFixed(3)}` : ''}</SvgText>
      </Svg>
      <View style={styles.swrLegend}>
        <View style={styles.legendItem}><View style={[styles.legendColor, { backgroundColor: '#4CAF50' }]} /><Text style={styles.legendText}>{'\u2264'}1.5 ({usable15?.toFixed(2)})</Text></View>
        <View style={styles.legendItem}><View style={[styles.legendColor, { backgroundColor: '#FFC107' }]} /><Text style={styles.legendText}>{'\u2264'}2.0 ({usable20?.toFixed(2)})</Text></View>
        {showResonant && <View style={styles.legendItem}><View style={[styles.legendColor, { backgroundColor: '#FF9800' }]} /><Text style={styles.legendText}>Resonant</Text></View>}
      </View>
    </View>
  );
};
