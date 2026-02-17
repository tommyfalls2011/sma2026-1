import React from 'react';
import { View, Text } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

export const SpecSection = ({ title, icon, color, children }: { title: string; icon: string; color: string; children: React.ReactNode }) => (
  <View style={{ marginBottom: 12 }}>
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 6 }}>
      <Ionicons name={icon as any} size={14} color={color} />
      <Text style={{ fontSize: 12, fontWeight: '600', color }}>{title}</Text>
    </View>
    <View style={{ backgroundColor: '#1a1a1a', borderRadius: 8, padding: 10 }}>
      {children}
    </View>
  </View>
);

export const SpecRow = ({ label, value, accent, small }: { label: string; value: string; accent?: string; small?: boolean }) => (
  <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: small ? 2 : 4 }}>
    <Text style={{ fontSize: small ? 10 : 11, color: '#888' }}>{label}</Text>
    <Text style={{ fontSize: small ? 10 : 11, color: accent || '#fff', fontWeight: '500' }}>{value}</Text>
  </View>
);
