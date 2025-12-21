import React, { createContext, useContext, useState, useEffect } from 'react';
import { 
  createUserWithEmailAndPassword, 
  signInWithEmailAndPassword, 
  signOut, 
  onAuthStateChanged,
  sendPasswordResetEmail
} from 'firebase/auth';
import { auth } from '../utils/firebase';

// Create the authentication context
const AuthContext = createContext();

// Hook to use the auth context
export function useAuth() {
  return useContext(AuthContext);
}

// Provider component that wraps the app and provides auth context
export function AuthProvider({ children }) {
  const [currentUser, setCurrentUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Function to sign up a user
  async function signup(email, password) {
    try {
      setError('');
      console.log('[AuthContext] signup:start', { email });
      return await createUserWithEmailAndPassword(auth, email, password);
    } catch (error) {
      setError(error.message);
      console.error("Signup error:", error);
      throw error;
    }
  }

  // Function to log in a user
  async function login(email, password) {
    try {
      setError('');
      console.log('[AuthContext] login:start', { email });
      return await signInWithEmailAndPassword(auth, email, password);
    } catch (error) {
      setError(error.message);
      console.error("Login error:", error);
      throw error;
    }
  }

  // Function to log out a user
  async function logout() {
    try {
      setError('');
      console.log('[AuthContext] logout:start');
      return await signOut(auth);
    } catch (error) {
      setError(error.message);
      console.error("Logout error:", error);
      throw error;
    }
  }

  // Function to reset password
  async function resetPassword(email) {
    try {
      setError('');
      console.log('[AuthContext] resetPassword:start', { email });
      return await sendPasswordResetEmail(auth, email);
    } catch (error) {
      setError(error.message);
      console.error("Password reset error:", error);
      throw error;
    }
  }

  // Set up an observer for changes to the user's sign-in state
  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (user) => {
      console.log('[AuthContext] onAuthStateChanged', {
        hasUser: !!user,
        email: user?.email || null,
        uidPrefix: user?.uid ? user.uid.slice(0, 8) : null
      });
      setCurrentUser(user);
      setLoading(false);
    });

    // Clean up the observer when component unmounts
    return unsubscribe;
  }, []);

  // Value to be provided by the context
  const value = {
    currentUser,
    error,
    signup,
    login,
    logout,
    resetPassword
  };

  return (
    <AuthContext.Provider value={value}>
      {!loading && children}
    </AuthContext.Provider>
  );
}
