import React, { useState } from 'react';
import { View, Text, StyleSheet, TextInput, TouchableOpacity, ActivityIndicator, KeyboardAvoidingView, Platform, ScrollView, Linking } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useAuth } from './context/AuthContext';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL || 'https://helpful-adaptation-production.up.railway.app';

export default function LoginScreen() {
  const router = useRouter();
  const { login, register } = useAuth();
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [showForgotPassword, setShowForgotPassword] = useState(false);
  const [resetEmail, setResetEmail] = useState('');
  const [resetCode, setResetCode] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [resetStep, setResetStep] = useState<'email' | 'code'>('email');
  const [resetMessage, setResetMessage] = useState('');

  const handleForgotPassword = async () => {
    if (resetStep === 'email') {
      if (!resetEmail) { setError('Enter your email'); return; }
      setLoading(true);
      try {
        const res = await fetch(`${BACKEND_URL}/api/auth/forgot-password`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email: resetEmail }),
        });
        const data = await res.json();
        setResetMessage(data.message);
        setResetStep('code');
        setError('');
      } catch (e) { setError('Failed to send reset email'); }
      setLoading(false);
    } else {
      if (!resetCode || !newPassword) { setError('Enter code and new password'); return; }
      setLoading(true);
      try {
        const res = await fetch(`${BACKEND_URL}/api/auth/reset-password`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ token: resetCode, new_password: newPassword }),
        });
        if (res.ok) {
          setResetMessage('Password reset! You can now sign in.');
          setTimeout(() => { setShowForgotPassword(false); setResetStep('email'); setResetMessage(''); setResetCode(''); setNewPassword(''); setResetEmail(''); }, 2000);
        } else {
          const data = await res.json();
          setError(data.detail || 'Invalid code');
        }
      } catch (e) { setError('Reset failed'); }
      setLoading(false);
    }
  };

  const handleSubmit = async () => {
    setError('');
    if (!email || !password || (!isLogin && !name)) {
      setError('Please fill in all fields');
      return;
    }

    setLoading(true);
    try {
      let result;
      if (isLogin) {
        result = await login(email, password);
      } else {
        result = await register(email, password, name);
      }

      if (result.success) {
        router.replace('/');
      } else {
        setError(result.error || 'Authentication failed');
      }
    } catch (err) {
      setError('An error occurred');
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={styles.flex}>
        <ScrollView contentContainerStyle={styles.scrollContent} keyboardShouldPersistTaps="handled">
          
          {/* Logo */}
          <View style={styles.logoContainer}>
            <Ionicons name="radio-outline" size={60} color="#4CAF50" />
            <Text style={styles.logoTitle}>Antenna Calculator</Text>
            <Text style={styles.logoSubtitle}>Professional RF Design Tool</Text>
          </View>

          {/* Form Card */}
          <View style={styles.formCard}>
            <Text style={styles.formTitle}>{isLogin ? 'Welcome Back' : 'Create Account'}</Text>
            <Text style={styles.formSubtitle}>
              {isLogin ? 'Sign in to continue' : 'Start with a 1-hour free trial'}
            </Text>

            {error ? (
              <View style={styles.errorBox}>
                <Ionicons name="alert-circle" size={16} color="#f44336" />
                <Text style={styles.errorText}>{error}</Text>
              </View>
            ) : null}

            {!isLogin && (
              <View style={styles.inputGroup}>
                <Text style={styles.inputLabel}>Full Name</Text>
                <View style={styles.inputWrapper}>
                  <Ionicons name="person-outline" size={18} color="#888" style={styles.inputIcon} />
                  <TextInput
                    style={styles.input}
                    placeholder="John Doe"
                    placeholderTextColor="#555"
                    value={name}
                    onChangeText={setName}
                    autoCapitalize="words"
                  />
                </View>
              </View>
            )}

            <View style={styles.inputGroup}>
              <Text style={styles.inputLabel}>Email</Text>
              <View style={styles.inputWrapper}>
                <Ionicons name="mail-outline" size={18} color="#888" style={styles.inputIcon} />
                <TextInput
                  style={styles.input}
                  placeholder="email@example.com"
                  placeholderTextColor="#555"
                  value={email}
                  onChangeText={setEmail}
                  keyboardType="email-address"
                  autoCapitalize="none"
                />
              </View>
            </View>

            <View style={styles.inputGroup}>
              <Text style={styles.inputLabel}>Password</Text>
              <View style={styles.inputWrapper}>
                <Ionicons name="lock-closed-outline" size={18} color="#888" style={styles.inputIcon} />
                <TextInput
                  style={styles.input}
                  placeholder="••••••••"
                  placeholderTextColor="#555"
                  value={password}
                  onChangeText={setPassword}
                  secureTextEntry
                />
              </View>
            </View>

            <TouchableOpacity style={styles.submitButton} onPress={handleSubmit} disabled={loading}>
              {loading ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <>
                  <Text style={styles.submitButtonText}>{isLogin ? 'Sign In' : 'Create Account'}</Text>
                  <Ionicons name="arrow-forward" size={18} color="#fff" />
                </>
              )}
            </TouchableOpacity>

            <TouchableOpacity style={styles.switchButton} onPress={() => { setIsLogin(!isLogin); setError(''); }}>
              <Text style={styles.switchButtonText}>
                {isLogin ? "Don't have an account? " : 'Already have an account? '}
                <Text style={styles.switchButtonLink}>{isLogin ? 'Sign Up' : 'Sign In'}</Text>
              </Text>
            </TouchableOpacity>
          </View>

          {/* Pricing Preview */}
          <View style={styles.pricingPreview}>
            <Text style={styles.pricingTitle}>Subscription Plans</Text>
            <View style={styles.tierRow}>
              <View style={[styles.tierBadge, { backgroundColor: '#CD7F32' }]}>
                <Text style={styles.tierBadgeText}>Bronze</Text>
                <Text style={styles.tierPrice}>$39.99/mo</Text>
              </View>
              <View style={[styles.tierBadge, { backgroundColor: '#C0C0C0' }]}>
                <Text style={styles.tierBadgeText}>Silver</Text>
                <Text style={styles.tierPrice}>$59.99/mo</Text>
              </View>
              <View style={[styles.tierBadge, { backgroundColor: '#FFD700' }]}>
                <Text style={styles.tierBadgeText}>Gold</Text>
                <Text style={styles.tierPrice}>$99.99/mo</Text>
              </View>
            </View>
            <Text style={styles.yearlyHint}>Yearly plans available - Save up to $150!</Text>
          </View>

          {/* Expo Go Download Section */}
          <View style={styles.expoSection}>
            <Text style={styles.expoTitle}>📱 Using Expo Go?</Text>
            <Text style={styles.expoDesc}>Download the Expo Go app to test this app on your phone</Text>
            <View style={styles.expoButtons}>
              <TouchableOpacity 
                style={styles.expoButton}
                onPress={() => Linking.openURL('https://play.google.com/store/apps/details?id=host.exp.exponent')}
              >
                <Ionicons name="logo-google-playstore" size={18} color="#fff" />
                <Text style={styles.expoButtonText}>Google Play</Text>
              </TouchableOpacity>
              <TouchableOpacity 
                style={styles.expoButton}
                onPress={() => Linking.openURL('https://apps.apple.com/app/expo-go/id982107779')}
              >
                <Ionicons name="logo-apple" size={18} color="#fff" />
                <Text style={styles.expoButtonText}>App Store</Text>
              </TouchableOpacity>
            </View>
          </View>

        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#121212' },
  flex: { flex: 1 },
  scrollContent: { padding: 20, minHeight: '100%' },
  
  logoContainer: { alignItems: 'center', marginTop: 30, marginBottom: 30 },
  logoTitle: { fontSize: 26, fontWeight: 'bold', color: '#fff', marginTop: 12 },
  logoSubtitle: { fontSize: 14, color: '#888', marginTop: 4 },
  
  formCard: { backgroundColor: '#1a1a1a', borderRadius: 16, padding: 24, marginBottom: 20 },
  formTitle: { fontSize: 22, fontWeight: 'bold', color: '#fff', marginBottom: 4 },
  formSubtitle: { fontSize: 14, color: '#888', marginBottom: 20 },
  
  errorBox: { flexDirection: 'row', alignItems: 'center', backgroundColor: 'rgba(244,67,54,0.1)', padding: 12, borderRadius: 8, marginBottom: 16, gap: 8 },
  errorText: { color: '#f44336', fontSize: 13, flex: 1 },
  
  inputGroup: { marginBottom: 16 },
  inputLabel: { fontSize: 12, color: '#aaa', marginBottom: 6, fontWeight: '500' },
  inputWrapper: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#252525', borderRadius: 10, borderWidth: 1, borderColor: '#333' },
  inputIcon: { paddingLeft: 14 },
  input: { flex: 1, padding: 14, fontSize: 15, color: '#fff' },
  
  submitButton: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', backgroundColor: '#4CAF50', borderRadius: 10, padding: 16, marginTop: 8, gap: 8 },
  submitButtonText: { color: '#fff', fontSize: 16, fontWeight: '600' },
  
  switchButton: { marginTop: 20, alignItems: 'center' },
  switchButtonText: { color: '#888', fontSize: 14 },
  switchButtonLink: { color: '#4CAF50', fontWeight: '600' },
  
  pricingPreview: { backgroundColor: '#1a1a1a', borderRadius: 16, padding: 16, marginBottom: 16 },
  pricingTitle: { fontSize: 14, fontWeight: '600', color: '#888', textAlign: 'center', marginBottom: 12 },
  tierRow: { flexDirection: 'row', justifyContent: 'space-around', gap: 8 },
  tierBadge: { alignItems: 'center', paddingVertical: 12, paddingHorizontal: 16, borderRadius: 10, minWidth: 90 },
  tierBadgeText: { color: '#000', fontSize: 12, fontWeight: '700' },
  tierPrice: { color: '#000', fontSize: 13, fontWeight: '800', marginTop: 2 },
  yearlyHint: { textAlign: 'center', color: '#4CAF50', fontSize: 12, marginTop: 12, fontWeight: '500' },
  
  expoSection: { backgroundColor: '#1a1a1a', borderRadius: 16, padding: 16, marginBottom: 30, borderWidth: 1, borderColor: '#333' },
  expoTitle: { fontSize: 16, fontWeight: '600', color: '#fff', textAlign: 'center', marginBottom: 4 },
  expoDesc: { fontSize: 12, color: '#888', textAlign: 'center', marginBottom: 12 },
  expoButtons: { flexDirection: 'row', justifyContent: 'center', gap: 12 },
  expoButton: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#333', paddingVertical: 10, paddingHorizontal: 16, borderRadius: 8, gap: 6 },
  expoButtonText: { color: '#fff', fontSize: 13, fontWeight: '500' },
});
