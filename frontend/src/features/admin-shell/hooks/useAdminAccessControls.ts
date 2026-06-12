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
  const canReadCategories = useAnyPermission(['category:read']);
  const canReadBrands = useAnyPermission(['brand:read']);
  const canReadSuppliers = useAnyPermission(['supplier:read']);
  const canReadOrders = useAnyPermission(['order:read']);
  const canReadVouchers = useAnyPermission(['voucher:read']);
  const canReadCustomers = useAnyPermission(['customer:read']);
  const canReadInventory = useAnyPermission(['inventory:read']);
  const canReadReviews = useAnyPermission(['review:read']);
  const canReadContent = useAnyPermission(['content:read']);
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
    services: canReadProducts,
    orders: canReadOrders,
    vouchers: canReadVouchers,
    flashSales: canReadProducts,
    customers: canReadCustomers,
    inventoryReceipts: canReadInventory,
    inventory: canReadInventory,
    reviews: canReadReviews,
    interactions: canReadReviews,
    content: canReadContent,
    banners: canReadContent,
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
