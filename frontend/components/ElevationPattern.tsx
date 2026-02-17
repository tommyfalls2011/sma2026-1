import React from 'react';
import { View, Text, Dimensions } from 'react-native';
import Svg, { Circle, Line, Path, Text as SvgText, Rect, G } from 'react-native-svg';
import { Ionicons } from '@expo/vector-icons';
import { styles } from './styles';

const screenWidth = typeof window !== 'undefined' ? Dimensions.get('window').width : 400;

export const ElevationPattern = ({ takeoffAngle, gain, orientation, elevationData, fbRatio }: { takeoffAngle: number, gain: number, orientation?: string, elevationData?: any[], fbRatio?: number }) => {
  const width = Math.max(200, Math.min(screenWidth - 48, 340));
  const height = 200;
  const groundY = height - 22;
  const centerX = width / 2;
  const centerY = groundY;
  const maxRadius = groundY - 12;

  const buildPolarPath = () => {
    if (!elevationData || elevationData.length === 0) return '';
    const maxMag = Math.max(...elevationData.map((p: any) => p.magnitude), 1);
    let path = '';
    const points = elevationData.filter((p: any) => p.angle <= 180);
    points.forEach((pt: any, i: number) => {
      const angleRad = pt.angle * Math.PI / 180;
      const r = (pt.magnitude / maxMag) * maxRadius;
      const x = centerX + Math.cos(angleRad) * r;
      const y = centerY - Math.sin(angleRad) * r;
      path += i === 0 ? `M ${x} ${y}` : ` L ${x} ${y}`;
    });
    path += ' Z';
    return path;
  };

  const buildFrontPath = () => {
    if (!elevationData || elevationData.length === 0) return '';
    const maxMag = Math.max(...elevationData.map((p: any) => p.magnitude), 1);
    let path = `M ${centerX} ${centerY}`;
    const front = elevationData.filter((p: any) => p.angle <= 90);
    front.forEach((pt: any) => {
      const angleRad = pt.angle * Math.PI / 180;
      const r = (pt.magnitude / maxMag) * maxRadius;
      path += ` L ${centerX + Math.cos(angleRad) * r} ${centerY - Math.sin(angleRad) * r}`;
    });
    path += ` L ${centerX} ${centerY - 1} Z`;
    return path;
  };

  const buildBackPath = () => {
    if (!elevationData || elevationData.length === 0) return '';
    const maxMag = Math.max(...elevationData.map((p: any) => p.magnitude), 1);
    let path = `M ${centerX} ${centerY - 1}`;
    const back = elevationData.filter((p: any) => p.angle >= 90 && p.angle <= 180);
    back.forEach((pt: any) => {
      const angleRad = pt.angle * Math.PI / 180;
      const r = (pt.magnitude / maxMag) * maxRadius;
      path += ` L ${centerX + Math.cos(angleRad) * r} ${centerY - Math.sin(angleRad) * r}`;
    });
    path += ` L ${centerX} ${centerY} Z`;
    return path;
  };

  const refAngles = [15, 30, 45, 60, 75];

  return (
    <View style={styles.elevationContainer}>
      <Text style={styles.elevationTitle}>
        Side View (Elevation Pattern)
      </Text>
      <Svg width={width} height={height}>
        <Rect x={0} y={0} width={width} height={groundY} fill="#0d1520" />
        <Rect x={0} y={groundY} width={width} height={22} fill="#1a2f15" />
        <Line x1={0} y1={groundY} x2={width} y2={groundY} stroke="#3d6b2a" strokeWidth="2" />
        {[0.25, 0.5, 0.75, 1.0].map(frac => (
          <Path key={frac} d={`M ${centerX - maxRadius * frac} ${centerY} A ${maxRadius * frac} ${maxRadius * frac} 0 0 1 ${centerX + maxRadius * frac} ${centerY}`} fill="none" stroke="#1a2a3a" strokeWidth="0.5" />
        ))}
        {refAngles.map(angle => {
          const rad = angle * Math.PI / 180;
          const fEndX = centerX + Math.cos(rad) * maxRadius;
          const fEndY = centerY - Math.sin(rad) * maxRadius;
          const bEndX = centerX - Math.cos(rad) * maxRadius;
          const bEndY = centerY - Math.sin(rad) * maxRadius;
          return (
            <G key={angle}>
              <Line x1={centerX} y1={centerY} x2={fEndX} y2={fEndY} stroke="#1a2a3a" strokeWidth="0.5" strokeDasharray="3,5" />
              <Line x1={centerX} y1={centerY} x2={bEndX} y2={bEndY} stroke="#1a2028" strokeWidth="0.5" strokeDasharray="3,5" />
              <SvgText x={fEndX + 2} y={fEndY + 3} fill="#3a5a6a" fontSize="7">{angle}°</SvgText>
            </G>
          );
        })}
        <Line x1={10} y1={centerY} x2={width - 10} y2={centerY} stroke="#2a3d4a" strokeWidth="0.8" strokeDasharray="4,4" />
        {elevationData && <Path d={buildFrontPath()} fill="rgba(76,175,80,0.35)" stroke="none" />}
        {elevationData && <Path d={buildBackPath()} fill="rgba(255,152,0,0.3)" stroke="none" />}
        {elevationData && <Path d={buildPolarPath()} fill="none" stroke="#4CAF50" strokeWidth="1.5" />}
        {takeoffAngle > 0 && (() => {
          const rad = takeoffAngle * Math.PI / 180;
          const tipX = centerX + Math.cos(rad) * (maxRadius + 5);
          const tipY = centerY - Math.sin(rad) * (maxRadius + 5);
          return (
            <G>
              <Line x1={centerX} y1={centerY} x2={tipX} y2={tipY} stroke="#FF5722" strokeWidth="1.5" strokeDasharray="4,3" />
              <Circle cx={tipX} cy={tipY} r={3} fill="#FF5722" />
              <SvgText x={tipX + 5} y={tipY + 3} fill="#FF5722" fontSize="9" fontWeight="bold">{takeoffAngle}°</SvgText>
            </G>
          );
        })()}
        <Line x1={centerX - 18} y1={centerY} x2={centerX + 18} y2={centerY} stroke="#888" strokeWidth="2.5" />
        <SvgText x={width - 30} y={centerY - 5} fill="#4CAF50" fontSize="8" fontWeight="bold">FWD</SvgText>
        <SvgText x={5} y={centerY - 5} fill="#FF9800" fontSize="8" fontWeight="bold">BACK</SvgText>
        <SvgText x={centerX - 10} y={12} fill="#9C27B0" fontSize="8">NVIS</SvgText>
      </Svg>
      <View style={styles.elevationLegend}>
        <View style={styles.elevationLegendRow}>
          <View style={[styles.elevationLegendDot, { backgroundColor: '#4CAF50' }]} />
          <Text style={styles.elevationLegendText}>
            {takeoffAngle < 10 ? 'Elite: Extremely low angle, massive DX' :
             takeoffAngle < 15 ? 'Deep DX: Reaching other continents' :
             takeoffAngle < 18 ? 'DX Sweet Spot: Maximum ground gain' :
             takeoffAngle < 28 ? 'Regional/Mid-Range skip' :
             takeoffAngle < 35 ? 'Minimum: Moderate skip' :
             takeoffAngle < 50 ? 'Medium: Regional/DX mix' :
             takeoffAngle < 70 ? 'Near Vertical: Short distance' :
             'Inefficient: Ground absorption'}
          </Text>
        </View>
        <View style={styles.elevationLegendRow}>
          <View style={[styles.elevationLegendDot, { backgroundColor: '#FF9800' }]} />
          <Text style={styles.elevationLegendText}>Back lobes (F/B: {fbRatio ?? '-'} dB)</Text>
        </View>
      </View>
    </View>
  );
};
