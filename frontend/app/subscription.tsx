import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ScrollView, ActivityIndicator, Alert, Linking } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useAuth } from './context/AuthContext';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL || '';

const TIER_COLORS: Record<string, string> = {
  trial: '#888',
  bronze: '#CD7F32',
  silver: '#C0C0C0',
  gold: '#FFD700',
  subadmin: '#9C27B0',
  admin: '#f44336'
};

const TIER_ICONS: Record<string, any> = {
  trial: 'time-outline',
  bronze: 'shield-outline',
  silver: 'shield-half-outline',
  gold: 'shield-checkmark',
  subadmin: 'key-outline',
  admin: 'key'
};

export default function SubscriptionScreen() {
  const router = useRouter();
  const { user, token, tiers, paymentMethods, upgradeSubscription, refreshUser, logout } = useAuth();
  const [selectedTier, setSelectedTier] = useState<string | null>(null);
  const [selectedPayment, setSelectedPayment] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [trialRemaining, setTrialRemaining] = useState<number | null>(null);
  const [isAdmin, setIsAdmin] = useState(false);

  useEffect(() => {
    if (user?.is_trial && user?.trial_started) {
      const updateTimer = () => {
        const started = new Date(user.trial_started!);
        const now = new Date();
        const elapsed = (now.getTime() - started.getTime()) / 1000;
        const remaining = Math.max(0, 3600 - elapsed);
        setTrialRemaining(remaining);
      };
      updateTimer();
      const interval = setInterval(updateTimer, 1000);
      return () => clearInterval(interval);
    }
  }, [user]);

  // Check if user is admin
  useEffect(() => {
    const checkAdmin = async () => {
      if (token) {
        try {
          const res = await fetch(`${BACKEND_URL}/api/admin/check`, {
            headers: { Authorization: `Bearer ${token}` }
          });
          if (res.ok) {
            const data = await res.json();
            setIsAdmin(data.is_admin);
          }
        } catch (e) {}
      }
    };
    checkAdmin();
  }, [token]);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const handlePaymentSelect = (method: string) => {
    setSelectedPayment(method);
    if (method === 'paypal' && paymentMethods?.paypal?.email) {
      Alert.alert(
        'PayPal Payment',
        `Send payment to:\n\n${paymentMethods.paypal.email}\n\nAmount: $${tiers?.[selectedTier!]?.price}\n\nAfter payment, click "Confirm Payment"`,
        [
          { text: 'Copy Email', onPress: () => {} },
          { text: 'OK' }
        ]
      );
    } else if (method === 'cashapp' && paymentMethods?.cashapp?.tag) {
      Alert.alert(
        'Cash App Payment',
        `Send payment to:\n\n${paymentMethods.cashapp.tag}\n\nAmount: $${tiers?.[selectedTier!]?.price}\n\nAfter payment, click "Confirm Payment"`,
        [
          { text: 'Open Cash App', onPress: () => Linking.openURL(`https://cash.app/${paymentMethods.cashapp.tag.replace('$', '')}`) },
          { text: 'OK' }
        ]
      );
    }
  };

  const handleUpgrade = async () => {
    if (!selectedTier || !selectedPayment) {
      Alert.alert('Error', 'Please select a plan and payment method');
      return;
    }

    Alert.alert(
      'Confirm Payment',
      `Have you completed the ${selectedPayment === 'paypal' ? 'PayPal' : 'Cash App'} payment of $${tiers?.[selectedTier]?.price}?`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Yes, Confirm',
          onPress: async () => {
            setLoading(true);
            const result = await upgradeSubscription(selectedTier, selectedPayment);
            setLoading(false);
            if (result.success) {
              Alert.alert('Success', `Upgraded to ${tiers?.[selectedTier]?.name}!`, [
                { text: 'OK', onPress: () => router.back() }
              ]);
            } else {
              Alert.alert('Error', result.error || 'Upgrade failed');
            }
          }
        }
      ]
    );
  };

  if (!user) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.centered}>
          <Text style={styles.message}>Please login to view subscription</Text>
          <TouchableOpacity style={styles.loginBtn} onPress={() => router.replace('/login')}>
            <Text style={styles.loginBtnText}>Go to Login</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView style={styles.scrollView} contentContainerStyle={styles.scrollContent}>
        
        {/* Header */}
        <View style={styles.header}>
          <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
            <Ionicons name="arrow-back" size={24} color="#fff" />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Subscription</Text>
          <TouchableOpacity onPress={logout} style={styles.logoutBtn}>
            <Ionicons name="log-out-outline" size={22} color="#f44336" />
          </TouchableOpacity>
        </View>

        {/* Admin Panel Button (only for admin) */}
        {isAdmin && (
          <TouchableOpacity style={styles.adminPanelBtn} onPress={() => router.push('/admin')}>
            <Ionicons name="settings" size={18} color="#fff" />
            <Text style={styles.adminPanelBtnText}>Admin Panel</Text>
            <Ionicons name="chevron-forward" size={18} color="#fff" />
          </TouchableOpacity>
        )}

        {/* Current Status */}
        <View style={[styles.statusCard, { borderColor: TIER_COLORS[user.subscription_tier] }]}>
          <View style={styles.statusHeader}>
            <Ionicons name={TIER_ICONS[user.subscription_tier]} size={28} color={TIER_COLORS[user.subscription_tier]} />
            <View style={styles.statusInfo}>
              <Text style={styles.statusName}>{user.name}</Text>
              <Text style={styles.statusEmail}>{user.email}</Text>
            </View>
          </View>
          <View style={styles.statusDetails}>
            <View style={[styles.tierBadge, { backgroundColor: TIER_COLORS[user.subscription_tier] }]}>
              <Text style={styles.tierBadgeText}>{tiers?.[user.subscription_tier]?.name || user.subscription_tier}</Text>
            </View>
            {user.is_trial && trialRemaining !== null && (
              <View style={styles.trialTimer}>
                <Ionicons name="time" size={14} color={trialRemaining < 600 ? '#f44336' : '#FFC107'} />
                <Text style={[styles.trialTimerText, trialRemaining < 600 && { color: '#f44336' }]}>
                  {trialRemaining > 0 ? formatTime(trialRemaining) : 'Expired'}
                </Text>
              </View>
            )}
          </View>
          <Text style={styles.maxElements}>Max Elements: {tiers?.[user.subscription_tier]?.max_elements || 3}</Text>
        </View>

        {/* Upgrade Plans */}
        {user.subscription_tier !== 'gold' && user.subscription_tier !== 'admin' && (
          <>
            <Text style={styles.sectionTitle}>Upgrade Your Plan</Text>
            
            {tiers && Object.entries(tiers)
              .filter(([key]) => key !== 'trial' && key !== 'admin')
              .map(([key, tier]) => (
                <TouchableOpacity
                  key={key}
                  style={[
                    styles.planCard,
                    { borderColor: TIER_COLORS[key] },
                    selectedTier === key && styles.planCardSelected
                  ]}
                  onPress={() => setSelectedTier(key)}
                >
                  <View style={styles.planHeader}>
                    <Ionicons name={TIER_ICONS[key]} size={24} color={TIER_COLORS[key]} />
                    <Text style={[styles.planName, { color: TIER_COLORS[key] }]}>{tier.name}</Text>
                    {selectedTier === key && (
                      <Ionicons name="checkmark-circle" size={22} color="#4CAF50" style={styles.checkIcon} />
                    )}
                  </View>
                  <Text style={styles.planPrice}>${tier.price}<Text style={styles.planPeriod}>/month</Text></Text>
                  <Text style={styles.planDesc}>{tier.description}</Text>
                  <View style={styles.planFeatures}>
                    <Text style={styles.planFeature}>• Up to {tier.max_elements} elements</Text>
                    {tier.features.includes('all') ? (
                      <Text style={styles.planFeature}>• All features unlocked</Text>
                    ) : (
                      tier.features.map((f: string, i: number) => (
                        <Text key={i} style={styles.planFeature}>• {f.replace('_', ' ')}</Text>
                      ))
                    )}
                  </View>
                </TouchableOpacity>
              ))}

            {/* Payment Methods */}
            {selectedTier && (
              <>
                <Text style={styles.sectionTitle}>Payment Method</Text>
                
                <TouchableOpacity
                  style={[styles.paymentCard, selectedPayment === 'paypal' && styles.paymentCardSelected]}
                  onPress={() => handlePaymentSelect('paypal')}
                >
                  <View style={styles.paymentHeader}>
                    <Ionicons name="logo-paypal" size={28} color="#003087" />
                    <View style={styles.paymentInfo}>
                      <Text style={styles.paymentName}>PayPal</Text>
                      <Text style={styles.paymentEmail}>{paymentMethods?.paypal?.email}</Text>
                    </View>
                    {selectedPayment === 'paypal' && <Ionicons name="checkmark-circle" size={22} color="#4CAF50" />}
                  </View>
                </TouchableOpacity>

                <TouchableOpacity
                  style={[styles.paymentCard, selectedPayment === 'cashapp' && styles.paymentCardSelected]}
                  onPress={() => handlePaymentSelect('cashapp')}
                >
                  <View style={styles.paymentHeader}>
                    <View style={styles.cashAppIcon}>
                      <Text style={styles.cashAppText}>$</Text>
                    </View>
                    <View style={styles.paymentInfo}>
                      <Text style={styles.paymentName}>Cash App</Text>
                      <Text style={styles.paymentEmail}>{paymentMethods?.cashapp?.tag}</Text>
                    </View>
                    {selectedPayment === 'cashapp' && <Ionicons name="checkmark-circle" size={22} color="#4CAF50" />}
                  </View>
                </TouchableOpacity>

                {/* Confirm Button */}
                <TouchableOpacity
                  style={[styles.confirmBtn, (!selectedPayment || loading) && styles.confirmBtnDisabled]}
                  onPress={handleUpgrade}
                  disabled={!selectedPayment || loading}
                >
                  {loading ? (
                    <ActivityIndicator color="#fff" />
                  ) : (
                    <>
                      <Text style={styles.confirmBtnText}>Confirm Payment</Text>
                      <Ionicons name="arrow-forward" size={18} color="#fff" />
                    </>
                  )}
                </TouchableOpacity>
              </>
            )}
          </>
        )}

        {/* Gold/Admin Message */}
        {(user.subscription_tier === 'gold' || user.subscription_tier === 'admin') && (
          <View style={styles.maxTierCard}>
            <Ionicons name="star" size={40} color="#FFD700" />
            <Text style={styles.maxTierTitle}>You have full access!</Text>
            <Text style={styles.maxTierDesc}>
              Enjoy all features with unlimited elements.
            </Text>
          </View>
        )}

      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#121212' },
  scrollView: { flex: 1 },
  scrollContent: { padding: 16, paddingBottom: 40 },
  centered: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 20 },
  message: { color: '#888', fontSize: 16, marginBottom: 20 },
  loginBtn: { backgroundColor: '#4CAF50', paddingHorizontal: 24, paddingVertical: 12, borderRadius: 8 },
  loginBtnText: { color: '#fff', fontWeight: '600' },

  header: { flexDirection: 'row', alignItems: 'center', marginBottom: 20 },
  backBtn: { padding: 8 },
  headerTitle: { flex: 1, fontSize: 20, fontWeight: 'bold', color: '#fff', textAlign: 'center' },
  logoutBtn: { padding: 8 },

  statusCard: { backgroundColor: '#1a1a1a', borderRadius: 12, padding: 16, marginBottom: 20, borderWidth: 2 },
  statusHeader: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  statusInfo: { flex: 1 },
  statusName: { fontSize: 18, fontWeight: '600', color: '#fff' },
  statusEmail: { fontSize: 13, color: '#888' },
  statusDetails: { flexDirection: 'row', alignItems: 'center', marginTop: 12, gap: 12 },
  tierBadge: { paddingHorizontal: 12, paddingVertical: 4, borderRadius: 12 },
  tierBadgeText: { color: '#000', fontSize: 12, fontWeight: '700' },
  trialTimer: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  trialTimerText: { color: '#FFC107', fontSize: 14, fontWeight: '600' },
  maxElements: { color: '#888', fontSize: 12, marginTop: 8 },

  sectionTitle: { fontSize: 16, fontWeight: '600', color: '#fff', marginBottom: 12, marginTop: 8 },

  planCard: { backgroundColor: '#1a1a1a', borderRadius: 12, padding: 16, marginBottom: 12, borderWidth: 2, borderColor: '#333' },
  planCardSelected: { borderColor: '#4CAF50', backgroundColor: '#1f2f1f' },
  planHeader: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  planName: { fontSize: 18, fontWeight: '700', flex: 1 },
  checkIcon: { marginLeft: 'auto' },
  planPrice: { fontSize: 28, fontWeight: '800', color: '#fff', marginTop: 8 },
  planPeriod: { fontSize: 14, fontWeight: '400', color: '#888' },
  planDesc: { fontSize: 13, color: '#888', marginTop: 4 },
  planFeatures: { marginTop: 12 },
  planFeature: { fontSize: 12, color: '#aaa', marginBottom: 2 },

  paymentCard: { backgroundColor: '#1a1a1a', borderRadius: 12, padding: 16, marginBottom: 12, borderWidth: 2, borderColor: '#333' },
  paymentCardSelected: { borderColor: '#4CAF50' },
  paymentHeader: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  paymentInfo: { flex: 1 },
  paymentName: { fontSize: 16, fontWeight: '600', color: '#fff' },
  paymentEmail: { fontSize: 13, color: '#888' },
  cashAppIcon: { width: 28, height: 28, backgroundColor: '#00D632', borderRadius: 6, justifyContent: 'center', alignItems: 'center' },
  cashAppText: { color: '#fff', fontWeight: '800', fontSize: 18 },

  confirmBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', backgroundColor: '#4CAF50', borderRadius: 12, padding: 16, marginTop: 8, gap: 8 },
  confirmBtnDisabled: { backgroundColor: '#333' },
  confirmBtnText: { color: '#fff', fontSize: 16, fontWeight: '600' },

  maxTierCard: { backgroundColor: '#1a1a1a', borderRadius: 12, padding: 30, alignItems: 'center', marginTop: 20 },
  maxTierTitle: { fontSize: 20, fontWeight: '700', color: '#FFD700', marginTop: 12 },
  maxTierDesc: { fontSize: 14, color: '#888', textAlign: 'center', marginTop: 8 },
});
