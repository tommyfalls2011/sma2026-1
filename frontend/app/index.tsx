import React, { useState, useCallback, useEffect } from 'react';
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

interface AntennaInput {
  num_elements: number;
  elements: ElementDimension[];
  height_from_ground: string;
  height_unit: 'ft' | 'inches';
  boom_diameter: string;
  boom_unit: 'mm' | 'inches';
  band: string;
  frequency_mhz: string;
}

interface SwrPoint {
  frequency: number;
  swr: number;
}

interface AntennaOutput {
  swr: number;
  swr_description: string;
  fb_ratio: number;
  fb_ratio_description: string;
  beamwidth: number;
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
  band_info: { name: string; center: number; start: number; end: number };
  input_summary: Record<string, any>;
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
      <Ionicons name={icon} size={22} color={color} />
      <Text style={styles.resultTitle}>{title}</Text>
    </View>
    <Text style={[styles.resultValue, { color }]}>{value}</Text>
    <Text style={styles.resultDescription}>{description}</Text>
  </View>
);

const SwrMeter = ({ data, centerFreq, usable15, usable20 }: { 
  data: SwrPoint[]; 
  centerFreq: number;
  usable15: number;
  usable20: number;
}) => {
  const width = Math.min(screenWidth - 32, 380);
  const height = 200;
  const padding = { top: 20, right: 20, bottom: 40, left: 50 };
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

  return (
    <View style={styles.swrContainer}>
      <Text style={styles.swrTitle}>SWR Bandwidth Meter</Text>
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

        {/* Grid lines */}
        {[1.0, 1.5, 2.0, 2.5, 3.0].map((swr) => (
          <G key={swr}>
            <Line
              x1={padding.left}
              y1={yScale(swr)}
              x2={width - padding.right}
              y2={yScale(swr)}
              stroke={swr === 1.5 ? '#4CAF50' : swr === 2.0 ? '#FFC107' : '#333'}
              strokeWidth={swr === 1.5 || swr === 2.0 ? 1.5 : 1}
              strokeDasharray={swr === 1.5 || swr === 2.0 ? '0' : '4,4'}
            />
            <SvgText
              x={padding.left - 8}
              y={yScale(swr) + 4}
              fill="#888"
              fontSize="11"
              textAnchor="end"
            >
              {swr.toFixed(1)}
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

        {/* X-axis labels */}
        <SvgText x={padding.left} y={height - 8} fill="#888" fontSize="10" textAnchor="start">
          {minFreq.toFixed(2)}
        </SvgText>
        <SvgText x={xScale(centerFreq)} y={height - 8} fill="#2196F3" fontSize="10" textAnchor="middle">
          {centerFreq.toFixed(3)}
        </SvgText>
        <SvgText x={width - padding.right} y={height - 8} fill="#888" fontSize="10" textAnchor="end">
          {maxFreq.toFixed(2)}
        </SvgText>
        <SvgText x={width / 2} y={height - 22} fill="#666" fontSize="11" textAnchor="middle">
          Frequency (MHz)
        </SvgText>

        {/* Y-axis label */}
        <SvgText x={12} y={height / 2} fill="#666" fontSize="11" textAnchor="middle" rotation="-90" origin={`12, ${height / 2}`}>
          SWR
        </SvgText>
      </Svg>

      {/* Legend */}
      <View style={styles.swrLegend}>
        <View style={styles.legendItem}>
          <View style={[styles.legendColor, { backgroundColor: 'rgba(76, 175, 80, 0.5)' }]} />
          <Text style={styles.legendText}>Usable ≤1.5:1 ({usable15.toFixed(3)} MHz)</Text>
        </View>
        <View style={styles.legendItem}>
          <View style={[styles.legendColor, { backgroundColor: 'rgba(255, 193, 7, 0.5)' }]} />
          <Text style={styles.legendText}>Usable ≤2.0:1 ({usable20.toFixed(3)} MHz)</Text>
        </View>
      </View>
    </View>
  );
};

const PolarPattern = ({ data }: { data: { angle: number; magnitude: number }[] }) => {
  const size = Math.min(screenWidth - 48, 300);
  const center = size / 2;
  const maxRadius = center - 30;

  const createPolarPath = () => {
    if (!data || data.length === 0) return '';
    let pathData = '';
    data.forEach((point, index) => {
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
      <Text style={styles.polarTitle}>Far Field Pattern (Polar View)</Text>
      <Svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        {[0.25, 0.5, 0.75, 1].map((scale) => (
          <Circle key={scale} cx={center} cy={center} r={maxRadius * scale} stroke="#333" strokeWidth="1" fill="none" />
        ))}
        <Line x1={center} y1={30} x2={center} y2={size - 30} stroke="#333" strokeWidth="1" />
        <Line x1={30} y1={center} x2={size - 30} y2={center} stroke="#333" strokeWidth="1" />
        <SvgText x={center} y={18} fill="#888" fontSize="11" textAnchor="middle">0°</SvgText>
        <SvgText x={size - 10} y={center + 4} fill="#888" fontSize="11" textAnchor="middle">90°</SvgText>
        <SvgText x={center} y={size - 8} fill="#888" fontSize="11" textAnchor="middle">180°</SvgText>
        <SvgText x={12} y={center + 4} fill="#888" fontSize="11" textAnchor="middle">270°</SvgText>
        <Path d={createPolarPath()} fill="rgba(76, 175, 80, 0.3)" stroke="#4CAF50" strokeWidth="2" />
        <Circle cx={center} cy={center} r={4} fill="#4CAF50" />
      </Svg>
      <Text style={styles.polarSubtitle}>Main lobe direction: 0° (Forward)</Text>
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
        <Ionicons name={isOpen ? 'chevron-up' : 'chevron-down'} size={20} color="#888" />
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
          <Text style={styles.elementLabel}>Length (inches)</Text>
          <TextInput
            style={styles.elementInput}
            value={element.length}
            onChangeText={(v) => onChange(index, 'length', v)}
            keyboardType="decimal-pad"
            placeholder="e.g., 216"
            placeholderTextColor="#555"
          />
        </View>
        <View style={styles.elementField}>
          <Text style={styles.elementLabel}>Diameter (inches)</Text>
          <TextInput
            style={styles.elementInput}
            value={element.diameter}
            onChangeText={(v) => onChange(index, 'diameter', v)}
            keyboardType="decimal-pad"
            placeholder="e.g., 0.5"
            placeholderTextColor="#555"
          />
        </View>
      </View>
      {element.element_type !== 'reflector' && (
        <View style={styles.elementField}>
          <Text style={styles.elementLabel}>Position from Reflector (inches)</Text>
          <TextInput
            style={styles.elementInput}
            value={element.position}
            onChangeText={(v) => onChange(index, 'position', v)}
            keyboardType="decimal-pad"
            placeholder="e.g., 48"
            placeholderTextColor="#555"
          />
        </View>
      )}
    </View>
  );
};

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
  });

  const [results, setResults] = useState<AntennaOutput | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showResults, setShowResults] = useState(false);

  // Update elements when num_elements changes
  const updateElementCount = (newCount: number) => {
    const count = Math.max(2, Math.min(20, newCount));
    const newElements: ElementDimension[] = [];
    
    // Always add reflector
    newElements.push(
      inputs.elements.find(e => e.element_type === 'reflector') || 
      { element_type: 'reflector', length: '216', diameter: '0.5', position: '0' }
    );
    
    // Always add driven element
    newElements.push(
      inputs.elements.find(e => e.element_type === 'driven') || 
      { element_type: 'driven', length: '204', diameter: '0.5', position: '48' }
    );
    
    // Add directors
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

  const handleBandChange = (bandId: string) => {
    const band = BANDS.find(b => b.id === bandId);
    setInputs(prev => ({
      ...prev,
      band: bandId,
      frequency_mhz: band ? band.center.toString() : prev.frequency_mhz,
    }));
  };

  const calculateAntenna = useCallback(async () => {
    // Validate inputs
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
            <Ionicons name="radio-outline" size={32} color="#4CAF50" />
            <Text style={styles.headerTitle}>Antenna Calculator</Text>
            <Text style={styles.headerSubtitle}>Yagi-Uda Antenna Analysis</Text>
          </View>

          {/* Band Selection */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>
              <Ionicons name="radio" size={16} color="#4CAF50" /> Band Selection
            </Text>
            <Dropdown
              label="Operating Band"
              value={inputs.band}
              options={bandOptions}
              onChange={handleBandChange}
            />
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
              <Ionicons name="git-branch-outline" size={16} color="#4CAF50" /> Element Configuration
            </Text>
            <Dropdown
              label="Number of Elements"
              value={inputs.num_elements.toString()}
              options={elementOptions}
              onChange={(v) => updateElementCount(parseInt(v))}
            />
            
            {inputs.elements.map((elem, index) => (
              <ElementInput
                key={`${elem.element_type}-${index}`}
                element={elem}
                index={index}
                onChange={updateElement}
              />
            ))}
          </View>

          {/* Physical Setup */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>
              <Ionicons name="construct-outline" size={16} color="#4CAF50" /> Physical Setup
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
                <TouchableOpacity
                  style={[styles.unitBtn, inputs.height_unit === 'ft' && styles.unitBtnActive]}
                  onPress={() => setInputs(prev => ({ ...prev, height_unit: 'ft' }))}
                >
                  <Text style={[styles.unitBtnText, inputs.height_unit === 'ft' && styles.unitBtnTextActive]}>ft</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={[styles.unitBtn, inputs.height_unit === 'inches' && styles.unitBtnActive]}
                  onPress={() => setInputs(prev => ({ ...prev, height_unit: 'inches' }))}
                >
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
                <TouchableOpacity
                  style={[styles.unitBtn, inputs.boom_unit === 'mm' && styles.unitBtnActive]}
                  onPress={() => setInputs(prev => ({ ...prev, boom_unit: 'mm' }))}
                >
                  <Text style={[styles.unitBtnText, inputs.boom_unit === 'mm' && styles.unitBtnTextActive]}>mm</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={[styles.unitBtn, inputs.boom_unit === 'inches' && styles.unitBtnActive]}
                  onPress={() => setInputs(prev => ({ ...prev, boom_unit: 'inches' }))}
                >
                  <Text style={[styles.unitBtnText, inputs.boom_unit === 'inches' && styles.unitBtnTextActive]}>in</Text>
                </TouchableOpacity>
              </View>
            </View>
          </View>

          {/* Error Message */}
          {error && (
            <View style={styles.errorContainer}>
              <Ionicons name="alert-circle" size={20} color="#f44336" />
              <Text style={styles.errorText}>{error}</Text>
            </View>
          )}

          {/* Calculate Button */}
          <TouchableOpacity
            style={[styles.calculateButton, loading && styles.buttonDisabled]}
            onPress={calculateAntenna}
            disabled={loading}
            activeOpacity={0.8}
          >
            {loading ? (
              <ActivityIndicator color="#fff" size="small" />
            ) : (
              <>
                <Ionicons name="calculator" size={22} color="#fff" />
                <Text style={styles.calculateButtonText}>Calculate Parameters</Text>
              </>
            )}
          </TouchableOpacity>

          {/* Results Section */}
          {showResults && results && (
            <View style={styles.resultsSection}>
              <View style={styles.resultsHeader}>
                <Text style={styles.sectionTitle}>
                  <Ionicons name="analytics" size={16} color="#4CAF50" /> Analysis Results
                </Text>
                <TouchableOpacity onPress={resetForm} style={styles.resetButton}>
                  <Ionicons name="refresh" size={18} color="#888" />
                  <Text style={styles.resetText}>Reset</Text>
                </TouchableOpacity>
              </View>

              <View style={styles.bandInfoCard}>
                <Text style={styles.bandInfoTitle}>{results.band_info.name}</Text>
                <Text style={styles.bandInfoText}>Center: {results.center_frequency.toFixed(3)} MHz</Text>
              </View>

              {/* SWR Bandwidth Meter */}
              <SwrMeter 
                data={results.swr_curve} 
                centerFreq={results.center_frequency}
                usable15={results.usable_bandwidth_1_5}
                usable20={results.usable_bandwidth_2_0}
              />

              <ResultCard
                title="Gain"
                value={`${results.gain_dbi} dBi`}
                description={results.gain_description}
                icon="trending-up"
                color="#4CAF50"
              />

              <ResultCard
                title="SWR at Center"
                value={`${results.swr}:1`}
                description={results.swr_description}
                icon="pulse"
                color="#2196F3"
              />

              <ResultCard
                title="Front-to-Back Ratio"
                value={`${results.fb_ratio} dB`}
                description={results.fb_ratio_description}
                icon="swap-horizontal"
                color="#9C27B0"
              />

              <ResultCard
                title="Beamwidth"
                value={`${results.beamwidth}°`}
                description={results.beamwidth_description}
                icon="radio-button-on"
                color="#FF9800"
              />

              <ResultCard
                title="Usable Bandwidth (≤1.5:1)"
                value={`${results.usable_bandwidth_1_5.toFixed(3)} MHz`}
                description={`Full bandwidth at 2:1: ${results.usable_bandwidth_2_0.toFixed(3)} MHz`}
                icon="resize"
                color="#00BCD4"
              />

              <ResultCard
                title="Multiplication Factor"
                value={`${results.multiplication_factor}x`}
                description={results.multiplication_description}
                icon="flash"
                color="#E91E63"
              />

              <ResultCard
                title="Antenna Efficiency"
                value={`${results.antenna_efficiency}%`}
                description={results.efficiency_description}
                icon="speedometer"
                color="#8BC34A"
              />

              <PolarPattern data={results.far_field_pattern} />
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
  scrollContent: { padding: 16, paddingBottom: 40 },
  header: { alignItems: 'center', marginBottom: 16, paddingVertical: 12 },
  headerTitle: { fontSize: 26, fontWeight: 'bold', color: '#fff', marginTop: 6 },
  headerSubtitle: { fontSize: 13, color: '#888', marginTop: 2 },
  section: { backgroundColor: '#1a1a1a', borderRadius: 14, padding: 14, marginBottom: 14 },
  sectionTitle: { fontSize: 16, fontWeight: '600', color: '#fff', marginBottom: 12 },
  inputGroup: { marginBottom: 12 },
  inputLabel: { fontSize: 13, color: '#aaa', marginBottom: 6 },
  input: { backgroundColor: '#252525', borderRadius: 10, padding: 12, fontSize: 15, color: '#fff', borderWidth: 1, borderColor: '#333' },
  rowInput: { flexDirection: 'row', alignItems: 'flex-end', marginBottom: 12, gap: 10 },
  flexInput: { flex: 1 },
  unitToggle: { flexDirection: 'row', backgroundColor: '#252525', borderRadius: 8, overflow: 'hidden' },
  unitBtn: { paddingVertical: 12, paddingHorizontal: 14, minWidth: 44 },
  unitBtnActive: { backgroundColor: '#4CAF50' },
  unitBtnText: { fontSize: 14, color: '#888', textAlign: 'center' },
  unitBtnTextActive: { color: '#fff', fontWeight: '600' },
  dropdownContainer: { marginBottom: 12 },
  dropdownButton: { backgroundColor: '#252525', borderRadius: 10, padding: 12, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', borderWidth: 1, borderColor: '#333' },
  dropdownButtonText: { fontSize: 15, color: '#fff' },
  dropdownList: { backgroundColor: '#2a2a2a', borderRadius: 10, marginTop: 4, maxHeight: 200, borderWidth: 1, borderColor: '#333' },
  dropdownScroll: { maxHeight: 200 },
  dropdownItem: { padding: 12, borderBottomWidth: 1, borderBottomColor: '#333' },
  dropdownItemSelected: { backgroundColor: '#333' },
  dropdownItemText: { fontSize: 14, color: '#ccc' },
  dropdownItemTextSelected: { color: '#4CAF50', fontWeight: '500' },
  elementCard: { backgroundColor: '#222', borderRadius: 10, padding: 12, marginTop: 10, borderLeftWidth: 3 },
  elementTitle: { fontSize: 14, fontWeight: '600', marginBottom: 10 },
  elementRow: { flexDirection: 'row', gap: 10 },
  elementField: { flex: 1, marginBottom: 8 },
  elementLabel: { fontSize: 11, color: '#888', marginBottom: 4 },
  elementInput: { backgroundColor: '#1a1a1a', borderRadius: 8, padding: 10, fontSize: 14, color: '#fff', borderWidth: 1, borderColor: '#333' },
  errorContainer: { flexDirection: 'row', alignItems: 'center', backgroundColor: 'rgba(244, 67, 54, 0.1)', padding: 12, borderRadius: 10, marginBottom: 14 },
  errorText: { color: '#f44336', marginLeft: 8, flex: 1, fontSize: 13 },
  calculateButton: { backgroundColor: '#4CAF50', flexDirection: 'row', alignItems: 'center', justifyContent: 'center', padding: 16, borderRadius: 12, marginBottom: 16, gap: 8 },
  buttonDisabled: { opacity: 0.7 },
  calculateButtonText: { color: '#fff', fontSize: 17, fontWeight: '600' },
  resultsSection: { marginBottom: 16 },
  resultsHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 },
  resetButton: { flexDirection: 'row', alignItems: 'center', padding: 8, gap: 4 },
  resetText: { color: '#888', fontSize: 13 },
  bandInfoCard: { backgroundColor: '#1a1a1a', borderRadius: 10, padding: 12, marginBottom: 12, alignItems: 'center' },
  bandInfoTitle: { fontSize: 16, fontWeight: '600', color: '#4CAF50' },
  bandInfoText: { fontSize: 13, color: '#888', marginTop: 4 },
  resultCard: { backgroundColor: '#1a1a1a', borderRadius: 10, padding: 14, marginBottom: 10, borderLeftWidth: 4 },
  resultHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 6, gap: 8 },
  resultTitle: { fontSize: 12, color: '#888', textTransform: 'uppercase', letterSpacing: 0.5 },
  resultValue: { fontSize: 26, fontWeight: 'bold', marginBottom: 4 },
  resultDescription: { fontSize: 12, color: '#888' },
  swrContainer: { backgroundColor: '#1a1a1a', borderRadius: 14, padding: 14, marginBottom: 12, alignItems: 'center' },
  swrTitle: { fontSize: 15, fontWeight: '600', color: '#fff', marginBottom: 12 },
  swrLegend: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'center', marginTop: 10, gap: 12 },
  legendItem: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  legendColor: { width: 14, height: 14, borderRadius: 3 },
  legendText: { fontSize: 11, color: '#888' },
  polarContainer: { backgroundColor: '#1a1a1a', borderRadius: 14, padding: 14, alignItems: 'center', marginTop: 8 },
  polarTitle: { fontSize: 15, fontWeight: '600', color: '#fff', marginBottom: 12 },
  polarSubtitle: { fontSize: 11, color: '#666', marginTop: 10 },
});
