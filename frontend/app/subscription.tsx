import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ScrollView, ActivityIndicator, Alert, Linking, Platform } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useAuth } from '../context/AuthContext';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL || 'https://helpful-adaptation-production.up.railway.app';

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
  const [pendingRequest, setPendingRequest] = useState<any>(null);
  const [stripePolling, setStripePolling] = useState(false);
  const [stripeSuccess, setStripeSuccess] = useState(false);

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

  // Check admin + pending requests + stripe return
  useEffect(() => {
    if (token) {
      checkAdmin();
      checkPending();
      checkStripeReturn();
    }
  }, [token]);

  const checkAdmin = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/admin/check`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setIsAdmin(data.is_admin);
      }
    } catch (e) {}
  };

  const checkPending = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/subscription/pending`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setPendingRequest(data.pending);
      }
    } catch (e) {}
  };

  const checkStripeReturn = async () => {
    if (Platform.OS !== 'web') return;
    const params = new URLSearchParams(window.location.search);
    const sessionId = params.get('session_id');
    const paymentStatus = params.get('payment');

    // Handle Stripe return
    if (sessionId && paymentStatus === 'success') {
      setStripePolling(true);
      await pollStripeStatus(sessionId, 0);
      window.history.replaceState({}, '', window.location.pathname);
      return;
    }

    // Handle PayPal return
    if (paymentStatus === 'paypal_success') {
      const ppToken = params.get('token'); // PayPal appends token=ORDER_ID
      if (ppToken) {
        setStripePolling(true); // reuse the processing UI
        await capturePayPalOrder(ppToken);
        window.history.replaceState({}, '', window.location.pathname);
      }
    }
  };

  const capturePayPalOrder = async (orderId: string) => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/subscription/paypal-capture/${orderId}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        if (data.success) {
          setStripePolling(false);
          setStripeSuccess(true);
          await refreshUser();
          showAlert('PayPal Payment Successful!', `You've been upgraded to ${data.tier_name || 'your new plan'}!`);
          return;
        }
      }
    } catch (e) {}
    setStripePolling(false);
    showAlert('Payment Processing', 'Your PayPal payment is being verified. If your account is not upgraded shortly, please contact support.');
  };

  const pollStripeStatus = async (sessionId: string, attempt: number) => {
    if (attempt >= 5) {
      setStripePolling(false);
      showAlert('Payment Status', 'Payment is being processed. Your account will be upgraded shortly.');
      return;
    }
    try {
      const res = await fetch(`${BACKEND_URL}/api/subscription/stripe-status/${sessionId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        if (data.payment_status === 'paid') {
          setStripePolling(false);
          setStripeSuccess(true);
          await refreshUser();
          showAlert('Payment Successful!', `You've been upgraded to ${data.tier_name || 'your new plan'}!`);
          return;
        }
      }
    } catch (e) {}
    await new Promise(r => setTimeout(r, 2000));
    await pollStripeStatus(sessionId, attempt + 1);
  };

  const showAlert = (title: string, message: string) => {
    if (Platform.OS === 'web') {
      window.alert(`${title}\n\n${message}`);
    } else {
      Alert.alert(title, message);
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const handlePaymentSelect = (method: string) => {
    setSelectedPayment(method);
  };

  const handleUpgrade = async () => {
    if (!selectedTier || !selectedPayment) return;

    if (selectedPayment === 'stripe') {
      // Stripe: redirect to Stripe Checkout
      setLoading(true);
      try {
        const originUrl = Platform.OS === 'web' ? window.location.origin : BACKEND_URL;
        const res = await fetch(`${BACKEND_URL}/api/subscription/stripe-checkout`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ tier: selectedTier, origin_url: originUrl }),
        });
        const data = await res.json();
        if (res.ok && data.url) {
          if (Platform.OS === 'web') {
            window.location.href = data.url;
          } else {
            Linking.openURL(data.url);
          }
        } else {
          showAlert('Error', data.detail || 'Failed to start checkout');
        }
      } catch (e) {
        showAlert('Error', 'Network error. Please try again.');
      }
      setLoading(false);
      return;
    }

    if (selectedPayment === 'paypal') {
      // PayPal: redirect to PayPal Checkout
      setLoading(true);
      try {
        const originUrl = Platform.OS === 'web' ? window.location.origin : BACKEND_URL;
        const res = await fetch(`${BACKEND_URL}/api/subscription/paypal-checkout`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ tier: selectedTier, origin_url: originUrl }),
        });
        const data = await res.json();
        if (res.ok && data.url) {
          if (Platform.OS === 'web') {
            window.location.href = data.url;
          } else {
            Linking.openURL(data.url);
          }
        } else {
          showAlert('Error', data.detail || 'Failed to start PayPal checkout');
        }
      } catch (e) {
        showAlert('Error', 'Network error. Please try again.');
      }
      setLoading(false);
      return;
    }

    // CashApp: still manual (pending admin approval)
    setLoading(true);
    try {
      const result = await upgradeSubscription(selectedTier, selectedPayment);
      if (result.success) {
        await checkPending();
        showAlert(
          'Request Submitted',
          'Your upgrade request has been submitted. Your account will be upgraded once payment is verified by the admin.'
        );
        setSelectedTier(null);
        setSelectedPayment(null);
      } else {
        showAlert('Error', result.error || 'Failed to submit request');
      }
    } catch (error) {
      showAlert('Error', 'Failed to process upgrade request');
    }
    setLoading(false);
  };

  const getUserTierBase = () => {
    if (!user?.subscription_tier) return '';
    return user.subscription_tier.replace('_monthly', '').replace('_yearly', '');
  };

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

        {/* Admin Panel Button */}
        {isAdmin && (
          <TouchableOpacity style={styles.adminPanelBtn} onPress={() => router.push('/admin')}>
            <Ionicons name="settings" size={18} color="#fff" />
            <Text style={styles.adminPanelBtnText}>Admin Panel</Text>
            <Ionicons name="chevron-forward" size={18} color="#fff" />
          </TouchableOpacity>
        )}

        {/* Stripe Payment Processing */}
        {stripePolling && (
          <View style={styles.processingCard}>
            <ActivityIndicator size="large" color="#4CAF50" />
            <Text style={styles.processingText}>Verifying payment...</Text>
            <Text style={styles.processingSubtext}>Please wait while we confirm your payment</Text>
          </View>
        )}

        {/* Stripe Success */}
        {stripeSuccess && (
          <View style={[styles.statusBanner, { borderColor: '#4CAF50' }]}>
            <Ionicons name="checkmark-circle" size={24} color="#4CAF50" />
            <Text style={styles.statusBannerText}>Payment confirmed! Your account has been upgraded.</Text>
          </View>
        )}

        {/* Pending Request Banner */}
        {pendingRequest && (
          <View style={[styles.statusBanner, { borderColor: '#FF9800' }]}>
            <Ionicons name="time" size={24} color="#FF9800" />
            <View style={{ flex: 1 }}>
              <Text style={[styles.statusBannerText, { color: '#FF9800' }]}>Upgrade Pending</Text>
              <Text style={styles.statusBannerSubtext}>
                Your request for {pendingRequest.tier_name} via {pendingRequest.payment_method} is awaiting admin verification.
              </Text>
            </View>
          </View>
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
                onPress={() => { setBillingCycle('monthly'); setSelectedTier(null); setSelectedPayment(null); }}
              >
                <Text style={[styles.billingToggleText, billingCycle === 'monthly' && styles.billingToggleTextActive]}>
                  Monthly
                </Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.billingToggle, billingCycle === 'yearly' && styles.billingToggleActive]}
                onPress={() => { setBillingCycle('yearly'); setSelectedTier(null); setSelectedPayment(null); }}
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
                    <Text style={styles.planFeature}>Up to {tier.max_elements} elements</Text>
                    {tier.features.includes('all') ? (
                      <Text style={styles.planFeature}>All features unlocked</Text>
                    ) : (
                      tier.features.map((f: string, i: number) => (
                        <Text key={i} style={styles.planFeature}>{f.replace('_', ' ')}</Text>
                      ))
                    )}
                    {billingCycle === 'yearly' && (
                      <Text style={[styles.planFeature, { color: '#4CAF50', fontWeight: '600' }]}>
                        Save money vs monthly!
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

                {/* Stripe */}
                <TouchableOpacity
                  style={[styles.paymentCard, selectedPayment === 'stripe' && styles.paymentCardSelected]}
                  onPress={() => setSelectedPayment('stripe')}
                  data-testid="payment-stripe"
                >
                  <View style={styles.paymentHeader}>
                    <Ionicons name="card" size={28} color="#635BFF" />
                    <View style={styles.paymentInfo}>
                      <Text style={styles.paymentName}>Credit / Debit Card</Text>
                      <Text style={styles.paymentEmail}>Powered by Stripe — instant activation</Text>
                    </View>
                    {selectedPayment === 'stripe' && <Ionicons name="checkmark-circle" size={22} color="#4CAF50" />}
                  </View>
                </TouchableOpacity>

                {/* PayPal */}
                <TouchableOpacity
                  style={[styles.paymentCard, selectedPayment === 'paypal' && styles.paymentCardSelected]}
                  onPress={() => handlePaymentSelect('paypal')}
                  data-testid="payment-paypal"
                >
                  <View style={styles.paymentHeader}>
                    <Ionicons name="logo-paypal" size={28} color="#003087" />
                    <View style={styles.paymentInfo}>
                      <Text style={styles.paymentName}>PayPal</Text>
                      <Text style={styles.paymentEmail}>Pay securely with PayPal — instant activation</Text>
                    </View>
                    {selectedPayment === 'paypal' && <Ionicons name="checkmark-circle" size={22} color="#4CAF50" />}
                  </View>
                </TouchableOpacity>

                {/* CashApp */}
                <TouchableOpacity
                  style={[styles.paymentCard, selectedPayment === 'cashapp' && styles.paymentCardSelected]}
                  onPress={() => handlePaymentSelect('cashapp')}
                  data-testid="payment-cashapp"
                >
                  <View style={styles.paymentHeader}>
                    <View style={styles.cashAppIcon}>
                      <Text style={styles.cashAppText}>$</Text>
                    </View>
                    <View style={styles.paymentInfo}>
                      <Text style={styles.paymentName}>Cash App</Text>
                      <Text style={styles.paymentEmail}>{paymentMethods?.cashapp?.tag} — manual verification</Text>
                    </View>
                    {selectedPayment === 'cashapp' && <Ionicons name="checkmark-circle" size={22} color="#4CAF50" />}
                  </View>
                </TouchableOpacity>

                {/* Confirm Button */}
                <TouchableOpacity
                  style={[styles.confirmBtn, (!selectedPayment || loading) && styles.confirmBtnDisabled]}
                  onPress={handleUpgrade}
                  disabled={!selectedPayment || loading}
                  data-testid="confirm-payment-btn"
                >
                  {loading ? (
                    <ActivityIndicator color="#fff" />
                  ) : (
                    <>
                      <Text style={styles.confirmBtnText}>
                        {selectedPayment === 'stripe' ? 'Pay with Card' : selectedPayment === 'paypal' ? 'Pay with PayPal' : 'Submit Payment Request'}
                      </Text>
                      <Ionicons name="arrow-forward" size={18} color="#fff" />
                    </>
                  )}
                </TouchableOpacity>

                {selectedPayment === 'cashapp' && (
                  <Text style={styles.manualNote}>
                    Cash App payments require manual verification. Your account will be upgraded once the admin confirms your payment.
                  </Text>
                )}
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

  processingCard: { backgroundColor: '#1a2a1a', borderRadius: 12, padding: 24, alignItems: 'center', marginBottom: 16, borderWidth: 1, borderColor: '#4CAF50' },
  processingText: { color: '#4CAF50', fontSize: 16, fontWeight: '600', marginTop: 12 },
  processingSubtext: { color: '#888', fontSize: 13, marginTop: 4 },

  statusBanner: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#1E1E1E', borderRadius: 12, padding: 14, marginBottom: 16, borderWidth: 1, gap: 12 },
  statusBannerText: { color: '#4CAF50', fontSize: 14, fontWeight: '600' },
  statusBannerSubtext: { color: '#888', fontSize: 12, marginTop: 2 },

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
  paymentEmail: { fontSize: 12, color: '#888' },
  cashAppIcon: { width: 28, height: 28, backgroundColor: '#00D632', borderRadius: 6, justifyContent: 'center', alignItems: 'center' },
  cashAppText: { color: '#fff', fontSize: 18, fontWeight: 'bold' },

  confirmBtn: { backgroundColor: '#4CAF50', borderRadius: 12, padding: 16, flexDirection: 'row', justifyContent: 'center', alignItems: 'center', gap: 8, marginTop: 8 },
  confirmBtnDisabled: { backgroundColor: '#333' },
  confirmBtnText: { color: '#fff', fontSize: 16, fontWeight: '600' },

  manualNote: { fontSize: 12, color: '#666', textAlign: 'center', marginTop: 8, paddingHorizontal: 16, lineHeight: 18 },

  maxTierCard: { backgroundColor: '#1E1E1E', borderRadius: 12, padding: 24, alignItems: 'center', marginTop: 20 },
  maxTierTitle: { fontSize: 20, fontWeight: 'bold', color: '#FFD700', marginTop: 12 },
  maxTierDesc: { fontSize: 14, color: '#888', textAlign: 'center', marginTop: 8 },
});
