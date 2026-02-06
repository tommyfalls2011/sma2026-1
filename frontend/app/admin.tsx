import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ScrollView, TextInput, ActivityIndicator, Alert, RefreshControl, Modal, Platform } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useAuth } from './context/AuthContext';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL || '';

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
  bronze: { price: number; max_elements: number };
  silver: { price: number; max_elements: number };
  gold: { price: number; max_elements: number };
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
  const [activeTab, setActiveTab] = useState<'pricing' | 'users' | 'designs'>('pricing');
  
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
        setBronzePrice(data.bronze.price.toString());
        setBronzeElements(data.bronze.max_elements.toString());
        setSilverPrice(data.silver.price.toString());
        setSilverElements(data.silver.max_elements.toString());
        setGoldPrice(data.gold.price.toString());
        setGoldElements(data.gold.max_elements.toString());
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
          bronze_price: parseFloat(bronzePrice),
          bronze_max_elements: parseInt(bronzeElements),
          silver_price: parseFloat(silverPrice),
          silver_max_elements: parseInt(silverElements),
          gold_price: parseFloat(goldPrice),
          gold_max_elements: parseInt(goldElements)
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
      <View style={styles.tabs}>
        <TouchableOpacity
          style={[styles.tab, activeTab === 'pricing' && styles.tabActive]}
          onPress={() => setActiveTab('pricing')}
        >
          <Ionicons name="pricetag" size={16} color={activeTab === 'pricing' ? '#4CAF50' : '#888'} />
          <Text style={[styles.tabText, activeTab === 'pricing' && styles.tabTextActive]}>Pricing</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.tab, activeTab === 'users' && styles.tabActive]}
          onPress={() => setActiveTab('users')}
        >
          <Ionicons name="people" size={16} color={activeTab === 'users' ? '#4CAF50' : '#888'} />
          <Text style={[styles.tabText, activeTab === 'users' && styles.tabTextActive]}>Users</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.tab, activeTab === 'designs' && styles.tabActive]}
          onPress={() => setActiveTab('designs')}
        >
          <Ionicons name="save" size={16} color={activeTab === 'designs' ? '#FF9800' : '#888'} />
          <Text style={[styles.tabText, activeTab === 'designs' && styles.tabTextActive]}>Designs</Text>
        </TouchableOpacity>
      </View>

      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#4CAF50" />}
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
                  <Text style={styles.fieldLabel}>Price (one-time)</Text>
                  <TextInput
                    style={styles.input}
                    value={bronzePrice}
                    onChangeText={setBronzePrice}
                    keyboardType="decimal-pad"
                    placeholder="29.99"
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
            </View>

            {/* Silver */}
            <View style={[styles.tierCard, { borderLeftColor: TIER_COLORS.silver }]}>
              <View style={styles.tierHeader}>
                <Ionicons name="shield-half-outline" size={20} color={TIER_COLORS.silver} />
                <Text style={[styles.tierName, { color: TIER_COLORS.silver }]}>Silver</Text>
              </View>
              <View style={styles.tierFields}>
                <View style={styles.field}>
                  <Text style={styles.fieldLabel}>Price (one-time)</Text>
                  <TextInput
                    style={styles.input}
                    value={silverPrice}
                    onChangeText={setSilverPrice}
                    keyboardType="decimal-pad"
                    placeholder="49.99"
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
            </View>

            {/* Gold */}
            <View style={[styles.tierCard, { borderLeftColor: TIER_COLORS.gold }]}>
              <View style={styles.tierHeader}>
                <Ionicons name="shield-checkmark" size={20} color={TIER_COLORS.gold} />
                <Text style={[styles.tierName, { color: TIER_COLORS.gold }]}>Gold</Text>
              </View>
              <View style={styles.tierFields}>
                <View style={styles.field}>
                  <Text style={styles.fieldLabel}>Price (one-time)</Text>
                  <TextInput
                    style={styles.input}
                    value={goldPrice}
                    onChangeText={setGoldPrice}
                    keyboardType="decimal-pad"
                    placeholder="69.99"
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
  
  scrollView: { flex: 1 },
  scrollContent: { padding: 16, paddingBottom: 40 },
  
  sectionTitle: { fontSize: 16, fontWeight: '600', color: '#fff', marginBottom: 12 },
  hint: { fontSize: 12, color: '#888', marginBottom: 16 },
  
  tierCard: { backgroundColor: '#1a1a1a', borderRadius: 12, padding: 16, marginBottom: 12, borderLeftWidth: 4 },
  tierHeader: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 12 },
  tierName: { fontSize: 18, fontWeight: '700' },
  tierFields: { flexDirection: 'row', gap: 12 },
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
