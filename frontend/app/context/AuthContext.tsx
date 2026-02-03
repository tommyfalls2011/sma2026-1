import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL || '';

interface User {
  id: string;
  email: string;
  name: string;
  subscription_tier: string;
  subscription_expires?: string;
  is_trial: boolean;
  trial_started?: string;
  is_active?: boolean;
  status_message?: string;
  max_elements?: number;
}

interface TierInfo {
  name: string;
  price: number;
  max_elements: number;
  features: string[];
  description: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  loading: boolean;
  tiers: Record<string, TierInfo> | null;
  paymentMethods: any;
  login: (email: string, password: string) => Promise<{ success: boolean; error?: string }>;
  register: (email: string, password: string, name: string) => Promise<{ success: boolean; error?: string }>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  upgradeSubscription: (tier: string, paymentMethod: string, reference?: string) => Promise<{ success: boolean; error?: string }>;
  getMaxElements: () => number;
  isFeatureAvailable: (feature: string) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [tiers, setTiers] = useState<Record<string, TierInfo> | null>(null);
  const [paymentMethods, setPaymentMethods] = useState<any>(null);

  useEffect(() => {
    loadStoredAuth();
    loadTiers();
  }, []);

  const loadStoredAuth = async () => {
    try {
      const storedToken = await AsyncStorage.getItem('authToken');
      if (storedToken) {
        setToken(storedToken);
        await fetchUserInfo(storedToken);
      }
    } catch (error) {
      console.error('Failed to load auth:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadTiers = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/subscription/tiers`);
      if (response.ok) {
        const data = await response.json();
        setTiers(data.tiers);
        setPaymentMethods(data.payment_methods);
      }
    } catch (error) {
      console.error('Failed to load tiers:', error);
    }
  };

  const fetchUserInfo = async (authToken: string) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/auth/me`, {
        headers: { Authorization: `Bearer ${authToken}` }
      });
      if (response.ok) {
        const userData = await response.json();
        setUser(userData);
      } else {
        await logout();
      }
    } catch (error) {
      console.error('Failed to fetch user:', error);
    }
  };

  const login = async (email: string, password: string): Promise<{ success: boolean; error?: string }> => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });

      const data = await response.json();

      if (response.ok) {
        await AsyncStorage.setItem('authToken', data.token);
        setToken(data.token);
        setUser(data.user);
        return { success: true };
      } else {
        return { success: false, error: data.detail || 'Login failed' };
      }
    } catch (error) {
      return { success: false, error: 'Network error' };
    }
  };

  const register = async (email: string, password: string, name: string): Promise<{ success: boolean; error?: string }> => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, name })
      });

      const data = await response.json();

      if (response.ok) {
        await AsyncStorage.setItem('authToken', data.token);
        setToken(data.token);
        setUser(data.user);
        return { success: true };
      } else {
        return { success: false, error: data.detail || 'Registration failed' };
      }
    } catch (error) {
      return { success: false, error: 'Network error' };
    }
  };

  const logout = async () => {
    await AsyncStorage.removeItem('authToken');
    setToken(null);
    setUser(null);
  };

  const refreshUser = async () => {
    if (token) {
      await fetchUserInfo(token);
    }
  };

  const upgradeSubscription = async (tier: string, paymentMethod: string, reference?: string): Promise<{ success: boolean; error?: string }> => {
    if (!token) return { success: false, error: 'Not authenticated' };

    try {
      const response = await fetch(`${BACKEND_URL}/api/subscription/upgrade`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ tier, payment_method: paymentMethod, payment_reference: reference })
      });

      const data = await response.json();

      if (response.ok) {
        await refreshUser();
        return { success: true };
      } else {
        return { success: false, error: data.detail || 'Upgrade failed' };
      }
    } catch (error) {
      return { success: false, error: 'Network error' };
    }
  };

  const getMaxElements = (): number => {
    if (!user) return 3;
    return user.max_elements || tiers?.[user.subscription_tier]?.max_elements || 3;
  };

  const isFeatureAvailable = (feature: string): boolean => {
    if (!user || !tiers) return false;
    const tierInfo = tiers[user.subscription_tier];
    if (!tierInfo) return false;
    return tierInfo.features.includes('all') || tierInfo.features.includes(feature);
  };

  return (
    <AuthContext.Provider value={{
      user,
      token,
      loading,
      tiers,
      paymentMethods,
      login,
      register,
      logout,
      refreshUser,
      upgradeSubscription,
      getMaxElements,
      isFeatureAvailable
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
