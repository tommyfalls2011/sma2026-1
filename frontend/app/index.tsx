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
import Svg, { Circle, Line, Path, Text as SvgText, G } from 'react-native-svg';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL || '';
const { width: screenWidth } = Dimensions.get('window');

interface AntennaInput {
  num_elements: string;
  height_from_ground: string;
  boom_diameter: string;
  element_size: string;
  tapered: boolean;
  frequency_mhz: string;
  unit: 'meters' | 'inches';
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
      <Ionicons name={icon} size={24} color={color} />
      <Text style={styles.resultTitle}>{title}</Text>
    </View>
    <Text style={[styles.resultValue, { color }]}>{value}</Text>
    <Text style={styles.resultDescription}>{description}</Text>
  </View>
);

const PolarPattern = ({ data }: { data: { angle: number; magnitude: number }[] }) => {
  const size = Math.min(screenWidth - 48, 320);
  const center = size / 2;
  const maxRadius = center - 30;

  // Create path for the pattern
  const createPolarPath = () => {
    if (!data || data.length === 0) return '';

    let pathData = '';
    data.forEach((point, index) => {
      const angleRad = (point.angle - 90) * (Math.PI / 180); // Adjust so 0° is at top
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
        {/* Background circles */}
        {[0.25, 0.5, 0.75, 1].map((scale) => (
          <Circle
            key={scale}
            cx={center}
            cy={center}
            r={maxRadius * scale}
            stroke="#333"
            strokeWidth="1"
            fill="none"
          />
        ))}

        {/* Cross lines */}
        <Line x1={center} y1={30} x2={center} y2={size - 30} stroke="#333" strokeWidth="1" />
        <Line x1={30} y1={center} x2={size - 30} y2={center} stroke="#333" strokeWidth="1" />

        {/* Angle labels */}
        <SvgText x={center} y={18} fill="#888" fontSize="12" textAnchor="middle">0°</SvgText>
        <SvgText x={size - 12} y={center + 4} fill="#888" fontSize="12" textAnchor="middle">90°</SvgText>
        <SvgText x={center} y={size - 8} fill="#888" fontSize="12" textAnchor="middle">180°</SvgText>
        <SvgText x={12} y={center + 4} fill="#888" fontSize="12" textAnchor="middle">270°</SvgText>

        {/* Radiation pattern */}
        <Path
          d={createPolarPath()}
          fill="rgba(76, 175, 80, 0.3)"
          stroke="#4CAF50"
          strokeWidth="2"
        />

        {/* Center dot */}
        <Circle cx={center} cy={center} r={4} fill="#4CAF50" />
      </Svg>
      <Text style={styles.polarSubtitle}>Main lobe direction: 0° (Forward)</Text>
    </View>
  );
};

export default function AntennaCalculator() {
  const [inputs, setInputs] = useState<AntennaInput>({
    num_elements: '5',
    height_from_ground: '10',
    boom_diameter: '0.025',
    element_size: '0.01',
    tapered: false,
    frequency_mhz: '144',
    unit: 'meters',
  });

  const [results, setResults] = useState<AntennaOutput | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showResults, setShowResults] = useState(false);

  const handleInputChange = (field: keyof AntennaInput, value: string | boolean) => {
    setInputs((prev) => ({ ...prev, [field]: value }));
    setError(null);
  };

  const toggleUnit = () => {
    const newUnit = inputs.unit === 'meters' ? 'inches' : 'meters';
    
    // Convert values
    const conversionFactor = newUnit === 'inches' ? 39.3701 : 0.0254;
    
    setInputs((prev) => ({
      ...prev,
      unit: newUnit,
      height_from_ground: prev.height_from_ground ? (parseFloat(prev.height_from_ground) * conversionFactor).toFixed(4) : '',
      boom_diameter: prev.boom_diameter ? (parseFloat(prev.boom_diameter) * conversionFactor).toFixed(4) : '',
      element_size: prev.element_size ? (parseFloat(prev.element_size) * conversionFactor).toFixed(4) : '',
    }));
  };

  const calculateAntenna = useCallback(async () => {
    // Validate inputs
    if (!inputs.num_elements || parseInt(inputs.num_elements) < 1) {
      setError('Number of elements must be at least 1');
      return;
    }
    if (!inputs.height_from_ground || parseFloat(inputs.height_from_ground) <= 0) {
      setError('Height from ground must be positive');
      return;
    }
    if (!inputs.boom_diameter || parseFloat(inputs.boom_diameter) <= 0) {
      setError('Boom diameter must be positive');
      return;
    }
    if (!inputs.element_size || parseFloat(inputs.element_size) <= 0) {
      setError('Element size must be positive');
      return;
    }
    if (!inputs.frequency_mhz || parseFloat(inputs.frequency_mhz) <= 0) {
      setError('Frequency must be positive');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${BACKEND_URL}/api/calculate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          num_elements: parseInt(inputs.num_elements),
          height_from_ground: parseFloat(inputs.height_from_ground),
          boom_diameter: parseFloat(inputs.boom_diameter),
          element_size: parseFloat(inputs.element_size),
          tapered: inputs.tapered,
          frequency_mhz: parseFloat(inputs.frequency_mhz),
          unit: inputs.unit,
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
      num_elements: '5',
      height_from_ground: '10',
      boom_diameter: '0.025',
      element_size: '0.01',
      tapered: false,
      frequency_mhz: '144',
      unit: 'meters',
    });
    setResults(null);
    setShowResults(false);
    setError(null);
  };

  return (
    <SafeAreaView style={styles.container}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={styles.flex}
      >
        <ScrollView
          style={styles.scrollView}
          contentContainerStyle={styles.scrollContent}
          showsVerticalScrollIndicator={false}
        >
          {/* Header */}
          <View style={styles.header}>
            <Ionicons name="radio-outline" size={36} color="#4CAF50" />
            <Text style={styles.headerTitle}>Antenna Calculator</Text>
            <Text style={styles.headerSubtitle}>Yagi-Uda Antenna Analysis</Text>
          </View>

          {/* Unit Toggle */}
          <View style={styles.unitToggle}>
            <Text style={[styles.unitLabel, inputs.unit === 'meters' && styles.unitLabelActive]}>
              Meters
            </Text>
            <Switch
              value={inputs.unit === 'inches'}
              onValueChange={toggleUnit}
              trackColor={{ false: '#4CAF50', true: '#2196F3' }}
              thumbColor="#fff"
            />
            <Text style={[styles.unitLabel, inputs.unit === 'inches' && styles.unitLabelActive]}>
              Inches
            </Text>
          </View>

          {/* Input Section */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>
              <Ionicons name="settings-outline" size={18} color="#4CAF50" /> Antenna Specifications
            </Text>

            <View style={styles.inputGroup}>
              <Text style={styles.inputLabel}>Number of Elements</Text>
              <TextInput
                style={styles.input}
                value={inputs.num_elements}
                onChangeText={(v) => handleInputChange('num_elements', v)}
                keyboardType="number-pad"
                placeholder="e.g., 5"
                placeholderTextColor="#666"
              />
            </View>

            <View style={styles.inputGroup}>
              <Text style={styles.inputLabel}>Height from Ground ({inputs.unit})</Text>
              <TextInput
                style={styles.input}
                value={inputs.height_from_ground}
                onChangeText={(v) => handleInputChange('height_from_ground', v)}
                keyboardType="decimal-pad"
                placeholder={inputs.unit === 'meters' ? 'e.g., 10' : 'e.g., 394'}
                placeholderTextColor="#666"
              />
            </View>

            <View style={styles.inputGroup}>
              <Text style={styles.inputLabel}>Boom Diameter ({inputs.unit})</Text>
              <TextInput
                style={styles.input}
                value={inputs.boom_diameter}
                onChangeText={(v) => handleInputChange('boom_diameter', v)}
                keyboardType="decimal-pad"
                placeholder={inputs.unit === 'meters' ? 'e.g., 0.025' : 'e.g., 1'}
                placeholderTextColor="#666"
              />
            </View>

            <View style={styles.inputGroup}>
              <Text style={styles.inputLabel}>Element Size/Diameter ({inputs.unit})</Text>
              <TextInput
                style={styles.input}
                value={inputs.element_size}
                onChangeText={(v) => handleInputChange('element_size', v)}
                keyboardType="decimal-pad"
                placeholder={inputs.unit === 'meters' ? 'e.g., 0.01' : 'e.g., 0.4'}
                placeholderTextColor="#666"
              />
            </View>

            <View style={styles.inputGroup}>
              <Text style={styles.inputLabel}>Operating Frequency (MHz)</Text>
              <TextInput
                style={styles.input}
                value={inputs.frequency_mhz}
                onChangeText={(v) => handleInputChange('frequency_mhz', v)}
                keyboardType="decimal-pad"
                placeholder="e.g., 144"
                placeholderTextColor="#666"
              />
            </View>

            <View style={styles.switchGroup}>
              <View style={styles.switchRow}>
                <Text style={styles.inputLabel}>Tapered Elements</Text>
                <Switch
                  value={inputs.tapered}
                  onValueChange={(v) => handleInputChange('tapered', v)}
                  trackColor={{ false: '#444', true: '#4CAF50' }}
                  thumbColor={inputs.tapered ? '#fff' : '#ccc'}
                />
              </View>
              <Text style={styles.switchHint}>
                Tapered elements improve bandwidth and reduce wind load
              </Text>
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
                  <Ionicons name="analytics" size={18} color="#4CAF50" /> Analysis Results
                </Text>
                <TouchableOpacity onPress={resetForm} style={styles.resetButton}>
                  <Ionicons name="refresh" size={18} color="#888" />
                  <Text style={styles.resetText}>Reset</Text>
                </TouchableOpacity>
              </View>

              <ResultCard
                title="Gain"
                value={`${results.gain_dbi} dBi`}
                description={results.gain_description}
                icon="trending-up"
                color="#4CAF50"
              />

              <ResultCard
                title="SWR"
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
                title="Bandwidth"
                value={`${results.bandwidth} MHz`}
                description={results.bandwidth_description}
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

              {/* Far Field Pattern */}
              <PolarPattern data={results.far_field_pattern} />
            </View>
          )}

          {/* Info Section */}
          <View style={styles.infoSection}>
            <Text style={styles.infoTitle}>
              <Ionicons name="information-circle" size={16} color="#666" /> About Calculations
            </Text>
            <Text style={styles.infoText}>
              This calculator uses Yagi-Uda antenna theory to estimate performance parameters.
              Results are approximations for typical antenna designs. Actual performance may vary
              based on construction quality, ground conditions, and environmental factors.
            </Text>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#121212',
  },
  flex: {
    flex: 1,
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    padding: 16,
    paddingBottom: 40,
  },
  header: {
    alignItems: 'center',
    marginBottom: 20,
    paddingVertical: 16,
  },
  headerTitle: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#fff',
    marginTop: 8,
  },
  headerSubtitle: {
    fontSize: 14,
    color: '#888',
    marginTop: 4,
  },
  unitToggle: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 20,
    padding: 12,
    backgroundColor: '#1a1a1a',
    borderRadius: 12,
  },
  unitLabel: {
    fontSize: 16,
    color: '#666',
    marginHorizontal: 12,
  },
  unitLabelActive: {
    color: '#fff',
    fontWeight: '600',
  },
  section: {
    backgroundColor: '#1a1a1a',
    borderRadius: 16,
    padding: 16,
    marginBottom: 16,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#fff',
    marginBottom: 16,
  },
  inputGroup: {
    marginBottom: 16,
  },
  inputLabel: {
    fontSize: 14,
    color: '#bbb',
    marginBottom: 8,
  },
  input: {
    backgroundColor: '#252525',
    borderRadius: 10,
    padding: 14,
    fontSize: 16,
    color: '#fff',
    borderWidth: 1,
    borderColor: '#333',
  },
  switchGroup: {
    marginTop: 8,
  },
  switchRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  switchHint: {
    fontSize: 12,
    color: '#666',
    marginTop: 4,
  },
  errorContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(244, 67, 54, 0.1)',
    padding: 12,
    borderRadius: 10,
    marginBottom: 16,
  },
  errorText: {
    color: '#f44336',
    marginLeft: 8,
    flex: 1,
  },
  calculateButton: {
    backgroundColor: '#4CAF50',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 16,
    borderRadius: 12,
    marginBottom: 20,
    gap: 8,
  },
  buttonDisabled: {
    opacity: 0.7,
  },
  calculateButtonText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '600',
  },
  resultsSection: {
    marginBottom: 20,
  },
  resultsHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  resetButton: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 8,
    gap: 4,
  },
  resetText: {
    color: '#888',
    fontSize: 14,
  },
  resultCard: {
    backgroundColor: '#1a1a1a',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    borderLeftWidth: 4,
  },
  resultHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
    gap: 8,
  },
  resultTitle: {
    fontSize: 14,
    color: '#888',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  resultValue: {
    fontSize: 28,
    fontWeight: 'bold',
    marginBottom: 4,
  },
  resultDescription: {
    fontSize: 13,
    color: '#888',
  },
  polarContainer: {
    backgroundColor: '#1a1a1a',
    borderRadius: 16,
    padding: 16,
    alignItems: 'center',
    marginTop: 8,
  },
  polarTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
    marginBottom: 16,
  },
  polarSubtitle: {
    fontSize: 12,
    color: '#666',
    marginTop: 12,
  },
  infoSection: {
    backgroundColor: '#1a1a1a',
    borderRadius: 12,
    padding: 16,
    marginTop: 8,
  },
  infoTitle: {
    fontSize: 14,
    color: '#888',
    marginBottom: 8,
  },
  infoText: {
    fontSize: 13,
    color: '#666',
    lineHeight: 20,
  },
});
