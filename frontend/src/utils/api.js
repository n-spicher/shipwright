import { auth } from './firebase';

// API Configuration
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8010';

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
