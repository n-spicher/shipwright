import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { 
  getUserProfile, 
  updateUserProfile, 
  deleteUserAccount,
  getSubscriptionTiers,
  getSubscriptionStatus,
  createCheckoutSession,
  createPortalSession,
  cancelSubscription
} from '../utils/api';

const ProfileSetup = () => {
  const { currentUser, updateEmail, updatePassword, logout } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  
  // Profile state
  const [profile, setProfile] = useState({
    firstName: '',
    lastName: '',
    companyName: '',
    email: ''
  });
  const [profileLoading, setProfileLoading] = useState(true);
  const [profileSaving, setProfileSaving] = useState(false);
  
  // Password state
  const [passwords, setPasswords] = useState({
    current: '',
    new: '',
    confirm: ''
  });
  const [passwordChanging, setPasswordChanging] = useState(false);
  
  // Subscription state
  const [subscriptionTiers, setSubscriptionTiers] = useState([]);
  const [subscriptionStatus, setSubscriptionStatus] = useState(null);
  const [subscriptionLoading, setSubscriptionLoading] = useState(true);
  
  // UI state
  const [activeSection, setActiveSection] = useState('profile');
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleteConfirmText, setDeleteConfirmText] = useState('');
  const [deleting, setDeleting] = useState(false);

  // Check for Stripe redirect params
  useEffect(() => {
    if (searchParams.get('success') === 'true') {
      setSuccessMessage('Subscription activated successfully!');
      setActiveSection('subscription');
      // Refresh subscription status
      loadSubscriptionData();
    } else if (searchParams.get('canceled') === 'true') {
      setErrorMessage('Subscription checkout was canceled.');
      setActiveSection('subscription');
    }
  }, [searchParams]);

  // Load profile data
  useEffect(() => {
    loadProfileData();
    loadSubscriptionData();
  }, []);

  const loadProfileData = async () => {
    try {
      setProfileLoading(true);
      const data = await getUserProfile();
      setProfile({
        firstName: data.first_name || '',
        lastName: data.last_name || '',
        companyName: data.company_name || '',
        email: data.email || currentUser?.email || ''
      });
    } catch (error) {
      console.error('Error loading profile:', error);
      setErrorMessage('Failed to load profile data');
    } finally {
      setProfileLoading(false);
    }
  };

  const loadSubscriptionData = async () => {
    try {
      setSubscriptionLoading(true);
      const [tiers, status] = await Promise.all([
        getSubscriptionTiers(),
        getSubscriptionStatus()
      ]);
      setSubscriptionTiers(tiers);
      setSubscriptionStatus(status);
    } catch (error) {
      console.error('Error loading subscription data:', error);
    } finally {
      setSubscriptionLoading(false);
    }
  };

  const handleProfileChange = (e) => {
    const { name, value } = e.target;
    setProfile(prev => ({ ...prev, [name]: value }));
  };

  const handlePasswordChange = (e) => {
    const { name, value } = e.target;
    setPasswords(prev => ({ ...prev, [name]: value }));
  };

  const handleProfileSubmit = async (e) => {
    e.preventDefault();
    setErrorMessage('');
    setSuccessMessage('');
    
    try {
      setProfileSaving(true);
      
      // Update profile in backend
      await updateUserProfile({
        first_name: profile.firstName,
        last_name: profile.lastName,
        company_name: profile.companyName
      });
      
      // If email changed, update in Firebase first
      if (profile.email !== currentUser?.email) {
        await updateEmail(profile.email);
        // Then update in backend
        await updateUserProfile({ email: profile.email });
      }
      
      setSuccessMessage('Profile updated successfully');
      setTimeout(() => setSuccessMessage(''), 5000);
    } catch (error) {
      console.error('Error updating profile:', error);
      setErrorMessage(error.message || 'Failed to update profile');
      setTimeout(() => setErrorMessage(''), 5000);
    } finally {
      setProfileSaving(false);
    }
  };

  const handlePasswordSubmit = async (e) => {
    e.preventDefault();
    setErrorMessage('');
    setSuccessMessage('');
    
    if (passwords.new !== passwords.confirm) {
      setErrorMessage('New passwords do not match');
      return;
    }
    
    if (passwords.new.length < 6) {
      setErrorMessage('Password must be at least 6 characters');
      return;
    }
    
    try {
      setPasswordChanging(true);
      await updatePassword(passwords.new);
      setPasswords({ current: '', new: '', confirm: '' });
      setSuccessMessage('Password updated successfully');
      setTimeout(() => setSuccessMessage(''), 5000);
    } catch (error) {
      console.error('Error updating password:', error);
      setErrorMessage(error.message || 'Failed to update password');
      setTimeout(() => setErrorMessage(''), 5000);
    } finally {
      setPasswordChanging(false);
    }
  };

  const handleUpgrade = async (tier) => {
    try {
      setErrorMessage('');
      const { checkout_url } = await createCheckoutSession(tier);
      window.location.href = checkout_url;
    } catch (error) {
      console.error('Error creating checkout session:', error);
      setErrorMessage(error.message || 'Failed to start checkout');
      setTimeout(() => setErrorMessage(''), 5000);
    }
  };

  const handleManageBilling = async () => {
    try {
      setErrorMessage('');
      const { portal_url } = await createPortalSession();
      window.location.href = portal_url;
    } catch (error) {
      console.error('Error creating portal session:', error);
      setErrorMessage(error.message || 'Failed to open billing portal');
      setTimeout(() => setErrorMessage(''), 5000);
    }
  };

  const handleCancelSubscription = async () => {
    try {
      setErrorMessage('');
      await cancelSubscription();
      setSuccessMessage('Subscription will be canceled at the end of the billing period');
      loadSubscriptionData();
      setTimeout(() => setSuccessMessage(''), 5000);
    } catch (error) {
      console.error('Error canceling subscription:', error);
      setErrorMessage(error.message || 'Failed to cancel subscription');
      setTimeout(() => setErrorMessage(''), 5000);
    }
  };

  const handleDeleteAccount = async () => {
    if (deleteConfirmText !== 'DELETE') {
      setErrorMessage('Please type DELETE to confirm');
      return;
    }
    
    try {
      setDeleting(true);
      await deleteUserAccount();
      await logout();
      navigate('/login');
    } catch (error) {
      console.error('Error deleting account:', error);
      setErrorMessage(error.message || 'Failed to delete account');
      setDeleting(false);
    }
  };

  const getTierBadgeColor = (tier) => {
    switch (tier) {
      case 'pro': return 'bg-blue-500';
      case 'enterprise': return 'bg-purple-500';
      default: return 'bg-gray-500';
    }
  };

  const renderProfileSection = () => (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-white">Profile Information</h2>
      
      <form onSubmit={handleProfileSubmit} className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              First Name
            </label>
            <input
              type="text"
              name="firstName"
              value={profile.firstName}
              onChange={handleProfileChange}
              className="w-full p-3 bg-gray-700 border border-gray-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Enter first name"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              Last Name
            </label>
            <input
              type="text"
              name="lastName"
              value={profile.lastName}
              onChange={handleProfileChange}
              className="w-full p-3 bg-gray-700 border border-gray-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Enter last name"
            />
          </div>
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">
            Company Name
          </label>
          <input
            type="text"
            name="companyName"
            value={profile.companyName}
            onChange={handleProfileChange}
            className="w-full p-3 bg-gray-700 border border-gray-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="Enter company name"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">
            Email Address
          </label>
          <input
            type="email"
            name="email"
            value={profile.email}
            onChange={handleProfileChange}
            className="w-full p-3 bg-gray-700 border border-gray-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="Enter email"
          />
          <p className="mt-1 text-xs text-gray-400">
            Changing your email will update your login credentials
          </p>
        </div>
        
        <button
          type="submit"
          disabled={profileSaving}
          className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
        >
          {profileSaving ? 'Saving...' : 'Save Changes'}
        </button>
      </form>
    </div>
  );

  const renderPasswordSection = () => (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-white">Change Password</h2>
      
      <form onSubmit={handlePasswordSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">
            New Password
          </label>
          <input
            type="password"
            name="new"
            value={passwords.new}
            onChange={handlePasswordChange}
            className="w-full p-3 bg-gray-700 border border-gray-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="Enter new password"
            minLength={6}
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">
            Confirm New Password
          </label>
          <input
            type="password"
            name="confirm"
            value={passwords.confirm}
            onChange={handlePasswordChange}
            className="w-full p-3 bg-gray-700 border border-gray-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="Confirm new password"
            minLength={6}
          />
        </div>
        
        <button
          type="submit"
          disabled={passwordChanging || !passwords.new || !passwords.confirm}
          className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
        >
          {passwordChanging ? 'Updating...' : 'Update Password'}
        </button>
      </form>
    </div>
  );

  const renderSubscriptionSection = () => (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-white">Subscription</h2>
      
      {/* Current Plan */}
      {subscriptionStatus && (
        <div className="bg-gray-700 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-400">Current Plan</p>
              <p className="text-lg font-semibold text-white flex items-center gap-2">
                {subscriptionTiers.find(t => t.tier === subscriptionStatus.tier)?.name || 'Free'}
                <span className={`px-2 py-0.5 text-xs rounded-full ${getTierBadgeColor(subscriptionStatus.tier)}`}>
                  {subscriptionStatus.tier.toUpperCase()}
                </span>
              </p>
            </div>
            {subscriptionStatus.current_period_end && (
              <div className="text-right">
                <p className="text-sm text-gray-400">
                  {subscriptionStatus.cancel_at_period_end ? 'Cancels on' : 'Renews on'}
                </p>
                <p className="text-white">
                  {new Date(subscriptionStatus.current_period_end).toLocaleDateString()}
                </p>
              </div>
            )}
          </div>
          
          {subscriptionStatus.tier !== 'free' && (
            <div className="mt-4 flex gap-2">
              <button
                onClick={handleManageBilling}
                className="px-4 py-2 bg-gray-600 hover:bg-gray-500 text-white rounded-md text-sm"
              >
                Manage Billing
              </button>
              {!subscriptionStatus.cancel_at_period_end && (
                <button
                  onClick={handleCancelSubscription}
                  className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-md text-sm"
                >
                  Cancel Subscription
                </button>
              )}
            </div>
          )}
        </div>
      )}
      
      {/* Tier Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {subscriptionTiers.map((tier) => (
          <div 
            key={tier.tier}
            className={`bg-gray-700 rounded-lg p-4 border-2 ${
              subscriptionStatus?.tier === tier.tier 
                ? 'border-blue-500' 
                : 'border-transparent'
            }`}
          >
            <h3 className="text-lg font-bold text-white">{tier.name}</h3>
            <p className="text-2xl font-bold text-white mt-2">
              ${tier.price}<span className="text-sm text-gray-400">/month</span>
            </p>
            
            <ul className="mt-4 space-y-2">
              {tier.features.map((feature, idx) => (
                <li key={idx} className="text-sm text-gray-300 flex items-start gap-2">
                  <span className="text-green-400 mt-0.5">✓</span>
                  {feature}
                </li>
              ))}
            </ul>
            
            <div className="mt-4">
              {subscriptionStatus?.tier === tier.tier ? (
                <button
                  disabled
                  className="w-full px-4 py-2 bg-gray-500 text-white rounded-md cursor-not-allowed"
                >
                  Current Plan
                </button>
              ) : tier.tier === 'free' ? (
                subscriptionStatus?.tier !== 'free' && (
                  <button
                    onClick={handleCancelSubscription}
                    className="w-full px-4 py-2 bg-gray-600 hover:bg-gray-500 text-white rounded-md"
                  >
                    Downgrade
                  </button>
                )
              ) : (
                <button
                  onClick={() => handleUpgrade(tier.tier)}
                  className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md"
                >
                  {subscriptionStatus?.tier === 'free' ? 'Upgrade' : 'Switch Plan'}
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  const renderDangerZone = () => (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-red-400">Danger Zone</h2>
      
      <div className="bg-red-900/20 border border-red-500/50 rounded-lg p-4">
        <h3 className="text-lg font-semibold text-white">Delete Account</h3>
        <p className="text-sm text-gray-400 mt-1">
          Once you delete your account, you have 30 days to recover it. After that, all your data will be permanently deleted.
        </p>
        
        <button
          onClick={() => setShowDeleteModal(true)}
          className="mt-4 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-md"
        >
          Delete My Account
        </button>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-background text-white">
      {/* Header */}
      <header className="w-full p-4 border-b border-gray-700 flex justify-between items-center">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/dashboard')}
            className="text-gray-400 hover:text-white"
          >
            ← Back to Dashboard
          </button>
          <h1 className="text-xl font-bold">Settings</h1>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-400">
            {profile.firstName || currentUser?.email}
          </span>
          {subscriptionStatus && (
            <span className={`px-2 py-0.5 text-xs rounded-full ${getTierBadgeColor(subscriptionStatus.tier)}`}>
              {subscriptionStatus.tier.toUpperCase()}
            </span>
          )}
        </div>
      </header>

      {/* Alert Messages */}
      {errorMessage && (
        <div className="mx-4 mt-4 p-3 bg-red-900/50 border border-red-500 text-red-200 rounded-lg">
          {errorMessage}
        </div>
      )}
      
      {successMessage && (
        <div className="mx-4 mt-4 p-3 bg-green-900/50 border border-green-500 text-green-200 rounded-lg">
          {successMessage}
        </div>
      )}

      {/* Main Content */}
      <div className="flex flex-col md:flex-row max-w-6xl mx-auto p-4 gap-6">
        {/* Sidebar Navigation */}
        <div className="w-full md:w-64 shrink-0">
          <nav className="bg-gray-800 rounded-lg p-2 space-y-1">
            {[
              { id: 'profile', label: 'Profile' },
              { id: 'password', label: 'Password' },
              { id: 'subscription', label: 'Subscription' },
              { id: 'danger', label: 'Delete Account' }
            ].map((item) => (
              <button
                key={item.id}
                onClick={() => setActiveSection(item.id)}
                className={`w-full text-left px-4 py-2 rounded-md transition-colors ${
                  activeSection === item.id
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-300 hover:bg-gray-700'
                }`}
              >
                {item.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Content Area */}
        <div className="flex-1 bg-gray-800 rounded-lg p-6">
          {profileLoading || subscriptionLoading ? (
            <div className="flex justify-center items-center h-64">
              <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
            </div>
          ) : (
            <>
              {activeSection === 'profile' && renderProfileSection()}
              {activeSection === 'password' && renderPasswordSection()}
              {activeSection === 'subscription' && renderSubscriptionSection()}
              {activeSection === 'danger' && renderDangerZone()}
            </>
          )}
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      {showDeleteModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-xl font-bold text-white">Delete Account</h3>
            <p className="text-gray-400 mt-2">
              This action will schedule your account for deletion. You have 30 days to recover it.
            </p>
            
            <div className="mt-4">
              <label className="block text-sm text-gray-300 mb-2">
                Type <span className="font-bold text-red-400">DELETE</span> to confirm:
              </label>
              <input
                type="text"
                value={deleteConfirmText}
                onChange={(e) => setDeleteConfirmText(e.target.value)}
                className="w-full p-3 bg-gray-700 border border-gray-600 rounded-md text-white"
                placeholder="Type DELETE"
              />
            </div>
            
            <div className="mt-6 flex gap-3 justify-end">
              <button
                onClick={() => {
                  setShowDeleteModal(false);
                  setDeleteConfirmText('');
                }}
                className="px-4 py-2 bg-gray-600 hover:bg-gray-500 text-white rounded-md"
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteAccount}
                disabled={deleteConfirmText !== 'DELETE' || deleting}
                className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-md disabled:opacity-50"
              >
                {deleting ? 'Deleting...' : 'Delete Account'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ProfileSetup;
