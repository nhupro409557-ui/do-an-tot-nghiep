import { useMemo } from 'react';
import type { AdminTab } from '../components/AdminDashboardConfig';

type PermissionReader = (permission: string) => boolean;
type AnyPermissionReader = (permissions: string[]) => boolean;

export function useAdminAccessControls(
  usePermission: PermissionReader,
  useAnyPermission: AnyPermissionReader,
) {
  const canManageCustomerAccess = usePermission('sys:manage_users');
  const canManageCustomerProfile = useAnyPermission(['customer:update', 'customer:loyalty_adjust', 'customer:issue_voucher', 'sys:manage_users']);
  const canReadOverview = useAnyPermission(['overview:read']);
  const canReadProducts = useAnyPermission(['product:read']);
  const canManageProducts = useAnyPermission(['product:create', 'product:update', 'product:delete']);
  const canReadCategories = useAnyPermission(['category:read']);
  const canReadBrands = useAnyPermission(['brand:read']);
  const canReadSuppliers = useAnyPermission(['supplier:read']);
  const canReadOrders = useAnyPermission(['order:read']);
  const canReadVouchers = useAnyPermission(['voucher:read']);
  const canManageVouchers = useAnyPermission(['voucher:create', 'voucher:update', 'voucher:delete']);
  const canReadCustomers = useAnyPermission(['customer:read']);
  const canReadInventory = useAnyPermission(['inventory:read']);
  const canManageInventory = useAnyPermission(['inventory:adjust', 'inventory:count', 'inventory:approve', 'inventory:reserve']);
  const canReadReviews = useAnyPermission(['review:read']);
  const canManageReviews = useAnyPermission(['review:update', 'review:delete']);
  const canReadContent = useAnyPermission(['content:read']);
  const canManageContent = useAnyPermission(['content:create', 'content:update', 'content:delete']);
  const canReadAudit = useAnyPermission(['audit:read']);
  const canManageRoles = useAnyPermission(['sys:manage_roles']);
  const canCreateContent = usePermission('content:create');
  const canUpdateContent = usePermission('content:update');
  const canDeleteContent = usePermission('content:delete');

  const tabAccess = useMemo<Record<AdminTab, boolean>>(() => ({
    overview: canReadOverview,
    products: canReadProducts,
    categories: canReadCategories,
    brands: canReadBrands,
    suppliers: canReadSuppliers,
    services: canManageProducts,
    orders: canReadOrders,
    vouchers: canReadVouchers,
    flashSales: canManageProducts || canManageVouchers,
    customers: canReadCustomers,
    inventoryReceipts: canManageInventory,
    inventory: canReadInventory,
    reviews: canReadReviews,
    interactions: canManageReviews,
    content: canReadContent,
    banners: canManageContent,
    audit: canReadAudit,
    permissions: canManageRoles,
  }), [
    canManageRoles,
    canReadAudit,
    canReadBrands,
    canReadCategories,
    canReadContent,
    canReadCustomers,
    canReadInventory,
    canReadOrders,
    canReadOverview,
    canReadProducts,
    canReadReviews,
    canReadSuppliers,
    canReadVouchers,
    canManageContent,
    canManageInventory,
    canManageProducts,
    canManageReviews,
    canManageVouchers,
  ]);

  return {
    canCreateContent,
    canDeleteContent,
    canManageCustomerAccess,
    canManageCustomerProfile,
    canUpdateContent,
    tabAccess,
  };
}
