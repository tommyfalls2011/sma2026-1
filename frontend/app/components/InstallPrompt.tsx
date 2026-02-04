import React, { useState, useEffect } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, Platform, Animated } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import AsyncStorage from '@react-native-async-storage/async-storage';

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
}

const InstallPrompt: React.FC = () => {
  const [showPrompt, setShowPrompt] = useState(false);
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const [isInstalled, setIsInstalled] = useState(false);
  const slideAnim = useState(new Animated.Value(100))[0];

  useEffect(() => {
    if (Platform.OS !== 'web') return;

    // Check if already installed
    const checkInstalled = () => {
      if (typeof window !== 'undefined') {
        const isStandalone = window.matchMedia('(display-mode: standalone)').matches;
        const isInWebAppiOS = (window.navigator as any).standalone === true;
        setIsInstalled(isStandalone || isInWebAppiOS);
      }
    };
    checkInstalled();

    // Check if user dismissed the prompt before
    const checkDismissed = async () => {
      try {
        const dismissed = await AsyncStorage.getItem('pwa_prompt_dismissed');
        if (dismissed) {
          const dismissedTime = parseInt(dismissed);
          // Show again after 7 days
          if (Date.now() - dismissedTime < 7 * 24 * 60 * 60 * 1000) {
            return true;
          }
        }
        return false;
      } catch {
        return false;
      }
    };

    // Listen for the beforeinstallprompt event
    const handleBeforeInstall = async (e: Event) => {
      e.preventDefault();
      const wasDismissed = await checkDismissed();
      if (!wasDismissed) {
        setDeferredPrompt(e as BeforeInstallPromptEvent);
        setShowPrompt(true);
        // Animate in
        Animated.spring(slideAnim, {
          toValue: 0,
          useNativeDriver: true,
          friction: 8,
        }).start();
      }
    };

    window.addEventListener('beforeinstallprompt', handleBeforeInstall);

    // Listen for successful install
    window.addEventListener('appinstalled', () => {
      setShowPrompt(false);
      setIsInstalled(true);
    });

    return () => {
      window.removeEventListener('beforeinstallprompt', handleBeforeInstall);
    };
  }, []);

  const handleInstall = async () => {
    if (!deferredPrompt) return;

    try {
      await deferredPrompt.prompt();
      const { outcome } = await deferredPrompt.userChoice;
      
      if (outcome === 'accepted') {
        setShowPrompt(false);
      }
      setDeferredPrompt(null);
    } catch (error) {
      console.error('Install error:', error);
    }
  };

  const handleDismiss = async () => {
    Animated.timing(slideAnim, {
      toValue: 100,
      duration: 200,
      useNativeDriver: true,
    }).start(() => {
      setShowPrompt(false);
    });
    
    try {
      await AsyncStorage.setItem('pwa_prompt_dismissed', Date.now().toString());
    } catch {}
  };

  // Also show manual instructions for iOS
  const isIOS = Platform.OS === 'web' && typeof navigator !== 'undefined' && /iPad|iPhone|iPod/.test(navigator.userAgent);

  if (Platform.OS !== 'web' || isInstalled) return null;

  // iOS manual install instructions
  if (isIOS && !showPrompt) {
    return (
      <IOSInstallBanner />
    );
  }

  if (!showPrompt) return null;

  return (
    <Animated.View style={[styles.container, { transform: [{ translateY: slideAnim }] }]}>
      <View style={styles.content}>
        <View style={styles.iconContainer}>
          <Ionicons name="radio-outline" size={28} color="#4CAF50" />
        </View>
        <View style={styles.textContainer}>
          <Text style={styles.title}>Install Antenna Analyzer</Text>
          <Text style={styles.subtitle}>Add to home screen for quick access</Text>
        </View>
      </View>
      <View style={styles.buttons}>
        <TouchableOpacity style={styles.dismissBtn} onPress={handleDismiss}>
          <Text style={styles.dismissText}>Later</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.installBtn} onPress={handleInstall}>
          <Ionicons name="download-outline" size={18} color="#fff" />
          <Text style={styles.installText}>Install</Text>
        </TouchableOpacity>
      </View>
    </Animated.View>
  );
};

// iOS Install Banner (manual instructions)
const IOSInstallBanner: React.FC = () => {
  const [show, setShow] = useState(false);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    const checkDismissed = async () => {
      try {
        const d = await AsyncStorage.getItem('ios_install_dismissed');
        if (d && Date.now() - parseInt(d) < 7 * 24 * 60 * 60 * 1000) {
          setDismissed(true);
        }
      } catch {}
    };
    checkDismissed();
    
    // Check if in standalone mode
    if (typeof window !== 'undefined') {
      const isStandalone = (window.navigator as any).standalone === true;
      if (!isStandalone) {
        setTimeout(() => setShow(true), 2000);
      }
    }
  }, []);

  const handleDismiss = async () => {
    setShow(false);
    setDismissed(true);
    try {
      await AsyncStorage.setItem('ios_install_dismissed', Date.now().toString());
    } catch {}
  };

  if (!show || dismissed) return null;

  return (
    <View style={styles.iosBanner}>
      <View style={styles.iosContent}>
        <Ionicons name="share-outline" size={20} color="#007AFF" />
        <Text style={styles.iosText}>
          Tap <Ionicons name="share-outline" size={14} color="#007AFF" /> then "Add to Home Screen"
        </Text>
      </View>
      <TouchableOpacity onPress={handleDismiss}>
        <Ionicons name="close" size={20} color="#888" />
      </TouchableOpacity>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    backgroundColor: '#1a1a1a',
    borderTopWidth: 1,
    borderTopColor: '#333',
    padding: 16,
    paddingBottom: 24,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: -4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 10,
    zIndex: 9999,
  },
  content: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  iconContainer: {
    width: 48,
    height: 48,
    borderRadius: 12,
    backgroundColor: 'rgba(76,175,80,0.15)',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  textContainer: {
    flex: 1,
  },
  title: {
    fontSize: 15,
    fontWeight: '600',
    color: '#fff',
  },
  subtitle: {
    fontSize: 12,
    color: '#888',
    marginTop: 2,
  },
  buttons: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  dismissBtn: {
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  dismissText: {
    fontSize: 14,
    color: '#888',
  },
  installBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: '#4CAF50',
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 20,
  },
  installText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#fff',
  },
  // iOS Banner styles
  iosBanner: {
    position: 'absolute',
    bottom: 20,
    left: 16,
    right: 16,
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 14,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.15,
    shadowRadius: 8,
    elevation: 5,
    zIndex: 9999,
  },
  iosContent: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    flex: 1,
  },
  iosText: {
    fontSize: 13,
    color: '#333',
    flex: 1,
  },
});

export default InstallPrompt;
