import React, { useState } from 'react';
import { View, Text, TouchableOpacity, Modal, FlatList } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { styles } from './styles';

export const Dropdown = ({ label, value, options, onChange }: any) => {
  const [open, setOpen] = useState(false);
  const selectedLabel = options.find((o: any) => o.value === value)?.label || value;
  return (
    <View style={styles.dropdownContainer}>
      {label && <Text style={styles.inputLabel}>{label}</Text>}
      <TouchableOpacity style={styles.dropdownButton} onPress={() => setOpen(true)}>
        <Text style={styles.dropdownButtonText}>{selectedLabel}</Text>
        <Ionicons name="chevron-down" size={14} color="#888" />
      </TouchableOpacity>
      <Modal visible={open} transparent animationType="fade" onRequestClose={() => setOpen(false)}>
        <TouchableOpacity style={styles.modalOverlay} activeOpacity={1} onPress={() => setOpen(false)}>
          <View style={styles.modalDropdown}>
            {label && <Text style={styles.modalDropdownTitle}>{label}</Text>}
            <FlatList
              data={options}
              keyExtractor={(item: any) => item.value}
              renderItem={({ item }: any) => (
                <TouchableOpacity
                  style={[styles.modalDropdownItem, item.value === value && styles.modalDropdownItemSelected]}
                  onPress={() => { onChange(item.value); setOpen(false); }}
                >
                  <Text style={[styles.modalDropdownItemText, item.value === value && styles.modalDropdownItemTextSelected]}>{item.label}</Text>
                  {item.value === value && <Ionicons name="checkmark" size={18} color="#4CAF50" />}
                </TouchableOpacity>
              )}
            />
          </View>
        </TouchableOpacity>
      </Modal>
    </View>
  );
};
