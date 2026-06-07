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

const HomePage = lazy(() => import('./features/home/pages/HomePage'));
const CategoryPage = lazy(() => import('./features/products/pages/CategoryPage'));
const ComparePage = lazy(() => import('./features/products/pages/ComparePage'));
const LoginPage = lazy(() => import('./features/account/pages/LoginPage'));
const RegisterPage = lazy(() => import('./features/account/pages/RegisterPage'));
const ForgotPasswordPage = lazy(() => import('./features/account/pages/ForgotPasswordPage'));
const ResetPasswordPage = lazy(() => import('./features/account/pages/ResetPasswordPage'));
const VerifyEmailPage = lazy(() => import('./features/account/pages/VerifyEmailPage'));
const DashboardPage = lazy(() => import('./features/account/pages/DashboardPage'));
const ChangePasswordPage = lazy(() => import('./features/account/pages/ChangePasswordPage'));
const LoyaltyRewardsPage = lazy(() => import('./features/account/pages/LoyaltyRewardsPage'));
const ProductPage = lazy(() => import('./features/products/pages/ProductPage'));
const ProductListPage = lazy(() => import('./features/products/pages/ProductListPage'));
const BrandLandingPage = lazy(() => import('./features/products/pages/BrandLandingPage'));
const CartPage = lazy(() => import('./features/storefront-commerce/pages/CartPage'));
const CheckoutPage = lazy(() => import('./features/storefront-commerce/pages/CheckoutPage'));
const VideoPage = lazy(() => import('./features/media/pages/VideoPage'));
const ImagesPage = lazy(() => import('./features/media/pages/ImagesPage'));
const RankingsPage = lazy(() => import('./features/products/pages/RankingsPage'));
const AdminDashboard = lazy(() => import('./features/admin-shell/pages/AdminDashboard'));
const AdminLoginPage = lazy(() => import('./features/admin-shell/pages/AdminLoginPage'));
const NotFoundPage = lazy(() => import('./features/home/pages/NotFoundPage'));
const AboutPage = lazy(() => import('./features/home/pages/AboutPage'));
const WarrantyPage = lazy(() => import('./features/storefront-policies/pages/WarrantyPage'));
const PrivacyPage = lazy(() => import('./features/storefront-policies/pages/PrivacyPage'));
const DisputePage = lazy(() => import('./features/storefront-policies/pages/DisputePage'));
const InvoicePage = lazy(() => import('./features/storefront-commerce/pages/InvoicePage'));
const DataBackupPage = lazy(() => import('./features/admin-shell/pages/DataBackupPage'));
const ExtendedWarrantyPage = lazy(() => import('./features/storefront-policies/pages/ExtendedWarrantyPage'));
const PurchasePolicyPage = lazy(() => import('./features/storefront-policies/pages/PurchasePolicyPage'));
const DeliveryPolicyPage = lazy(() => import('./features/storefront-policies/pages/DeliveryPolicyPage'));
const ReturnWarrantyPolicyPage = lazy(() => import('./features/storefront-policies/pages/ReturnWarrantyPolicyPage'));
const TermsPage = lazy(() => import('./features/storefront-policies/pages/TermsPage'));
const MemberPolicyPage = lazy(() => import('./features/storefront-policies/pages/MemberPolicyPage'));

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
  const isCategoryArea = location.pathname === '/category' || location.pathname.startsWith('/category/');

  return (
    <div className="flex min-h-[100dvh] flex-col">
      {!isAdminArea && <Header />}
      <main className={`flex-1 bg-background text-slate-800 ${isAdminArea ? '' : 'px-3 sm:px-4 lg:px-6'} ${isCategoryArea ? 'overflow-hidden lg:overflow-visible' : ''}`}>
        <Suspense fallback={<div className="flex items-center justify-center p-20"><div className="h-8 w-8 animate-spin rounded-full border-4 border-[#d70018] border-t-transparent"></div></div>}>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/about" element={<AboutPage />} />
            <Route path="/warranty" element={<WarrantyPage />} />
            <Route path="/privacy" element={<PrivacyPage />} />
            <Route path="/dispute" element={<DisputePage />} />
            <Route path="/invoice" element={<InvoicePage />} />
            <Route path="/data-backup" element={<DataBackupPage />} />
            <Route path="/extended-warranty" element={<ExtendedWarrantyPage />} />
            <Route path="/purchase-policy" element={<PurchasePolicyPage />} />
            <Route path="/delivery-policy" element={<DeliveryPolicyPage />} />
            <Route path="/return-warranty-policy" element={<ReturnWarrantyPolicyPage />} />
            <Route path="/terms" element={<TermsPage />} />
            <Route path="/member-policy" element={<MemberPolicyPage />} />
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
          <div className={isCategoryArea ? 'hidden lg:block' : ''}>
            <Footer />
          </div>
          <BottomNav />
          <AIChatWidget />
        </>
      )}
    </div>
  );
}
