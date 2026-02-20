import React, { useEffect, useState, useCallback } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ScrollView, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL || 'https://helpful-adaptation-production.up.railway.app';
const CHECK_INTERVAL = 5 * 60 * 1000;

type HealthData = {
  overall: string;
  api: string;
  database: string;
  production: string;
  db_latency_ms: number | null;
  prod_latency_ms: number | null;
  checked_at: string;
};

const STATUS_COLORS: Record<string, string> = {
  up: '#4CAF50',
  degraded: '#FF9800',
  down: '#f44336',
  checking: '#888',
};

const STATUS_LABELS: Record<string, string> = {
  up: 'Operational',
  degraded: 'Degraded',
  down: 'Down',
  checking: 'Checking...',
};

function ServiceCard({ name, icon, status, latency }: { name: string; icon: any; status: string; latency: number | null }) {
  const color = STATUS_COLORS[status] || '#888';
  return (
    <View style={[s.serviceCard, { borderColor: color }]} data-testid={`service-${name.toLowerCase().replace(/\s/g, '-')}`}>
      <View style={s.serviceHeader}>
        <Ionicons name={icon} size={22} color={color} />
        <Text style={s.serviceName}>{name}</Text>
        <View style={[s.statusPill, { backgroundColor: color + '22', borderColor: color }]}>
          <View style={[s.statusDotSmall, { backgroundColor: color }]} />
          <Text style={[s.statusText, { color }]}>{STATUS_LABELS[status] || status}</Text>
        </View>
      </View>
      {latency !== null && (
        <Text style={s.latencyText}>Response: {latency}ms</Text>
      )}
    </View>
  );
}

export default function StatusPage() {
  const router = useRouter();
  const [health, setHealth] = useState<HealthData | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

  const fetchHealth = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/health`);
      if (res.ok) {
        const data = await res.json();
        setHealth(data);
      } else {
        setHealth({ overall: 'degraded', api: 'degraded', database: 'unknown', production: 'unknown', db_latency_ms: null, prod_latency_ms: null, checked_at: '' });
      }
    } catch {
      setHealth({ overall: 'down', api: 'down', database: 'unknown', production: 'unknown', db_latency_ms: null, prod_latency_ms: null, checked_at: '' });
    }
    setLastRefresh(new Date());
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, CHECK_INTERVAL);
    return () => clearInterval(interval);
  }, [fetchHealth]);

  const overallColor = health ? (STATUS_COLORS[health.overall] || '#888') : '#888';

  return (
    <SafeAreaView style={s.container}>
      <ScrollView style={s.scroll} contentContainerStyle={s.scrollContent}>

        {/* Header */}
        <View style={s.header}>
          <TouchableOpacity onPress={() => router.back()} style={s.backBtn}>
            <Ionicons name="arrow-back" size={24} color="#fff" />
          </TouchableOpacity>
          <Text style={s.headerTitle}>System Status</Text>
          <TouchableOpacity onPress={fetchHealth} style={s.refreshBtn} data-testid="refresh-status-btn">
            {loading ? <ActivityIndicator size="small" color="#4CAF50" /> : <Ionicons name="refresh" size={22} color="#4CAF50" />}
          </TouchableOpacity>
        </View>

        {/* Overall Status Banner */}
        <View style={[s.overallBanner, { borderColor: overallColor }]}>
          <View style={[s.overallDot, { backgroundColor: overallColor }]} />
          <View style={s.overallInfo}>
            <Text style={[s.overallTitle, { color: overallColor }]}>
              {health?.overall === 'up' ? 'All Systems Operational' :
               health?.overall === 'degraded' ? 'Partial Outage' :
               health?.overall === 'down' ? 'Major Outage — Needs Attention' : 'Checking...'}
            </Text>
            {lastRefresh && (
              <Text style={s.lastChecked}>Last checked: {lastRefresh.toLocaleTimeString()}</Text>
            )}
          </View>
        </View>

        {/* Auto refresh note */}
        <Text style={s.autoNote}>Auto-refreshes every 5 minutes</Text>

        {/* Service Cards */}
        <Text style={s.sectionTitle}>Services</Text>

        <ServiceCard
          name="API Server"
          icon="server-outline"
          status={health?.api || 'checking'}
          latency={null}
        />

        <ServiceCard
          name="Database"
          icon="layers-outline"
          status={health?.database || 'checking'}
          latency={health?.db_latency_ms ?? null}
        />

        <ServiceCard
          name="Production (Railway)"
          icon="cloud-outline"
          status={health?.production || 'checking'}
          latency={health?.prod_latency_ms ?? null}
        />

        {/* Legend */}
        <View style={s.legend}>
          <View style={s.legendItem}>
            <View style={[s.legendDot, { backgroundColor: '#4CAF50' }]} />
            <Text style={s.legendText}>Operational</Text>
          </View>
          <View style={s.legendItem}>
            <View style={[s.legendDot, { backgroundColor: '#FF9800' }]} />
            <Text style={s.legendText}>Degraded</Text>
          </View>
          <View style={s.legendItem}>
            <View style={[s.legendDot, { backgroundColor: '#f44336' }]} />
            <Text style={s.legendText}>Down</Text>
          </View>
        </View>

        <View style={{ height: 40 }} />
      </ScrollView>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#121212' },
  scroll: { flex: 1 },
  scrollContent: { padding: 16 },

  header: { flexDirection: 'row', alignItems: 'center', marginBottom: 20, paddingVertical: 8 },
  backBtn: { padding: 4 },
  headerTitle: { flex: 1, fontSize: 20, fontWeight: 'bold', color: '#fff', marginLeft: 12 },
  refreshBtn: { padding: 4 },

  overallBanner: { backgroundColor: '#1E1E1E', borderRadius: 16, padding: 20, borderWidth: 2, flexDirection: 'row', alignItems: 'center', gap: 16, marginBottom: 8 },
  overallDot: { width: 16, height: 16, borderRadius: 8 },
  overallInfo: { flex: 1 },
  overallTitle: { fontSize: 18, fontWeight: 'bold' },
  lastChecked: { fontSize: 12, color: '#666', marginTop: 4 },

  autoNote: { fontSize: 11, color: '#555', textAlign: 'center', marginBottom: 20 },

  sectionTitle: { fontSize: 16, fontWeight: '600', color: '#aaa', marginBottom: 12, letterSpacing: 1, textTransform: 'uppercase' },

  serviceCard: { backgroundColor: '#1E1E1E', borderRadius: 12, padding: 16, marginBottom: 12, borderWidth: 1, borderLeftWidth: 3 },
  serviceHeader: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  serviceName: { fontSize: 15, fontWeight: '600', color: '#fff', flex: 1 },
  statusPill: { flexDirection: 'row', alignItems: 'center', gap: 6, paddingHorizontal: 10, paddingVertical: 4, borderRadius: 12, borderWidth: 1 },
  statusDotSmall: { width: 6, height: 6, borderRadius: 3 },
  statusText: { fontSize: 12, fontWeight: '600' },
  latencyText: { fontSize: 11, color: '#666', marginTop: 8, marginLeft: 32 },

  legend: { flexDirection: 'row', justifyContent: 'center', gap: 24, marginTop: 20, paddingTop: 16, borderTopWidth: 1, borderTopColor: '#222' },
  legendItem: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  legendDot: { width: 8, height: 8, borderRadius: 4 },
  legendText: { fontSize: 12, color: '#888' },
});
