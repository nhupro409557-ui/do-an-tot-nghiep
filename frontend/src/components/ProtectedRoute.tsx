import React from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export const ProtectedRoute = ({ adminOnly = false }: { adminOnly?: boolean }) => {
  const { user, canAccessAdmin, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="w-8 h-8 rounded-full border-4 border-[#d70018] border-t-transparent animate-spin"></div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to={adminOnly ? '/admin/login' : '/login'} replace />;
  }

  if (adminOnly && !canAccessAdmin) {
    return <Navigate to="/admin/login" replace />;
  }

  return <Outlet />;
};
