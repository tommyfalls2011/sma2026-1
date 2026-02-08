import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ScrollView, TextInput, ActivityIndicator, Alert, RefreshControl, Modal, Platform, Switch, Image } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useAuth } from './context/AuthContext';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL || 'https://helpful-adaptation-production.up.railway.app';

// Web-compatible confirm function
const confirmAction = (title: string, message: string, onConfirm: () => void) => {
  if (Platform.OS === 'web') {
    if (window.confirm(`${title}\n\n${message}`)) {
      onConfirm();
    }
  } else {
    Alert.alert(title, message, [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Confirm', style: 'destructive', onPress: onConfirm }
    ]);
  }
};

const TIER_COLORS: Record<string, string> = {
  trial: '#888',
  bronze: '#CD7F32',
  silver: '#C0C0C0',
  gold: '#FFD700',
  subadmin: '#9C27B0',
  admin: '#f44336'
};

interface PricingData {
  bronze: { monthly_price?: number; yearly_price?: number; max_elements: number };
  silver: { monthly_price?: number; yearly_price?: number; max_elements: number };
  gold: { monthly_price?: number; yearly_price?: number; max_elements: number };
  payment: { paypal_email: string; cashapp_tag: string };
}

interface UserData {
  id: string;
  email: string;
  name: string;
  subscription_tier: string;
  created_at: string;
}

export default function AdminScreen() {
  const router = useRouter();
  const { user, token } = useAuth();
  const [isAdmin, setIsAdmin] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [activeTab, setActiveTab] = useState<'pricing' | 'users' | 'designs' | 'tutorial' | 'designer' | 'discounts' | 'notify'>('pricing');
  
  // Pricing state
  const [pricing, setPricing] = useState<PricingData | null>(null);
  const [bronzeMonthlyPrice, setBronzeMonthlyPrice] = useState('');
  const [bronzeYearlyPrice, setBronzeYearlyPrice] = useState('');
  const [bronzeElements, setBronzeElements] = useState('');
  const [silverMonthlyPrice, setSilverMonthlyPrice] = useState('');
  const [silverYearlyPrice, setSilverYearlyPrice] = useState('');
  const [silverElements, setSilverElements] = useState('');
  const [goldMonthlyPrice, setGoldMonthlyPrice] = useState('');
  const [goldYearlyPrice, setGoldYearlyPrice] = useState('');
  const [goldElements, setGoldElements] = useState('');
  const [paypalEmail, setPaypalEmail] = useState('');
  const [cashappTag, setCashappTag] = useState('');
  
  // Feature toggles per tier
  const ALL_FEATURES = ['auto_tune', 'optimize_height', 'save_designs', 'csv_export', 'stacking', 'taper', 'corona_balls', 'ground_radials'];
  const FEATURE_LABELS: Record<string, string> = {
    auto_tune: 'Auto-Tune', optimize_height: 'Optimize Height', save_designs: 'Save Designs',
    csv_export: 'CSV Export', stacking: 'Stacking', taper: 'Tapered Elements',
    corona_balls: 'Corona Balls', ground_radials: 'Ground Radials'
  };
  const [bronzeFeatures, setBronzeFeatures] = useState<string[]>(['basic_calc', 'swr_meter', 'band_selection']);
  const [silverFeatures, setSilverFeatures] = useState<string[]>(['basic_calc', 'swr_meter', 'band_selection', 'auto_tune', 'save_designs']);
  const [goldFeatures, setGoldFeatures] = useState<string[]>(['all']);
  
  // Users state
  const [users, setUsers] = useState<UserData[]>([]);
  
  // Designs state
  const [designs, setDesigns] = useState<any[]>([]);
  const [deletingDesignId, setDeletingDesignId] = useState<string | null>(null);
  
  // Add User Modal state
  const [showAddUserModal, setShowAddUserModal] = useState(false);
  const [newUserEmail, setNewUserEmail] = useState('');
  const [newUserName, setNewUserName] = useState('');
  const [newUserPassword, setNewUserPassword] = useState('');
  const [newUserTier, setNewUserTier] = useState('trial');
  const [newUserTrialDays, setNewUserTrialDays] = useState('7');  // Default 7 days
  const [addingUser, setAddingUser] = useState(false);
  
  // Edit User Modal state
  const [showEditUserModal, setShowEditUserModal] = useState(false);
  const [editingUser, setEditingUser] = useState<any>(null);
  const [editUserTier, setEditUserTier] = useState('');
  const [savingUserRole, setSavingUserRole] = useState(false);
  
  // Tutorial state
  const [tutorialContent, setTutorialContent] = useState('');
  const [tutorialUpdatedAt, setTutorialUpdatedAt] = useState('');
  const [tutorialUpdatedBy, setTutorialUpdatedBy] = useState('');
  const [savingTutorial, setSavingTutorial] = useState(false);

  // Designer Info state
  const [designerContent, setDesignerContent] = useState('');
  const [designerUpdatedAt, setDesignerUpdatedAt] = useState('');
  const [designerUpdatedBy, setDesignerUpdatedBy] = useState('');
  const [savingDesigner, setSavingDesigner] = useState(false);

  // Discounts state
  const [discounts, setDiscounts] = useState<any[]>([]);
  const [discCode, setDiscCode] = useState('');
  const [discType, setDiscType] = useState<'percentage' | 'fixed'>('percentage');
  const [discValue, setDiscValue] = useState('');
  const [discApplies, setDiscApplies] = useState('all');
  const [discTiers, setDiscTiers] = useState<string[]>(['bronze', 'silver', 'gold']);
  const [discMaxUses, setDiscMaxUses] = useState('');
  const [discEmails, setDiscEmails] = useState('');
  const [creatingDiscount, setCreatingDiscount] = useState(false);
  const [editingDiscountId, setEditingDiscountId] = useState<string | null>(null);

  // Notify state
  const [expoUrl, setExpoUrl] = useState('');
  const [downloadLink, setDownloadLink] = useState('');
  const [qrBase64, setQrBase64] = useState('');
  const [emailSubject, setEmailSubject] = useState('SMA Antenna Calc - New Update Available!');
  const [emailMessage, setEmailMessage] = useState('We have released a new version of SMA Antenna Calc with improvements and bug fixes. Please install the latest version using the QR code or download link below.');
  const [sendingEmail, setSendingEmail] = useState(false);
  const [emailResult, setEmailResult] = useState('');
  const [userEmails, setUserEmails] = useState<any[]>([]);

  useEffect(() => {
    checkAdminAndLoad();
  }, [token]);

  const checkAdminAndLoad = async () => {
    if (!token) {
      setLoading(false);
      return;
    }

    try {
      // Check admin status
      const checkRes = await fetch(`${BACKEND_URL}/api/admin/check`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (checkRes.ok) {
        const status = await checkRes.json();
        setIsAdmin(status.is_admin);
        
        if (status.is_admin) {
          await loadData();
        }
      }
    } catch (error) {
      console.error('Admin check failed:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadData = async () => {
    try {
      // Load pricing
      const pricingRes = await fetch(`${BACKEND_URL}/api/admin/pricing`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (pricingRes.ok) {
        const data = await pricingRes.json();
        setPricing(data);
        setBronzeMonthlyPrice(data.bronze.monthly_price?.toString() || '');
        setBronzeYearlyPrice(data.bronze.yearly_price?.toString() || '');
        setBronzeElements(data.bronze.max_elements.toString());
        setBronzeFeatures(data.bronze.features || ['basic_calc', 'swr_meter', 'band_selection']);
        setSilverMonthlyPrice(data.silver.monthly_price?.toString() || '');
        setSilverYearlyPrice(data.silver.yearly_price?.toString() || '');
        setSilverElements(data.silver.max_elements.toString());
        setSilverFeatures(data.silver.features || ['basic_calc', 'swr_meter', 'band_selection', 'auto_tune', 'save_designs']);
        setGoldMonthlyPrice(data.gold.monthly_price?.toString() || '');
        setGoldYearlyPrice(data.gold.yearly_price?.toString() || '');
        setGoldElements(data.gold.max_elements.toString());
        setGoldFeatures(data.gold.features || ['all']);
        setPaypalEmail(data.payment.paypal_email);
        setCashappTag(data.payment.cashapp_tag);
      }

      // Load users
      const usersRes = await fetch(`${BACKEND_URL}/api/admin/users`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (usersRes.ok) {
        const usersData = await usersRes.json();
        setUsers(usersData);
      }
      
      // Load designs
      const designsRes = await fetch(`${BACKEND_URL}/api/admin/designs`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (designsRes.ok) {
        const designsData = await designsRes.json();
        setDesigns(designsData.designs || []);
      }
    } catch (error) {
      console.error('Failed to load admin data:', error);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await loadData();
    setRefreshing(false);
  };

  const loadTutorialContent = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/admin/tutorial`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setTutorialContent(data.content || '');
        setTutorialUpdatedAt(data.updated_at || '');
        setTutorialUpdatedBy(data.updated_by || '');
      }
    } catch (e) { /* ignore */ }
  };

  const saveTutorialContent = async () => {
    setSavingTutorial(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/admin/tutorial`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ content: tutorialContent })
      });
      if (res.ok) {
        if (Platform.OS === 'web') { window.alert('Tutorial content saved!'); }
        else { Alert.alert('Saved', 'Tutorial content updated successfully.'); }
        loadTutorialContent();
      }
    } catch (e) {
      if (Platform.OS === 'web') { window.alert('Failed to save tutorial'); }
      else { Alert.alert('Error', 'Failed to save tutorial content.'); }
    } finally {
      setSavingTutorial(false);
    }
  };

  const loadDesignerContent = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/admin/designer-info`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setDesignerContent(data.content || '');
        setDesignerUpdatedAt(data.updated_at || '');
        setDesignerUpdatedBy(data.updated_by || '');
      }
    } catch (e) { /* ignore */ }
  };

  const saveDesignerContent = async () => {
    setSavingDesigner(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/admin/designer-info`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ content: designerContent })
      });
      if (res.ok) {
        if (Platform.OS === 'web') { window.alert('Designer info saved!'); }
        else { Alert.alert('Saved', 'Designer info updated successfully.'); }
        loadDesignerContent();
      }
    } catch (e) {
      if (Platform.OS === 'web') { window.alert('Failed to save designer info'); }
      else { Alert.alert('Error', 'Failed to save designer info.'); }
    } finally {
      setSavingDesigner(false);
    }
  };

  // === DISCOUNT FUNCTIONS ===
  const loadDiscounts = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/admin/discounts`, { headers: { 'Authorization': `Bearer ${token}` } });
      if (res.ok) { const d = await res.json(); setDiscounts(d.discounts || []); }
    } catch (e) { console.error('Load discounts error:', e); }
  };

  const createDiscount = async () => {
    if (!discCode || !discValue) { Alert.alert('Error', 'Code and value are required'); return; }
    setCreatingDiscount(true);
    try {
      const isEditing = !!editingDiscountId;
      const url = isEditing ? `${BACKEND_URL}/api/admin/discounts/${editingDiscountId}` : `${BACKEND_URL}/api/admin/discounts`;
      const res = await fetch(url, {
        method: isEditing ? 'PUT' : 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({
          code: discCode, discount_type: discType, value: parseFloat(discValue),
          applies_to: discApplies, tiers: discTiers,
          max_uses: discMaxUses ? parseInt(discMaxUses) : null,
          user_emails: discEmails ? discEmails.split(',').map((e: string) => e.trim()) : [],
        }),
      });
      if (res.ok) { clearDiscountForm(); loadDiscounts(); Alert.alert('Success', isEditing ? 'Discount updated!' : 'Discount created!'); }
      else { const err = await res.json(); Alert.alert('Error', err.detail || 'Failed'); }
    } catch (e) { Alert.alert('Error', 'Failed to save discount'); }
    setCreatingDiscount(false);
  };

  const editDiscount = (d: any) => {
    setEditingDiscountId(d.id);
    setDiscCode(d.code);
    setDiscType(d.discount_type || 'percentage');
    setDiscValue(String(d.value));
    setDiscApplies(d.applies_to || 'all');
    setDiscTiers(d.tiers || ['bronze', 'silver', 'gold']);
    setDiscMaxUses(d.max_uses ? String(d.max_uses) : '');
    setDiscEmails((d.user_emails || []).join(', '));
  };

  const clearDiscountForm = () => {
    setEditingDiscountId(null);
    setDiscCode(''); setDiscValue(''); setDiscMaxUses(''); setDiscEmails('');
    setDiscType('percentage'); setDiscApplies('all'); setDiscTiers(['bronze', 'silver', 'gold']);
  };

  const deleteDiscount = (id: string) => {
    confirmAction('Delete Discount', 'Are you sure?', async () => {
      await fetch(`${BACKEND_URL}/api/admin/discounts/${id}`, { method: 'DELETE', headers: { 'Authorization': `Bearer ${token}` } });
      loadDiscounts();
    });
  };

  const toggleDiscount = async (id: string) => {
    await fetch(`${BACKEND_URL}/api/admin/discounts/${id}/toggle`, { method: 'POST', headers: { 'Authorization': `Bearer ${token}` } });
    loadDiscounts();
  };

  // === NOTIFY FUNCTIONS ===
  const loadNotifyData = async () => {
    try {
      const [settingsRes, emailsRes] = await Promise.all([
        fetch(`${BACKEND_URL}/api/admin/app-update-settings`, { headers: { 'Authorization': `Bearer ${token}` } }),
        fetch(`${BACKEND_URL}/api/admin/user-emails`, { headers: { 'Authorization': `Bearer ${token}` } }),
      ]);
      if (settingsRes.ok) {
        const d = await settingsRes.json();
        setExpoUrl(d.expo_url || '');
        setDownloadLink(d.download_link || '');
        if (d.expo_url) {
          const qrRes = await fetch(`${BACKEND_URL}/api/admin/qr-code`, { headers: { 'Authorization': `Bearer ${token}` } });
          if (qrRes.ok) { const qd = await qrRes.json(); setQrBase64(qd.qr_base64); }
        }
      }
      if (emailsRes.ok) {
        const d = await emailsRes.json();
        const filtered = (d.users || []).filter((u: any) => {
          const e = (u.email || '').toLowerCase();
          if (e === (user?.email || '').toLowerCase()) return false; // exclude admin
          if (e.endsWith('@testuser.com')) return false; // exclude test users
          return true;
        });
        setUserEmails(filtered);
      }
    } catch (e) { console.error('Load notify error:', e); }
  };

  const saveUpdateSettings = async () => {
    try {
      await fetch(`${BACKEND_URL}/api/admin/app-update-settings`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ expo_url: expoUrl, download_link: downloadLink }),
      });
      if (expoUrl) {
        const qrRes = await fetch(`${BACKEND_URL}/api/admin/qr-code`, { headers: { 'Authorization': `Bearer ${token}` } });
        if (qrRes.ok) { const d = await qrRes.json(); setQrBase64(d.qr_base64); }
      }
      Alert.alert('Success', 'Settings saved!');
    } catch (e) { Alert.alert('Error', 'Failed to save settings'); }
  };

  const sendUpdateEmail = async () => {
    setSendingEmail(true); setEmailResult('');
    try {
      // Get all user emails, send them to admin in one email
      const emailsRes = await fetch(`${BACKEND_URL}/api/admin/user-emails`, { headers: { 'Authorization': `Bearer ${token}` } });
      const emailsData = emailsRes.ok ? await emailsRes.json() : { users: [] };
      const allUsers = emailsData.users || [];
      const adminEmail = (user?.email || 'fallstommy@gmail.com').toLowerCase();
      const filtered = allUsers.filter((u: any) => {
        const e = (u.email || '').toLowerCase();
        if (e === adminEmail) return false;
        if (e.endsWith('@testuser.com')) return false;
        return true;
      });
      setUserEmails(filtered);
      const allEmails = filtered.map((u: any) => u.email).filter(Boolean);

      if (allEmails.length === 0) { setEmailResult('❌ No users found'); setSendingEmail(false); return; }

      const emailList = allEmails.join(', ');
      const fullMessage = `${emailMessage}\n\n--- COPY THE EMAILS BELOW INTO GMAIL BCC ---\n\n${emailList}\n\n--- ${allEmails.length} USERS TOTAL ---\n\nQR/Download Link: ${expoUrl || downloadLink || 'Not set'}`;

      const res = await fetch(`${BACKEND_URL}/api/admin/send-update-email`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ subject: emailSubject, message: fullMessage, expo_url: expoUrl, download_link: downloadLink, send_to: user?.email || 'fallstommy@gmail.com' }),
      });
      const d = await res.json();
      if (res.ok) { setEmailResult(`✅ Email list sent to your inbox (${allEmails.length} users)`); }
      else { setEmailResult(`❌ ${d.detail || 'Failed'}`); }
    } catch (e) { setEmailResult('❌ Network error'); }
    setSendingEmail(false);
  };

  const savePricing = async () => {
    setSaving(true);
    try {
      // Save pricing
      const pricingRes = await fetch(`${BACKEND_URL}/api/admin/pricing`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          bronze_monthly_price: parseFloat(bronzeMonthlyPrice),
          bronze_yearly_price: parseFloat(bronzeYearlyPrice),
          bronze_max_elements: parseInt(bronzeElements),
          bronze_features: bronzeFeatures,
          silver_monthly_price: parseFloat(silverMonthlyPrice),
          silver_yearly_price: parseFloat(silverYearlyPrice),
          silver_max_elements: parseInt(silverElements),
          silver_features: silverFeatures,
          gold_monthly_price: parseFloat(goldMonthlyPrice),
          gold_yearly_price: parseFloat(goldYearlyPrice),
          gold_max_elements: parseInt(goldElements),
          gold_features: goldFeatures
        })
      });

      // Save payment config
      const paymentRes = await fetch(`${BACKEND_URL}/api/admin/payment`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          paypal_email: paypalEmail,
          cashapp_tag: cashappTag
        })
      });

      if (pricingRes.ok && paymentRes.ok) {
        Alert.alert('Success', 'Settings saved successfully!');
      } else {
        Alert.alert('Error', 'Failed to save settings');
      }
    } catch (error) {
      Alert.alert('Error', 'Network error');
    } finally {
      setSaving(false);
    }
  };

  const changeUserRole = (user: any) => {
    setEditingUser(user);
    setEditUserTier(user.subscription_tier);
    setShowEditUserModal(true);
  };

  const saveUserRole = async () => {
    if (!editingUser) return;
    
    setSavingUserRole(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/admin/users/${editingUser.id}/role`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ role: editUserTier })
      });

      if (res.ok) {
        Alert.alert('Success', `${editingUser.name} is now ${editUserTier}`);
        setShowEditUserModal(false);
        setEditingUser(null);
        await loadData();
      } else {
        const error = await res.json();
        Alert.alert('Error', error.detail || 'Failed to update role');
      }
    } catch (error) {
      Alert.alert('Error', 'Network error');
    } finally {
      setSavingUserRole(false);
    }
  };

  const addNewUser = async () => {
    if (!newUserEmail.trim() || !newUserName.trim() || !newUserPassword.trim()) {
      Alert.alert('Error', 'Please fill in all fields');
      return;
    }
    
    setAddingUser(true);
    try {
      const payload: any = {
        email: newUserEmail.trim(),
        name: newUserName.trim(),
        password: newUserPassword,
        subscription_tier: newUserTier
      };
      
      // Add trial_days if trial tier is selected
      if (newUserTier === 'trial') {
        payload.trial_days = parseInt(newUserTrialDays) || 7;
      }
      
      const res = await fetch(`${BACKEND_URL}/api/admin/users/create`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        const data = await res.json();
        Alert.alert('Success', `User ${newUserEmail} created successfully!`);
        setShowAddUserModal(false);
        setNewUserEmail('');
        setNewUserName('');
        setNewUserPassword('');
        setNewUserTier('trial');
        setNewUserTrialDays('7');
        await loadData();
      } else {
        const error = await res.json();
        Alert.alert('Error', error.detail || 'Failed to create user');
      }
    } catch (error) {
      Alert.alert('Error', 'Network error');
    } finally {
      setAddingUser(false);
    }
  };

  const deleteUser = async (userId: string, userEmail: string) => {
    confirmAction(
      'Delete User',
      `Are you sure you want to delete ${userEmail}?\n\nThis will also delete all their saved designs.`,
      async () => {
        try {
          const res = await fetch(`${BACKEND_URL}/api/admin/users/${userId}`, {
            method: 'DELETE',
            headers: { Authorization: `Bearer ${token}` }
          });

          if (res.ok) {
            Alert.alert('Success', `User ${userEmail} deleted`);
            await loadData();
          } else {
            const error = await res.json();
            Alert.alert('Error', error.detail || 'Failed to delete user');
          }
        } catch (error) {
          Alert.alert('Error', 'Network error');
        }
      }
    );
  };

  const deleteDesign = async (designId: string, designName: string) => {
    confirmAction(
      'Delete Design',
      `Are you sure you want to delete "${designName}"?`,
      async () => {
        setDeletingDesignId(designId);
        try {
          const res = await fetch(`${BACKEND_URL}/api/admin/designs/${designId}`, {
            method: 'DELETE',
            headers: { Authorization: `Bearer ${token}` }
          });

          if (res.ok) {
            Alert.alert('Success', `Design "${designName}" deleted`);
            await loadData();
          } else {
            const error = await res.json();
            Alert.alert('Error', error.detail || 'Failed to delete design');
          }
        } catch (error) {
          Alert.alert('Error', 'Network error');
        } finally {
          setDeletingDesignId(null);
        }
      }
    );
  };

  const deleteAllDesigns = async () => {
    confirmAction(
      'Delete ALL Designs',
      `Are you sure you want to delete ALL ${designs.length} saved designs? This cannot be undone!`,
      async () => {
        try {
          const res = await fetch(`${BACKEND_URL}/api/admin/designs/bulk/all`, {
            method: 'DELETE',
            headers: { Authorization: `Bearer ${token}` }
          });

          if (res.ok) {
            const data = await res.json();
            Alert.alert('Success', data.message);
            await loadData();
          } else {
            const error = await res.json();
            Alert.alert('Error', error.detail || 'Failed to delete designs');
          }
        } catch (error) {
          Alert.alert('Error', 'Network error');
        }
      }
    );
  };

  if (loading) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.centered}>
          <ActivityIndicator size="large" color="#4CAF50" />
        </View>
      </SafeAreaView>
    );
  }

  if (!user || !isAdmin) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.header}>
          <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
            <Ionicons name="arrow-back" size={24} color="#fff" />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Admin Panel</Text>
          <View style={{ width: 40 }} />
        </View>
        <View style={styles.centered}>
          <Ionicons name="lock-closed" size={60} color="#f44336" />
          <Text style={styles.accessDenied}>Access Denied</Text>
          <Text style={styles.accessDeniedSub}>Admin privileges required</Text>
          <TouchableOpacity style={styles.loginBtn} onPress={() => router.replace('/login')}>
            <Text style={styles.loginBtnText}>Go to Login</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
          <Ionicons name="arrow-back" size={24} color="#fff" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Admin Panel</Text>
        <View style={styles.adminBadge}>
          <Ionicons name="shield-checkmark" size={16} color="#f44336" />
        </View>
      </View>

      {/* Tabs */}
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ backgroundColor: '#1a1a1a', maxHeight: 48 }} contentContainerStyle={{ paddingHorizontal: 8, paddingVertical: 6, gap: 6, alignItems: 'center' }}>
        <TouchableOpacity style={[styles.tabPill, activeTab === 'pricing' && styles.tabPillActive]} onPress={() => setActiveTab('pricing')}>
          <Ionicons name="pricetag" size={14} color={activeTab === 'pricing' ? '#fff' : '#888'} />
          <Text style={[styles.tabPillText, activeTab === 'pricing' && styles.tabPillTextActive]}>Pricing</Text>
        </TouchableOpacity>
        <TouchableOpacity style={[styles.tabPill, activeTab === 'users' && styles.tabPillActive]} onPress={() => setActiveTab('users')}>
          <Ionicons name="people" size={14} color={activeTab === 'users' ? '#fff' : '#888'} />
          <Text style={[styles.tabPillText, activeTab === 'users' && styles.tabPillTextActive]}>Users</Text>
        </TouchableOpacity>
        <TouchableOpacity style={[styles.tabPill, activeTab === 'designs' && styles.tabPillActive]} onPress={() => setActiveTab('designs')}>
          <Ionicons name="save" size={14} color={activeTab === 'designs' ? '#fff' : '#888'} />
          <Text style={[styles.tabPillText, activeTab === 'designs' && styles.tabPillTextActive]}>Designs</Text>
        </TouchableOpacity>
        <TouchableOpacity style={[styles.tabPill, activeTab === 'tutorial' && styles.tabPillActive]} onPress={() => { setActiveTab('tutorial'); loadTutorialContent(); }}>
          <Ionicons name="book" size={14} color={activeTab === 'tutorial' ? '#fff' : '#888'} />
          <Text style={[styles.tabPillText, activeTab === 'tutorial' && styles.tabPillTextActive]}>Tutorial</Text>
        </TouchableOpacity>
        <TouchableOpacity style={[styles.tabPill, activeTab === 'designer' && styles.tabPillActive]} onPress={() => { setActiveTab('designer'); loadDesignerContent(); }}>
          <Ionicons name="person" size={14} color={activeTab === 'designer' ? '#fff' : '#888'} />
          <Text style={[styles.tabPillText, activeTab === 'designer' && styles.tabPillTextActive]}>Designer</Text>
        </TouchableOpacity>
        <TouchableOpacity style={[styles.tabPill, activeTab === 'discounts' && styles.tabPillActive]} onPress={() => { setActiveTab('discounts'); loadDiscounts(); }}>
          <Ionicons name="pricetags" size={14} color={activeTab === 'discounts' ? '#fff' : '#888'} />
          <Text style={[styles.tabPillText, activeTab === 'discounts' && styles.tabPillTextActive]}>Discounts</Text>
        </TouchableOpacity>
        <TouchableOpacity style={[styles.tabPill, activeTab === 'notify' && styles.tabPillActive]} onPress={() => { setActiveTab('notify'); loadNotifyData(); }}>
          <Ionicons name="mail" size={14} color={activeTab === 'notify' ? '#fff' : '#888'} />
          <Text style={[styles.tabPillText, activeTab === 'notify' && styles.tabPillTextActive]}>Notify</Text>
        </TouchableOpacity>
      </ScrollView>

      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#4CAF50" />}
        keyboardShouldPersistTaps="handled"
        nestedScrollEnabled={true}
      >
        {activeTab === 'pricing' ? (
          <>
            {/* Pricing Section */}
            <Text style={styles.sectionTitle}>Subscription Pricing</Text>
            
            {/* Bronze */}
            <View style={[styles.tierCard, { borderLeftColor: TIER_COLORS.bronze }]}>
              <View style={styles.tierHeader}>
                <Ionicons name="shield-outline" size={20} color={TIER_COLORS.bronze} />
                <Text style={[styles.tierName, { color: TIER_COLORS.bronze }]}>Bronze</Text>
              </View>
              <View style={styles.tierFields}>
                <View style={styles.field}>
                  <Text style={styles.fieldLabel}>Monthly Price</Text>
                  <TextInput
                    style={styles.input}
                    value={bronzeMonthlyPrice}
                    onChangeText={setBronzeMonthlyPrice}
                    keyboardType="decimal-pad"
                    placeholder="9.99"
                    placeholderTextColor="#555"
                  />
                </View>
                <View style={styles.field}>
                  <Text style={styles.fieldLabel}>Yearly Price</Text>
                  <TextInput
                    style={styles.input}
                    value={bronzeYearlyPrice}
                    onChangeText={setBronzeYearlyPrice}
                    keyboardType="decimal-pad"
                    placeholder="99.99"
                    placeholderTextColor="#555"
                  />
                </View>
                <View style={styles.field}>
                  <Text style={styles.fieldLabel}>Max Elements</Text>
                  <TextInput
                    style={styles.input}
                    value={bronzeElements}
                    onChangeText={setBronzeElements}
                    keyboardType="number-pad"
                    placeholder="3"
                    placeholderTextColor="#555"
                  />
                </View>
              </View>

            {/* Bronze Features */}
            <View style={styles.featuresSection}>
              <Text style={styles.featuresTitle}>Features</Text>
              {ALL_FEATURES.map(feat => (
                <View key={feat} style={styles.featureRow}>
                  <Text style={styles.featureLabel}>{FEATURE_LABELS[feat]}</Text>
                  <Switch value={bronzeFeatures.includes(feat) || bronzeFeatures.includes('all')} onValueChange={(v) => {
                    if (v) setBronzeFeatures(prev => [...prev, feat]);
                    else setBronzeFeatures(prev => prev.filter(f => f !== feat && f !== 'all'));
                  }} trackColor={{ false: '#333', true: '#CD7F32' }} thumbColor="#fff" />
                </View>
              ))}
            </View>
            </View>

            {/* Silver */}
            <View style={[styles.tierCard, { borderLeftColor: TIER_COLORS.silver }]}>
              <View style={styles.tierHeader}>
                <Ionicons name="shield-half-outline" size={20} color={TIER_COLORS.silver} />
                <Text style={[styles.tierName, { color: TIER_COLORS.silver }]}>Silver</Text>
              </View>
              <View style={styles.tierFields}>
                <View style={styles.field}>
                  <Text style={styles.fieldLabel}>Monthly Price</Text>
                  <TextInput
                    style={styles.input}
                    value={silverMonthlyPrice}
                    onChangeText={setSilverMonthlyPrice}
                    keyboardType="decimal-pad"
                    placeholder="19.99"
                    placeholderTextColor="#555"
                  />
                </View>
                <View style={styles.field}>
                  <Text style={styles.fieldLabel}>Yearly Price</Text>
                  <TextInput
                    style={styles.input}
                    value={silverYearlyPrice}
                    onChangeText={setSilverYearlyPrice}
                    keyboardType="decimal-pad"
                    placeholder="199.99"
                    placeholderTextColor="#555"
                  />
                </View>
                <View style={styles.field}>
                  <Text style={styles.fieldLabel}>Max Elements</Text>
                  <TextInput
                    style={styles.input}
                    value={silverElements}
                    onChangeText={setSilverElements}
                    keyboardType="number-pad"
                    placeholder="7"
                    placeholderTextColor="#555"
                  />
                </View>
              </View>

            {/* Silver Features */}
            <View style={styles.featuresSection}>
              <Text style={styles.featuresTitle}>Features</Text>
              {ALL_FEATURES.map(feat => (
                <View key={feat} style={styles.featureRow}>
                  <Text style={styles.featureLabel}>{FEATURE_LABELS[feat]}</Text>
                  <Switch value={silverFeatures.includes(feat) || silverFeatures.includes('all')} onValueChange={(v) => {
                    if (v) setSilverFeatures(prev => [...prev, feat]);
                    else setSilverFeatures(prev => prev.filter(f => f !== feat && f !== 'all'));
                  }} trackColor={{ false: '#333', true: '#C0C0C0' }} thumbColor="#fff" />
                </View>
              ))}
            </View>
            </View>

            {/* Gold */}
            <View style={[styles.tierCard, { borderLeftColor: TIER_COLORS.gold }]}>
              <View style={styles.tierHeader}>
                <Ionicons name="shield-checkmark" size={20} color={TIER_COLORS.gold} />
                <Text style={[styles.tierName, { color: TIER_COLORS.gold }]}>Gold</Text>
              </View>
              <View style={styles.tierFields}>
                <View style={styles.field}>
                  <Text style={styles.fieldLabel}>Monthly Price</Text>
                  <TextInput
                    style={styles.input}
                    value={goldMonthlyPrice}
                    onChangeText={setGoldMonthlyPrice}
                    keyboardType="decimal-pad"
                    placeholder="29.99"
                    placeholderTextColor="#555"
                  />
                </View>
                <View style={styles.field}>
                  <Text style={styles.fieldLabel}>Yearly Price</Text>
                  <TextInput
                    style={styles.input}
                    value={goldYearlyPrice}
                    onChangeText={setGoldYearlyPrice}
                    keyboardType="decimal-pad"
                    placeholder="299.99"
                    placeholderTextColor="#555"
                  />
                </View>
                <View style={styles.field}>
                  <Text style={styles.fieldLabel}>Max Elements</Text>
                  <TextInput
                    style={styles.input}
                    value={goldElements}
                    onChangeText={setGoldElements}
                    keyboardType="number-pad"
                    placeholder="20"
                    placeholderTextColor="#555"
                  />
                </View>
              </View>

            {/* Gold Features */}
            <View style={styles.featuresSection}>
              <Text style={styles.featuresTitle}>Features</Text>
              <View style={styles.featureRow}>
                <Text style={styles.featureLabel}>All Features</Text>
                <Switch value={goldFeatures.includes('all')} onValueChange={(v) => {
                  if (v) setGoldFeatures(['all']);
                  else setGoldFeatures(['basic_calc', 'swr_meter', 'band_selection']);
                }} trackColor={{ false: '#333', true: '#FFD700' }} thumbColor="#fff" />
              </View>
              {!goldFeatures.includes('all') && ALL_FEATURES.map(feat => (
                <View key={feat} style={styles.featureRow}>
                  <Text style={styles.featureLabel}>{FEATURE_LABELS[feat]}</Text>
                  <Switch value={goldFeatures.includes(feat)} onValueChange={(v) => {
                    if (v) setGoldFeatures(prev => [...prev, feat]);
                    else setGoldFeatures(prev => prev.filter(f => f !== feat));
                  }} trackColor={{ false: '#333', true: '#FFD700' }} thumbColor="#fff" />
                </View>
              ))}
            </View>
            </View>

            {/* Payment Config */}
            <Text style={[styles.sectionTitle, { marginTop: 20 }]}>Payment Settings</Text>
            
            <View style={styles.paymentCard}>
              <View style={styles.paymentRow}>
                <Ionicons name="logo-paypal" size={24} color="#003087" />
                <View style={styles.paymentField}>
                  <Text style={styles.fieldLabel}>PayPal Email</Text>
                  <TextInput
                    style={styles.input}
                    value={paypalEmail}
                    onChangeText={setPaypalEmail}
                    keyboardType="email-address"
                    autoCapitalize="none"
                    placeholder="your@email.com"
                    placeholderTextColor="#555"
                  />
                </View>
              </View>
              <View style={styles.paymentRow}>
                <View style={styles.cashAppIcon}>
                  <Text style={styles.cashAppText}>$</Text>
                </View>
                <View style={styles.paymentField}>
                  <Text style={styles.fieldLabel}>Cash App Tag</Text>
                  <TextInput
                    style={styles.input}
                    value={cashappTag}
                    onChangeText={setCashappTag}
                    autoCapitalize="none"
                    placeholder="$yourtag"
                    placeholderTextColor="#555"
                  />
                </View>
              </View>
            </View>

            {/* Save Button */}
            <TouchableOpacity
              style={[styles.saveBtn, saving && styles.saveBtnDisabled]}
              onPress={savePricing}
              disabled={saving}
            >
              {saving ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <>
                  <Ionicons name="save" size={18} color="#fff" />
                  <Text style={styles.saveBtnText}>Save Changes</Text>
                </>
              )}
            </TouchableOpacity>
          </>
        ) : activeTab === 'users' ? (
          <>
            {/* Users Section */}
            <View style={styles.usersSectionHeader}>
              <Text style={styles.sectionTitle}>Manage Users ({users.length})</Text>
              <TouchableOpacity style={styles.addUserBtn} onPress={() => setShowAddUserModal(true)}>
                <Ionicons name="person-add" size={16} color="#fff" />
                <Text style={styles.addUserBtnText}>Add User</Text>
              </TouchableOpacity>
            </View>
            <Text style={styles.hint}>Tap a user to change their role. Long press to delete. Sub-admins get full access but can't edit settings.</Text>
            
            {users.map(u => (
              <TouchableOpacity
                key={u.id}
                style={[styles.userCard, { borderLeftColor: TIER_COLORS[u.subscription_tier] || '#888' }]}
                onPress={() => u.email.toLowerCase() !== 'fallstommy@gmail.com' && changeUserRole(u)}
                onLongPress={() => u.email.toLowerCase() !== 'fallstommy@gmail.com' && deleteUser(u.id, u.email)}
                disabled={u.email.toLowerCase() === 'fallstommy@gmail.com'}
              >
                <View style={styles.userInfo}>
                  <Text style={styles.userName}>{u.name}</Text>
                  <Text style={styles.userEmail}>{u.email}</Text>
                </View>
                <View style={[styles.userTierBadge, { backgroundColor: TIER_COLORS[u.subscription_tier] || '#888' }]}>
                  <Text style={styles.userTierText}>{u.subscription_tier}</Text>
                </View>
                {u.email.toLowerCase() !== 'fallstommy@gmail.com' && (
                  <TouchableOpacity onPress={() => deleteUser(u.id, u.email)} style={styles.deleteUserBtn}>
                    <Ionicons name="trash-outline" size={18} color="#f44336" />
                  </TouchableOpacity>
                )}
              </TouchableOpacity>
            ))}
          </>
        ) : null}
        
        {activeTab === 'designs' && (
          <>
            {/* Designs Section */}
            <View style={styles.usersSectionHeader}>
              <Text style={styles.sectionTitle}>Saved Designs ({designs.length})</Text>
              {designs.length > 0 && (
                <TouchableOpacity style={[styles.addUserBtn, { backgroundColor: '#f44336' }]} onPress={deleteAllDesigns}>
                  <Ionicons name="trash" size={14} color="#fff" />
                  <Text style={styles.addUserBtnText}>Delete All</Text>
                </TouchableOpacity>
              )}
            </View>
            <Text style={styles.hint}>Manage all user-saved antenna designs. Tap delete icon to remove individual designs.</Text>
            
            {designs.length === 0 ? (
              <View style={styles.emptyDesigns}>
                <Ionicons name="folder-open-outline" size={48} color="#444" />
                <Text style={styles.emptyDesignsText}>No saved designs found</Text>
              </View>
            ) : (
              designs.map(design => (
                <View key={design.id} style={styles.designCard}>
                  <View style={styles.designInfo}>
                    <Text style={styles.designName}>{design.name || 'Unnamed Design'}</Text>
                    <Text style={styles.designMeta}>
                      {design.element_count} elements • By: {design.user_name || design.user_email}
                    </Text>
                    <Text style={styles.designDate}>
                      {design.created_at ? new Date(design.created_at).toLocaleDateString() : 'Unknown date'}
                    </Text>
                  </View>
                  <TouchableOpacity 
                    onPress={() => deleteDesign(design.id, design.name)} 
                    style={styles.deleteDesignBtn}
                    disabled={deletingDesignId === design.id}
                  >
                    {deletingDesignId === design.id ? (
                      <ActivityIndicator size="small" color="#f44336" />
                    ) : (
                      <Ionicons name="trash-outline" size={20} color="#f44336" />
                    )}
                  </TouchableOpacity>
                </View>
              ))
            )}
          </>
        )}

        {/* Tutorial Editor Tab */}
        {activeTab === 'tutorial' && (
          <>
            <Text style={styles.sectionTitle}>Tutorial / Intro Content</Text>
            <Text style={styles.hint}>
              Edit the tutorial text shown to users when they first open the app. Uses simple markdown: # for headers, ## for subheaders, - for list items, **bold** for emphasis.
            </Text>
            {tutorialUpdatedAt ? (
              <Text style={{ fontSize: 10, color: '#666', marginBottom: 8 }}>
                Last updated: {new Date(tutorialUpdatedAt).toLocaleDateString()} by {tutorialUpdatedBy}
              </Text>
            ) : null}
            <TextInput
              style={{ backgroundColor: '#1a1a1a', borderRadius: 8, borderWidth: 1, borderColor: '#333', color: '#ccc', fontSize: 12, padding: 10, minHeight: 400, maxHeight: 500, textAlignVertical: 'top', fontFamily: 'monospace' }}
              value={tutorialContent}
              onChangeText={setTutorialContent}
              multiline
              scrollEnabled={true}
              numberOfLines={20}
              placeholder="Enter tutorial content here..."
              placeholderTextColor="#555"
            />
            <TouchableOpacity
              style={{ backgroundColor: '#FF9800', borderRadius: 8, padding: 12, marginTop: 12, alignItems: 'center', opacity: savingTutorial ? 0.6 : 1 }}
              onPress={saveTutorialContent}
              disabled={savingTutorial}
            >
              {savingTutorial ? <ActivityIndicator color="#fff" /> : (
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                  <Ionicons name="save" size={16} color="#fff" />
                  <Text style={{ color: '#fff', fontWeight: '600', fontSize: 13 }}>Save Tutorial</Text>
                </View>
              )}
            </TouchableOpacity>
            
            {/* Preview Section */}
            <Text style={[styles.sectionTitle, { marginTop: 20 }]}>Preview</Text>
            <View style={{ backgroundColor: '#1a1a1a', borderRadius: 8, padding: 12, borderWidth: 1, borderColor: '#333' }}>
              {tutorialContent.split('\n').map((line: string, i: number) => {
                const trimmed = line.trim();
                if (trimmed.startsWith('# ')) return <Text key={i} style={{ fontSize: 16, fontWeight: 'bold', color: '#FF9800', marginTop: 8, marginBottom: 4 }}>{trimmed.slice(2)}</Text>;
                if (trimmed.startsWith('## ')) return <Text key={i} style={{ fontSize: 13, fontWeight: '700', color: '#4CAF50', marginTop: 10, marginBottom: 3 }}>{trimmed.slice(3)}</Text>;
                if (trimmed.startsWith('- **')) {
                  const match = trimmed.match(/- \*\*(.+?)\*\*:?\s*(.*)/);
                  if (match) return <Text key={i} style={{ fontSize: 11, color: '#ccc', marginLeft: 8, marginBottom: 2 }}><Text style={{ fontWeight: '700', color: '#fff' }}>{match[1]}</Text>: {match[2]}</Text>;
                }
                if (trimmed.startsWith('- ')) return <Text key={i} style={{ fontSize: 11, color: '#ccc', marginLeft: 8, marginBottom: 2 }}>• {trimmed.slice(2)}</Text>;
                if (trimmed === '') return <View key={i} style={{ height: 4 }} />;
                return <Text key={i} style={{ fontSize: 11, color: '#ccc', marginBottom: 2, lineHeight: 16 }}>{trimmed}</Text>;
              })}
            </View>
          </>
        )}

        {/* Designer Info Editor Tab */}
        {activeTab === 'designer' && (
          <>
            <Text style={styles.sectionTitle}>Designer Info / About Me</Text>
            <Text style={styles.hint}>
              Edit the Designer Info shown to users when they tap "Designer Info" on the main screen. Uses simple markdown.
            </Text>
            {designerUpdatedAt ? (
              <Text style={{ fontSize: 10, color: '#666', marginBottom: 8 }}>
                Last updated: {new Date(designerUpdatedAt).toLocaleDateString()} by {designerUpdatedBy}
              </Text>
            ) : null}
            <TextInput
              style={{ backgroundColor: '#1a1a1a', borderRadius: 8, borderWidth: 1, borderColor: '#333', color: '#ccc', fontSize: 12, padding: 10, minHeight: 400, maxHeight: 500, textAlignVertical: 'top', fontFamily: 'monospace' }}
              value={designerContent}
              onChangeText={setDesignerContent}
              multiline
              scrollEnabled={true}
              numberOfLines={20}
              placeholder="Enter designer info / about me content..."
              placeholderTextColor="#555"
            />
            <TouchableOpacity
              style={{ backgroundColor: '#2196F3', borderRadius: 8, padding: 12, marginTop: 12, alignItems: 'center', opacity: savingDesigner ? 0.6 : 1 }}
              onPress={saveDesignerContent}
              disabled={savingDesigner}
            >
              {savingDesigner ? <ActivityIndicator color="#fff" /> : (
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                  <Ionicons name="save" size={16} color="#fff" />
                  <Text style={{ color: '#fff', fontWeight: '600', fontSize: 13 }}>Save Designer Info</Text>
                </View>
              )}
            </TouchableOpacity>
            
            {/* Preview Section */}
            <Text style={[styles.sectionTitle, { marginTop: 20 }]}>Preview</Text>
            <View style={{ backgroundColor: '#1a1a1a', borderRadius: 8, padding: 12, borderWidth: 1, borderColor: '#333' }}>
              {designerContent.split('\n').map((line: string, i: number) => {
                const trimmed = line.trim();
                if (trimmed.startsWith('# ')) return <Text key={i} style={{ fontSize: 16, fontWeight: 'bold', color: '#2196F3', marginTop: 8, marginBottom: 4 }}>{trimmed.slice(2)}</Text>;
                if (trimmed.startsWith('## ')) return <Text key={i} style={{ fontSize: 13, fontWeight: '700', color: '#4CAF50', marginTop: 10, marginBottom: 3 }}>{trimmed.slice(3)}</Text>;
                if (trimmed.startsWith('### ')) return <Text key={i} style={{ fontSize: 12, fontWeight: '700', color: '#FF9800', marginTop: 8, marginBottom: 3 }}>{trimmed.slice(4)}</Text>;
                if (trimmed.startsWith('- **')) {
                  const match = trimmed.match(/- \*\*(.+?)\*\*:?\s*(.*)/);
                  if (match) return <Text key={i} style={{ fontSize: 11, color: '#ccc', marginLeft: 8, marginBottom: 2 }}><Text style={{ fontWeight: '700', color: '#fff' }}>{match[1]}</Text>: {match[2]}</Text>;
                }
                if (trimmed.startsWith('- ')) return <Text key={i} style={{ fontSize: 11, color: '#ccc', marginLeft: 8, marginBottom: 2 }}>• {trimmed.slice(2)}</Text>;
                if (trimmed === '') return <View key={i} style={{ height: 4 }} />;
                return <Text key={i} style={{ fontSize: 11, color: '#ccc', marginBottom: 2, lineHeight: 16 }}>{trimmed}</Text>;
              })}
            </View>
          </>
        )}

        {/* === DISCOUNTS TAB === */}
        {activeTab === 'discounts' && (
          <>
            <Text style={styles.sectionTitle}>{editingDiscountId ? 'Edit Discount Code' : 'Create Discount Code'}</Text>
            <View style={{ backgroundColor: '#1a1a1a', borderRadius: 8, padding: 12, marginBottom: 12, borderWidth: 1, borderColor: editingDiscountId ? '#FF9800' : '#333' }}>
              <Text style={{ fontSize: 11, color: '#888', marginBottom: 4 }}>Code</Text>
              <TextInput style={{ backgroundColor: '#252525', borderRadius: 6, color: '#fff', padding: 10, fontSize: 14, marginBottom: 8, borderWidth: 1, borderColor: '#444' }} value={discCode} onChangeText={(t) => setDiscCode(t.toUpperCase())} placeholder="e.g. TEST50" placeholderTextColor="#555" autoCapitalize="characters" />

              <View style={{ flexDirection: 'row', gap: 8, marginBottom: 8 }}>
                <TouchableOpacity onPress={() => setDiscType('percentage')} style={{ flex: 1, backgroundColor: discType === 'percentage' ? '#4CAF50' : '#333', borderRadius: 6, padding: 10, alignItems: 'center' }}>
                  <Text style={{ color: '#fff', fontWeight: '600', fontSize: 12 }}>% Off</Text>
                </TouchableOpacity>
                <TouchableOpacity onPress={() => setDiscType('fixed')} style={{ flex: 1, backgroundColor: discType === 'fixed' ? '#4CAF50' : '#333', borderRadius: 6, padding: 10, alignItems: 'center' }}>
                  <Text style={{ color: '#fff', fontWeight: '600', fontSize: 12 }}>$ Off</Text>
                </TouchableOpacity>
              </View>

              <Text style={{ fontSize: 11, color: '#888', marginBottom: 4 }}>Value ({discType === 'percentage' ? '%' : '$'})</Text>
              <TextInput style={{ backgroundColor: '#252525', borderRadius: 6, color: '#fff', padding: 10, fontSize: 14, marginBottom: 8, borderWidth: 1, borderColor: '#444' }} value={discValue} onChangeText={setDiscValue} placeholder={discType === 'percentage' ? 'e.g. 50' : 'e.g. 10.00'} placeholderTextColor="#555" keyboardType="numeric" />

              <Text style={{ fontSize: 11, color: '#888', marginBottom: 4 }}>Applies To</Text>
              <View style={{ flexDirection: 'row', gap: 6, marginBottom: 8 }}>
                {['all', 'monthly', 'yearly'].map(opt => (
                  <TouchableOpacity key={opt} onPress={() => setDiscApplies(opt)} style={{ flex: 1, backgroundColor: discApplies === opt ? '#2196F3' : '#333', borderRadius: 6, padding: 8, alignItems: 'center' }}>
                    <Text style={{ color: '#fff', fontSize: 11, fontWeight: '600' }}>{opt.charAt(0).toUpperCase() + opt.slice(1)}</Text>
                  </TouchableOpacity>
                ))}
              </View>

              <Text style={{ fontSize: 11, color: '#888', marginBottom: 4 }}>Tiers</Text>
              <View style={{ flexDirection: 'row', gap: 6, marginBottom: 8 }}>
                {['bronze', 'silver', 'gold'].map(tier => (
                  <TouchableOpacity key={tier} onPress={() => setDiscTiers(prev => prev.includes(tier) ? prev.filter(t => t !== tier) : [...prev, tier])} style={{ flex: 1, backgroundColor: discTiers.includes(tier) ? (TIER_COLORS[tier] || '#888') : '#333', borderRadius: 6, padding: 8, alignItems: 'center' }}>
                    <Text style={{ color: '#fff', fontSize: 11, fontWeight: '600' }}>{tier.charAt(0).toUpperCase() + tier.slice(1)}</Text>
                  </TouchableOpacity>
                ))}
              </View>

              <Text style={{ fontSize: 11, color: '#888', marginBottom: 4 }}>Max Uses (optional)</Text>
              <TextInput style={{ backgroundColor: '#252525', borderRadius: 6, color: '#fff', padding: 10, fontSize: 14, marginBottom: 8, borderWidth: 1, borderColor: '#444' }} value={discMaxUses} onChangeText={setDiscMaxUses} placeholder="Leave empty for unlimited" placeholderTextColor="#555" keyboardType="numeric" />

              <Text style={{ fontSize: 11, color: '#888', marginBottom: 4 }}>Restrict to Emails (optional, comma-separated)</Text>
              <TextInput style={{ backgroundColor: '#252525', borderRadius: 6, color: '#fff', padding: 10, fontSize: 14, marginBottom: 12, borderWidth: 1, borderColor: '#444' }} value={discEmails} onChangeText={setDiscEmails} placeholder="Leave empty for all users" placeholderTextColor="#555" autoCapitalize="none" />

              <TouchableOpacity onPress={createDiscount} disabled={creatingDiscount} style={{ backgroundColor: '#E91E63', borderRadius: 8, padding: 12, alignItems: 'center', opacity: creatingDiscount ? 0.6 : 1 }}>
                {creatingDiscount ? <ActivityIndicator color="#fff" /> : (
                  <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                    <Ionicons name="add-circle" size={16} color="#fff" />
                    <Text style={{ color: '#fff', fontWeight: '700', fontSize: 13 }}>Create Discount</Text>
                  </View>
                )}
              </TouchableOpacity>
            </View>

            <Text style={styles.sectionTitle}>Active Discounts ({discounts.length})</Text>
            {discounts.length === 0 && <Text style={{ color: '#666', fontSize: 12, textAlign: 'center', padding: 20 }}>No discounts yet</Text>}
            {discounts.map((d: any) => (
              <View key={d.id} style={{ backgroundColor: '#1a1a1a', borderRadius: 8, padding: 12, marginBottom: 8, borderWidth: 1, borderColor: d.active ? '#E91E63' : '#333', opacity: d.active ? 1 : 0.5 }}>
                <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                    <Text style={{ color: '#E91E63', fontWeight: '700', fontSize: 16 }}>{d.code}</Text>
                    <View style={{ backgroundColor: d.discount_type === 'percentage' ? '#4CAF50' : '#FF9800', borderRadius: 4, paddingHorizontal: 6, paddingVertical: 2 }}>
                      <Text style={{ color: '#fff', fontSize: 10, fontWeight: '600' }}>{d.discount_type === 'percentage' ? `${d.value}%` : `$${d.value}`}</Text>
                    </View>
                  </View>
                  <View style={{ flexDirection: 'row', gap: 8 }}>
                    <TouchableOpacity onPress={() => toggleDiscount(d.id)}>
                      <Ionicons name={d.active ? 'pause-circle' : 'play-circle'} size={24} color={d.active ? '#FF9800' : '#4CAF50'} />
                    </TouchableOpacity>
                    <TouchableOpacity onPress={() => deleteDiscount(d.id)}>
                      <Ionicons name="trash" size={22} color="#f44336" />
                    </TouchableOpacity>
                  </View>
                </View>
                <Text style={{ fontSize: 10, color: '#888' }}>
                  {d.applies_to === 'all' ? 'All billing' : d.applies_to} · Tiers: {(d.tiers || []).join(', ')} · Used: {d.times_used}{d.max_uses ? `/${d.max_uses}` : ''}{d.user_emails?.length ? ` · ${d.user_emails.length} specific users` : ' · All users'}
                </Text>
              </View>
            ))}
          </>
        )}

        {/* === NOTIFY TAB === */}
        {activeTab === 'notify' && (
          <>
            <Text style={styles.sectionTitle}>App Update & QR Code</Text>
            <View style={{ backgroundColor: '#1a1a1a', borderRadius: 8, padding: 12, marginBottom: 12, borderWidth: 1, borderColor: '#333' }}>
              <Text style={{ fontSize: 11, color: '#888', marginBottom: 4 }}>Expo Build URL</Text>
              <TextInput style={{ backgroundColor: '#252525', borderRadius: 6, color: '#fff', padding: 10, fontSize: 12, marginBottom: 8, borderWidth: 1, borderColor: '#444' }} value={expoUrl} onChangeText={setExpoUrl} placeholder="exp://u.expo.dev/..." placeholderTextColor="#555" autoCapitalize="none" />

              <Text style={{ fontSize: 11, color: '#888', marginBottom: 4 }}>Download Link (optional, fallback for non-Expo users)</Text>
              <TextInput style={{ backgroundColor: '#252525', borderRadius: 6, color: '#fff', padding: 10, fontSize: 12, marginBottom: 8, borderWidth: 1, borderColor: '#444' }} value={downloadLink} onChangeText={setDownloadLink} placeholder="https://expo.dev/@your-app" placeholderTextColor="#555" autoCapitalize="none" />

              <TouchableOpacity onPress={saveUpdateSettings} style={{ backgroundColor: '#4CAF50', borderRadius: 8, padding: 10, alignItems: 'center', marginBottom: 12 }}>
                <Text style={{ color: '#fff', fontWeight: '600', fontSize: 12 }}>Save & Generate QR</Text>
              </TouchableOpacity>

              {qrBase64 ? (
                <View style={{ alignItems: 'center', padding: 12, backgroundColor: '#fff', borderRadius: 8, marginBottom: 8 }}>
                  <Text style={{ fontSize: 12, color: '#333', fontWeight: '600', marginBottom: 8 }}>Scan to Install</Text>
                  <Image source={{ uri: `data:image/png;base64,${qrBase64}` }} style={{ width: 200, height: 200, borderRadius: 4 }} resizeMode="contain" />
                  <Text style={{ fontSize: 10, color: '#666', marginTop: 6 }}>{expoUrl}</Text>
                </View>
              ) : null}
            </View>

            <Text style={styles.sectionTitle}>Compose Update Email</Text>
            <View style={{ backgroundColor: '#1a1a1a', borderRadius: 8, padding: 12, marginBottom: 12, borderWidth: 1, borderColor: '#333' }}>
              <Text style={{ fontSize: 11, color: '#888', marginBottom: 4 }}>Subject</Text>
              <TextInput style={{ backgroundColor: '#252525', borderRadius: 6, color: '#fff', padding: 10, fontSize: 13, marginBottom: 8, borderWidth: 1, borderColor: '#444' }} value={emailSubject} onChangeText={setEmailSubject} placeholder="Email subject" placeholderTextColor="#555" />

              <Text style={{ fontSize: 11, color: '#888', marginBottom: 4 }}>Message</Text>
              <TextInput style={{ backgroundColor: '#252525', borderRadius: 6, color: '#fff', padding: 10, fontSize: 12, marginBottom: 12, minHeight: 120, textAlignVertical: 'top', borderWidth: 1, borderColor: '#444' }} value={emailMessage} onChangeText={setEmailMessage} multiline numberOfLines={6} placeholder="Type your update message..." placeholderTextColor="#555" />

              <View style={{ backgroundColor: '#252525', borderRadius: 6, padding: 8, marginBottom: 12 }}>
                <Text style={{ fontSize: 11, color: '#4CAF50', fontWeight: '600', marginBottom: 6 }}>Recipients: {userEmails.length} users (tap to remove)</Text>
                <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 4 }}>
                  {userEmails.map((u: any, i: number) => (
                    <TouchableOpacity key={i} onPress={() => setUserEmails(prev => prev.filter((_, idx) => idx !== i))} style={{ flexDirection: 'row', alignItems: 'center', backgroundColor: '#333', borderRadius: 12, paddingHorizontal: 8, paddingVertical: 4, gap: 4 }}>
                      <Text style={{ fontSize: 10, color: '#ccc' }}>{u.email}</Text>
                      <Ionicons name="close-circle" size={14} color="#f44336" />
                    </TouchableOpacity>
                  ))}
                </View>
                {userEmails.length === 0 && <Text style={{ fontSize: 10, color: '#f44336', marginTop: 4 }}>No recipients — reload tab to refresh</Text>}
              </View>

              {emailResult ? <Text style={{ fontSize: 12, color: emailResult.startsWith('✅') ? '#4CAF50' : '#f44336', marginBottom: 8, textAlign: 'center' }}>{emailResult}</Text> : null}

              <TouchableOpacity onPress={() => confirmAction('Send Email List', `This will send all ${userEmails.length} user emails to your inbox. You can then BCC them in Gmail.`, sendUpdateEmail)} disabled={sendingEmail} style={{ backgroundColor: '#2196F3', borderRadius: 8, padding: 14, alignItems: 'center', opacity: sendingEmail ? 0.6 : 1 }}>
                {sendingEmail ? <ActivityIndicator color="#fff" /> : (
                  <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                    <Ionicons name="send" size={16} color="#fff" />
                    <Text style={{ color: '#fff', fontWeight: '700', fontSize: 14 }}>Send Email List to My Inbox</Text>
                  </View>
                )}
              </TouchableOpacity>
            </View>
          </>
        )}
      </ScrollView>
      
      {/* Add User Modal */}
      <Modal visible={showAddUserModal} transparent animationType="fade" onRequestClose={() => setShowAddUserModal(false)}>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Add New User</Text>
              <TouchableOpacity onPress={() => setShowAddUserModal(false)}>
                <Ionicons name="close" size={24} color="#888" />
              </TouchableOpacity>
            </View>
            
            <Text style={styles.modalLabel}>Email</Text>
            <TextInput
              style={styles.modalInput}
              value={newUserEmail}
              onChangeText={setNewUserEmail}
              placeholder="user@example.com"
              placeholderTextColor="#555"
              keyboardType="email-address"
              autoCapitalize="none"
            />
            
            <Text style={styles.modalLabel}>Name</Text>
            <TextInput
              style={styles.modalInput}
              value={newUserName}
              onChangeText={setNewUserName}
              placeholder="John Doe"
              placeholderTextColor="#555"
            />
            
            <Text style={styles.modalLabel}>Password</Text>
            <TextInput
              style={styles.modalInput}
              value={newUserPassword}
              onChangeText={setNewUserPassword}
              placeholder="••••••••"
              placeholderTextColor="#555"
              secureTextEntry
            />
            
            <Text style={styles.modalLabel}>Subscription Tier</Text>
            <View style={styles.tierSelector}>
              {['trial', 'bronze', 'silver', 'gold', 'subadmin'].map(tier => (
                <TouchableOpacity
                  key={tier}
                  style={[styles.tierOption, newUserTier === tier && { backgroundColor: TIER_COLORS[tier], borderColor: TIER_COLORS[tier] }]}
                  onPress={() => setNewUserTier(tier)}
                >
                  <Text style={[styles.tierOptionText, newUserTier === tier && styles.tierOptionTextActive]}>
                    {tier}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
            
            {/* Trial Duration - only show when trial is selected */}
            {newUserTier === 'trial' && (
              <View style={styles.trialDurationSection}>
                <Text style={styles.modalLabel}>Trial Duration</Text>
                <View style={styles.trialDurationSelector}>
                  {['3', '7', '14', '30', '60'].map(days => (
                    <TouchableOpacity
                      key={days}
                      style={[styles.trialDayOption, newUserTrialDays === days && styles.trialDayOptionActive]}
                      onPress={() => setNewUserTrialDays(days)}
                    >
                      <Text style={[styles.trialDayText, newUserTrialDays === days && styles.trialDayTextActive]}>
                        {days}d
                      </Text>
                    </TouchableOpacity>
                  ))}
                </View>
                <Text style={styles.trialDurationHint}>Trial will expire in {newUserTrialDays} days</Text>
              </View>
            )}
            
            <TouchableOpacity style={styles.createUserBtn} onPress={addNewUser} disabled={addingUser}>
              {addingUser ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <>
                  <Ionicons name="person-add" size={18} color="#fff" />
                  <Text style={styles.createUserBtnText}>Create User</Text>
                </>
              )}
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
      
      {/* Edit User Role Modal */}
      <Modal visible={showEditUserModal} transparent animationType="fade" onRequestClose={() => setShowEditUserModal(false)}>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Edit User Access</Text>
              <TouchableOpacity onPress={() => setShowEditUserModal(false)}>
                <Ionicons name="close" size={24} color="#888" />
              </TouchableOpacity>
            </View>
            
            {editingUser && (
              <>
                <View style={styles.editUserInfo}>
                  <Text style={styles.editUserName}>{editingUser.name}</Text>
                  <Text style={styles.editUserEmail}>{editingUser.email}</Text>
                  <View style={[styles.currentTierBadge, { backgroundColor: TIER_COLORS[editingUser.subscription_tier] || '#888' }]}>
                    <Text style={styles.currentTierText}>Current: {editingUser.subscription_tier}</Text>
                  </View>
                </View>
                
                <Text style={styles.modalLabel}>Change Subscription Tier</Text>
                <View style={styles.tierSelector}>
                  {['trial', 'bronze', 'silver', 'gold', 'subadmin'].map(tier => (
                    <TouchableOpacity
                      key={tier}
                      style={[styles.tierOption, editUserTier === tier && { backgroundColor: TIER_COLORS[tier], borderColor: TIER_COLORS[tier] }]}
                      onPress={() => setEditUserTier(tier)}
                    >
                      <Text style={[styles.tierOptionText, editUserTier === tier && styles.tierOptionTextActive]}>
                        {tier}
                      </Text>
                    </TouchableOpacity>
                  ))}
                </View>
                
                {editUserTier !== editingUser.subscription_tier && (
                  <View style={styles.tierChangeWarning}>
                    <Ionicons name="information-circle" size={16} color="#FF9800" />
                    <Text style={styles.tierChangeWarningText}>
                      Changing from {editingUser.subscription_tier} → {editUserTier}
                    </Text>
                  </View>
                )}
                
                <View style={styles.editUserButtons}>
                  <TouchableOpacity style={styles.cancelBtn} onPress={() => setShowEditUserModal(false)}>
                    <Text style={styles.cancelBtnText}>Cancel</Text>
                  </TouchableOpacity>
                  <TouchableOpacity 
                    style={[styles.saveRoleBtn, editUserTier === editingUser.subscription_tier && styles.saveRoleBtnDisabled]} 
                    onPress={saveUserRole}
                    disabled={savingUserRole || editUserTier === editingUser.subscription_tier}
                  >
                    {savingUserRole ? (
                      <ActivityIndicator color="#fff" size="small" />
                    ) : (
                      <>
                        <Ionicons name="checkmark" size={18} color="#fff" />
                        <Text style={styles.saveRoleBtnText}>Save Changes</Text>
                      </>
                    )}
                  </TouchableOpacity>
                </View>
              </>
            )}
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#121212' },
  centered: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 20 },
  
  header: { flexDirection: 'row', alignItems: 'center', padding: 16, borderBottomWidth: 1, borderBottomColor: '#222' },
  backBtn: { padding: 4 },
  headerTitle: { flex: 1, fontSize: 20, fontWeight: 'bold', color: '#fff', textAlign: 'center' },
  adminBadge: { backgroundColor: 'rgba(244,67,54,0.15)', padding: 8, borderRadius: 20 },
  
  tabs: { flexDirection: 'row', backgroundColor: '#1a1a1a', paddingVertical: 4, paddingHorizontal: 8 },
  tab: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', paddingVertical: 12, gap: 6, borderRadius: 8 },
  tabActive: { backgroundColor: 'rgba(76,175,80,0.15)' },
  tabText: { fontSize: 14, color: '#888', fontWeight: '500' },
  tabTextActive: { color: '#4CAF50' },
  tabPill: { flexDirection: 'row', alignItems: 'center', gap: 4, paddingHorizontal: 12, paddingVertical: 8, borderRadius: 20, backgroundColor: '#252525', borderWidth: 1, borderColor: '#333' },
  tabPillActive: { backgroundColor: '#4CAF50', borderColor: '#4CAF50' },
  tabPillText: { fontSize: 11, color: '#888', fontWeight: '600' },
  tabPillTextActive: { color: '#fff' },
  
  scrollView: { flex: 1 },
  scrollContent: { padding: 16, paddingBottom: 40 },
  
  sectionTitle: { fontSize: 16, fontWeight: '600', color: '#fff', marginBottom: 12 },
  hint: { fontSize: 12, color: '#888', marginBottom: 16 },
  
  tierCard: { backgroundColor: '#1a1a1a', borderRadius: 12, padding: 16, marginBottom: 12, borderLeftWidth: 4 },
  featuresSection: { marginTop: 12, paddingTop: 12, borderTopWidth: 1, borderTopColor: '#333' },
  featuresTitle: { fontSize: 13, fontWeight: '700', color: '#aaa', marginBottom: 8, textTransform: 'uppercase', letterSpacing: 1 },
  featureRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 6 },
  featureLabel: { fontSize: 13, color: '#ccc' },
  tierHeader: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 12 },
  tierName: { fontSize: 18, fontWeight: '700' },
  tierFields: { flexDirection: 'row', flexWrap: 'wrap', gap: 12 },
  field: { flex: 1 },
  fieldLabel: { fontSize: 11, color: '#888', marginBottom: 4 },
  input: { backgroundColor: '#252525', borderRadius: 8, padding: 12, fontSize: 14, color: '#fff', borderWidth: 1, borderColor: '#333' },
  
  paymentCard: { backgroundColor: '#1a1a1a', borderRadius: 12, padding: 16 },
  paymentRow: { flexDirection: 'row', alignItems: 'center', gap: 12, marginBottom: 16 },
  paymentField: { flex: 1 },
  cashAppIcon: { width: 24, height: 24, backgroundColor: '#00D632', borderRadius: 4, justifyContent: 'center', alignItems: 'center' },
  cashAppText: { color: '#fff', fontWeight: '800', fontSize: 14 },
  
  saveBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', backgroundColor: '#4CAF50', borderRadius: 12, padding: 16, marginTop: 20, gap: 8 },
  saveBtnDisabled: { backgroundColor: '#333' },
  saveBtnText: { color: '#fff', fontSize: 16, fontWeight: '600' },
  
  userCard: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#1a1a1a', borderRadius: 12, padding: 14, marginBottom: 10, borderLeftWidth: 4 },
  userInfo: { flex: 1 },
  userName: { fontSize: 15, fontWeight: '600', color: '#fff' },
  userEmail: { fontSize: 12, color: '#888', marginTop: 2 },
  userTierBadge: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 12, marginRight: 8 },
  userTierText: { fontSize: 11, fontWeight: '700', color: '#000', textTransform: 'capitalize' },
  deleteUserBtn: { padding: 8 },
  
  // Users section header
  usersSectionHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
  addUserBtn: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#4CAF50', borderRadius: 8, paddingVertical: 8, paddingHorizontal: 12, gap: 6 },
  addUserBtnText: { color: '#fff', fontWeight: '600', fontSize: 13 },
  
  // Modal styles
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.8)', justifyContent: 'center', alignItems: 'center', padding: 20 },
  modalContent: { backgroundColor: '#1a1a1a', borderRadius: 16, padding: 20, width: '100%', maxWidth: 360 },
  modalHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 },
  modalTitle: { fontSize: 20, fontWeight: 'bold', color: '#fff' },
  modalLabel: { fontSize: 12, color: '#888', marginBottom: 6, marginTop: 12 },
  modalInput: { backgroundColor: '#252525', borderRadius: 8, padding: 12, fontSize: 14, color: '#fff', borderWidth: 1, borderColor: '#333' },
  tierSelector: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 4 },
  tierOption: { paddingHorizontal: 12, paddingVertical: 8, borderRadius: 8, borderWidth: 1, borderColor: '#444', backgroundColor: '#252525' },
  tierOptionText: { fontSize: 12, color: '#888', textTransform: 'capitalize' },
  tierOptionTextActive: { color: '#000', fontWeight: '600' },
  createUserBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', backgroundColor: '#4CAF50', borderRadius: 12, padding: 14, marginTop: 20, gap: 8 },
  createUserBtnText: { color: '#fff', fontSize: 16, fontWeight: '600' },
  
  accessDenied: { fontSize: 24, fontWeight: 'bold', color: '#f44336', marginTop: 16 },
  accessDeniedSub: { fontSize: 14, color: '#888', marginTop: 8 },
  loginBtn: { backgroundColor: '#4CAF50', paddingHorizontal: 24, paddingVertical: 12, borderRadius: 8, marginTop: 20 },
  loginBtnText: { color: '#fff', fontWeight: '600' },
  
  // Designs styles
  designCard: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#1a1a1a', borderRadius: 12, padding: 14, marginBottom: 10, borderLeftWidth: 4, borderLeftColor: '#FF9800' },
  designInfo: { flex: 1 },
  designName: { fontSize: 15, fontWeight: '600', color: '#fff' },
  designMeta: { fontSize: 11, color: '#4CAF50', marginTop: 2 },
  designDate: { fontSize: 10, color: '#666', marginTop: 2 },
  deleteDesignBtn: { padding: 10 },
  emptyDesigns: { alignItems: 'center', justifyContent: 'center', paddingVertical: 40 },
  emptyDesignsText: { color: '#666', fontSize: 14, marginTop: 12 },
  
  // Trial Duration styles
  trialDurationSection: { marginTop: 8, marginBottom: 8, padding: 10, backgroundColor: 'rgba(156,39,176,0.1)', borderRadius: 8, borderWidth: 1, borderColor: 'rgba(156,39,176,0.3)' },
  trialDurationSelector: { flexDirection: 'row', gap: 8, marginTop: 8 },
  trialDayOption: { flex: 1, paddingVertical: 10, backgroundColor: '#252525', borderRadius: 8, borderWidth: 1, borderColor: '#333', alignItems: 'center' },
  trialDayOptionActive: { backgroundColor: '#9C27B0', borderColor: '#9C27B0' },
  trialDayText: { fontSize: 13, color: '#888', fontWeight: '600' },
  trialDayTextActive: { color: '#fff' },
  trialDurationHint: { fontSize: 10, color: '#9C27B0', marginTop: 8, textAlign: 'center' },
  
  // Edit User Modal styles
  editUserInfo: { alignItems: 'center', marginBottom: 20, padding: 16, backgroundColor: '#1a1a1a', borderRadius: 12 },
  editUserName: { fontSize: 18, fontWeight: '600', color: '#fff' },
  editUserEmail: { fontSize: 13, color: '#888', marginTop: 4 },
  currentTierBadge: { paddingHorizontal: 12, paddingVertical: 6, borderRadius: 12, marginTop: 10 },
  currentTierText: { fontSize: 11, color: '#fff', fontWeight: '600', textTransform: 'capitalize' },
  tierChangeWarning: { flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 12, padding: 10, backgroundColor: 'rgba(255,152,0,0.1)', borderRadius: 8 },
  tierChangeWarningText: { fontSize: 12, color: '#FF9800' },
  editUserButtons: { flexDirection: 'row', gap: 12, marginTop: 20 },
  cancelBtn: { flex: 1, padding: 14, backgroundColor: '#333', borderRadius: 12, alignItems: 'center' },
  cancelBtnText: { fontSize: 14, color: '#888', fontWeight: '600' },
  saveRoleBtn: { flex: 2, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6, padding: 14, backgroundColor: '#4CAF50', borderRadius: 12 },
  saveRoleBtnDisabled: { backgroundColor: '#333' },
  saveRoleBtnText: { fontSize: 14, color: '#fff', fontWeight: '600' },
});
