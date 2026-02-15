import React from 'react';
import { View, Text, Dimensions } from 'react-native';
import Svg, { Circle, Line, Path, Rect, G, Ellipse, Text as SvgText } from 'react-native-svg';
import { Ionicons } from '@expo/vector-icons';
import { styles } from '../styles';

const { width: screenWidth } = Dimensions.get('window');

export const ElevationPattern = ({ takeoffAngle, gain, orientation }: { takeoffAngle: number, gain: number, orientation?: string }) => {
  const width = Math.min(screenWidth - 48, 300);
  const height = 160;
  const groundY = height - 25;
  const centerX = width / 2;
  const centerY = groundY - 50;
  const mainLobeLength = Math.min(width * 0.35, 80 + gain * 3);
  const mainLobeWidth = Math.max(15, 40 - gain);
  const backLobeSize = Math.max(15, 45 - gain);
  const effectiveAngle = takeoffAngle * Math.PI / 180;
  const mainLobeEndX = centerX + Math.cos(effectiveAngle) * mainLobeLength;
  const mainLobeEndY = centerY - Math.sin(effectiveAngle) * mainLobeLength;
  const mainLobePath = `M ${centerX} ${centerY} Q ${centerX + mainLobeLength * 0.3} ${centerY - mainLobeWidth}, ${mainLobeEndX} ${mainLobeEndY} Q ${centerX + mainLobeLength * 0.3} ${centerY + mainLobeWidth * 0.5}, ${centerX} ${centerY}`;

  return (
    <View style={styles.elevationContainer}>
      <Text style={styles.elevationTitle}>
        <Ionicons name="radio-outline" size={12} color="#FF5722" /> Side View (Elevation Pattern)
      </Text>
      <Svg width={width} height={height}>
        <Rect x={0} y={0} width={width} height={groundY} fill="#0d1520" />
        <Rect x={0} y={groundY} width={width} height={25} fill="#1a2f15" />
        <Line x1={0} y1={groundY} x2={width} y2={groundY} stroke="#3d6b2a" strokeWidth="2" />
        {[10, 20, 30, 45, 60].map(angle => {
          const rad = angle * Math.PI / 180;
          const lineLen = width * 0.4;
          return (
            <G key={angle}>
              <Line x1={centerX} y1={centerY} x2={centerX + Math.cos(rad) * lineLen} y2={centerY - Math.sin(rad) * lineLen} stroke="#2a3d4a" strokeWidth="0.5" strokeDasharray="4,4" />
              <SvgText x={centerX + Math.cos(rad) * lineLen + 3} y={centerY - Math.sin(rad) * lineLen} fill="#4a6070" fontSize="8">{angle}{'\u00B0'}</SvgText>
            </G>
          );
        })}
        <Line x1={centerX - 20} y1={centerY} x2={width - 20} y2={centerY} stroke="#2a3d4a" strokeWidth="0.5" strokeDasharray="4,4" />
        <Path d={mainLobePath} fill="rgba(76,175,80,0.5)" stroke="#4CAF50" strokeWidth="2" />
        <Ellipse cx={centerX - backLobeSize / 2} cy={centerY} rx={backLobeSize / 2} ry={backLobeSize / 3} fill="rgba(255,152,0,0.4)" stroke="#FF9800" strokeWidth="1.5" />
        <Line x1={centerX - 25} y1={centerY} x2={centerX + 25} y2={centerY} stroke="#888" strokeWidth="3" />
        <Line x1={centerX} y1={centerY} x2={centerX} y2={groundY} stroke="#666" strokeWidth="2" />
        <Line x1={centerX} y1={centerY} x2={mainLobeEndX * 0.85 + centerX * 0.15} y2={mainLobeEndY * 0.85 + centerY * 0.15} stroke="#FF5722" strokeWidth="2" />
        <Circle cx={mainLobeEndX * 0.85 + centerX * 0.15} cy={mainLobeEndY * 0.85 + centerY * 0.15} r={4} fill="#FF5722" />
        <SvgText x={centerX + 45} y={20} fill="#4CAF50" fontSize="10" fontWeight="bold">Main Beam</SvgText>
        <SvgText x={10} y={centerY + 4} fill="#FF9800" fontSize="9">Back Lobe</SvgText>
        <SvgText x={centerX + 5} y={groundY - 5} fill="#FF5722" fontSize="10" fontWeight="bold">{takeoffAngle}{'\u00B0'} take-off</SvgText>
        <SvgText x={width - 35} y={centerY + 4} fill="#2196F3" fontSize="8" fontWeight="bold">DX {'\u2192'}</SvgText>
        <SvgText x={centerX - 10} y={15} fill="#9C27B0" fontSize="8">NVIS {'\u2191'}</SvgText>
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
      </View>
    </View>
  );
};
