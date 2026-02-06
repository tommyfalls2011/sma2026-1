import React, { useState } from 'react';
import { View, Text, StyleSheet, TextInput, TouchableOpacity, ActivityIndicator, KeyboardAvoidingView, Platform, ScrollView, Linking } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useAuth } from './context/AuthContext';

export default function LoginScreen() {
  const router = useRouter();
  const { login, register } = useAuth();
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

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
                <Text style={styles.tierPrice}>$29.99</Text>
              </View>
              <View style={[styles.tierBadge, { backgroundColor: '#C0C0C0' }]}>
                <Text style={styles.tierBadgeText}>Silver</Text>
                <Text style={styles.tierPrice}>$49.99</Text>
              </View>
              <View style={[styles.tierBadge, { backgroundColor: '#FFD700' }]}>
                <Text style={styles.tierBadgeText}>Gold</Text>
                <Text style={styles.tierPrice}>$69.99</Text>
              </View>
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
  
  pricingPreview: { backgroundColor: '#1a1a1a', borderRadius: 16, padding: 16, marginBottom: 30 },
  pricingTitle: { fontSize: 14, fontWeight: '600', color: '#888', textAlign: 'center', marginBottom: 12 },
  tierRow: { flexDirection: 'row', justifyContent: 'space-around', gap: 8 },
  tierBadge: { alignItems: 'center', paddingVertical: 12, paddingHorizontal: 16, borderRadius: 10, minWidth: 90 },
  tierBadgeText: { color: '#000', fontSize: 12, fontWeight: '700' },
  tierPrice: { color: '#000', fontSize: 14, fontWeight: '800', marginTop: 2 },
});
