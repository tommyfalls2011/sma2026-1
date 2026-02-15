import React from 'react';
import { View, Text } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { styles } from '../styles';

export const ResultCard = ({ title, value, description, icon, color }: any) => (
  <View style={[styles.resultCard, { borderLeftColor: color }]}>
    <View style={styles.resultHeader}><Ionicons name={icon} size={16} color={color} /><Text style={styles.resultTitle}>{title}</Text></View>
    <Text style={[styles.resultValue, { color }]}>{value}</Text>
    {description && <Text style={styles.resultDescription}>{description}</Text>}
  </View>
);
