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
  bronze_monthly: '#CD7F32',
  bronze_yearly: '#CD7F32',
  silver: '#C0C0C0',
  silver_monthly: '#C0C0C0',
  silver_yearly: '#C0C0C0',
  gold: '#FFD700',
  gold_monthly: '#FFD700',
  gold_yearly: '#FFD700',
  subadmin: '#9C27B0',
  admin: '#f44336'
};

const TIER_ICONS: Record<string, any> = {
  trial: 'time-outline',
  bronze: 'shield-outline',
  bronze_monthly: 'shield-outline',
  bronze_yearly: 'shield-outline',
  silver: 'shield-half-outline',
  silver_monthly: 'shield-half-outline',
  silver_yearly: 'shield-half-outline',
  gold: 'shield-checkmark',
  gold_monthly: 'shield-checkmark',
  gold_yearly: 'shield-checkmark',
  subadmin: 'key-outline',
  admin: 'key'
};

export default function SubscriptionScreen() {
  const router = useRouter();
  const { user, token, tiers, paymentMethods, upgradeSubscription, refreshUser, logout, getMaxElements } = useAuth();
  const [selectedTier, setSelectedTier] = useState<string | null>(null);
  const [selectedPayment, setSelectedPayment] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [trialRemaining, setTrialRemaining] = useState<number | null>(null);
  const [isAdmin, setIsAdmin] = useState(false);
  const [billingCycle, setBillingCycle] = useState<'monthly' | 'yearly'>('monthly');

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
        `Send payment to:\n\n${paymentMethods.paypal.email}\n\nInclude your email (${user?.email}) in the payment note.`,
        [
          { text: 'Copy Email', onPress: () => {} },
          { text: 'Open PayPal', onPress: () => Linking.openURL(`https://paypal.me/${paymentMethods.paypal.email.split('@')[0]}`) },
          { text: 'OK' }
        ]
      );
    } else if (method === 'cashapp' && paymentMethods?.cashapp?.tag) {
      Alert.alert(
        'Cash App Payment',
        `Send payment to:\n\n${paymentMethods.cashapp.tag}\n\nInclude your email (${user?.email}) in the payment note.`,
        [
          { text: 'Copy Tag', onPress: () => {} },
          { text: 'Open Cash App', onPress: () => Linking.openURL(`https://cash.app/${paymentMethods.cashapp.tag}`) },
          { text: 'OK' }
        ]
      );
    }
  };

  const handleUpgrade = async () => {
    if (!selectedTier || !selectedPayment) return;
    
    setLoading(true);
    try {
      const success = await upgradeSubscription(selectedTier, selectedPayment);
      if (success) {
        Alert.alert(
          'Upgrade Requested',
          'Your upgrade request has been submitted. Your account will be upgraded once payment is verified.',
          [{ text: 'OK', onPress: () => router.back() }]
        );
      }
    } catch (error) {
      Alert.alert('Error', 'Failed to process upgrade request');
    }
    setLoading(false);
  };

  // Get current user tier base (e.g., "bronze" from "bronze_monthly")
  const getUserTierBase = () => {
    if (!user?.subscription_tier) return '';
    return user.subscription_tier.replace('_monthly', '').replace('_yearly', '');
  };

  // Filter and group tiers by base tier (bronze, silver, gold)
  const getDisplayTiers = () => {
    if (!tiers) return [];
    
    const baseTiers = ['bronze', 'silver', 'gold'];
    return baseTiers.map(base => {
      const monthlyKey = `${base}_monthly`;
      const yearlyKey = `${base}_yearly`;
      const monthly = tiers[monthlyKey];
      const yearly = tiers[yearlyKey];
      
      if (!monthly || !yearly) return null;
      
      return {
        base,
        monthly: { ...monthly, key: monthlyKey },
        yearly: { ...yearly, key: yearlyKey },
        color: TIER_COLORS[base],
        icon: TIER_ICONS[base]
      };
    }).filter(Boolean);
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

  const displayTiers = getDisplayTiers();
  const userTierBase = getUserTierBase();

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
        <View style={[styles.statusCard, { borderColor: TIER_COLORS[user.subscription_tier] || '#888' }]}>
          <View style={styles.statusHeader}>
            <Ionicons name={TIER_ICONS[user.subscription_tier] || 'person'} size={28} color={TIER_COLORS[user.subscription_tier] || '#888'} />
            <View style={styles.statusInfo}>
              <Text style={styles.statusName}>{user.name}</Text>
              <Text style={styles.statusEmail}>{user.email}</Text>
            </View>
          </View>
          <View style={styles.statusDetails}>
            <View style={[styles.tierBadge, { backgroundColor: TIER_COLORS[user.subscription_tier] || '#888' }]}>
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
          <Text style={styles.maxElements}>Max Elements: {getMaxElements()}</Text>
        </View>

        {/* Upgrade Plans */}
        {userTierBase !== 'gold' && user.subscription_tier !== 'admin' && (
          <>
            <Text style={styles.sectionTitle}>Upgrade Your Plan</Text>
            
            {/* Billing Cycle Toggle */}
            <View style={styles.billingToggleContainer}>
              <TouchableOpacity
                style={[styles.billingToggle, billingCycle === 'monthly' && styles.billingToggleActive]}
                onPress={() => { setBillingCycle('monthly'); setSelectedTier(null); }}
              >
                <Text style={[styles.billingToggleText, billingCycle === 'monthly' && styles.billingToggleTextActive]}>
                  Monthly
                </Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.billingToggle, billingCycle === 'yearly' && styles.billingToggleActive]}
                onPress={() => { setBillingCycle('yearly'); setSelectedTier(null); }}
              >
                <Text style={[styles.billingToggleText, billingCycle === 'yearly' && styles.billingToggleTextActive]}>
                  Yearly
                </Text>
                <View style={styles.saveBadge}>
                  <Text style={styles.saveBadgeText}>SAVE!</Text>
                </View>
              </TouchableOpacity>
            </View>

            {/* Plan Cards */}
            {displayTiers.map((tierGroup: any) => {
              const tier = billingCycle === 'monthly' ? tierGroup.monthly : tierGroup.yearly;
              const tierKey = tier.key;
              const isCurrentTier = userTierBase === tierGroup.base;
              
              return (
                <TouchableOpacity
                  key={tierKey}
                  style={[
                    styles.planCard,
                    { borderColor: tierGroup.color },
                    selectedTier === tierKey && styles.planCardSelected,
                    isCurrentTier && styles.planCardCurrent
                  ]}
                  onPress={() => !isCurrentTier && setSelectedTier(tierKey)}
                  disabled={isCurrentTier}
                >
                  <View style={styles.planHeader}>
                    <Ionicons name={tierGroup.icon} size={24} color={tierGroup.color} />
                    <Text style={[styles.planName, { color: tierGroup.color }]}>
                      {tierGroup.base.charAt(0).toUpperCase() + tierGroup.base.slice(1)}
                    </Text>
                    {isCurrentTier ? (
                      <View style={styles.currentBadge}>
                        <Text style={styles.currentBadgeText}>CURRENT</Text>
                      </View>
                    ) : selectedTier === tierKey ? (
                      <Ionicons name="checkmark-circle" size={22} color="#4CAF50" style={styles.checkIcon} />
                    ) : null}
                  </View>
                  <Text style={styles.planPrice}>
                    ${tier.price}
                    <Text style={styles.planPeriod}>/{billingCycle === 'monthly' ? 'month' : 'year'}</Text>
                  </Text>
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
                    {billingCycle === 'yearly' && (
                      <Text style={[styles.planFeature, { color: '#4CAF50', fontWeight: '600' }]}>
                        • Save money vs monthly!
                      </Text>
                    )}
                  </View>
                </TouchableOpacity>
              );
            })}

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

        {/* Already at max tier */}
        {(userTierBase === 'gold' || user.subscription_tier === 'admin') && (
          <View style={styles.maxTierCard}>
            <Ionicons name="trophy" size={48} color="#FFD700" />
            <Text style={styles.maxTierTitle}>You have full access!</Text>
            <Text style={styles.maxTierDesc}>
              Enjoy all features with your {tiers?.[user.subscription_tier]?.name || 'Premium'} subscription.
            </Text>
          </View>
        )}

        <View style={{ height: 40 }} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#121212' },
  scrollView: { flex: 1 },
  scrollContent: { padding: 16 },
  centered: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  message: { fontSize: 16, color: '#888', marginBottom: 16 },
  loginBtn: { backgroundColor: '#2196F3', paddingVertical: 12, paddingHorizontal: 24, borderRadius: 8 },
  loginBtnText: { color: '#fff', fontSize: 16, fontWeight: '600' },
  
  header: { flexDirection: 'row', alignItems: 'center', marginBottom: 16, paddingVertical: 8 },
  backBtn: { padding: 4 },
  headerTitle: { flex: 1, fontSize: 20, fontWeight: 'bold', color: '#fff', marginLeft: 12 },
  logoutBtn: { padding: 4 },
  
  adminPanelBtn: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#1E1E1E', padding: 12, borderRadius: 8, marginBottom: 16, gap: 8 },
  adminPanelBtnText: { flex: 1, color: '#fff', fontSize: 14, fontWeight: '500' },
  
  statusCard: { backgroundColor: '#1E1E1E', borderRadius: 12, padding: 16, marginBottom: 20, borderWidth: 2 },
  statusHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 12 },
  statusInfo: { marginLeft: 12, flex: 1 },
  statusName: { fontSize: 18, fontWeight: 'bold', color: '#fff' },
  statusEmail: { fontSize: 13, color: '#888' },
  statusDetails: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  tierBadge: { paddingHorizontal: 12, paddingVertical: 4, borderRadius: 12 },
  tierBadgeText: { color: '#121212', fontSize: 12, fontWeight: 'bold' },
  trialTimer: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  trialTimerText: { fontSize: 14, color: '#FFC107', fontWeight: '600' },
  maxElements: { fontSize: 12, color: '#888', marginTop: 8 },
  
  sectionTitle: { fontSize: 18, fontWeight: '600', color: '#fff', marginBottom: 12, marginTop: 8 },
  
  billingToggleContainer: { flexDirection: 'row', backgroundColor: '#1E1E1E', borderRadius: 12, padding: 4, marginBottom: 16 },
  billingToggle: { flex: 1, paddingVertical: 12, paddingHorizontal: 16, borderRadius: 10, alignItems: 'center', flexDirection: 'row', justifyContent: 'center', gap: 6 },
  billingToggleActive: { backgroundColor: '#2196F3' },
  billingToggleText: { fontSize: 15, color: '#888', fontWeight: '600' },
  billingToggleTextActive: { color: '#fff' },
  saveBadge: { backgroundColor: '#4CAF50', paddingHorizontal: 6, paddingVertical: 2, borderRadius: 4 },
  saveBadgeText: { color: '#fff', fontSize: 10, fontWeight: 'bold' },
  
  planCard: { backgroundColor: '#1E1E1E', borderRadius: 12, padding: 16, marginBottom: 12, borderWidth: 2 },
  planCardSelected: { backgroundColor: '#1a2a1a', borderColor: '#4CAF50' },
  planCardCurrent: { opacity: 0.6 },
  planHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 8 },
  planName: { fontSize: 18, fontWeight: 'bold', marginLeft: 8, flex: 1 },
  checkIcon: { marginLeft: 'auto' },
  currentBadge: { backgroundColor: '#666', paddingHorizontal: 8, paddingVertical: 2, borderRadius: 4 },
  currentBadgeText: { color: '#fff', fontSize: 10, fontWeight: 'bold' },
  planPrice: { fontSize: 28, fontWeight: 'bold', color: '#fff', marginBottom: 4 },
  planPeriod: { fontSize: 14, color: '#888', fontWeight: 'normal' },
  planDesc: { fontSize: 13, color: '#888', marginBottom: 12 },
  planFeatures: { gap: 4 },
  planFeature: { fontSize: 13, color: '#aaa' },
  
  paymentCard: { backgroundColor: '#1E1E1E', borderRadius: 12, padding: 16, marginBottom: 12, borderWidth: 2, borderColor: '#333' },
  paymentCardSelected: { borderColor: '#4CAF50', backgroundColor: '#1a2a1a' },
  paymentHeader: { flexDirection: 'row', alignItems: 'center' },
  paymentInfo: { marginLeft: 12, flex: 1 },
  paymentName: { fontSize: 16, fontWeight: '600', color: '#fff' },
  paymentEmail: { fontSize: 13, color: '#888' },
  cashAppIcon: { width: 28, height: 28, backgroundColor: '#00D632', borderRadius: 6, justifyContent: 'center', alignItems: 'center' },
  cashAppText: { color: '#fff', fontSize: 18, fontWeight: 'bold' },
  
  confirmBtn: { backgroundColor: '#4CAF50', borderRadius: 12, padding: 16, flexDirection: 'row', justifyContent: 'center', alignItems: 'center', gap: 8, marginTop: 8 },
  confirmBtnDisabled: { backgroundColor: '#333' },
  confirmBtnText: { color: '#fff', fontSize: 16, fontWeight: '600' },
  
  maxTierCard: { backgroundColor: '#1E1E1E', borderRadius: 12, padding: 24, alignItems: 'center', marginTop: 20 },
  maxTierTitle: { fontSize: 20, fontWeight: 'bold', color: '#FFD700', marginTop: 12 },
  maxTierDesc: { fontSize: 14, color: '#888', textAlign: 'center', marginTop: 8 },
});
