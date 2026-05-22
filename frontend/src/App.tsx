import React, { Suspense, lazy } from 'react';
import { BrowserRouter as Router, Routes, Route, useLocation } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { CartProvider } from './context/CartContext';
import { Header } from './components/layout/Header';
import { Footer } from './components/layout/Footer';
import { BottomNav } from './components/layout/BottomNav';
import { AIChatWidget } from './components/layout/AIChatWidget';
import { ErrorBoundary } from './ErrorBoundary';
import { ProtectedRoute } from './components/ProtectedRoute';

const HomePage = lazy(() => import('./pages/HomePage'));
const CategoryPage = lazy(() => import('./pages/CategoryPage'));
const ComparePage = lazy(() => import('./pages/ComparePage'));
const LoginPage = lazy(() => import('./pages/LoginPage'));
const RegisterPage = lazy(() => import('./pages/RegisterPage'));
const ForgotPasswordPage = lazy(() => import('./pages/ForgotPasswordPage'));
const ResetPasswordPage = lazy(() => import('./pages/ResetPasswordPage'));
const VerifyEmailPage = lazy(() => import('./pages/VerifyEmailPage'));
const DashboardPage = lazy(() => import('./pages/DashboardPage'));
const ChangePasswordPage = lazy(() => import('./pages/ChangePasswordPage'));
const LoyaltyRewardsPage = lazy(() => import('./pages/LoyaltyRewardsPage'));
const ProductPage = lazy(() => import('./pages/ProductPage'));
const ProductListPage = lazy(() => import('./pages/ProductListPage'));
const BrandLandingPage = lazy(() => import('./pages/BrandLandingPage'));
const CartPage = lazy(() => import('./pages/CartPage'));
const CheckoutPage = lazy(() => import('./pages/CheckoutPage'));
const VideoPage = lazy(() => import('./pages/VideoPage'));
const ImagesPage = lazy(() => import('./pages/ImagesPage'));
const RankingsPage = lazy(() => import('./pages/RankingsPage'));
const AdminDashboard = lazy(() => import('./pages/AdminDashboard'));
const AdminLoginPage = lazy(() => import('./pages/AdminLoginPage'));
const NotFoundPage = lazy(() => import('./pages/NotFoundPage'));
const PolicyPage = lazy(() => import('./pages/PolicyPage'));

export default function App() {
  return (
    <Router>
      <ErrorBoundary>
        <AuthProvider>
          <CartProvider>
            <AppShell />
          </CartProvider>
        </AuthProvider>
      </ErrorBoundary>
    </Router>
  );
}

function AppShell() {
  const location = useLocation();
  const isAdminArea = location.pathname === '/admin' || location.pathname.startsWith('/admin/');

  return (
    <div className="flex min-h-[100dvh] flex-col">
      {!isAdminArea && <Header />}
      <main className={`flex-1 bg-background text-slate-800 ${isAdminArea ? '' : 'px-3 sm:px-4 lg:px-6'}`}>
        <Suspense fallback={<div className="flex items-center justify-center p-20"><div className="h-8 w-8 animate-spin rounded-full border-4 border-[#d70018] border-t-transparent"></div></div>}>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/video" element={<VideoPage />} />
            <Route path="/images" element={<ImagesPage />} />
            <Route path="/rankings" element={<RankingsPage />} />
            <Route path="/category" element={<CategoryPage />} />
            <Route path="/category/:categoryName" element={<CategoryPage />} />
            <Route path="/products" element={<ProductListPage />} />
            <Route path="/search" element={<ProductListPage />} />
            <Route path="/products/:categoryName" element={<ProductListPage />} />
            <Route path="/brands/:slug" element={<BrandLandingPage />} />
            <Route path="/compare" element={<ComparePage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/forgot-password" element={<ForgotPasswordPage />} />
            <Route path="/reset-password" element={<ResetPasswordPage />} />
            <Route path="/verify-email" element={<VerifyEmailPage />} />
            <Route path="/product/:id" element={<ProductPage />} />
            <Route path="/cart" element={<CartPage />} />
            <Route path="/policy" element={<PolicyPage />} />
            <Route path="/admin/login" element={<AdminLoginPage />} />

            <Route element={<ProtectedRoute />}>
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/change-password" element={<ChangePasswordPage />} />
              <Route path="/loyalty" element={<LoyaltyRewardsPage />} />
              <Route path="/checkout" element={<CheckoutPage />} />
            </Route>

            <Route element={<ProtectedRoute adminOnly />}>
              <Route path="/admin" element={<AdminDashboard />} />
            </Route>

            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </Suspense>
      </main>
      {!isAdminArea && (
        <>
          <Footer />
          <BottomNav />
          <AIChatWidget />
        </>
      )}
    </div>
  );
}
