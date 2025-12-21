import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const PrivateRoute = ({ children }) => {
  const { currentUser } = useAuth();
  
  // Check for development mode - this is for the bypass login feature
  const isDevelopment = process.env.NODE_ENV === 'development';
  
  // In development mode, we'll allow access even without login
  // In production, we'll require login
  return (isDevelopment || currentUser) ? children : <Navigate to="/login" />;
};

export default PrivateRoute;
