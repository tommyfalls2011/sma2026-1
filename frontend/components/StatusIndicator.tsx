import React, { useState, useEffect, useCallback } from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { useRouter } from 'expo-router';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL || 'https://helpful-adaptation-production.up.railway.app';
const CHECK_INTERVAL = 5 * 60 * 1000; // 5 minutes

type HealthStatus = {
  overall: 'up' | 'degraded' | 'down' | 'checking';
  api: string;
  database: string;
  production: string;
  db_latency_ms: number | null;
  prod_latency_ms: number | null;
  checked_at: string;
};

export function useHealthStatus() {
  const [status, setStatus] = useState<HealthStatus>({
    overall: 'checking', api: 'checking', database: 'checking',
    production: 'checking', db_latency_ms: null, prod_latency_ms: null, checked_at: '',
  });

  const checkHealth = useCallback(async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/health`);
      if (res.ok) {
        const data = await res.json();
        setStatus(data);
      } else {
        setStatus(prev => ({ ...prev, overall: 'degraded', api: 'degraded' }));
      }
    } catch {
      setStatus(prev => ({ ...prev, overall: 'down', api: 'down' }));
    }
  }, []);

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, CHECK_INTERVAL);
    return () => clearInterval(interval);
  }, [checkHealth]);

  return { status, refresh: checkHealth };
}

const STATUS_COLORS: Record<string, string> = {
  up: '#4CAF50',
  degraded: '#FF9800',
  down: '#f44336',
  checking: '#888',
};

export function StatusDot({ onPress }: { onPress?: () => void }) {
  const { status } = useHealthStatus();
  const color = STATUS_COLORS[status.overall] || '#888';

  return (
    <TouchableOpacity
      onPress={onPress}
      style={dotStyles.container}
      data-testid="status-dot"
      activeOpacity={0.7}
    >
      <View style={[dotStyles.dot, { backgroundColor: color }]} />
      <View style={[dotStyles.ring, { borderColor: color }]} />
    </TouchableOpacity>
  );
}

const dotStyles = StyleSheet.create({
  container: { width: 20, height: 20, justifyContent: 'center', alignItems: 'center' },
  dot: { width: 8, height: 8, borderRadius: 4, position: 'absolute' },
  ring: { width: 14, height: 14, borderRadius: 7, borderWidth: 1.5, opacity: 0.4 },
});
