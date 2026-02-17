'use client';

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';

// Lazy imports for SSR compatibility
let AsyncStorage: any = null;
let NetInfo: any = null;
if (typeof window !== 'undefined') {
  try { AsyncStorage = require('@react-native-async-storage/async-storage').default; } catch {}
  try { NetInfo = require('@react-native-community/netinfo').default; } catch {}
}

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL || 'https://helpful-adaptation-production.up.railway.app';
const MAX_RETRIES = 3;
const RETRY_DELAY = 1000; // 1 second

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
  isOnline: boolean;
  login: (email: string, password: string) => Promise<{ success: boolean; error?: string }>;
  register: (email: string, password: string, name: string) => Promise<{ success: boolean; error?: string }>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  upgradeSubscription: (tier: string, paymentMethod: string, reference?: string) => Promise<{ success: boolean; error?: string }>;
  getMaxElements: () => number;
  isFeatureAvailable: (feature: string) => boolean;
  retryConnection: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Helper function for fetch with retry and timeout
const fetchWithRetry = async (
  url: string, 
  options: RequestInit = {}, 
  retries = MAX_RETRIES,
  timeout = 10000
): Promise<Response> => {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);
  
  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
    return response;
  } catch (error: any) {
    clearTimeout(timeoutId);
    
    if (retries > 0 && (error.name === 'AbortError' || error.message === 'Network request failed')) {
      console.log(`Retrying... (${MAX_RETRIES - retries + 1}/${MAX_RETRIES})`);
      await new Promise(resolve => setTimeout(resolve, RETRY_DELAY));
      return fetchWithRetry(url, options, retries - 1, timeout);
    }
    throw error;
  }
};

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [tiers, setTiers] = useState<Record<string, TierInfo> | null>(null);
  const [paymentMethods, setPaymentMethods] = useState<any>(null);
  const [isOnline, setIsOnline] = useState(true);

  // Monitor network status
  useEffect(() => {
    const unsubscribe = NetInfo.addEventListener(state => {
      setIsOnline(state.isConnected ?? true);
    });
    
    return () => unsubscribe();
  }, []);

  useEffect(() => {
    loadStoredAuth();
    loadTiers();
  }, []);

  // Retry loading when coming back online
  useEffect(() => {
    if (isOnline && !tiers) {
      loadTiers();
    }
    if (isOnline && token && !user) {
      fetchUserInfo(token);
    }
  }, [isOnline]);

  const loadStoredAuth = async () => {
    try {
      const storedToken = await AsyncStorage.getItem('authToken');
      const storedUser = await AsyncStorage.getItem('cachedUser');
      
      // Load cached user immediately for faster UI
      if (storedUser) {
        try {
          setUser(JSON.parse(storedUser));
        } catch {}
      }
      
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
      const response = await fetchWithRetry(`${BACKEND_URL}/api/subscription/tiers`);
      if (response.ok) {
        const data = await response.json();
        setTiers(data.tiers);
        setPaymentMethods(data.payment_methods);
        // Cache tiers for offline use
        await AsyncStorage.setItem('cachedTiers', JSON.stringify(data));
      }
    } catch (error) {
      console.error('Failed to load tiers:', error);
      // Try to load from cache
      try {
        const cached = await AsyncStorage.getItem('cachedTiers');
        if (cached) {
          const data = JSON.parse(cached);
          setTiers(data.tiers);
          setPaymentMethods(data.payment_methods);
        }
      } catch {}
    }
  };

  const fetchUserInfo = async (authToken: string) => {
    try {
      const response = await fetchWithRetry(`${BACKEND_URL}/api/auth/me`, {
        headers: { Authorization: `Bearer ${authToken}` }
      });
      if (response.ok) {
        const userData = await response.json();
        setUser(userData);
        // Cache user for offline/fast loading
        await AsyncStorage.setItem('cachedUser', JSON.stringify(userData));
      } else if (response.status === 401) {
        // Only logout on explicit token expiry, not transient errors
        const errorData = await response.json().catch(() => ({}));
        if (errorData.detail === 'Token expired') {
          await logout();
        }
        // For other 401s (network, server restart), keep cached user
      }
    } catch (error) {
      console.error('Failed to fetch user:', error);
      // Keep using cached user if available
    }
  };

  const login = async (email: string, password: string): Promise<{ success: boolean; error?: string }> => {
    if (!isOnline) {
      return { success: false, error: 'No internet connection. Please check your network.' };
    }
    
    try {
      const response = await fetchWithRetry(`${BACKEND_URL}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });

      const data = await response.json();

      if (response.ok) {
        await AsyncStorage.setItem('authToken', data.token);
        await AsyncStorage.setItem('cachedUser', JSON.stringify(data.user));
        setToken(data.token);
        setUser(data.user);
        return { success: true };
      } else {
        return { success: false, error: data.detail || 'Login failed' };
      }
    } catch (error: any) {
      if (error.name === 'AbortError') {
        return { success: false, error: 'Connection timed out. Please try again.' };
      }
      return { success: false, error: 'Network error. Please check your internet connection.' };
    }
  };

  const register = async (email: string, password: string, name: string): Promise<{ success: boolean; error?: string }> => {
    if (!isOnline) {
      return { success: false, error: 'No internet connection. Please check your network.' };
    }
    
    try {
      const response = await fetchWithRetry(`${BACKEND_URL}/api/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, name })
      });

      const data = await response.json();

      if (response.ok) {
        await AsyncStorage.setItem('authToken', data.token);
        await AsyncStorage.setItem('cachedUser', JSON.stringify(data.user));
        setToken(data.token);
        setUser(data.user);
        return { success: true };
      } else {
        return { success: false, error: data.detail || 'Registration failed' };
      }
    } catch (error: any) {
      if (error.name === 'AbortError') {
        return { success: false, error: 'Connection timed out. Please try again.' };
      }
      return { success: false, error: 'Network error. Please check your internet connection.' };
    }
  };

  const logout = async () => {
    await AsyncStorage.removeItem('authToken');
    await AsyncStorage.removeItem('cachedUser');
    setToken(null);
    setUser(null);
  };

  const refreshUser = async () => {
    if (token) {
      await fetchUserInfo(token);
    }
  };

  const retryConnection = async () => {
    await loadTiers();
    if (token) {
      await fetchUserInfo(token);
    }
  };

  const upgradeSubscription = async (tier: string, paymentMethod: string, reference?: string): Promise<{ success: boolean; error?: string }> => {
    if (!token) return { success: false, error: 'Not authenticated' };
    if (!isOnline) return { success: false, error: 'No internet connection' };

    try {
      const response = await fetchWithRetry(`${BACKEND_URL}/api/subscription/upgrade`, {
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
    } catch (error: any) {
      if (error.name === 'AbortError') {
        return { success: false, error: 'Connection timed out. Please try again.' };
      }
      return { success: false, error: 'Network error. Please try again.' };
    }
  };

  const getMaxElements = (): number => {
    if (!user) return 3;
    // Admin and subadmin get 20 elements
    if (user.subscription_tier === 'admin' || user.subscription_tier === 'subadmin') return 20;
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
      isOnline,
      login,
      register,
      logout,
      refreshUser,
      upgradeSubscription,
      getMaxElements,
      isFeatureAvailable,
      retryConnection
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
