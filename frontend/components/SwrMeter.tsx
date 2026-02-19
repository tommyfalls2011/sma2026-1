import React from 'react';
import { View, Text, Dimensions } from 'react-native';
import Svg, { Line, Path, Text as SvgText, Rect, G, Circle, Defs, LinearGradient, Stop } from 'react-native-svg';
import { styles } from './styles';

const screenWidth = typeof window !== 'undefined' ? Dimensions.get('window').width : 400;

export const SwrMeter = ({ data, centerFreq, resonantFreq, usable15, usable20, channelSpacing }: any) => {
  const width = Math.max(200, Math.min(screenWidth - 32, 380));
  const height = 210;
  const padding = { top: 18, right: 12, bottom: 52, left: 36 };
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;
  if (!data?.length) return null;

  const minFreq = Math.min(...data.map((d: any) => d.frequency));
  const maxFreq = Math.max(...data.map((d: any) => d.frequency));
  const freqRange = maxFreq - minFreq;
  const xScale = (freq: number) => padding.left + ((freq - minFreq) / freqRange) * chartWidth;
  const yScale = (swr: number) => padding.top + chartHeight - ((Math.min(swr, 3) - 1) / 2) * chartHeight;

  const createSwrPath = () => {
    let p = '';
    data.forEach((pt: any, i: number) => {
      p += i === 0 ? `M ${xScale(pt.frequency)} ${yScale(pt.swr)}` : ` L ${xScale(pt.frequency)} ${yScale(pt.swr)}`;
    });
    return p;
  };

  // Zone calculation with channel counts
  const getZone = (threshold: number) => {
    const pts = data.filter((p: any) => p.swr <= threshold);
    if (!pts.length) return null;
    const freqs = pts.map((p: any) => p.frequency);
    return {
      start: xScale(Math.min(...freqs)),
      end: xScale(Math.max(...freqs)),
      channels: pts.length,
      startFreq: Math.min(...freqs),
      endFreq: Math.max(...freqs),
    };
  };

  const zone20 = getZone(2.0);
  const zone15 = getZone(1.5);
  const markers = data.filter((p: any) => p.channel % 10 === 0);

  // Find minimum SWR point
  const minPt = data.reduce((min: any, pt: any) => pt.swr < min.swr ? pt : min, data[0]);

  const showResonant = resonantFreq && Math.abs(resonantFreq - centerFreq) > 0.01 && resonantFreq >= minFreq && resonantFreq <= maxFreq;

  // Channel spacing for label
  const chSpacingMhz = (channelSpacing || 10) / 1000;

  return (
    <View style={styles.swrContainer} data-testid="swr-bandwidth-chart">
      <Text style={styles.swrTitle}>SWR Bandwidth</Text>
      <Svg width={width} height={height}>
        <Defs>
          <LinearGradient id="zone15grad" x1="0" y1="0" x2="0" y2="1">
            <Stop offset="0" stopColor="#4CAF50" stopOpacity="0.35" />
            <Stop offset="1" stopColor="#4CAF50" stopOpacity="0.08" />
          </LinearGradient>
          <LinearGradient id="zone20grad" x1="0" y1="0" x2="0" y2="1">
            <Stop offset="0" stopColor="#FFC107" stopOpacity="0.25" />
            <Stop offset="1" stopColor="#FFC107" stopOpacity="0.05" />
          </LinearGradient>
        </Defs>

        {/* Chart background */}
        <Rect x={padding.left} y={padding.top} width={chartWidth} height={chartHeight} fill="#111" rx={2} />

        {/* 2.0:1 zone band */}
        {zone20 && (
          <G>
            <Rect x={zone20.start} y={padding.top} width={zone20.end - zone20.start} height={chartHeight} fill="url(#zone20grad)" />
            <Line x1={zone20.start} y1={padding.top} x2={zone20.start} y2={padding.top + chartHeight} stroke="#FFC107" strokeWidth="0.8" strokeOpacity="0.5" strokeDasharray="2,2" />
            <Line x1={zone20.end} y1={padding.top} x2={zone20.end} y2={padding.top + chartHeight} stroke="#FFC107" strokeWidth="0.8" strokeOpacity="0.5" strokeDasharray="2,2" />
          </G>
        )}

        {/* 1.5:1 zone band */}
        {zone15 && (
          <G>
            <Rect x={zone15.start} y={padding.top} width={zone15.end - zone15.start} height={chartHeight} fill="url(#zone15grad)" />
            <Line x1={zone15.start} y1={padding.top} x2={zone15.start} y2={padding.top + chartHeight} stroke="#4CAF50" strokeWidth="1" strokeOpacity="0.6" strokeDasharray="2,2" />
            <Line x1={zone15.end} y1={padding.top} x2={zone15.end} y2={padding.top + chartHeight} stroke="#4CAF50" strokeWidth="1" strokeOpacity="0.6" strokeDasharray="2,2" />
          </G>
        )}

        {/* Grid lines */}
        {[1.0, 1.5, 2.0, 3.0].map(swr => (
          <G key={swr}>
            <Line x1={padding.left} y1={yScale(swr)} x2={width - padding.right} y2={yScale(swr)} stroke={swr === 1.0 ? '#00BCD4' : swr === 1.5 ? '#4CAF50' : swr === 2.0 ? '#FFC107' : '#282828'} strokeWidth={swr <= 2.0 ? 1 : 0.6} strokeDasharray={swr > 2.0 ? '3,3' : '0'} />
            <SvgText x={padding.left - 4} y={yScale(swr) + 3} fill={swr === 1.0 ? '#00BCD4' : swr === 1.5 ? '#4CAF50' : swr === 2.0 ? '#FFC107' : '#444'} fontSize="8" textAnchor="end">{swr.toFixed(1)}</SvgText>
          </G>
        ))}

        {/* Channel markers */}
        {markers.map((pt: any) => (
          <G key={pt.channel}>
            <Line x1={xScale(pt.frequency)} y1={height - padding.bottom} x2={xScale(pt.frequency)} y2={height - padding.bottom + 3} stroke={pt.channel === 0 ? '#2196F3' : '#444'} strokeWidth={pt.channel === 0 ? 1.5 : 0.8} />
            <SvgText x={xScale(pt.frequency)} y={height - padding.bottom + 12} fill={pt.channel === 0 ? '#2196F3' : '#555'} fontSize="7" textAnchor="middle">{pt.channel === 0 ? 'CTR' : pt.channel > 0 ? `+${pt.channel}` : pt.channel}</SvgText>
          </G>
        ))}

        {/* Center freq vertical */}
        <Line x1={xScale(centerFreq)} y1={padding.top} x2={xScale(centerFreq)} y2={height - padding.bottom} stroke="#2196F3" strokeWidth="1.5" strokeDasharray="3,3" />

        {/* Resonant freq line */}
        {showResonant && <Line x1={xScale(resonantFreq)} y1={padding.top} x2={xScale(resonantFreq)} y2={height - padding.bottom} stroke="#FF9800" strokeWidth="1.5" strokeDasharray="5,3" />}
        {showResonant && <SvgText x={xScale(resonantFreq)} y={padding.top - 3} fill="#FF9800" fontSize="7" textAnchor="middle">RES</SvgText>}

        {/* SWR curve */}
        <Path d={createSwrPath()} fill="none" stroke="#FF5722" strokeWidth="2.2" strokeLinejoin="round" />

        {/* Min SWR indicator dot */}
        <Circle cx={xScale(minPt.frequency)} cy={yScale(minPt.swr)} r={3.5} fill="#FF5722" stroke="#fff" strokeWidth="1.2" />
        <SvgText x={xScale(minPt.frequency)} y={yScale(minPt.swr) - 7} fill="#fff" fontSize="8" fontWeight="bold" textAnchor="middle">{minPt.swr.toFixed(2)}</SvgText>

        {/* Channel count badges */}
        {zone15 && zone15.channels > 0 && (
          <G>
            <Rect x={(zone15.start + zone15.end) / 2 - 20} y={padding.top + 3} width={40} height={16} rx={8} fill="#4CAF50" fillOpacity="0.85" />
            <SvgText x={(zone15.start + zone15.end) / 2} y={padding.top + 14} fill="#fff" fontSize="9" fontWeight="bold" textAnchor="middle">{zone15.channels} CH</SvgText>
          </G>
        )}
        {zone20 && zone20.channels > 0 && (!zone15 || zone20.channels !== zone15.channels) && (
          <G>
            <Rect x={zone20.end - 38} y={padding.top + 22} width={36} height={14} rx={7} fill="#FFC107" fillOpacity="0.85" />
            <SvgText x={zone20.end - 20} y={padding.top + 32} fill="#1a1a1a" fontSize="8" fontWeight="bold" textAnchor="middle">{zone20.channels} CH</SvgText>
          </G>
        )}

        {/* Bottom frequency label */}
        <SvgText x={width / 2} y={height - 2} fill="#2196F3" fontSize="13" fontWeight="bold" textAnchor="middle">{centerFreq.toFixed(3)} MHz{showResonant ? `  |  Res: ${resonantFreq.toFixed(3)}` : ''}</SvgText>
      </Svg>

      {/* Legend with bandwidth values */}
      <View style={styles.swrLegend}>
        <View style={styles.legendItem}>
          <View style={[styles.legendColor, { backgroundColor: '#4CAF50' }]} />
          <Text style={styles.legendText}>{'\u2264'}1.5 : {usable15?.toFixed(2) || '0.00'} MHz{zone15 ? ` (${zone15.channels} ch)` : ''}</Text>
        </View>
        <View style={styles.legendItem}>
          <View style={[styles.legendColor, { backgroundColor: '#FFC107' }]} />
          <Text style={styles.legendText}>{'\u2264'}2.0 : {usable20?.toFixed(2) || '0.00'} MHz{zone20 ? ` (${zone20.channels} ch)` : ''}</Text>
        </View>
        {showResonant && (
          <View style={styles.legendItem}>
            <View style={[styles.legendColor, { backgroundColor: '#FF9800' }]} />
            <Text style={styles.legendText}>Resonant</Text>
          </View>
        )}
      </View>
    </View>
  );
};
