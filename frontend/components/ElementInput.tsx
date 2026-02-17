import React from 'react';
import { View, Text, TextInput } from 'react-native';
import { styles } from './styles';
import type { ElementDimension, TaperConfig } from './types';

export const ElementInput = ({ element, index, onChange, unit, taperEnabled, taperConfig }: {
  element: ElementDimension;
  index: number;
  onChange: (index: number, field: keyof ElementDimension, value: string) => void;
  unit: string;
  taperEnabled: boolean;
  taperConfig: TaperConfig;
}) => {
  const color = element.element_type === 'reflector' ? '#FF9800' : element.element_type === 'driven' ? '#4CAF50' : '#2196F3';
  const unitLabel = unit === 'meters' ? ' (m)' : ' (in)';
  let tipDiameter = element.diameter;
  if (taperEnabled && taperConfig.sections.length > 0) {
    const lastSection = taperConfig.sections[taperConfig.sections.length - 1];
    tipDiameter = lastSection?.end_diameter || element.diameter;
  }
  return (
    <View style={[styles.elementCard, { borderLeftColor: color }]}>
      <Text style={[styles.elementTitle, { color }]}>{element.element_type.charAt(0).toUpperCase() + element.element_type.slice(1)} {element.element_type === 'director' ? `#${index}` : ''}</Text>
      <View style={styles.elementRow}>
        <View style={styles.elementField}><Text style={styles.elementLabel}>Length{unitLabel}</Text><TextInput style={styles.elementInput} value={element.length} onChangeText={v => onChange(index, 'length', v)} keyboardType="decimal-pad" placeholder="0" placeholderTextColor="#555" /></View>
        <View style={styles.elementField}>
          <Text style={styles.elementLabel}>
            {taperEnabled ? `BoomØ${unitLabel}` : `Dia${unitLabel}`}
            {taperEnabled && <Text style={{ color: '#E91E63' }}> → {tipDiameter}"</Text>}
          </Text>
          <TextInput
            style={[styles.elementInput, taperEnabled && styles.inputDisabled]}
            value={element.diameter}
            onChangeText={v => onChange(index, 'diameter', v)}
            keyboardType="decimal-pad"
            placeholder="0.5"
            placeholderTextColor="#555"
            editable={!taperEnabled}
          />
        </View>
        <View style={styles.elementField}><Text style={styles.elementLabel}>Pos{unitLabel}</Text><TextInput style={styles.elementInput} value={element.position} onChangeText={v => onChange(index, 'position', v)} keyboardType="decimal-pad" placeholder="0" placeholderTextColor="#555" /></View>
      </View>
    </View>
  );
};
