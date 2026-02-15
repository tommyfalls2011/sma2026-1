import React from 'react';
import { View, Text, TextInput } from 'react-native';
import { styles } from '../styles';

export const ElementInput = ({ element, index, onChange, unit, taperEnabled, taperConfig }: any) => {
  const title = element.element_type === 'reflector' ? 'Reflector' : element.element_type === 'driven' ? 'Driven' : `Dir ${index - 1}`;
  const color = element.element_type === 'reflector' ? '#FF9800' : element.element_type === 'driven' ? '#4CAF50' : '#2196F3';
  const unitLabel = unit === 'meters' ? 'm' : '"';

  let tipDiameter = element.diameter;
  let centerDia = element.diameter;
  if (taperEnabled && taperConfig?.sections?.length > 0) {
    centerDia = taperConfig.sections[0]?.start_diameter || element.diameter;
    const lastSection = taperConfig.sections[taperConfig.sections.length - 1];
    tipDiameter = lastSection?.end_diameter || element.diameter;
  }

  return (
    <View style={[styles.elementCard, { borderLeftColor: color }]}>
      <Text style={[styles.elementTitle, { color }]}>{title}</Text>
      <View style={styles.elementRow}>
        <View style={styles.elementField}><Text style={styles.elementLabel}>Length{unitLabel}</Text><TextInput style={styles.elementInput} value={element.length} onChangeText={v => onChange(index, 'length', v)} keyboardType="decimal-pad" placeholder="0" placeholderTextColor="#555" /></View>
        <View style={styles.elementField}>
          <Text style={styles.elementLabel}>{taperEnabled ? `\u00D8 ${centerDia}"\u2192${tipDiameter}"` : `Dia${unitLabel}`}</Text>
          <TextInput
            style={[styles.elementInput, taperEnabled && styles.inputDisabled]}
            value={taperEnabled ? centerDia : element.diameter}
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
