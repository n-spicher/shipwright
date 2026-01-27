import { auth } from './firebase';

// API Configuration
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';
console.log('[API] Base URL configured:', API_BASE_URL);

const createRequestId = () => {
  try {
    if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
      return crypto.randomUUID();
    }
  } catch (e) {
    // ignore
  }
  return `req_${Date.now()}_${Math.random().toString(16).slice(2)}`;
};

/**
 * Get authentication headers with Firebase ID token
 * @returns {Promise<Object>} Headers object with Authorization and Content-Type
 */
export const getAuthHeaders = async () => {
  const currentUser = auth.currentUser;
  
  if (!currentUser) {
    console.error('[API] No current user found');
    throw new Error('User not authenticated');
  }
  try {
    console.log('[API] Getting Firebase ID token for user:', currentUser.email);
    const idToken = await currentUser.getIdToken();
    console.log('[API] Successfully obtained ID token', { tokenLength: idToken?.length || 0 });
    
    return {
      'Authorization': `Bearer ${idToken}`,
      'Content-Type': 'application/json',
    };
  } catch (error) {
    console.error('[API] Error getting ID token:', error);
    throw new Error('Failed to get authentication token');
  }
};

/**
 * Send a chat message to the backend
 * @param {string} message - User message
 * @param {string} mode - Chat mode (GC, MC, EC, or NONE)
 * @returns {Promise<{response: string, chunks: Array, applicable_keywords: Array}>}
 */
export const sendChatMessage = async (message, mode = 'NONE') => {
  const requestId = createRequestId();
  const startMs = performance.now();
  console.log('[API] sendChatMessage:start', { requestId, mode, messageLength: message?.length || 0 });
  
  try {
    const headers = await getAuthHeaders();
    headers['X-Request-ID'] = requestId;
    
    const response = await fetch(`${API_BASE_URL}/ask`, {
      method: 'POST',
      headers: headers,
      body: JSON.stringify({
        message: message,
        mode: mode,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      console.error('[API] sendChatMessage:error', { requestId, status: response.status, errorData });
      throw new Error(errorData.detail || 'Failed to send message');
    }

    const data = await response.json();
    console.log('[API] sendChatMessage:success', {
      requestId,
      status: response.status,
      durationMs: Math.round(performance.now() - startMs),
      hasResponseText: !!data?.response,
      responseLength: data?.response?.length || 0
    });
    return data;
  } catch (error) {
    console.error('[API] sendChatMessage:exception', { requestId, error });
    throw error;
  }
};

// ============================================================================
// PROFILE API FUNCTIONS
// ============================================================================

/**
 * Get the current user's profile
 * @returns {Promise<Object>} User profile data
 */
export const getUserProfile = async () => {
  console.log('[API] getUserProfile: fetching from', `${API_BASE_URL}/users/me`);
  const headers = await getAuthHeaders();
  
  const response = await fetch(`${API_BASE_URL}/users/me`, {
    method: 'GET',
    headers: headers,
  });

  console.log('[API] getUserProfile: response status', response.status);
  
  if (!response.ok) {
    const errorData = await response.json();
    const detail = typeof errorData.detail === 'string' 
      ? errorData.detail 
      : Array.isArray(errorData.detail) 
        ? errorData.detail.map(e => e.msg || e.message || JSON.stringify(e)).join(', ')
        : 'Failed to get profile';
    console.error('[API] getUserProfile: error', detail);
    throw new Error(detail);
  }

  const data = await response.json();
  console.log('[API] getUserProfile: success', data);
  return data;
};

/**
 * Update the current user's profile
 * @param {Object} profileData - Profile data to update
 * @returns {Promise<Object>} Updated user profile
 */
export const updateUserProfile = async (profileData) => {
  const headers = await getAuthHeaders();
  
  const response = await fetch(`${API_BASE_URL}/users/me`, {
    method: 'PUT',
    headers: headers,
    body: JSON.stringify(profileData),
  });

  if (!response.ok) {
    const errorData = await response.json();
    const detail = typeof errorData.detail === 'string' 
      ? errorData.detail 
      : Array.isArray(errorData.detail) 
        ? errorData.detail.map(e => e.msg || e.message || JSON.stringify(e)).join(', ')
        : 'Failed to update profile';
    throw new Error(detail);
  }

  return response.json();
};

/**
 * Delete the current user's account (soft delete)
 * @returns {Promise<Object>} Deletion confirmation
 */
export const deleteUserAccount = async () => {
  const headers = await getAuthHeaders();
  
  const response = await fetch(`${API_BASE_URL}/users/me`, {
    method: 'DELETE',
    headers: headers,
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || 'Failed to delete account');
  }

  return response.json();
};

// ============================================================================
// SUBSCRIPTION API FUNCTIONS
// ============================================================================

/**
 * Get all available subscription tiers
 * @returns {Promise<Array>} List of subscription tiers
 */
export const getSubscriptionTiers = async () => {
  const headers = await getAuthHeaders();
  
  const response = await fetch(`${API_BASE_URL}/subscription/tiers`, {
    method: 'GET',
    headers: headers,
  });

  if (!response.ok) {
    const errorData = await response.json();
    const detail = typeof errorData.detail === 'string' 
      ? errorData.detail 
      : Array.isArray(errorData.detail) 
        ? errorData.detail.map(e => e.msg || e.message || JSON.stringify(e)).join(', ')
        : 'Failed to get subscription tiers';
    throw new Error(detail);
  }

  return response.json();
};

/**
 * Get the current user's subscription status
 * @returns {Promise<Object>} Subscription status
 */
export const getSubscriptionStatus = async () => {
  const headers = await getAuthHeaders();
  
  const response = await fetch(`${API_BASE_URL}/subscription/status`, {
    method: 'GET',
    headers: headers,
  });

  if (!response.ok) {
    const errorData = await response.json();
    const detail = typeof errorData.detail === 'string' 
      ? errorData.detail 
      : Array.isArray(errorData.detail) 
        ? errorData.detail.map(e => e.msg || e.message || JSON.stringify(e)).join(', ')
        : 'Failed to get subscription status';
    throw new Error(detail);
  }

  return response.json();
};

/**
 * Create a Stripe checkout session for subscription upgrade
 * @param {string} tier - Target subscription tier
 * @returns {Promise<Object>} Checkout session with URL
 */
export const createCheckoutSession = async (tier) => {
  const headers = await getAuthHeaders();
  
  const response = await fetch(`${API_BASE_URL}/subscription/create-checkout-session?tier=${tier}`, {
    method: 'POST',
    headers: headers,
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || 'Failed to create checkout session');
  }

  return response.json();
};

/**
 * Create a Stripe customer portal session for managing billing
 * @returns {Promise<Object>} Portal session with URL
 */
export const createPortalSession = async () => {
  const headers = await getAuthHeaders();
  
  const response = await fetch(`${API_BASE_URL}/subscription/create-portal-session`, {
    method: 'POST',
    headers: headers,
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || 'Failed to create portal session');
  }

  return response.json();
};

/**
 * Cancel the current subscription
 * @returns {Promise<Object>} Cancellation confirmation
 */
export const cancelSubscription = async () => {
  const headers = await getAuthHeaders();
  
  const response = await fetch(`${API_BASE_URL}/subscription/cancel`, {
    method: 'POST',
    headers: headers,
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || 'Failed to cancel subscription');
  }

  return response.json();
};
