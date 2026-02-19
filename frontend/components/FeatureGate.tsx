import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet, Platform } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useAuth } from '../context/AuthContext';

interface FeatureGateProps {
  feature: string;
  label: string;
  children: React.ReactNode;
  compact?: boolean;
}

export function FeatureGate({ feature, label, children, compact }: FeatureGateProps) {
  const { user, isFeatureAvailable, tiers } = useAuth();
  const router = useRouter();

  // Debug logging
  console.log(`FeatureGate[${feature}]: user=${user?.subscription_tier || 'null'}, tiers=${tiers ? Object.keys(tiers).length : 'null'}, available=${user && tiers ? isFeatureAvailable(feature) : 'N/A'}`);

  // Non-logged-in users see everything (gated by login elsewhere)
  if (!user) return <>{children}</>;

  // Feature available — render normally
  if (isFeatureAvailable(feature)) return <>{children}</>;

  const tierName = user.subscription_tier?.charAt(0).toUpperCase() + user.subscription_tier?.slice(1);

  const handleUpgrade = () => {
    if (Platform.OS === 'web') {
      router.push('/subscription');
    } else {
      router.push('/subscription');
    }
  };

  if (compact) {
    return (
      <TouchableOpacity
        style={styles.compactLock}
        onPress={handleUpgrade}
        activeOpacity={0.7}
        data-testid={`feature-gate-${feature}`}
      >
        <Ionicons name="lock-closed" size={12} color="#FF9800" />
        <Text style={styles.compactText}>{label}</Text>
        <Text style={styles.compactUpgrade}>Upgrade</Text>
      </TouchableOpacity>
    );
  }

  return (
    <View style={styles.container} data-testid={`feature-gate-${feature}`}>
      {/* Dimmed placeholder of the content */}
      <View style={styles.dimmedContent} pointerEvents="none">
        {children}
      </View>
      {/* Lock overlay */}
      <TouchableOpacity
        style={styles.overlay}
        onPress={handleUpgrade}
        activeOpacity={0.85}
      >
        <View style={styles.lockBadge}>
          <Ionicons name="lock-closed" size={18} color="#FF9800" />
          <View style={styles.lockTextWrap}>
            <Text style={styles.lockTitle}>{label}</Text>
            <Text style={styles.lockSubtitle}>
              Not included in {tierName} plan
            </Text>
          </View>
          <View style={styles.upgradeBtn}>
            <Ionicons name="arrow-up-circle" size={14} color="#fff" />
            <Text style={styles.upgradeBtnText}>Upgrade</Text>
          </View>
        </View>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    position: 'relative',
    overflow: 'hidden',
    borderRadius: 8,
  },
  dimmedContent: {
    opacity: 0.15,
  },
  overlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(0,0,0,0.6)',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#FF980033',
  },
  lockBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#1a1a1a',
    borderRadius: 8,
    paddingHorizontal: 14,
    paddingVertical: 10,
    gap: 10,
    borderWidth: 1,
    borderColor: '#FF980044',
  },
  lockTextWrap: {
    flexShrink: 1,
  },
  lockTitle: {
    fontSize: 12,
    fontWeight: '700',
    color: '#FF9800',
  },
  lockSubtitle: {
    fontSize: 9,
    color: '#888',
    marginTop: 1,
  },
  upgradeBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FF9800',
    borderRadius: 6,
    paddingHorizontal: 10,
    paddingVertical: 5,
    gap: 4,
  },
  upgradeBtnText: {
    fontSize: 11,
    fontWeight: '700',
    color: '#fff',
  },
  compactLock: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#1a1a1a',
    borderRadius: 6,
    paddingHorizontal: 10,
    paddingVertical: 8,
    gap: 6,
    borderWidth: 1,
    borderColor: '#FF980033',
    marginVertical: 4,
  },
  compactText: {
    fontSize: 11,
    color: '#888',
    flex: 1,
  },
  compactUpgrade: {
    fontSize: 10,
    fontWeight: '700',
    color: '#FF9800',
  },
});
