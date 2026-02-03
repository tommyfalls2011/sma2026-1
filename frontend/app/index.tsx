import React, { useState, useCallback } from 'react';
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

// Band definitions
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
}

interface SwrPoint {
  frequency: number;
  swr: number;
  channel: number;
}

interface StackingInfo {
  orientation: string;
  num_antennas: number;
  spacing: number;
  spacing_unit: string;
  spacing_wavelengths: number;
  gain_increase_db: number;
  new_beamwidth_h: number;
  new_beamwidth_v: number;
  stacked_multiplication_factor: number;
  optimal_spacing_ft: number;
  total_height_ft?: number;
  total_width_ft?: number;
}

interface AntennaOutput {
  swr: number;
  swr_description: string;
  fb_ratio: number;
  fb_ratio_description: string;
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
  swr_curve: SwrPoint[];
  usable_bandwidth_1_5: number;
  usable_bandwidth_2_0: number;
  center_frequency: number;
  band_info: { name: string; center: number; start: number; end: number; channel_spacing_khz: number };
  input_summary: Record<string, any>;
  stacking_enabled: boolean;
  stacking_info?: StackingInfo;
  stacked_gain_dbi?: number;
  stacked_pattern?: { angle: number; magnitude: number }[];
}

const ResultCard = ({ title, value, description, icon, color }: {
  title: string;
  value: string;
  description: string;
  icon: keyof typeof Ionicons.glyphMap;
  color: string;
}) => (
  <View style={[styles.resultCard, { borderLeftColor: color }]}>
    <View style={styles.resultHeader}>
      <Ionicons name={icon} size={20} color={color} />
      <Text style={styles.resultTitle}>{title}</Text>
    </View>
    <Text style={[styles.resultValue, { color }]}>{value}</Text>
    <Text style={styles.resultDescription}>{description}</Text>
  </View>
);

const SwrMeter = ({ data, centerFreq, usable15, usable20, channelSpacing }: { 
  data: SwrPoint[]; 
  centerFreq: number;
  usable15: number;
  usable20: number;
  channelSpacing: number;
}) => {
  const width = Math.min(screenWidth - 32, 400);
  const height = 220;
  const padding = { top: 25, right: 15, bottom: 50, left: 45 };
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  if (!data || data.length === 0) return null;

  const minFreq = Math.min(...data.map(d => d.frequency));
  const maxFreq = Math.max(...data.map(d => d.frequency));
  const freqRange = maxFreq - minFreq;

  // Scale functions
  const xScale = (freq: number) => padding.left + ((freq - minFreq) / freqRange) * chartWidth;
  const yScale = (swr: number) => padding.top + chartHeight - ((Math.min(swr, 3) - 1) / 2) * chartHeight;

  // Create path for SWR curve
  const createSwrPath = () => {
    let pathData = '';
    data.forEach((point, index) => {
      const x = xScale(point.frequency);
      const y = yScale(point.swr);
      if (index === 0) {
        pathData += `M ${x} ${y}`;
      } else {
        pathData += ` L ${x} ${y}`;
      }
    });
    return pathData;
  };

  // Find usable bandwidth zones
  const getUsableZone = (threshold: number) => {
    const usablePoints = data.filter(p => p.swr <= threshold);
    if (usablePoints.length === 0) return null;
    const startFreq = Math.min(...usablePoints.map(p => p.frequency));
    const endFreq = Math.max(...usablePoints.map(p => p.frequency));
    return { start: xScale(startFreq), end: xScale(endFreq) };
  };

  const zone20 = getUsableZone(2.0);
  const zone15 = getUsableZone(1.5);

  // Channel markers (every 10 channels)
  const channelMarkers = data.filter(p => p.channel % 10 === 0);

  return (
    <View style={styles.swrContainer}>
      <Text style={styles.swrTitle}>SWR Bandwidth Meter</Text>
      <Text style={styles.swrSubtitle}>30 CH below to 20 CH above center ({channelSpacing} kHz/CH)</Text>
      <Svg width={width} height={height}>
        {/* Background */}
        <Rect x={padding.left} y={padding.top} width={chartWidth} height={chartHeight} fill="#1a1a1a" />
        
        {/* Usable bandwidth zones */}
        {zone20 && (
          <Rect 
            x={zone20.start} 
            y={padding.top} 
            width={zone20.end - zone20.start} 
            height={chartHeight} 
            fill="rgba(255, 193, 7, 0.15)" 
          />
        )}
        {zone15 && (
          <Rect 
            x={zone15.start} 
            y={padding.top} 
            width={zone15.end - zone15.start} 
            height={chartHeight} 
            fill="rgba(76, 175, 80, 0.2)" 
          />
        )}

        {/* Grid lines for SWR levels */}
        {[1.0, 1.5, 2.0, 2.5, 3.0].map((swr) => (
          <G key={swr}>
            <Line
              x1={padding.left}
              y1={yScale(swr)}
              x2={width - padding.right}
              y2={yScale(swr)}
              stroke={swr === 1.5 ? '#4CAF50' : swr === 2.0 ? '#FFC107' : '#333'}
              strokeWidth={swr === 1.5 || swr === 2.0 ? 1.5 : 1}
              strokeDasharray={swr === 1.5 || swr === 2.0 ? '0' : '3,3'}
            />
            <SvgText
              x={padding.left - 6}
              y={yScale(swr) + 4}
              fill={swr === 1.5 ? '#4CAF50' : swr === 2.0 ? '#FFC107' : '#666'}
              fontSize="10"
              textAnchor="end"
            >
              {swr.toFixed(1)}
            </SvgText>
          </G>
        ))}

        {/* Channel markers */}
        {channelMarkers.map((point) => (
          <G key={point.channel}>
            <Line
              x1={xScale(point.frequency)}
              y1={height - padding.bottom}
              x2={xScale(point.frequency)}
              y2={height - padding.bottom + 5}
              stroke={point.channel === 0 ? '#2196F3' : '#555'}
              strokeWidth={point.channel === 0 ? 2 : 1}
            />
            <SvgText
              x={xScale(point.frequency)}
              y={height - padding.bottom + 16}
              fill={point.channel === 0 ? '#2196F3' : '#666'}
              fontSize="9"
              textAnchor="middle"
            >
              {point.channel === 0 ? 'CTR' : (point.channel > 0 ? `+${point.channel}` : point.channel)}
            </SvgText>
          </G>
        ))}

        {/* Center frequency line */}
        <Line
          x1={xScale(centerFreq)}
          y1={padding.top}
          x2={xScale(centerFreq)}
          y2={height - padding.bottom}
          stroke="#2196F3"
          strokeWidth="2"
          strokeDasharray="4,4"
        />

        {/* SWR Curve */}
        <Path
          d={createSwrPath()}
          fill="none"
          stroke="#FF5722"
          strokeWidth="2.5"
        />

        {/* Frequency labels */}
        <SvgText x={padding.left} y={height - 5} fill="#888" fontSize="9" textAnchor="start">
          {minFreq.toFixed(3)}
        </SvgText>
        <SvgText x={xScale(centerFreq)} y={height - 32} fill="#2196F3" fontSize="9" textAnchor="middle">
          {centerFreq.toFixed(3)} MHz
        </SvgText>
        <SvgText x={width - padding.right} y={height - 5} fill="#888" fontSize="9" textAnchor="end">
          {maxFreq.toFixed(3)}
        </SvgText>

        {/* Y-axis label */}
        <SvgText x={10} y={height / 2 - 10} fill="#666" fontSize="10" textAnchor="middle" rotation="-90" origin={`10, ${height / 2 - 10}`}>
          SWR
        </SvgText>
      </Svg>

      {/* Legend */}
      <View style={styles.swrLegend}>
        <View style={styles.legendItem}>
          <View style={[styles.legendColor, { backgroundColor: 'rgba(76, 175, 80, 0.6)' }]} />
          <Text style={styles.legendText}>≤1.5:1 ({usable15.toFixed(3)} MHz)</Text>
        </View>
        <View style={styles.legendItem}>
          <View style={[styles.legendColor, { backgroundColor: 'rgba(255, 193, 7, 0.6)' }]} />
          <Text style={styles.legendText}>≤2.0:1 ({usable20.toFixed(3)} MHz)</Text>
        </View>
      </View>
    </View>
  );
};

const PolarPattern = ({ data, stackedData, isStacked }: { 
  data: { angle: number; magnitude: number }[]; 
  stackedData?: { angle: number; magnitude: number }[];
  isStacked: boolean;
}) => {
  const size = Math.min(screenWidth - 48, 300);
  const center = size / 2;
  const maxRadius = center - 30;

  const createPolarPath = (patternData: { angle: number; magnitude: number }[]) => {
    if (!patternData || patternData.length === 0) return '';
    let pathData = '';
    patternData.forEach((point, index) => {
      const angleRad = (point.angle - 90) * (Math.PI / 180);
      const radius = (point.magnitude / 100) * maxRadius;
      const x = center + radius * Math.cos(angleRad);
      const y = center + radius * Math.sin(angleRad);
      if (index === 0) {
        pathData += `M ${x} ${y}`;
      } else {
        pathData += ` L ${x} ${y}`;
      }
    });
    pathData += ' Z';
    return pathData;
  };

  return (
    <View style={styles.polarContainer}>
      <Text style={styles.polarTitle}>
        {isStacked ? 'Stacked Array Pattern' : 'Far Field Pattern'} (Azimuth)
      </Text>
      <Svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        {[0.25, 0.5, 0.75, 1].map((scale) => (
          <Circle key={scale} cx={center} cy={center} r={maxRadius * scale} stroke="#333" strokeWidth="1" fill="none" />
        ))}
        <Line x1={center} y1={30} x2={center} y2={size - 30} stroke="#333" strokeWidth="1" />
        <Line x1={30} y1={center} x2={size - 30} y2={center} stroke="#333" strokeWidth="1" />
        <SvgText x={center} y={16} fill="#888" fontSize="10" textAnchor="middle">0°</SvgText>
        <SvgText x={size - 8} y={center + 4} fill="#888" fontSize="10" textAnchor="middle">90°</SvgText>
        <SvgText x={center} y={size - 6} fill="#888" fontSize="10" textAnchor="middle">180°</SvgText>
        <SvgText x={10} y={center + 4} fill="#888" fontSize="10" textAnchor="middle">270°</SvgText>
        
        {/* Single antenna pattern (dimmed if stacked) */}
        <Path 
          d={createPolarPath(data)} 
          fill={isStacked ? 'rgba(100, 100, 100, 0.1)' : 'rgba(76, 175, 80, 0.3)'} 
          stroke={isStacked ? '#555' : '#4CAF50'} 
          strokeWidth={isStacked ? 1 : 2} 
          strokeDasharray={isStacked ? '4,4' : '0'}
        />
        
        {/* Stacked pattern */}
        {isStacked && stackedData && (
          <Path 
            d={createPolarPath(stackedData)} 
            fill="rgba(33, 150, 243, 0.3)" 
            stroke="#2196F3" 
            strokeWidth="2" 
          />
        )}
        
        <Circle cx={center} cy={center} r={4} fill={isStacked ? '#2196F3' : '#4CAF50'} />
      </Svg>
      {isStacked && (
        <View style={styles.patternLegend}>
          <View style={styles.legendItem}>
            <View style={[styles.legendColor, { backgroundColor: '#555', borderStyle: 'dashed' }]} />
            <Text style={styles.legendText}>Single Antenna</Text>
          </View>
          <View style={styles.legendItem}>
            <View style={[styles.legendColor, { backgroundColor: '#2196F3' }]} />
            <Text style={styles.legendText}>Stacked Array</Text>
          </View>
        </View>
      )}
      <Text style={styles.polarSubtitle}>Main lobe: 0° (Forward)</Text>
    </View>
  );
};

const Dropdown = ({ label, value, options, onChange }: {
  label: string;
  value: string;
  options: { value: string; label: string }[];
  onChange: (value: string) => void;
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const selectedOption = options.find(o => o.value === value);

  return (
    <View style={styles.dropdownContainer}>
      <Text style={styles.inputLabel}>{label}</Text>
      <TouchableOpacity 
        style={styles.dropdownButton} 
        onPress={() => setIsOpen(!isOpen)}
        activeOpacity={0.7}
      >
        <Text style={styles.dropdownButtonText}>{selectedOption?.label || 'Select...'}</Text>
        <Ionicons name={isOpen ? 'chevron-up' : 'chevron-down'} size={18} color="#888" />
      </TouchableOpacity>
      {isOpen && (
        <View style={styles.dropdownList}>
          <ScrollView style={styles.dropdownScroll} nestedScrollEnabled>
            {options.map((option) => (
              <TouchableOpacity
                key={option.value}
                style={[styles.dropdownItem, value === option.value && styles.dropdownItemSelected]}
                onPress={() => {
                  onChange(option.value);
                  setIsOpen(false);
                }}
              >
                <Text style={[styles.dropdownItemText, value === option.value && styles.dropdownItemTextSelected]}>
                  {option.label}
                </Text>
              </TouchableOpacity>
            ))}
          </ScrollView>
        </View>
      )}
    </View>
  );
};

const ElementInput = ({ element, index, onChange }: {
  element: ElementDimension;
  index: number;
  onChange: (index: number, field: keyof ElementDimension, value: string) => void;
}) => {
  const getTitle = () => {
    if (element.element_type === 'reflector') return 'Reflector';
    if (element.element_type === 'driven') return 'Driven Element';
    return `Director ${index - 1}`;
  };

  const getColor = () => {
    if (element.element_type === 'reflector') return '#FF9800';
    if (element.element_type === 'driven') return '#4CAF50';
    return '#2196F3';
  };

  return (
    <View style={[styles.elementCard, { borderLeftColor: getColor() }]}>
      <Text style={[styles.elementTitle, { color: getColor() }]}>{getTitle()}</Text>
      <View style={styles.elementRow}>
        <View style={styles.elementField}>
          <Text style={styles.elementLabel}>Length (in)</Text>
          <TextInput
            style={styles.elementInput}
            value={element.length}
            onChangeText={(v) => onChange(index, 'length', v)}
            keyboardType="decimal-pad"
            placeholder="216"
            placeholderTextColor="#555"
          />
        </View>
        <View style={styles.elementField}>
          <Text style={styles.elementLabel}>Diameter (in)</Text>
          <TextInput
            style={styles.elementInput}
            value={element.diameter}
            onChangeText={(v) => onChange(index, 'diameter', v)}
            keyboardType="decimal-pad"
            placeholder="0.5"
            placeholderTextColor="#555"
          />
        </View>
      </View>
      {element.element_type !== 'reflector' && (
        <View style={styles.elementField}>
          <Text style={styles.elementLabel}>Position from Reflector (in)</Text>
          <TextInput
            style={styles.elementInput}
            value={element.position}
            onChangeText={(v) => onChange(index, 'position', v)}
            keyboardType="decimal-pad"
            placeholder="48"
            placeholderTextColor="#555"
          />
        </View>
      )}
    </View>
  );
};

const StackingCard = ({ stacking, onChange }: {
  stacking: StackingConfig;
  onChange: (field: keyof StackingConfig, value: any) => void;
}) => {
  return (
    <View style={styles.section}>
      <View style={styles.sectionHeaderRow}>
        <Text style={styles.sectionTitle}>
          <Ionicons name="layers-outline" size={16} color="#9C27B0" /> Antenna Stacking
        </Text>
        <Switch
          value={stacking.enabled}
          onValueChange={(v) => onChange('enabled', v)}
          trackColor={{ false: '#333', true: '#9C27B0' }}
          thumbColor={stacking.enabled ? '#fff' : '#888'}
        />
      </View>
      
      {stacking.enabled && (
        <>
          {/* Orientation */}
          <Text style={styles.inputLabel}>Stack Orientation</Text>
          <View style={styles.orientationToggle}>
            <TouchableOpacity
              style={[styles.orientBtn, stacking.orientation === 'vertical' && styles.orientBtnActive]}
              onPress={() => onChange('orientation', 'vertical')}
            >
              <Ionicons name="swap-vertical" size={20} color={stacking.orientation === 'vertical' ? '#fff' : '#888'} />
              <Text style={[styles.orientBtnText, stacking.orientation === 'vertical' && styles.orientBtnTextActive]}>Vertical</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.orientBtn, stacking.orientation === 'horizontal' && styles.orientBtnActive]}
              onPress={() => onChange('orientation', 'horizontal')}
            >
              <Ionicons name="swap-horizontal" size={20} color={stacking.orientation === 'horizontal' ? '#fff' : '#888'} />
              <Text style={[styles.orientBtnText, stacking.orientation === 'horizontal' && styles.orientBtnTextActive]}>Horizontal</Text>
            </TouchableOpacity>
          </View>

          {/* Number of antennas */}
          <Dropdown
            label="Number of Antennas"
            value={stacking.num_antennas.toString()}
            options={[2,3,4,5,6,7,8].map(n => ({ value: n.toString(), label: `${n} Antennas` }))}
            onChange={(v) => onChange('num_antennas', parseInt(v))}
          />

          {/* Spacing */}
          <View style={styles.rowInput}>
            <View style={styles.flexInput}>
              <Text style={styles.inputLabel}>
                {stacking.orientation === 'vertical' ? 'Vertical Spacing (between antennas)' : 'Horizontal Spacing'}
              </Text>
              <TextInput
                style={styles.input}
                value={stacking.spacing}
                onChangeText={(v) => onChange('spacing', v)}
                keyboardType="decimal-pad"
                placeholder="20"
                placeholderTextColor="#555"
              />
            </View>
            <View style={styles.unitToggle}>
              <TouchableOpacity
                style={[styles.unitBtn, stacking.spacing_unit === 'ft' && styles.unitBtnActive]}
                onPress={() => onChange('spacing_unit', 'ft')}
              >
                <Text style={[styles.unitBtnText, stacking.spacing_unit === 'ft' && styles.unitBtnTextActive]}>ft</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.unitBtn, stacking.spacing_unit === 'inches' && styles.unitBtnActive]}
                onPress={() => onChange('spacing_unit', 'inches')}
              >
                <Text style={[styles.unitBtnText, stacking.spacing_unit === 'inches' && styles.unitBtnTextActive]}>in</Text>
              </TouchableOpacity>
            </View>
          </View>

          <Text style={styles.stackingHint}>
            {stacking.orientation === 'vertical' 
              ? 'Enter height above first antenna position'
              : 'Enter horizontal distance between antennas'}
          </Text>
        </>
      )}
    </View>
  );
};

const StackingResults = ({ info, baseGain, stackedGain }: { 
  info: StackingInfo; 
  baseGain: number;
  stackedGain: number;
}) => (
  <View style={styles.stackingResults}>
    <Text style={styles.stackingResultsTitle}>
      <Ionicons name="layers" size={16} color="#9C27B0" /> Stacking Results ({info.num_antennas}x {info.orientation})
    </Text>
    <View style={styles.stackingGrid}>
      <View style={styles.stackingItem}>
        <Text style={styles.stackingLabel}>Base Gain</Text>
        <Text style={styles.stackingValue}>{baseGain} dBi</Text>
      </View>
      <View style={styles.stackingItem}>
        <Text style={styles.stackingLabel}>Stacked Gain</Text>
        <Text style={[styles.stackingValue, { color: '#9C27B0' }]}>{stackedGain} dBi</Text>
      </View>
      <View style={styles.stackingItem}>
        <Text style={styles.stackingLabel}>Gain Increase</Text>
        <Text style={[styles.stackingValue, { color: '#4CAF50' }]}>+{info.gain_increase_db} dB</Text>
      </View>
      <View style={styles.stackingItem}>
        <Text style={styles.stackingLabel}>Mult. Factor</Text>
        <Text style={styles.stackingValue}>{info.stacked_multiplication_factor}x</Text>
      </View>
      <View style={styles.stackingItem}>
        <Text style={styles.stackingLabel}>H Beamwidth</Text>
        <Text style={styles.stackingValue}>{info.new_beamwidth_h}°</Text>
      </View>
      <View style={styles.stackingItem}>
        <Text style={styles.stackingLabel}>V Beamwidth</Text>
        <Text style={styles.stackingValue}>{info.new_beamwidth_v}°</Text>
      </View>
    </View>
    <View style={styles.stackingInfoRow}>
      <Text style={styles.stackingInfoLabel}>Spacing: {info.spacing} {info.spacing_unit} ({info.spacing_wavelengths}λ)</Text>
      <Text style={styles.stackingInfoLabel}>Optimal: ~{info.optimal_spacing_ft} ft (0.65λ)</Text>
    </View>
    {info.total_height_ft && (
      <Text style={styles.stackingInfoLabel}>Total array height: {info.total_height_ft} ft from ground</Text>
    )}
    {info.total_width_ft && (
      <Text style={styles.stackingInfoLabel}>Total array width: {info.total_width_ft} ft</Text>
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
    height_from_ground: '35',
    height_unit: 'ft',
    boom_diameter: '2',
    boom_unit: 'inches',
    band: '11m_cb',
    frequency_mhz: '27.185',
    stacking: {
      enabled: false,
      orientation: 'vertical',
      num_antennas: 2,
      spacing: '20',
      spacing_unit: 'ft',
    },
  });

  const [results, setResults] = useState<AntennaOutput | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showResults, setShowResults] = useState(false);

  const updateElementCount = (newCount: number) => {
    const count = Math.max(2, Math.min(20, newCount));
    const newElements: ElementDimension[] = [];
    
    newElements.push(
      inputs.elements.find(e => e.element_type === 'reflector') || 
      { element_type: 'reflector', length: '216', diameter: '0.5', position: '0' }
    );
    
    newElements.push(
      inputs.elements.find(e => e.element_type === 'driven') || 
      { element_type: 'driven', length: '204', diameter: '0.5', position: '48' }
    );
    
    const numDirectors = count - 2;
    const existingDirectors = inputs.elements.filter(e => e.element_type === 'director');
    
    for (let i = 0; i < numDirectors; i++) {
      if (existingDirectors[i]) {
        newElements.push(existingDirectors[i]);
      } else {
        const basePosition = 96 + (i * 48);
        const baseLength = 195 - (i * 3);
        newElements.push({
          element_type: 'director',
          length: baseLength.toString(),
          diameter: '0.5',
          position: basePosition.toString(),
        });
      }
    }
    
    setInputs(prev => ({ ...prev, num_elements: count, elements: newElements }));
  };

  const updateElement = (index: number, field: keyof ElementDimension, value: string) => {
    setInputs(prev => {
      const newElements = [...prev.elements];
      newElements[index] = { ...newElements[index], [field]: value };
      return { ...prev, elements: newElements };
    });
  };

  const updateStacking = (field: keyof StackingConfig, value: any) => {
    setInputs(prev => ({
      ...prev,
      stacking: { ...prev.stacking, [field]: value }
    }));
  };

  const handleBandChange = (bandId: string) => {
    const band = BANDS.find(b => b.id === bandId);
    setInputs(prev => ({
      ...prev,
      band: bandId,
      frequency_mhz: band ? band.center.toString() : prev.frequency_mhz,
    }));
  };

  const calculateAntenna = useCallback(async () => {
    for (const elem of inputs.elements) {
      if (!elem.length || parseFloat(elem.length) <= 0) {
        setError(`Please enter valid length for ${elem.element_type}`);
        return;
      }
      if (!elem.diameter || parseFloat(elem.diameter) <= 0) {
        setError(`Please enter valid diameter for ${elem.element_type}`);
        return;
      }
    }

    if (!inputs.height_from_ground || parseFloat(inputs.height_from_ground) <= 0) {
      setError('Height from ground must be positive');
      return;
    }
    if (!inputs.boom_diameter || parseFloat(inputs.boom_diameter) <= 0) {
      setError('Boom diameter must be positive');
      return;
    }
    if (inputs.stacking.enabled && (!inputs.stacking.spacing || parseFloat(inputs.stacking.spacing) <= 0)) {
      setError('Stacking spacing must be positive');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${BACKEND_URL}/api/calculate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          num_elements: inputs.num_elements,
          elements: inputs.elements.map(e => ({
            element_type: e.element_type,
            length: parseFloat(e.length),
            diameter: parseFloat(e.diameter),
            position: parseFloat(e.position) || 0,
          })),
          height_from_ground: parseFloat(inputs.height_from_ground),
          height_unit: inputs.height_unit,
          boom_diameter: parseFloat(inputs.boom_diameter),
          boom_unit: inputs.boom_unit,
          band: inputs.band,
          frequency_mhz: parseFloat(inputs.frequency_mhz) || null,
          stacking: inputs.stacking.enabled ? {
            enabled: true,
            orientation: inputs.stacking.orientation,
            num_antennas: inputs.stacking.num_antennas,
            spacing: parseFloat(inputs.stacking.spacing),
            spacing_unit: inputs.stacking.spacing_unit,
          } : null,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Calculation failed');
      }

      const data: AntennaOutput = await response.json();
      setResults(data);
      setShowResults(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  }, [inputs]);

  const resetForm = () => {
    setInputs({
      num_elements: 3,
      elements: [
        { element_type: 'reflector', length: '216', diameter: '0.5', position: '0' },
        { element_type: 'driven', length: '204', diameter: '0.5', position: '48' },
        { element_type: 'director', length: '195', diameter: '0.5', position: '96' },
      ],
      height_from_ground: '35',
      height_unit: 'ft',
      boom_diameter: '2',
      boom_unit: 'inches',
      band: '11m_cb',
      frequency_mhz: '27.185',
      stacking: { enabled: false, orientation: 'vertical', num_antennas: 2, spacing: '20', spacing_unit: 'ft' },
    });
    setResults(null);
    setShowResults(false);
    setError(null);
  };

  const elementOptions = Array.from({ length: 19 }, (_, i) => ({
    value: (i + 2).toString(),
    label: `${i + 2} Elements`,
  }));

  const bandOptions = BANDS.map(b => ({ value: b.id, label: b.name }));

  return (
    <SafeAreaView style={styles.container}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={styles.flex}>
        <ScrollView style={styles.scrollView} contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
          {/* Header */}
          <View style={styles.header}>
            <Ionicons name="radio-outline" size={30} color="#4CAF50" />
            <Text style={styles.headerTitle}>Antenna Calculator</Text>
            <Text style={styles.headerSubtitle}>Yagi-Uda Analysis with Stacking</Text>
          </View>

          {/* Band Selection */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>
              <Ionicons name="radio" size={14} color="#4CAF50" /> Band Selection
            </Text>
            <Dropdown label="Operating Band" value={inputs.band} options={bandOptions} onChange={handleBandChange} />
            <View style={styles.inputGroup}>
              <Text style={styles.inputLabel}>Center Frequency (MHz)</Text>
              <TextInput
                style={styles.input}
                value={inputs.frequency_mhz}
                onChangeText={(v) => setInputs(prev => ({ ...prev, frequency_mhz: v }))}
                keyboardType="decimal-pad"
                placeholder="27.185"
                placeholderTextColor="#555"
              />
            </View>
          </View>

          {/* Element Configuration */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>
              <Ionicons name="git-branch-outline" size={14} color="#4CAF50" /> Element Configuration
            </Text>
            <Dropdown
              label="Number of Elements"
              value={inputs.num_elements.toString()}
              options={elementOptions}
              onChange={(v) => updateElementCount(parseInt(v))}
            />
            {inputs.elements.map((elem, index) => (
              <ElementInput key={`${elem.element_type}-${index}`} element={elem} index={index} onChange={updateElement} />
            ))}
          </View>

          {/* Physical Setup */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>
              <Ionicons name="construct-outline" size={14} color="#4CAF50" /> Physical Setup
            </Text>
            <View style={styles.rowInput}>
              <View style={styles.flexInput}>
                <Text style={styles.inputLabel}>Height from Ground</Text>
                <TextInput
                  style={styles.input}
                  value={inputs.height_from_ground}
                  onChangeText={(v) => setInputs(prev => ({ ...prev, height_from_ground: v }))}
                  keyboardType="decimal-pad"
                  placeholder="35"
                  placeholderTextColor="#555"
                />
              </View>
              <View style={styles.unitToggle}>
                <TouchableOpacity style={[styles.unitBtn, inputs.height_unit === 'ft' && styles.unitBtnActive]} onPress={() => setInputs(prev => ({ ...prev, height_unit: 'ft' }))}>
                  <Text style={[styles.unitBtnText, inputs.height_unit === 'ft' && styles.unitBtnTextActive]}>ft</Text>
                </TouchableOpacity>
                <TouchableOpacity style={[styles.unitBtn, inputs.height_unit === 'inches' && styles.unitBtnActive]} onPress={() => setInputs(prev => ({ ...prev, height_unit: 'inches' }))}>
                  <Text style={[styles.unitBtnText, inputs.height_unit === 'inches' && styles.unitBtnTextActive]}>in</Text>
                </TouchableOpacity>
              </View>
            </View>
            <View style={styles.rowInput}>
              <View style={styles.flexInput}>
                <Text style={styles.inputLabel}>Boom Diameter</Text>
                <TextInput
                  style={styles.input}
                  value={inputs.boom_diameter}
                  onChangeText={(v) => setInputs(prev => ({ ...prev, boom_diameter: v }))}
                  keyboardType="decimal-pad"
                  placeholder="2"
                  placeholderTextColor="#555"
                />
              </View>
              <View style={styles.unitToggle}>
                <TouchableOpacity style={[styles.unitBtn, inputs.boom_unit === 'mm' && styles.unitBtnActive]} onPress={() => setInputs(prev => ({ ...prev, boom_unit: 'mm' }))}>
                  <Text style={[styles.unitBtnText, inputs.boom_unit === 'mm' && styles.unitBtnTextActive]}>mm</Text>
                </TouchableOpacity>
                <TouchableOpacity style={[styles.unitBtn, inputs.boom_unit === 'inches' && styles.unitBtnActive]} onPress={() => setInputs(prev => ({ ...prev, boom_unit: 'inches' }))}>
                  <Text style={[styles.unitBtnText, inputs.boom_unit === 'inches' && styles.unitBtnTextActive]}>in</Text>
                </TouchableOpacity>
              </View>
            </View>
          </View>

          {/* Stacking */}
          <StackingCard stacking={inputs.stacking} onChange={updateStacking} />

          {/* Error */}
          {error && (
            <View style={styles.errorContainer}>
              <Ionicons name="alert-circle" size={18} color="#f44336" />
              <Text style={styles.errorText}>{error}</Text>
            </View>
          )}

          {/* Calculate Button */}
          <TouchableOpacity style={[styles.calculateButton, loading && styles.buttonDisabled]} onPress={calculateAntenna} disabled={loading} activeOpacity={0.8}>
            {loading ? <ActivityIndicator color="#fff" size="small" /> : (
              <><Ionicons name="calculator" size={20} color="#fff" /><Text style={styles.calculateButtonText}>Calculate Parameters</Text></>
            )}
          </TouchableOpacity>

          {/* Results */}
          {showResults && results && (
            <View style={styles.resultsSection}>
              <View style={styles.resultsHeader}>
                <Text style={styles.sectionTitle}><Ionicons name="analytics" size={14} color="#4CAF50" /> Analysis Results</Text>
                <TouchableOpacity onPress={resetForm} style={styles.resetButton}>
                  <Ionicons name="refresh" size={16} color="#888" />
                  <Text style={styles.resetText}>Reset</Text>
                </TouchableOpacity>
              </View>

              <View style={styles.bandInfoCard}>
                <Text style={styles.bandInfoTitle}>{results.band_info.name}</Text>
                <Text style={styles.bandInfoText}>Center: {results.center_frequency.toFixed(3)} MHz | {results.band_info.channel_spacing_khz} kHz/CH</Text>
              </View>

              {/* Stacking Results */}
              {results.stacking_enabled && results.stacking_info && (
                <StackingResults info={results.stacking_info} baseGain={results.gain_dbi} stackedGain={results.stacked_gain_dbi!} />
              )}

              {/* SWR Bandwidth Meter */}
              <SwrMeter 
                data={results.swr_curve} 
                centerFreq={results.center_frequency}
                usable15={results.usable_bandwidth_1_5}
                usable20={results.usable_bandwidth_2_0}
                channelSpacing={results.band_info.channel_spacing_khz}
              />

              <ResultCard title="Gain" value={`${results.stacking_enabled ? results.stacked_gain_dbi : results.gain_dbi} dBi`} description={results.gain_description} icon="trending-up" color="#4CAF50" />
              <ResultCard title="SWR at Center" value={`${results.swr}:1`} description={results.swr_description} icon="pulse" color="#2196F3" />
              <ResultCard title="F/B Ratio" value={`${results.fb_ratio} dB`} description={results.fb_ratio_description} icon="swap-horizontal" color="#9C27B0" />
              <ResultCard title="Beamwidth" value={`H: ${results.beamwidth_h}° / V: ${results.beamwidth_v}°`} description={results.beamwidth_description} icon="radio-button-on" color="#FF9800" />
              <ResultCard title="Usable BW (≤1.5:1)" value={`${results.usable_bandwidth_1_5.toFixed(3)} MHz`} description={`At 2:1: ${results.usable_bandwidth_2_0.toFixed(3)} MHz`} icon="resize" color="#00BCD4" />
              <ResultCard title="Efficiency" value={`${results.antenna_efficiency}%`} description={results.efficiency_description} icon="speedometer" color="#8BC34A" />

              <PolarPattern 
                data={results.far_field_pattern} 
                stackedData={results.stacked_pattern || undefined}
                isStacked={results.stacking_enabled}
              />
            </View>
          )}
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#121212' },
  flex: { flex: 1 },
  scrollView: { flex: 1 },
  scrollContent: { padding: 14, paddingBottom: 40 },
  header: { alignItems: 'center', marginBottom: 14, paddingVertical: 10 },
  headerTitle: { fontSize: 24, fontWeight: 'bold', color: '#fff', marginTop: 4 },
  headerSubtitle: { fontSize: 12, color: '#888', marginTop: 2 },
  section: { backgroundColor: '#1a1a1a', borderRadius: 12, padding: 12, marginBottom: 12 },
  sectionTitle: { fontSize: 15, fontWeight: '600', color: '#fff', marginBottom: 10 },
  sectionHeaderRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 },
  inputGroup: { marginBottom: 10 },
  inputLabel: { fontSize: 12, color: '#aaa', marginBottom: 5 },
  input: { backgroundColor: '#252525', borderRadius: 8, padding: 11, fontSize: 14, color: '#fff', borderWidth: 1, borderColor: '#333' },
  rowInput: { flexDirection: 'row', alignItems: 'flex-end', marginBottom: 10, gap: 8 },
  flexInput: { flex: 1 },
  unitToggle: { flexDirection: 'row', backgroundColor: '#252525', borderRadius: 8, overflow: 'hidden' },
  unitBtn: { paddingVertical: 11, paddingHorizontal: 12, minWidth: 40 },
  unitBtnActive: { backgroundColor: '#4CAF50' },
  unitBtnText: { fontSize: 13, color: '#888', textAlign: 'center' },
  unitBtnTextActive: { color: '#fff', fontWeight: '600' },
  orientationToggle: { flexDirection: 'row', gap: 8, marginBottom: 12 },
  orientBtn: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', backgroundColor: '#252525', borderRadius: 8, padding: 12, gap: 6 },
  orientBtnActive: { backgroundColor: '#9C27B0' },
  orientBtnText: { fontSize: 13, color: '#888' },
  orientBtnTextActive: { color: '#fff', fontWeight: '600' },
  stackingHint: { fontSize: 11, color: '#666', fontStyle: 'italic', marginTop: 4 },
  dropdownContainer: { marginBottom: 10 },
  dropdownButton: { backgroundColor: '#252525', borderRadius: 8, padding: 11, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', borderWidth: 1, borderColor: '#333' },
  dropdownButtonText: { fontSize: 14, color: '#fff' },
  dropdownList: { backgroundColor: '#2a2a2a', borderRadius: 8, marginTop: 4, maxHeight: 180, borderWidth: 1, borderColor: '#333' },
  dropdownScroll: { maxHeight: 180 },
  dropdownItem: { padding: 11, borderBottomWidth: 1, borderBottomColor: '#333' },
  dropdownItemSelected: { backgroundColor: '#333' },
  dropdownItemText: { fontSize: 13, color: '#ccc' },
  dropdownItemTextSelected: { color: '#4CAF50', fontWeight: '500' },
  elementCard: { backgroundColor: '#222', borderRadius: 8, padding: 10, marginTop: 8, borderLeftWidth: 3 },
  elementTitle: { fontSize: 13, fontWeight: '600', marginBottom: 8 },
  elementRow: { flexDirection: 'row', gap: 8 },
  elementField: { flex: 1, marginBottom: 6 },
  elementLabel: { fontSize: 10, color: '#888', marginBottom: 3 },
  elementInput: { backgroundColor: '#1a1a1a', borderRadius: 6, padding: 9, fontSize: 13, color: '#fff', borderWidth: 1, borderColor: '#333' },
  errorContainer: { flexDirection: 'row', alignItems: 'center', backgroundColor: 'rgba(244, 67, 54, 0.1)', padding: 10, borderRadius: 8, marginBottom: 12 },
  errorText: { color: '#f44336', marginLeft: 8, flex: 1, fontSize: 12 },
  calculateButton: { backgroundColor: '#4CAF50', flexDirection: 'row', alignItems: 'center', justifyContent: 'center', padding: 14, borderRadius: 10, marginBottom: 14, gap: 8 },
  buttonDisabled: { opacity: 0.7 },
  calculateButtonText: { color: '#fff', fontSize: 16, fontWeight: '600' },
  resultsSection: { marginBottom: 14 },
  resultsHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 },
  resetButton: { flexDirection: 'row', alignItems: 'center', padding: 6, gap: 4 },
  resetText: { color: '#888', fontSize: 12 },
  bandInfoCard: { backgroundColor: '#1a1a1a', borderRadius: 10, padding: 10, marginBottom: 10, alignItems: 'center' },
  bandInfoTitle: { fontSize: 15, fontWeight: '600', color: '#4CAF50' },
  bandInfoText: { fontSize: 12, color: '#888', marginTop: 3 },
  resultCard: { backgroundColor: '#1a1a1a', borderRadius: 10, padding: 12, marginBottom: 8, borderLeftWidth: 3 },
  resultHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 4, gap: 6 },
  resultTitle: { fontSize: 11, color: '#888', textTransform: 'uppercase', letterSpacing: 0.5 },
  resultValue: { fontSize: 24, fontWeight: 'bold', marginBottom: 2 },
  resultDescription: { fontSize: 11, color: '#888' },
  swrContainer: { backgroundColor: '#1a1a1a', borderRadius: 12, padding: 12, marginBottom: 10, alignItems: 'center' },
  swrTitle: { fontSize: 14, fontWeight: '600', color: '#fff', marginBottom: 2 },
  swrSubtitle: { fontSize: 10, color: '#666', marginBottom: 10 },
  swrLegend: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'center', marginTop: 8, gap: 12 },
  legendItem: { flexDirection: 'row', alignItems: 'center', gap: 5 },
  legendColor: { width: 12, height: 12, borderRadius: 2 },
  legendText: { fontSize: 10, color: '#888' },
  polarContainer: { backgroundColor: '#1a1a1a', borderRadius: 12, padding: 12, alignItems: 'center', marginTop: 6 },
  polarTitle: { fontSize: 14, fontWeight: '600', color: '#fff', marginBottom: 10 },
  polarSubtitle: { fontSize: 10, color: '#666', marginTop: 8 },
  patternLegend: { flexDirection: 'row', gap: 16, marginTop: 8 },
  stackingResults: { backgroundColor: '#1a1a1a', borderRadius: 12, padding: 12, marginBottom: 10, borderWidth: 1, borderColor: '#9C27B0' },
  stackingResultsTitle: { fontSize: 14, fontWeight: '600', color: '#9C27B0', marginBottom: 10 },
  stackingGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  stackingItem: { width: '30%', backgroundColor: '#252525', borderRadius: 8, padding: 8, alignItems: 'center' },
  stackingLabel: { fontSize: 9, color: '#888', marginBottom: 2 },
  stackingValue: { fontSize: 14, fontWeight: '600', color: '#fff' },
  stackingInfoRow: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 10 },
  stackingInfoLabel: { fontSize: 10, color: '#888' },
});
