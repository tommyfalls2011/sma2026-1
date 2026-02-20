import React, { useState, useCallback, useEffect, useRef } from 'react';
import { View, Text, ScrollView, TextInput, TouchableOpacity, Pressable, ActivityIndicator, KeyboardAvoidingView, Platform, Dimensions, Switch, Alert, Modal, FlatList, AppState, Linking } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import Svg, { Circle, Line, Path, Text as SvgText, Rect, G } from 'react-native-svg';
import { useRouter } from 'expo-router';
import { useAuth } from '../context/AuthContext';
import AsyncStorage from '@react-native-async-storage/async-storage';
import appJson from '../app.json';

import {
  styles, TIER_COLORS, BANDS, COAX_OPTIONS,
  ResultCard, SwrMeter, PolarPattern, ElevationPattern, SmithChart,
  Dropdown, ElementInput, SpecSection, SpecRow,
} from '../components';
import { FeatureGate } from '../components/FeatureGate';
import { GammaDesigner } from '../components/GammaDesigner';
import { PhysicsDebugPanel } from '../components/PhysicsDebugPanel';
import type { ElementDimension, TaperSection, TaperConfig, CoronaBallConfig, StackingConfig, AntennaInput, AntennaOutput, HeightOptResult } from '../components';

// Lazy-load native-only modules to avoid SSR crash
let FileSystem: any = null;
let Sharing: any = null;
let Constants: any = null;
if (Platform.OS !== 'web') {
  try { FileSystem = require('expo-file-system/legacy'); } catch {}
  try { Sharing = require('expo-sharing'); } catch {}
  try { Constants = require('expo-constants'); } catch {}
}

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL || 'https://helpful-adaptation-production.up.railway.app';
const screenWidth = typeof window !== 'undefined' ? Dimensions.get('window').width : 400;
const APP_VERSION = appJson.expo.version;
const APP_BUILD_DATE = '2026-02-10T12:00:00';
const UPDATE_CHECK_URL = 'https://gist.githubusercontent.com/tommyfalls2011/3bb5c9e586bfa929d26da16776b0b9c6/raw/';

export default function AntennaCalculator() {
  const router = useRouter();
  const { user, token, loading: authLoading, getMaxElements, isFeatureAvailable, tiers } = useAuth();
  
  // Feature gate helper — returns true if feature is available, shows upgrade alert if not
  const checkFeature = (feature: string, featureLabel: string): boolean => {
    if (!user) return true; // Non-logged-in users get unrestricted UI (they're gated by login/subscription elsewhere)
    if (isFeatureAvailable(feature)) return true;
    Alert.alert('Upgrade Required', `"${featureLabel}" is not available on your ${user.subscription_tier} plan. Upgrade to unlock this feature!`, [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Upgrade', onPress: () => router.push('/subscription') }
    ]);
    return false;
  };
  const [inputs, setInputs] = useState<AntennaInput>({
    num_elements: 2,
    elements: [
      { element_type: 'reflector', length: '216', diameter: '0.5', position: '0' },
      { element_type: 'driven', length: '204', diameter: '0.5', position: '48' },
    ],
    height_from_ground: '54', height_unit: 'ft', boom_diameter: '1.5', boom_unit: 'inches', band: '11m_cb', frequency_mhz: '27.185',
    stacking: { enabled: false, orientation: 'vertical', layout: 'line', num_antennas: 2, spacing: '20', spacing_unit: 'ft', h_spacing: '20', h_spacing_unit: 'ft' },
    taper: { enabled: false, num_tapers: 2, center_length: '36', sections: [{ length: '36', start_diameter: '0.625', end_diameter: '0.5' }, { length: '36', start_diameter: '0.5', end_diameter: '0.375' }] },
    corona_balls: { enabled: false, diameter: '1.0' },
    ground_radials: { enabled: false, ground_type: 'average', wire_diameter: '0.5', num_radials: 8 },
    use_reflector: true,
    antenna_orientation: 'horizontal',  // horizontal (flat), vertical, angle45, or dual
    dual_active: false,  // When dual: both H+V beams transmit simultaneously
    dual_selected_beam: 'horizontal' as 'horizontal' | 'vertical',  // Which beam is selected in dual mode
    feed_type: 'gamma',  // direct, gamma, hairpin
    boom_grounded: true,  // legacy compat
    boom_mount: 'bonded' as 'bonded' | 'insulated' | 'nonconductive',  // bonded, insulated, nonconductive
  });
  const [results, setResults] = useState<AntennaOutput | null>(null);
  const [heightOptResult, setHeightOptResult] = useState<HeightOptResult | null>(null);
  const [optimizingHeight, setOptimizingHeight] = useState(false);
  const [loading, setLoading] = useState(false);
  const [tuning, setTuning] = useState(false);
  const [elementUnit, setElementUnit] = useState<'inches' | 'meters'>('inches');
  const debounceRef = useRef<NodeJS.Timeout | null>(null);
  
  // Boom Lock and Spacing Lock state
  const [boomLockEnabled, setBoomLockEnabled] = useState(false);
  const [maxBoomLength, setMaxBoomLength] = useState('120');  // Default 10 feet in inches
  const [spacingLockEnabled, setSpacingLockEnabled] = useState(false);
  
  // Element Spacing Mode
  const [spacingMode, setSpacingMode] = useState<'normal' | 'tight' | 'long'>('normal');
  const [spacingLevel, setSpacingLevel] = useState('1.0');
  
  // Spacing Overrides for Auto-Tune
  const [closeDriven, setCloseDriven] = useState<string | false>(false);
  const [farDriven, setFarDriven] = useState<string | false>(false);
  const [closeDir1, setCloseDir1] = useState<string | false>(false);
  const [farDir1, setFarDir1] = useState<string | false>(false);
  const [closeDir2, setCloseDir2] = useState<string | false>(false);
  const [farDir2, setFarDir2] = useState<string | false>(false);
  
  // Fine-tune nudge for element positions (±10% total range, 0.5% per step)
  const [drivenNudgeCount, setDrivenNudgeCount] = useState(0); // -10 to +10 steps
  const [dir1NudgeCount, setDir1NudgeCount] = useState(0); // -10 to +10 steps
  const [dir2NudgeCount, setDir2NudgeCount] = useState(0); // -10 to +10 steps
  const [spacingNudgeCount, setSpacingNudgeCount] = useState(0); // -10 to +10 steps
  const [rlTuning, setRlTuning] = useState(false);
  const [showDebugPanel, setShowDebugPanel] = useState(false);
  const [rlResult, setRlResult] = useState<any>(null);

  // Coax feedline settings
  const [coaxType, setCoaxType] = useState('ldf5-50a');
  const [coaxLengthFt, setCoaxLengthFt] = useState('100');
  const [transmitPowerWatts, setTransmitPowerWatts] = useState('500');

  // Hairpin design adjustments
  const [hairpinRodDia, setHairpinRodDia] = useState('0.25');
  const [hairpinRodSpacing, setHairpinRodSpacing] = useState('1.0');
  const [hairpinBarPos, setHairpinBarPos] = useState(0.5); // 0-1 ratio along hairpin length
  const [hairpinBoomGap, setHairpinBoomGap] = useState(1.0); // inches from rods to boom
  // Gamma design adjustments
  const [gammaRodDia, setGammaRodDia] = useState<string | null>(null);
  const [gammaRodSpacing, setGammaRodSpacing] = useState<string | null>('3.5');
  const [gammaCapPf, setGammaCapPf] = useState<string | null>(null);
  const [gammaBarPos, setGammaBarPos] = useState(18); // shorting bar position in inches from feedpoint center
  const [gammaRodInsertion, setGammaRodInsertion] = useState(8.0); // rod insertion into tube in inches
  const [originalDrivenLength, setOriginalDrivenLength] = useState<string | null>(null);

  // Apply feed type shortening to driven element
  const switchFeedType = (newType: string) => {
    setInputs(prev => {
      const e = [...prev.elements];
      const drivenIdx = e.findIndex(el => el.element_type === 'driven');
      if (drivenIdx >= 0) {
        const currentLen = parseFloat(e[drivenIdx].length) || 0;
        const oldType = prev.feed_type;
        // Restore to original first
        let baseLen = currentLen;
        if (oldType === 'gamma' && originalDrivenLength) baseLen = parseFloat(originalDrivenLength);
        else if (oldType === 'hairpin' && originalDrivenLength) baseLen = parseFloat(originalDrivenLength);
        else baseLen = currentLen;
        // Save original if first time switching from direct
        if (oldType === 'direct' || !originalDrivenLength) {
          setOriginalDrivenLength(e[drivenIdx].length);
          baseLen = currentLen;
        }
        // Apply new shortening
        if (newType === 'gamma') {
          e[drivenIdx] = { ...e[drivenIdx], length: (baseLen * 0.97).toFixed(3) };
        } else if (newType === 'hairpin') {
          e[drivenIdx] = { ...e[drivenIdx], length: (baseLen * 0.96).toFixed(3) };
        } else {
          // Direct — restore original
          if (originalDrivenLength) {
            e[drivenIdx] = { ...e[drivenIdx], length: originalDrivenLength };
            setOriginalDrivenLength(null);
          }
        }
      }
      return { ...prev, feed_type: newType, elements: e };
    });
  };
  
  const SPACING_OPTIONS = {
    tight: [
      { value: '0.6', label: 'Very Tight (60%)' },
      { value: '0.75', label: 'Tight (75%)' },
      { value: '0.85', label: 'Mod Tight (85%)' },
    ],
    long: [
      { value: '1.15', label: 'Mod Long (115%)' },
      { value: '1.3', label: 'Long (130%)' },
      { value: '1.5', label: 'Very Long (150%)' },
    ],
  };

  const applySpacing = (factor: string) => {
    const f = parseFloat(factor);
    const oldF = parseFloat(spacingLevel) || 1;
    setSpacingLevel(factor);
    setInputs(prev => ({
      ...prev,
      elements: prev.elements.map((el, i) => {
        if (i === 0) return el;
        const basePos = parseFloat(el.position);
        const firstPos = parseFloat(prev.elements[0].position);
        const relativePos = basePos - firstPos;
        const newPos = firstPos + (relativePos * f / oldF);
        return { ...el, position: newPos.toFixed(3) };
      })
    }));
  };

  // Nudge element position by 0.5% per click, ±45% max
  const nudgeElement = (type: 'driven' | 'dir1' | 'dir2', direction: number) => {
    const STEP = 0.5;
    const MAX = 45;
    const currentCount = type === 'driven' ? drivenNudgeCount : type === 'dir1' ? dir1NudgeCount : dir2NudgeCount;
    const newCount = currentCount + direction;
    if (newCount * STEP > MAX || newCount * STEP < -MAX) return;
    if (type === 'driven') setDrivenNudgeCount(newCount);
    else if (type === 'dir1') setDir1NudgeCount(newCount);
    else setDir2NudgeCount(newCount);
    setInputs(prev => {
      const e = [...prev.elements];
      let targetIdx: number;
      if (type === 'driven') {
        targetIdx = e.findIndex(el => el.element_type === 'driven');
      } else if (type === 'dir1') {
        targetIdx = e.findIndex(el => el.element_type === 'director');
      } else {
        // dir2: find the second director
        const firstDir = e.findIndex(el => el.element_type === 'director');
        targetIdx = firstDir >= 0 ? e.findIndex((el, i) => i > firstDir && el.element_type === 'director') : -1;
      }
      if (targetIdx >= 0) {
        const pos = parseFloat(e[targetIdx].position) || 1;
        const step = pos * (STEP / 100);
        e[targetIdx] = { ...e[targetIdx], position: (pos + direction * step).toFixed(3) };
      }
      return { ...prev, elements: e };
    });
  };

  // Nudge ALL element spacing by 0.5% per click, ±45% max
  const nudgeSpacing = (direction: number) => {
    const STEP = 0.5;
    const MAX = 45;
    const newCount = spacingNudgeCount + direction;
    if (newCount * STEP > MAX || newCount * STEP < -MAX) return;
    setSpacingNudgeCount(newCount);
    setInputs(prev => {
      const e = [...prev.elements];
      for (let i = 1; i < e.length; i++) {
        const pos = parseFloat(e[i].position) || 0;
        if (pos > 0) {
          const step = pos * (STEP / 100);
          e[i] = { ...e[i], position: (pos + direction * step).toFixed(3) };
        }
      }
      return { ...prev, elements: e };
    });
  };

  // Height optimizer sort option
  const [heightSortBy, setHeightSortBy] = useState<'default' | 'takeoff' | 'gain' | 'fb'>('default');
  
  // Save/Load state
  const [showSaveModal, setShowSaveModal] = useState(false);
  const [showLoadModal, setShowLoadModal] = useState(false);
  const [designName, setDesignName] = useState('');
  const [savedDesigns, setSavedDesigns] = useState<any[]>([]);

  // Return Loss Tune — sweep spacings to find best match
  const runReturnLossTune = async () => {
    setRlTuning(true);
    setRlResult(null);
    try {
      const elementsForRl = elementUnit === 'meters'
        ? inputs.elements.map((e: any) => ({ element_type: e.element_type, length: parseFloat(e.length) * 39.3701, diameter: parseFloat(e.diameter) * 39.3701, position: parseFloat(e.position) * 39.3701 }))
        : inputs.elements.map((e: any) => ({ element_type: e.element_type, length: parseFloat(e.length) || 0, diameter: parseFloat(e.diameter) || 0, position: parseFloat(e.position) || 0 }));
      const body = {
        num_elements: inputs.elements.length,
        band: inputs.band,
        frequency_mhz: parseFloat(inputs.frequency_mhz) || null,
        feed_type: inputs.feed_type,
        antenna_orientation: inputs.antenna_orientation,
        height_from_ground: parseFloat(inputs.height_from_ground) || 0,
        height_unit: inputs.height_unit,
        boom_diameter: parseFloat(inputs.boom_diameter) || 0,
        boom_unit: inputs.boom_unit,
        boom_grounded: inputs.boom_mount === 'bonded',
        boom_mount: inputs.boom_mount,
        gamma_bar_pos: gammaBarPos,
        gamma_element_gap: gammaRodInsertion,
        elements: elementsForRl,
      };
      const res = await fetch(`${BACKEND_URL}/api/optimize-return-loss`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      if (!res.ok) { setRlTuning(false); return; }
      const data = await res.json();
      setRlResult(data);
      if (data?.best_elements?.length) {
        const newElements = data.best_elements.map((e: any) => ({
          element_type: e.element_type,
          length: String(elementUnit === 'meters' ? (e.length / 39.3701).toFixed(4) : e.length),
          diameter: String(elementUnit === 'meters' ? (e.diameter / 39.3701).toFixed(4) : e.diameter),
          position: String(elementUnit === 'meters' ? (e.position / 39.3701).toFixed(4) : e.position),
        }));
        setInputs((p: any) => ({ ...p, elements: newElements }));
        setDrivenNudgeCount(0);
        setDir1NudgeCount(0);
        setSpacingNudgeCount(0);
      }
    } catch (err) {
      console.error('RL tune error:', err);
    }
    setRlTuning(false);
  };

  const applyRlResult = () => {
    if (!rlResult?.best_elements) return;
    const newElements = rlResult.best_elements.map((e: any) => ({
      element_type: e.element_type,
      length: String(e.length),
      diameter: String(e.diameter),
      position: String(e.position),
    }));
    setInputs((p: any) => ({ ...p, elements: newElements }));
    setRlResult(null);
    setDrivenNudgeCount(0);
    setDir1NudgeCount(0);
    setSpacingNudgeCount(0);
  };

  const [savingDesign, setSavingDesign] = useState(false);
  const [loadingDesigns, setLoadingDesigns] = useState(false);
  const [deletingDesignId, setDeletingDesignId] = useState<string | null>(null);

  // Tutorial / Intro state
  const [showTutorial, setShowTutorial] = useState(false);
  const [tutorialContent, setTutorialContent] = useState('');
  const [tutorialEnabled, setTutorialEnabled] = useState(true);
  const [tutorialLoaded, setTutorialLoaded] = useState(false);

  // Designer Info state
  const [showDesignerInfo, setShowDesignerInfo] = useState(false);
  const [showGammaDesigner, setShowGammaDesigner] = useState(false);
  const [showSpecSheet, setShowSpecSheet] = useState(false);
  const [designerInfoContent, setDesignerInfoContent] = useState('');
  const [gainMode, setGainMode] = useState<'realworld' | 'freespace'>('realworld');
  const [optimizingStacking, setOptimizingStacking] = useState(false);

  // Update checker state
  const [updateAvailable, setUpdateAvailable] = useState<{version: string; apkUrl: string; notes: string; forceUpdate: boolean; buildDate?: string} | null>(null);
  const [updateDismissed, setUpdateDismissed] = useState(false);
  const [updateDebug, setUpdateDebug] = useState('');

  // Check for updates on launch — tries own backend first, falls back to Gist
  useEffect(() => {
    const compareVersions = (local: string, remote: string): boolean => {
      // Returns true if remote > local (e.g. "3.3.0" > "3.2.5")
      const lParts = local.split('.').map(Number);
      const rParts = remote.split('.').map(Number);
      for (let i = 0; i < 3; i++) {
        const l = lParts[i] || 0;
        const r = rParts[i] || 0;
        if (r > l) return true;
        if (r < l) return false;
      }
      return false; // equal
    };

    const checkForUpdates = async () => {
      let debugLog = '';
      const logD = (msg: string) => { debugLog += msg + '\n'; };
      
      logD(`Installed: v${APP_VERSION}`);
      
      // Source 1: Own backend (no CDN caching)
      let data: any = null;
      try {
        logD(`Trying backend: ${BACKEND_URL}/api/app-update`);
        const res = await fetch(`${BACKEND_URL}/api/app-update?t=${Date.now()}`);
        logD(`Backend response: ${res.status}`);
        if (res.ok) {
          data = await res.json();
          logD(`Backend: v${data.version}`);
        }
      } catch (e: any) {
        logD(`Backend failed: ${e.message}`);
      }
      
      // Source 2: Gist fallback
      if (!data || !data.version) {
        try {
          logD(`Trying Gist...`);
          const res = await fetch(UPDATE_CHECK_URL + '?t=' + Date.now());
          logD(`Gist response: ${res.status}`);
          if (res.ok) {
            data = await res.json();
            logD(`Gist: v${data.version}`);
          }
        } catch (e: any) {
          logD(`Gist failed: ${e.message}`);
        }
      }
      
      if (data && data.version && data.apkUrl) {
        const isNewer = compareVersions(APP_VERSION, data.version);
        logD(`Compare: v${APP_VERSION} vs v${data.version} → ${isNewer ? 'UPDATE AVAILABLE' : 'up to date'}`);
        
        if (isNewer) {
          logD('Showing update banner');
          setUpdateAvailable({
            version: data.version,
            apkUrl: data.apkUrl,
            notes: data.releaseNotes || '',
            forceUpdate: data.forceUpdate || false,
            buildDate: data.buildDate,
          });
        }
      } else {
        logD('No valid update data from either source');
      }
      
      setUpdateDebug(debugLog);
    };
    checkForUpdates();
  }, []);

  // Load tutorial content and preference, then show if user is logged in
  useEffect(() => {
    let cancelled = false;
    const initTutorial = async () => {
      try {
        // Load preference
        const stored = await AsyncStorage.getItem('tutorial_enabled');
        const enabled = stored !== 'false'; // Default true for new users
        if (cancelled) return;
        setTutorialEnabled(enabled);

        // Load content from API (tutorial + designer info)
        const [tutRes, designerRes] = await Promise.all([
          fetch(`${BACKEND_URL}/api/tutorial`),
          fetch(`${BACKEND_URL}/api/designer-info`)
        ]);
        if (tutRes.ok && !cancelled) {
          const data = await tutRes.json();
          setTutorialContent(data.content || '');
          setTutorialLoaded(true);

          // Show tutorial if user is logged in and toggle is ON
          if (enabled && user) {
            setShowTutorial(true);
          }
        }
        if (designerRes.ok && !cancelled) {
          const data = await designerRes.json();
          setDesignerInfoContent(data.content || '');
        }
      } catch (e) { /* ignore */ }
    };
    if (user) {
      initTutorial();
    }
    return () => { cancelled = true; };
  }, [user]);

  // Also show tutorial when app comes back to foreground (user already logged in)
  useEffect(() => {
    const handleAppState = (nextState: string) => {
      if (nextState === 'active' && user && tutorialEnabled && tutorialLoaded) {
        setShowTutorial(true);
      }
    };
    const sub = AppState.addEventListener('change', handleAppState);
    return () => sub.remove();
  }, [user, tutorialEnabled, tutorialLoaded]);

  const toggleTutorialEnabled = async (val: boolean) => {
    setTutorialEnabled(val);
    await AsyncStorage.setItem('tutorial_enabled', val ? 'true' : 'false');
  };

  // Refresh/Reset - resets all options but keeps current element count
  const handleRefresh = () => {
    const currentCount = inputs.num_elements;
    const currentBand = inputs.band;
    const currentFreq = inputs.frequency_mhz;
    
    // Reset spacing
    setSpacingMode('normal');
    setSpacingLevel('1.0');
    
    // Reset locks
    setBoomLockEnabled(false);
    setMaxBoomLength('120');
    setSpacingLockEnabled(false);
    
    // Reset options but keep elements, band, freq
    setInputs(prev => ({
      ...prev,
      height_from_ground: '54', height_unit: 'ft',
      boom_diameter: '1.5', boom_unit: 'inches',
      band: currentBand, frequency_mhz: currentFreq,
      stacking: { enabled: false, orientation: 'vertical', layout: 'line', num_antennas: 2, spacing: '20', spacing_unit: 'ft', h_spacing: '20', h_spacing_unit: 'ft' },
      taper: { enabled: false, num_tapers: 2, center_length: '36', sections: [{ length: '36', start_diameter: '0.625', end_diameter: '0.5' }, { length: '36', start_diameter: '0.5', end_diameter: '0.375' }] },
      corona_balls: { enabled: false, diameter: '1.0' },
      ground_radials: { enabled: false, ground_type: 'average', wire_diameter: '0.5', num_radials: 8 },
      use_reflector: true,
      antenna_orientation: 'horizontal',
      dual_active: false,
      dual_selected_beam: 'horizontal' as 'horizontal' | 'vertical',
    }));
    
    // Clear results
    setResults(null);
    setHeightOptResult(null);
  };

  // Get max elements based on subscription
  const tierMaxElements = user ? getMaxElements() : 3;
  const maxElements = inputs.antenna_orientation === 'vertical' ? Math.min(tierMaxElements, 12) : tierMaxElements;

  // Convert element values between inches and meters
  const convertElementUnit = (newUnit: 'inches' | 'meters') => {
    if (newUnit === elementUnit) return;
    
    const factor = newUnit === 'meters' ? 0.0254 : 39.3701; // inches to meters or meters to inches
    const newElements = inputs.elements.map(elem => ({
      ...elem,
      length: (parseFloat(elem.length) * factor).toFixed(newUnit === 'meters' ? 3 : 1),
      diameter: (parseFloat(elem.diameter) * factor).toFixed(newUnit === 'meters' ? 4 : 3),
      position: (parseFloat(elem.position) * factor).toFixed(newUnit === 'meters' ? 3 : 1),
    }));
    
    setInputs(prev => ({ ...prev, elements: newElements }));
    setElementUnit(newUnit);
  };

  // Calculate boom length from element positions (last element position)
  const calculateBoomLength = () => {
    if (!inputs.elements.length) return { ft: 0, inches: 0, total_inches: 0 };
    const lastPos = Math.max(...inputs.elements.map(e => parseFloat(e.position) || 0));
    
    // If in meters, convert to inches first
    const posInInches = elementUnit === 'meters' ? lastPos * 39.3701 : lastPos;
    const totalFt = Math.floor(posInInches / 12);
    const remainingInches = posInInches % 12;
    
    return { ft: totalFt, inches: remainingInches, total_inches: posInInches };
  };

  // Calculate on ANY input change
  const calculateAntenna = useCallback(async () => {
    for (const elem of inputs.elements) {
      if (!elem.length || parseFloat(elem.length) <= 0 || !elem.diameter || parseFloat(elem.diameter) <= 0) return;
    }
    if (!inputs.height_from_ground || parseFloat(inputs.height_from_ground) <= 0 || !inputs.boom_diameter || parseFloat(inputs.boom_diameter) <= 0) return;
    
    // Convert to inches for API if currently in meters
    const elementsForApi = elementUnit === 'meters' 
      ? inputs.elements.map(e => ({
          element_type: e.element_type,
          length: parseFloat(e.length) * 39.3701,
          diameter: parseFloat(e.diameter) * 39.3701,
          position: parseFloat(e.position) * 39.3701,
        }))
      : inputs.elements.map(e => ({
          element_type: e.element_type,
          length: parseFloat(e.length) || 0,
          diameter: parseFloat(e.diameter) || 0,
          position: parseFloat(e.position) || 0,
        }));
    
    try {
      const response = await fetch(`${BACKEND_URL}/api/calculate`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          num_elements: inputs.num_elements,
          elements: elementsForApi,
          height_from_ground: parseFloat(inputs.height_from_ground) || 0, height_unit: inputs.height_unit,
          boom_diameter: parseFloat(inputs.boom_diameter) || 0, boom_unit: inputs.boom_unit, boom_grounded: inputs.boom_mount === 'bonded', boom_mount: inputs.boom_mount,
          band: inputs.band, frequency_mhz: parseFloat(inputs.frequency_mhz) || null,
          stacking: inputs.stacking.enabled ? { ...inputs.stacking, spacing: parseFloat(inputs.stacking.spacing) || 0, h_spacing: inputs.stacking.layout === 'quad' ? (parseFloat(inputs.stacking.h_spacing) || 0) : null } : null,
          taper: inputs.taper.enabled ? { ...inputs.taper, sections: inputs.taper.sections.map(s => ({ length: parseFloat(s.length) || 0, start_diameter: parseFloat(s.start_diameter) || 0, end_diameter: parseFloat(s.end_diameter) || 0 })) } : null,
          corona_balls: inputs.corona_balls.enabled ? { ...inputs.corona_balls, diameter: parseFloat(inputs.corona_balls.diameter) || 1.0 } : null,
          ground_radials: inputs.ground_radials.enabled ? { ...inputs.ground_radials, wire_diameter: parseFloat(inputs.ground_radials.wire_diameter) || 0.5 } : null,
          antenna_orientation: inputs.antenna_orientation,
          feed_type: inputs.feed_type,
          ...(inputs.feed_type === 'gamma' ? {
            gamma_rod_dia: gammaRodDia !== null ? (parseFloat(gammaRodDia) || undefined) : undefined,
            gamma_rod_spacing: gammaRodSpacing !== null ? (parseFloat(gammaRodSpacing) || undefined) : undefined,
            gamma_bar_pos: gammaBarPos,
            gamma_element_gap: gammaRodInsertion,
            gamma_cap_pf: gammaCapPf !== null ? (parseFloat(gammaCapPf) || undefined) : undefined,
          } : {}),
          ...(inputs.feed_type === 'hairpin' ? {
            hairpin_rod_dia: parseFloat(hairpinRodDia) || undefined,
            hairpin_rod_spacing: parseFloat(hairpinRodSpacing) || undefined,
            hairpin_bar_pos: hairpinBarPos,
            hairpin_boom_gap: hairpinBoomGap,
          } : {}),
          dual_active: inputs.dual_active,
          dual_selected_beam: inputs.antenna_orientation === 'dual' ? inputs.dual_selected_beam : undefined,
          coax_type: coaxType,
          coax_length_ft: parseFloat(coaxLengthFt) || 100,
          transmit_power_watts: parseFloat(transmitPowerWatts) || 500,
        }),
      });
      if (response.ok) setResults(await response.json());
    } catch (err) { console.error(err); }
  }, [inputs, elementUnit, gammaRodDia, gammaRodSpacing, gammaBarPos, gammaRodInsertion, hairpinRodDia, hairpinRodSpacing, hairpinBarPos, hairpinBoomGap, coaxType, coaxLengthFt, transmitPowerWatts]);

  // Initial calculation on mount
  useEffect(() => { calculateAntenna(); }, []);

  // Track whether spacing override changes should trigger auto-tune
  const spacingOverrideTriggered = useRef(false);
  const triggerSpacingAutoTune = () => { 
    spacingOverrideTriggered.current = true;
  };
  useEffect(() => {
    if (spacingOverrideTriggered.current) {
      spacingOverrideTriggered.current = false;
      // Small delay to ensure all batched state updates are applied
      const timer = setTimeout(() => autoTune(), 100);
      return () => clearTimeout(timer);
    }
  }, [closeDriven, farDriven, closeDir1, farDir1, closeDir2, farDir2]);

  // Single debounced auto-recalculate on any input change
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => calculateAntenna(), 300);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [JSON.stringify(inputs), gammaRodDia, gammaRodSpacing, gammaBarPos, gammaRodInsertion, gammaCapPf, hairpinRodDia, hairpinRodSpacing, hairpinBarPos, hairpinBoomGap, coaxType, coaxLengthFt, transmitPowerWatts]);

  const optimizeStacking = async () => {
    setOptimizingStacking(true);
    try {
      const elementsForApi = elementUnit === 'meters' 
        ? inputs.elements.map(e => ({ element_type: e.element_type, length: parseFloat(e.length) * 39.3701, diameter: parseFloat(e.diameter) * 39.3701, position: parseFloat(e.position) * 39.3701 }))
        : inputs.elements.map(e => ({ element_type: e.element_type, length: parseFloat(e.length) || 0, diameter: parseFloat(e.diameter) || 0, position: parseFloat(e.position) || 0 }));
      const response = await fetch(`${BACKEND_URL}/api/optimize-stacking`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          num_elements: inputs.num_elements,
          elements: elementsForApi,
          height_from_ground: parseFloat(inputs.height_from_ground) || 0,
          height_unit: inputs.height_unit,
          boom_diameter: parseFloat(inputs.boom_diameter) || 0,
          boom_unit: inputs.boom_unit,
          band: inputs.band,
          frequency_mhz: parseFloat(inputs.frequency_mhz) || null,
          antenna_orientation: inputs.antenna_orientation,
          dual_active: inputs.dual_active,
          dual_selected_beam: inputs.dual_selected_beam,
          feed_type: inputs.feed_type,
          stacking_orientation: inputs.stacking.orientation,
          stacking_layout: inputs.stacking.layout,
          num_antennas: inputs.stacking.layout === 'quad' ? 4 : inputs.stacking.num_antennas,
          min_spacing_ft: 15,
          max_spacing_ft: 40,
          taper: inputs.taper.enabled ? { ...inputs.taper, sections: inputs.taper.sections.map(s => ({ length: parseFloat(s.length) || 0, start_diameter: parseFloat(s.start_diameter) || 0, end_diameter: parseFloat(s.end_diameter) || 0 })) } : null,
          corona_balls: inputs.corona_balls.enabled ? { ...inputs.corona_balls, diameter: parseFloat(inputs.corona_balls.diameter) || 1.0 } : null,
          ground_radials: inputs.ground_radials.enabled ? { ...inputs.ground_radials, wire_diameter: parseFloat(inputs.ground_radials.wire_diameter) || 0.5 } : null,
        }),
      });
      if (response.ok) {
        const data = await response.json();
        setInputs(p => ({
          ...p,
          stacking: {
            ...p.stacking,
            spacing: data.best_spacing_ft.toString(),
            spacing_unit: 'ft',
            ...(p.stacking.layout === 'quad' ? { h_spacing: (data.best_h_spacing_ft || data.best_spacing_ft).toString(), h_spacing_unit: 'ft' } : {}),
          }
        }));
      }
    } catch (err) { console.error(err); }
    setOptimizingStacking(false);
  };

  const autoTune = async () => {
    setTuning(true);
    try {
      // Prepare locked positions if spacing lock is enabled
      const lockedPositions = spacingLockEnabled 
        ? inputs.elements.map(e => parseFloat(e.position) || 0)
        : null;
      
      // Convert max boom length to inches if in meters
      const maxBoomInches = boomLockEnabled 
        ? (elementUnit === 'meters' ? parseFloat(maxBoomLength) * 39.3701 : parseFloat(maxBoomLength))
        : null;
      
      const response = await fetch(`${BACKEND_URL}/api/auto-tune`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          num_elements: inputs.num_elements,
          height_from_ground: parseFloat(inputs.height_from_ground) || 54,
          height_unit: inputs.height_unit,
          boom_diameter: parseFloat(inputs.boom_diameter) || 1.5,
          boom_unit: inputs.boom_unit,
          band: inputs.band,
          frequency_mhz: parseFloat(inputs.frequency_mhz) || null,
          taper: inputs.taper.enabled ? inputs.taper : null,
          corona_balls: inputs.corona_balls.enabled ? inputs.corona_balls : null,
          use_reflector: inputs.use_reflector,
          boom_lock_enabled: boomLockEnabled,
          max_boom_length: maxBoomInches,
          spacing_lock_enabled: spacingLockEnabled,
          locked_positions: lockedPositions,
          spacing_mode: spacingMode,
          spacing_level: parseFloat(spacingLevel) || 1.0,
          close_driven: closeDriven,
          far_driven: farDriven,
          close_dir1: closeDir1,
          far_dir1: farDir1,
          close_dir2: closeDir2,
          far_dir2: farDir2,
        }),
      });
      if (response.ok) {
        const data = await response.json();
        // Apply optimized elements while preserving current diameters and respecting use_reflector
        let newElements = data.optimized_elements.map((e: any, idx: number) => ({
          element_type: e.element_type,
          length: parseFloat(e.length).toFixed(3),
          diameter: inputs.elements[idx]?.diameter || parseFloat(e.diameter).toFixed(3),
          position: spacingLockEnabled ? inputs.elements[idx]?.position || parseFloat(e.position).toFixed(3) : parseFloat(e.position).toFixed(3),
        }));
        
        // If no reflector mode, filter out reflector from results
        if (!inputs.use_reflector) {
          newElements = newElements.filter((e: any) => e.element_type !== 'reflector');
          // Adjust positions so driven is at 0
          const drivenPos = parseFloat(newElements.find((e: any) => e.element_type === 'driven')?.position || '0');
          newElements = newElements.map((e: any) => ({
            ...e,
            position: (parseFloat(e.position) - drivenPos).toFixed(3)
          }));
        }
        
        setInputs(prev => ({ ...prev, elements: newElements }));
        // Reset nudge counts after auto-tune provides new positions
        setDrivenNudgeCount(0);
        setDir1NudgeCount(0);
        setSpacingNudgeCount(0);
        
        // Backend already applies spacing_mode/spacing_level if sent
        // When boom lock is active, reset spacing state cleanly
        if (boomLockEnabled) {
          setSpacingMode('normal');
          setSpacingLevel('1.0');
        }
        // No re-application needed — backend handles spacing
        
        // Build alert message with lock info
        let alertMsg = `Predicted SWR: ${data.predicted_swr}:1\nPredicted Gain: ${data.predicted_gain} dBi`;
        if (boomLockEnabled) alertMsg += `\n\n🔒 Boom constrained to ${maxBoomLength}${elementUnit === 'meters' ? 'm' : '"'}`;
        if (spacingLockEnabled) alertMsg += `\n🔒 Element spacing preserved`;
        alertMsg += `\n\n${data.optimization_notes.slice(0, 3).join('\n')}`;
        
        Alert.alert('Auto-Tune Complete', alertMsg);
      }
    } catch (err) { Alert.alert('Error', 'Auto-tune failed'); }
    setTuning(false);
  };

  // Optimize height from ground (10' to 100')
  const optimizeHeight = async () => {
    setOptimizingHeight(true);
    setHeightOptResult(null);
    try {
      // Convert to inches for API if currently in meters
      const elementsForApi = elementUnit === 'meters' 
        ? inputs.elements.map(e => ({
            element_type: e.element_type,
            length: parseFloat(e.length) * 39.3701,
            diameter: parseFloat(e.diameter) * 39.3701,
            position: parseFloat(e.position) * 39.3701,
          }))
        : inputs.elements.map(e => ({
            element_type: e.element_type,
            length: parseFloat(e.length) || 0,
            diameter: parseFloat(e.diameter) || 0,
            position: parseFloat(e.position) || 0,
          }));
      
      console.log('Optimize Height - Elements being sent:', JSON.stringify(elementsForApi));
      
      const response = await fetch(`${BACKEND_URL}/api/optimize-height`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          num_elements: inputs.num_elements,
          elements: elementsForApi,
          boom_diameter: parseFloat(inputs.boom_diameter) || 1.5,
          boom_unit: inputs.boom_unit,
          band: inputs.band,
          frequency_mhz: parseFloat(inputs.frequency_mhz) || null,
          min_height: 10,
          max_height: 100,
          step: 1,
          ground_radials: inputs.ground_radials.enabled ? { ...inputs.ground_radials, wire_diameter: parseFloat(inputs.ground_radials.wire_diameter) || 0.5 } : null,
        }),
      });
      if (response.ok) {
        const data = await response.json();
        console.log('Optimize Height - Result:', JSON.stringify(data));
        setHeightOptResult(data);
        setInputs(prev => ({ ...prev, height_from_ground: data.optimal_height.toString() }));
        Alert.alert('Height Optimized', `Best height: ${data.optimal_height}'\n\nSWR: ${data.optimal_swr.toFixed(2)}:1\nGain: ${data.optimal_gain} dBi\nF/B: ${data.optimal_fb_ratio} dB`);
      } else {
        console.log('Optimize Height - Error response:', response.status);
      }
    } catch (err) { 
      console.error('Optimize Height error:', err);
      Alert.alert('Error', 'Height optimization failed'); 
    }
    setOptimizingHeight(false);
  };

  // Toggle reflector on/off
  const toggleReflector = (useReflector: boolean) => {
    if (useReflector) {
      // Add reflector back
      const driven = inputs.elements.find(e => e.element_type === 'driven') || { element_type: 'driven', length: '204', diameter: '0.5', position: '48' };
      const dirs = inputs.elements.filter(e => e.element_type === 'director');
      const newElements: ElementDimension[] = [
        { element_type: 'reflector', length: '216', diameter: '0.5', position: '0' },
        { ...driven, position: '48' },
        ...dirs.map((d, i) => ({ ...d, position: (96 + i * 48).toString() }))
      ];
      setInputs(prev => ({ ...prev, use_reflector: true, elements: newElements }));
    } else {
      // Remove reflector
      const driven = inputs.elements.find(e => e.element_type === 'driven') || { element_type: 'driven', length: '204', diameter: '0.5', position: '0' };
      const dirs = inputs.elements.filter(e => e.element_type === 'director');
      const newElements: ElementDimension[] = [
        { ...driven, position: '0' },
        ...dirs.map((d, i) => ({ ...d, position: (48 + i * 48).toString() }))
      ];
      setInputs(prev => ({ ...prev, use_reflector: false, elements: newElements }));
    }
  };

  const updateElementCount = (count: number) => {
    const c = Math.max(2, Math.min(maxElements, count));
    if (count > maxElements) {
      Alert.alert('Upgrade Required', `Your ${user?.subscription_tier || 'trial'} plan allows up to ${maxElements} elements. Upgrade to unlock more!`, [
        { text: 'Cancel', style: 'cancel' },
        { text: 'Upgrade', onPress: () => router.push('/subscription') }
      ]);
      return;
    }
    
    // Apply active spacing factor to default positions
    const factor = (spacingMode !== 'normal') ? parseFloat(spacingLevel) || 1.0 : 1.0;
    
    const newElements: ElementDimension[] = [];
    
    if (inputs.use_reflector) {
      newElements.push({ element_type: 'reflector', length: '216', diameter: '0.5', position: '0' });
      newElements.push({ element_type: 'driven', length: '204', diameter: '0.5', position: (48 * factor).toFixed(1) });
      for (let i = 0; i < c - 2; i++) newElements.push({ element_type: 'director', length: (195 - i * 3).toString(), diameter: '0.5', position: ((96 + i * 48) * factor).toFixed(1) });
    } else {
      newElements.push({ element_type: 'driven', length: '204', diameter: '0.5', position: '0' });
      for (let i = 0; i < c - 1; i++) newElements.push({ element_type: 'director', length: (195 - i * 3).toString(), diameter: '0.5', position: ((48 + i * 48) * factor).toFixed(1) });
    }
    
    setInputs(prev => ({ ...prev, num_elements: c, elements: newElements }));
  };

  const updateElement = (idx: number, field: keyof ElementDimension, value: string) => {
    setInputs(prev => { const e = [...prev.elements]; e[idx] = { ...e[idx], [field]: value }; return { ...prev, elements: e }; });
  };

  const handleBandChange = (id: string) => {
    const b = BANDS.find(x => x.id === id);
    setInputs(prev => ({ ...prev, band: id, frequency_mhz: b ? b.center.toString() : prev.frequency_mhz }));
  };

  const updateTaperCount = (num: number) => {
    const sections: TaperSection[] = [];
    for (let i = 0; i < num; i++) sections.push(inputs.taper.sections[i] || { length: '36', start_diameter: (0.625 - i * 0.0625).toFixed(3), end_diameter: (0.5 - i * 0.0625).toFixed(3) });
    setInputs(prev => ({ ...prev, taper: { ...prev.taper, num_tapers: num, sections } }));
  };

  const updateTaperSection = (idx: number, field: keyof TaperSection, value: string) => {
    setInputs(prev => { const s = [...prev.taper.sections]; s[idx] = { ...s[idx], [field]: value }; return { ...prev, taper: { ...prev.taper, sections: s } }; });
  };

  // Save design
  const saveDesign = async () => {
    if (!token) {
      Alert.alert('Login Required', 'Please login to save designs');
      return;
    }
    if (!designName.trim()) {
      Alert.alert('Error', 'Please enter a design name');
      return;
    }
    setSavingDesign(true);
    try {
      const response = await fetch(`${BACKEND_URL}/api/designs/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          name: designName,
          design_data: inputs,
          spacing_state: {
            spacingMode, spacingLevel, spacingNudgeCount,
            closeDriven, farDriven, closeDir1, farDir1, closeDir2, farDir2,
            drivenNudgeCount, dir1NudgeCount, dir2NudgeCount,
          }
        })
      });
      if (response.ok) {
        Alert.alert('Success', 'Design saved successfully!');
        setShowSaveModal(false);
        setDesignName('');
      } else {
        Alert.alert('Error', 'Failed to save design');
      }
    } catch (err) {
      Alert.alert('Error', 'Network error');
    }
    setSavingDesign(false);
  };

  // Load designs list
  const loadDesignsList = async () => {
    if (!token) {
      Alert.alert('Login Required', 'Please login to view saved designs');
      return;
    }
    setLoadingDesigns(true);
    try {
      const response = await fetch(`${BACKEND_URL}/api/designs`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setSavedDesigns(data);
        setShowLoadModal(true);
      }
    } catch (err) {
      Alert.alert('Error', 'Failed to load designs');
    }
    setLoadingDesigns(false);
  };

  // Load a specific design
  const loadDesign = async (designId: string) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/designs/${designId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setInputs(data.design_data);
        // Restore spacing state if saved
        if (data.spacing_state) {
          const s = data.spacing_state;
          setSpacingMode(s.spacingMode ?? 'normal');
          setSpacingLevel(s.spacingLevel ?? '1.0');
          setSpacingNudgeCount(s.spacingNudgeCount ?? 0);
          setCloseDriven(s.closeDriven ?? false);
          setFarDriven(s.farDriven ?? false);
          setCloseDir1(s.closeDir1 ?? false);
          setFarDir1(s.farDir1 ?? false);
          setCloseDir2(s.closeDir2 ?? false);
          setFarDir2(s.farDir2 ?? false);
          setDrivenNudgeCount(s.drivenNudgeCount ?? 0);
          setDir1NudgeCount(s.dir1NudgeCount ?? 0);
          setDir2NudgeCount(s.dir2NudgeCount ?? 0);
        }
        setShowLoadModal(false);
        Alert.alert('Loaded', `Design "${data.name}" loaded successfully`);
      }
    } catch (err) {
      Alert.alert('Error', 'Failed to load design');
    }
  };

  // Delete a design
  const deleteDesign = async (designId: string, name: string) => {
    Alert.alert('Delete Design', `Are you sure you want to delete "${name}"?`, [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Delete', style: 'destructive', onPress: async () => {
        try {
          await fetch(`${BACKEND_URL}/api/designs/${designId}`, {
            method: 'DELETE',
            headers: { Authorization: `Bearer ${token}` }
          });
          setSavedDesigns(prev => prev.filter(d => d.id !== designId));
        } catch (err) {}
      }}
    ]);
  };

  // Generate timestamp for filenames
  const getTimestamp = () => {
    const now = new Date();
    return now.toISOString().replace(/[:.]/g, '-').slice(0, 19);
  };

  // Sanitize filename - remove all illegal characters for Android/iOS
  const sanitizeFilename = (name: string) => {
    return name.replace(/[^a-zA-Z0-9_\-\.]/g, '_');
  };

  // Export height optimization data to CSV
  const exportHeightData = async () => {
    if (!heightOptResult || !heightOptResult.heights_tested) {
      Alert.alert('No Data', 'Run height optimization first');
      return;
    }
    
    const timestamp = getTimestamp();
    const userEmail = user?.email || 'guest';
    const filename = sanitizeFilename(`height_optimization_${timestamp}_${userEmail.replace('@', '_at_')}`) + '.csv';
    
    let csv = '';
    csv += 'HEIGHT OPTIMIZATION REPORT\n';
    csv += `Date:, ${new Date().toLocaleString()}\n`;
    csv += `User:, ${userEmail}\n`;
    csv += `Band:, ${inputs.band}\n`;
    csv += `Elements:, ${inputs.num_elements}${inputs.antenna_orientation === 'dual' ? ` (${inputs.num_elements}H + ${inputs.num_elements}V Dual)` : ''}\n`;
    csv += `Orientation:, ${inputs.antenna_orientation}\n`;
    csv += `Feed Match:, ${inputs.feed_type === 'gamma' ? 'Gamma Match' : inputs.feed_type === 'hairpin' ? 'Hairpin Match' : 'Direct Feed'}\n\n`;
    
    csv += 'OPTIMAL RESULT\n';
    csv += `Best Height:, ${heightOptResult.optimal_height} ft\n`;
    csv += `SWR at Best:, ${heightOptResult.optimal_swr}:1\n`;
    csv += `Gain at Best:, ${heightOptResult.optimal_gain} dBi\n`;
    csv += `F/B at Best:, ${heightOptResult.optimal_fb_ratio} dB\n\n`;
    
    csv += 'ALL HEIGHTS TESTED\n';
    csv += 'Height (ft), SWR, Gain (dBi), F/B (dB), Efficiency (%), TOA (deg), Score, Optimal?\n';
    heightOptResult.heights_tested.forEach((h: any) => {
      const isOptimal = h.height === heightOptResult.optimal_height ? '  <<<' : '';
      csv += `${h.height}, ${h.swr}, ${h.gain}, ${h.fb_ratio}, ${h.efficiency || '-'}, ${h.takeoff_angle || '-'}, ${h.score},${isOptimal}\n`;
    });
    csv += `\nTotal Heights Tested:, ${heightOptResult.heights_tested.length}\n`;
    
    downloadCSV(csv, filename);
  };

  // Export all antenna results to CSV
  const exportAllData = async () => {
    if (!results) {
      Alert.alert('No Data', 'Calculate antenna first');
      return;
    }
    
    const timestamp = getTimestamp();
    const userEmail = user?.email || 'guest';
    const filename = sanitizeFilename(`antenna_results_${timestamp}_${userEmail.replace('@', '_at_')}`) + '.csv';
    
    const isDual = inputs.antenna_orientation === 'dual';
    const feedLabel = inputs.feed_type === 'gamma' ? 'Gamma Match' : inputs.feed_type === 'hairpin' ? 'Hairpin Match' : 'Direct Feed';
    
    let csv = '';
    csv += 'ANTENNA DESIGN REPORT\n';
    csv += `Date:, ${new Date().toLocaleString()}\n`;
    csv += `User:, ${userEmail}\n\n`;
    
    // --- CONFIGURATION ---
    csv += 'CONFIGURATION\n';
    csv += `Band:, ${inputs.band}\n`;
    csv += `Center Frequency:, ${inputs.frequency_mhz} MHz\n`;
    csv += `Antenna Type:, ${isDual ? 'Dual Polarity Yagi' : 'Yagi-Uda'}\n`;
    csv += `Polarization:, ${inputs.antenna_orientation === 'horizontal' ? 'Horizontal' : inputs.antenna_orientation === 'vertical' ? 'Vertical' : inputs.antenna_orientation === 'angle45' ? '45° Slant' : 'Dual (H+V)'}\n`;
    csv += `Feed System:, ${feedLabel}\n`;
    csv += `Elements:, ${inputs.num_elements}${isDual ? ` per polarization (${inputs.num_elements}H + ${inputs.num_elements}V = ${inputs.num_elements * 2} total)` : ''}\n`;
    csv += `Reflector:, ${inputs.use_reflector ? 'Yes' : 'No'}\n`;
    csv += `Height:, ${inputs.height_from_ground} ${inputs.height_unit}\n`;
    csv += `Boom:, ${inputs.boom_diameter} ${inputs.boom_unit} diameter\n`;
    csv += `Gain Mode:, ${gainMode === 'realworld' ? 'Real World' : 'Free Space'}\n\n`;
    
    // --- ELEMENT TABLE ---
    csv += 'ELEMENT DIMENSIONS\n';
    csv += '#, Type, Length (in), Diameter (in), Position (in)\n';
    inputs.elements.forEach((e: any, i: number) => {
      csv += `${i + 1}, ${e.element_type}, ${e.length}, ${e.diameter}, ${e.position}\n`;
    });
    csv += '\n';
    
    // --- PERFORMANCE ---
    csv += 'PERFORMANCE RESULTS\n\n';
    
    csv += 'Signal\n';
    csv += `  Gain:, ${results.gain_dbi} dBi\n`;
    csv += `  Base Free-Space Gain:, ${results.base_gain_dbi || '-'} dBi\n`;
    csv += `  Gain Description:, ${results.gain_description}\n`;
    csv += `  Multiplication Factor:, ${results.multiplication_factor}x\n`;
    csv += `  Efficiency:, ${results.antenna_efficiency}%\n`;
    if (results.gain_breakdown) {
      csv += '\n  Gain Breakdown\n';
      csv += `    Element Gain (lookup):, ${results.gain_breakdown.standard_gain || '-'} dBi\n`;
      csv += `    Boom Adjustment:, ${results.gain_breakdown.boom_adj >= 0 ? '+' : ''}${results.gain_breakdown.boom_adj || 0} dB\n`;
      csv += `    Reflector Adjustment:, ${results.gain_breakdown.reflector_adj >= 0 ? '+' : ''}${results.gain_breakdown.reflector_adj || 0} dB\n`;
      csv += `    Taper Bonus:, +${results.gain_breakdown.taper_bonus || 0} dB\n`;
      csv += `    Corona Adjustment:, ${results.gain_breakdown.corona_adj || 0} dB\n`;
      csv += `    Height/Ground Bonus:, +${results.gain_breakdown.height_bonus || 0} dB\n`;
      csv += `    Boom Length Bonus:, +${results.gain_breakdown.boom_bonus || 0} dB\n`;
      if (results.gain_breakdown.boom_grounded_adj) {
        csv += `    Boom Grounded Adj:, ${results.gain_breakdown.boom_grounded_adj} dB\n`;
      }
      if (results.gain_breakdown.ground_type) {
        csv += `    Ground Type:, ${results.gain_breakdown.ground_type} (scale: ${results.gain_breakdown.ground_scale || '-'})\n`;
      }
      if (results.gain_breakdown.dual_active_bonus > 0) {
        csv += `    H+V Active Bonus:, +${results.gain_breakdown.dual_active_bonus} dB\n`;
      }
      csv += `    Final Gain:, ${results.gain_breakdown.final_gain || results.gain_dbi} dBi\n`;
    }
    csv += '\n';
    
    csv += 'SWR & Impedance\n';
    csv += `  SWR:, ${Number(results.swr).toFixed(3)}:1, ${results.swr_description}\n`;
    if (results.matching_info && results.feed_type !== 'direct') {
      csv += `  Feed Match:, ${results.matching_info.type}\n`;
      csv += `  Original SWR:, ${results.matching_info.original_swr}:1\n`;
      csv += `  Matched SWR:, ${results.matching_info.matched_swr}:1\n`;
    }
    csv += `  Impedance Range:, ${results.impedance_low || '-'} - ${results.impedance_high || '-'} Ohms\n`;
    csv += `  Return Loss:, ${results.return_loss_db || '-'} dB\n`;
    csv += `  Mismatch Loss:, ${results.mismatch_loss_db || '-'} dB\n\n`;
    
    csv += 'Radiation Pattern\n';
    csv += `  F/B Ratio:, ${results.fb_ratio} dB\n`;
    csv += `  F/S Ratio:, ${results.fs_ratio} dB\n`;
    csv += `  Horizontal Beamwidth:, ${results.beamwidth_h}°\n`;
    csv += `  Vertical Beamwidth:, ${results.beamwidth_v}°\n\n`;
    
    csv += 'Propagation\n';
    csv += `  Take-off Angle:, ${results.takeoff_angle || '-'}°\n`;
    csv += `  Angle Rating:, ${results.takeoff_angle_description || '-'}\n`;
    csv += `  Height Performance:, ${results.height_performance || '-'}\n`;
    csv += `  Noise Level:, ${results.noise_level || '-'} — ${results.noise_description || ''}\n\n`;
    
    csv += 'Bandwidth\n';
    csv += `  Total Bandwidth:, ${results.bandwidth} MHz\n`;
    csv += `  Usable @ 1.5:1 SWR:, ${results.usable_bandwidth_1_5} MHz\n`;
    csv += `  Usable @ 2.0:1 SWR:, ${results.usable_bandwidth_2_0} MHz\n\n`;
    
    // --- DUAL POLARITY ---
    if (results.dual_polarity_info) {
        csv += 'DUAL POLARITY DETAILS\n';
        csv += `  Configuration:, ${results.dual_polarity_info.description}\n`;
      csv += `  Gain per Polarization:, ${results.dual_polarity_info.gain_per_polarization_dbi} dBi\n`;
      csv += `  Cross-Coupling Bonus:, +${results.dual_polarity_info.coupling_bonus_db} dB\n`;
      csv += `  F/B Improvement:, +${results.dual_polarity_info.fb_bonus_db} dB\n\n`;
    }
    
    // --- STACKING ---
    if (results.stacking_enabled && results.stacking_info) {
        csv += 'STACKING CONFIGURATION\n';
        csv += `  Layout:, ${results.stacking_info.layout === 'quad' ? '2x2 Quad (H-Frame)' : `${results.stacking_info.num_antennas}x Line (${results.stacking_info.orientation})`}\n`;
        csv += `  Antennas Stacked:, ${results.stacking_info.num_antennas}\n`;
      csv += `  Spacing:, ${results.stacking_info.spacing} ${results.stacking_info.spacing_unit} (${results.stacking_info.spacing_wavelengths?.toFixed(2) || '-'}λ)\n`;
      if (results.stacking_info.quad_notes) {
        csv += `  H Spacing:, ${results.stacking_info.quad_notes.h_spacing}\n`;
      }
      csv += `  Stacking Gain Increase:, +${results.stacking_info.gain_increase_db} dB\n`;
      csv += `  Stacked Gain:, ${results.stacked_gain_dbi} dBi\n`;
      csv += `  Stacked Beamwidth H/V:, ${results.stacking_info.new_beamwidth_h}° / ${results.stacking_info.new_beamwidth_v}°\n`;
      csv += `  Spacing Status:, ${results.stacking_info.spacing_status || '-'}\n`;
      csv += `  Isolation:, ~${results.stacking_info.isolation_db}dB\n`;
      if (results.stacking_info.quad_notes) {
        csv += '\n  2x2 QUAD NOTES\n';
        csv += `  Layout:, ${results.stacking_info.quad_notes.layout}\n`;
        csv += `  Effect:, ${results.stacking_info.quad_notes.effect}\n`;
        csv += `  V Spacing:, ${results.stacking_info.quad_notes.v_spacing}\n`;
        csv += `  H Spacing:, ${results.stacking_info.quad_notes.h_spacing}\n`;
        csv += `  H-Frame Note:, ${results.stacking_info.quad_notes.h_frame_note}\n`;
        csv += `  Identical Note:, ${results.stacking_info.quad_notes.identical_note}\n`;
      }
      if (results.stacking_info.power_splitter) {
        csv += '\n  POWER SPLITTER\n';
        csv += `  Type:, ${results.stacking_info.power_splitter.type}\n`;
        csv += `  Input Impedance:, ${results.stacking_info.power_splitter.input_impedance}\n`;
        csv += `  Combined Load:, ${results.stacking_info.power_splitter.combined_load}\n`;
        csv += `  Matching Method:, ${results.stacking_info.power_splitter.matching_method}\n`;
        csv += `  Quarter-Wave Line:, ${results.stacking_info.power_splitter.quarter_wave_ft}' (${results.stacking_info.power_splitter.quarter_wave_in}")\n`;
        csv += `  Power per Antenna @ 100W:, ${results.stacking_info.power_splitter.power_per_antenna_100w}W\n`;
        csv += `  Power per Antenna @ 1kW:, ${results.stacking_info.power_splitter.power_per_antenna_1kw}W\n`;
        csv += `  Min Power Rating:, ${results.stacking_info.power_splitter.min_power_rating}\n`;
        csv += `  Phase Requirement:, ${results.stacking_info.power_splitter.phase_lines}\n`;
        csv += `  Isolation:, ${results.stacking_info.power_splitter.isolation_note}\n`;
      }
      csv += '\n';
    }
    
    // --- TAPER ---
    if (results.taper_info?.enabled) {
        csv += 'ELEMENT TAPER\n';
        csv += `  Taper Steps:, ${results.taper_info.num_tapers}\n`;
      csv += `  Gain Bonus:, +${results.taper_info.gain_bonus} dB\n`;
      csv += `  Bandwidth Improvement:, ${results.taper_info.bandwidth_improvement}\n\n`;
    }
    
    // --- CORONA BALLS ---
    if (results.corona_info?.enabled) {
        csv += 'CORONA BALL TIPS\n';
        csv += `  Diameter:, ${results.corona_info.diameter}"\n`;
      csv += `  Corona Reduction:, ${results.corona_info.corona_reduction}%\n`;
      csv += `  Gain Effect:, ${results.corona_info.gain_effect} dB\n`;
      csv += `  Bandwidth Effect:, x${results.corona_info.bandwidth_effect}\n`;
      csv += `  Description:, ${results.corona_info.description}\n\n`;
    }
    
    // --- POWER ---
    if (results.forward_power_100w) {
        csv += 'POWER ANALYSIS\n';
        csv += `, @ 100W, @ 1000W\n`;
      csv += `  Forward Power:, ${results.forward_power_100w}W, ${results.forward_power_1kw}W\n`;
      csv += `  Reflected Power:, ${results.reflected_power_100w}W, ${results.reflected_power_1kw}W\n\n`;
    }
    
    // --- GROUND RADIALS ---
    if (results.ground_radials_info) {
        csv += 'GROUND RADIAL SYSTEM\n';
        csv += `  Ground Type:, ${results.ground_radials_info.ground_type}\n`;
      csv += `  Radials:, ${results.ground_radials_info.num_radials}\n`;
      csv += `  Radial Length:, ${results.ground_radials_info.radial_length_ft}' (${results.ground_radials_info.radial_length_in}")\n`;
      csv += `  Total Wire:, ${results.ground_radials_info.total_wire_length_ft}'\n`;
      csv += `  SWR Improvement:, ${results.ground_radials_info.estimated_improvements?.swr_improvement}\n`;
      csv += `  Efficiency Bonus:, +${results.ground_radials_info.estimated_improvements?.efficiency_bonus_percent}%\n\n`;
    }
    
    // --- WIND LOAD ---
    if (results.wind_load) {
      csv += 'WIND LOAD & MECHANICAL\n';
      csv += `  Total Wind Area:, ${results.wind_load.total_area_sqft} sq ft\n`;
      csv += `  Total Weight:, ${results.wind_load.total_weight_lbs} lbs\n`;
      csv += `  Elements:, ${results.wind_load.element_weight_lbs} lbs\n`;
      csv += `  Boom (${results.wind_load.boom_length_ft}ft):, ${results.wind_load.boom_weight_lbs} lbs\n`;
      csv += `  Hardware/Truss:, ${results.wind_load.hardware_weight_lbs} lbs\n`;
      csv += `  Turn Radius:, ${results.wind_load.turn_radius_ft}' (${results.wind_load.turn_radius_in}")\n`;
      csv += `  Survival Rating:, ${results.wind_load.survival_mph} mph\n`;
      if (results.wind_load.has_truss) csv += `  Truss:, Boom support wires recommended (boom > 12ft)\n`;
      csv += '\n  WIND FORCE BY SPEED\n';
      csv += '  MPH, Force (lbs), Torque (ft-lbs)\n';
      ['50','70','80','90','100','120'].forEach(mph => {
        const r = results.wind_load.wind_ratings?.[mph];
        if (r) csv += `  ${mph}, ${r.force_lbs}, ${r.torque_ft_lbs}\n`;
      });
      csv += '\n';
    }
    
    // --- BOOM CORRECTION ---
    if (results.boom_correction_info) {
      csv += 'BOOM CORRECTION (G3SEK/DL6WU)\n';
      const mt = results.boom_correction_info.boom_mount;
      csv += `  Mount Type:, ${mt === 'bonded' ? 'Bonded (Elements to Metal Boom)' : mt === 'insulated' ? 'Insulated on Metal Boom' : 'Non-Conductive Boom'}\n`;
      if (results.boom_correction_info.enabled) {
        csv += `  Correction Level:, ${(results.boom_correction_info.correction_multiplier * 100).toFixed(0)}% of full DL6WU\n`;
        csv += `  Boom/Element Ratio:, ${results.boom_correction_info.boom_to_element_ratio}:1\n`;
        csv += `  Shorten Each Element:, ${results.boom_correction_info.correction_total_in}" total\n`;
        csv += `  Per Side:, ${results.boom_correction_info.correction_per_side_in}"\n`;
        csv += `  Gain Effect:, ${results.boom_correction_info.gain_adj_db} dB\n`;
        csv += `  F/B Effect:, ${results.boom_correction_info.fb_adj_db} dB\n`;
        csv += `  Impedance Shift:, ${results.boom_correction_info.impedance_shift_ohm} ohm\n`;
      }
      csv += `  Note:, ${results.boom_correction_info.description}\n`;
      if (results.boom_correction_info.corrected_elements?.length > 0) {
        csv += '\n  CORRECTED CUT LIST\n';
        csv += '  Element, Original, Corrected, Correction\n';
        results.boom_correction_info.corrected_elements.forEach((el: any) => {
          csv += `  ${el.type}, ${el.original_length}", ${el.corrected_length}", -${el.correction}"\n`;
        });
      }
      if (results.boom_correction_info.practical_notes) {
        csv += '\n  PRACTICAL NOTES\n';
        results.boom_correction_info.practical_notes.forEach((note: string) => {
          csv += `  -, ${note}\n`;
        });
      }
      csv += '\n';
    }
    
    // --- FAR-FIELD PATTERN DATA ---
    csv += 'FAR-FIELD RADIATION PATTERN\n';
    csv += 'Angle (°), Magnitude (%)\n';
    results.far_field_pattern?.forEach((p: any) => {
      csv += `${p.angle}, ${p.magnitude}\n`;
    });
    csv += '\n';
    
    // --- SWR CURVE DATA ---
    csv += 'SWR ACROSS BAND\n';
    csv += 'Frequency (MHz), SWR, Channel\n';
    results.swr_curve?.forEach((s: any) => {
      csv += `${s.frequency}, ${s.swr}, ${s.channel || ''}\n`;
    });
    
    csv += '\nEND OF REPORT\n';
    
    downloadCSV(csv, filename);
  };

  // Download CSV (works on web and mobile)
  const downloadCSV = async (csvContent: string, filename: string) => {
    if (Platform.OS === 'web') {
      // Web: Create blob and download
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      link.click();
      URL.revokeObjectURL(url);
      Alert.alert('Exported', `File saved as ${filename}`);
    } else {
      // Mobile: Save to cache and use SAF to let user pick save location
      try {
        const fileUri = FileSystem.cacheDirectory + filename;
        await FileSystem.writeAsStringAsync(fileUri, csvContent, {
          encoding: 'utf8',
        });
        
        // Try using StorageAccessFramework to save to user-chosen location
        try {
          const permissions = await FileSystem.StorageAccessFramework.requestDirectoryPermissionsAsync();
          if (permissions.granted) {
            const newFile = await FileSystem.StorageAccessFramework.createFileAsync(
              permissions.directoryUri,
              filename,
              'text/csv'
            );
            await FileSystem.writeAsStringAsync(newFile, csvContent, {
              encoding: 'utf8',
            });
            Alert.alert('✅ Exported!', `CSV saved to your chosen folder as:\n${filename}`);
            return;
          }
        } catch (safError) {
          console.log('SAF not available, falling back to share sheet');
        }
        
        // Fallback: Use share sheet
        const isAvailable = await Sharing.isAvailableAsync();
        if (isAvailable) {
          await Sharing.shareAsync(fileUri, {
            mimeType: 'text/csv',
            dialogTitle: `Save ${filename}`,
            UTI: 'public.comma-separated-values-text',
          });
        } else {
          Alert.alert('File Saved', `File saved to app cache:\n${filename}\n\nSharing not available on this device.`);
        }
      } catch (error: any) {
        console.error('Export error:', error);
        Alert.alert('Export Error', `Failed to save file: ${error?.message || 'Unknown error'}\n\nPlease try again.`);
      }
    }
  };

  // Generate element count options based on subscription (up to 20)
  const elementOptions = [];
  for (let i = 2; i <= 20; i++) {
    const isLocked = i > maxElements;
    elementOptions.push({
      value: i.toString(),
      label: isLocked ? `${i} Elements 🔒` : `${i} Elements`
    });
  }

  return (
    <SafeAreaView style={styles.container}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={styles.flex}>
        <ScrollView style={styles.scrollView} contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false} keyboardShouldPersistTaps="handled">
          
          {/* User Header */}
          <View style={styles.userHeader}>
            <TouchableOpacity style={styles.userHeaderLeft} onPress={() => user ? router.push('/subscription') : router.push('/login')}>
              <Ionicons name="radio-outline" size={24} color="#4CAF50" />
              <View>
                <Text style={styles.headerTitle}>SMA Antenna Calculator</Text>
                <Text style={{ fontSize: 9, color: '#ccc' }}>v{APP_VERSION} | Built: {new Date(APP_BUILD_DATE).toLocaleDateString()}</Text>
              </View>
            </TouchableOpacity>
            
            {user ? (
              <TouchableOpacity style={styles.userBadge} onPress={() => router.push('/subscription')}>
                <View style={[styles.tierDot, { backgroundColor: TIER_COLORS[user.subscription_tier] || '#888' }]} />
                <Text style={styles.userBadgeText}>{user.subscription_tier}</Text>
                <Ionicons name="chevron-forward" size={14} color="#888" />
              </TouchableOpacity>
            ) : (
              <TouchableOpacity style={styles.loginBadge} onPress={() => router.push('/login')}>
                <Text style={styles.loginBadgeText}>Login</Text>
                <Ionicons name="log-in-outline" size={16} color="#4CAF50" />
              </TouchableOpacity>
            )}
          </View>
          
          {/* Update Available Banner */}
          {updateAvailable && !updateDismissed && (
            <View style={{ marginHorizontal: 12, marginBottom: 8, backgroundColor: '#1a3a1a', borderRadius: 8, padding: 10, borderWidth: 1, borderColor: '#4CAF50' }}>
              <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
                <View style={{ flex: 1 }}>
                  <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                    <Ionicons name="arrow-up-circle" size={16} color="#4CAF50" />
                    <Text style={{ color: '#4CAF50', fontWeight: '700', fontSize: 12 }}>Update Available v{updateAvailable.version}</Text>
                  </View>
                  {updateAvailable.notes ? <Text style={{ color: '#ddd', fontSize: 10, marginBottom: 6 }}>{updateAvailable.notes}</Text> : null}
                  <TouchableOpacity onPress={() => { Linking.openURL(updateAvailable.apkUrl); setUpdateDismissed(true); }} style={{ backgroundColor: '#4CAF50', borderRadius: 6, paddingVertical: 6, paddingHorizontal: 12, alignSelf: 'flex-start' }}>
                    <Text style={{ color: '#000', fontWeight: '700', fontSize: 11 }}>Download APK</Text>
                  </TouchableOpacity>
                </View>
                {!updateAvailable.forceUpdate && (
                  <TouchableOpacity onPress={() => setUpdateDismissed(true)} style={{ padding: 4 }}>
                    <Ionicons name="close" size={18} color="#666" />
                  </TouchableOpacity>
                )}
              </View>
              <Text style={{ color: '#bbb', fontSize: 9, marginTop: 4 }}>Installed: {new Date(APP_BUILD_DATE).toLocaleString()}{updateAvailable.buildDate ? ` | New: ${new Date(updateAvailable.buildDate).toLocaleString()}` : ''}</Text>
            </View>
          )}
          
          {/* Update Debug Panel — tap version number to toggle */}
          {updateDebug ? (
            <TouchableOpacity onPress={() => setUpdateDebug(prev => prev.startsWith('HIDDEN:') ? prev.replace('HIDDEN:', '') : 'HIDDEN:' + prev)}>
              {!updateDebug.startsWith('HIDDEN:') && (
                <View style={{ marginHorizontal: 12, marginBottom: 6, backgroundColor: '#1a1a2a', borderRadius: 6, padding: 8, borderWidth: 1, borderColor: '#333' }}>
                  <Text style={{ fontSize: 8, fontWeight: '700', color: '#666', marginBottom: 2 }}>UPDATE CHECK LOG (tap to hide)</Text>
                  <Text style={{ fontSize: 8, color: '#888', fontFamily: 'monospace' }}>{updateDebug}</Text>
                </View>
              )}
            </TouchableOpacity>
          ) : null}

          {/* Action Buttons Row */}
          <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, paddingHorizontal: 12, paddingBottom: 8, flexWrap: 'wrap' }}>
            {user && (
              <>
                <TouchableOpacity style={{ flexDirection: 'row', alignItems: 'center', backgroundColor: '#f44336', borderRadius: 6, paddingHorizontal: 10, paddingVertical: 6, gap: 4 }} onPress={handleRefresh}>
                  <Ionicons name="refresh-outline" size={14} color="#fff" />
                  <Text style={{ fontSize: 10, color: '#fff', fontWeight: '600' }}>Reset</Text>
                </TouchableOpacity>
                <TouchableOpacity style={{ flexDirection: 'row', alignItems: 'center', backgroundColor: '#2196F3', borderRadius: 6, paddingHorizontal: 10, paddingVertical: 6, gap: 4 }} onPress={() => { if (checkFeature('save_designs', 'Save Designs')) setShowSaveModal(true); }}>
                  <Ionicons name="save-outline" size={14} color="#fff" />
                  <Text style={{ fontSize: 10, color: '#fff', fontWeight: '600' }}>Save</Text>
                </TouchableOpacity>
                <TouchableOpacity style={{ flexDirection: 'row', alignItems: 'center', backgroundColor: '#9C27B0', borderRadius: 6, paddingHorizontal: 10, paddingVertical: 6, gap: 4 }} onPress={() => { if (checkFeature('save_designs', 'Save Designs')) loadDesignsList(); }} disabled={loadingDesigns}>
                  {loadingDesigns ? <ActivityIndicator size="small" color="#fff" /> : <Ionicons name="folder-open-outline" size={14} color="#fff" />}
                  <Text style={{ fontSize: 10, color: '#fff', fontWeight: '600' }}>Load</Text>
                </TouchableOpacity>
                <TouchableOpacity style={{ flexDirection: 'row', alignItems: 'center', backgroundColor: '#FF9800', borderRadius: 6, paddingHorizontal: 10, paddingVertical: 6, gap: 4 }} onPress={() => setShowTutorial(true)}>
                  <Ionicons name="help-circle-outline" size={14} color="#fff" />
                  <Text style={{ fontSize: 10, color: '#fff', fontWeight: '600' }}>Help</Text>
                </TouchableOpacity>
              </>
            )}
            <TouchableOpacity style={{ flexDirection: 'row', alignItems: 'center', backgroundColor: '#1a3a5c', borderRadius: 6, paddingHorizontal: 10, paddingVertical: 6, gap: 4 }} onPress={() => setShowDesignerInfo(true)}>
              <Ionicons name="person-circle-outline" size={14} color="#2196F3" />
              <Text style={{ fontSize: 10, color: '#2196F3', fontWeight: '600' }}>Designer Info</Text>
            </TouchableOpacity>
            <TouchableOpacity style={{ flexDirection: 'row', alignItems: 'center', backgroundColor: showDebugPanel ? '#1a3c1a' : '#1a1a1a', borderRadius: 6, paddingHorizontal: 10, paddingVertical: 6, gap: 4, borderWidth: 1, borderColor: showDebugPanel ? '#4CAF50' : '#333' }} onPress={() => setShowDebugPanel(!showDebugPanel)} data-testid="debug-panel-toggle">
              <Ionicons name="code-slash" size={14} color={showDebugPanel ? '#4CAF50' : '#888'} />
              <Text style={{ fontSize: 10, color: showDebugPanel ? '#4CAF50' : '#888', fontWeight: '600' }}>Physics Trace</Text>
            </TouchableOpacity>
          </View>
          
          {/* Band & Frequency */}
          <View style={[styles.section, { zIndex: 2000 }]}>
            <View style={[styles.rowSpaced, { zIndex: 2000 }]}>
              <View style={{ flex: 1, zIndex: 2000 }}><Dropdown label="Band" value={inputs.band} options={BANDS.map(b => ({ value: b.id, label: b.name }))} onChange={handleBandChange} /></View>
              <View style={{ flex: 1, marginLeft: 8 }}><Text style={styles.inputLabel}>Freq (MHz)</Text><TextInput style={styles.input} value={inputs.frequency_mhz} onChangeText={v => setInputs(p => ({ ...p, frequency_mhz: v }))} keyboardType="decimal-pad" /></View>
            </View>
            {inputs.band === '11m_cb' && (
              <View style={{ flexDirection: 'row', gap: 6, marginTop: 6 }}>
                {[
                  { label: 'Ch6 Super Bowl', freq: '27.025' },
                  { label: 'Ch11 Trax', freq: '27.085' },
                  { label: 'Ch19 Truckers', freq: '27.185' },
                  { label: 'Ch28 High Rollers', freq: '27.285' },
                ].map(ch => {
                  const isActive = inputs.frequency_mhz === ch.freq;
                  return (
                    <TouchableOpacity key={ch.freq} onPress={() => setInputs(p => ({ ...p, frequency_mhz: ch.freq }))}
                      style={{ flex: 1, paddingVertical: 6, borderRadius: 6, borderWidth: 1, borderColor: isActive ? '#FF9800' : '#333', backgroundColor: isActive ? 'rgba(255,152,0,0.15)' : '#1a1a1a', alignItems: 'center' }}>
                      <Text style={{ fontSize: 8, fontWeight: '700', color: isActive ? '#FF9800' : '#888' }}>{ch.label}</Text>
                    </TouchableOpacity>
                  );
                })}
              </View>
            )}
            
            {/* Antenna Orientation */}
            <View style={styles.orientationSection}>
              <Text style={styles.orientationLabel}><Ionicons name="compass-outline" size={12} color="#888" /> Antenna Orientation</Text>
              <View style={styles.orientationToggle}>
                <TouchableOpacity 
                  style={[styles.orientationBtn, inputs.antenna_orientation === 'horizontal' && styles.orientationBtnActive]} 
                  onPress={() => setInputs(p => ({ ...p, antenna_orientation: 'horizontal' }))}
                >
                  <Text style={styles.orientationIcon}>—</Text>
                  <Text style={[styles.orientationBtnText, inputs.antenna_orientation === 'horizontal' && styles.orientationBtnTextActive]}>Flat</Text>
                </TouchableOpacity>
                <TouchableOpacity 
                  style={[styles.orientationBtn, inputs.antenna_orientation === 'vertical' && styles.orientationBtnActive]} 
                  onPress={() => setInputs(p => ({ ...p, antenna_orientation: 'vertical' }))}
                >
                  <Text style={styles.orientationIcon}>|</Text>
                  <Text style={[styles.orientationBtnText, inputs.antenna_orientation === 'vertical' && styles.orientationBtnTextActive]}>Vertical</Text>
                </TouchableOpacity>
                <TouchableOpacity 
                  style={[styles.orientationBtn, inputs.antenna_orientation === 'angle45' && styles.orientationBtnActive]} 
                  onPress={() => setInputs(p => ({ ...p, antenna_orientation: 'angle45' }))}
                >
                  <Text style={styles.orientationIcon}>/</Text>
                  <Text style={[styles.orientationBtnText, inputs.antenna_orientation === 'angle45' && styles.orientationBtnTextActive]}>45°</Text>
                </TouchableOpacity>
                <TouchableOpacity 
                  style={[styles.orientationBtn, inputs.antenna_orientation === 'dual' && styles.orientationBtnActive, inputs.antenna_orientation === 'dual' && { borderColor: '#FF9800' }]} 
                  onPress={() => { if (checkFeature('dual_polarity', 'Dual Polarity')) setInputs(p => ({ ...p, antenna_orientation: 'dual' })); }}
                >
                  <Text style={styles.orientationIcon}>+</Text>
                  <Text style={[styles.orientationBtnText, inputs.antenna_orientation === 'dual' && styles.orientationBtnTextActive, inputs.antenna_orientation === 'dual' && { color: '#FF9800' }]}>Dual</Text>
                </TouchableOpacity>
              </View>
              {inputs.antenna_orientation === 'dual' && (
                <View style={{ marginTop: 6 }}>
                  <View style={{ flexDirection: 'row', gap: 10, marginBottom: 8 }}>
                    <TouchableOpacity 
                      onPress={() => { if (!inputs.dual_active) setInputs(p => ({ ...p, dual_selected_beam: 'horizontal' })); }}
                      style={{ flexDirection: 'row', alignItems: 'center', gap: 6, flex: 1, paddingVertical: 8, paddingHorizontal: 10, backgroundColor: inputs.dual_selected_beam === 'horizontal' ? 'rgba(255,152,0,0.15)' : '#1a1a1a', borderRadius: 6, borderWidth: 1, borderColor: inputs.dual_selected_beam === 'horizontal' ? '#FF9800' : '#333', opacity: inputs.dual_active ? 0.4 : 1 }}
                    >
                      <View style={{ width: 20, height: 20, borderRadius: 4, borderWidth: 2, borderColor: inputs.dual_selected_beam === 'horizontal' ? '#FF9800' : '#555', backgroundColor: inputs.dual_selected_beam === 'horizontal' ? '#FF9800' : 'transparent', justifyContent: 'center', alignItems: 'center' }}>
                        {inputs.dual_selected_beam === 'horizontal' && <Ionicons name="checkmark" size={14} color="#000" />}
                      </View>
                      <Text style={{ fontSize: 11, color: inputs.dual_selected_beam === 'horizontal' ? '#FF9800' : '#888' }}>Horizontal</Text>
                    </TouchableOpacity>
                    <TouchableOpacity 
                      onPress={() => { if (!inputs.dual_active) setInputs(p => ({ ...p, dual_selected_beam: 'vertical' })); }}
                      style={{ flexDirection: 'row', alignItems: 'center', gap: 6, flex: 1, paddingVertical: 8, paddingHorizontal: 10, backgroundColor: inputs.dual_selected_beam === 'vertical' ? 'rgba(255,152,0,0.15)' : '#1a1a1a', borderRadius: 6, borderWidth: 1, borderColor: inputs.dual_selected_beam === 'vertical' ? '#FF9800' : '#333', opacity: inputs.dual_active ? 0.4 : 1 }}
                    >
                      <View style={{ width: 20, height: 20, borderRadius: 4, borderWidth: 2, borderColor: inputs.dual_selected_beam === 'vertical' ? '#FF9800' : '#555', backgroundColor: inputs.dual_selected_beam === 'vertical' ? '#FF9800' : 'transparent', justifyContent: 'center', alignItems: 'center' }}>
                        {inputs.dual_selected_beam === 'vertical' && <Ionicons name="checkmark" size={14} color="#000" />}
                      </View>
                      <Text style={{ fontSize: 11, color: inputs.dual_selected_beam === 'vertical' ? '#FF9800' : '#888' }}>Vertical</Text>
                    </TouchableOpacity>
                  </View>
                  <TouchableOpacity 
                    onPress={() => setInputs(p => ({ ...p, dual_active: !p.dual_active }))}
                    style={{ flexDirection: 'row', alignItems: 'center', gap: 8, paddingVertical: 6, paddingHorizontal: 8, backgroundColor: inputs.dual_active ? 'rgba(255,152,0,0.15)' : '#1a1a1a', borderRadius: 6, borderWidth: 1, borderColor: inputs.dual_active ? '#FF9800' : '#333' }}
                  >
                    <View style={{ width: 20, height: 20, borderRadius: 4, borderWidth: 2, borderColor: inputs.dual_active ? '#FF9800' : '#555', backgroundColor: inputs.dual_active ? '#FF9800' : 'transparent', justifyContent: 'center', alignItems: 'center' }}>
                      {inputs.dual_active && <Ionicons name="checkmark" size={14} color="#000" />}
                    </View>
                    <Text style={{ fontSize: 11, color: inputs.dual_active ? '#FF9800' : '#888' }}>Both H+V active simultaneously</Text>
                  </TouchableOpacity>
                </View>
              )}
            </View>

            {/* Feed Type / Matching */}
            <View style={styles.orientationSection}>
              <Text style={styles.orientationLabel}><Ionicons name="git-merge-outline" size={12} color="#888" /> Feed Match</Text>
              <View style={styles.orientationToggle}>
                <TouchableOpacity 
                  style={[styles.orientationBtn, inputs.feed_type === 'direct' && styles.orientationBtnActive]} 
                  onPress={() => switchFeedType('direct')}
                >
                  <Text style={[styles.orientationBtnText, inputs.feed_type === 'direct' && styles.orientationBtnTextActive]}>Direct</Text>
                </TouchableOpacity>
                <TouchableOpacity 
                  style={[styles.orientationBtn, inputs.feed_type === 'gamma' && styles.orientationBtnActive]} 
                  onPress={() => { if (checkFeature('gamma_match', 'Gamma Match')) switchFeedType('gamma'); }}
                >
                  <Text style={[styles.orientationBtnText, inputs.feed_type === 'gamma' && styles.orientationBtnTextActive]}>Gamma</Text>
                </TouchableOpacity>
                <TouchableOpacity 
                  style={[styles.orientationBtn, inputs.feed_type === 'hairpin' && styles.orientationBtnActive]} 
                  onPress={() => { if (checkFeature('hairpin_match', 'Hairpin Match')) switchFeedType('hairpin'); }}
                >
                  <Text style={[styles.orientationBtnText, inputs.feed_type === 'hairpin' && styles.orientationBtnTextActive]}>Hairpin</Text>
                </TouchableOpacity>
              </View>

              {/* Gamma Designer Button */}
              {inputs.feed_type === 'gamma' && (
                <TouchableOpacity
                  onPress={() => setShowGammaDesigner(true)}
                  style={{ marginTop: 8, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', backgroundColor: '#1a1a2e', borderRadius: 8, padding: 10, borderWidth: 1, borderColor: '#FF9800', gap: 6 }}
                  data-testid="open-gamma-designer-btn"
                >
                  <Ionicons name="construct" size={16} color="#FF9800" />
                  <Text style={{ fontSize: 12, color: '#FF9800', fontWeight: '700' }}>Gamma Match Designer</Text>
                  <Text style={{ fontSize: 9, color: '#888' }}>- One-click recipe</Text>
                </TouchableOpacity>
              )}

              {/* Gamma Match Design Panel */}
              {inputs.feed_type === 'gamma' && results && results.matching_info?.gamma_design && (
                <View style={{ marginTop: 10, backgroundColor: '#1a1a2e', borderRadius: 8, padding: 12, borderWidth: 1, borderColor: '#FF9800' }}>
                  <Text style={{ fontSize: 13, color: '#FF9800', fontWeight: '700', marginBottom: 8 }}>Gamma Match Design</Text>
                  
                  <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginBottom: 6 }}>
                    <View style={{ flex: 1 }}>
                      <Text style={{ fontSize: 10, color: '#888' }}>Feedpoint R</Text>
                      <Text style={{ fontSize: 14, color: '#4CAF50', fontWeight: '700' }}>{results.matching_info.gamma_design.feedpoint_impedance_ohms} ohms</Text>
                    </View>
                    <View style={{ flex: 1, alignItems: 'center' }}>
                      <Text style={{ fontSize: 10, color: '#888' }}>Target</Text>
                      <Text style={{ fontSize: 14, color: '#fff', fontWeight: '700' }}>50 ohms</Text>
                    </View>
                    <View style={{ flex: 1, alignItems: 'flex-end' }}>
                      <Text style={{ fontSize: 10, color: '#888' }}>Step-Up Ratio</Text>
                      <Text style={{ fontSize: 14, color: '#FF9800', fontWeight: '700' }}>{results.matching_info.gamma_design.step_up_ratio}:1</Text>
                    </View>
                  </View>

                  <View style={{ height: 1, backgroundColor: '#333', marginVertical: 8 }} />

                  <View style={{ flexDirection: 'row', gap: 8, marginBottom: 8 }}>
                    <View style={{ flex: 1 }}>
                      <Text style={{ fontSize: 10, color: '#888', marginBottom: 4 }}>Gamma Rod Dia (in)</Text>
                      <TextInput style={{ backgroundColor: '#252525', color: '#fff', borderRadius: 6, padding: 8, fontSize: 13, borderWidth: 1, borderColor: '#333' }} value={gammaRodDia !== null ? gammaRodDia : String(results.matching_info.gamma_design.gamma_rod_diameter_in)} onChangeText={setGammaRodDia} keyboardType="decimal-pad" placeholder={String(results.matching_info.gamma_design.gamma_rod_diameter_in)} placeholderTextColor="#555" />
                    </View>
                    <View style={{ flex: 1 }}>
                      <Text style={{ fontSize: 10, color: '#888', marginBottom: 4 }}>Rod-Element Spacing (in)</Text>
                      <TextInput style={{ backgroundColor: '#252525', color: '#fff', borderRadius: 6, padding: 8, fontSize: 13, borderWidth: 1, borderColor: '#333' }} value={gammaRodSpacing !== null ? gammaRodSpacing : String(results.matching_info.gamma_design.gamma_rod_spacing_in)} onChangeText={setGammaRodSpacing} keyboardType="decimal-pad" placeholder={String(results.matching_info.gamma_design.gamma_rod_spacing_in)} placeholderTextColor="#555" />
                    </View>
                  </View>

                  {(() => {
                    const gd = results.matching_info.gamma_design;
                    const rodDia = gammaRodDia !== null ? parseFloat(gammaRodDia) || gd.gamma_rod_diameter_in : gd.gamma_rod_diameter_in;
                    const rodSpace = gammaRodSpacing !== null ? parseFloat(gammaRodSpacing) || gd.gamma_rod_spacing_in : gd.gamma_rod_spacing_in;
                    const elemDia = gd.element_diameter_in;
                    // Recalculate based on user inputs
                    const ratio = rodSpace > 0 && rodDia > 0 ? Math.sqrt(1 + (elemDia / rodDia) * Math.log(2 * rodSpace / rodDia) / Math.log(2 * rodSpace / elemDia)) : gd.step_up_ratio;
                    const rodLen = (gd.gamma_rod_length_in || 36.0) * Math.max(0.5, Math.min(2.0, rodDia / gd.gamma_rod_diameter_in));
                    // Series cap: user-editable, defaults to backend-calculated value
                    const autoCapPf = gd.capacitance_pf * Math.max(0.3, Math.min(3.0, rodDia / gd.gamma_rod_diameter_in));
                    const capPf = gammaCapPf !== null ? (parseFloat(gammaCapPf) || autoCapPf) : autoCapPf;
                    // Shorting bar length = rod-element spacing (bridges the gap)
                    const barLength = rodSpace;
                    // Shorting bar position in inches from feedpoint center
                    const barPosIn = gammaBarPos;
                    // Inductance: L(nH) ≈ 5.08 * length * (ln(2*length/dia) - 1)
                    const barInductanceNh = barPosIn > 0 && rodDia > 0 ? (5.08 * barPosIn * (Math.log(2.0 * barPosIn / rodDia) - 1.0 + rodDia / (2.0 * barPosIn))) : 0;
                    // Reactance from bar inductance: XL = 2πfL
                    const freqHz = inputs.frequency_mhz * 1e6;
                    const xL = 2 * Math.PI * freqHz * (barInductanceNh * 1e-9); // ohms
                    // Reactance from series cap: XC = 1/(2πfC)
                    const xC = capPf > 0 ? 1 / (2 * Math.PI * freqHz * (capPf * 1e-12)) : 0; // ohms
                    // Net reactance — should be near 0 when tuned (cap cancels bar inductance)
                    const netX = xL - xC;
                    return (<>
                      <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginBottom: 6 }}>
                        <View style={{ flex: 1 }}>
                          <Text style={{ fontSize: 10, color: '#888' }}>Gamma Rod Length</Text>
                          <Text style={{ fontSize: 16, color: '#4CAF50', fontWeight: '700' }}>{rodLen.toFixed(2)}"</Text>
                        </View>
                        <View style={{ flex: 1, alignItems: 'center' }}>
                          <Text style={{ fontSize: 10, color: '#888' }}>Tube</Text>
                          <Text style={{ fontSize: 14, color: '#2196F3', fontWeight: '700' }}>{gd.tube_length_in?.toFixed(1) || '22.0'}"</Text>
                        </View>
                        <View style={{ flex: 1, alignItems: 'center' }}>
                          <Text style={{ fontSize: 10, color: '#888' }}>Series Cap (pF)</Text>
                          <TextInput
                            style={{ fontSize: 16, color: '#4CAF50', fontWeight: '700', backgroundColor: '#252525', borderRadius: 6, padding: 4, borderWidth: 1, borderColor: gammaCapPf !== null ? '#4CAF50' : '#333', textAlign: 'center', minWidth: 80 }}
                            value={gammaCapPf !== null ? gammaCapPf : autoCapPf.toFixed(1)}
                            onChangeText={setGammaCapPf}
                            keyboardType="decimal-pad"
                            placeholder={autoCapPf.toFixed(1)}
                            placeholderTextColor="#555"
                          />
                        </View>
                        <View style={{ flex: 1, alignItems: 'flex-end' }}>
                          <Text style={{ fontSize: 10, color: '#888' }}>Shorting Bar</Text>
                          <Text style={{ fontSize: 16, color: '#4CAF50', fontWeight: '700' }}>{barLength.toFixed(1)}"</Text>
                        </View>
                      </View>

                      <View style={{ height: 1, backgroundColor: '#333', marginVertical: 6 }} />

                      {/* Inline Gamma SWR Meter */}
                      {results.matching_info && (() => {
                        const mi = results.matching_info;
                        const swrVal = results.swr || 10;
                        const stubL = mi.stub_inductance_nh || 0;
                        const z0g = mi.z0_gamma || 300;
                        const zR = mi.z_matched_r || 0;
                        const zX = mi.z_matched_x || 0;
                        const xStub = mi.x_stub || 0;
                        const xCap = mi.x_cap || 0;
                        const netReact = mi.net_reactance || 0;
                        const swrPct = Math.min((swrVal - 1) / 2, 1);
                        const swrColor = swrVal <= 1.2 ? '#4CAF50' : swrVal <= 1.5 ? '#8BC34A' : swrVal <= 2.0 ? '#FFC107' : swrVal <= 3.0 ? '#FF9800' : '#F44336';
                        const drvDia = mi.driven_element_dia_in || 0.5;
                        const rodOd = mi.hardware?.rod_od || 0.34;
                        return (
                          <View style={{ backgroundColor: '#111', borderRadius: 6, padding: 8, marginBottom: 8, borderWidth: 1, borderColor: '#333' }} data-testid="gamma-swr-meter">
                            <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 6 }}>
                              <Text style={{ fontSize: 10, color: '#888', flex: 1 }}>Gamma SWR</Text>
                              <Text style={{ fontSize: 22, color: swrColor, fontWeight: '800', marginRight: 8 }}>{swrVal.toFixed(2)}:1</Text>
                              <View style={{ flex: 2, height: 10, backgroundColor: '#222', borderRadius: 5, overflow: 'hidden' }}>
                                <View style={{ width: `${(1 - swrPct) * 100}%`, height: '100%', backgroundColor: swrColor, borderRadius: 5 }} />
                              </View>
                            </View>
                            <View style={{ flexDirection: 'row', justifyContent: 'space-between', flexWrap: 'wrap' }}>
                              <View style={{ marginRight: 12 }}>
                                <Text style={{ fontSize: 8, color: '#555' }}>Z0 ({drvDia}" + {rodOd}")</Text>
                                <Text style={{ fontSize: 11, color: '#2196F3', fontWeight: '600' }}>{z0g.toFixed(0)}{'\u03A9'}</Text>
                              </View>
                              <View style={{ marginRight: 12 }}>
                                <Text style={{ fontSize: 8, color: '#555' }}>Stub L</Text>
                                <Text style={{ fontSize: 11, color: '#FF9800', fontWeight: '600' }}>{stubL.toFixed(0)} nH</Text>
                              </View>
                              <View style={{ marginRight: 12 }}>
                                <Text style={{ fontSize: 8, color: '#555' }}>X stub</Text>
                                <Text style={{ fontSize: 11, color: '#FF9800', fontWeight: '600' }}>+{xStub.toFixed(1)}j</Text>
                              </View>
                              <View style={{ marginRight: 12 }}>
                                <Text style={{ fontSize: 8, color: '#555' }}>X cap</Text>
                                <Text style={{ fontSize: 11, color: '#2196F3', fontWeight: '600' }}>{xCap.toFixed(1)}j</Text>
                              </View>
                              <View style={{ marginRight: 12 }}>
                                <Text style={{ fontSize: 8, color: '#555' }}>Net X</Text>
                                <Text style={{ fontSize: 11, color: Math.abs(netReact) < 5 ? '#4CAF50' : '#FFC107', fontWeight: '600' }}>{netReact >= 0 ? '+' : ''}{netReact.toFixed(1)}j</Text>
                              </View>
                              <View>
                                <Text style={{ fontSize: 8, color: '#555' }}>Z match</Text>
                                <Text style={{ fontSize: 11, color: swrColor, fontWeight: '600' }}>{zR.toFixed(0)}{zX >= 0 ? '+' : ''}{zX.toFixed(0)}j</Text>
                              </View>
                            </View>
                          </View>
                        );
                      })()}

                      <View style={{ marginBottom: 10 }}>
                        <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginBottom: 4 }}>
                          <Text style={{ fontSize: 10, color: '#888' }}>Shorting Bar Position (from feedpoint center)</Text>
                          <Text style={{ fontSize: 12, color: '#FF9800', fontWeight: '700' }}>{barPosIn.toFixed(2)}" along {rodLen.toFixed(0)}" rod</Text>
                        </View>
                        <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                          <Pressable onPress={() => setGammaBarPos(Math.max(4, gammaBarPos - 0.25))} style={{ paddingHorizontal: 10, paddingVertical: 6, backgroundColor: '#252525', borderRadius: 4, borderWidth: 1, borderColor: '#FF9800', marginRight: 6 }}>
                            <Text style={{ color: '#FF9800', fontWeight: '700', fontSize: 16 }}>-</Text>
                          </Pressable>
                          <View style={{ flex: 1, height: 8, backgroundColor: '#333', borderRadius: 4, overflow: 'hidden', position: 'relative' }}>
                            {(() => {
                              const teflonLen = results?.matching_info?.teflon_sleeve_inches || 23;
                              const teflonPct = ((teflonLen - 4) / Math.max(rodLen - 4, 1)) * 100;
                              return teflonLen < rodLen ? (
                                <View style={{ position: 'absolute', left: `${teflonPct}%`, top: -2, bottom: -2, width: 2, backgroundColor: '#4CAF50', zIndex: 2 }} />
                              ) : null;
                            })()}
                            <View style={{ width: `${((barPosIn - 4) / Math.max(rodLen - 4, 1)) * 100}%`, height: '100%', backgroundColor: '#FF9800', borderRadius: 4 }} />
                          </View>
                          <Pressable onPress={() => setGammaBarPos(Math.min(Math.floor(rodLen), gammaBarPos + 0.25))} style={{ paddingHorizontal: 10, paddingVertical: 6, backgroundColor: '#252525', borderRadius: 4, borderWidth: 1, borderColor: '#FF9800', marginLeft: 6 }}>
                            <Text style={{ color: '#FF9800', fontWeight: '700', fontSize: 16 }}>+</Text>
                          </Pressable>
                        </View>
                        <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginTop: 2 }}>
                          <Text style={{ fontSize: 9, color: '#555' }}>Toward feedpoint (higher freq)</Text>
                          <Text style={{ fontSize: 9, color: '#4CAF50' }}>Teflon ends @ {(results?.matching_info?.teflon_sleeve_inches || 23).toFixed(0)}" | Bar range: {(results?.matching_info?.teflon_sleeve_inches || 23).toFixed(0)}"–{rodLen.toFixed(0)}"</Text>
                          <Text style={{ fontSize: 9, color: '#555' }}>Toward tip (lower freq)</Text>
                        </View>
                        <View style={{ flexDirection: 'row', justifyContent: 'center', marginTop: 1 }}>
                          <Text style={{ fontSize: 9, color: barInductanceNh > 0 ? '#FF9800' : '#555' }}>L: {barInductanceNh.toFixed(0)} nH | {netX >= 0 ? '+' : ''}{netX.toFixed(1)}j ohms</Text>
                        </View>
                      </View>

                      <View style={{ marginBottom: 4 }}>
                        <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginBottom: 4 }}>
                          <Text style={{ fontSize: 10, color: '#888' }}>Rod Insertion (Capacitance)</Text>
                          <Text style={{ fontSize: 12, color: '#2196F3', fontWeight: '700' }}>{gammaRodInsertion.toFixed(1)}" into {results?.matching_info?.tube_length_inches?.toFixed(1) || '22'}" tube</Text>
                        </View>
                        <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                          <Pressable onPress={() => setGammaRodInsertion(Math.max(0, gammaRodInsertion - 0.25))} style={{ paddingHorizontal: 10, paddingVertical: 6, backgroundColor: '#252525', borderRadius: 4, borderWidth: 1, borderColor: '#2196F3', marginRight: 6 }}>
                            <Text style={{ color: '#2196F3', fontWeight: '700', fontSize: 16 }}>-</Text>
                          </Pressable>
                          <View style={{ flex: 1, height: 8, backgroundColor: '#333', borderRadius: 4, overflow: 'hidden' }}>
                            <View style={{ width: `${(gammaRodInsertion / (results?.matching_info?.tube_length_inches || 22)) * 100}%`, height: '100%', backgroundColor: '#2196F3', borderRadius: 4 }} />
                          </View>
                          <Pressable onPress={() => setGammaRodInsertion(Math.min(results?.matching_info?.tube_length_inches || 22, gammaRodInsertion + 0.25))} style={{ paddingHorizontal: 10, paddingVertical: 6, backgroundColor: '#252525', borderRadius: 4, borderWidth: 1, borderColor: '#2196F3', marginLeft: 6 }}>
                            <Text style={{ color: '#2196F3', fontWeight: '700', fontSize: 16 }}>+</Text>
                          </Pressable>
                        </View>
                        <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginTop: 2 }}>
                          <Text style={{ fontSize: 9, color: '#555' }}>Less capacitance (0")</Text>
                          <Text style={{ fontSize: 9, color: '#888' }}>{results?.matching_info?.teflon_sleeve_inches?.toFixed(0) || '23'}" teflon sleeve on rod</Text>
                          <Text style={{ fontSize: 9, color: '#555' }}>More capacitance ({(results?.matching_info?.tube_length_inches || 22).toFixed(0)}")</Text>
                        </View>
                      </View>
                    </>);
                  })()}

                  <View style={{ height: 1, backgroundColor: '#333', marginVertical: 8 }} />
                  <Text style={{ fontSize: 10, color: '#FF9800' }}>Driven element auto-shortened 3% for gamma match</Text>
                  <Text style={{ fontSize: 9, color: '#666', marginTop: 4 }}>Slide shorting bar for resistance (50 ohm target), adjust rod insertion to cancel reactance.</Text>

                  <View style={{ height: 1, backgroundColor: '#333', marginVertical: 6 }} />
                  <Text style={{ fontSize: 10, color: '#888', fontWeight: '600', marginBottom: 4 }}>Components</Text>
                  <Text style={{ fontSize: 9, color: '#666' }}>Gamma Rod (inner) + Tube (outer) + Teflon (PTFE, 60kV/mm) = variable series capacitor. Rod connects to coax center conductor, slides in/out of tube to set capacitance.</Text>
                  <Text style={{ fontSize: 9, color: '#666', marginTop: 2 }}>Shorting Bar: Al/Cu strap bridging tube to element, sets impedance tap point.</Text>
                  <Text style={{ fontSize: 9, color: '#666', marginTop: 2 }}>Grounding: Coax shield connects directly to boom/element center (RF voltage null point).</Text>
                </View>
              )}

              {/* Hairpin Design Panel */}
              {inputs.feed_type === 'hairpin' && results && results.matching_info?.hairpin_design && (
                <View style={{ marginTop: 10, backgroundColor: '#1a1a2e', borderRadius: 8, padding: 12, borderWidth: 1, borderColor: '#2196F3' }}>
                  <Text style={{ fontSize: 13, color: '#2196F3', fontWeight: '700', marginBottom: 8 }}>Hairpin Match Design</Text>
                  
                  <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginBottom: 6 }}>
                    <View style={{ flex: 1 }}>
                      <Text style={{ fontSize: 10, color: '#888' }}>Feedpoint R</Text>
                      <Text style={{ fontSize: 14, color: '#4CAF50', fontWeight: '700' }}>{results.matching_info.hairpin_design.feedpoint_impedance_ohms} ohms</Text>
                    </View>
                    <View style={{ flex: 1, alignItems: 'center' }}>
                      <Text style={{ fontSize: 10, color: '#888' }}>Target</Text>
                      <Text style={{ fontSize: 14, color: '#fff', fontWeight: '700' }}>50 ohms</Text>
                    </View>
                    <View style={{ flex: 1, alignItems: 'flex-end' }}>
                      <Text style={{ fontSize: 10, color: '#888' }}>X_L Required</Text>
                      <Text style={{ fontSize: 14, color: '#FF9800', fontWeight: '700' }}>{results.matching_info.hairpin_design.required_reactance_ohms} ohms</Text>
                    </View>
                  </View>

                  <View style={{ height: 1, backgroundColor: '#333', marginVertical: 8 }} />

                  <View style={{ flexDirection: 'row', gap: 8, marginBottom: 8 }}>
                    <View style={{ flex: 1 }}>
                      <Text style={{ fontSize: 10, color: '#888', marginBottom: 4 }}>Rod Dia (in)</Text>
                      <TextInput style={{ backgroundColor: '#252525', color: '#fff', borderRadius: 6, padding: 8, fontSize: 13, borderWidth: 1, borderColor: '#333' }} value={hairpinRodDia} onChangeText={setHairpinRodDia} keyboardType="decimal-pad" />
                    </View>
                    <View style={{ flex: 1 }}>
                      <Text style={{ fontSize: 10, color: '#888', marginBottom: 4 }}>Rod Spacing (in)</Text>
                      <TextInput style={{ backgroundColor: '#252525', color: '#fff', borderRadius: 6, padding: 8, fontSize: 13, borderWidth: 1, borderColor: '#333' }} value={hairpinRodSpacing} onChangeText={setHairpinRodSpacing} keyboardType="decimal-pad" />
                    </View>
                  </View>

                  {(() => {
                    const hp = results.matching_info.hairpin_design;
                    const d = parseFloat(hairpinRodDia) || 0.25;
                    const s = parseFloat(hairpinRodSpacing) || 1.0;
                    const z0 = s > 0 && d > 0 ? 276.0 * Math.log10(2.0 * s / d) : hp.z0_ohms;
                    const lenDeg = z0 > 0 ? Math.atan(hp.required_reactance_ohms / z0) * (180 / Math.PI) : 0;
                    const lenIn = (lenDeg / 360.0) * hp.wavelength_inches;
                    const barIn = lenIn * hairpinBarPos;
                    return (<>
                      <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginBottom: 8 }}>
                        <View style={{ flex: 1 }}>
                          <Text style={{ fontSize: 10, color: '#888' }}>Z0</Text>
                          <Text style={{ fontSize: 14, color: '#fff', fontWeight: '700' }}>{z0.toFixed(1)} ohms</Text>
                        </View>
                        <View style={{ flex: 1, alignItems: 'center' }}>
                          <Text style={{ fontSize: 10, color: '#888' }}>Length</Text>
                          <Text style={{ fontSize: 14, color: '#fff', fontWeight: '700' }}>{lenDeg.toFixed(1)} deg</Text>
                        </View>
                        <View style={{ flex: 1, alignItems: 'flex-end' }}>
                          <Text style={{ fontSize: 10, color: '#888' }}>Hairpin Length</Text>
                          <Text style={{ fontSize: 16, color: '#4CAF50', fontWeight: '700' }}>{lenIn.toFixed(2)}"</Text>
                        </View>
                      </View>

                      <View style={{ height: 1, backgroundColor: '#333', marginVertical: 6 }} />

                      <View style={{ marginBottom: 10 }}>
                        <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginBottom: 4 }}>
                          <Text style={{ fontSize: 10, color: '#888' }}>Shorting Bar Position</Text>
                          <Text style={{ fontSize: 12, color: '#4CAF50', fontWeight: '700' }}>{barIn.toFixed(2)}" from open end</Text>
                        </View>
                        <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                          <Pressable onPress={() => setHairpinBarPos(Math.max(0.2, hairpinBarPos - 0.05))} style={{ paddingHorizontal: 10, paddingVertical: 6, backgroundColor: '#252525', borderRadius: 4, borderWidth: 1, borderColor: '#4CAF50', marginRight: 6 }}>
                            <Text style={{ color: '#4CAF50', fontWeight: '700', fontSize: 16 }}>-</Text>
                          </Pressable>
                          <View style={{ flex: 1, height: 8, backgroundColor: '#333', borderRadius: 4, overflow: 'hidden' }}>
                            <View style={{ width: `${((hairpinBarPos - 0.2) / 0.7) * 100}%`, height: '100%', backgroundColor: '#4CAF50', borderRadius: 4 }} />
                          </View>
                          <Pressable onPress={() => setHairpinBarPos(Math.min(0.9, hairpinBarPos + 0.05))} style={{ paddingHorizontal: 10, paddingVertical: 6, backgroundColor: '#252525', borderRadius: 4, borderWidth: 1, borderColor: '#4CAF50', marginLeft: 6 }}>
                            <Text style={{ color: '#4CAF50', fontWeight: '700', fontSize: 16 }}>+</Text>
                          </Pressable>
                        </View>
                        <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginTop: 2 }}>
                          <Text style={{ fontSize: 9, color: '#555' }}>Less inductance</Text>
                          <Text style={{ fontSize: 9, color: '#555' }}>More inductance</Text>
                        </View>
                      </View>

                      <View style={{ marginBottom: 4 }}>
                        <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginBottom: 4 }}>
                          <Text style={{ fontSize: 10, color: '#888' }}>Rods to Boom Gap</Text>
                          <Text style={{ fontSize: 12, color: '#2196F3', fontWeight: '700' }}>{hairpinBoomGap.toFixed(2)}"</Text>
                        </View>
                        <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                          <Pressable onPress={() => setHairpinBoomGap(Math.max(0.25, hairpinBoomGap - 0.25))} style={{ paddingHorizontal: 10, paddingVertical: 6, backgroundColor: '#252525', borderRadius: 4, borderWidth: 1, borderColor: '#2196F3', marginRight: 6 }}>
                            <Text style={{ color: '#2196F3', fontWeight: '700', fontSize: 16 }}>-</Text>
                          </Pressable>
                          <View style={{ flex: 1, height: 8, backgroundColor: '#333', borderRadius: 4, overflow: 'hidden' }}>
                            <View style={{ width: `${((hairpinBoomGap - 0.25) / 2.75) * 100}%`, height: '100%', backgroundColor: '#2196F3', borderRadius: 4 }} />
                          </View>
                          <Pressable onPress={() => setHairpinBoomGap(Math.min(3.0, hairpinBoomGap + 0.25))} style={{ paddingHorizontal: 10, paddingVertical: 6, backgroundColor: '#252525', borderRadius: 4, borderWidth: 1, borderColor: '#2196F3', marginLeft: 6 }}>
                            <Text style={{ color: '#2196F3', fontWeight: '700', fontSize: 16 }}>+</Text>
                          </Pressable>
                        </View>
                        <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginTop: 2 }}>
                          <Text style={{ fontSize: 9, color: '#555' }}>Closer to boom</Text>
                          <Text style={{ fontSize: 9, color: '#555' }}>Farther from boom</Text>
                        </View>
                      </View>
                    </>);
                  })()}

                  <View style={{ height: 1, backgroundColor: '#333', marginVertical: 8 }} />
                  <Text style={{ fontSize: 10, color: '#FF9800' }}>Driven element auto-shortened 4% for hairpin match</Text>
                  <Text style={{ fontSize: 9, color: '#666', marginTop: 4 }}>Start slightly long, slide shorting bar to tune for lowest SWR at center freq</Text>
                </View>
              )}

              {/* Coax Feedline Settings */}
              <FeatureGate feature="coax_loss" label="Coax Loss Calculator">
              <View style={{ marginTop: 12, paddingTop: 10, borderTopWidth: 1, borderTopColor: '#333' }}>
                <Text style={{ fontSize: 12, color: '#888', fontWeight: '700', marginBottom: 8 }}>Feedline / Power</Text>
                <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 4, marginBottom: 8 }}>
                  {COAX_OPTIONS.map(c => (
                    <TouchableOpacity key={c.key}
                      style={{ paddingHorizontal: 8, paddingVertical: 5, borderRadius: 5, borderWidth: 1, borderColor: coaxType === c.key ? '#2196F3' : '#333', backgroundColor: coaxType === c.key ? '#2196F322' : '#1a1a1a' }}
                      onPress={() => setCoaxType(c.key)}
                    >
                      <Text style={{ fontSize: 10, fontWeight: '700', color: coaxType === c.key ? '#2196F3' : '#888' }}>{c.label}</Text>
                    </TouchableOpacity>
                  ))}
                </View>
                <View style={{ flexDirection: 'row', gap: 8 }}>
                  <View style={{ flex: 1 }}>
                    <Text style={{ fontSize: 9, color: '#888', marginBottom: 3 }}>Length (ft)</Text>
                    <TextInput
                      style={{ backgroundColor: '#111', borderWidth: 1, borderColor: '#333', borderRadius: 5, paddingHorizontal: 8, paddingVertical: 5, color: '#fff', fontSize: 13, fontWeight: '700' }}
                      value={coaxLengthFt}
                      onChangeText={setCoaxLengthFt}
                      keyboardType="numeric"
                      placeholder="100"
                      placeholderTextColor="#555"
                    />
                  </View>
                  <View style={{ flex: 1 }}>
                    <Text style={{ fontSize: 9, color: '#888', marginBottom: 3 }}>TX Power (W)</Text>
                    <TextInput
                      style={{ backgroundColor: '#111', borderWidth: 1, borderColor: '#333', borderRadius: 5, paddingHorizontal: 8, paddingVertical: 5, color: '#fff', fontSize: 13, fontWeight: '700' }}
                      value={transmitPowerWatts}
                      onChangeText={setTransmitPowerWatts}
                      keyboardType="numeric"
                      placeholder="500"
                      placeholderTextColor="#555"
                    />
                  </View>
                </View>
                {results?.coax_info && (
                  <View style={{ marginTop: 6, flexDirection: 'row', gap: 12 }}>
                    <Text style={{ fontSize: 9, color: '#666' }}>Loss: <Text style={{ color: (results.coax_info.total_loss_db || 0) > 1.0 ? '#f44336' : '#4CAF50', fontWeight: '700' }}>{results.coax_info.total_loss_db} dB</Text></Text>
                    <Text style={{ fontSize: 9, color: '#666' }}>At antenna: <Text style={{ color: '#2196F3', fontWeight: '700' }}>{results.power_at_antenna_watts}W</Text></Text>
                  </View>
                )}
              </View>
              </FeatureGate>

            </View>
          </View>

          {/* Elements */}
          <View style={[styles.section, { zIndex: 100 }]}>
            <View style={styles.rowSpaced}>
              <Text style={styles.sectionTitle}><Ionicons name="git-branch-outline" size={14} color="#4CAF50" /> Elements <Text style={styles.maxElementsHint}>(max: {maxElements})</Text></Text>
              <View style={styles.unitToggle}>
                <TouchableOpacity style={[styles.unitBtn, elementUnit === 'inches' && styles.unitBtnActive]} onPress={() => convertElementUnit('inches')}><Text style={[styles.unitBtnText, elementUnit === 'inches' && styles.unitBtnTextActive]}>in</Text></TouchableOpacity>
                <TouchableOpacity style={[styles.unitBtn, elementUnit === 'meters' && styles.unitBtnActive]} onPress={() => convertElementUnit('meters')}><Text style={[styles.unitBtnText, elementUnit === 'meters' && styles.unitBtnTextActive]}>m</Text></TouchableOpacity>
              </View>
            </View>
            {/* Reflector Toggle */}
            <View style={[styles.rowSpaced, { marginVertical: 6 }]}>
              <View style={styles.reflectorToggle}>
                <TouchableOpacity 
                  style={[styles.reflectorBtn, inputs.use_reflector && styles.reflectorBtnActive]} 
                  onPress={() => toggleReflector(true)}
                >
                  <Ionicons name="checkmark-circle" size={14} color={inputs.use_reflector ? '#fff' : '#666'} />
                  <Text style={[styles.reflectorBtnText, inputs.use_reflector && styles.reflectorBtnTextActive]}>With Reflector</Text>
                </TouchableOpacity>
                <TouchableOpacity 
                  style={[styles.reflectorBtn, !inputs.use_reflector && styles.reflectorBtnActive]} 
                  onPress={() => toggleReflector(false)}
                >
                  <Ionicons name="close-circle" size={14} color={!inputs.use_reflector ? '#fff' : '#666'} />
                  <Text style={[styles.reflectorBtnText, !inputs.use_reflector && styles.reflectorBtnTextActive]}>No Reflector</Text>
                </TouchableOpacity>
              </View>
            </View>
            <View style={[styles.rowSpaced, { marginTop: 6, zIndex: 1000 }]}>
              <View style={{ flex: 1, zIndex: 1000 }}>
                <Dropdown value={inputs.num_elements.toString()} options={elementOptions} onChange={(v: string) => updateElementCount(parseInt(v))} />
              </View>
              <TouchableOpacity style={styles.autoTuneBtn} onPress={() => { if (checkFeature('auto_tune', 'Auto-Tune')) autoTune(); }} disabled={tuning}>
                {tuning ? <ActivityIndicator size="small" color="#fff" /> : <><Ionicons name="flash" size={14} color="#fff" /><Text style={styles.autoTuneBtnText}>Auto-Tune</Text></>}
              </TouchableOpacity>
            </View>
            <View style={{ zIndex: 1 }}>
              {inputs.elements.map((elem, idx) => <ElementInput key={`${elem.element_type}-${idx}`} element={elem} index={idx} onChange={updateElement} unit={elementUnit} taperEnabled={inputs.taper.enabled} taperConfig={inputs.taper} />)}
            </View>
          </View>

          {/* Visual Element Viewer - Top Down */}
          <View style={{ backgroundColor: '#111', borderRadius: 8, padding: 8, marginBottom: 10, borderWidth: 1, borderColor: '#222' }}>
            <Text style={{ fontSize: 12, color: '#fff', marginBottom: 4, fontWeight: '600' }}>TOP VIEW (looking down on boom)</Text>
            <Svg width={Math.max(200, screenWidth - 40)} height={80}>
              {(() => {
                const w = Math.max(200, screenWidth - 40);
                const pad = 20;
                const elements = inputs.elements;
                const positions = elements.map(e => parseFloat(e.position) || 0);
                const lengths = elements.map(e => parseFloat(e.length) || 0);
                const maxPos = Math.max(...positions, 1);
                const maxLen = Math.max(...lengths, 1);
                const scale = (w - pad * 2) / maxPos;
                const yCenter = 40;
                const boomY = yCenter;
                const nodes: any[] = [];
                // Boom line
                const boomStart = pad;
                const boomEnd = pad + maxPos * scale;
                nodes.push(<Line key="boom" x1={boomStart} y1={boomY} x2={boomEnd} y2={boomY} stroke="#444" strokeWidth={3} />);
                // Elements
                elements.forEach((el, i) => {
                  const x = pad + positions[i] * scale;
                  const halfLen = (lengths[i] / maxLen) * 30;
                  const color = el.element_type === 'reflector' ? '#f44336' : el.element_type === 'driven' ? '#4CAF50' : '#2196F3';
                  nodes.push(<Line key={`el-${i}`} x1={x} y1={yCenter - halfLen} x2={x} y2={yCenter + halfLen} stroke={color} strokeWidth={2.5} strokeLinecap="round" />);
                  nodes.push(<SvgText key={`lbl-${i}`} x={x} y={12} fill={color} fontSize={10} textAnchor="middle" fontWeight="bold">{el.element_type === 'reflector' ? 'R' : el.element_type === 'driven' ? 'DE' : `D${i - (inputs.use_reflector ? 1 : 0)}`}</SvgText>);
                  // Spacing label between elements
                  if (i > 0) {
                    const prevX = pad + positions[i - 1] * scale;
                    const midX = (prevX + x) / 2;
                    const spacing = (positions[i] - positions[i - 1]).toFixed(1);
                    nodes.push(<SvgText key={`sp-${i}`} x={midX} y={74} fill="#aaa" fontSize={9} textAnchor="middle">{spacing}"</SvgText>);
                  }
                });
                return nodes;
              })()}
            </Svg>
          </View>

          {/* Physical Setup */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}><Ionicons name="construct-outline" size={14} color="#4CAF50" /> Setup</Text>
            <View style={styles.rowSpaced}>
              <View style={{ flex: 1 }}><Text style={styles.inputLabel}>Height</Text><TextInput style={styles.input} value={inputs.height_from_ground} onChangeText={v => setInputs(p => ({ ...p, height_from_ground: v }))} keyboardType="decimal-pad" /></View>
              <View style={styles.unitToggle}><TouchableOpacity style={[styles.unitBtn, inputs.height_unit === 'ft' && styles.unitBtnActive]} onPress={() => setInputs(p => ({ ...p, height_unit: 'ft' }))}><Text style={[styles.unitBtnText, inputs.height_unit === 'ft' && styles.unitBtnTextActive]}>ft</Text></TouchableOpacity><TouchableOpacity style={[styles.unitBtn, inputs.height_unit === 'inches' && styles.unitBtnActive]} onPress={() => setInputs(p => ({ ...p, height_unit: 'inches' }))}><Text style={[styles.unitBtnText, inputs.height_unit === 'inches' && styles.unitBtnTextActive]}>in</Text></TouchableOpacity></View>
              <View style={{ flex: 1, marginLeft: 8 }}><Text style={styles.inputLabel}>Boom Ø</Text><TextInput style={styles.input} value={inputs.boom_diameter} onChangeText={v => setInputs(p => ({ ...p, boom_diameter: v }))} keyboardType="decimal-pad" /></View>
              <View style={styles.unitToggle}><TouchableOpacity style={[styles.unitBtn, inputs.boom_unit === 'mm' && styles.unitBtnActive]} onPress={() => setInputs(p => ({ ...p, boom_unit: 'mm' }))}><Text style={[styles.unitBtnText, inputs.boom_unit === 'mm' && styles.unitBtnTextActive]}>mm</Text></TouchableOpacity><TouchableOpacity style={[styles.unitBtn, inputs.boom_unit === 'inches' && styles.unitBtnActive]} onPress={() => setInputs(p => ({ ...p, boom_unit: 'inches' }))}><Text style={[styles.unitBtnText, inputs.boom_unit === 'inches' && styles.unitBtnTextActive]}>in</Text></TouchableOpacity></View>
            </View>
            {/* Element Mount Type - 3 options */}
            <View style={{ flexDirection: 'row', gap: 6, marginTop: 8 }}>
              {([
                { key: 'bonded', label: 'Bonded', icon: 'flash', color: '#FF9800', desc: 'Welded/bolted to metal boom' },
                { key: 'insulated', label: 'Insulated', icon: 'shield-half', color: '#2196F3', desc: 'Sleeves on metal boom' },
                { key: 'nonconductive', label: 'Non-Cond', icon: 'leaf', color: '#4CAF50', desc: 'PVC/wood/fiberglass boom' },
              ] as const).map(opt => {
                const active = inputs.boom_mount === opt.key;
                return (
                  <TouchableOpacity key={opt.key} onPress={() => setInputs(p => ({ ...p, boom_mount: opt.key as any, boom_grounded: opt.key === 'bonded' }))}
                    style={{ flex: 1, alignItems: 'center', justifyContent: 'center', gap: 3, paddingVertical: 7, borderRadius: 6, borderWidth: 1, borderColor: active ? opt.color : '#333', backgroundColor: active ? `${opt.color}22` : '#1a1a1a' }}>
                    <Ionicons name={opt.icon as any} size={14} color={active ? opt.color : '#555'} />
                    <Text style={{ fontSize: 10, fontWeight: '700', color: active ? opt.color : '#888' }}>{opt.label}</Text>
                    <Text style={{ fontSize: 7, color: active ? opt.color + 'AA' : '#555' }}>{opt.desc}</Text>
                  </TouchableOpacity>
                );
              })}
            </View>
            {/* Optimize Height Button */}
            <TouchableOpacity style={styles.optimizeHeightBtn} onPress={() => { if (checkFeature('optimize_height', 'Optimize Height')) optimizeHeight(); }} disabled={optimizingHeight}>
              {optimizingHeight ? <ActivityIndicator size="small" color="#fff" /> : <><Ionicons name="trending-up" size={14} color="#fff" /><Text style={styles.optimizeHeightBtnText}>Optimize Height (10'-100')</Text></>}
            </TouchableOpacity>
            {/* Height Optimization Result */}
            {heightOptResult && (
              <View style={styles.heightOptResult}>
                <Text style={styles.heightOptTitle}>Best Height Found</Text>
                <View style={styles.heightOptRow}>
                  <View style={styles.heightOptItem}><Text style={styles.heightOptLabel}>Height</Text><Text style={styles.heightOptValue}>{heightOptResult.optimal_height}'</Text></View>
                  <View style={styles.heightOptItem}><Text style={styles.heightOptLabel}>SWR</Text><Text style={styles.heightOptValue}>{heightOptResult.optimal_swr.toFixed(2)}:1</Text></View>
                  <View style={styles.heightOptItem}><Text style={styles.heightOptLabel}>Gain</Text><Text style={styles.heightOptValue}>{heightOptResult.optimal_gain}dBi</Text></View>
                  <View style={styles.heightOptItem}><Text style={styles.heightOptLabel}>F/B</Text><Text style={styles.heightOptValue}>{heightOptResult.optimal_fb_ratio}dB</Text></View>
                </View>
                
                {/* Sort Options */}
                <View style={styles.heightSortSection}>
                  <Text style={styles.heightSortLabel}>Sort Heights By:</Text>
                  <View style={styles.heightSortOptions}>
                    <TouchableOpacity 
                      style={[styles.heightSortBtn, heightSortBy === 'default' && styles.heightSortBtnActive]}
                      onPress={() => setHeightSortBy('default')}
                    >
                      <Text style={[styles.heightSortBtnText, heightSortBy === 'default' && styles.heightSortBtnTextActive]}>Score</Text>
                    </TouchableOpacity>
                    <TouchableOpacity 
                      style={[styles.heightSortBtn, heightSortBy === 'takeoff' && styles.heightSortBtnActive]}
                      onPress={() => setHeightSortBy('takeoff')}
                    >
                      <Text style={[styles.heightSortBtnText, heightSortBy === 'takeoff' && styles.heightSortBtnTextActive]}>Take-off</Text>
                    </TouchableOpacity>
                    <TouchableOpacity 
                      style={[styles.heightSortBtn, heightSortBy === 'gain' && styles.heightSortBtnActive]}
                      onPress={() => setHeightSortBy('gain')}
                    >
                      <Text style={[styles.heightSortBtnText, heightSortBy === 'gain' && styles.heightSortBtnTextActive]}>Gain</Text>
                    </TouchableOpacity>
                    <TouchableOpacity 
                      style={[styles.heightSortBtn, heightSortBy === 'fb' && styles.heightSortBtnActive]}
                      onPress={() => setHeightSortBy('fb')}
                    >
                      <Text style={[styles.heightSortBtnText, heightSortBy === 'fb' && styles.heightSortBtnTextActive]}>F/B</Text>
                    </TouchableOpacity>
                  </View>
                </View>
                
                {/* Sorted Heights List */}
                {heightOptResult.heights_tested && (
                  <View style={styles.sortedHeightsList}>
                    <Text style={styles.sortedHeightsTitle}>
                      Top 10 Heights by {heightSortBy === 'default' ? 'Combined Score' : heightSortBy === 'takeoff' ? 'Take-off Angle (Low→High)' : heightSortBy === 'gain' ? 'Gain (High→Low)' : 'F/B Ratio (High→Low)'}
                    </Text>
                    <View style={styles.sortedHeightsHeader}>
                      <Text style={[styles.sortedHeightsCell, { flex: 0.8 }]}>Ht</Text>
                      <Text style={[styles.sortedHeightsCell, { flex: 1 }]}>Take-off</Text>
                      <Text style={[styles.sortedHeightsCell, { flex: 1 }]}>Gain</Text>
                      <Text style={[styles.sortedHeightsCell, { flex: 1 }]}>F/B</Text>
                      <Text style={[styles.sortedHeightsCell, { flex: 0.8 }]}>SWR</Text>
                    </View>
                    {[...heightOptResult.heights_tested]
                      .sort((a: any, b: any) => {
                        if (heightSortBy === 'takeoff') return (a.takeoff_angle || 90) - (b.takeoff_angle || 90);
                        if (heightSortBy === 'gain') return b.gain - a.gain;
                        if (heightSortBy === 'fb') return b.fb_ratio - a.fb_ratio;
                        return b.score - a.score;  // default: best score first
                      })
                      .slice(0, 10)
                      .map((h: any, idx: number) => (
                        <View key={h.height} style={[styles.sortedHeightsRow, idx === 0 && styles.sortedHeightsRowTop]}>
                          <Text style={[styles.sortedHeightsCell, styles.sortedHeightsCellValue, { flex: 0.8 }]}>{h.height}'</Text>
                          <Text style={[styles.sortedHeightsCell, styles.sortedHeightsCellValue, { flex: 1, color: (h.takeoff_angle || 0) < 25 ? '#4CAF50' : '#888' }]}>{h.takeoff_angle || '-'}°</Text>
                          <Text style={[styles.sortedHeightsCell, styles.sortedHeightsCellValue, { flex: 1 }]}>{h.gain}dBi</Text>
                          <Text style={[styles.sortedHeightsCell, styles.sortedHeightsCellValue, { flex: 1 }]}>{h.fb_ratio}dB</Text>
                          <Text style={[styles.sortedHeightsCell, styles.sortedHeightsCellValue, { flex: 0.8 }]}>{h.swr.toFixed(1)}</Text>
                        </View>
                      ))
                    }
                  </View>
                )}
              </View>
            )}
          </View>
          
          {/* Boom Lock & Spacing Lock */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}><Ionicons name="lock-closed-outline" size={14} color="#FF9800" /> Tuning Locks</Text>
            <Text style={styles.lockHint}>Control what Auto-Tune can modify</Text>
            
            {/* Boom Lock */}
            <View style={styles.lockRow}>
              <View style={styles.lockLeft}>
                <Switch value={boomLockEnabled} onValueChange={(v) => { setBoomLockEnabled(v); if (v && spacingMode !== 'normal') { applySpacing('1.0'); setSpacingMode('normal'); } }} trackColor={{ false: '#333', true: '#FF9800' }} thumbColor="#fff" />
                <View style={styles.lockLabelContainer}>
                  <Text style={styles.lockLabel}>Boom Restraint</Text>
                  <Text style={styles.lockDesc}>Set boom length, adjust spacing</Text>
                </View>
              </View>
              {boomLockEnabled && (
                <View style={styles.lockInputContainer}>
                  <TextInput 
                    style={styles.lockInput} 
                    value={maxBoomLength} 
                    onChangeText={setMaxBoomLength} 
                    keyboardType="decimal-pad" 
                    placeholder="120"
                    placeholderTextColor="#555"
                  />
                  <Text style={styles.lockInputUnit}>{elementUnit === 'meters' ? 'm' : '"'}</Text>
                </View>
              )}
            </View>
            
            {/* Current Boom Display */}
            <View style={styles.currentBoomInfo}>
              <Ionicons name="resize-outline" size={12} color="#888" />
              <Text style={styles.currentBoomText}>Current boom: {calculateBoomLength().ft}' {calculateBoomLength().inches.toFixed(1)}" ({calculateBoomLength().total_inches.toFixed(0)}")</Text>
              {boomLockEnabled && parseFloat(maxBoomLength) < calculateBoomLength().total_inches && (
                <Text style={styles.boomWarning}> ↕️ Will compress</Text>
              )}
              {boomLockEnabled && parseFloat(maxBoomLength) > calculateBoomLength().total_inches && (
                <Text style={[styles.boomWarning, { color: '#4CAF50' }]}> ↕️ Will extend</Text>
              )}
            </View>
            
            {/* Spacing Lock */}
            <View style={[styles.lockRow, { marginTop: 12 }]}>
              <View style={styles.lockLeft}>
                <Switch value={spacingLockEnabled} onValueChange={setSpacingLockEnabled} trackColor={{ false: '#333', true: '#2196F3' }} thumbColor="#fff" />
                <View style={styles.lockLabelContainer}>
                  <Text style={styles.lockLabel}>Spacing Lock</Text>
                  <Text style={styles.lockDesc}>Only tune lengths, keep positions</Text>
                </View>
              </View>
              {spacingLockEnabled && (
                <View style={styles.lockBadge}>
                  <Ionicons name="lock-closed" size={10} color="#2196F3" />
                  <Text style={styles.lockBadgeText}>Positions locked</Text>
                </View>
              )}
            </View>

            {/* Element Spacing Control - hidden when boom lock is active */}
            {!boomLockEnabled && (
            <FeatureGate feature="spacing_control" label="Spacing Control">
            <View style={{ marginTop: 12, backgroundColor: '#1a1a1a', borderRadius: 8, padding: 12 }}>
              <Text style={{ fontSize: 12, fontWeight: '700', color: '#aaa', marginBottom: 8 }}>
                <Ionicons name="resize-outline" size={12} color="#9C27B0" /> Element Spacing
              </Text>
              <View style={{ flexDirection: 'row', marginBottom: 8, gap: 4 }}>
                <TouchableOpacity 
                  style={{ flex: 1, padding: 6, borderRadius: 6, backgroundColor: spacingMode === 'tight' && spacingLevel === '0.6' ? '#9C27B0' : '#252525', alignItems: 'center' }}
                  onPress={() => { setSpacingMode('tight'); applySpacing('0.6'); setSpacingNudgeCount(0); }}
                >
                  <Ionicons name="contract-outline" size={12} color={spacingMode === 'tight' && spacingLevel === '0.6' ? '#fff' : '#888'} />
                  <Text style={{ fontSize: 9, color: spacingMode === 'tight' && spacingLevel === '0.6' ? '#fff' : '#888', marginTop: 1 }}>V.Short</Text>
                </TouchableOpacity>
                <TouchableOpacity 
                  style={{ flex: 1, padding: 6, borderRadius: 6, backgroundColor: spacingMode === 'tight' && spacingLevel !== '0.6' ? '#2196F3' : '#252525', alignItems: 'center' }}
                  onPress={() => { setSpacingMode('tight'); applySpacing('0.8'); setSpacingNudgeCount(0); }}
                >
                  <Ionicons name="contract-outline" size={12} color={spacingMode === 'tight' && spacingLevel !== '0.6' ? '#fff' : '#888'} />
                  <Text style={{ fontSize: 9, color: spacingMode === 'tight' && spacingLevel !== '0.6' ? '#fff' : '#888', marginTop: 1 }}>Short</Text>
                </TouchableOpacity>
                <TouchableOpacity 
                  style={{ flex: 1, padding: 6, borderRadius: 6, backgroundColor: spacingMode === 'normal' ? '#4CAF50' : '#252525', alignItems: 'center' }}
                  onPress={() => { setSpacingMode('normal'); applySpacing('1.0'); setSpacingNudgeCount(0); }}
                >
                  <Ionicons name="remove-outline" size={12} color={spacingMode === 'normal' ? '#fff' : '#888'} />
                  <Text style={{ fontSize: 9, color: spacingMode === 'normal' ? '#fff' : '#888', marginTop: 1 }}>Normal</Text>
                </TouchableOpacity>
                <TouchableOpacity 
                  style={{ flex: 1, padding: 6, borderRadius: 6, backgroundColor: spacingMode === 'long' && spacingLevel !== '1.5' ? '#FF9800' : '#252525', alignItems: 'center' }}
                  onPress={() => { setSpacingMode('long'); applySpacing('1.2'); setSpacingNudgeCount(0); }}
                >
                  <Ionicons name="expand-outline" size={12} color={spacingMode === 'long' && spacingLevel !== '1.5' ? '#fff' : '#888'} />
                  <Text style={{ fontSize: 9, color: spacingMode === 'long' && spacingLevel !== '1.5' ? '#fff' : '#888', marginTop: 1 }}>Long</Text>
                </TouchableOpacity>
                <TouchableOpacity 
                  style={{ flex: 1, padding: 6, borderRadius: 6, backgroundColor: spacingMode === 'long' && spacingLevel === '1.5' ? '#f44336' : '#252525', alignItems: 'center' }}
                  onPress={() => { setSpacingMode('long'); applySpacing('1.5'); setSpacingNudgeCount(0); }}
                >
                  <Ionicons name="expand-outline" size={12} color={spacingMode === 'long' && spacingLevel === '1.5' ? '#fff' : '#888'} />
                  <Text style={{ fontSize: 9, color: spacingMode === 'long' && spacingLevel === '1.5' ? '#fff' : '#888', marginTop: 1 }}>V.Long</Text>
                </TouchableOpacity>
              </View>
              <View style={{ flexDirection: 'row', marginTop: 6, alignItems: 'center', justifyContent: 'center', gap: 8 }}>
                <TouchableOpacity
                  onPress={() => nudgeSpacing(-1)}
                  style={{ flexDirection: 'row', alignItems: 'center', paddingHorizontal: 14, paddingVertical: 8, borderRadius: 6, backgroundColor: '#252525', borderWidth: 1, borderColor: spacingNudgeCount <= -20 ? '#333' : '#9C27B0', opacity: spacingNudgeCount <= -20 ? 0.4 : 1 }}
                  disabled={spacingNudgeCount <= -20}
                >
                  <Ionicons name="chevron-back" size={18} color="#9C27B0" />
                  <Text style={{ fontSize: 12, color: '#9C27B0', fontWeight: '700', marginLeft: 2 }}>Tighter</Text>
                </TouchableOpacity>
                <View style={{ backgroundColor: '#333', borderRadius: 6, paddingHorizontal: 10, paddingVertical: 6, minWidth: 50, alignItems: 'center' }}>
                  <Text style={{ fontSize: 11, color: spacingNudgeCount === 0 ? '#666' : '#9C27B0', fontWeight: '700' }}>
                    {spacingNudgeCount === 0 ? '0%' : `${(spacingNudgeCount * 0.5) > 0 ? '+' : ''}${(spacingNudgeCount * 0.5).toFixed(1)}%`}
                  </Text>
                </View>
                <TouchableOpacity
                  onPress={() => nudgeSpacing(1)}
                  style={{ flexDirection: 'row', alignItems: 'center', paddingHorizontal: 14, paddingVertical: 8, borderRadius: 6, backgroundColor: '#252525', borderWidth: 1, borderColor: spacingNudgeCount >= 20 ? '#333' : '#9C27B0', opacity: spacingNudgeCount >= 20 ? 0.4 : 1 }}
                  disabled={spacingNudgeCount >= 20}
                >
                  <Text style={{ fontSize: 12, color: '#9C27B0', fontWeight: '700', marginRight: 2 }}>Wider</Text>
                  <Ionicons name="chevron-forward" size={18} color="#9C27B0" />
                </TouchableOpacity>
              </View>

              {/* Spacing Overrides for Driven Element */}
              <View style={{ marginTop: 10 }}>
                <Text style={{ fontSize: 11, color: '#888', marginBottom: 6 }}>Driven Element Spacing</Text>
                <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 4 }}>
                  <TouchableOpacity
                    style={{ flex: 1, minWidth: 60, padding: 6, borderRadius: 6, backgroundColor: closeDriven === 'vclose' ? '#9C27B0' : '#252525', alignItems: 'center' }}
                    onPress={() => { setCloseDriven(closeDriven === 'vclose' ? false : 'vclose'); setFarDriven(false); setDrivenNudgeCount(0); triggerSpacingAutoTune(); }}
                  >
                    <Ionicons name="arrow-back-outline" size={12} color={closeDriven === 'vclose' ? '#fff' : '#888'} />
                    <Text style={{ fontSize: 9, color: closeDriven === 'vclose' ? '#fff' : '#888', marginTop: 1 }}>V.Close (0.08)</Text>
                  </TouchableOpacity>
                  <TouchableOpacity
                    style={{ flex: 1, minWidth: 60, padding: 6, borderRadius: 6, backgroundColor: closeDriven === 'close' ? '#2196F3' : '#252525', alignItems: 'center' }}
                    onPress={() => { setCloseDriven(closeDriven === 'close' ? false : 'close'); setFarDriven(false); setDrivenNudgeCount(0); triggerSpacingAutoTune(); }}
                  >
                    <Ionicons name="arrow-back-outline" size={12} color={closeDriven === 'close' ? '#fff' : '#888'} />
                    <Text style={{ fontSize: 9, color: closeDriven === 'close' ? '#fff' : '#888', marginTop: 1 }}>Close (0.12)</Text>
                  </TouchableOpacity>
                  <TouchableOpacity
                    style={{ flex: 1, minWidth: 60, padding: 6, borderRadius: 6, backgroundColor: (!closeDriven && !farDriven) ? '#4CAF50' : '#252525', alignItems: 'center' }}
                    onPress={() => { setCloseDriven(false); setFarDriven(false); setDrivenNudgeCount(0); triggerSpacingAutoTune(); }}
                  >
                    <Ionicons name="remove-outline" size={12} color={(!closeDriven && !farDriven) ? '#fff' : '#888'} />
                    <Text style={{ fontSize: 9, color: (!closeDriven && !farDriven) ? '#fff' : '#888', marginTop: 1 }}>Normal (0.18)</Text>
                  </TouchableOpacity>
                  <TouchableOpacity
                    style={{ flex: 1, minWidth: 60, padding: 6, borderRadius: 6, backgroundColor: farDriven === 'far' ? '#FF9800' : '#252525', alignItems: 'center' }}
                    onPress={() => { setFarDriven(farDriven === 'far' ? false : 'far'); setCloseDriven(false); setDrivenNudgeCount(0); triggerSpacingAutoTune(); }}
                  >
                    <Ionicons name="arrow-forward-outline" size={12} color={farDriven === 'far' ? '#fff' : '#888'} />
                    <Text style={{ fontSize: 9, color: farDriven === 'far' ? '#fff' : '#888', marginTop: 1 }}>Far (0.22)</Text>
                  </TouchableOpacity>
                  <TouchableOpacity
                    style={{ flex: 1, minWidth: 60, padding: 6, borderRadius: 6, backgroundColor: farDriven === 'vfar' ? '#f44336' : '#252525', alignItems: 'center' }}
                    onPress={() => { setFarDriven(farDriven === 'vfar' ? false : 'vfar'); setCloseDriven(false); setDrivenNudgeCount(0); triggerSpacingAutoTune(); }}
                  >
                    <Ionicons name="arrow-forward-outline" size={12} color={farDriven === 'vfar' ? '#fff' : '#888'} />
                    <Text style={{ fontSize: 9, color: farDriven === 'vfar' ? '#fff' : '#888', marginTop: 1 }}>V.Far (0.28)</Text>
                  </TouchableOpacity>
                </View>
                <View style={{ flexDirection: 'row', marginTop: 6, alignItems: 'center', justifyContent: 'center', gap: 8 }}>
                  <TouchableOpacity
                    onPress={() => nudgeElement('driven', -1)}
                    style={{ flexDirection: 'row', alignItems: 'center', paddingHorizontal: 14, paddingVertical: 8, borderRadius: 6, backgroundColor: '#252525', borderWidth: 1, borderColor: drivenNudgeCount <= -90 ? '#333' : '#4CAF50', opacity: drivenNudgeCount <= -90 ? 0.4 : 1 }}
                    disabled={drivenNudgeCount <= -90}
                  >
                    <Ionicons name="chevron-back" size={18} color="#4CAF50" />
                    <Text style={{ fontSize: 12, color: '#4CAF50', fontWeight: '700', marginLeft: 2 }}>Closer</Text>
                  </TouchableOpacity>
                  <View style={{ backgroundColor: '#333', borderRadius: 6, paddingHorizontal: 10, paddingVertical: 6, minWidth: 50, alignItems: 'center' }}>
                    <Text style={{ fontSize: 11, color: drivenNudgeCount === 0 ? '#666' : '#4CAF50', fontWeight: '700' }}>
                      {drivenNudgeCount === 0 ? '0%' : `${(drivenNudgeCount * 0.5) > 0 ? '+' : ''}${(drivenNudgeCount * 0.5).toFixed(1)}%`}
                    </Text>
                  </View>
                  <TouchableOpacity
                    onPress={() => nudgeElement('driven', 1)}
                    style={{ flexDirection: 'row', alignItems: 'center', paddingHorizontal: 14, paddingVertical: 8, borderRadius: 6, backgroundColor: '#252525', borderWidth: 1, borderColor: drivenNudgeCount >= 90 ? '#333' : '#4CAF50', opacity: drivenNudgeCount >= 90 ? 0.4 : 1 }}
                    disabled={drivenNudgeCount >= 90}
                  >
                    <Text style={{ fontSize: 12, color: '#4CAF50', fontWeight: '700', marginRight: 2 }}>Farther</Text>
                    <Ionicons name="chevron-forward" size={18} color="#4CAF50" />
                  </TouchableOpacity>
                </View>
              </View>

              {/* Spacing Overrides for First Director */}
              <View style={{ marginTop: 10 }}>
                <Text style={{ fontSize: 11, color: '#888', marginBottom: 6 }}>1st Director Spacing</Text>
                <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 4 }}>
                  <TouchableOpacity
                    style={{ flex: 1, minWidth: 60, padding: 6, borderRadius: 6, backgroundColor: closeDir1 === 'vclose' ? '#9C27B0' : '#252525', alignItems: 'center' }}
                    onPress={() => { setCloseDir1(closeDir1 === 'vclose' ? false : 'vclose'); setFarDir1(false); setDir1NudgeCount(0); triggerSpacingAutoTune(); }}
                  >
                    <Ionicons name="arrow-back-outline" size={12} color={closeDir1 === 'vclose' ? '#fff' : '#888'} />
                    <Text style={{ fontSize: 9, color: closeDir1 === 'vclose' ? '#fff' : '#888', marginTop: 1 }}>V.Close</Text>
                  </TouchableOpacity>
                  <TouchableOpacity
                    style={{ flex: 1, minWidth: 60, padding: 6, borderRadius: 6, backgroundColor: closeDir1 === 'close' ? '#2196F3' : '#252525', alignItems: 'center' }}
                    onPress={() => { setCloseDir1(closeDir1 === 'close' ? false : 'close'); setFarDir1(false); setDir1NudgeCount(0); triggerSpacingAutoTune(); }}
                  >
                    <Ionicons name="arrow-back-outline" size={12} color={closeDir1 === 'close' ? '#fff' : '#888'} />
                    <Text style={{ fontSize: 9, color: closeDir1 === 'close' ? '#fff' : '#888', marginTop: 1 }}>Close</Text>
                  </TouchableOpacity>
                  <TouchableOpacity
                    style={{ flex: 1, minWidth: 60, padding: 6, borderRadius: 6, backgroundColor: (!closeDir1 && !farDir1) ? '#4CAF50' : '#252525', alignItems: 'center' }}
                    onPress={() => { setCloseDir1(false); setFarDir1(false); setDir1NudgeCount(0); triggerSpacingAutoTune(); }}
                  >
                    <Ionicons name="remove-outline" size={12} color={(!closeDir1 && !farDir1) ? '#fff' : '#888'} />
                    <Text style={{ fontSize: 9, color: (!closeDir1 && !farDir1) ? '#fff' : '#888', marginTop: 1 }}>Normal</Text>
                  </TouchableOpacity>
                  <TouchableOpacity
                    style={{ flex: 1, minWidth: 60, padding: 6, borderRadius: 6, backgroundColor: farDir1 === 'far' ? '#FF9800' : '#252525', alignItems: 'center' }}
                    onPress={() => { setFarDir1(farDir1 === 'far' ? false : 'far'); setCloseDir1(false); setDir1NudgeCount(0); triggerSpacingAutoTune(); }}
                  >
                    <Ionicons name="arrow-forward-outline" size={12} color={farDir1 === 'far' ? '#fff' : '#888'} />
                    <Text style={{ fontSize: 9, color: farDir1 === 'far' ? '#fff' : '#888', marginTop: 1 }}>Far</Text>
                  </TouchableOpacity>
                  <TouchableOpacity
                    style={{ flex: 1, minWidth: 60, padding: 6, borderRadius: 6, backgroundColor: farDir1 === 'vfar' ? '#f44336' : '#252525', alignItems: 'center' }}
                    onPress={() => { setFarDir1(farDir1 === 'vfar' ? false : 'vfar'); setCloseDir1(false); setDir1NudgeCount(0); triggerSpacingAutoTune(); }}
                  >
                    <Ionicons name="arrow-forward-outline" size={12} color={farDir1 === 'vfar' ? '#fff' : '#888'} />
                    <Text style={{ fontSize: 9, color: farDir1 === 'vfar' ? '#fff' : '#888', marginTop: 1 }}>V.Far</Text>
                  </TouchableOpacity>
                </View>
                <View style={{ flexDirection: 'row', marginTop: 6, alignItems: 'center', justifyContent: 'center', gap: 8 }}>
                  {inputs.elements.some(e => e.element_type === 'director') ? (<>
                  <TouchableOpacity
                    onPress={() => nudgeElement('dir1', -1)}
                    style={{ flexDirection: 'row', alignItems: 'center', paddingHorizontal: 14, paddingVertical: 8, borderRadius: 6, backgroundColor: '#252525', borderWidth: 1, borderColor: dir1NudgeCount <= -90 ? '#333' : '#2196F3', opacity: dir1NudgeCount <= -90 ? 0.4 : 1 }}
                    disabled={dir1NudgeCount <= -90}
                  >
                    <Ionicons name="chevron-back" size={18} color="#2196F3" />
                    <Text style={{ fontSize: 12, color: '#2196F3', fontWeight: '700', marginLeft: 2 }}>Closer</Text>
                  </TouchableOpacity>
                  <View style={{ backgroundColor: '#333', borderRadius: 6, paddingHorizontal: 10, paddingVertical: 6, minWidth: 50, alignItems: 'center' }}>
                    <Text style={{ fontSize: 11, color: dir1NudgeCount === 0 ? '#666' : '#2196F3', fontWeight: '700' }}>
                      {dir1NudgeCount === 0 ? '0%' : `${(dir1NudgeCount * 0.5) > 0 ? '+' : ''}${(dir1NudgeCount * 0.5).toFixed(1)}%`}
                    </Text>
                  </View>
                  <TouchableOpacity
                    onPress={() => nudgeElement('dir1', 1)}
                    style={{ flexDirection: 'row', alignItems: 'center', paddingHorizontal: 14, paddingVertical: 8, borderRadius: 6, backgroundColor: '#252525', borderWidth: 1, borderColor: dir1NudgeCount >= 90 ? '#333' : '#2196F3', opacity: dir1NudgeCount >= 90 ? 0.4 : 1 }}
                    disabled={dir1NudgeCount >= 90}
                  >
                    <Text style={{ fontSize: 12, color: '#2196F3', fontWeight: '700', marginRight: 2 }}>Farther</Text>
                    <Ionicons name="chevron-forward" size={18} color="#2196F3" />
                  </TouchableOpacity>
                  </>) : (
                    <Text style={{ fontSize: 10, color: '#555', fontStyle: 'italic' }}>Add 3+ elements for director nudge</Text>
                  )}
                </View>
              </View>

              {/* 2nd Director Spacing */}
              <View style={{ marginTop: 10 }}>
                <Text style={{ fontSize: 11, color: '#888', marginBottom: 6 }}>2nd Director Spacing</Text>
                <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 4 }}>
                  <TouchableOpacity style={{ flex: 1, minWidth: 60, padding: 6, borderRadius: 6, backgroundColor: closeDir2 === 'vclose' ? '#9C27B0' : '#252525', alignItems: 'center' }} onPress={() => { setCloseDir2(closeDir2 === 'vclose' ? false : 'vclose'); setFarDir2(false); setDir2NudgeCount(0); triggerSpacingAutoTune(); }}>
                    <Ionicons name="arrow-back-outline" size={12} color={closeDir2 === 'vclose' ? '#fff' : '#888'} />
                    <Text style={{ fontSize: 9, color: closeDir2 === 'vclose' ? '#fff' : '#888', marginTop: 1 }}>V.Close</Text>
                  </TouchableOpacity>
                  <TouchableOpacity style={{ flex: 1, minWidth: 60, padding: 6, borderRadius: 6, backgroundColor: closeDir2 === 'close' ? '#2196F3' : '#252525', alignItems: 'center' }} onPress={() => { setCloseDir2(closeDir2 === 'close' ? false : 'close'); setFarDir2(false); setDir2NudgeCount(0); triggerSpacingAutoTune(); }}>
                    <Ionicons name="arrow-back-outline" size={12} color={closeDir2 === 'close' ? '#fff' : '#888'} />
                    <Text style={{ fontSize: 9, color: closeDir2 === 'close' ? '#fff' : '#888', marginTop: 1 }}>Close</Text>
                  </TouchableOpacity>
                  <TouchableOpacity style={{ flex: 1, minWidth: 60, padding: 6, borderRadius: 6, backgroundColor: (!closeDir2 && !farDir2) ? '#4CAF50' : '#252525', alignItems: 'center' }} onPress={() => { setCloseDir2(false); setFarDir2(false); setDir2NudgeCount(0); triggerSpacingAutoTune(); }}>
                    <Ionicons name="remove-outline" size={12} color={(!closeDir2 && !farDir2) ? '#fff' : '#888'} />
                    <Text style={{ fontSize: 9, color: (!closeDir2 && !farDir2) ? '#fff' : '#888', marginTop: 1 }}>Normal</Text>
                  </TouchableOpacity>
                  <TouchableOpacity style={{ flex: 1, minWidth: 60, padding: 6, borderRadius: 6, backgroundColor: farDir2 === 'far' ? '#FF9800' : '#252525', alignItems: 'center' }} onPress={() => { setFarDir2(farDir2 === 'far' ? false : 'far'); setCloseDir2(false); setDir2NudgeCount(0); triggerSpacingAutoTune(); }}>
                    <Ionicons name="arrow-forward-outline" size={12} color={farDir2 === 'far' ? '#fff' : '#888'} />
                    <Text style={{ fontSize: 9, color: farDir2 === 'far' ? '#fff' : '#888', marginTop: 1 }}>Far</Text>
                  </TouchableOpacity>
                  <TouchableOpacity style={{ flex: 1, minWidth: 60, padding: 6, borderRadius: 6, backgroundColor: farDir2 === 'vfar' ? '#f44336' : '#252525', alignItems: 'center' }} onPress={() => { setFarDir2(farDir2 === 'vfar' ? false : 'vfar'); setCloseDir2(false); setDir2NudgeCount(0); triggerSpacingAutoTune(); }}>
                    <Ionicons name="arrow-forward-outline" size={12} color={farDir2 === 'vfar' ? '#fff' : '#888'} />
                    <Text style={{ fontSize: 9, color: farDir2 === 'vfar' ? '#fff' : '#888', marginTop: 1 }}>V.Far</Text>
                  </TouchableOpacity>
                </View>
                {inputs.elements.filter(e => e.element_type === 'director').length >= 2 ? (
                <View style={{ flexDirection: 'row', marginTop: 6, alignItems: 'center', justifyContent: 'center', gap: 8 }}>
                  <TouchableOpacity onPress={() => nudgeElement('dir2', -1)} style={{ flexDirection: 'row', alignItems: 'center', paddingHorizontal: 14, paddingVertical: 8, borderRadius: 6, backgroundColor: '#252525', borderWidth: 1, borderColor: dir2NudgeCount <= -90 ? '#333' : '#FF9800', opacity: dir2NudgeCount <= -90 ? 0.4 : 1 }} disabled={dir2NudgeCount <= -90}>
                    <Ionicons name="chevron-back" size={18} color="#FF9800" />
                    <Text style={{ fontSize: 12, color: '#FF9800', fontWeight: '700', marginLeft: 2 }}>Closer</Text>
                  </TouchableOpacity>
                  <View style={{ backgroundColor: '#333', borderRadius: 6, paddingHorizontal: 10, paddingVertical: 6, minWidth: 50, alignItems: 'center' }}>
                    <Text style={{ fontSize: 11, color: dir2NudgeCount === 0 ? '#666' : '#FF9800', fontWeight: '700' }}>
                      {dir2NudgeCount === 0 ? '0%' : `${(dir2NudgeCount * 0.5) > 0 ? '+' : ''}${(dir2NudgeCount * 0.5).toFixed(1)}%`}
                    </Text>
                  </View>
                  <TouchableOpacity onPress={() => nudgeElement('dir2', 1)} style={{ flexDirection: 'row', alignItems: 'center', paddingHorizontal: 14, paddingVertical: 8, borderRadius: 6, backgroundColor: '#252525', borderWidth: 1, borderColor: dir2NudgeCount >= 90 ? '#333' : '#FF9800', opacity: dir2NudgeCount >= 90 ? 0.4 : 1 }} disabled={dir2NudgeCount >= 90}>
                    <Text style={{ fontSize: 12, color: '#FF9800', fontWeight: '700', marginRight: 2 }}>Farther</Text>
                    <Ionicons name="chevron-forward" size={18} color="#FF9800" />
                  </TouchableOpacity>
                </View>
                ) : (
                  <Text style={{ fontSize: 10, color: '#555', fontStyle: 'italic', textAlign: 'center', marginTop: 4 }}>Add 4+ elements for 2nd director nudge</Text>
                )}
              </View>
            </View>
            )}
            {boomLockEnabled && (
              <View style={{ marginTop: 12, backgroundColor: '#1a1a1a', borderRadius: 8, padding: 10, borderLeftWidth: 3, borderLeftColor: '#FF9800' }}>
                <Text style={{ fontSize: 11, color: '#888' }}>
                  <Ionicons name="information-circle-outline" size={12} color="#FF9800" /> Spacing controls disabled — Boom Restraint sets the boom length and distributes elements equally.
                </Text>
              </View>
            )}

            {/* Return Loss Tune */}
            <View style={{ marginTop: 14, borderTopWidth: 1, borderTopColor: '#333', paddingTop: 12 }}>
              <TouchableOpacity
                onPress={() => { if (checkFeature('return_loss_tune', 'Return Loss Tune')) runReturnLossTune(); }}
                disabled={rlTuning}
                style={{ backgroundColor: rlTuning ? '#333' : '#00BCD4', borderRadius: 8, padding: 12, alignItems: 'center', flexDirection: 'row', justifyContent: 'center' }}
                data-testid="return-loss-tune-btn"
              >
                {rlTuning ? (
                  <ActivityIndicator size="small" color="#00BCD4" />
                ) : (
                  <Ionicons name="pulse-outline" size={16} color="#fff" />
                )}
                <Text style={{ color: '#fff', fontWeight: '700', fontSize: 13, marginLeft: 8 }}>
                  {rlTuning ? 'Sweeping Spacings...' : 'Return Loss Tune'}
                </Text>
              </TouchableOpacity>
              <Text style={{ fontSize: 9, color: '#555', marginTop: 4, textAlign: 'center' }}>
                Sweeps driven & director spacing to find highest return loss
              </Text>

              {rlResult && rlResult.best_elements && (
                <View style={{ marginTop: 10, backgroundColor: '#0d2818', borderRadius: 8, padding: 12, borderWidth: 1, borderColor: '#4CAF50' }}>
                  <Text style={{ color: '#4CAF50', fontWeight: '700', fontSize: 13, marginBottom: 6 }}>
                    Best Match Found
                  </Text>
                  <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginBottom: 8 }}>
                    <View>
                      <Text style={{ color: '#888', fontSize: 10 }}>Raw Return Loss</Text>
                      <Text style={{ color: '#00BCD4', fontSize: 18, fontWeight: '700' }}>{rlResult.best_return_loss_db} dB</Text>
                    </View>
                    <View>
                      <Text style={{ color: '#888', fontSize: 10 }}>Raw SWR</Text>
                      <Text style={{ color: '#4CAF50', fontSize: 18, fontWeight: '700' }}>{rlResult.best_swr}:1</Text>
                    </View>
                    <View>
                      <Text style={{ color: '#888', fontSize: 10 }}>Gain</Text>
                      <Text style={{ color: '#FF9800', fontSize: 18, fontWeight: '700' }}>{rlResult.best_gain}</Text>
                    </View>
                  </View>
                  {rlResult.best_elements.map((e: any, i: number) => (
                    <Text key={i} style={{ color: '#aaa', fontSize: 10 }}>
                      {e.element_type}: {e.length}" @ {e.position}"
                    </Text>
                  ))}
                  <TouchableOpacity
                    onPress={applyRlResult}
                    style={{ backgroundColor: '#4CAF50', borderRadius: 6, padding: 10, alignItems: 'center', marginTop: 10 }}
                    data-testid="apply-rl-result-btn"
                  >
                    <Text style={{ color: '#fff', fontWeight: '700', fontSize: 13 }}>Apply These Spacings</Text>
                  </TouchableOpacity>
                </View>
              )}
            </View>
            </FeatureGate>
            )}

          </View>
          <View style={[styles.section, { zIndex: 50 }]}>
            <View style={styles.sectionHeaderRow}><Text style={styles.sectionTitle}><Ionicons name="git-merge-outline" size={14} color="#E91E63" /> Tapered Elements</Text><Switch value={inputs.taper.enabled} onValueChange={v => { if (!v || checkFeature('taper', 'Tapered Elements')) setInputs(p => ({ ...p, taper: { ...p.taper, enabled: v } })); }} trackColor={{ false: '#333', true: '#E91E63' }} thumbColor="#fff" /></View>
            {inputs.taper.enabled && (
              <>
              <Text style={styles.taperHint}>Center is largest (5/8"-1.25"), each taper reduces outward to tip</Text>
              <View style={[styles.rowSpaced, { zIndex: 100 }]}>
                <View style={{ flex: 1 }}><Text style={styles.inputLabel}>Center Len" (from boom)</Text><TextInput style={styles.input} value={inputs.taper.center_length} onChangeText={v => setInputs(p => ({ ...p, taper: { ...p.taper, center_length: v } }))} keyboardType="decimal-pad" placeholder="36" placeholderTextColor="#555" /></View>
                <View style={{ flex: 1, marginLeft: 8, zIndex: 200 }}><Dropdown label="Tapers" value={inputs.taper.num_tapers.toString()} options={[1,2,3,4,5].map(n => ({ value: n.toString(), label: `${n} Taper${n > 1 ? 's' : ''}` }))} onChange={(v: string) => updateTaperCount(parseInt(v))} /></View>
              </View>
              <View style={{ zIndex: 1 }}>
              {inputs.taper.sections.map((sec, idx) => (<View key={idx} style={styles.taperSection}><Text style={styles.taperSectionTitle}>Taper {idx + 1} (outward)</Text><View style={styles.elementRow}><View style={styles.elementField}><Text style={styles.elementLabel}>Len"</Text><TextInput style={styles.elementInput} value={sec.length} onChangeText={v => updateTaperSection(idx, 'length', v)} keyboardType="decimal-pad" /></View><View style={styles.elementField}><Text style={styles.elementLabel}>StartØ"</Text><TextInput style={styles.elementInput} value={sec.start_diameter} onChangeText={v => updateTaperSection(idx, 'start_diameter', v)} keyboardType="decimal-pad" /></View><View style={styles.elementField}><Text style={styles.elementLabel}>TipØ"</Text><TextInput style={styles.elementInput} value={sec.end_diameter} onChangeText={v => updateTaperSection(idx, 'end_diameter', v)} keyboardType="decimal-pad" /></View></View></View>))}
              </View>
              </>
            )}
          </View>

          {/* Corona */}
          <View style={styles.section}>
            <View style={styles.sectionHeaderRow}><Text style={styles.sectionTitle}><Ionicons name="ellipse-outline" size={14} color="#00BCD4" /> Corona Balls</Text><Switch value={inputs.corona_balls.enabled} onValueChange={v => { if (!v || checkFeature('corona_balls', 'Corona Balls')) setInputs(p => ({ ...p, corona_balls: { ...p.corona_balls, enabled: v } })); }} trackColor={{ false: '#333', true: '#00BCD4' }} thumbColor="#fff" /></View>
            {inputs.corona_balls.enabled && <View style={{ marginTop: 8 }}><Text style={styles.inputLabel}>Diameter (in)</Text><TextInput style={styles.input} value={inputs.corona_balls.diameter} onChangeText={v => setInputs(p => ({ ...p, corona_balls: { ...p.corona_balls, diameter: v } }))} keyboardType="decimal-pad" /></View>}
          </View>

          {/* Ground Radials */}
          <View style={[styles.section, { zIndex: 2000 }]}>
            <View style={styles.sectionHeaderRow}><Text style={styles.sectionTitle}><Ionicons name="git-network-outline" size={14} color="#8BC34A" /> Ground Radials</Text><Switch value={inputs.ground_radials.enabled} onValueChange={v => { if (!v || checkFeature('ground_radials', 'Ground Radials')) setInputs(p => ({ ...p, ground_radials: { ...p.ground_radials, enabled: v } })); }} trackColor={{ false: '#333', true: '#8BC34A' }} thumbColor="#fff" /></View>
            {inputs.ground_radials.enabled && (
              <View style={{ marginTop: 8 }}>
                <View style={[styles.rowSpaced, { zIndex: 2100 }]}>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.inputLabel}>Ground Type</Text>
                    <View style={styles.groundTypeSelector}>
                      {['wet', 'average', 'dry'].map(gt => (
                        <TouchableOpacity 
                          key={gt} 
                          style={[styles.groundTypeBtn, inputs.ground_radials.ground_type === gt && styles.groundTypeBtnActive]}
                          onPress={() => setInputs(p => ({ ...p, ground_radials: { ...p.ground_radials, ground_type: gt } }))}
                        >
                          <Ionicons name={gt === 'wet' ? 'water' : gt === 'dry' ? 'sunny' : 'partly-sunny'} size={14} color={inputs.ground_radials.ground_type === gt ? '#fff' : '#888'} />
                          <Text style={[styles.groundTypeBtnText, inputs.ground_radials.ground_type === gt && styles.groundTypeBtnTextActive]}>{gt.charAt(0).toUpperCase() + gt.slice(1)}</Text>
                        </TouchableOpacity>
                      ))}
                    </View>
                  </View>
                  <View style={{ width: 100, zIndex: 2200 }}>
                    <Dropdown 
                      label="# Radials" 
                      value={inputs.ground_radials.num_radials.toString()} 
                      options={[4, 8, 16, 24, 32, 48, 64, 96, 128].map(n => ({ value: n.toString(), label: `${n}` }))} 
                      onChange={(v: string) => setInputs(p => ({ ...p, ground_radials: { ...p.ground_radials, num_radials: parseInt(v) } }))} 
                    />
                  </View>
                </View>
                <Text style={styles.groundRadialHint}>{inputs.ground_radials.num_radials} radials • ¼λ length • 0.5" dia wire</Text>
                {results?.ground_radials_info && (
                  <View style={styles.groundRadialInfo}>
                    <Text style={styles.groundRadialInfoText}>
                      Radial Length: {results.ground_radials_info.radial_length_ft}' ({results.ground_radials_info.radial_length_in}")
                    </Text>
                    <Text style={styles.groundRadialInfoText}>
                      Total Wire: {results.ground_radials_info.total_wire_length_ft}' • Conductivity: {results.ground_radials_info.ground_conductivity} S/m
                    </Text>
                    <Text style={[styles.groundRadialInfoText, { color: '#4CAF50' }]}>
                      Bonus: +{results.ground_radials_info.estimated_improvements.efficiency_bonus_percent}% efficiency
                    </Text>
                  </View>
                )}
              </View>
            )}
          </View>

          {/* Stacking */}
          <View style={[styles.section, { zIndex: 1500 }]}>
            <View style={styles.sectionHeaderRow}><Text style={styles.sectionTitle}><Ionicons name="layers-outline" size={14} color="#9C27B0" /> Stacking</Text><Switch value={inputs.stacking.enabled} onValueChange={v => { if (!v || checkFeature('stacking', 'Stacking')) setInputs(p => ({ ...p, stacking: { ...p.stacking, enabled: v } })); }} trackColor={{ false: '#333', true: '#9C27B0' }} thumbColor="#fff" /></View>
            {inputs.stacking.enabled && (
              <><View style={styles.orientationToggle}><TouchableOpacity style={[styles.orientBtn, inputs.stacking.layout === 'line' && inputs.stacking.orientation === 'vertical' && styles.orientBtnActive]} onPress={() => setInputs(p => ({ ...p, stacking: { ...p.stacking, layout: 'line', orientation: 'vertical' } }))}><Ionicons name="swap-vertical" size={16} color={inputs.stacking.layout === 'line' && inputs.stacking.orientation === 'vertical' ? '#fff' : '#888'} /><Text style={[styles.orientBtnText, inputs.stacking.layout === 'line' && inputs.stacking.orientation === 'vertical' && styles.orientBtnTextActive]}>V</Text></TouchableOpacity><TouchableOpacity style={[styles.orientBtn, inputs.stacking.layout === 'line' && inputs.stacking.orientation === 'horizontal' && styles.orientBtnActive]} onPress={() => setInputs(p => ({ ...p, stacking: { ...p.stacking, layout: 'line', orientation: 'horizontal' } }))}><Ionicons name="swap-horizontal" size={16} color={inputs.stacking.layout === 'line' && inputs.stacking.orientation === 'horizontal' ? '#fff' : '#888'} /><Text style={[styles.orientBtnText, inputs.stacking.layout === 'line' && inputs.stacking.orientation === 'horizontal' && styles.orientBtnTextActive]}>H</Text></TouchableOpacity><TouchableOpacity style={[styles.orientBtn, inputs.stacking.layout === 'quad' && styles.orientBtnActive, inputs.stacking.layout === 'quad' && { borderColor: '#E91E63' }]} onPress={() => setInputs(p => ({ ...p, stacking: { ...p.stacking, layout: 'quad', num_antennas: 4 } }))}><Ionicons name="grid" size={16} color={inputs.stacking.layout === 'quad' ? '#E91E63' : '#888'} /><Text style={[styles.orientBtnText, inputs.stacking.layout === 'quad' && { color: '#E91E63', fontWeight: '700' }]}>2x2</Text></TouchableOpacity></View>
              {inputs.stacking.layout !== 'quad' && (
                <View>
                <View style={[styles.rowSpaced, { zIndex: 1500 }]}><View style={{ flex: 1, zIndex: 1500 }}><Dropdown value={inputs.stacking.num_antennas.toString()} options={[2,3,4].map(n => ({ value: n.toString(), label: `${n}x` }))} onChange={(v: string) => setInputs(p => ({ ...p, stacking: { ...p.stacking, num_antennas: parseInt(v) } }))} /></View><View style={{ flex: 1, marginLeft: 8 }}><Text style={styles.inputLabel}>Spacing (center-to-center)</Text><TextInput style={styles.input} value={inputs.stacking.spacing} onChangeText={v => setInputs(p => ({ ...p, stacking: { ...p.stacking, spacing: v } }))} keyboardType="decimal-pad" /></View><View style={styles.unitToggle}><TouchableOpacity style={[styles.unitBtn, inputs.stacking.spacing_unit === 'ft' && styles.unitBtnActive]} onPress={() => setInputs(p => ({ ...p, stacking: { ...p.stacking, spacing_unit: 'ft' } }))}><Text style={[styles.unitBtnText, inputs.stacking.spacing_unit === 'ft' && styles.unitBtnTextActive]}>ft</Text></TouchableOpacity><TouchableOpacity style={[styles.unitBtn, inputs.stacking.spacing_unit === 'inches' && styles.unitBtnActive]} onPress={() => setInputs(p => ({ ...p, stacking: { ...p.stacking, spacing_unit: 'inches' } }))}><Text style={[styles.unitBtnText, inputs.stacking.spacing_unit === 'inches' && styles.unitBtnTextActive]}>in</Text></TouchableOpacity></View></View>
                <View style={{ flexDirection: 'row', gap: 6, marginTop: 6 }}>
                  {[{ label: '½λ', mult: 0.5 }, { label: '¾λ', mult: 0.75 }, { label: '1λ', mult: 1.0 }].map(opt => {
                    const freqMhz = parseFloat(inputs.frequency_mhz) || 27.185;
                    const wlFt = (984 / freqMhz) * opt.mult;
                    const wlFtStr = wlFt.toFixed(1);
                    const step = (984 / freqMhz) * 0.25;
                    const currentSpacing = parseFloat(inputs.stacking.spacing) || 0;
                    const isActive = Math.abs(currentSpacing - wlFt) < 0.5;
                    return (
                      <View key={opt.label} style={{ flex: 1, alignItems: 'center' }}>
                        <TouchableOpacity onPress={() => setInputs(p => ({ ...p, stacking: { ...p.stacking, spacing: wlFtStr, spacing_unit: 'ft' } }))}
                          style={{ width: '100%', paddingVertical: 6, borderRadius: 6, borderWidth: 1, borderColor: isActive ? '#9C27B0' : '#333', backgroundColor: isActive ? 'rgba(156,39,176,0.15)' : '#1a1a1a', alignItems: 'center' }}>
                          <Text style={{ fontSize: 11, fontWeight: '700', color: isActive ? '#CE93D8' : '#888' }}>{opt.label}</Text>
                          <Text style={{ fontSize: 8, color: isActive ? '#CE93D8' : '#666', marginTop: 1 }}>{wlFtStr} ft</Text>
                        </TouchableOpacity>
                        <View style={{ flexDirection: 'row', marginTop: 3, gap: 8 }}>
                          <TouchableOpacity onPress={() => setInputs(p => ({ ...p, stacking: { ...p.stacking, spacing: Math.max(1, (parseFloat(p.stacking.spacing) || 0) - wlFt * 0.05).toFixed(1), spacing_unit: 'ft' } }))}
                            style={{ paddingHorizontal: 8, paddingVertical: 2, borderRadius: 4, backgroundColor: '#1a1a1a' }}>
                            <Ionicons name="arrow-back" size={12} color="#9C27B0" />
                          </TouchableOpacity>
                          <TouchableOpacity onPress={() => setInputs(p => ({ ...p, stacking: { ...p.stacking, spacing: ((parseFloat(p.stacking.spacing) || 0) + wlFt * 0.05).toFixed(1), spacing_unit: 'ft' } }))}
                            style={{ paddingHorizontal: 8, paddingVertical: 2, borderRadius: 4, backgroundColor: '#1a1a1a' }}>
                            <Ionicons name="arrow-forward" size={12} color="#9C27B0" />
                          </TouchableOpacity>
                        </View>
                      </View>
                    );
                  })}
                </View>
                </View>
              )}
              {inputs.stacking.layout === 'quad' && (
                <View>
                  <Text style={{ fontSize: 10, color: '#E91E63', marginBottom: 6, fontWeight: '600' }}>Wavelength Spacing:</Text>
                  <View style={{ flexDirection: 'row', gap: 6, marginBottom: 8 }}>
                    {[{ label: '½λ', mult: 0.5 }, { label: '¾λ', mult: 0.75 }, { label: '1λ', mult: 1.0 }].map(opt => {
                      const freqMhz = parseFloat(inputs.frequency_mhz) || 27.185;
                      const wlFt = (984 / freqMhz) * opt.mult;
                      const wlFtStr = wlFt.toFixed(1);
                      const step = (984 / freqMhz) * 0.25;
                      const currentSpacing = parseFloat(inputs.stacking.spacing) || 0;
                      const isActive = Math.abs(currentSpacing - wlFt) < 0.5;
                      return (
                        <View key={opt.label} style={{ flex: 1, alignItems: 'center' }}>
                          <TouchableOpacity onPress={() => setInputs(p => ({ ...p, stacking: { ...p.stacking, spacing: wlFtStr, spacing_unit: 'ft', h_spacing: wlFtStr, h_spacing_unit: 'ft' } }))}
                            style={{ width: '100%', paddingVertical: 8, borderRadius: 6, borderWidth: 1, borderColor: isActive ? '#E91E63' : '#333', backgroundColor: isActive ? 'rgba(233,30,99,0.15)' : '#1a1a1a', alignItems: 'center' }}>
                            <Text style={{ fontSize: 12, fontWeight: '700', color: isActive ? '#E91E63' : '#888' }}>{opt.label}</Text>
                            <Text style={{ fontSize: 9, color: isActive ? '#E91E63' : '#666', marginTop: 2 }}>{wlFtStr} ft</Text>
                          </TouchableOpacity>
                          <View style={{ flexDirection: 'row', marginTop: 3, gap: 8 }}>
                            <TouchableOpacity onPress={() => setInputs(p => { const v = Math.max(1, (parseFloat(p.stacking.spacing) || 0) - wlFt * 0.05).toFixed(1); return { ...p, stacking: { ...p.stacking, spacing: v, spacing_unit: 'ft', h_spacing: v, h_spacing_unit: 'ft' } }; })}
                              style={{ paddingHorizontal: 8, paddingVertical: 2, borderRadius: 4, backgroundColor: '#1a1a1a' }}>
                              <Ionicons name="arrow-back" size={12} color="#E91E63" />
                            </TouchableOpacity>
                            <TouchableOpacity onPress={() => setInputs(p => { const v = ((parseFloat(p.stacking.spacing) || 0) + wlFt * 0.05).toFixed(1); return { ...p, stacking: { ...p.stacking, spacing: v, spacing_unit: 'ft', h_spacing: v, h_spacing_unit: 'ft' } }; })}
                              style={{ paddingHorizontal: 8, paddingVertical: 2, borderRadius: 4, backgroundColor: '#1a1a1a' }}>
                              <Ionicons name="arrow-forward" size={12} color="#E91E63" />
                            </TouchableOpacity>
                          </View>
                        </View>
                      );
                    })}
                  </View>
                  <View style={[styles.rowSpaced, { marginBottom: 6 }]}><View style={{ flex: 1 }}><Text style={styles.inputLabel}>V Spacing (up/down)</Text><TextInput style={styles.input} value={inputs.stacking.spacing} onChangeText={v => setInputs(p => ({ ...p, stacking: { ...p.stacking, spacing: v } }))} keyboardType="decimal-pad" /></View><View style={styles.unitToggle}><TouchableOpacity style={[styles.unitBtn, inputs.stacking.spacing_unit === 'ft' && styles.unitBtnActive]} onPress={() => setInputs(p => ({ ...p, stacking: { ...p.stacking, spacing_unit: 'ft' } }))}><Text style={[styles.unitBtnText, inputs.stacking.spacing_unit === 'ft' && styles.unitBtnTextActive]}>ft</Text></TouchableOpacity><TouchableOpacity style={[styles.unitBtn, inputs.stacking.spacing_unit === 'inches' && styles.unitBtnActive]} onPress={() => setInputs(p => ({ ...p, stacking: { ...p.stacking, spacing_unit: 'inches' } }))}><Text style={[styles.unitBtnText, inputs.stacking.spacing_unit === 'inches' && styles.unitBtnTextActive]}>in</Text></TouchableOpacity></View></View>
                  <View style={[styles.rowSpaced]}><View style={{ flex: 1 }}><Text style={styles.inputLabel}>H Spacing (side-by-side)</Text><TextInput style={styles.input} value={inputs.stacking.h_spacing} onChangeText={v => setInputs(p => ({ ...p, stacking: { ...p.stacking, h_spacing: v } }))} keyboardType="decimal-pad" /></View><View style={styles.unitToggle}><TouchableOpacity style={[styles.unitBtn, inputs.stacking.h_spacing_unit === 'ft' && styles.unitBtnActive]} onPress={() => setInputs(p => ({ ...p, stacking: { ...p.stacking, h_spacing_unit: 'ft' } }))}><Text style={[styles.unitBtnText, inputs.stacking.h_spacing_unit === 'ft' && styles.unitBtnTextActive]}>ft</Text></TouchableOpacity><TouchableOpacity style={[styles.unitBtn, inputs.stacking.h_spacing_unit === 'inches' && styles.unitBtnActive]} onPress={() => setInputs(p => ({ ...p, stacking: { ...p.stacking, h_spacing_unit: 'inches' } }))}><Text style={[styles.unitBtnText, inputs.stacking.h_spacing_unit === 'inches' && styles.unitBtnTextActive]}>in</Text></TouchableOpacity></View></View>
                  <Text style={{ fontSize: 9, color: '#E91E63', marginTop: 4 }}>2x2 Quad: 4 identical antennas in H-frame (2V x 2H). Narrows both beamwidths.</Text>
                </View>
              )}
              <Text style={{ fontSize: 9, color: '#666', marginTop: 4 }}>Boom center to boom center. Min recommended: 0.5λ of lowest frequency.</Text>
              {inputs.stacking.layout === 'line' && inputs.stacking.orientation === 'vertical' && (
                <Text style={{ fontSize: 9, color: '#4CAF50', marginTop: 4, fontStyle: 'italic' }}>Collinear: Keep antennas on same vertical axis, element-to-element. Do NOT stagger or offset.</Text>
              )}</>            )}
          </View>

          {/* Results */}
          {results && (
            <View style={styles.resultsSection}>
              <Text style={styles.sectionTitle}><Ionicons name="analytics" size={14} color="#4CAF50" /> Results</Text>
              
              {/* Bonuses */}
              {results.taper_info && <View style={styles.bonusCard}><Text style={styles.bonusText}><Ionicons name="git-merge" size={12} color="#E91E63" /> Taper: +{results.taper_info.gain_bonus}dB, +{results.taper_info.bandwidth_improvement} BW</Text></View>}
              {results.corona_info && <View style={styles.bonusCard}><Text style={styles.bonusText}><Ionicons name="ellipse" size={12} color="#00BCD4" /> Corona: {results.corona_info.corona_reduction}% reduction</Text></View>}
              {results.stacking_enabled && results.stacking_info && <View style={styles.bonusCard}><Text style={styles.bonusText}><Ionicons name="layers" size={12} color="#9C27B0" /> {results.stacking_info.layout === 'quad' ? '2x2 Quad' : 'Stacked'}: +{results.stacking_info.gain_increase_db}dB ({results.gain_dbi}→{results.stacked_gain_dbi})</Text></View>}
              {results.ground_radials_info && <View style={styles.bonusCard}><Text style={styles.bonusText}><Ionicons name="git-network" size={12} color="#8BC34A" /> Ground Radials ({results.ground_radials_info.ground_type}): +{results.ground_radials_info.estimated_improvements.efficiency_bonus_percent}% eff</Text></View>}
              {results.matching_info && results.feed_type !== 'direct' && <View style={styles.bonusCard}><Text style={styles.bonusText}><Ionicons name="git-merge" size={12} color="#2196F3" /> {results.matching_info.type}: SWR {results.matching_info.original_swr}→{results.matching_info.matched_swr} {results.matching_info.bandwidth_effect}{results.matching_info.tuning_quality != null ? ` | Tune: ${Math.round(results.matching_info.tuning_quality * 100)}%` : ''}</Text></View>}
              {results.boom_correction_info?.enabled && <View style={[styles.bonusCard, { borderLeftWidth: 2, borderLeftColor: '#FF9800' }]}><Text style={styles.bonusText}><Ionicons name="flash" size={12} color="#FF9800" /> {results.boom_correction_info.boom_mount === 'bonded' ? 'Bonded' : 'Insulated'}: {results.boom_correction_info.gain_adj_db}dB gain, {results.boom_correction_info.fb_adj_db}dB F/B | Shorten elements by {results.boom_correction_info.correction_total_in}" each</Text></View>}
              {results.dual_polarity_info && <View style={[styles.bonusCard, { borderLeftWidth: 2, borderLeftColor: '#FF9800' }]}><Text style={styles.bonusText}><Ionicons name="swap-horizontal" size={12} color="#FF9800" /> Dual Pol: {results.dual_polarity_info.description} | +{results.dual_polarity_info.coupling_bonus_db}dB coupling | +{results.dual_polarity_info.fb_bonus_db}dB F/B</Text></View>}
              
              <SwrMeter data={results.swr_curve} centerFreq={results.center_frequency} resonantFreq={results.resonant_freq_mhz} usable15={results.usable_bandwidth_1_5} usable20={results.usable_bandwidth_2_0} channelSpacing={results.band_info?.channel_spacing_khz} />
              
              <View style={styles.mainResults}>
                <View style={styles.mainResultItem}>
                  <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4 }}>
                    <Text style={styles.mainResultLabel}>Gain</Text>
                    <TouchableOpacity
                      onPress={() => setGainMode(gainMode === 'realworld' ? 'freespace' : 'realworld')}
                      style={{ backgroundColor: gainMode === 'freespace' ? '#1a3a5c' : '#1f3d1f', borderRadius: 4, paddingHorizontal: 5, paddingVertical: 2 }}
                    >
                      <Text style={{ fontSize: 8, color: gainMode === 'freespace' ? '#64B5F6' : '#81C784', fontWeight: '600' }}>
                        {gainMode === 'freespace' ? 'Free Space' : 'Real World'}
                      </Text>
                    </TouchableOpacity>
                  </View>
                  <Text style={[styles.mainResultValue, { color: gainMode === 'freespace' ? '#64B5F6' : '#4CAF50' }]}>
                    {gainMode === 'freespace' && results.gain_breakdown
                      ? (results.gain_dbi - (results.gain_breakdown.height_bonus || 0)).toFixed(1)
                      : (results.stacking_enabled ? results.stacked_gain_dbi : results.gain_dbi)} dBi
                  </Text>
                </View>
                <View style={styles.mainResultItem}><Text style={styles.mainResultLabel}>SWR</Text><Text style={[styles.mainResultValue, { color: results.swr <= 1.5 ? '#4CAF50' : results.swr <= 2.0 ? '#FFC107' : '#f44336' }]}>{Number(results.swr).toFixed(3)}:1</Text></View>
                <View style={styles.mainResultItem}><Text style={styles.mainResultLabel}>F/B</Text><Text style={styles.mainResultValue}>{results.fb_ratio}dB</Text></View>
                <View style={styles.mainResultItem}><Text style={styles.mainResultLabel}>F/S</Text><Text style={styles.mainResultValue}>{results.fs_ratio}dB</Text></View>
              </View>

              {results.matching_info && results.feed_type !== 'direct' && (results.matching_info.resonant_freq_mhz || results.matching_info.element_resonant_freq_mhz) && (
                <View style={{ backgroundColor: '#1a1a1a', borderRadius: 8, padding: 10, marginBottom: 6, borderLeftWidth: 3, borderLeftColor: '#FF9800' }}>
                  <Text style={{ fontSize: 12, fontWeight: '600', color: '#FF9800', marginBottom: 6 }}>Resonant Frequency</Text>
                  <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
                    {results.matching_info.element_resonant_freq_mhz && (
                      <View style={{ flex: 1 }}>
                        <Text style={{ fontSize: 9, color: '#888' }}>Element Resonance</Text>
                        <Text style={{ fontSize: 15, color: '#FF9800', fontWeight: '700' }}>{results.matching_info.element_resonant_freq_mhz} MHz</Text>
                      </View>
                    )}
                    {results.resonant_freq_mhz && (
                      <View style={{ flex: 1, alignItems: 'center' }}>
                        <Text style={{ fontSize: 9, color: '#888' }}>{results.feed_type === 'gamma' ? 'Gamma Tuned' : 'Match Tuned'}</Text>
                        <Text style={{ fontSize: 15, color: '#4CAF50', fontWeight: '700' }}>{results.resonant_freq_mhz} MHz</Text>
                      </View>
                    )}
                    {results.matching_info.q_factor && (
                      <View style={{ flex: 1, alignItems: 'flex-end' }}>
                        <Text style={{ fontSize: 9, color: '#888' }}>Q / BW</Text>
                        <Text style={{ fontSize: 15, color: '#2196F3', fontWeight: '700' }}>Q{results.matching_info.q_factor} / {results.matching_info.gamma_bandwidth_mhz}MHz</Text>
                      </View>
                    )}
                  </View>
                </View>
              )}
              
              {/* Gain Breakdown Card */}
              {results.base_gain_dbi != null && results.gain_breakdown && (
                <View style={{ backgroundColor: '#1a1a1a', borderRadius: 8, padding: 10, marginBottom: 6, borderLeftWidth: 3, borderLeftColor: gainMode === 'freespace' ? '#64B5F6' : '#4CAF50' }}>
                  <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                    <Text style={{ fontSize: 12, fontWeight: '600', color: gainMode === 'freespace' ? '#64B5F6' : '#4CAF50' }}>
                      <Ionicons name="trending-up" size={12} color={gainMode === 'freespace' ? '#64B5F6' : '#4CAF50'} /> {gainMode === 'freespace' ? 'Free Space' : 'Real World'} Gain
                    </Text>
                    <TouchableOpacity
                      onPress={() => setGainMode(gainMode === 'realworld' ? 'freespace' : 'realworld')}
                      style={{ backgroundColor: gainMode === 'freespace' ? '#1a3a5c' : '#1f3d1f', borderRadius: 6, paddingHorizontal: 8, paddingVertical: 3 }}
                    >
                      <Text style={{ fontSize: 9, color: gainMode === 'freespace' ? '#64B5F6' : '#81C784', fontWeight: '600' }}>
                        {gainMode === 'freespace' ? '→ Real World' : '→ Free Space'}
                      </Text>
                    </TouchableOpacity>
                  </View>
                  <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                    <View style={{ alignItems: 'center' }}>
                      <Text style={{ fontSize: 9, color: '#888' }}>Base ({inputs.num_elements} elem)</Text>
                      <Text style={{ fontSize: 20, fontWeight: 'bold', color: '#888' }}>{results.base_gain_dbi} dBi</Text>
                    </View>
                    <Ionicons name="arrow-forward" size={18} color={gainMode === 'freespace' ? '#64B5F6' : '#4CAF50'} />
                    <View style={{ alignItems: 'center' }}>
                      <Text style={{ fontSize: 9, color: '#888' }}>{gainMode === 'freespace' ? 'Free Space' : 'Real World'}</Text>
                      <Text style={{ fontSize: 20, fontWeight: 'bold', color: gainMode === 'freespace' ? '#64B5F6' : '#4CAF50' }}>
                        {gainMode === 'freespace'
                          ? (results.gain_dbi - (results.gain_breakdown.height_bonus || 0)).toFixed(1)
                          : results.gain_dbi} dBi
                      </Text>
                    </View>
                    <View style={{ alignItems: 'center', backgroundColor: gainMode === 'freespace' ? '#1a2a3a' : '#1f3d1f', borderRadius: 8, paddingHorizontal: 10, paddingVertical: 4 }}>
                      <Text style={{ fontSize: 9, color: gainMode === 'freespace' ? '#64B5F6' : '#4CAF50' }}>Increase</Text>
                      <Text style={{ fontSize: 16, fontWeight: 'bold', color: gainMode === 'freespace' ? '#64B5F6' : '#4CAF50' }}>
                        +{gainMode === 'freespace'
                          ? (results.gain_dbi - (results.gain_breakdown.height_bonus || 0) - results.base_gain_dbi).toFixed(1)
                          : (results.gain_dbi - results.base_gain_dbi).toFixed(1)} dBi
                      </Text>
                      <Text style={{ fontSize: 9, color: gainMode === 'freespace' ? '#90CAF9' : '#81C784' }}>
                        {gainMode === 'freespace' ? 'No ground gain' : `+${(results.gain_breakdown.height_bonus || 0).toFixed(1)} ground`}
                      </Text>
                    </View>
                  </View>
                  {/* Individual bonuses */}
                  <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 4 }}>
                    {results.gain_breakdown.height_bonus > 0 && gainMode === 'realworld' && (
                      <View style={{ backgroundColor: '#252525', borderRadius: 4, paddingHorizontal: 6, paddingVertical: 3 }}>
                        <Text style={{ fontSize: 9, color: '#81C784' }}>Ground +{results.gain_breakdown.height_bonus}dB</Text>
                      </View>
                    )}
                    {results.gain_breakdown.boom_bonus > 0 && (
                      <View style={{ backgroundColor: '#252525', borderRadius: 4, paddingHorizontal: 6, paddingVertical: 3 }}>
                        <Text style={{ fontSize: 9, color: '#81C784' }}>Boom +{results.gain_breakdown.boom_bonus}dB</Text>
                      </View>
                    )}
                    {(results.gain_breakdown.spacing_adj || 0) !== 0 && (
                      <View style={{ backgroundColor: '#252525', borderRadius: 4, paddingHorizontal: 6, paddingVertical: 3 }}>
                        <Text style={{ fontSize: 9, color: (results.gain_breakdown.spacing_adj || 0) > 0 ? '#FF9800' : '#f44336' }}>
                          Spacing {(results.gain_breakdown.spacing_adj || 0) > 0 ? '+' : ''}{results.gain_breakdown.spacing_adj}dB
                        </Text>
                      </View>
                    )}
                    {results.gain_breakdown.taper_bonus > 0 && (
                      <View style={{ backgroundColor: '#252525', borderRadius: 4, paddingHorizontal: 6, paddingVertical: 3 }}>
                        <Text style={{ fontSize: 9, color: '#E91E63' }}>Taper +{results.gain_breakdown.taper_bonus}dB</Text>
                      </View>
                    )}
                    {(results.gain_breakdown.corona_adj || 0) !== 0 && (
                      <View style={{ backgroundColor: '#252525', borderRadius: 4, paddingHorizontal: 6, paddingVertical: 3 }}>
                        <Text style={{ fontSize: 9, color: '#00BCD4' }}>Corona {results.gain_breakdown.corona_adj}dB</Text>
                      </View>
                    )}
                    {(results.gain_breakdown.ground_radials_bonus || 0) > 0 && (
                      <View style={{ backgroundColor: '#252525', borderRadius: 4, paddingHorizontal: 6, paddingVertical: 3 }}>
                        <Text style={{ fontSize: 9, color: '#8BC34A' }}>Radials +{results.gain_breakdown.ground_radials_bonus}dB</Text>
                      </View>
                    )}
                    {results.gain_breakdown.reflector_adj < 0 && (
                      <View style={{ backgroundColor: '#252525', borderRadius: 4, paddingHorizontal: 6, paddingVertical: 3 }}>
                        <Text style={{ fontSize: 9, color: '#f44336' }}>No Refl {results.gain_breakdown.reflector_adj}dB</Text>
                      </View>
                    )}
                    {results.stacking_enabled && results.stacked_gain_dbi && (
                      <View style={{ backgroundColor: '#252525', borderRadius: 4, paddingHorizontal: 6, paddingVertical: 3 }}>
                        <Text style={{ fontSize: 9, color: '#9C27B0' }}>Stacked +{(results.stacked_gain_dbi - results.gain_dbi).toFixed(1)}dB</Text>
                      </View>
                    )}
                    {results.gain_breakdown?.dual_active_bonus > 0 && (
                      <View style={{ backgroundColor: '#252525', borderRadius: 4, paddingHorizontal: 6, paddingVertical: 3 }}>
                        <Text style={{ fontSize: 9, color: '#FF9800' }}>H+V Active +{results.gain_breakdown.dual_active_bonus}dB</Text>
                      </View>
                    )}
                  </View>
                </View>
              )}
              
              <View style={styles.secondaryResults}>
                <View style={styles.secondaryResultItem}><Text style={styles.secondaryLabel}>Boom Length</Text><Text style={styles.secondaryValue}>{calculateBoomLength().ft}' {calculateBoomLength().inches.toFixed(1)}"</Text></View>
                <View style={styles.secondaryResultItem}><Text style={styles.secondaryLabel}>Beamwidth</Text><Text style={styles.secondaryValue}>H:{results.beamwidth_h}° V:{results.beamwidth_v}°</Text></View>
                <View style={styles.secondaryResultItem}><Text style={styles.secondaryLabel}>Efficiency</Text><Text style={styles.secondaryValue}>{results.antenna_efficiency}%</Text></View>
                <View style={styles.secondaryResultItem}><Text style={styles.secondaryLabel}>Take-off</Text><Text style={[styles.secondaryValue, { color: (results.takeoff_angle || 0) < 25 ? '#4CAF50' : '#FF9800' }]}>{results.takeoff_angle}°</Text></View>
                <View style={styles.secondaryResultItem}><Text style={styles.secondaryLabel}>BW @1.5</Text><Text style={styles.secondaryValue}>{results.usable_bandwidth_1_5?.toFixed(2)} MHz</Text></View>
                <View style={styles.secondaryResultItem}><Text style={styles.secondaryLabel}>Mult</Text><Text style={styles.secondaryValue}>{results.multiplication_factor}x</Text></View>
              </View>
              
              {/* Take-off Angle Detail Card */}
              <View style={styles.takeoffCard}>
                <View style={styles.takeoffHeader}>
                  <Ionicons name="arrow-up-outline" size={16} color="#FF5722" />
                  <Text style={styles.takeoffTitle}>Take-off Angle</Text>
                </View>
                <View style={styles.takeoffContent}>
                  <Text style={styles.takeoffValue}>{results.takeoff_angle}°</Text>
                  <Text style={styles.takeoffDesc}>{results.takeoff_angle_description}</Text>
                </View>
                {results.height_performance && (
                  <Text style={{ fontSize: 10, color: '#aaa', marginBottom: 6, paddingHorizontal: 4 }}>{results.height_performance}</Text>
                )}
                <View style={styles.takeoffBar}>
                  <View style={[styles.takeoffBarFill, { width: `${Math.min((90 - (results.takeoff_angle || 45)) / 85 * 100, 100)}%` }]} />
                </View>
                <View style={styles.takeoffScale}>
                  <Text style={styles.takeoffScaleText}>5° DX</Text>
                  <Text style={styles.takeoffScaleText}>45° Regional</Text>
                  <Text style={styles.takeoffScaleText}>90° NVIS</Text>
                </View>
              </View>
              
              {/* Noise Level Indicator */}
              {results.noise_level && (
                <View style={{ backgroundColor: '#1a1a1a', borderRadius: 8, padding: 10, marginBottom: 6, borderLeftWidth: 3, borderLeftColor: results.noise_level === 'Low' ? '#4CAF50' : '#FF9800' }}>
                  <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                    <Ionicons name={results.noise_level === 'Low' ? 'volume-low' : 'volume-high'} size={14} color={results.noise_level === 'Low' ? '#4CAF50' : '#FF9800'} />
                    <Text style={{ fontSize: 12, fontWeight: '600', color: results.noise_level === 'Low' ? '#4CAF50' : '#FF9800' }}>Noise Floor: {results.noise_level}</Text>
                  </View>
                  <Text style={{ fontSize: 10, color: '#888' }}>{results.noise_description}</Text>
                </View>
              )}
              
              <FeatureGate feature="polar_pattern" label="Polar Pattern">
              <PolarPattern data={results.far_field_pattern} stackedData={results.stacked_pattern} isStacked={results.stacking_enabled} />
              </FeatureGate>
              
              {/* Side View / Elevation Pattern */}
              {results.takeoff_angle && (
                <FeatureGate feature="elevation_pattern" label="Elevation Pattern">
                <ElevationPattern takeoffAngle={results.takeoff_angle} gain={results.gain_dbi} orientation={inputs.antenna_orientation} elevationData={results.elevation_pattern} fbRatio={results.fb_ratio} />
                </FeatureGate>
              )}
              
              {/* Smith Chart */}
              {results.smith_chart_data && results.smith_chart_data.length > 0 && (
                <FeatureGate feature="smith_chart" label="Smith Chart">
                <SmithChart data={results.smith_chart_data} centerFreq={results.center_frequency} />
                </FeatureGate>
              )}
              
              {/* Pattern Data Table */}
              <View style={styles.patternDataSection}>
                <Text style={styles.patternDataTitle}><Ionicons name="analytics-outline" size={14} color="#4CAF50" /> Pattern Analysis</Text>
                <View style={styles.patternDataGrid}>
                  <View style={styles.patternDataRow}>
                    <View style={styles.patternDataCell}><Text style={styles.patternAngle}>0° (Fwd)</Text><Text style={styles.patternValue}>{results.far_field_pattern?.[0]?.magnitude || 0}%</Text></View>
                    <View style={styles.patternDataCell}><Text style={styles.patternAngle}>45°</Text><Text style={styles.patternValue}>{results.far_field_pattern?.[9]?.magnitude || 0}%</Text></View>
                    <View style={styles.patternDataCell}><Text style={styles.patternAngle}>90°</Text><Text style={styles.patternValue}>{results.far_field_pattern?.[18]?.magnitude || 0}%</Text></View>
                    <View style={styles.patternDataCell}><Text style={styles.patternAngle}>135°</Text><Text style={styles.patternValue}>{results.far_field_pattern?.[27]?.magnitude || 0}%</Text></View>
                  </View>
                  <View style={styles.patternDataRow}>
                    <View style={styles.patternDataCell}><Text style={styles.patternAngle}>180° (Back)</Text><Text style={[styles.patternValue, { color: '#f44336' }]}>{results.far_field_pattern?.[36]?.magnitude || 0}%</Text></View>
                    <View style={styles.patternDataCell}><Text style={styles.patternAngle}>225°</Text><Text style={styles.patternValue}>{results.far_field_pattern?.[45]?.magnitude || 0}%</Text></View>
                    <View style={styles.patternDataCell}><Text style={styles.patternAngle}>270°</Text><Text style={styles.patternValue}>{results.far_field_pattern?.[54]?.magnitude || 0}%</Text></View>
                    <View style={styles.patternDataCell}><Text style={styles.patternAngle}>315°</Text><Text style={styles.patternValue}>{results.far_field_pattern?.[63]?.magnitude || 0}%</Text></View>
                  </View>
                </View>
                
                {/* -3dB Beamwidth indicator */}
                <View style={styles.beamwidthIndicator}>
                  <View style={styles.beamwidthItem}>
                    <Ionicons name="swap-horizontal" size={14} color="#2196F3" />
                    <Text style={styles.beamwidthLabel}>-3dB H-Plane</Text>
                    <Text style={styles.beamwidthValue}>{results.beamwidth_h}°</Text>
                  </View>
                  <View style={styles.beamwidthItem}>
                    <Ionicons name="swap-vertical" size={14} color="#9C27B0" />
                    <Text style={styles.beamwidthLabel}>-3dB V-Plane</Text>
                    <Text style={styles.beamwidthValue}>{results.beamwidth_v}°</Text>
                  </View>
                  <View style={styles.beamwidthItem}>
                    <Ionicons name="radio" size={14} color="#4CAF50" />
                  </View>
                </View>
              </View>
              
              {/* Gain & F/B Performance Card */}
              <View style={styles.performanceCard}>
                <Text style={styles.performanceTitle}><Ionicons name="bar-chart-outline" size={14} color="#FF9800" /> Performance Metrics</Text>
                <View style={styles.performanceGrid}>
                  {(() => {
                    const gainVal = gainMode === 'freespace' && results.gain_breakdown ? results.gain_dbi - (results.gain_breakdown.height_bonus || 0) : (results.stacking_enabled ? results.stacked_gain_dbi : results.gain_dbi);
                    const fbVal = results.fb_ratio;
                    const fsVal = results.fs_ratio;
                    const effVal = results.antenna_efficiency;
                    // Each metric has a base max, auto-grows by 15% if value gets close
                    let gainScale = 15;
                    while (gainVal / gainScale > 0.85) { gainScale *= 1.15; }
                    let fbScale = 18;
                    while (fbVal / fbScale > 0.85) { fbScale *= 1.15; }
                    let fsScale = 8;
                    while (fsVal / fsScale > 0.85) { fsScale *= 1.15; }
                    // Efficiency: always 15% bigger than the value
                    const effScale = Math.max(100, effVal * 1.15);
                    return (
                      <>
                        <View style={styles.perfItem}>
                          <Text style={styles.perfLabel}>Gain ({gainMode === 'freespace' ? 'FS' : 'RW'})</Text>
                          <View style={styles.perfBar}>
                            <View style={[styles.perfBarFill, { width: `${Math.min(gainVal / gainScale * 100, 100)}%`, backgroundColor: gainMode === 'freespace' ? '#64B5F6' : '#4CAF50' }]} />
                          </View>
                          <Text style={styles.perfValue}>{gainVal} dBi</Text>
                        </View>
                        <View style={styles.perfItem}>
                          <Text style={styles.perfLabel}>F/B Ratio</Text>
                          <View style={styles.perfBar}>
                            <View style={[styles.perfBarFill, { width: `${Math.min(fbVal / fbScale * 100, 100)}%`, backgroundColor: '#2196F3' }]} />
                          </View>
                          <Text style={styles.perfValue}>{fbVal} dB</Text>
                        </View>
                        <View style={styles.perfItem}>
                          <Text style={styles.perfLabel}>F/S Ratio</Text>
                          <View style={styles.perfBar}>
                            <View style={[styles.perfBarFill, { width: `${Math.min(fsVal / fsScale * 100, 100)}%`, backgroundColor: '#9C27B0' }]} />
                          </View>
                          <Text style={styles.perfValue}>{fsVal} dB</Text>
                        </View>
                        <View style={styles.perfItem}>
                          <Text style={styles.perfLabel}>Efficiency</Text>
                          <View style={styles.perfBar}>
                            <View style={[styles.perfBarFill, { width: `${Math.min(effVal / effScale * 100, 100)}%`, backgroundColor: '#FF9800' }]} />
                          </View>
                          <Text style={styles.perfValue}>{effVal}%</Text>
                        </View>
                      </>
                    );
                  })()}
                </View>
                
                {/* Gain to Power Conversion */}
                <View style={styles.powerConversion}>
                  <Text style={styles.powerTitle}>Power Multiplication</Text>
                  <View style={styles.powerRow}>
                    <View style={styles.powerItem}><Text style={styles.powerLabel}>Linear</Text><Text style={styles.powerValue}>{results.multiplication_factor}x</Text></View>
                    <View style={styles.powerItem}><Text style={styles.powerLabel}>100W ERP</Text><Text style={styles.powerValue}>{(100 * results.multiplication_factor).toFixed(0)}W</Text></View>
                    <View style={styles.powerItem}><Text style={styles.powerLabel}>1kW ERP</Text><Text style={styles.powerValue}>{(results.multiplication_factor / 1000).toFixed(1)}kW</Text></View>
                  </View>
                </View>
              </View>
              
              {/* Reflected Power Card */}
              <FeatureGate feature="reflected_power" label="Reflected Power Analysis">
              <View style={styles.reflectedPowerCard}>
                <Text style={styles.reflectedPowerTitle}><Ionicons name="git-compare-outline" size={14} color="#f44336" /> Reflected Power Analysis</Text>
                
                <View style={styles.reflectedPowerGrid}>
                  <View style={styles.reflectedPowerItem}>
                    <Text style={styles.reflectedPowerLabel}>Reflection Coef (Γ)</Text>
                    <Text style={styles.reflectedPowerValue}>{results.reflection_coefficient?.toFixed(4) || '0'}</Text>
                  </View>
                  <View style={styles.reflectedPowerItem}>
                    <Text style={styles.reflectedPowerLabel}>Return Loss</Text>
                    <Text style={styles.reflectedPowerValue}>{results.return_loss_db?.toFixed(1) || '∞'} dB</Text>
                  </View>
                  <View style={styles.reflectedPowerItem}>
                    <Text style={styles.reflectedPowerLabel}>Mismatch Loss</Text>
                    <Text style={styles.reflectedPowerValue}>{results.mismatch_loss_db?.toFixed(3) || '0'} dB</Text>
                  </View>
                </View>
                
                <View style={styles.reflectedPowerTable}>
                  <View style={styles.reflectedPowerTableHeader}>
                    <Text style={styles.reflectedPowerTableHeaderText}>Input</Text>
                    <Text style={styles.reflectedPowerTableHeaderText}>At Antenna</Text>
                    <Text style={styles.reflectedPowerTableHeaderText}>Forward</Text>
                    <Text style={styles.reflectedPowerTableHeaderText}>Reflected</Text>
                  </View>
                  {results.coax_info && (
                    <View style={styles.reflectedPowerTableRow}>
                      <Text style={styles.reflectedPowerTableCell}>{results.coax_info.transmit_power_watts}W</Text>
                      <Text style={[styles.reflectedPowerTableCell, { color: '#2196F3' }]}>{results.power_at_antenna_watts?.toFixed(1)}W</Text>
                      <Text style={[styles.reflectedPowerTableCell, { color: '#4CAF50' }]}>{results.forward_power_watts?.toFixed(1)}W</Text>
                      <Text style={[styles.reflectedPowerTableCell, { color: '#f44336' }]}>{results.reflected_power_watts?.toFixed(2)}W</Text>
                    </View>
                  )}
                  <View style={styles.reflectedPowerTableRow}>
                    <Text style={styles.reflectedPowerTableCell}>100W</Text>
                    <Text style={[styles.reflectedPowerTableCell, { color: '#2196F3' }]}>-</Text>
                    <Text style={[styles.reflectedPowerTableCell, { color: '#4CAF50' }]}>{results.forward_power_100w?.toFixed(1) || '100'}W</Text>
                    <Text style={[styles.reflectedPowerTableCell, { color: '#f44336' }]}>{results.reflected_power_100w?.toFixed(2) || '0'}W</Text>
                  </View>
                  {results.coax_info && (
                    <View style={{ marginTop: 4, paddingHorizontal: 4 }}>
                      <Text style={{ fontSize: 8, color: '#666' }}>Feedline: {results.coax_info.type} {results.coax_info.length_ft}ft | Loss: {results.coax_info.total_loss_db} dB</Text>
                    </View>
                  )}
                </View>
                
                <View style={styles.impedanceRow}>
                  <Text style={styles.impedanceLabel}>Impedance Range (50Ω):</Text>
                  <Text style={styles.impedanceValue}>{results.impedance_low?.toFixed(1) || '50'}Ω - {results.impedance_high?.toFixed(1) || '50'}Ω</Text>
                </View>
              </View>
              </FeatureGate>
              {heightOptResult && heightOptResult.heights_tested && heightOptResult.heights_tested.length > 0 && (
                <View style={styles.heightPerfCard}>
                  <View style={styles.heightPerfTitleRow}>
                    <Text style={styles.heightPerfTitle}><Ionicons name="trending-up" size={14} color="#00BCD4" /> Height vs Performance ({heightOptResult.heights_tested.length} heights tested)</Text>
                    <TouchableOpacity style={styles.exportBtn} onPress={() => { if (checkFeature('csv_export', 'CSV Export')) exportHeightData(); }}>
                      <Ionicons name="download-outline" size={14} color="#fff" />
                      <Text style={styles.exportBtnText}>CSV</Text>
                    </TouchableOpacity>
                  </View>
                  
                  {/* Top 5 Best Heights */}
                  <View style={styles.top5Section}>
                    <Text style={styles.top5Title}><Ionicons name="trophy" size={12} color="#FFD700" /> Top 5 Best Heights</Text>
                    <View style={styles.top5Table}>
                      <View style={styles.top5Header}>
                        <Text style={styles.top5HeaderText}>#</Text>
                        <Text style={styles.top5HeaderText}>Height</Text>
                        <Text style={styles.top5HeaderText}>SWR</Text>
                        <Text style={styles.top5HeaderText}>Gain</Text>
                        <Text style={styles.top5HeaderText}>F/B</Text>
                        <Text style={styles.top5HeaderText}>Score</Text>
                      </View>
                      {[...heightOptResult.heights_tested]
                        .sort((a: any, b: any) => b.score - a.score)
                        .slice(0, 5)
                        .map((h: any, i: number) => (
                          <View key={i} style={[styles.top5Row, i === 0 && styles.top5RowBest]}>
                            <Text style={[styles.top5Cell, styles.top5Rank, i === 0 && styles.top5CellBest]}>
                              {i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : `${i + 1}`}
                            </Text>
                            <Text style={[styles.top5Cell, i === 0 && styles.top5CellBest]}>{h.height}'</Text>
                            <Text style={[styles.top5Cell, i === 0 && styles.top5CellBest]}>{h.swr}</Text>
                            <Text style={[styles.top5Cell, i === 0 && styles.top5CellBest]}>{h.gain}</Text>
                            <Text style={[styles.top5Cell, i === 0 && styles.top5CellBest]}>{h.fb_ratio}</Text>
                            <Text style={[styles.top5Cell, i === 0 && styles.top5CellBest]}>{h.score}</Text>
                          </View>
                        ))}
                    </View>
                  </View>
                  
                  {/* Full Height Table (scrollable) */}
                  <Text style={styles.fullTableTitle}>All Heights (scroll)</Text>
                  <ScrollView style={styles.heightPerfScrollView} nestedScrollEnabled>
                    <View style={styles.heightPerfTable}>
                      <View style={styles.heightPerfHeader}>
                        <Text style={styles.heightPerfHeaderText}>Height</Text>
                        <Text style={styles.heightPerfHeaderText}>SWR</Text>
                        <Text style={styles.heightPerfHeaderText}>Gain</Text>
                        <Text style={styles.heightPerfHeaderText}>F/B</Text>
                        <Text style={styles.heightPerfHeaderText}>Score</Text>
                      </View>
                      {heightOptResult.heights_tested.map((h: any, i: number) => (
                        <View key={i} style={[styles.heightPerfRow, h.height === heightOptResult.optimal_height && styles.heightPerfRowOptimal]}>
                          <Text style={[styles.heightPerfCell, h.height === heightOptResult.optimal_height && styles.heightPerfCellOptimal]}>{h.height}'</Text>
                          <Text style={[styles.heightPerfCell, h.height === heightOptResult.optimal_height && styles.heightPerfCellOptimal]}>{h.swr}</Text>
                          <Text style={[styles.heightPerfCell, h.height === heightOptResult.optimal_height && styles.heightPerfCellOptimal]}>{h.gain}</Text>
                          <Text style={[styles.heightPerfCell, h.height === heightOptResult.optimal_height && styles.heightPerfCellOptimal]}>{h.fb_ratio}</Text>
                          <Text style={[styles.heightPerfCell, h.height === heightOptResult.optimal_height && styles.heightPerfCellOptimal]}>{h.score}</Text>
                        </View>
                      ))}
                    </View>
                  </ScrollView>
                  <Text style={styles.heightPerfNote}>★ Optimal: {heightOptResult.optimal_height}' - SWR: {heightOptResult.optimal_swr}, Gain: {heightOptResult.optimal_gain}dBi, F/B: {heightOptResult.optimal_fb_ratio}dB</Text>
                </View>
              )}
              
              {/* View Spec Sheet Button */}
              {results && (
                <TouchableOpacity style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'center', backgroundColor: '#1a1a1a', borderRadius: 8, paddingVertical: 12, marginTop: 8, gap: 8, borderWidth: 1, borderColor: '#444' }} onPress={() => setShowSpecSheet(true)}>
                  <Ionicons name="reader-outline" size={16} color="#00BCD4" />
                  <Text style={{ fontSize: 13, color: '#00BCD4', fontWeight: '600' }}>View Spec Sheet</Text>
                </TouchableOpacity>
              )}
            </View>
          )}
        </ScrollView>
      </KeyboardAvoidingView>
      
      {/* Save Design Modal */}
      <Modal visible={showSaveModal} transparent animationType="fade" onRequestClose={() => setShowSaveModal(false)}>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Save Design</Text>
              <TouchableOpacity onPress={() => setShowSaveModal(false)}><Ionicons name="close" size={24} color="#888" /></TouchableOpacity>
            </View>
            <Text style={styles.modalLabel}>Design Name</Text>
            <TextInput 
              style={styles.modalInput} 
              value={designName} 
              onChangeText={setDesignName} 
              placeholder="My Antenna Design" 
              placeholderTextColor="#555"
              autoFocus
            />
            <View style={styles.modalInfo}>
              <Ionicons name="information-circle-outline" size={14} color="#888" />
              <Text style={styles.modalInfoText}>Saves current element configuration, band, and all settings</Text>
            </View>
            <TouchableOpacity style={styles.modalSaveBtn} onPress={saveDesign} disabled={savingDesign}>
              {savingDesign ? <ActivityIndicator size="small" color="#fff" /> : <><Ionicons name="save" size={16} color="#fff" /><Text style={styles.modalSaveBtnText}>Save Design</Text></>}
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
      
      {/* Load Design Modal */}
      <Modal visible={showLoadModal} transparent animationType="fade" onRequestClose={() => setShowLoadModal(false)}>
        <View style={styles.modalOverlay}>
          <View style={[styles.modalContent, { maxHeight: '70%' }]}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Load Design</Text>
              <TouchableOpacity onPress={() => setShowLoadModal(false)}><Ionicons name="close" size={24} color="#888" /></TouchableOpacity>
            </View>
            {savedDesigns.length === 0 ? (
              <View style={styles.emptyDesigns}>
                <Ionicons name="folder-open-outline" size={48} color="#444" />
                <Text style={styles.emptyDesignsText}>No saved designs yet</Text>
                <Text style={styles.emptyDesignsHint}>Save your first design using the save button</Text>
              </View>
            ) : (
              <FlatList
                data={savedDesigns}
                keyExtractor={item => item.id}
                renderItem={({ item }) => (
                  <View style={styles.designItem}>
                    <TouchableOpacity style={styles.designItemContent} onPress={() => loadDesign(item.id)}>
                      <View style={styles.designItemLeft}>
                        <Ionicons name="document-outline" size={20} color="#4CAF50" />
                        <View>
                          <Text style={styles.designItemName}>{item.name}</Text>
                          <Text style={styles.designItemDate}>{new Date(item.created_at).toLocaleDateString()}</Text>
                        </View>
                      </View>
                      <Ionicons name="chevron-forward" size={16} color="#888" />
                    </TouchableOpacity>
                    <TouchableOpacity style={styles.designDeleteBtn} onPress={() => deleteDesign(item.id, item.name)}>
                      <Ionicons name="trash-outline" size={18} color="#f44336" />
                    </TouchableOpacity>
                  </View>
                )}
                showsVerticalScrollIndicator={false}
              />
            )}
          </View>
        </View>
      </Modal>
      
      {/* Tutorial / Intro Modal */}
      <Modal visible={showTutorial} transparent animationType="fade" onRequestClose={() => setShowTutorial(false)}>
        <View style={styles.modalOverlay}>
          <View style={[styles.modalContent, { maxHeight: '85%', maxWidth: 400 }]}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}><Ionicons name="book-outline" size={18} color="#FF9800" /> How to Use</Text>
              <TouchableOpacity onPress={() => setShowTutorial(false)}><Ionicons name="close" size={24} color="#888" /></TouchableOpacity>
            </View>
            <ScrollView style={{ maxHeight: 500 }} showsVerticalScrollIndicator>
              {tutorialContent.split('\n').map((line: string, i: number) => {
                const trimmed = line.trim();
                if (trimmed.startsWith('# ')) return <Text key={i} style={{ fontSize: 18, fontWeight: 'bold', color: '#FF9800', marginTop: 12, marginBottom: 6 }}>{trimmed.slice(2)}</Text>;
                if (trimmed.startsWith('## ')) return <Text key={i} style={{ fontSize: 14, fontWeight: '700', color: '#4CAF50', marginTop: 14, marginBottom: 4 }}>{trimmed.slice(3)}</Text>;
                if (trimmed.startsWith('- **')) {
                  const match = trimmed.match(/- \*\*(.+?)\*\*:?\s*(.*)/);
                  if (match) return <Text key={i} style={{ fontSize: 12, color: '#ccc', marginLeft: 8, marginBottom: 3 }}><Text style={{ fontWeight: '700', color: '#fff' }}>{match[1]}</Text>: {match[2]}</Text>;
                }
                if (trimmed.startsWith('- ')) return <Text key={i} style={{ fontSize: 12, color: '#ccc', marginLeft: 8, marginBottom: 3 }}>• {trimmed.slice(2)}</Text>;
                if (trimmed === '') return <View key={i} style={{ height: 6 }} />;
                return <Text key={i} style={{ fontSize: 12, color: '#ccc', marginBottom: 3, lineHeight: 18 }}>{trimmed}</Text>;
              })}
            </ScrollView>
            <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: 12, paddingTop: 12, borderTopWidth: 1, borderTopColor: '#333' }}>
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                <Switch value={tutorialEnabled} onValueChange={toggleTutorialEnabled} trackColor={{ false: '#333', true: '#FF9800' }} thumbColor="#fff" />
                <Text style={{ fontSize: 11, color: '#888' }}>Show on login</Text>
              </View>
              <TouchableOpacity style={{ backgroundColor: '#FF9800', borderRadius: 8, paddingVertical: 8, paddingHorizontal: 16 }} onPress={() => setShowTutorial(false)}>
                <Text style={{ color: '#fff', fontWeight: '600', fontSize: 13 }}>Got it!</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

      {/* Designer Info Modal */}
      <Modal visible={showDesignerInfo} transparent animationType="fade" onRequestClose={() => setShowDesignerInfo(false)}>
        <View style={styles.modalOverlay}>
          <View style={[styles.modalContent, { maxHeight: '85%', maxWidth: 400 }]}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}><Ionicons name="person-circle-outline" size={18} color="#2196F3" /> Designer Info</Text>
              <TouchableOpacity onPress={() => setShowDesignerInfo(false)}><Ionicons name="close" size={24} color="#888" /></TouchableOpacity>
            </View>
            <ScrollView style={{ maxHeight: 500 }} showsVerticalScrollIndicator>
              {designerInfoContent.split('\n').map((line: string, i: number) => {
                const trimmed = line.trim();
                if (trimmed.startsWith('# ')) return <Text key={i} style={{ fontSize: 18, fontWeight: 'bold', color: '#2196F3', marginTop: 12, marginBottom: 6 }}>{trimmed.slice(2)}</Text>;
                if (trimmed.startsWith('## ')) return <Text key={i} style={{ fontSize: 14, fontWeight: '700', color: '#4CAF50', marginTop: 14, marginBottom: 4 }}>{trimmed.slice(3)}</Text>;
                if (trimmed.startsWith('### ')) return <Text key={i} style={{ fontSize: 13, fontWeight: '700', color: '#FF9800', marginTop: 10, marginBottom: 3 }}>{trimmed.slice(4)}</Text>;
                if (trimmed.startsWith('**') && trimmed.endsWith('**')) return <Text key={i} style={{ fontSize: 12, fontWeight: '700', color: '#fff', marginTop: 8, marginBottom: 3 }}>{trimmed.slice(2, -2)}</Text>;
                if (trimmed.startsWith('- **')) {
                  const match = trimmed.match(/- \*\*(.+?)\*\*:?\s*(.*)/);
                  if (match) return <Text key={i} style={{ fontSize: 12, color: '#ccc', marginLeft: 8, marginBottom: 3 }}><Text style={{ fontWeight: '700', color: '#fff' }}>{match[1]}</Text>: {match[2]}</Text>;
                }
                if (trimmed.startsWith('- ')) return <Text key={i} style={{ fontSize: 12, color: '#ccc', marginLeft: 8, marginBottom: 3 }}>• {trimmed.slice(2)}</Text>;
                if (trimmed === '') return <View key={i} style={{ height: 6 }} />;
                return <Text key={i} style={{ fontSize: 12, color: '#ccc', marginBottom: 3, lineHeight: 18 }}>{trimmed}</Text>;
              })}
            </ScrollView>
            <TouchableOpacity style={{ backgroundColor: '#2196F3', borderRadius: 8, paddingVertical: 10, marginTop: 12, alignItems: 'center' }} onPress={() => setShowDesignerInfo(false)}>
              <Text style={{ color: '#fff', fontWeight: '600', fontSize: 13 }}>Close</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>

      {/* Spec Sheet Modal */}
      <Modal visible={showSpecSheet} transparent animationType="slide" onRequestClose={() => setShowSpecSheet(false)}>
        <View style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.95)', paddingTop: Math.max(Constants?.statusBarHeight || 0, 48) }}>
          <View style={{ flex: 1, maxWidth: 500, alignSelf: 'center', width: '100%' }}>
            {/* Header Bar */}
            <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 16, paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: '#333' }}>
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                <Ionicons name="reader-outline" size={20} color="#00BCD4" />
                <Text style={{ fontSize: 16, fontWeight: '700', color: '#fff' }}>Antenna Spec Sheet</Text>
              </View>
              <View style={{ flexDirection: 'row', gap: 12 }}>
                <TouchableOpacity onPress={() => { if (checkFeature('csv_export', 'CSV Export')) exportAllData(); }} style={{ flexDirection: 'row', alignItems: 'center', gap: 4, backgroundColor: '#9C27B0', borderRadius: 6, paddingHorizontal: 10, paddingVertical: 6 }}>
                  <Ionicons name="download-outline" size={14} color="#fff" />
                  <Text style={{ fontSize: 11, color: '#fff', fontWeight: '600' }}>CSV</Text>
                </TouchableOpacity>
                <TouchableOpacity onPress={() => setShowSpecSheet(false)}>
                  <Ionicons name="close-circle" size={28} color="#888" />
                </TouchableOpacity>
              </View>
            </View>

            {results && (
            <ScrollView style={{ flex: 1 }} contentContainerStyle={{ padding: 16, paddingBottom: 40 }} showsVerticalScrollIndicator>
              
              {/* Title Card */}
              <View style={{ backgroundColor: '#1a1a1a', borderRadius: 12, padding: 16, marginBottom: 12, borderLeftWidth: 3, borderLeftColor: '#00BCD4' }}>
                <Text style={{ fontSize: 14, fontWeight: '700', color: '#00BCD4', marginBottom: 4 }}>
                  {inputs.num_elements}-Element {inputs.antenna_orientation === 'dual' ? 'Dual Polarity' : inputs.antenna_orientation === 'horizontal' ? 'Horizontal' : inputs.antenna_orientation === 'vertical' ? 'Vertical' : '45° Slant'} Yagi
                </Text>
                <Text style={{ fontSize: 11, color: '#888' }}>
                  {results.band_info?.name || inputs.band} | {inputs.frequency_mhz} MHz | {inputs.feed_type === 'gamma' ? 'Gamma Match' : inputs.feed_type === 'hairpin' ? 'Hairpin Match' : 'Direct Feed'}
                </Text>
                {results.dual_polarity_info && (
                  <Text style={{ fontSize: 11, color: '#FF9800', marginTop: 4 }}>{results.dual_polarity_info.description}</Text>
                )}
              </View>

              {/* Key Performance - Hero Numbers */}
              <View style={{ flexDirection: 'row', gap: 8, marginBottom: 12 }}>
                <View style={{ flex: 1, backgroundColor: '#1a1a1a', borderRadius: 10, padding: 12, alignItems: 'center' }}>
                  <Text style={{ fontSize: 22, fontWeight: '800', color: '#4CAF50' }}>{results.gain_dbi}</Text>
                  <Text style={{ fontSize: 9, color: '#888', marginTop: 2 }}>GAIN (dBi)</Text>
                </View>
                <View style={{ flex: 1, backgroundColor: '#1a1a1a', borderRadius: 10, padding: 12, alignItems: 'center' }}>
                  <Text style={{ fontSize: 22, fontWeight: '800', color: results.swr <= 1.5 ? '#4CAF50' : results.swr <= 2.0 ? '#FF9800' : '#f44336' }}>{Number(results.swr).toFixed(3)}</Text>
                  <Text style={{ fontSize: 9, color: '#888', marginTop: 2 }}>SWR</Text>
                </View>
                <View style={{ flex: 1, backgroundColor: '#1a1a1a', borderRadius: 10, padding: 12, alignItems: 'center' }}>
                  <Text style={{ fontSize: 22, fontWeight: '800', color: '#2196F3' }}>{results.fb_ratio}</Text>
                  <Text style={{ fontSize: 9, color: '#888', marginTop: 2 }}>F/B (dB)</Text>
                </View>
              </View>

              <View style={{ flexDirection: 'row', gap: 8, marginBottom: 16 }}>
                <View style={{ flex: 1, backgroundColor: '#1a1a1a', borderRadius: 10, padding: 10, alignItems: 'center' }}>
                  <Text style={{ fontSize: 16, fontWeight: '700', color: '#FF9800' }}>{results.multiplication_factor}x</Text>
                  <Text style={{ fontSize: 9, color: '#888' }}>POWER MULT</Text>
                </View>
                <View style={{ flex: 1, backgroundColor: '#1a1a1a', borderRadius: 10, padding: 10, alignItems: 'center' }}>
                  <Text style={{ fontSize: 16, fontWeight: '700', color: '#E91E63' }}>{results.antenna_efficiency}%</Text>
                  <Text style={{ fontSize: 9, color: '#888' }}>EFFICIENCY</Text>
                </View>
                <View style={{ flex: 1, backgroundColor: '#1a1a1a', borderRadius: 10, padding: 10, alignItems: 'center' }}>
                  <Text style={{ fontSize: 16, fontWeight: '700', color: '#9C27B0' }}>{results.takeoff_angle || '-'}°</Text>
                  <Text style={{ fontSize: 9, color: '#888' }}>TAKEOFF</Text>
                </View>
              </View>

              {/* Section: Configuration */}
              <SpecSection title="Configuration" icon="settings-outline" color="#00BCD4">
                <SpecRow label="Band" value={results.band_info?.name || inputs.band} />
                <SpecRow label="Center Frequency" value={`${inputs.frequency_mhz} MHz`} />
                <SpecRow label="Polarization" value={inputs.antenna_orientation === 'dual' ? 'Dual (H+V)' : inputs.antenna_orientation === 'horizontal' ? 'Horizontal' : inputs.antenna_orientation === 'vertical' ? 'Vertical' : '45° Slant'} />
                <SpecRow label="Feed System" value={inputs.feed_type === 'gamma' ? 'Gamma Match' : inputs.feed_type === 'hairpin' ? 'Hairpin Match' : 'Direct Feed'} />
                <SpecRow label="Elements" value={inputs.antenna_orientation === 'dual' ? `${inputs.num_elements} per pol (${inputs.num_elements * 2} total)` : `${inputs.num_elements}`} />
                <SpecRow label="Height" value={`${inputs.height_from_ground} ${inputs.height_unit}`} />
                <SpecRow label="Boom" value={`${inputs.boom_diameter} ${inputs.boom_unit} OD`} />
                <SpecRow label="Boom Mount" value={inputs.boom_mount === 'bonded' ? 'Bonded (Elements to Boom)' : inputs.boom_mount === 'insulated' ? 'Insulated (Sleeves)' : 'Non-Conductive Boom'} accent={inputs.boom_mount === 'bonded' ? '#FF9800' : inputs.boom_mount === 'insulated' ? '#2196F3' : '#4CAF50'} />
                <SpecRow label="Gain Mode" value={gainMode === 'realworld' ? 'Real World' : 'Free Space'} />
              </SpecSection>

              {/* Section: Element Table */}
              <SpecSection title="Element Dimensions" icon="resize-outline" color="#FF9800">
                <View style={{ backgroundColor: '#252525', borderRadius: 6, overflow: 'hidden' }}>
                  <View style={{ flexDirection: 'row', backgroundColor: '#333', paddingVertical: 6, paddingHorizontal: 8 }}>
                    <Text style={{ flex: 0.5, fontSize: 9, fontWeight: '700', color: '#888' }}>#</Text>
                    <Text style={{ flex: 1.5, fontSize: 9, fontWeight: '700', color: '#888' }}>Type</Text>
                    <Text style={{ flex: 1, fontSize: 9, fontWeight: '700', color: '#888', textAlign: 'right' }}>Length</Text>
                    <Text style={{ flex: 1, fontSize: 9, fontWeight: '700', color: '#888', textAlign: 'right' }}>Dia.</Text>
                    <Text style={{ flex: 1, fontSize: 9, fontWeight: '700', color: '#888', textAlign: 'right' }}>Pos.</Text>
                  </View>
                  {inputs.elements.map((e: any, i: number) => (
                    <View key={i} style={{ flexDirection: 'row', paddingVertical: 5, paddingHorizontal: 8, borderBottomWidth: i < inputs.elements.length - 1 ? 1 : 0, borderBottomColor: '#333' }}>
                      <Text style={{ flex: 0.5, fontSize: 11, color: '#666' }}>{i + 1}</Text>
                      <Text style={{ flex: 1.5, fontSize: 11, color: e.element_type === 'reflector' ? '#f44336' : e.element_type === 'driven' ? '#FF9800' : '#4CAF50', fontWeight: '600', textTransform: 'capitalize' }}>{e.element_type}</Text>
                      <Text style={{ flex: 1, fontSize: 11, color: '#fff', textAlign: 'right' }}>{e.length}"</Text>
                      <Text style={{ flex: 1, fontSize: 11, color: '#aaa', textAlign: 'right' }}>{e.diameter}"</Text>
                      <Text style={{ flex: 1, fontSize: 11, color: '#aaa', textAlign: 'right' }}>{e.position}"</Text>
                    </View>
                  ))}
                </View>
              </SpecSection>

              {/* Section: Signal Performance */}
              <SpecSection title="Signal" icon="pulse-outline" color="#4CAF50">
                <SpecRow label="Gain" value={`${results.gain_dbi} dBi`} accent="#4CAF50" />
                <SpecRow label="Base Free-Space Gain" value={`${results.base_gain_dbi || '-'} dBi`} />
                <SpecRow label="Multiplication Factor" value={`${results.multiplication_factor}x`} accent="#FF9800" />
                <SpecRow label="Efficiency" value={`${results.antenna_efficiency}%`} />
                {results.gain_breakdown && (
                  <View style={{ marginTop: 6, backgroundColor: '#1e1e1e', borderRadius: 6, padding: 8 }}>
                    <Text style={{ fontSize: 10, fontWeight: '700', color: '#666', marginBottom: 4 }}>GAIN BREAKDOWN</Text>
                    <SpecRow label="  Element Lookup" value={`${results.gain_breakdown.standard_gain} dBi`} small />
                    <SpecRow label="  Boom Adj." value={`${results.gain_breakdown.boom_adj >= 0 ? '+' : ''}${results.gain_breakdown.boom_adj} dB`} small />
                    {results.gain_breakdown.taper_bonus > 0 && <SpecRow label="  Taper Bonus" value={`+${results.gain_breakdown.taper_bonus} dB`} small />}
                    {results.gain_breakdown.height_bonus > 0 && <SpecRow label="  Height/Ground" value={`+${results.gain_breakdown.height_bonus} dB`} small />}
                    {results.gain_breakdown.boom_bonus > 0 && <SpecRow label="  Boom Bonus" value={`+${results.gain_breakdown.boom_bonus} dB`} small />}
                    {results.gain_breakdown.ground_type && <SpecRow label="  Ground Type" value={`${results.gain_breakdown.ground_type} (${results.gain_breakdown.ground_scale}x)`} small />}
                    {results.gain_breakdown.dual_active_bonus > 0 && <SpecRow label="  H+V Active" value={`+${results.gain_breakdown.dual_active_bonus} dB`} accent="#FF9800" small />}
                    <View style={{ borderTopWidth: 1, borderTopColor: '#333', marginTop: 4, paddingTop: 4 }}>
                      <SpecRow label="  Final" value={`${results.gain_breakdown.final_gain || results.gain_dbi} dBi`} accent="#4CAF50" small />
                    </View>
                  </View>
                )}
              </SpecSection>

              {/* Section: SWR & Impedance */}
              <SpecSection title="SWR & Impedance" icon="analytics-outline" color="#f44336">
                <SpecRow label="SWR" value={`${Number(results.swr).toFixed(3)}:1`} accent={results.swr <= 1.5 ? '#4CAF50' : results.swr <= 2.0 ? '#FF9800' : '#f44336'} />
                <SpecRow label="SWR Rating" value={results.swr_description} />
                {results.matching_info && results.feed_type !== 'direct' && (
                  <View style={{ marginTop: 4, backgroundColor: '#1e1e1e', borderRadius: 6, padding: 8 }}>
                    <Text style={{ fontSize: 10, fontWeight: '700', color: '#666', marginBottom: 4 }}>{results.matching_info.type?.toUpperCase()}</Text>
                    <SpecRow label="  Before Match" value={`${results.matching_info.original_swr}:1`} small />
                    <SpecRow label="  After Match" value={`${results.matching_info.matched_swr}:1`} accent="#4CAF50" small />
                    {results.matching_info.tuning_quality != null && <SpecRow label="  Tuning Quality" value={`${Math.round(results.matching_info.tuning_quality * 100)}%`} accent={results.matching_info.tuning_quality >= 0.9 ? '#4CAF50' : results.matching_info.tuning_quality >= 0.7 ? '#FF9800' : '#f44336'} small />}
                    <SpecRow label="  Bandwidth Effect" value={results.matching_info.bandwidth_effect} small />
                    {results.matching_info.technical_notes && (
                      <View style={{ marginTop: 6, paddingTop: 6, borderTopWidth: 1, borderTopColor: '#333' }}>
                        <Text style={{ fontSize: 9, fontWeight: '700', color: '#555', marginBottom: 3 }}>HOW IT WORKS</Text>
                        <Text style={{ fontSize: 9, color: '#aaa', lineHeight: 14, marginBottom: 3 }}>{results.matching_info.technical_notes.mechanism}</Text>
                        {results.matching_info.technical_notes.asymmetry && <Text style={{ fontSize: 9, color: '#FF9800', lineHeight: 14, marginBottom: 3 }}>{results.matching_info.technical_notes.asymmetry}</Text>}
                        {results.matching_info.technical_notes.pattern_stabilization && <Text style={{ fontSize: 9, color: '#4CAF50', lineHeight: 14, marginBottom: 3 }}>{results.matching_info.technical_notes.pattern_stabilization}</Text>}
                        {results.matching_info.technical_notes.balance && <Text style={{ fontSize: 9, color: '#2196F3', lineHeight: 14, marginBottom: 3 }}>{results.matching_info.technical_notes.balance}</Text>}
                        <Text style={{ fontSize: 9, color: '#aaa', lineHeight: 14, marginBottom: 3 }}>{results.matching_info.technical_notes.pattern_impact}</Text>
                        <Text style={{ fontSize: 9, color: '#4CAF50', lineHeight: 14, marginBottom: 3 }}>{results.matching_info.technical_notes.advantage}</Text>
                        <Text style={{ fontSize: 9, color: '#aaa', lineHeight: 14, marginBottom: 3 }}>{results.matching_info.technical_notes.tuning}</Text>
                        <Text style={{ fontSize: 9, color: '#888', fontStyle: 'italic', lineHeight: 14 }}>{results.matching_info.technical_notes.mitigation || results.matching_info.technical_notes.tradeoff}</Text>
                        {results.matching_info.technical_notes.balun_note && <Text style={{ fontSize: 9, color: '#f44336', fontWeight: '700', lineHeight: 14, marginTop: 3 }}>{results.matching_info.technical_notes.balun_note}</Text>}
                      </View>
                    )}
                  </View>
                )}
                <SpecRow label="Impedance Range" value={`${results.impedance_low || '-'} - ${results.impedance_high || '-'} \u03a9`} />
                <SpecRow label="Return Loss" value={`${results.return_loss_db || '-'} dB`} />
                <SpecRow label="Mismatch Loss" value={`${results.mismatch_loss_db || '-'} dB`} />
              </SpecSection>

              {/* Section: Radiation Pattern */}
              <SpecSection title="Radiation Pattern" icon="radio-outline" color="#2196F3">
                <SpecRow label="F/B Ratio" value={`${results.fb_ratio} dB`} accent="#2196F3" />
                <SpecRow label="F/S Ratio" value={`${results.fs_ratio} dB`} />
                <SpecRow label="Horizontal Beamwidth" value={`${results.beamwidth_h}°`} />
                <SpecRow label="Vertical Beamwidth" value={`${results.beamwidth_v}°`} />
              </SpecSection>

              {/* Section: Propagation */}
              <SpecSection title="Propagation" icon="earth-outline" color="#9C27B0">
                <SpecRow label="Take-off Angle" value={`${results.takeoff_angle || '-'}°`} accent="#9C27B0" />
                <SpecRow label="Rating" value={results.takeoff_angle_description || '-'} />
                <SpecRow label="Height Performance" value={results.height_performance || '-'} />
                <SpecRow label="Noise Level" value={`${results.noise_level || '-'}`} />
                <Text style={{ fontSize: 10, color: '#777', marginTop: 2, fontStyle: 'italic' }}>{results.noise_description}</Text>
              </SpecSection>

              {/* Section: Bandwidth */}
              <SpecSection title={results.dual_polarity_info ? "Bandwidth (per beam)" : "Bandwidth"} icon="swap-horizontal-outline" color="#FF9800">
                <SpecRow label={results.dual_polarity_info ? "Bandwidth per Beam" : "Total Bandwidth"} value={`${results.bandwidth} MHz`} accent="#FF9800" />
                <SpecRow label="Usable @ 1.5:1 SWR" value={`${results.usable_bandwidth_1_5} MHz`} />
                <SpecRow label="Usable @ 2.0:1 SWR" value={`${results.usable_bandwidth_2_0} MHz`} />
                {results.dual_polarity_info && (
                  <Text style={{ fontSize: 9, color: '#777', marginTop: 4, fontStyle: 'italic' }}>Each polarization beam has independent bandwidth. Only one beam is active at a time.</Text>
                )}
              </SpecSection>

              {/* Section: Dual Polarity (conditional) */}
              {results.dual_polarity_info && (
                <SpecSection title="Dual Polarity" icon="swap-vertical-outline" color="#FF9800">
                  <SpecRow label="Configuration" value={results.dual_polarity_info.description} />
                  <SpecRow label="Gain per Polarization" value={`${results.dual_polarity_info.gain_per_polarization_dbi} dBi`} />
                  <SpecRow label="Cross-Coupling Bonus" value={`+${results.dual_polarity_info.coupling_bonus_db} dB`} accent="#4CAF50" />
                  <SpecRow label="F/B Improvement" value={`+${results.dual_polarity_info.fb_bonus_db} dB`} accent="#2196F3" />
                </SpecSection>
              )}

              {/* Section: Stacking (conditional) */}
              {results.stacking_enabled && results.stacking_info && (
                <SpecSection title="Stacking" icon="layers-outline" color="#E91E63">
                  <SpecRow label="Antennas" value={results.stacking_info.layout === 'quad' ? `${results.stacking_info.num_antennas} in 2x2 Quad (H-Frame)` : `${results.stacking_info.num_antennas} stacked ${results.stacking_info.orientation}`} />
                  <SpecRow label="Spacing" value={`${results.stacking_info.spacing} ${results.stacking_info.spacing_unit} (${results.stacking_info.spacing_wavelengths?.toFixed(2) || '-'}\u03bb)`} />
                  <SpecRow label="Spacing Status" value={results.stacking_info.spacing_status || '-'} accent={results.stacking_info.spacing_status === 'Optimal' ? '#4CAF50' : results.stacking_info.spacing_status === 'Good' ? '#FF9800' : '#f44336'} />
                  <SpecRow label="Isolation" value={`~${results.stacking_info.isolation_db}dB`} />
                  <SpecRow label="Gain Increase" value={`+${results.stacking_info.gain_increase_db} dB`} accent="#4CAF50" />
                  <SpecRow label="Stacked Gain" value={`${results.stacked_gain_dbi} dBi`} accent="#E91E63" />
                  <SpecRow label="Optimal Spacing" value={`${results.stacking_info.optimal_spacing_ft}'`} />
                  <SpecRow label="Min Spacing" value={`${results.stacking_info.min_spacing_ft}'`} />
                  {results.stacking_info.vertical_notes && (
                    <View style={{ marginTop: 6, backgroundColor: '#1e1e1e', borderRadius: 6, padding: 8, borderLeftWidth: 2, borderLeftColor: '#4CAF50' }}>
                      <Text style={{ fontSize: 10, fontWeight: '700', color: '#4CAF50', marginBottom: 4 }}>COLLINEAR VERTICAL STACKING</Text>
                      <Text style={{ fontSize: 10, color: '#4CAF50', fontWeight: '600', marginBottom: 4 }}>{results.stacking_info.vertical_notes.alignment}</Text>
                      <Text style={{ fontSize: 10, color: '#aaa', marginBottom: 2 }}>{results.stacking_info.vertical_notes.effect}</Text>
                      <SpecRow label="  1λ Spacing" value={results.stacking_info.vertical_notes.one_wavelength_ft} small />
                      <SpecRow label="  Alignment" value={results.stacking_info.vertical_notes.alignment_status} small />
                      <SpecRow label="  Isolation" value={results.stacking_info.vertical_notes.isolation} small />
                      {results.stacking_info.vertical_notes.far_field && (
                        <View style={{ marginTop: 4, paddingTop: 4, borderTopWidth: 1, borderTopColor: '#333' }}>
                          <Text style={{ fontSize: 9, fontWeight: '700', color: '#666', marginBottom: 2 }}>FAR-FIELD PATTERN</Text>
                          <SpecRow label="  Elevation" value={results.stacking_info.vertical_notes.far_field.elevation} small />
                          <SpecRow label="  Azimuth" value={results.stacking_info.vertical_notes.far_field.azimuth} small />
                          <Text style={{ fontSize: 9, color: '#4CAF50', marginTop: 2, fontWeight: '600' }}>{results.stacking_info.vertical_notes.far_field.summary}</Text>
                        </View>
                      )}
                      <Text style={{ fontSize: 9, color: '#FF9800', marginTop: 4 }}>{results.stacking_info.vertical_notes.best_practice}</Text>
                      <Text style={{ fontSize: 9, color: '#f44336', marginTop: 2 }}>{results.stacking_info.vertical_notes.stagger_warning}</Text>
                      {results.stacking_info.vertical_notes.stagger_effects && (
                        <View style={{ marginTop: 2, paddingLeft: 6 }}>
                          <Text style={{ fontSize: 8, color: '#f44336' }}>- {results.stacking_info.vertical_notes.stagger_effects.nulls}</Text>
                          <Text style={{ fontSize: 8, color: '#f44336' }}>- {results.stacking_info.vertical_notes.stagger_effects.gain_loss}</Text>
                          <Text style={{ fontSize: 8, color: '#f44336' }}>- {results.stacking_info.vertical_notes.stagger_effects.detuning}</Text>
                          <Text style={{ fontSize: 8, color: '#f44336' }}>- {results.stacking_info.vertical_notes.stagger_effects.phasing}</Text>
                        </View>
                      )}
                      <Text style={{ fontSize: 9, color: '#aaa', marginTop: 2 }}>{results.stacking_info.vertical_notes.feed_line_note}</Text>
                      {results.stacking_info.vertical_notes.coupling_warning ? <Text style={{ fontSize: 9, color: '#f44336', fontWeight: '700', marginTop: 2 }}>{results.stacking_info.vertical_notes.coupling_warning}</Text> : null}
                    </View>
                  )}
                  {results.stacking_info.horizontal_notes && (
                    <View style={{ marginTop: 6, backgroundColor: '#1e1e1e', borderRadius: 6, padding: 8, borderLeftWidth: 2, borderLeftColor: '#2196F3' }}>
                      <Text style={{ fontSize: 10, fontWeight: '700', color: '#2196F3', marginBottom: 4 }}>HORIZONTAL STACKING</Text>
                      <Text style={{ fontSize: 10, color: '#aaa', marginBottom: 2 }}>{results.stacking_info.horizontal_notes.effect}</Text>
                      {results.stacking_info.horizontal_notes.far_field && (
                        <View style={{ marginTop: 4, paddingTop: 4, borderTopWidth: 1, borderTopColor: '#333' }}>
                          <Text style={{ fontSize: 9, fontWeight: '700', color: '#666', marginBottom: 2 }}>FAR-FIELD PATTERN</Text>
                          <SpecRow label="  Elevation" value={results.stacking_info.horizontal_notes.far_field.elevation} small />
                          <SpecRow label="  Azimuth" value={results.stacking_info.horizontal_notes.far_field.azimuth} small />
                          <Text style={{ fontSize: 9, color: '#2196F3', marginTop: 2, fontWeight: '600' }}>{results.stacking_info.horizontal_notes.far_field.summary}</Text>
                        </View>
                      )}
                      <Text style={{ fontSize: 9, color: '#FF9800', marginTop: 4 }}>{results.stacking_info.horizontal_notes.tradeoff}</Text>
                      <SpecRow label="  Isolation" value={results.stacking_info.horizontal_notes.isolation} small />
                      <Text style={{ fontSize: 9, color: '#aaa', marginTop: 2 }}>{results.stacking_info.horizontal_notes.feed_line_note}</Text>
                    </View>
                  )}
                  {results.stacking_info.dual_stacking && (
                    <View style={{ marginTop: 6, backgroundColor: '#1e1e1e', borderRadius: 6, padding: 8 }}>
                      <Text style={{ fontSize: 10, fontWeight: '700', color: '#666', marginBottom: 4 }}>DUAL-POL STACKING</Text>
                      <Text style={{ fontSize: 10, color: '#aaa', marginBottom: 2 }}>{results.stacking_info.dual_stacking.note}</Text>
                      <Text style={{ fontSize: 10, color: '#aaa', marginBottom: 2 }}>{results.stacking_info.dual_stacking.cross_pol}</Text>
                      {results.stacking_info.dual_stacking.mimo_note ? <Text style={{ fontSize: 10, color: '#2196F3', marginBottom: 2 }}>{results.stacking_info.dual_stacking.mimo_note}</Text> : null}
                      <Text style={{ fontSize: 9, color: '#777', marginTop: 2 }}>{results.stacking_info.dual_stacking.wind_load}</Text>
                    </View>
                  )}
                  {results.stacking_info.quad_notes && (
                    <View style={{ marginTop: 6, backgroundColor: '#1e1e1e', borderRadius: 6, padding: 8, borderLeftWidth: 2, borderLeftColor: '#E91E63' }}>
                      <Text style={{ fontSize: 10, fontWeight: '700', color: '#E91E63', marginBottom: 4 }}>2x2 QUAD STACK</Text>
                      <Text style={{ fontSize: 10, color: '#aaa', marginBottom: 2 }}>{results.stacking_info.quad_notes.layout}</Text>
                      <Text style={{ fontSize: 10, color: '#aaa', marginBottom: 2 }}>{results.stacking_info.quad_notes.effect}</Text>
                      <SpecRow label="  V Spacing" value={results.stacking_info.quad_notes.v_spacing} small />
                      <SpecRow label="  H Spacing" value={results.stacking_info.quad_notes.h_spacing} small />
                      <Text style={{ fontSize: 10, color: '#aaa', marginTop: 2 }}>{results.stacking_info.quad_notes.h_frame_note}</Text>
                      <SpecRow label="  Isolation" value={results.stacking_info.quad_notes.isolation} small />
                      {results.stacking_info.quad_notes.coupling_warning ? <Text style={{ fontSize: 9, color: '#f44336', marginTop: 2 }}>{results.stacking_info.quad_notes.coupling_warning}</Text> : null}
                      <Text style={{ fontSize: 9, color: '#E91E63', marginTop: 4, fontStyle: 'italic' }}>{results.stacking_info.quad_notes.identical_note}</Text>
                      <Text style={{ fontSize: 9, color: '#777', marginTop: 2 }}>{results.stacking_info.quad_notes.phasing_note}</Text>
                    </View>
                  )}
                  {results.stacking_info.phasing && (
                    <View style={{ marginTop: 6, backgroundColor: '#1e1e1e', borderRadius: 6, padding: 8 }}>
                      <Text style={{ fontSize: 10, fontWeight: '700', color: '#666', marginBottom: 4 }}>PHASING</Text>
                      <SpecRow label="  Requirement" value={results.stacking_info.phasing.requirement} small />
                      <Text style={{ fontSize: 9, color: '#777', marginTop: 2, fontStyle: 'italic' }}>{results.stacking_info.phasing.cable_note}</Text>
                    </View>
                  )}
                  {results.stacking_info.power_splitter && (
                    <View style={{ marginTop: 6, backgroundColor: '#1e1e1e', borderRadius: 6, padding: 8 }}>
                      <Text style={{ fontSize: 10, fontWeight: '700', color: '#666', marginBottom: 4 }}>POWER SPLITTER</Text>
                      <SpecRow label="  Type" value={results.stacking_info.power_splitter.type} small />
                      <SpecRow label="  Input" value={results.stacking_info.power_splitter.input_impedance} small />
                      <SpecRow label="  Combined Load" value={results.stacking_info.power_splitter.combined_load} small />
                      <SpecRow label="  Matching" value={results.stacking_info.power_splitter.matching_method} small />
                      <SpecRow label="  Quarter-Wave Line" value={`${results.stacking_info.power_splitter.quarter_wave_ft}' (${results.stacking_info.power_splitter.quarter_wave_in}")`} small />
                      <SpecRow label="  Power @ 100W" value={`${results.stacking_info.power_splitter.power_per_antenna_100w}W each`} small />
                      <SpecRow label="  Power @ 1kW" value={`${results.stacking_info.power_splitter.power_per_antenna_1kw}W each`} small />
                      <SpecRow label="  Min Rating" value={results.stacking_info.power_splitter.min_power_rating} small />
                    </View>
                  )}
                </SpecSection>
              )}

              {/* Section: Taper (conditional) */}
              {results.taper_info?.enabled && (
                <SpecSection title="Element Taper" icon="git-branch-outline" color="#00BCD4">
                  <SpecRow label="Taper Steps" value={`${results.taper_info.num_tapers}`} />
                  <SpecRow label="Gain Bonus" value={`+${results.taper_info.gain_bonus} dB`} accent="#4CAF50" />
                  <SpecRow label="Bandwidth Improvement" value={results.taper_info.bandwidth_improvement} />
                </SpecSection>
              )}

              {/* Section: Corona Balls (conditional) */}
              {results.corona_info?.enabled && (
                <SpecSection title="Corona Ball Tips" icon="ellipse-outline" color="#FF5722">
                  <SpecRow label="Diameter" value={`${results.corona_info.diameter}"`} />
                  <SpecRow label="Corona Reduction" value={`${results.corona_info.corona_reduction}%`} accent="#4CAF50" />
                  <SpecRow label="Bandwidth Effect" value={`x${results.corona_info.bandwidth_effect}`} />
                </SpecSection>
              )}

              {/* Section: Power Analysis (conditional) */}
              {results.forward_power_100w && (
                <SpecSection title="Power Analysis" icon="flash-outline" color="#f44336">
                  <View style={{ backgroundColor: '#252525', borderRadius: 6, overflow: 'hidden' }}>
                    <View style={{ flexDirection: 'row', backgroundColor: '#333', paddingVertical: 6, paddingHorizontal: 8 }}>
                      <Text style={{ flex: 1.5, fontSize: 9, fontWeight: '700', color: '#888' }}></Text>
                      <Text style={{ flex: 1, fontSize: 9, fontWeight: '700', color: '#888', textAlign: 'center' }}>@ {results.coax_info?.transmit_power_watts || 500}W</Text>
                      <Text style={{ flex: 1, fontSize: 9, fontWeight: '700', color: '#888', textAlign: 'center' }}>@ 100W</Text>
                    </View>
                    <View style={{ flexDirection: 'row', paddingVertical: 6, paddingHorizontal: 8, borderBottomWidth: 1, borderBottomColor: '#333' }}>
                      <Text style={{ flex: 1.5, fontSize: 11, color: '#2196F3' }}>At Antenna</Text>
                      <Text style={{ flex: 1, fontSize: 11, color: '#fff', textAlign: 'center' }}>{results.power_at_antenna_watts || '-'}W</Text>
                      <Text style={{ flex: 1, fontSize: 11, color: '#fff', textAlign: 'center' }}>-</Text>
                    </View>
                    <View style={{ flexDirection: 'row', paddingVertical: 6, paddingHorizontal: 8, borderBottomWidth: 1, borderBottomColor: '#333' }}>
                      <Text style={{ flex: 1.5, fontSize: 11, color: '#4CAF50' }}>Forward</Text>
                      <Text style={{ flex: 1, fontSize: 11, color: '#fff', textAlign: 'center' }}>{results.forward_power_watts?.toFixed(1) || '-'}W</Text>
                      <Text style={{ flex: 1, fontSize: 11, color: '#fff', textAlign: 'center' }}>{results.forward_power_100w}W</Text>
                    </View>
                    <View style={{ flexDirection: 'row', paddingVertical: 6, paddingHorizontal: 8 }}>
                      <Text style={{ flex: 1.5, fontSize: 11, color: '#f44336' }}>Reflected</Text>
                      <Text style={{ flex: 1, fontSize: 11, color: '#fff', textAlign: 'center' }}>{results.reflected_power_watts?.toFixed(2) || '-'}W</Text>
                      <Text style={{ flex: 1, fontSize: 11, color: '#fff', textAlign: 'center' }}>{results.reflected_power_100w}W</Text>
                    </View>
                    {results.coax_info && (
                      <View style={{ paddingVertical: 6, paddingHorizontal: 8, borderTopWidth: 1, borderTopColor: '#333', backgroundColor: '#1a1a2e' }}>
                        <Text style={{ fontSize: 9, color: '#888' }}>Feedline: {results.coax_info.type} | {results.coax_info.length_ft}ft | Loss: {results.coax_info.total_loss_db} dB</Text>
                      </View>
                    )}
                  </View>
                </SpecSection>
              )}

              {/* Section: Ground Radials (conditional) */}
              {results.ground_radials_info && (
                <SpecSection title="Ground Radial System" icon="git-network-outline" color="#8BC34A">
                  <SpecRow label="Ground Type" value={results.ground_radials_info.ground_type} />
                  <SpecRow label="Number of Radials" value={`${results.ground_radials_info.num_radials}`} />
                  <SpecRow label="Radial Length" value={`${results.ground_radials_info.radial_length_ft}' (${results.ground_radials_info.radial_length_in}")`} />
                  <SpecRow label="Total Wire" value={`${results.ground_radials_info.total_wire_length_ft}'`} />
                  <SpecRow label="SWR Improvement" value={`${results.ground_radials_info.estimated_improvements?.swr_improvement}`} />
                  <SpecRow label="Efficiency Bonus" value={`+${results.ground_radials_info.estimated_improvements?.efficiency_bonus_percent}%`} accent="#8BC34A" />
                </SpecSection>
              )}

              {/* Section: Boom Correction */}
              {results.boom_correction_info && (
                <SpecSection title={`Boom: ${results.boom_correction_info.boom_mount === 'bonded' ? 'Bonded' : results.boom_correction_info.boom_mount === 'insulated' ? 'Insulated' : 'Non-Conductive'}`} icon={results.boom_correction_info.boom_mount === 'bonded' ? 'flash' : results.boom_correction_info.boom_mount === 'nonconductive' ? 'leaf' : 'shield-half'} color={results.boom_correction_info.boom_mount === 'bonded' ? '#FF9800' : results.boom_correction_info.boom_mount === 'insulated' ? '#2196F3' : '#4CAF50'}>
                  <SpecRow label="Mount Type" value={results.boom_correction_info.boom_mount === 'bonded' ? 'Elements Bonded to Metal Boom' : results.boom_correction_info.boom_mount === 'insulated' ? 'Insulated on Metal Boom' : 'Non-Conductive Boom'} accent={results.boom_correction_info.boom_mount === 'bonded' ? '#FF9800' : results.boom_correction_info.boom_mount === 'insulated' ? '#2196F3' : '#4CAF50'} />
                  {results.boom_correction_info.enabled && (
                    <>
                      <SpecRow label="Correction" value={`${(results.boom_correction_info.correction_multiplier * 100).toFixed(0)}% of full DL6WU`} />
                      <SpecRow label="Boom/Element Ratio" value={`${results.boom_correction_info.boom_to_element_ratio}:1`} />
                      <SpecRow label="Shorten Each Element" value={`${results.boom_correction_info.correction_total_in}" total`} accent="#FF9800" />
                      <SpecRow label="Per Side" value={`${results.boom_correction_info.correction_per_side_in}"`} small />
                      <SpecRow label="Gain Effect" value={`${results.boom_correction_info.gain_adj_db} dB`} />
                      <SpecRow label="F/B Effect" value={`${results.boom_correction_info.fb_adj_db} dB`} />
                      <SpecRow label="Impedance Shift" value={`${results.boom_correction_info.impedance_shift_ohm} ohm`} />
                    </>
                  )}
                  <Text style={{ fontSize: 9, color: '#888', marginTop: 4, fontStyle: 'italic' }}>{results.boom_correction_info.description}</Text>
                  {/* CORRECTED CUT LIST */}
                  {results.boom_correction_info.corrected_elements && results.boom_correction_info.corrected_elements.length > 0 && (
                    <View style={{ marginTop: 6, backgroundColor: '#1a2a1a', borderRadius: 6, padding: 8, borderWidth: 1, borderColor: '#4CAF5044' }}>
                      <Text style={{ fontSize: 10, fontWeight: '700', color: '#4CAF50', marginBottom: 6 }}>CORRECTED CUT LIST</Text>
                      <View style={{ flexDirection: 'row', marginBottom: 4 }}>
                        <Text style={{ flex: 1, fontSize: 8, fontWeight: '700', color: '#666' }}>ELEMENT</Text>
                        <Text style={{ flex: 1, fontSize: 8, fontWeight: '700', color: '#666', textAlign: 'center' }}>ORIGINAL</Text>
                        <Text style={{ flex: 0.3, fontSize: 8, color: '#666', textAlign: 'center' }}></Text>
                        <Text style={{ flex: 1, fontSize: 8, fontWeight: '700', color: '#4CAF50', textAlign: 'center' }}>CUT TO</Text>
                      </View>
                      {results.boom_correction_info.corrected_elements.map((el: any, i: number) => (
                        <View key={i} style={{ flexDirection: 'row', alignItems: 'center', paddingVertical: 3, borderTopWidth: i > 0 ? 1 : 0, borderTopColor: '#333' }}>
                          <Text style={{ flex: 1, fontSize: 9, fontWeight: '600', color: el.type === 'reflector' ? '#f44336' : el.type === 'driven' ? '#4CAF50' : '#2196F3' }}>
                            {el.type === 'reflector' ? 'Reflector' : el.type === 'driven' ? 'Driven' : `Director ${i - (results.boom_correction_info.corrected_elements[0]?.type === 'reflector' ? 2 : 1) + 1}`}
                          </Text>
                          <Text style={{ flex: 1, fontSize: 10, color: '#999', textAlign: 'center' }}>{el.original_length}"</Text>
                          <Text style={{ flex: 0.3, fontSize: 10, color: '#FF9800', textAlign: 'center' }}>{'\u2192'}</Text>
                          <Text style={{ flex: 1, fontSize: 10, fontWeight: '700', color: '#4CAF50', textAlign: 'center' }}>{el.corrected_length}"</Text>
                        </View>
                      ))}
                      <Text style={{ fontSize: 7, color: '#666', marginTop: 4, fontStyle: 'italic' }}>Lengths shortened by {results.boom_correction_info.correction_total_in}" to compensate for boom capacitance</Text>
                    </View>
                  )}
                  {results.boom_correction_info.practical_notes && (
                    <View style={{ marginTop: 6, backgroundColor: '#1e1e1e', borderRadius: 6, padding: 8 }}>
                      <Text style={{ fontSize: 10, fontWeight: '700', color: '#666', marginBottom: 4 }}>PRACTICAL NOTES</Text>
                      {results.boom_correction_info.practical_notes.map((note: string, i: number) => (
                        <Text key={i} style={{ fontSize: 9, color: '#aaa', marginBottom: 2 }}>{'\u2022'} {note}</Text>
                      ))}
                    </View>
                  )}
                </SpecSection>
              )}

              {/* Section: Wind Load */}
              {results.wind_load && (
                <FeatureGate feature="wind_load" label="Wind Load & Mechanical">
                <SpecSection title="Wind Load & Mechanical" icon="thunderstorm-outline" color="#FF5722">
                  <SpecRow label="Total Wind Area" value={`${results.wind_load.total_area_sqft} sq ft`} />
                  <SpecRow label="Total Weight" value={`${results.wind_load.total_weight_lbs} lbs`} accent="#FF5722" />
                  <View style={{ marginTop: 4, backgroundColor: '#1e1e1e', borderRadius: 6, padding: 8 }}>
                    <Text style={{ fontSize: 10, fontWeight: '700', color: '#666', marginBottom: 4 }}>WEIGHT BREAKDOWN</Text>
                    <SpecRow label="  Elements" value={`${results.wind_load.element_weight_lbs} lbs`} small />
                    <SpecRow label="  Boom ({results.wind_load.boom_length_ft}ft)" value={`${results.wind_load.boom_weight_lbs} lbs`} small />
                    <SpecRow label="  Hardware/Truss" value={`${results.wind_load.hardware_weight_lbs} lbs`} small />
                    {results.wind_load.has_truss && <Text style={{ fontSize: 9, color: '#FF9800', marginTop: 2 }}>Boom truss/support wires recommended (boom &gt; 12ft)</Text>}
                  </View>
                  <SpecRow label="Turn Radius" value={`${results.wind_load.turn_radius_ft}' (${results.wind_load.turn_radius_in}")`} />
                  <SpecRow label="Survival Rating" value={`${results.wind_load.survival_mph} mph`} accent={results.wind_load.survival_mph >= 90 ? '#4CAF50' : results.wind_load.survival_mph >= 70 ? '#FF9800' : '#f44336'} />
                  {results.wind_load.num_stacked > 1 && <SpecRow label="Stacked" value={`${results.wind_load.num_stacked}x (values include all antennas)`} />}
                  <View style={{ marginTop: 6, backgroundColor: '#1e1e1e', borderRadius: 6, padding: 8 }}>
                    <Text style={{ fontSize: 10, fontWeight: '700', color: '#666', marginBottom: 4 }}>WIND FORCE BY SPEED</Text>
                    <View style={{ flexDirection: 'row', backgroundColor: '#252525', borderRadius: 4, paddingVertical: 4, paddingHorizontal: 6, marginBottom: 4 }}>
                      <Text style={{ flex: 1, fontSize: 9, fontWeight: '700', color: '#888' }}>MPH</Text>
                      <Text style={{ flex: 1, fontSize: 9, fontWeight: '700', color: '#888', textAlign: 'right' }}>Force</Text>
                      <Text style={{ flex: 1.2, fontSize: 9, fontWeight: '700', color: '#888', textAlign: 'right' }}>Torque</Text>
                    </View>
                    {['50','70','80','90','100','120'].map(mph => {
                      const r = results.wind_load.wind_ratings?.[mph];
                      if (!r) return null;
                      return (
                        <View key={mph} style={{ flexDirection: 'row', paddingVertical: 3, paddingHorizontal: 6 }}>
                          <Text style={{ flex: 1, fontSize: 10, color: '#aaa' }}>{mph}</Text>
                          <Text style={{ flex: 1, fontSize: 10, color: r.force_lbs > 200 ? '#f44336' : '#fff', textAlign: 'right' }}>{r.force_lbs} lbs</Text>
                          <Text style={{ flex: 1.2, fontSize: 10, color: r.torque_ft_lbs > 400 ? '#f44336' : '#fff', textAlign: 'right' }}>{r.torque_ft_lbs} ft-lbs</Text>
                        </View>
                      );
                    })}
                  </View>
                </SpecSection>
                </FeatureGate>
              )}

              <Text style={{ fontSize: 9, color: '#444', textAlign: 'center', marginTop: 16 }}>Generated {new Date().toLocaleString()} | {user?.email || 'guest'}</Text>
            </ScrollView>
            )}
          </View>
        </View>
      </Modal>

      {/* Gamma Match Designer Modal */}
      <GammaDesigner
        visible={showGammaDesigner}
        onClose={() => setShowGammaDesigner(false)}
        numElements={inputs.num_elements}
        drivenLength={parseFloat(inputs.elements.find(e => e.element_type === 'driven')?.length || '203') || 203}
        frequencyMhz={inputs.frequency_mhz}
        calculatedFeedpointR={results?.matching_info?.gamma_design?.feedpoint_impedance_ohms}
        calculatedResonantFreq={results?.matching_info?.element_resonant_freq_mhz}
        reflectorSpacingIn={(() => {
          const driven = inputs.elements.find(e => e.element_type === 'driven');
          const reflector = inputs.elements.find(e => e.element_type === 'reflector');
          if (driven && reflector) return Math.abs(parseFloat(driven.position) - parseFloat(reflector.position));
          return undefined;
        })()}
        directorSpacingsIn={(() => {
          const driven = inputs.elements.find(e => e.element_type === 'driven');
          const dirs = inputs.elements.filter(e => e.element_type === 'director').sort((a, b) => parseFloat(a.position) - parseFloat(b.position));
          if (driven && dirs.length > 0) return dirs.map(d => Math.abs(parseFloat(d.position) - parseFloat(driven.position)));
          return undefined;
        })()}
        currentRodDia={gammaRodDia !== null ? parseFloat(gammaRodDia) || undefined : results?.matching_info?.gamma_design?.gamma_rod_diameter_in}
        currentRodSpacing={gammaRodSpacing !== null ? parseFloat(gammaRodSpacing) || undefined : results?.matching_info?.gamma_design?.gamma_rod_spacing_in}
        elementDiameter={parseFloat(inputs.elements.find(e => e.element_type === 'driven')?.diameter || '1.0') || 1.0}
        onApply={(barPos, insertion, recommendedDrivenLength) => {
          setGammaBarPos(barPos);
          setGammaRodInsertion(insertion);
          if (recommendedDrivenLength) {
            setInputs(prev => {
              const newElements = prev.elements.map(e => 
                e.element_type === 'driven' ? { ...e, length: recommendedDrivenLength.toFixed(2) } : e
              );
              return { ...prev, elements: newElements };
            });
          }
        }}
      />

      {/* Physics Debug Panel - floating sidebar */}
      <PhysicsDebugPanel
        visible={showDebugPanel}
        onClose={() => setShowDebugPanel(false)}
        debugTrace={results?.matching_info?.debug_trace || []}
        smithChartData={results?.smith_chart_data}
        centerFreq={parseFloat(inputs.frequency_mhz) || 27.185}
      />

    </SafeAreaView>
  );
}

