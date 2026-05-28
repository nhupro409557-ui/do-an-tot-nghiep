import React, { Suspense, useEffect, useMemo, useRef, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  BadgePercent,
  BarChart3,

  Boxes,
  Building2,
  CheckCircle2,
  ClipboardList,
  Copy,
  Download,
  Edit2,
  Eye,
  FileText,
  FolderTree,
  GripVertical,

  Image,
  LayoutDashboard,


  Megaphone,

  Package,
  Plus,
  RefreshCw,
  RotateCcw,

  KeyRound,
  ScrollText,
  ShieldCheck,
  ShoppingBag,
  Star,
  TrendingUp,
  Trash2,
  Truck,
  Upload,

  UserCircle,
  Users,
  WalletCards,
  X,
} from 'lucide-react';
import {
  AdminBadge,
  AdminPanel,
  AdminTable,
  AdminTopBar,
  AlertRow,
  BrandLogo,
  CategoryTableRow,
  Checkbox,
  CollapsibleSection,
  EmptyState,
  FileInput,
  Input,
  MediaPreview,
  MetricCard,
  MiniMetric,
  MultiSelectBox,
  RichTextEditor,
  RowActions,
  SearchBox,
  Select,
  SimpleList,
  StatCard,
  SubmitButtons,
  VideoPreview,
  VoucherConditions,
  type StatTone,
} from '../components/admin/AdminDashboardParts';
import { useAuth } from '../context/AuthContext';
import { apiDb } from '../services/apiDb';

const AdminOverviewTab = React.lazy(() => import('../components/admin/tabs/AdminOverviewTab'));
const AdminProductsTab = React.lazy(() => import('../components/admin/tabs/AdminProductsTab'));
const AdminCategoriesTab = React.lazy(() => import('../components/admin/tabs/AdminCategoriesTab'));
const AdminOrdersTab = React.lazy(() => import('../components/admin/tabs/AdminOrdersTab'));
const AdminPermissionsTab = React.lazy(() => import('../components/admin/tabs/AdminPermissionsTab'));

type AdminTab = 'overview' | 'products' | 'categories' | 'brands' | 'services' | 'orders' | 'vouchers' | 'customers' | 'inventory' | 'reviews' | 'content' | 'audit' | 'permissions';
type AdminTabGroup = 'Tổng quan' | 'Kinh doanh' | 'Catalog' | 'Vận hành' | 'Khách hàng' | 'Hệ thống';
type SpecField = { key: string; label: string; group?: string; type: string; required: boolean; variant: boolean; isFilterable?: boolean; filterType?: string; filterEnabled?: boolean };
type CategoryFilterField = { key: string; label: string; type: string; enabled: boolean; source?: string };
type VariantForm = {
  id?: string;
  sku: string;
  colorName: string;
  colorCode: string;
  storage: string;
  ram: string;
  configuration: string;
  specs: Record<string, string>;
  imageUrl: string;
  price: number;
  salePrice: number;
  isActive: boolean;
};
type AccessoryOfferForm = {
  productId: string;
  productName: string;
  productSku: string;
  imageUrl: string;
  discountType: 'FIXED' | 'PERCENT';
  discountValue: number;
  maxQuantity: number;
};
type AttachedServiceForm = {
  serviceId: string;
  name: string;
  code: string;
  serviceType: string;
  attributeGroup: string;
  durationMonths: number;
  priceMode: string;
  fixedPrice: number;
  percentValue: number;
};
type WarrantyPolicyForm = {
  inheritWarrantyPolicy: boolean;
  hasWarranty: boolean;
  warrantyMonths: number;
  allowOneForOne: boolean;
  oneForOneDays: number;
};

const currency = new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 });
const compactCurrency = new Intl.NumberFormat('vi-VN', { notation: 'compact', maximumFractionDigits: 1 });
const percent = new Intl.NumberFormat('vi-VN', { style: 'percent', maximumFractionDigits: 1 });
const categoryStatusOptions: [string, string][] = [
  ['DRAFT', 'Nháp'],
  ['PENDING_REVIEW', 'Chờ duyệt'],
  ['APPROVED', 'Đã duyệt'],
  ['ACTIVE', 'Đang hiển thị'],
  ['REJECTED', 'Từ chối'],
  ['INACTIVE', 'Tạm ẩn'],
];
const reviewStatusOptions: [string, string][] = [
  ['all', 'Tất cả trạng thái'],
  ['PENDING', 'Chờ duyệt'],
  ['PUBLISHED', 'Đang hiển thị'],
  ['HIDDEN', 'Đã ẩn'],
  ['REJECTED', 'Từ chối'],
];
const reviewStarOptions: [string, string][] = [
  ['all', 'Tất cả số sao'],
  ['5', '5 sao'],
  ['4', '4 sao'],
  ['3', '3 sao'],
  ['2', '2 sao'],
  ['1', '1 sao'],
];
const warrantyDurationOptions: [string, string][] = [
  ['0', 'Không thời hạn'],
  ['3', '3 tháng'],
  ['6', '6 tháng'],
  ['9', '9 tháng'],
  ['12', '12 tháng'],
  ['18', '18 tháng'],
  ['24', '24 tháng'],
  ['36', '36 tháng'],
];
const serviceAttributeGroupOptions: [string, string][] = [
  ['WARRANTY', 'Bảo hành'],
  ['EXTENDED_WARRANTY', 'Bảo hành mở rộng'],
  ['ONE_FOR_ONE', '1 đổi 1'],
  ['ACCIDENTAL_DAMAGE', 'Rơi vỡ - rơi nước'],
  ['INSTALLATION', 'Lắp đặt'],
  ['CLEANING', 'Vệ sinh'],
  ['SUPPORT', 'Hỗ trợ kỹ thuật'],
];

const toNumber = (value: unknown) => Number(value || 0);
const getOrderTotal = (order: any) => toNumber(order.totalAmount ?? order.total_amount ?? order.total ?? order.grandTotal);
const reviewStatusLabel: Record<string, string> = {
  PENDING: 'Chờ duyệt',
  PUBLISHED: 'Đang hiển thị',
  HIDDEN: 'Đã ẩn',
  REJECTED: 'Từ chối',
};
const getOrderDate = (order: any) => new Date(order.createdAt || order.created_at || order.updatedAt || order.updated_at || Date.now());
const getProductStock = (product: any) => {
  const variantStock = Array.isArray(product.variants) ? product.variants.reduce((sum: number, variant: any) => sum + toNumber(variant.stock ?? variant.quantity), 0) : 0;
  return toNumber(product.stock ?? product.quantity ?? product.inventoryQuantity ?? variantStock);
};
const getInventorySettings = (product: any) => {
  const salesConfig = product?.salesConfig && typeof product.salesConfig === 'object' ? product.salesConfig : {};
  return {
    minimumStock: toNumber(salesConfig.minimumStock),
    blockSaleWhenOutOfStock: salesConfig.blockSaleWhenOutOfStock !== false,
    preferredLocationCode: String(salesConfig.preferredLocationCode || ''),
    preferredLocationName: String(salesConfig.preferredLocationName || ''),
    cycleCountDays: toNumber(salesConfig.cycleCountDays || 30),
  };
};
const getProductSold = (product: any) => toNumber(product.soldCount ?? product.sold_count ?? product.totalSold ?? product.salesCount ?? product.periodSoldCount);
const getVoucherBudgetUsage = (voucher: any) => {
  const cap = toNumber(voucher.totalBudgetCap ?? voucher.total_budget_cap ?? voucher.budgetCap);
  const used = toNumber(voucher.usedBudget ?? voucher.used_budget ?? voucher.budgetUsed ?? voucher.discountUsed);
  return cap > 0 ? used / cap : 0;
};
const slugifyText = (value: string) => value
  .normalize('NFD')
  .replace(/[\u0300-\u036f]/g, '')
  .toLowerCase()
  .replace(/[^a-z0-9]+/g, '-')
  .replace(/^-+|-+$/g, '');

const defaultWarrantyPolicy: WarrantyPolicyForm = {
  inheritWarrantyPolicy: true,
  hasWarranty: false,
  warrantyMonths: 0,
  allowOneForOne: false,
  oneForOneDays: 0,
};

function normalizeWarrantyPolicy(value: any): WarrantyPolicyForm {
  return {
    inheritWarrantyPolicy: value?.inheritWarrantyPolicy !== false,
    hasWarranty: Boolean(value?.hasWarranty),
    warrantyMonths: Number(value?.warrantyMonths || 0),
    allowOneForOne: Boolean(value?.allowOneForOne),
    oneForOneDays: Number(value?.oneForOneDays || 0),
  };
}

function categoryWarrantyPolicy(category: any, parent?: any): WarrantyPolicyForm {
  const own = normalizeWarrantyPolicy(category?.warrantyPolicy || defaultWarrantyPolicy);
  if (category?.parentId && own.inheritWarrantyPolicy && parent) {
    return normalizeWarrantyPolicy(parent.warrantyPolicy || defaultWarrantyPolicy);
  }
  return own;
}

const tabs: { id: AdminTab; label: string; icon: React.ElementType }[] = [
  { id: 'overview', label: 'Tổng quan', icon: LayoutDashboard },
  { id: 'products', label: 'Sản phẩm', icon: Package },
  { id: 'categories', label: 'Danh mục', icon: FolderTree },
  { id: 'brands', label: 'Thương hiệu', icon: Building2 },
  { id: 'services', label: 'Dịch vụ', icon: ShieldCheck },
  { id: 'orders', label: 'Đơn hàng', icon: ClipboardList },
  { id: 'vouchers', label: 'Voucher', icon: BadgePercent },
  { id: 'customers', label: 'Khách hàng', icon: Users },
  { id: 'inventory', label: 'Tồn kho', icon: Boxes },
  { id: 'reviews', label: 'Đánh giá', icon: Star },
  { id: 'content', label: 'Video & ná»™i dung', icon: Megaphone },
  { id: 'audit', label: 'Nhật ký', icon: ScrollText },
  { id: 'permissions', label: 'Phân quyền', icon: KeyRound },
];

const tabTone: Record<AdminTab, { active: string; item: string; icon: string; surface: string; label: string; title: string; description: string }> = {
  overview: {
    active: 'bg-rose-900 text-white shadow-sm shadow-rose-900/50 border-l-4 border-l-white',
    item: 'border-red-100 bg-red-50/70 text-red-950 hover:bg-red-100/80',
    icon: 'bg-red-100 text-red-600 ring-red-200',
    surface: 'border-red-100 bg-red-50 text-red-900',
    label: 'Dashboard',
    title: 'Tổng quan điều hành',
    description: 'Khu vực đọc số liệu nhanh, theo dõi doanh thu, đơn hàng và cảnh báo vận hành.',
  },
  products: {
    active: 'bg-red-600 text-white shadow-sm shadow-red-200',
    item: 'border-red-100 bg-red-50/70 text-red-950 hover:bg-red-100/80',
    icon: 'bg-red-50 text-red-700 ring-red-100',
    surface: 'border-red-100 bg-red-50/70 text-red-900',
    label: 'Quản lý',
    title: 'Quản lý sản phẩm',
    description: 'Khu vực cập nhật dữ liệu sản phẩm, media, biến thể và giá bán.',
  },
  categories: {
    active: 'bg-red-600 text-white shadow-sm shadow-red-200',
    item: 'border-rose-100 bg-rose-50/70 text-rose-950 hover:bg-rose-100/80',
    icon: 'bg-red-50 text-red-700 ring-red-100',
    surface: 'border-red-100 bg-red-50/70 text-red-900',
    label: 'Quản lý',
    title: 'Quản lý danh mục',
    description: 'Khu vực tổ chức danh mục và form thông số kỹ thuật.',
  },
  brands: {
    active: 'bg-red-600 text-white shadow-sm shadow-red-200',
    item: 'border-pink-100 bg-pink-50/70 text-pink-950 hover:bg-pink-100/80',
    icon: 'bg-red-50 text-red-700 ring-red-100',
    surface: 'border-red-100 bg-red-50/70 text-red-900',
    label: 'Quản lý',
    title: 'Quản lý thương hiệu',
    description: 'Khu vực quản lý logo, mã thương hiệu và thứ tự hiển thị.',
  },
  services: {
    active: 'border-emerald-200 bg-emerald-100 text-slate-800 shadow-sm shadow-emerald-50',
    item: 'border-emerald-100 bg-emerald-50/75 text-slate-700 hover:bg-emerald-100/80',
    icon: 'bg-emerald-50 text-emerald-700 ring-emerald-100',
    surface: 'border-emerald-100 bg-emerald-50/80 text-emerald-900',
    label: 'Catalog',
    title: 'Quản lý dịch vụ',
    description: 'Quản lý bảo hành mở rộng, lắp đặt, vệ sinh và các dịch vụ đi kèm sản phẩm.',
  },
  orders: {
    active: 'bg-amber-600 text-white shadow-sm shadow-amber-200',
    item: 'border-amber-100 bg-amber-50/75 text-amber-950 hover:bg-amber-100/80',
    icon: 'bg-amber-50 text-amber-700 ring-amber-100',
    surface: 'border-amber-100 bg-amber-50/80 text-amber-900',
    label: 'Vận hành',
    title: 'Quản lý đơn hàng',
    description: 'Khu vực xử lý trạng thái đơn hàng và theo dõi quy trình giao nhận.',
  },
  vouchers: {
    active: 'bg-amber-600 text-white shadow-sm shadow-amber-200',
    item: 'border-yellow-100 bg-yellow-50/75 text-yellow-950 hover:bg-yellow-100/80',
    icon: 'bg-amber-50 text-amber-700 ring-amber-100',
    surface: 'border-amber-100 bg-amber-50/80 text-amber-900',
    label: 'Vận hành',
    title: 'Quản lý voucher',
    description: 'Khu vực cài đặt chiến dịch ưu đãi, ngân sách và điều kiện áp dụng.',
  },
  customers: {
    active: 'bg-sky-600 text-white shadow-sm shadow-sky-200',
    item: 'border-sky-100 bg-sky-50/75 text-sky-950 hover:bg-sky-100/80',
    icon: 'bg-sky-50 text-sky-700 ring-sky-100',
    surface: 'border-sky-100 bg-sky-50/80 text-sky-900',
    label: 'Khách hàng',
    title: 'Quản lý khách hàng',
    description: 'Khu vực theo dõi hồ sơ, hạng thành viên và giá trị mua hàng.',
  },
  inventory: {
    active: 'bg-amber-600 text-white shadow-sm shadow-amber-200',
    item: 'border-orange-100 bg-orange-50/75 text-orange-950 hover:bg-orange-100/80',
    icon: 'bg-amber-50 text-amber-700 ring-amber-100',
    surface: 'border-amber-100 bg-amber-50/80 text-amber-900',
    label: 'Vận hành',
    title: 'Quản lý tồn kho',
    description: 'Khu vực theo dõi số lượng, cảnh báo thiếu hàng và trạng thái kho.',
  },
  reviews: {
    active: 'bg-sky-600 text-white shadow-sm shadow-sky-200',
    item: 'border-cyan-100 bg-cyan-50/75 text-cyan-950 hover:bg-cyan-100/80',
    icon: 'bg-sky-50 text-sky-700 ring-sky-100',
    surface: 'border-sky-100 bg-sky-50/80 text-sky-900',
    label: 'Khách hàng',
    title: 'Quản lý đánh giá',
    description: 'Khu vực kiểm duyệt phản hồi và chất lượng trải nghiệm sau mua.',
  },
  content: {
    active: 'bg-teal-600 text-white shadow-sm shadow-teal-200',
    item: 'border-teal-100 bg-teal-50/75 text-teal-950 hover:bg-teal-100/80',
    icon: 'bg-teal-50 text-teal-700 ring-teal-100',
    surface: 'border-teal-100 bg-teal-50/80 text-teal-900',
    label: 'Ná»™i dung',
    title: 'Video & ná»™i dung',
    description: 'Khu vực quản lý video, bài viết và nội dung hiển thị riêng với dashboard.',
  },
  audit: {
    active: 'bg-slate-700 text-white shadow-sm shadow-slate-200',
    item: 'border-slate-200 bg-slate-100/80 text-slate-950 hover:bg-slate-200/70',
    icon: 'bg-slate-100 text-slate-700 ring-slate-200',
    surface: 'border-slate-200 bg-slate-100/80 text-slate-900',
    label: 'Bảo mật',
    title: 'Nhật ký quản trị',
    description: 'Khu vực truy vết đăng nhập, thay đổi dữ liệu và thao tác nhạy cảm trong Admin.',
  },
  permissions: {
    active: 'bg-slate-700 text-white shadow-sm shadow-slate-200',
    item: 'border-slate-200 bg-slate-100/80 text-slate-950 hover:bg-slate-200/70',
    icon: 'bg-slate-100 text-slate-700 ring-slate-200',
    surface: 'border-slate-200 bg-slate-100/80 text-slate-900',
    label: 'Bảo mật',
    title: 'Phân quyền quản trị',
    description: 'Khu vực gán quyền thao tác theo vai trò quản trị.',
  },
};

const adminTabs: { id: AdminTab; label: string; group: AdminTabGroup; icon: React.ElementType }[] = [
  { id: 'overview', label: 'Tổng quan', group: 'Tổng quan', icon: LayoutDashboard },
  { id: 'orders', label: 'Đơn hàng', group: 'Kinh doanh', icon: ClipboardList },
  { id: 'vouchers', label: 'Voucher', group: 'Kinh doanh', icon: BadgePercent },
  { id: 'products', label: 'Sản phẩm', group: 'Catalog', icon: Package },
  { id: 'categories', label: 'Danh mục', group: 'Catalog', icon: FolderTree },
  { id: 'brands', label: 'Thương hiệu', group: 'Catalog', icon: Building2 },
  { id: 'services', label: 'Dịch vụ', group: 'Catalog', icon: ShieldCheck },
  { id: 'inventory', label: 'Tồn kho', group: 'Vận hành', icon: Boxes },
  { id: 'content', label: 'Video', group: 'Vận hành', icon: Megaphone },
  { id: 'customers', label: 'Khách hàng', group: 'Khách hàng', icon: Users },
  { id: 'reviews', label: 'Đánh giá', group: 'Khách hàng', icon: Star },
  { id: 'audit', label: 'Nhật ký', group: 'Hệ thống', icon: ScrollText },
  { id: 'permissions', label: 'Phân quyền', group: 'Hệ thống', icon: KeyRound },
];

// This normalized tone map overrides legacy mojibake strings while keeping the old data flow intact.
const adminTabTone: Record<AdminTab, { active: string; item: string; icon: string; surface: string; label: string; title: string; description: string }> = {
  overview: {
    active: 'border-rose-200 bg-rose-100 text-slate-800 shadow-sm shadow-rose-50',
    item: 'border-rose-100 bg-rose-50 text-slate-700 hover:bg-rose-100/80',
    icon: 'bg-rose-100 text-rose-600 ring-rose-200',
    surface: 'border-rose-100 bg-rose-50 text-rose-900',
    label: 'Dashboard',
    title: 'Tổng quan điều hành',
    description: 'Khu vực đọc số liệu nhanh, theo dõi doanh thu, đơn hàng và cảnh báo vận hành.',
  },
  products: {
    active: 'border-rose-200 bg-rose-100 text-slate-800 shadow-sm shadow-rose-50',
    item: 'border-rose-100 bg-rose-50/70 text-slate-700 hover:bg-rose-100/80',
    icon: 'bg-rose-50 text-rose-700 ring-rose-100',
    surface: 'border-rose-100 bg-rose-50/70 text-rose-900',
    label: 'Quản lý',
    title: 'Quản lý sản phẩm',
    description: 'Khu vực cập nhật dữ liệu sản phẩm, media, biến thể và giá bán.',
  },
  categories: {
    active: 'border-rose-200 bg-rose-100 text-slate-800 shadow-sm shadow-rose-50',
    item: 'border-rose-100 bg-rose-50/70 text-slate-700 hover:bg-rose-100/80',
    icon: 'bg-rose-50 text-rose-700 ring-rose-100',
    surface: 'border-rose-100 bg-rose-50/70 text-rose-900',
    label: 'Quản lý',
    title: 'Quản lý danh mục',
    description: 'Khu vực tổ chức danh mục và form thông số kỹ thuật.',
  },
  brands: {
    active: 'border-rose-200 bg-rose-100 text-slate-800 shadow-sm shadow-rose-50',
    item: 'border-rose-100 bg-rose-50/70 text-slate-700 hover:bg-rose-100/80',
    icon: 'bg-rose-50 text-rose-700 ring-rose-100',
    surface: 'border-rose-100 bg-rose-50/70 text-rose-900',
    label: 'Quản lý',
    title: 'Quản lý thương hiệu',
    description: 'Khu vực quản lý logo, mã thương hiệu và thứ tự hiển thị.',
  },
  services: {
    active: 'border-emerald-200 bg-emerald-100 text-slate-800 shadow-sm shadow-emerald-50',
    item: 'border-emerald-100 bg-emerald-50/75 text-slate-700 hover:bg-emerald-100/80',
    icon: 'bg-emerald-50 text-emerald-700 ring-emerald-100',
    surface: 'border-emerald-100 bg-emerald-50/80 text-emerald-900',
    label: 'Catalog',
    title: 'Quản lý dịch vụ',
    description: 'Quản lý bảo hành mở rộng, lắp đặt, vệ sinh và các dịch vụ đi kèm sản phẩm.',
  },
  orders: {
    active: 'border-sky-200 bg-sky-100 text-slate-800 shadow-sm shadow-sky-50',
    item: 'border-sky-100 bg-sky-50/75 text-slate-700 hover:bg-sky-100/80',
    icon: 'bg-sky-50 text-sky-700 ring-sky-100',
    surface: 'border-sky-100 bg-sky-50/80 text-sky-900',
    label: 'Kinh doanh',
    title: 'Quản lý đơn hàng',
    description: 'Khu vực xử lý trạng thái đơn hàng và theo dõi quy trình giao nhận.',
  },
  vouchers: {
    active: 'border-sky-200 bg-sky-100 text-slate-800 shadow-sm shadow-sky-50',
    item: 'border-sky-100 bg-sky-50/75 text-slate-700 hover:bg-sky-100/80',
    icon: 'bg-sky-50 text-sky-700 ring-sky-100',
    surface: 'border-sky-100 bg-sky-50/80 text-sky-900',
    label: 'Kinh doanh',
    title: 'Quản lý voucher',
    description: 'Khu vực cài đặt chiến dịch ưu đãi, ngân sách và điều kiện áp dụng.',
  },
  customers: {
    active: 'border-sky-200 bg-sky-100 text-slate-800 shadow-sm shadow-sky-50',
    item: 'border-sky-100 bg-sky-50/75 text-slate-700 hover:bg-sky-100/80',
    icon: 'bg-sky-50 text-sky-700 ring-sky-100',
    surface: 'border-sky-100 bg-sky-50/80 text-sky-900',
    label: 'Khách hàng',
    title: 'Quản lý khách hàng',
    description: 'Khu vực theo dõi hồ sơ, hạng thành viên và giá trị mua hàng.',
  },
  inventory: {
    active: 'border-emerald-200 bg-emerald-100 text-slate-800 shadow-sm shadow-emerald-50',
    item: 'border-emerald-100 bg-emerald-50/75 text-slate-700 hover:bg-emerald-100/80',
    icon: 'bg-emerald-50 text-emerald-700 ring-emerald-100',
    surface: 'border-emerald-100 bg-emerald-50/80 text-emerald-900',
    label: 'Vận hành',
    title: 'Quản lý tồn kho',
    description: 'Khu vực theo dõi số lượng, cảnh báo thiếu hàng và trạng thái kho.',
  },
  reviews: {
    active: 'border-cyan-200 bg-cyan-100 text-slate-800 shadow-sm shadow-cyan-50',
    item: 'border-cyan-100 bg-cyan-50/75 text-slate-700 hover:bg-cyan-100/80',
    icon: 'bg-sky-50 text-sky-700 ring-sky-100',
    surface: 'border-sky-100 bg-sky-50/80 text-sky-900',
    label: 'Khách hàng',
    title: 'Quản lý đánh giá',
    description: 'Khu vực kiểm duyệt phản hồi và chất lượng trải nghiệm sau mua.',
  },
  content: {
    active: 'border-emerald-200 bg-emerald-100 text-slate-800 shadow-sm shadow-emerald-50',
    item: 'border-emerald-100 bg-emerald-50/75 text-slate-700 hover:bg-emerald-100/80',
    icon: 'bg-emerald-50 text-emerald-700 ring-emerald-100',
    surface: 'border-emerald-100 bg-emerald-50/80 text-emerald-900',
    label: 'Ná»™i dung',
    title: 'Video và nội dung',
    description: 'Khu vực quản lý video, bài viết và nội dung hiển thị riêng với dashboard.',
  },
  audit: {
    active: 'border-slate-200 bg-slate-100 text-slate-800 shadow-sm shadow-slate-50',
    item: 'border-slate-200 bg-slate-100/80 text-slate-700 hover:bg-slate-200/70',
    icon: 'bg-slate-100 text-slate-700 ring-slate-200',
    surface: 'border-slate-200 bg-slate-100/80 text-slate-900',
    label: 'Hệ thống',
    title: 'Nhật ký quản trị',
    description: 'Khu vực truy vết đăng nhập, thay đổi dữ liệu và thao tác nhạy cảm trong Admin.',
  },
  permissions: {
    active: 'border-slate-200 bg-slate-100 text-slate-800 shadow-sm shadow-slate-50',
    item: 'border-slate-200 bg-slate-100/80 text-slate-700 hover:bg-slate-200/70',
    icon: 'bg-slate-100 text-slate-700 ring-slate-200',
    surface: 'border-slate-200 bg-slate-100/80 text-slate-900',
    label: 'Hệ thống',
    title: 'Phân quyền quản trị',
    description: 'Khu vực gán quyền thao tác theo vai trò quản trị.',
  },
};

const searchPlaceholderByTab: Record<AdminTab, string> = {
  overview: 'Tìm số liệu, cảnh báo hoặc khu vực cần theo dõi',
  products: 'Tìm sản phẩm, SKU, thương hiệu',
  categories: 'Tìm danh mục, slug, danh mục cha',
  brands: 'Tìm thương hiệu, mã hoặc SEO',
  services: 'Tìm dịch vụ, mã, nhóm hoặc loại dịch vụ',
  orders: 'Tìm mã đơn, khách hàng, trạng thái',
  vouchers: 'Tìm mã voucher, loại, trạng thái',
  customers: 'Tìm khách hàng, email, hạng',
  inventory: 'Tìm sản phẩm, SKU, trạng thái kho',
  reviews: 'Tìm sản phẩm, khách hàng, nội dung',
  content: 'Tìm tiêu đề, loại, mô tả',
  audit: 'Tìm sự kiện, tài nguyên hoặc IP',
  permissions: 'Tìm vai trò, nhóm quyền hoặc thao tác',
};

const statusLabel: Record<string, string> = {
  PENDING: 'Chờ xử lý',
  CONFIRMED: 'Đã xác nhận',
  PAID: 'Đã thanh toán',
  PROCESSING: 'Đang đóng gói',
  SHIPPED: 'Đang giao',
  COMPLETED: 'Đã giao',
  CANCELLED: 'Đã hủy',
  REFUNDED: 'Đã hoàn tiền',
  PAYMENT_FAILED: 'Thanh toán thất bại',
  RETURNING: 'Đang hoàn hàng',
  RETURNED: 'Đã nhận hàng hoàn',
  ACTIVE: 'Đang bán',
  INACTIVE: 'Tạm ẩn',
  DRAFT: 'Nháp',
  REVISION_DRAFT: 'Nháp chỉnh sửa',
  ARCHIVED: 'Lưu trữ',
};

const orderStatusOptions: [string, string][] = [
  ['PENDING', 'Chờ xử lý'],
  ['PROCESSING', 'Đang đóng gói'],
  ['SHIPPED', 'Đang giao'],
  ['COMPLETED', 'Đã giao'],
  ['CANCELLED', 'Đã hủy'],
  ['PAYMENT_FAILED', 'Thanh toán thất bại'],
  ['RETURNING', 'Đang hoàn hàng'],
  ['RETURNED', 'Đã nhận hàng hoàn'],
];

const orderTransitionMap: Record<string, string[]> = {
  PENDING: ['PENDING', 'PROCESSING', 'CANCELLED'],
  PAID: ['PAID', 'PROCESSING', 'REFUNDED', 'PAYMENT_FAILED'],
  PROCESSING: ['PROCESSING', 'SHIPPED', 'CANCELLED'],
  SHIPPED: ['SHIPPED', 'COMPLETED', 'RETURNING'],
  COMPLETED: ['COMPLETED', 'RETURNING'],
  CANCELLED: ['CANCELLED'],
  REFUNDED: ['REFUNDED'],
  PAYMENT_FAILED: ['PAYMENT_FAILED'],
  RETURNING: ['RETURNING', 'RETURNED', 'REFUNDED'],
  RETURNED: ['RETURNED', 'REFUNDED'],
};

const productStatusOptions: [string, string][] = [
  ['DRAFT', 'Nháp'],
  ['REVISION_DRAFT', 'Nháp chỉnh sửa'],
  ['PENDING', 'Chờ duyệt'],
  ['ACTIVE', 'Đang bán'],
  ['INACTIVE', 'Tạm ẩn'],
  ['ARCHIVED', 'Lưu trữ'],
];

const productStatusLabel: Record<string, string> = Object.fromEntries(productStatusOptions);
const contentTypeOptions: [string, string][] = [
  ['VIDEO', 'Video'],
  ['BANNER', 'Banner'],
  ['MARKETING_PAGE', 'Trang marketing'],
];
const videoSourceOptions: [string, string][] = [
  ['UPLOAD', 'Upload file'],
  ['YOUTUBE', 'Link YouTube'],
];
const videoCategoryOptions: [string, string][] = [
  ['PRODUCT', 'Liên quan sản phẩm'],
  ['NEWS', 'Tin tức'],
  ['TIPS', 'Mẹo hay'],
  ['SERVICE', 'Dịch vụ'],
  ['REVIEW', 'Đánh giá / trải nghiệm'],
  ['OTHER', 'Khác'],
];
const contentStatusOptions: [string, string][] = [
  ['DRAFT', 'Nháp'],
  ['SCHEDULED', 'Chờ đăng'],
  ['PUBLISHED', 'Đã xuất bản'],
  ['ARCHIVED', 'Lưu trữ'],
];


const emptyContentForm = {
  title: '',
  description: '',
  contentType: 'VIDEO',
  videoSource: 'UPLOAD',
  videoCategory: 'PRODUCT',
  status: 'DRAFT',
  videoUrl: '',
  thumbnailUrl: '',
  bannerImageUrl: '',
  contentBody: '',
  ctaLabel: '',
  ctaUrl: '',
  productIds: '',
  categoryIds: '',
  commentsText: '',
  likeCount: 0,
  viewCount: 0,
  sortOrder: 0,
  scheduledAt: '',
  publishedAt: '',
  isActive: true,
  version: 1,
};

const inventoryTransactionOptions: [string, string][] = [
  ['RECEIPT', 'Nhập kho'],
  ['ADJUSTMENT', 'Điều chỉnh'],
  ['RETURN', 'Hoàn hàng'],
  ['REVERSAL', 'Đảo giao dịch'],
];

const voucherCampaignOptions: [string, string][] = [
  ['ACQUISITION', 'Tân binh / đơn đầu tiên'],
  ['RETENTION', 'Giữ chân / mua lại'],
  ['LOYALTY', 'Theo hạng thành viên'],
  ['CONVERSION', 'Thúc đẩy chốt đơn'],
  ['FLASH_SALE', 'Flash sale ngắn hạn'],
  ['ABANDONED_CART', 'Giỏ hàng bị bỏ quên'],
  ['CUSTOMER_SERVICE', 'Chăm sóc / đền bù'],
];

const voucherAudienceOptions: [string, string][] = [
  ['PUBLIC', 'Công khai'],
  ['NEW_CUSTOMER', 'Khách hàng mới'],
  ['MEMBER_TIER', 'Theo hạng thành viên'],
  ['SPECIFIC_USER', 'Một khách hàng cụ thể'],
  ['HIDDEN', 'Mã ẩn do admin cấp'],
  ['ABANDONED_CART', 'Khôi phục giỏ hàng'],
];

const voucherTierOptions = ['MEMBER', 'SILVER', 'GOLD', 'PLATINUM', 'DIAMOND'];

const emptyVariant: VariantForm = {
  sku: '',
  colorName: '',
  colorCode: '#111827',
  storage: '',
  ram: '',
  configuration: '',
  specs: {},
  imageUrl: '',
  price: 0,
  salePrice: 0,
  isActive: true,
};

const emptyProduct = {
  name: '',
  price: 0,
  discountPrice: 0,
  brand: 'Apple',
  category: 'PHONE',
  categoryId: '',
  subcategoryId: '',
  brandId: '',
  imageUrl: '',
  images: [] as string[],
  videoUrl: '',
  description: '',
  specifications: {} as Record<string, string>,
  seoTitle: '',
  seoDescription: '',
  seoSlug: '',
  accessoryOffers: [] as AccessoryOfferForm[],
  attachedServices: [] as AttachedServiceForm[],
  warrantyPolicy: defaultWarrantyPolicy,
  updatedAt: '',
  version: 1,
  variantSpecKeys: [] as string[],
  variants: [] as VariantForm[],
  status: 'DRAFT',
  isFeatured: false,
  isFlashSale: false,
};

const productExtraKeys = ['_variantSpecKeys', '_seoTitle', '_seoDescription', '_seoSlug', '_accessoryProducts', '_accessoryOffers', '_attachedServices', '_warrantyPolicy'];

function buildVariantSku(productName: string, colorName: string, index: number) {
  const part = (value: string, fallback: string) => slugifyText(value || fallback).split('-').map((item) => item.charAt(0)).join('').slice(0, 5).toUpperCase() || fallback;
  return `${part(productName, 'SP')}-${part(colorName, `M${index + 1}`)}-${String(index + 1).padStart(2, '0')}`;
}

function compactId(id?: string) {
  return id ? `#${id.slice(0, 8).toUpperCase()}` : '#';
}

function matchesSearch(item: any, keyword: string, fields: string[]) {
  const needle = keyword.trim().toLowerCase();
  if (!needle) return true;
  return fields
    .map((field) => {
      const value = field.split('.').reduce<any>((source, key) => source?.[key], item);
      return value == null ? '' : String(value);
    })
    .join(' ')
    .toLowerCase()
    .includes(needle);
}

function sameId(left: unknown, right: unknown) {
  return String(left || '') !== '' && String(left || '') === String(right || '');
}

function splitIds(value: string) {
  return value.split(/[\n,]/).map((item) => item.trim()).filter(Boolean);
}

function groupSpecFields(fields: SpecField[]) {
  return fields.reduce<{ title: string; fields: SpecField[] }[]>((groups, field) => {
    const title = field.group?.trim() || 'Thông số chung';
    const existing = groups.find((group) => group.title === title);
    if (existing) existing.fields.push(field);
    else groups.push({ title, fields: [field] });
    return groups;
  }, []);
}

async function uploadFiles(files: FileList | null, folder: 'products' | 'brands' | 'categories' | 'content' = 'products') {
  if (!files) return [];
  const uploads = Array.from(files).map(async (file) => {
    const presigned = await apiDb.adminCreatePresignedUpload({
      filename: file.name,
      contentType: file.type,
      size: file.size,
      folder,
    });
    const response = await fetch(presigned.uploadUrl, {
      method: 'PUT',
      headers: { 'Content-Type': file.type },
      body: file,
    });
    if (!response.ok) throw new Error('Không thể upload file lên kho lưu trữ.');
    return presigned.publicUrl as string;
  });
  return Promise.all(uploads);
}

export default function AdminDashboard() {
  const { canAccessAdmin, loading, usePermission, useAnyPermission } = useAuth();
  const [tab, setTab] = useState<AdminTab>('overview');
  const [query, setQuery] = useState('');
  const [productCategoryFilter, setProductCategoryFilter] = useState('');
  const [productBrandFilter, setProductBrandFilter] = useState('');
  const [inventoryCategoryFilter, setInventoryCategoryFilter] = useState('');
  const [inventoryBrandFilter, setInventoryBrandFilter] = useState('');
  const [brandCategoryFilter, setBrandCategoryFilter] = useState('');
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [busy, setBusy] = useState(false);
  const [overview, setOverview] = useState<any>({});
  const [orders, setOrders] = useState<any[]>([]);
  const [products, setProducts] = useState<any[]>([]);
  const [attachedServices, setAttachedServices] = useState<any[]>([]);
  const [categories, setCategories] = useState<any[]>([]);
  const [categoryMetrics, setCategoryMetrics] = useState<any>({});
  const [categoryAuditLogs, setCategoryAuditLogs] = useState<any[]>([]);
  const [categoryMigrationJobs, setCategoryMigrationJobs] = useState<any[]>([]);
  const [categoryPanelBusy, setCategoryPanelBusy] = useState(false);
  const [brands, setBrands] = useState<any[]>([]);
  const [brandStatusFilter, setBrandStatusFilter] = useState('all');
  const [brandPage, setBrandPage] = useState(1);
  const [brandTotal, setBrandTotal] = useState(0);
  const [vouchers, setVouchers] = useState<any[]>([]);
  const [customers, setCustomers] = useState<any[]>([]);
  const [customerPage, setCustomerPage] = useState(1);
  const [customerTotal, setCustomerTotal] = useState(0);
  const [selectedCustomerIds, setSelectedCustomerIds] = useState<string[]>([]);
  const [selectedCustomer, setSelectedCustomer] = useState<any | null>(null);
  const [customerDetailOpen, setCustomerDetailOpen] = useState(false);
  const [customerDetailBusy, setCustomerDetailBusy] = useState(false);
  const [customerActiveSection, setCustomerActiveSection] = useState<'summary' | 'orders' | 'loyalty' | 'notes' | 'audit'>('summary');
  const [customerOrders, setCustomerOrders] = useState<any[]>([]);
  const [customerLoyaltyHistory, setCustomerLoyaltyHistory] = useState<any[]>([]);
  const [customerNotes, setCustomerNotes] = useState<any[]>([]);
  const [customerAuditLogs, setCustomerAuditLogs] = useState<any[]>([]);
  const [customerTagDraft, setCustomerTagDraft] = useState('');
  const [customerNoteDraft, setCustomerNoteDraft] = useState('');
  const [customerVoucherId, setCustomerVoucherId] = useState('');
  const [customerVoucherNote, setCustomerVoucherNote] = useState('');
  const [customerPointDelta, setCustomerPointDelta] = useState('0');
  const [customerPointReason, setCustomerPointReason] = useState('');
  const [reviews, setReviews] = useState<any[]>([]);
  const [reviewSummary, setReviewSummary] = useState<any[]>([]);
  const [reviewStatusFilter, setReviewStatusFilter] = useState('all');
  const [reviewStarFilter, setReviewStarFilter] = useState('all');
  const [contentTypeFilter, setContentTypeFilter] = useState('all');
  const [contentStatusFilter, setContentStatusFilter] = useState('all');
  const [videoProductSearch, setVideoProductSearch] = useState('');
  const [videoProductCategoryFilter, setVideoProductCategoryFilter] = useState('all');
  const [videoProductBrandFilter, setVideoProductBrandFilter] = useState('all');
  const [videoReplyDrafts, setVideoReplyDrafts] = useState<Record<string, string>>({});
  const [contentItems, setContentItems] = useState<any[]>([]);
  const [contentForm, setContentForm] = useState(emptyContentForm);
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [permissions, setPermissions] = useState<any[]>([]);
  const [roles, setRoles] = useState<any[]>([]);
  const [rolePermissionMap, setRolePermissionMap] = useState<Record<string, string[]>>({});
  const [staffForm, setStaffForm] = useState({ email: '', password: '', fullName: '', phone: '', status: 'ACTIVE', permissionCodes: [] as string[] });
  const [editingStaffAccessId, setEditingStaffAccessId] = useState<string | null>(null);
  const [rolePermissionEditing, setRolePermissionEditing] = useState(false);
  const [staffPermissionEditor, setStaffPermissionEditor] = useState<any | null>(null);
  const [staffPermissionDraft, setStaffPermissionDraft] = useState<string[]>([]);
  const [inventoryDraft, setInventoryDraft] = useState<{
    product: any;
    variant?: any;
    transactionType: string;
    delta: number;
    referenceCode: string;
    reason: string;
    note: string;
    supplierName: string;
    unitCost: number;
    locationCode: string;
    locationName: string;
    imeis: string;
    minimumStock: number;
    blockSaleWhenOutOfStock: boolean;
    cycleCountDays: number;
    logs: any[];
  } | null>(null);
  const [selectedOrder, setSelectedOrder] = useState<any | null>(null);
  const [orderPanelOpen, setOrderPanelOpen] = useState(false);
  const [orderPanelBusy, setOrderPanelBusy] = useState(false);
  const [orderSaving, setOrderSaving] = useState(false);
  const [orderDraft, setOrderDraft] = useState({
    status: 'PENDING',
    assignedStaffName: '',
    internalNote: '',
    cancellationReason: '',
    shippingProvider: '',
    trackingCode: '',
    refundPayment: false,
  });

  const [productForm, setProductForm] = useState(emptyProduct);
  const [serviceForm, setServiceForm] = useState({ code: '', name: '', serviceType: 'SUPPORT_SERVICE', attributeGroup: '', durationMonths: 0, priceMode: 'FIXED', fixedPrice: 0, percentValue: 0, baseAmount: 0, isActive: true });
  const [editingServiceId, setEditingServiceId] = useState<string | null>(null);
  const [serviceFormOpen, setServiceFormOpen] = useState(false);
  const [accessorySearch, setAccessorySearch] = useState('');
  const [accessoryCategoryFilter, setAccessoryCategoryFilter] = useState('');
  const [accessoryBrandFilter, setAccessoryBrandFilter] = useState('');
  const [attachedServiceTypeFilter, setAttachedServiceTypeFilter] = useState('');
  const [attachedServiceGroupFilter, setAttachedServiceGroupFilter] = useState('');
  const [attachedServiceSearch, setAttachedServiceSearch] = useState('');
  const [selectedProductIds, setSelectedProductIds] = useState<string[]>([]);
  const [previewProduct, setPreviewProduct] = useState<any | null>(null);
  const [categoryForm, setCategoryForm] = useState({
    name: '',
    slug: '',
    icon: 'phone',
    iconUrl: '',
    bannerUrl: '',
    parentId: '',
    order: 0,
    isActive: true,
    status: 'ACTIVE',
    seoTitle: '',
    seoDescription: '',
    seoKeywords: '',
    specFields: [] as SpecField[],
    filterConfig: [] as CategoryFilterField[],
    inventoryPolicy: { inheritImeiPolicy: true, trackImei: false },
    warrantyPolicy: { inheritWarrantyPolicy: true, hasWarranty: false, warrantyMonths: 0, allowOneForOne: false, oneForOneDays: 0 },
    version: null as number | null,
  });
  const [brandForm, setBrandForm] = useState({ name: '', code: '', slug: '', logoUrl: '', logoAltText: '', order: 0, isActive: true, landingTitle: '', seoTitle: '', seoDescription: '' });
  const [brandCodeStatus, setBrandCodeStatus] = useState<'idle' | 'checking' | 'available' | 'taken'>('idle');
  const [brandImportMode, setBrandImportMode] = useState('skip');
  const [brandImportJobs, setBrandImportJobs] = useState<any[]>([]);
  const [activeBrandImportJob, setActiveBrandImportJob] = useState<any | null>(null);
  const [selectedBrandIds, setSelectedBrandIds] = useState<string[]>([]);
  const [voucherForm, setVoucherForm] = useState({
    code: '',
    discountType: 'FIXED',
    discountAmount: 100000,
    minOrderValue: 0,
    maxDiscount: 0,
    usageLimit: 100,
    totalBudgetCap: 0,
    perUserLimit: 1,
    perDeviceLimit: 0,
    perIpLimit: 0,
    campaignType: 'CONVERSION',
    audienceType: 'PUBLIC',
    eligibleTiers: [] as string[],
    eligibleUserRegisteredAfter: '',
    assignedUserId: '',
    includeProductIds: '',
    excludeProductIds: '',
    includeCategoryIds: '',
    excludeCategoryIds: '',
    firstOrderOnly: false,
    hiddenCode: false,
    abandonedCartOnly: false,
    validityDaysAfterClaim: 0,
    stackable: false,
    refundPolicy: 'SHOP_FAULT_ONLY',
    startsAt: '',
    endsAt: '',
    internalNote: '',
    status: 'ACTIVE',
  });
  const [editingProductId, setEditingProductId] = useState<string | null>(null);
  const [editingCategoryId, setEditingCategoryId] = useState<string | null>(null);
  const [categorySlugStatus, setCategorySlugStatus] = useState<'idle' | 'checking' | 'available' | 'taken'>('idle');
  const [editingBrandId, setEditingBrandId] = useState<string | null>(null);
  const [editingVoucherId, setEditingVoucherId] = useState<string | null>(null);
  const [editingContentId, setEditingContentId] = useState<string | null>(null);

  const rootCategories = useMemo(() => categories.filter((item) => !item.parentId), [categories]);
  const subCategories = useMemo(() => categories.filter((item) => item.parentId), [categories]);
  const editingCategory = useMemo(() => categories.find((item) => item.id === editingCategoryId), [categories, editingCategoryId]);
  const categoryParentMigrationHint = Boolean(editingCategoryId && Number(editingCategory?.productCount || 0) > 0);
  const isEditingChildCategory = Boolean(categoryForm.parentId);
  const selectedCategory = useMemo(() => categories.find((item) => item.id === productForm.categoryId), [categories, productForm.categoryId]);
  const selectedSubCategory = useMemo(() => categories.find((item) => item.id === productForm.subcategoryId), [categories, productForm.subcategoryId]);
  const specFields: SpecField[] = useMemo(() => {
    const childOwnFields = selectedSubCategory?.ownSpecFields || [];
    const merged = [...(selectedCategory?.specFields || []), ...childOwnFields];
    const seen = new Set<string>();
    return merged.filter((field) => {
      if (!field.key || seen.has(field.key)) return false;
      seen.add(field.key);
      return true;
    });
  }, [selectedCategory, selectedSubCategory]);
  const variantFields = specFields.filter((item) => item.variant);
  const activeVariantFields = variantFields.filter((item) => productForm.variantSpecKeys.includes(item.key));
  const productSpecFields = specFields.filter((item) => !item.variant || !productForm.variantSpecKeys.includes(item.key));
  const groupedProductSpecFields = useMemo(() => groupSpecFields(productSpecFields), [productSpecFields]);
  const groupedActiveVariantFields = useMemo(() => groupSpecFields(activeVariantFields), [activeVariantFields]);
  const productBrandOptions = useMemo(() => {
    return [['', 'Tất cả thương hiệu'], ...brands.filter((b: any) => {
      if (!productCategoryFilter) return true;
      if (b.categoryIds && (b.categoryIds.includes(productCategoryFilter) || categories.some((c: any) => c.parentId === productCategoryFilter && b.categoryIds.includes(c.id)))) return true;
      return products.some((p: any) => (p.brandId === b.id || p.brand === b.name) && (p.categoryId === productCategoryFilter || p.subcategoryId === productCategoryFilter || categories.some((c: any) => c.parentId === productCategoryFilter && (p.categoryId === c.id || p.subcategoryId === c.id))));
    }).map((b: any) => [b.id, b.name])];
  }, [brands, productCategoryFilter, categories, products]);

  const inventoryBrandOptions = useMemo(() => {
    return [['', 'Tất cả thương hiệu'], ...brands.filter((b: any) => {
      if (!inventoryCategoryFilter) return true;
      if (b.categoryIds && (b.categoryIds.includes(inventoryCategoryFilter) || categories.some((c: any) => c.parentId === inventoryCategoryFilter && b.categoryIds.includes(c.id)))) return true;
      return products.some((p: any) => (p.brandId === b.id || p.brand === b.name) && (p.categoryId === inventoryCategoryFilter || p.subcategoryId === inventoryCategoryFilter || categories.some((c: any) => c.parentId === inventoryCategoryFilter && (p.categoryId === c.id || p.subcategoryId === c.id))));
    }).map((b: any) => [b.id, b.name])];
  }, [brands, inventoryCategoryFilter, categories, products]);

  const filteredProducts = useMemo(() => {
    return products.filter((product) => {
      const ms = matchesSearch(product, query, ['name', 'brand', 'categoryName', 'category', 'sku', 'status']);
      const mc = !productCategoryFilter || String(product.categoryId) === productCategoryFilter || String(product.subcategoryId) === productCategoryFilter;
      const mb = !productBrandFilter || String(product.brandId) === productBrandFilter || (product.brand && brands.find(b => String(b.id) === productBrandFilter)?.name === product.brand);
      return ms && mc && mb;
    });
  }, [products, query, productCategoryFilter, productBrandFilter, brands]);
  const accessoryProductChoices = useMemo(() => {
    const selectedCategory = categories.find((category) => sameId(category.id, accessoryCategoryFilter));
    const childCategoryIds = new Set(categories.filter((category) => sameId(category.parentId, accessoryCategoryFilter)).map((category) => String(category.id)));
    return products
      .filter((product) => !sameId(product.id, editingProductId))
      .filter((product) => !productForm.accessoryOffers.some((offer) => sameId(offer.productId, product.id)))
      .filter((product) => {
        if (!accessoryCategoryFilter) return true;
        return sameId(product.categoryId, accessoryCategoryFilter)
          || sameId(product.subcategoryId, accessoryCategoryFilter)
          || childCategoryIds.has(String(product.categoryId || ''))
          || childCategoryIds.has(String(product.subcategoryId || ''))
          || (!!selectedCategory && [product.category, product.categoryName, product.subcategoryName].some((value) => String(value || '').toLowerCase() === String(selectedCategory.name || selectedCategory.code || selectedCategory.slug || '').toLowerCase()));
      })
      .filter((product) => !accessoryBrandFilter || sameId(product.brandId, accessoryBrandFilter) || sameId(product.brand, brands.find((brand) => sameId(brand.id, accessoryBrandFilter))?.name))
      .filter((product) => matchesSearch(product, accessorySearch, ['name', 'sku', 'brand', 'brandName', 'categoryName', 'category']))
      .slice(0, 50);
  }, [accessoryBrandFilter, accessoryCategoryFilter, accessorySearch, brands, categories, editingProductId, productForm.accessoryOffers, products]);
  const filteredCategories = useMemo(() => {
    return categories.filter((category) => matchesSearch(category, query, ['name', 'slug', 'parentName', 'icon']));
  }, [categories, query]);
  const filteredRootCategories = useMemo(() => {
    return rootCategories.filter((category) => matchesSearch(category, query, ['name', 'slug', 'icon']));
  }, [rootCategories, query]);
  const filteredCategoryTree = useMemo(() => {
    const visibleIds = new Set(filteredCategories.map((category) => category.id));
    return rootCategories
      .filter((category) => visibleIds.has(category.id) || subCategories.some((child) => child.parentId === category.id && visibleIds.has(child.id)))
      .map((category) => ({
        ...category,
        children: subCategories.filter((child) => child.parentId === category.id && visibleIds.has(child.id)),
      }));
  }, [filteredCategories, rootCategories, subCategories]);
  const categorySlugTaken = useMemo(() => {
    const slug = categoryForm.slug.trim().toLowerCase();
    if (!slug) return false;
    return categories.some((category) => category.id !== editingCategoryId && String(category.slug || '').toLowerCase() === slug);
  }, [categories, categoryForm.slug, editingCategoryId]);

  useEffect(() => {
    setCategorySlugStatus(categorySlugTaken ? 'taken' : 'idle');
  }, [categorySlugTaken]);
  const filteredBrands = useMemo(() => {
    return brands.filter((brand) => {
      const ms = matchesSearch(brand, query, ['name', 'code']);
      const mc = !brandCategoryFilter || (brand.categoryIds && (brand.categoryIds.includes(brandCategoryFilter) || categories.some((c: any) => c.parentId === brandCategoryFilter && brand.categoryIds.includes(c.id))));
      return ms && mc;
    });
  }, [brands, query, brandCategoryFilter, categories]);
  const filteredOrders = useMemo(() => {
    return orders.filter((order) => matchesSearch(order, query, ['id', 'orderCode', 'userId', 'user_id', 'recipientName', 'recipientPhone', 'paymentMethod', 'payment_method', 'trackingCode', 'status']));
  }, [orders, query]);
  const filteredVouchers = useMemo(() => {
    return vouchers.filter((voucher) => matchesSearch(voucher, query, ['code', 'discountType', 'status']));
  }, [vouchers, query]);
  const filteredCustomers = useMemo(() => customers, [customers]);
  const staffUsers = useMemo(() => (
    customers
      .filter((item) => String(item.role || '').toUpperCase() === 'STAFF_ADMIN')
      .sort((a, b) => String(a.role || '').localeCompare(String(b.role || '')))
  ), [customers]);
  const staffBasePermissionCodes = useMemo(() => {
    const staffRole = roles.find((role) => role.code === 'STAFF_ADMIN');
    return staffRole ? (rolePermissionMap[staffRole.id] || []) : [];
  }, [rolePermissionMap, roles]);
  const permissionsByModule = useMemo(() => permissions.reduce<Record<string, any[]>>((groups, permission) => {
    const moduleName = permission.module || 'Khác';
    groups[moduleName] = [...(groups[moduleName] || []), permission];
    return groups;
  }, {}), [permissions]);
  const filteredInventory = useMemo(() => {
    return products.filter((product) => {
      const ms = matchesSearch(product, query, ['name', 'sku', 'brand', 'categoryName', 'status']);
      const mc = !inventoryCategoryFilter || String(product.categoryId) === inventoryCategoryFilter || String(product.subcategoryId) === inventoryCategoryFilter;
      const mb = !inventoryBrandFilter || String(product.brandId) === inventoryBrandFilter || (product.brand && brands.find(b => String(b.id) === inventoryBrandFilter)?.name === product.brand);
      return ms && mc && mb;
    });
  }, [products, query, inventoryCategoryFilter, inventoryBrandFilter, brands]);
  const filteredReviews = useMemo(() => {
    return reviews.filter((review) => {
      const matchesQuery = matchesSearch(review, query, ['productName', 'userName', 'status', 'comment', 'moderationNote', 'shopReply', 'flaggedReason', 'spamReason', 'orderOutcome']);
      const matchesStatus = reviewStatusFilter === 'all' || review.status === reviewStatusFilter;
      const matchesStars = reviewStarFilter === 'all' || String(review.rating) === reviewStarFilter;
      return matchesQuery && matchesStatus && matchesStars;
    });
  }, [reviews, query, reviewStatusFilter, reviewStarFilter]);
  const filteredContentItems = useMemo(() => {
    return contentItems.filter((item) => {
      const matchesQuery = matchesSearch(item, query, ['title', 'description', 'status', 'contentType']);
      const matchesType = contentTypeFilter === 'all' || item.videoCategory === contentTypeFilter;
      const matchesStatus = contentStatusFilter === 'all' || item.status === contentStatusFilter;
      return matchesQuery && matchesType && matchesStatus;
    });
  }, [contentItems, contentStatusFilter, contentTypeFilter, query]);
  const selectedVideoProductIds = useMemo(() => splitIds(contentForm.productIds), [contentForm.productIds]);
  const videoProductChoices = useMemo(() => {
    const keyword = videoProductSearch.trim().toLowerCase();
    return products
      .filter((product) => {
        if (videoProductCategoryFilter !== 'all' && String(product.categoryId || product.category_id || product.category || '') !== videoProductCategoryFilter) return false;
        if (videoProductBrandFilter !== 'all' && String(product.brandId || product.brand_id || product.brand || '') !== videoProductBrandFilter) return false;
        if (!keyword) return true;
        return [product.name, product.sku, product.brand, product.categoryName, product.category]
          .some((value) => String(value || '').toLowerCase().includes(keyword));
      })
      .slice(0, 30);
  }, [products, videoProductBrandFilter, videoProductCategoryFilter, videoProductSearch]);
  const reviewMetrics = useMemo(() => ({
    total: reviews.length,
    pending: reviews.filter((item) => item.status === 'PENDING').length,
    published: reviews.filter((item) => item.status === 'PUBLISHED').length,
    flagged: reviews.filter((item) => item.flaggedReason || item.isSpam).length,
  }), [reviews]);
  const revenue = useMemo(() => orders.reduce((sum, order) => sum + Number(order.totalAmount || order.total_amount || 0), 0), [orders]);
  const tabPermissions: Record<AdminTab, string[]> = {
    overview: ['overview:read'],
    products: ['product:read'],
    categories: ['category:read'],
    brands: ['brand:read'],
    services: ['product:read'],
    orders: ['order:read'],
    vouchers: ['voucher:read'],
    customers: ['customer:read'],
    inventory: ['inventory:read'],
    reviews: ['review:read'],
    content: ['content:read'],
    audit: ['audit:read'],
    permissions: ['sys:manage_roles'],
  };
  const availableTabs = useMemo(() => adminTabs.filter((item) => useAnyPermission(tabPermissions[item.id])), [useAnyPermission]);
  const canManageCustomerAccess = usePermission('sys:manage_users');
  const canManageCustomerProfile = useAnyPermission(['customer:update', 'customer:loyalty_adjust', 'customer:issue_voucher', 'sys:manage_users']);
  const canCreateContent = usePermission('content:create');
  const canUpdateContent = usePermission('content:update');
  const canDeleteContent = usePermission('content:delete');
  const loadedAdminSectionsRef = useRef<Set<AdminTab>>(new Set());
  const preloadingAdminSectionsRef = useRef(false);

  useEffect(() => {
    if (canAccessAdmin) void loadData(tab);
  }, [canAccessAdmin, tab]);

  // Prefetch effect removed to optimize admin loading performance.

  useEffect(() => {
    if (canAccessAdmin && tab === 'categories') {
      void loadCategoryWorkspace(editingCategoryId);
    }
  }, [canAccessAdmin, tab, editingCategoryId]);

  useEffect(() => {
    if (tab !== 'categories' || !editingCategoryId) return;
    if (!categoryMigrationJobs.some((job) => ['PENDING', 'RUNNING', 'IN_PROGRESS'].includes(String(job.status)))) return;
    const timer = window.setInterval(() => {
      void loadCategoryWorkspace(editingCategoryId);
    }, 4000);
    return () => window.clearInterval(timer);
  }, [categoryMigrationJobs, editingCategoryId, tab]);

  useEffect(() => {
    if (canAccessAdmin && tab === 'brands') void loadData('brands', { force: true });
  }, [brandPage, brandStatusFilter, query, tab]);

  useEffect(() => {
    if (tab === 'customers') {
      setCustomerPage(1);
    }
  }, [query]);

  useEffect(() => {
    setBrandPage(1);
  }, [brandStatusFilter, query]);

  useEffect(() => {
    if (!activeBrandImportJob || ['COMPLETED', 'FAILED'].includes(activeBrandImportJob.status)) return;
    const timer = window.setInterval(async () => {
      const nextJob = await apiDb.adminGetBrandImportJob(activeBrandImportJob.id).catch(() => null);
      if (!nextJob) return;
      setActiveBrandImportJob(nextJob);
      if (['COMPLETED', 'FAILED'].includes(nextJob.status)) {
        window.clearInterval(timer);
        await loadData(tab, { force: true });
      }
    }, 3000);
    return () => window.clearInterval(timer);
  }, [activeBrandImportJob?.id, activeBrandImportJob?.status]);

  useEffect(() => {
    if (!availableTabs.some((item) => item.id === tab)) {
      setTab(availableTabs[0]?.id || 'products');
    }
  }, [availableTabs, tab]);

  useEffect(() => {
    if (canAccessAdmin && tab === 'customers') {
      void loadData('customers', { force: true });
    }
  }, [canAccessAdmin, tab, customerPage]);

  const serviceGroupOptions = useMemo(() => {
    const groups = new Set<string>();
    attachedServices.forEach((service) => {
      const group = String(service.attributeGroup || '').trim();
      if (group) groups.add(group);
    });
    return Array.from(groups).sort((left, right) => left.localeCompare(right));
  }, [attachedServices]);

  const productAttachedServiceChoices = useMemo(() => {
    const keyword = attachedServiceSearch.trim().toLowerCase();
    return attachedServices
      .filter((service) => service.isActive !== false)
      .filter((service) => !productForm.attachedServices.some((item) => item.serviceId === service.id))
      .filter((service) => !attachedServiceTypeFilter || service.serviceType === attachedServiceTypeFilter)
      .filter((service) => !attachedServiceGroupFilter || service.attributeGroup === attachedServiceGroupFilter)
      .filter((service) => {
        if (!keyword) return true;
        return [service.name, service.code, service.attributeGroup, service.serviceType]
          .some((value) => String(value || '').toLowerCase().includes(keyword));
      });
  }, [attachedServiceGroupFilter, attachedServiceSearch, attachedServiceTypeFilter, attachedServices, productForm.attachedServices]);

  async function loadData(targetTab: AdminTab = tab, options: { force?: boolean; silent?: boolean; prefetch?: boolean } = {}) {
    if (options.prefetch && loadedAdminSectionsRef.current.has(targetTab)) return;
    if (!options.silent) setBusy(true);
    try {
      const ensureOverview = async () => {
        const overviewData = await apiDb.adminOverview().catch(() => ({}));
        setOverview(overviewData);
      };
      const loadProducts = async () => {
        const productData = await apiDb.adminListProducts().catch(() => apiDb.listProducts());
        setProducts(productData);
      };
      const loadCategories = async () => {
        const categoryData = await apiDb.adminListCategories().catch(() => apiDb.listCategories());
        setCategories(categoryData);
      };
      const loadBrands = async () => {
        const brandData = await apiDb.adminListBrands({ page: brandPage, limit: 1000, search: query, status: brandStatusFilter }).catch(() => apiDb.listBrands().then((items) => ({ items, total: items.length, page: 1, limit: items.length || 1000 })));
        setBrands(Array.isArray(brandData) ? brandData : brandData.items || []);
        setBrandTotal(Array.isArray(brandData) ? brandData.length : brandData.total || 0);
        if (targetTab === 'brands') {
          setBrandImportJobs(await apiDb.adminListBrandImportJobs().catch(() => []));
        }
      };
      const loadServices = async () => {
        const serviceData = await apiDb.adminListAttachedServices().catch(() => []);
        setAttachedServices(serviceData);
      };
      const loadOrders = async () => {
        const orderData = await apiDb.listOrders().catch(() => []);
        setOrders(orderData);
      };
      const loadVouchers = async () => {
        const voucherData = await apiDb.adminListVouchers().catch(() => []);
        setVouchers(voucherData);
      };
      const loadCustomers = async () => {
        const customerData = await apiDb.adminListCustomers({ search: query, page: customerPage, limit: 20 }).catch(() => ({ items: [], total: 0, page: 1, limit: 20 }));
        setCustomers(Array.isArray(customerData) ? customerData : customerData.items || []);
        setCustomerTotal(Array.isArray(customerData) ? customerData.length : customerData.total || 0);
      };
      const loadReviews = async () => {
        const [reviewData, reviewSummaryData] = await Promise.all([
          apiDb.adminListReviews().catch(() => []),
          apiDb.adminListReviewSummary().catch(() => []),
        ]);
        setReviews(reviewData);
        setReviewSummary(reviewSummaryData);
      };
      const loadContent = async () => {
        const contentData = await apiDb.adminListVideos().catch(() => []);
        setContentItems(contentData);
      };
      const loadAudit = async () => {
        const auditData = await apiDb.adminListAuditLogs({ limit: 100 }).catch(() => []);
        setAuditLogs(auditData);
      };
      const loadPermissions = async () => {
        const [permissionData, roleData] = await Promise.all([
          apiDb.adminListPermissions().catch(() => []),
          apiDb.adminListRoles().catch(() => []),
        ]);
        setPermissions(permissionData);
        setRoles(roleData);
        const roleEntries = await Promise.all((roleData || []).map(async (role: any) => {
          const detail = await apiDb.adminGetRolePermissions(role.id).catch(() => ({ permissionCodes: [] }));
          return [role.id, detail.permissionCodes || []] as const;
        }));
        setRolePermissionMap(Object.fromEntries(roleEntries));
      };

      if (options.force) loadedAdminSectionsRef.current.delete(targetTab);
      if (loadedAdminSectionsRef.current.has(targetTab) && !options.force) return;

      if (targetTab === 'overview') {
        await ensureOverview();
      } else if (targetTab === 'products') {
        await Promise.all([loadProducts(), loadCategories(), loadBrands(), loadServices()]);
      } else if (targetTab === 'categories') {
        await loadCategories();
      } else if (targetTab === 'brands') {
        await loadBrands();
      } else if (targetTab === 'services') {
        await loadServices();
      } else if (targetTab === 'orders') {
        await loadOrders();
      } else if (targetTab === 'vouchers') {
        await Promise.all([loadVouchers(), loadProducts(), loadCategories()]);
      } else if (targetTab === 'customers') {
        await Promise.all([loadCustomers(), loadVouchers()]);
      } else if (targetTab === 'inventory') {
        await loadProducts();
      } else if (targetTab === 'reviews') {
        await loadReviews();
      } else if (targetTab === 'content') {
        await Promise.all([loadContent(), loadProducts(), loadCategories(), loadBrands()]);
      } else if (targetTab === 'audit') {
        await loadAudit();
      } else if (targetTab === 'permissions') {
        await Promise.all([loadPermissions(), loadCustomers()]);
      }
      loadedAdminSectionsRef.current.add(targetTab);
    } finally {
      if (!options.silent) setBusy(false);
    }
  }

  async function loadCategoryWorkspace(categoryId?: string | null) {
    setCategoryPanelBusy(true);
    try {
      const [categoryData, metricsData, auditData, migrationData] = await Promise.all([
        apiDb.adminListCategories().catch(() => apiDb.listCategories()),
        apiDb.adminCategoryMetrics().catch(() => ({})),
        categoryId ? apiDb.adminCategoryAuditLogs(categoryId).catch(() => []) : Promise.resolve([]),
        categoryId ? apiDb.adminCategoryMigrationJobs(categoryId).catch(() => []) : Promise.resolve([]),
      ]);
      setCategories(categoryData);
      setCategoryMetrics(metricsData);
      setCategoryAuditLogs(auditData);
      setCategoryMigrationJobs(migrationData);
    } finally {
      setCategoryPanelBusy(false);
    }
  }

  async function refreshCategoryWorkspace(categoryId = editingCategoryId) {
    await loadCategoryWorkspace(categoryId);
  }

  function resetProductForm() {
    setEditingProductId(null);
    setProductForm({ ...emptyProduct, images: [], specifications: {}, variants: [] });
    setAccessorySearch('');
    setAccessoryCategoryFilter('');
    setAccessoryBrandFilter('');
  }

  function resetCategoryForm() {
    setEditingCategoryId(null);
    setCategorySlugStatus('idle');
    setCategoryAuditLogs([]);
    setCategoryMigrationJobs([]);
    setCategoryForm({ name: '', slug: '', icon: 'phone', iconUrl: '', bannerUrl: '', parentId: '', order: 0, isActive: true, status: 'ACTIVE', seoTitle: '', seoDescription: '', seoKeywords: '', specFields: [], filterConfig: [], inventoryPolicy: { inheritImeiPolicy: true, trackImei: false }, warrantyPolicy: { inheritWarrantyPolicy: true, hasWarranty: false, warrantyMonths: 0, allowOneForOne: false, oneForOneDays: 0 }, version: null });
  }

  function resetBrandForm() {
    setEditingBrandId(null);
    setBrandCodeStatus('idle');
    setBrandForm({ name: '', code: '', slug: '', logoUrl: '', logoAltText: '', order: 0, isActive: true, landingTitle: '', seoTitle: '', seoDescription: '' });
  }

  function resetVoucherForm() {
    setEditingVoucherId(null);
    setVoucherForm({
      code: '',
      discountType: 'FIXED',
      discountAmount: 100000,
      minOrderValue: 0,
      maxDiscount: 0,
      usageLimit: 100,
      totalBudgetCap: 0,
      perUserLimit: 1,
      perDeviceLimit: 0,
      perIpLimit: 0,
      campaignType: 'CONVERSION',
      audienceType: 'PUBLIC',
      eligibleTiers: [],
      eligibleUserRegisteredAfter: '',
      assignedUserId: '',
      includeProductIds: '',
      excludeProductIds: '',
      includeCategoryIds: '',
      excludeCategoryIds: '',
      firstOrderOnly: false,
      hiddenCode: false,
      abandonedCartOnly: false,
      validityDaysAfterClaim: 0,
      stackable: false,
      refundPolicy: 'SHOP_FAULT_ONLY',
      startsAt: '',
      endsAt: '',
      internalNote: '',
      status: 'ACTIVE',
    });
  }


  function resetContentForm() {
    setEditingContentId(null);
    setContentForm(emptyContentForm);
  }

  function serializeContentComments(value: string) {
    return value
      .split('\n')
      .map((line) => line.trim())
      .filter(Boolean)
      .map((line, index) => {
        const [userName, ...rest] = line.split(':');
        const content = rest.join(':').trim();
        return {
          id: `draft-${index + 1}`,
          userName: (content ? userName : 'Khách hàng').trim() || 'Khách hàng',
          content: (content || userName).trim(),
          isHidden: false,
        };
      });
  }

  function isConcurrentUpdateError(error: unknown) {
    const message = error instanceof Error ? error.message : '';
    return message.includes('Reload before saving') || message.includes('updated by another admin') || message.includes('409');
  }

  function syncOrderDraft(order: any) {
    setOrderDraft({
      status: order.status || 'PENDING',
      assignedStaffName: order.assignedStaffName || '',
      internalNote: order.internalNote || '',
      cancellationReason: order.cancellationReason || '',
      shippingProvider: order.shippingProvider || '',
      trackingCode: order.trackingCode || '',
      refundPayment: order.paymentMethod && order.paymentMethod !== 'COD' && ['PAID', 'PENDING'].includes(order.paymentStatus || ''),
    });
  }

  async function openOrderPanel(orderId: string) {
    setOrderPanelOpen(true);
    setOrderPanelBusy(true);
    try {
      const detail = await apiDb.getOrderDetail(orderId);
      setSelectedOrder(detail);
      syncOrderDraft(detail);
    } finally {
      setOrderPanelBusy(false);
    }
  }

  function mergeOrderListItem(detail: any) {
    setOrders((items) => items.map((item) => (item.id === detail.id ? { ...item, ...detail } : item)));
  }

  async function updateOrderStatus(id: string, status: string) {
    await apiDb.updateOrderStatus(id, status);
    setOrders((items) => items.map((item) => (item.id === id ? { ...item, status } : item)));
  }

  async function saveOrderDraft() {
    if (!selectedOrder) return;
    setOrderSaving(true);
    try {
      await apiDb.adminUpdateOrder(selectedOrder.id, {
        status: orderDraft.status,
        assigned_staff_name: orderDraft.assignedStaffName || null,
        internal_note: orderDraft.internalNote || null,
        cancellation_reason: orderDraft.cancellationReason || null,
        shipping_provider: orderDraft.shippingProvider || null,
        tracking_code: orderDraft.trackingCode || null,
        refund_payment: orderDraft.refundPayment,
      });
      const detail = await apiDb.getOrderDetail(selectedOrder.id);
      setSelectedOrder(detail);
      syncOrderDraft(detail);
      mergeOrderListItem(detail);
    } finally {
      setOrderSaving(false);
    }
  }

  function printOrderDocument(order: any, mode: 'invoice' | 'delivery') {
    const popup = window.open('', '_blank', 'width=900,height=700');
    if (!popup) return;
    const rows = Array.isArray(order.items) ? order.items : [];
    const title = mode === 'invoice' ? 'Hoa don ban hang' : 'Phieu giao hang';
    const note = mode === 'invoice' ? `Tong thanh toan: ${currency.format(Number(order.totalAmount || 0))}` : `Nguoi nhan: ${order.recipientName || '-'} - ${order.recipientPhone || '-'}`;
    popup.document.write(`
      <html>
        <head><title>${title}</title><style>body{font-family:Arial,sans-serif;padding:24px;color:#0f172a}table{width:100%;border-collapse:collapse;margin-top:16px}th,td{border:1px solid #cbd5e1;padding:8px;text-align:left}h1{margin:0 0 8px}p{margin:4px 0}</style></head>
        <body>
          <h1>${title}</h1>
          <p>Ma don: ${order.orderCode || compactId(order.id)}</p>
          <p>Trang thai: ${statusLabel[order.status] || order.status}</p>
          <p>${note}</p>
          <p>Dia chi giao: ${order.shippingAddress || '-'}</p>
          <table>
            <thead><tr><th>San pham</th><th>SL</th><th>Don gia</th><th>Thanh tien</th></tr></thead>
            <tbody>
              ${rows.map((item: any) => `<tr><td>${item.productName || '-'}</td><td>${item.quantity || 0}</td><td>${currency.format(Number(item.price || 0))}</td><td>${currency.format(Number(item.totalPrice || 0))}</td></tr>`).join('')}
            </tbody>
          </table>
        </body>
      </html>
    `);
    popup.document.close();
    popup.focus();
    popup.print();
  }

  function productPayload() {
    const specifications = {
      ...productForm.specifications,
      _variantSpecKeys: productForm.variantSpecKeys,
      _accessoryOffers: productForm.accessoryOffers.map((item) => ({
        productId: item.productId,
        discountType: item.discountType,
        discountValue: item.discountValue,
        maxQuantity: item.maxQuantity,
      })),
      _attachedServices: productForm.attachedServices.map((item) => ({
        serviceId: item.serviceId,
      })),
      _warrantyPolicy: productForm.warrantyPolicy,
    };
    const sortedVariants = [...productForm.variants].sort((left, right) => {
      const leftColor = `${left.colorName || ''}`.toLowerCase();
      const rightColor = `${right.colorName || ''}`.toLowerCase();
      if (leftColor !== rightColor) return leftColor.localeCompare(rightColor);
      return JSON.stringify(left.specs || {}).localeCompare(JSON.stringify(right.specs || {}));
    });
    return {
      name: productForm.name,
      price: productForm.price,
      imageUrl: productForm.imageUrl || null,
      images: [],
      description: productForm.description || null,
      isFeatured: productForm.isFeatured,
      isFlashSale: productForm.isFlashSale,
      status: productForm.status,
      specifications,
      discountPrice: productForm.discountPrice || null,
      categoryId: productForm.categoryId || null,
      subcategoryId: productForm.subcategoryId || null,
      brandId: productForm.brandId || null,
      videoUrl: productForm.videoUrl || null,
      variants: sortedVariants.map((item) => ({
        ...item,
        sku: item.sku || buildVariantSku(productForm.name, item.colorName, sortedVariants.indexOf(item)),
        storage: '',
        ram: '',
        configuration: '',
        salePrice: item.salePrice || null,
        specs: Object.fromEntries(Object.entries(item.specs || {}).filter(([key]) => productForm.variantSpecKeys.includes(key))),
      })),
      updatedAt: productForm.updatedAt || null,
      version: productForm.version || null,
    };
  }

  async function handleProductSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (editingProductId) {
      await apiDb.adminUpdateProduct(editingProductId, productPayload());
    } else {
      await apiDb.adminCreateProduct(productPayload());
    }
    resetProductForm();
    await loadData(tab, { force: true });
  }

  async function handleCategorySubmit(event: React.FormEvent) {
    event.preventDefault();
    if (categorySlugTaken) {
      window.alert('Slug này đã tồn tại. Vui lòng chọn slug khác.');
      return;
    }
    const payload = {
      ...categoryForm,
      parentId: categoryForm.parentId || null,
      isActive: ['ACTIVE', 'APPROVED'].includes(categoryForm.status),
      specFields: categoryForm.specFields,
      filterConfig: categoryForm.filterConfig.filter((item) => item.source !== 'attribute'),
      version: editingCategoryId ? categoryForm.version : null,
    };
    try {
      if (editingCategoryId) await apiDb.adminUpdateCategory(editingCategoryId, payload);
      else await apiDb.adminCreateCategory(payload);
    } catch (error: any) {
      const message = error instanceof Error ? error.message : '';
      if (message.includes('SPEC_TYPE_CHANGE_REQUIRES_CONFIRMATION') || message.includes('Thay đổi kiểu thông số')) {
        if (!window.confirm('Thay đổi kiểu dữ liệu thông số có thể ảnh hưởng dữ liệu sản phẩm hiện tại. Tiếp tục và tạo phiên bản thông số mới?')) return;
        try {
          if (editingCategoryId) await apiDb.adminUpdateCategory(editingCategoryId, { ...payload, allowSpecTypeMigration: true });
          else await apiDb.adminCreateCategory({ ...payload, allowSpecTypeMigration: true });
        } catch (retryError) {
          if (isConcurrentUpdateError(retryError)) {
            window.alert('Dữ liệu danh mục đã được cập nhật bởi một người khác. Vui lòng tải lại trang rồi thử lại.');
            await refreshCategoryWorkspace(editingCategoryId);
            return;
          }
          throw retryError;
        }
      } else if (isConcurrentUpdateError(error)) {
        window.alert('Dữ liệu danh mục đã được cập nhật bởi một người khác. Vui lòng tải lại trang rồi thử lại.');
        await refreshCategoryWorkspace(editingCategoryId);
        return;
      } else {
        throw error;
      }
    }
    resetCategoryForm();
    await refreshCategoryWorkspace();
  }

  async function handleBrandSubmit(event: React.FormEvent) {
    event.preventDefault();
    const existing = brands.find((item) => item.id === editingBrandId);
    const payload = { ...brandForm, categoryIds: existing?.categoryIds || [] };
    if (payload.code.trim()) {
      const check = await apiDb.adminCheckBrandCode({ code: payload.code.trim(), excludeId: editingBrandId });
      if (!check.available) {
        window.alert('Mã thương hiệu đã tồn tại. Vui lòng chọn mã khác.');
        return;
      }
    }
    if (editingBrandId) await apiDb.adminUpdateBrand(editingBrandId, payload);
    else await apiDb.adminCreateBrand(payload);
    resetBrandForm();
    await loadData(tab, { force: true });
  }

  async function checkBrandCodeOnBlur() {
    const code = brandForm.code.trim();
    if (!code) {
      setBrandCodeStatus('idle');
      return;
    }
    setBrandCodeStatus('checking');
    const result = await apiDb.adminCheckBrandCode({ code, excludeId: editingBrandId });
    setBrandCodeStatus(result.available ? 'available' : 'taken');
  }

  function parseCsvRows(text: string) {
    const rows: string[][] = [];
    let row: string[] = [];
    let cell = '';
    let quoted = false;
    for (let index = 0; index < text.length; index += 1) {
      const char = text[index];
      const next = text[index + 1];
      if (char === '"' && quoted && next === '"') {
        cell += '"';
        index += 1;
      } else if (char === '"') {
        quoted = !quoted;
      } else if (char === ',' && !quoted) {
        row.push(cell.trim());
        cell = '';
      } else if ((char === '\n' || char === '\r') && !quoted) {
        if (char === '\r' && next === '\n') index += 1;
        row.push(cell.trim());
        if (row.some(Boolean)) rows.push(row);
        row = [];
        cell = '';
      } else {
        cell += char;
      }
    }
    row.push(cell.trim());
    if (row.some(Boolean)) rows.push(row);
    return rows;
  }

  async function handleBrandImportFile(files: FileList | null) {
    const file = files?.[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith('.csv')) {
      window.alert('Vui lòng chọn file CSV.');
      return;
    }
    const result = await apiDb.adminImportBrands(file, brandImportMode);
    setActiveBrandImportJob({ id: result.jobId, status: result.status, progress: 0, totalRows: 0, processedRows: 0, importedRows: 0, updatedRows: 0, skippedRows: 0 });
    await loadData(tab, { force: true });
    window.alert(`Đã đưa file vào hàng đợi xử lý. Mã lịch sử: ${result.jobId}`);
  }

  async function handleVoucherSubmit(event: React.FormEvent) {
    event.preventDefault();
    const payload = {
      ...voucherForm,
      maxDiscount: voucherForm.maxDiscount || null,
      totalBudgetCap: voucherForm.totalBudgetCap || null,
      eligibleUserRegisteredAfter: voucherForm.eligibleUserRegisteredAfter || null,
      assignedUserId: voucherForm.assignedUserId || null,
      includeProductIds: splitIds(voucherForm.includeProductIds),
      excludeProductIds: splitIds(voucherForm.excludeProductIds),
      includeCategoryIds: splitIds(voucherForm.includeCategoryIds),
      excludeCategoryIds: splitIds(voucherForm.excludeCategoryIds),
      startsAt: voucherForm.startsAt || null,
      endsAt: voucherForm.endsAt || null,
      hiddenCode: voucherForm.hiddenCode || voucherForm.audienceType === 'HIDDEN',
      firstOrderOnly: voucherForm.firstOrderOnly || voucherForm.audienceType === 'NEW_CUSTOMER',
      abandonedCartOnly: voucherForm.abandonedCartOnly || voucherForm.audienceType === 'ABANDONED_CART',
    };
    if (editingVoucherId) await apiDb.adminUpdateVoucher(editingVoucherId, payload);
    else await apiDb.adminCreateVoucher(payload);
    resetVoucherForm();
    await loadData(tab, { force: true });
  }


  async function handleContentSubmit(event: React.FormEvent) {
    event.preventDefault();
    const payload = {
      ...contentForm,
      contentType: 'VIDEO',
      productIds: splitIds(contentForm.productIds),
      categoryIds: [],
      comments: [],
      sortOrder: Number(contentForm.sortOrder || 0),
      scheduledAt: contentForm.scheduledAt || null,
      publishedAt: contentForm.publishedAt || null,
      videoUrl: contentForm.videoUrl || null,
      thumbnailUrl: contentForm.thumbnailUrl || null,
      bannerImageUrl: null,
      ctaLabel: contentForm.ctaLabel || null,
      ctaUrl: contentForm.ctaUrl || null,
      version: editingContentId ? Number(contentForm.version || 1) : undefined,
    };
    if (editingContentId) await apiDb.adminUpdateVideo(editingContentId, payload);
    else await apiDb.adminCreateVideo(payload);
    resetContentForm();
    await loadData(tab, { force: true });
  }

  function editProduct(product: any) {
    setEditingProductId(product.id);
    const savedVariantSpecKeys = Array.isArray(product.specifications?._variantSpecKeys)
      ? product.specifications._variantSpecKeys
      : Array.from(new Set((product.variants || []).flatMap((item: any) => Object.keys(item.specs || {}))));
    const cleanSpecifications = { ...(product.specifications || {}) };
    productExtraKeys.forEach((key) => delete cleanSpecifications[key]);
    setProductForm({
      ...emptyProduct,
      name: product.name || '',
      price: Number(product.price || 0),
      discountPrice: Number(product.discountPrice || 0),
      brand: product.brand || '',
      category: product.category || 'ACCESSORY',
      categoryId: product.categoryId || '',
      subcategoryId: product.subcategoryId || '',
      brandId: product.brandId || '',
      imageUrl: product.imageUrl || '',
      images: [],
      videoUrl: product.videoUrl || '',
      description: product.description || '',
      specifications: cleanSpecifications,
      seoTitle: product.seoMetadata?.title || product.specifications?._seoTitle || '',
      seoDescription: product.seoMetadata?.description || product.specifications?._seoDescription || '',
      seoSlug: product.seoMetadata?.slug || product.specifications?._seoSlug || product.slug || '',
      accessoryOffers: (product.salesConfig?.accessoryOffers || []).map((item: any) => ({
        productId: item.productId || '',
        productName: item.productName || '',
        productSku: item.productSku || '',
        imageUrl: item.imageUrl || '',
        discountType: item.discountType === 'FIXED' ? 'FIXED' : 'PERCENT',
        discountValue: Number(item.discountValue || 0),
        maxQuantity: Number(item.maxQuantity || 1),
      })),
      attachedServices: (product.salesConfig?.attachedServices || []).map((item: any) => ({
        serviceId: item.serviceId || '',
        name: item.name || '',
        code: item.code || '',
        serviceType: item.serviceType || 'SUPPORT_SERVICE',
        attributeGroup: item.attributeGroup || '',
        durationMonths: Number(item.durationMonths || 0),
        priceMode: item.priceMode || 'FIXED',
        fixedPrice: Number(item.fixedPrice || 0),
        percentValue: Number(item.percentValue || 0),
      })),
      warrantyPolicy: normalizeWarrantyPolicy(product.salesConfig?.warrantyPolicy || product.specifications?._warrantyPolicy || defaultWarrantyPolicy),
      updatedAt: product.updatedAt || '',
      version: Number(product.version || 1),
      variantSpecKeys: savedVariantSpecKeys,
      variants: (product.variants || []).map((item: any) => ({
        ...emptyVariant,
        id: item.id,
        sku: item.sku || '',
        colorName: item.colorName || '',
        colorCode: item.colorCode || '#111827',
        storage: item.storage || '',
        ram: item.ram || '',
        configuration: item.configuration || '',
        specs: item.specs || {},
        imageUrl: item.imageUrl || '',
        price: Number(item.price || 0),
        salePrice: Number(item.salePrice || 0),
        isActive: item.isActive !== false,
      })),
      status: product.status || 'ACTIVE',
      isFeatured: Boolean(product.isFeatured),
      isFlashSale: Boolean(product.isFlashSale),
    });
  }

  function editCategory(category: any) {
    setEditingCategoryId(category.id);
    setCategorySlugStatus('idle');
    setCategoryForm({
      name: category.name || '',
      slug: category.slug || '',
      icon: category.icon || 'phone',
      iconUrl: category.iconUrl || '',
      bannerUrl: category.bannerUrl || '',
      parentId: category.parentId || '',
      order: Number(category.order || 0),
      isActive: category.isActive !== false,
      status: category.status || (category.isActive === false ? 'INACTIVE' : 'ACTIVE'),
      seoTitle: category.seoTitle || '',
      seoDescription: category.seoDescription || '',
      seoKeywords: category.seoKeywords || '',
      specFields: category.ownSpecFields || category.specFields || [],
      filterConfig: category.ownFilterConfig || category.filterConfig || [],
      inventoryPolicy: category.inventoryPolicy || { inheritImeiPolicy: true, trackImei: false },
      warrantyPolicy: category.warrantyPolicy || { inheritWarrantyPolicy: true, hasWarranty: false, warrantyMonths: 0, allowOneForOne: false, oneForOneDays: 0 },
      version: Number(category.version || 1),
    });
  }

  function editBrand(brand: any) {
    setEditingBrandId(brand.id);
    setBrandForm({
      name: brand.name || '',
      code: brand.code || '',
      slug: brand.slug || '',
      logoUrl: brand.logoUrl || '',
      logoAltText: brand.logoAltText || '',
      order: Number(brand.order || 0),
      isActive: brand.isActive !== false,
      landingTitle: brand.landingTitle || '',
      seoTitle: brand.seoTitle || '',
      seoDescription: brand.seoDescription || '',
    });
  }

  function editVoucher(voucher: any) {
    setEditingVoucherId(voucher.id);
    setVoucherForm({
      code: voucher.code || '',
      discountType: voucher.discountType || 'FIXED',
      discountAmount: Number(voucher.discountAmount || 0),
      minOrderValue: Number(voucher.minOrderValue || 0),
      maxDiscount: Number(voucher.maxDiscount || 0),
      usageLimit: Number(voucher.usageLimit || 0),
      totalBudgetCap: Number(voucher.totalBudgetCap || 0),
      perUserLimit: Number(voucher.perUserLimit || 0),
      perDeviceLimit: Number(voucher.perDeviceLimit || 0),
      perIpLimit: Number(voucher.perIpLimit || 0),
      campaignType: voucher.campaignType || 'CONVERSION',
      audienceType: voucher.audienceType || 'PUBLIC',
      eligibleTiers: Array.isArray(voucher.eligibleTiers) ? voucher.eligibleTiers : [],
      eligibleUserRegisteredAfter: voucher.eligibleUserRegisteredAfter ? String(voucher.eligibleUserRegisteredAfter).slice(0, 16) : '',
      assignedUserId: voucher.assignedUserId || '',
      includeProductIds: Array.isArray(voucher.includeProductIds) ? voucher.includeProductIds.join(', ') : '',
      excludeProductIds: Array.isArray(voucher.excludeProductIds) ? voucher.excludeProductIds.join(', ') : '',
      includeCategoryIds: Array.isArray(voucher.includeCategoryIds) ? voucher.includeCategoryIds.join(', ') : '',
      excludeCategoryIds: Array.isArray(voucher.excludeCategoryIds) ? voucher.excludeCategoryIds.join(', ') : '',
      firstOrderOnly: Boolean(voucher.firstOrderOnly),
      hiddenCode: Boolean(voucher.hiddenCode),
      abandonedCartOnly: Boolean(voucher.abandonedCartOnly),
      validityDaysAfterClaim: Number(voucher.validityDaysAfterClaim || 0),
      stackable: Boolean(voucher.stackable),
      refundPolicy: voucher.refundPolicy || 'SHOP_FAULT_ONLY',
      startsAt: voucher.startsAt ? String(voucher.startsAt).slice(0, 16) : '',
      endsAt: voucher.endsAt ? String(voucher.endsAt).slice(0, 16) : '',
      internalNote: voucher.internalNote || '',
      status: voucher.status || 'ACTIVE',
    });
  }


  function editContent(item: any) {
    setEditingContentId(item.id);
    setContentForm({
      title: item.title || '',
      description: item.description || '',
      contentType: item.contentType || 'VIDEO',
      videoSource: item.videoSource || 'UPLOAD',
      videoCategory: item.videoCategory || 'PRODUCT',
      status: item.status || 'DRAFT',
      videoUrl: item.videoUrl || '',
      thumbnailUrl: item.thumbnailUrl || '',
      bannerImageUrl: item.bannerImageUrl || '',
      contentBody: item.contentBody || '',
      ctaLabel: item.ctaLabel || '',
      ctaUrl: item.ctaUrl || '',
      productIds: Array.isArray(item.productIds) ? item.productIds.join(', ') : '',
      categoryIds: Array.isArray(item.categoryIds) ? item.categoryIds.join(', ') : '',
      commentsText: Array.isArray(item.comments) ? item.comments.map((comment: any) => `${comment.userName || 'Khách hàng'}: ${comment.content || ''}`).join('\n') : '',
      likeCount: Number(item.likeCount || 0),
      viewCount: Number(item.viewCount || 0),
      sortOrder: Number(item.sortOrder || 0),
      scheduledAt: item.scheduledAt ? String(item.scheduledAt).slice(0, 16) : '',
      publishedAt: item.publishedAt ? String(item.publishedAt).slice(0, 16) : '',
      isActive: item.isActive !== false,
      version: Number(item.version || 1),
    });
  }

  function setVideoProductSelected(productId: string, selected: boolean) {
    const current = new Set(splitIds(contentForm.productIds));
    if (selected) current.add(productId);
    else current.delete(productId);
    setContentForm({ ...contentForm, productIds: Array.from(current).join(', ') });
  }

  async function replyVideoComment(video: any, comment: any) {
    const body = (videoReplyDrafts[comment.id] || '').trim();
    if (!body) return;
    await apiDb.adminReplyVideoComment(video.id, comment.id, body);
    setVideoReplyDrafts((drafts) => ({ ...drafts, [comment.id]: '' }));
    await loadData(tab, { force: true });
  }

  async function toggleVideoCommentHidden(video: any, comment: any) {
    await apiDb.adminUpdateVideoComment(video.id, comment.id, { isHidden: !comment.isHidden });
    await loadData(tab, { force: true });
  }

  async function confirmDelete(label: string, action: () => Promise<unknown>) {
    if (!window.confirm(`Bạn có chắc muốn xóa ${label}? Nếu mục này đã có dữ liệu liên quan, hệ thống sẽ ẩn thay vì xóa để giữ lịch sử.`)) return;
    try {
      const result = await action() as { action?: string };
      await loadData(tab, { force: true });
      if (result?.action === 'deleted') {
        window.alert(`${label} đã được xóa vì chưa có ràng buộc dữ liệu.`);
      } else if (result?.action === 'archived') {
        window.alert(`${label} đã được lưu trữ.`);
      } else if (result?.action === 'deactivated') {
        window.alert(`${label} đã có dữ liệu liên quan nên đã được ẩn.`);
      }
    } catch (error) {
      window.alert(error instanceof Error ? error.message : 'Không thể xóa mục này.');
    }
  }

  async function reactivateProduct(product: any) {
    await apiDb.adminUpdateProduct(product.id, { ...product, status: 'ACTIVE', discountPrice: product.discountPrice || null });
    await loadData(tab, { force: true });
  }

  async function openInventoryDialog(product: any, variant?: any) {
    const detail = await apiDb.adminGetProductInventory(product.id);
    const inventorySettings = getInventorySettings(detail);
    setInventoryDraft({
      product,
      variant,
      transactionType: 'RECEIPT',
      delta: 1,
      referenceCode: '',
      reason: variant ? `Điều chỉnh ${variant.sku || 'biến thể'}` : `Điều chỉnh ${product.sku || product.name}`,
      note: '',
      supplierName: '',
      unitCost: 0,
      locationCode: detail.preferredLocationCode || inventorySettings.preferredLocationCode || '',
      locationName: detail.preferredLocationName || inventorySettings.preferredLocationName || '',
      imeis: '',
      minimumStock: detail.minimumStock ?? inventorySettings.minimumStock,
      blockSaleWhenOutOfStock: detail.blockSaleWhenOutOfStock ?? inventorySettings.blockSaleWhenOutOfStock,
      cycleCountDays: detail.cycleCountDays ?? inventorySettings.cycleCountDays,
      logs: detail.logs || [],
    });
  }

  async function submitInventoryDraft(event: React.FormEvent) {
    event.preventDefault();
    if (!inventoryDraft) return;
    if (!inventoryDraft.referenceCode.trim()) {
      window.alert('Vui lòng nhập mã phiếu tham chiếu.');
      return;
    }
    if (!Number.isFinite(inventoryDraft.delta) || inventoryDraft.delta === 0) {
      window.alert('Số lượng thay đổi phải khác 0.');
      return;
    }
    await apiDb.adminUpdateInventorySettings(inventoryDraft.product.id, {
      minimumStock: inventoryDraft.minimumStock,
      blockSaleWhenOutOfStock: inventoryDraft.blockSaleWhenOutOfStock,
      preferredLocationCode: inventoryDraft.locationCode.trim(),
      preferredLocationName: inventoryDraft.locationName.trim(),
      cycleCountDays: inventoryDraft.cycleCountDays,
    });
    await apiDb.adminAdjustInventory(inventoryDraft.product.id, {
      variantId: inventoryDraft.variant?.id || null,
      delta: inventoryDraft.delta,
      transactionType: inventoryDraft.transactionType,
      referenceCode: inventoryDraft.referenceCode.trim(),
      reason: inventoryDraft.reason || inventoryDraft.transactionType,
      note: inventoryDraft.note || null,
      supplierName: inventoryDraft.supplierName.trim() || null,
      unitCost: Number.isFinite(inventoryDraft.unitCost) && inventoryDraft.unitCost > 0 ? inventoryDraft.unitCost : null,
      locationCode: inventoryDraft.locationCode.trim() || null,
      locationName: inventoryDraft.locationName.trim() || null,
      imeis: inventoryDraft.imeis.split(/[\n,]/).map((item) => item.trim()).filter(Boolean),
    });
    setInventoryDraft(null);
    await loadData(tab, { force: true });
  }

  async function exportInventorySnapshot() {
    const blob = await apiDb.adminExportInventory(query.trim());
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `inventory-export-${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  }

  async function submitProduct(product: any) {
    await apiDb.adminSubmitProduct(product.id);
    await loadData(tab, { force: true });
  }

  async function approveProduct(product: any) {
    await apiDb.adminApproveProduct(product.id);
    await loadData(tab, { force: true });
  }

  async function duplicateProduct(product: any) {
    const result = await apiDb.adminDuplicateProduct(product.id);
    await loadData(tab, { force: true });
    window.alert(`Đã sao chép sản phẩm sang bản nháp mới: ${result.id}`);
  }

  async function bulkApproveProducts() {
    const ids = selectedProductIds.filter((id) => products.find((product) => product.id === id)?.status === 'PENDING');
    if (ids.length > 500) {
      window.alert('Mỗi lần chỉ duyệt tối đa 500 sản phẩm. Vui lòng chia nhỏ danh sách.');
      return;
    }
    if (!ids.length) {
      window.alert('Chọn ít nhất một sản phẩm đang chờ duyệt.');
      return;
    }
    const result = await apiDb.adminBulkApproveProducts(ids);
    setSelectedProductIds([]);
    await loadData(tab, { force: true });
    window.alert(`Đã duyệt ${result.updated} sản phẩm. Bỏ qua: ${result.skipped.length}.`);
  }

  async function exportProducts() {
    const result = await apiDb.adminExportProducts({ search: query });
    window.alert(`Đã đưa yêu cầu xuất file vào hàng đợi. Mã job: ${result.jobId}`);
  }

  async function importProducts(files: FileList | null) {
    const file = files?.[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith('.csv')) {
      window.alert('Vui lòng chọn file CSV.');
      return;
    }
    const result = await apiDb.adminImportProducts(file);
    window.alert(`Đã đưa file vào hàng đợi import. Mã job: ${result.jobId}`);
    window.setTimeout(loadData, 1500);
  }

  async function archiveProduct(product: any) {
    await apiDb.adminArchiveProduct(product.id);
    await loadData(tab, { force: true });
  }

  async function reactivateCategory(category: any) {
    await apiDb.adminRestoreCategory(category.id);
    await refreshCategoryWorkspace(category.id);
    window.alert('Danh mục đã được khôi phục. Các sản phẩm thuộc danh mục này vẫn đang ở trạng thái Ẩn. Vui lòng vào Quản lý sản phẩm để kích hoạt lại nếu cần.');
  }

  async function reactivateBrand(brand: any) {
    await apiDb.adminUpdateBrandStatus(brand.id, true);
    await loadData(tab, { force: true });
  }

  async function hideBrand(brand: any) {
    if (!window.confirm(`Ẩn thương hiệu ${brand.name}? Thương hiệu sẽ không hiển thị ở storefront.`)) return;
    await apiDb.adminUpdateBrandStatus(brand.id, false);
    await loadData(tab, { force: true });
  }

  async function bulkUpdateBrandStatus(isActive: boolean) {
    if (!selectedBrandIds.length) return;
    if (!window.confirm(`${isActive ? 'Khôi phục' : 'Ẩn'} ${selectedBrandIds.length} thương hiệu đã chọn?`)) return;
    const result = await apiDb.adminUpdateBrandsStatus(selectedBrandIds, isActive);
    setSelectedBrandIds([]);
    await loadData(tab, { force: true });
    window.alert(`Đã cập nhật ${result.updated} thương hiệu. Lỗi: ${result.failed.length}.`);
  }

  function addSpecField() {
    setCategoryForm((prev) => ({
      ...prev,
      specFields: [...prev.specFields, { key: '', label: '', group: 'Thông số chung', type: 'text', required: false, variant: false, isFilterable: false, filterType: 'checkbox', filterEnabled: true }],
    }));
  }

  function patchSpecField(index: number, patch: Partial<SpecField>) {
    setCategoryForm((prev) => ({ ...prev, specFields: prev.specFields.map((item, i) => (i === index ? { ...item, ...patch } : item)) }));
  }

  function addCategoryFilter() {
    setCategoryForm((prev) => ({
      ...prev,
      filterConfig: [...prev.filterConfig, { key: '', label: '', type: 'checkbox', enabled: true }],
    }));
  }

  function patchCategoryFilter(index: number, patch: Partial<CategoryFilterField>) {
    setCategoryForm((prev) => ({ ...prev, filterConfig: prev.filterConfig.map((item, i) => (i === index ? { ...item, ...patch } : item)) }));
  }

  const derivedCategoryFilters = useMemo(() => {
    const fromAttributes = categoryForm.specFields
      .filter((field) => field.key && field.isFilterable)
      .map((field) => ({
        key: field.key,
        label: field.label || field.key,
        type: field.filterType || (field.type === 'number' ? 'range' : 'checkbox'),
        enabled: field.filterEnabled !== false,
        source: 'attribute',
      }));
    const manual = categoryForm.filterConfig.filter((field) => field.source !== 'attribute' && !fromAttributes.some((item) => item.key === field.key));
    return [...fromAttributes, ...manual];
  }, [categoryForm.filterConfig, categoryForm.specFields]);

  async function reorderCategory(draggedId: string, targetId: string) {
    if (draggedId === targetId) return;
    const dragged = categories.find((item) => item.id === draggedId);
    const target = categories.find((item) => item.id === targetId);
    if (!dragged || !target || (dragged.parentId || '') !== (target.parentId || '')) return;
    const siblings = categories.filter((item) => (item.parentId || '') === (dragged.parentId || '')).sort((a, b) => Number(a.order || 0) - Number(b.order || 0));
    const nextSiblings = siblings.filter((item) => item.id !== draggedId);
    nextSiblings.splice(nextSiblings.findIndex((item) => item.id === targetId), 0, dragged);
    setCategories((items) => items.map((item) => {
      const index = nextSiblings.findIndex((sibling) => sibling.id === item.id);
      return index >= 0 ? { ...item, order: index + 1 } : item;
    }));
    await apiDb.adminReorderCategories(nextSiblings.map((item, index) => ({
      id: item.id,
      parentId: item.parentId || null,
      order: index + 1,
    })));
    await refreshCategoryWorkspace(editingCategoryId || draggedId);
  }

  async function checkCategorySlug() {
    const slug = categoryForm.slug.trim();
    if (!slug) return;
    if (categorySlugTaken) {
      setCategorySlugStatus('taken');
      return;
    }
    setCategorySlugStatus('checking');
    try {
      await apiDb.adminCheckCategorySlug({ slug, excludeId: editingCategoryId });
      setCategorySlugStatus('available');
    } catch {
      setCategorySlugStatus('taken');
    }
  }

  function addVariant() {
    setProductForm((prev) => ({ ...prev, variants: [...prev.variants, { ...emptyVariant, price: prev.price, salePrice: prev.discountPrice }] }));
  }

  function patchVariant(index: number, patch: Partial<VariantForm>) {
    setProductForm((prev) => ({ ...prev, variants: prev.variants.map((item, i) => (i === index ? { ...item, ...patch } : item)) }));
  }

  function addAccessoryOffer(item: any) {
    setProductForm((prev) => ({
      ...prev,
      accessoryOffers: [
        ...prev.accessoryOffers,
        {
          productId: item.id,
          productName: item.name || '',
          productSku: item.sku || '',
          imageUrl: item.imageUrl || '',
          discountType: 'PERCENT',
          discountValue: 25,
          maxQuantity: 1,
        },
      ],
    }));
    setAccessorySearch('');
  }

  function patchAccessoryOffer(productId: string, patch: Partial<AccessoryOfferForm>) {
    setProductForm((prev) => ({
      ...prev,
      accessoryOffers: prev.accessoryOffers.map((item) => (item.productId === productId ? { ...item, ...patch } : item)),
    }));
  }

  function removeAccessoryOffer(productId: string) {
    setProductForm((prev) => ({
      ...prev,
      accessoryOffers: prev.accessoryOffers.filter((item) => item.productId !== productId),
    }));
  }

  function addAttachedService(service: any) {
    const group = String(service.attributeGroup || '').trim();
    if (group && productForm.attachedServices.some((item) => item.serviceType === service.serviceType && item.attributeGroup === group)) {
      window.alert('Mỗi nhóm thuộc tính của dịch vụ chỉ được chọn một lựa chọn. Hãy bỏ lựa chọn cũ trước khi chọn lựa chọn mới.');
      return;
    }
    setProductForm((prev) => prev.attachedServices.some((item) => item.serviceId === service.id)
      ? prev
      : {
        ...prev,
        attachedServices: [
          ...prev.attachedServices,
          {
            serviceId: service.id,
            name: service.name || '',
            code: service.code || '',
            serviceType: service.serviceType || 'SUPPORT_SERVICE',
            attributeGroup: service.attributeGroup || '',
            durationMonths: Number(service.durationMonths || 0),
            priceMode: service.priceMode || 'FIXED',
            fixedPrice: Number(service.fixedPrice || 0),
            percentValue: Number(service.percentValue || 0),
          },
        ],
      });
  }

  function removeAttachedService(serviceId: string) {
    setProductForm((prev) => ({ ...prev, attachedServices: prev.attachedServices.filter((item) => item.serviceId !== serviceId) }));
  }

  function editService(service: any) {
    setEditingServiceId(service.id);
    setServiceFormOpen(true);
    setServiceForm({
      code: service.code || '',
      name: service.name || '',
      serviceType: service.serviceType || 'SUPPORT_SERVICE',
      attributeGroup: service.attributeGroup || '',
      durationMonths: Number(service.durationMonths || 0),
      priceMode: service.serviceType === 'PRODUCT_SERVICE' ? 'TIERED_AMOUNT' : service.priceMode || 'FIXED',
      fixedPrice: Number(service.fixedPrice || 0),
      percentValue: Number(service.percentValue || 0),
      baseAmount: Number(service.baseAmount || 0),
      isActive: service.isActive !== false,
    });
  }

  function resetServiceForm() {
    setEditingServiceId(null);
    setServiceFormOpen(false);
    setServiceForm({ code: '', name: '', serviceType: 'SUPPORT_SERVICE', attributeGroup: '', durationMonths: 0, priceMode: 'FIXED', fixedPrice: 0, percentValue: 0, baseAmount: 0, isActive: true });
  }

  async function handleServiceSubmit(event: React.FormEvent) {
    event.preventDefault();
    const payload = serviceForm.serviceType === 'PRODUCT_SERVICE'
      ? { ...serviceForm, priceMode: 'TIERED_AMOUNT', fixedPrice: 0, percentValue: 0, baseAmount: 0 }
      : serviceForm;
    if (editingServiceId) await apiDb.adminUpdateAttachedService(editingServiceId, payload);
    else await apiDb.adminCreateAttachedService(payload);
    resetServiceForm();
    await loadData(tab, { force: true });
  }

  function toggleVariantSpecField(key: string, checked: boolean) {
    setProductForm((prev) => ({
      ...prev,
      variantSpecKeys: checked ? [...new Set([...prev.variantSpecKeys, key])] : prev.variantSpecKeys.filter((item) => item !== key),
      variants: checked
        ? prev.variants
        : prev.variants.map((variant) => {
          const specs = { ...variant.specs };
          delete specs[key];
          return { ...variant, specs };
        }),
    }));
  }

  async function updateReviewStatus(review: any, status: 'PENDING' | 'PUBLISHED' | 'HIDDEN' | 'REJECTED') {
    await apiDb.adminUpdateReview(review.id, { status });
    await loadData(tab, { force: true });
  }

  async function replyToReview(review: any) {
    const nextReply = window.prompt(`Phản hồi đánh giá cho ${review.userName || 'khách hàng'}`, review.shopReply || '');
    if (nextReply === null) return;
    await apiDb.adminUpdateReview(review.id, { shopReply: nextReply });
    await loadData(tab, { force: true });
  }

  async function flagReview(review: any) {
    const reason = window.prompt(`Lý do báo cáo/đánh dấu đánh giá của ${review.userName || 'khách hàng'}`, review.flaggedReason || 'Có dấu hiệu nội dung xấu hoặc cần xem xét thêm');
    if (reason === null) return;
    await apiDb.adminUpdateReview(review.id, { flaggedReason: reason, status: review.status === 'PUBLISHED' ? 'HIDDEN' : review.status });
    await loadData(tab, { force: true });
  }

  async function markReviewSpam(review: any) {
    const reason = window.prompt(`Lý do đánh dấu spam cho đánh giá của ${review.userName || 'khách hàng'}`, review.spamReason || 'Spam hoặc nội dung lặp bất thường');
    if (reason === null) return;
    await apiDb.adminUpdateReview(review.id, { isSpam: true, spamReason: reason, status: 'REJECTED', moderationNote: 'Đánh dấu spam bởi quản trị viên.' });
    await loadData(tab, { force: true });
  }

  async function deleteReview(review: any) {
    if (!window.confirm(`Xóa vĩnh viễn đánh giá của ${review.userName || 'khách hàng'} cho sản phẩm ${review.productName}?`)) return;
    await apiDb.adminDeleteReview(review.id);
    await loadData(tab, { force: true });
  }

  async function updateUserAccess(customer: any, patch: { role?: string; status?: string }) {
    if (!usePermission('sys:manage_users')) return;
    if (customer.role === 'SUPER_ADMIN' || patch.role === 'SUPER_ADMIN') return;
    await apiDb.adminUpdateUserRole(customer.id, {
      role: patch.role || customer.role || 'CUSTOMER',
      status: patch.status || customer.status || 'ACTIVE',
      permissionCodes: patch.role === 'STAFF_ADMIN' || (!patch.role && customer.role === 'STAFF_ADMIN') ? (customer.extraPermissionCodes || []) : [],
    });
    setEditingStaffAccessId(null);
    await loadData(tab, { force: true });
  }

  async function createStaffAccount(event: React.FormEvent) {
    event.preventDefault();
    if (!canManageCustomerAccess || !staffForm.email.trim() || !staffForm.password || !staffForm.fullName.trim()) return;
    await apiDb.adminCreateStaff({
      email: staffForm.email.trim(),
      password: staffForm.password,
      fullName: staffForm.fullName.trim(),
      phone: staffForm.phone.trim() || undefined,
      status: staffForm.status,
      permissionCodes: [],
    });
    setStaffForm({ email: '', password: '', fullName: '', phone: '', status: 'ACTIVE', permissionCodes: [] });
    await loadData(tab, { force: true });
  }

  async function openStaffPermissionEditor(staff: any) {
    if (!canManageCustomerAccess) return;
    const detail = await apiDb.adminGetUserPermissions(staff.id).catch(() => ({ permissionCodes: staff.extraPermissionCodes || [] }));
    setStaffPermissionEditor(staff);
    setStaffPermissionDraft(detail.permissionCodes || []);
  }

  async function saveStaffPermissions() {
    if (!staffPermissionEditor?.id || !canManageCustomerAccess) return;
    await apiDb.adminUpdateUserPermissions(staffPermissionEditor.id, staffPermissionDraft);
    setStaffPermissionEditor(null);
    setStaffPermissionDraft([]);
    await loadData(tab, { force: true });
  }

  async function openCustomerDetail(customer: any) {
    setCustomerDetailOpen(true);
    setCustomerDetailBusy(true);
    setCustomerActiveSection('summary');
    try {
      const detail = await apiDb.adminGetCustomerOverview(customer.id);
      setSelectedCustomer(detail);
      setCustomerOrders([]);
      setCustomerLoyaltyHistory([]);
      setCustomerNotes([]);
      setCustomerAuditLogs([]);
      setCustomerTagDraft(Array.isArray(detail.tags) ? detail.tags.join(', ') : '');
      setCustomerVoucherId('');
      setCustomerVoucherNote('');
      setCustomerPointDelta('0');
      setCustomerPointReason('');
      setCustomerNoteDraft('');
    } finally {
      setCustomerDetailBusy(false);
    }
  }

  async function refreshSelectedCustomer() {
    if (!selectedCustomer?.id) return;
    const detail = await apiDb.adminGetCustomerOverview(selectedCustomer.id);
    setSelectedCustomer(detail);
    setCustomerTagDraft(Array.isArray(detail.tags) ? detail.tags.join(', ') : '');
    await loadData(tab, { force: true });
  }

  async function loadCustomerSection(section: 'orders' | 'loyalty' | 'notes' | 'audit') {
    if (!selectedCustomer?.id) return;
    setCustomerActiveSection(section);
    if (section === 'orders' && customerOrders.length === 0) {
      setCustomerOrders(await apiDb.adminGetCustomerOrders(selectedCustomer.id).catch(() => []));
    }
    if (section === 'loyalty' && customerLoyaltyHistory.length === 0) {
      setCustomerLoyaltyHistory(await apiDb.adminGetCustomerLoyaltyHistory(selectedCustomer.id).catch(() => []));
    }
    if (section === 'notes' && customerNotes.length === 0) {
      setCustomerNotes(await apiDb.adminGetCustomerNotes(selectedCustomer.id).catch(() => []));
    }
    if (section === 'audit' && customerAuditLogs.length === 0) {
      setCustomerAuditLogs(await apiDb.adminGetCustomerAuditLogs(selectedCustomer.id).catch(() => []));
    }
  }

  async function saveCustomerTags() {
    if (!selectedCustomer?.id || !useAnyPermission(['customer:update', 'sys:manage_users'])) return;
    const tags = customerTagDraft.split(',').map((item) => item.trim()).filter(Boolean);
    await apiDb.adminUpdateCustomerTags(selectedCustomer.id, tags);
    await refreshSelectedCustomer();
  }

  async function addCustomerNote() {
    if (!selectedCustomer?.id || !customerNoteDraft.trim() || !useAnyPermission(['customer:update', 'sys:manage_users'])) return;
    await apiDb.adminCreateCustomerNote(selectedCustomer.id, customerNoteDraft.trim());
    setCustomerNoteDraft('');
    await refreshSelectedCustomer();
  }

  async function adjustCustomerPoints() {
    if (!selectedCustomer?.id || !usePermission('customer:loyalty_adjust')) return;
    const delta = Number(customerPointDelta || 0);
    if (!delta || !customerPointReason.trim()) return;
    await apiDb.adminAdjustCustomerLoyalty(selectedCustomer.id, { delta, reason: customerPointReason.trim() });
    setCustomerPointDelta('0');
    setCustomerPointReason('');
    await refreshSelectedCustomer();
  }

  async function issueCustomerVoucher() {
    if (!selectedCustomer?.id || !customerVoucherId || !usePermission('customer:issue_voucher')) return;
    await apiDb.adminIssueCustomerVoucher(selectedCustomer.id, { voucherId: customerVoucherId, note: customerVoucherNote.trim() || undefined });
    setCustomerVoucherId('');
    setCustomerVoucherNote('');
    await refreshSelectedCustomer();
  }

  async function bulkSuspendCustomers() {
    if (!selectedCustomerIds.length || !canManageCustomerAccess) return;
    await apiDb.adminBulkUpdateUserStatus(selectedCustomerIds, 'SUSPENDED');
    setSelectedCustomerIds([]);
    await loadData(tab, { force: true });
  }

  async function bulkApplyCustomerTags() {
    if (!selectedCustomerIds.length || !canManageCustomerProfile) return;
    const tags = customerTagDraft.split(',').map((item) => item.trim()).filter(Boolean);
    await apiDb.adminBulkUpdateCustomerTags(selectedCustomerIds, tags);
    setSelectedCustomerIds([]);
    await loadData(tab, { force: true });
  }

  async function toggleRolePermission(roleId: string, code: string, checked: boolean) {
    const current = rolePermissionMap[roleId] || [];
    const next = checked ? [...new Set([...current, code])] : current.filter((item) => item !== code);
    setRolePermissionMap((prev) => ({ ...prev, [roleId]: next }));
    await apiDb.adminUpdateRolePermissions(roleId, next);
    await loadData(tab, { force: true });
  }

  if (loading || !canAccessAdmin) return <div className="flex min-h-[60vh] items-center justify-center text-sm font-semibold text-slate-500">Đang kiểm tra quyền truy cập...</div>;

  const stats = [
    { label: 'Doanh thu', value: currency.format(overview?.revenue || 0), icon: WalletCards, tone: 'emerald', caption: `${overview?.orders?.total || 0} đơn đã ghi nhận` },
    { label: 'Sản phẩm', value: overview?.products?.total || 0, icon: Package, tone: 'red', caption: `${overview?.products?.active || 0} đang bán` },
    { label: 'Đơn hàng', value: overview?.orders?.total || 0, icon: Truck, tone: 'sky', caption: `${overview?.orders?.pending || 0} chờ xử lý` },
    { label: 'Voucher', value: overview?.vouchers?.total || 0, icon: BadgePercent, tone: 'amber', caption: `${overview?.vouchers?.active || 0} đang chạy` },
  ];

  const roleDashboards = [
    { role: 'Nhân viên kho', metric: `${(overview?.lowStockCount || 0) + (overview?.negativeStockCount || 0)} cảnh báo`, helper: 'Thiếu hàng, tồn kho âm hoặc cần kiểm kê', icon: Boxes },
    { role: 'CSKH', metric: `${(overview?.orders?.pending || 0) + (overview?.orders?.processing || 0)} đơn cần theo dõi`, helper: 'Ưu tiên đơn chờ xử lý và phản hồi mới', icon: UserCircle },
    { role: 'Quản lý', metric: currency.format(overview?.revenue || 0), helper: 'Theo dõi doanh thu, tỉ lệ hủy và ngân sách voucher', icon: ShieldCheck },
  ];
  const activeTone = adminTabTone[tab];
  const ActiveIcon = availableTabs.find((item) => item.id === tab)?.icon || LayoutDashboard;
  const groupedTabs = availableTabs.reduce<Record<string, typeof availableTabs>>((groups, item) => {
    groups[item.group] = [...(groups[item.group] || []), item];
    return groups;
  }, {});

  return (
    <div className={`h-screen overflow-hidden px-4 py-6 text-slate-900 sm:px-6 lg:px-8 ${tab === 'overview' ? 'bg-[linear-gradient(180deg,#eef2ff_0%,#f8fafc_42%,#f8fafc_100%)]' : tab === 'content' ? 'bg-[linear-gradient(180deg,#ecfdf5_0%,#f8fafc_42%,#f8fafc_100%)]' : 'bg-[linear-gradient(180deg,#f8fafc_0%,#f1f5f9_44%,#f8fafc_100%)]'}`}>
      <div className="mx-auto flex h-full w-full max-w-[1500px] flex-col">
        <AdminTopBar onRefresh={() => void loadData(tab, { force: true })} query={query} setQuery={setQuery} sidebarOpen={sidebarOpen} searchPlaceholder={searchPlaceholderByTab[tab]} onToggleSidebar={() => setSidebarOpen((value) => !value)} />
        <div className={`min-h-0 flex-1 grid gap-5 ${sidebarOpen ? 'lg:grid-cols-[280px_minmax(0,1fr)]' : 'lg:grid-cols-1'}`}>
          <aside className={`${sidebarOpen ? 'block' : 'hidden'} admin-scroll-panel rounded-[28px] border border-rose-200/80 bg-[linear-gradient(180deg,#fff7f7_0%,#fff1f2_100%)] p-4 shadow-[0_24px_60px_rgba(127,29,29,0.08)]`}>
            <div className="mb-4 rounded-2xl border border-rose-100 bg-[linear-gradient(135deg,#fff1f2_0%,#fffaf9_100%)] px-4 py-4 shadow-sm">
              <div className="text-xs font-bold uppercase tracking-[0.18em] text-indigo-500">Điều hướng</div>
              <div className="mt-1 text-sm font-semibold text-slate-900">Trung tâm vận hành admin</div>
              <p className="mt-2 text-xs leading-5 text-slate-500">Nhóm chức năng được gom theo ngữ cảnh để quét nhanh hơn và giảm tải thị giác.</p>
            </div>
            <div className="space-y-4">
              {Object.entries(groupedTabs).map(([groupName, items]) => (
                <div key={groupName}>
                  <div className="mb-2 px-2 text-[11px] font-bold uppercase tracking-[0.18em] text-slate-400">{groupName}</div>
                  <div className="space-y-2">
                    {items.map((item) => {
                      const Icon = item.icon;
                      const itemTone = adminTabTone[item.id];
                      return (
                        <button key={item.id} onClick={() => { setTab(item.id); setQuery(''); }} className={`flex h-12 w-full items-center gap-3 rounded-2xl border px-3 text-left text-sm font-semibold transition ${tab === item.id ? itemTone.active : 'border-slate-200 bg-slate-50/80 text-slate-700 hover:border-slate-300 hover:bg-white hover:text-slate-950'}`}>
                          <span className={`inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-xl ring-1 ${tab === item.id ? 'bg-white/70 text-slate-800 ring-white/80' : itemTone.icon}`}>
                            <Icon className="h-4 w-4" />
                          </span>
                          <span className="min-w-0 flex-1 truncate">{item.label}</span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          </aside>

          <section className="admin-scroll-panel min-w-0 rounded-[28px] pr-1">
            {busy && <div className="mb-4 flex items-center gap-2 rounded-2xl border border-sky-100 bg-sky-50 px-4 py-3 text-sm font-semibold text-sky-700 shadow-sm"><RefreshCw className="h-4 w-4 animate-spin" />Đang đồng bộ dữ liệu quản trị...</div>}

            <div className={`mb-5 flex flex-col gap-3 rounded-[24px] border px-5 py-5 shadow-sm sm:flex-row sm:items-center sm:justify-between ${activeTone.surface}`}>
              <div className="flex min-w-0 items-center gap-3">
                <span className={`inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-md bg-white/80 ring-1 ${activeTone.icon}`}>
                  <ActiveIcon className="h-5 w-5" />
                </span>
                <div className="min-w-0">
                  <div className="text-xs font-bold uppercase tracking-wide opacity-70">{activeTone.label}</div>
                  <h2 className="truncate text-xl font-bold text-current">{activeTone.title}</h2>
                  <p className="mt-1 text-sm font-medium leading-5 opacity-75">{activeTone.description}</p>
                </div>
              </div>
            </div>

            {tab === 'overview' && (
              <Suspense fallback={<div className="rounded-lg border border-slate-200 bg-white px-4 py-8 text-center text-sm font-semibold text-slate-500">?ang t?i t?ng quan...</div>}>
                <AdminOverviewTab
                  stats={stats}
                  overview={overview}
                  roleDashboards={roleDashboards}
                  currency={currency}
                  compactCurrency={compactCurrency}
                  percent={percent}
                />
              </Suspense>
            )}
            {tab === 'products' && (
              <Suspense fallback={<div className="rounded-lg border border-slate-200 bg-white px-4 py-8 text-center text-sm font-semibold text-slate-500">?ang t?i s?n ph?m...</div>}>
                <AdminProductsTab
                  productCategoryFilter={productCategoryFilter}
                  setProductCategoryFilter={setProductCategoryFilter}
                  productBrandFilter={productBrandFilter}
                  productBrandOptions={productBrandOptions}
                  setProductBrandFilter={setProductBrandFilter}
                  accessoryBrandFilter={accessoryBrandFilter}
                  accessoryCategoryFilter={accessoryCategoryFilter}
                  accessoryProductChoices={accessoryProductChoices}
                  accessorySearch={accessorySearch}
                  addAccessoryOffer={addAccessoryOffer}
                  addAttachedService={addAttachedService}
                  addVariant={addVariant}
                  approveProduct={approveProduct}
                  archiveProduct={archiveProduct}
                  attachedServiceGroupFilter={attachedServiceGroupFilter}
                  attachedServiceSearch={attachedServiceSearch}
                  attachedServiceTypeFilter={attachedServiceTypeFilter}
                  brands={brands}
                  buildVariantSku={buildVariantSku}
                  bulkApproveProducts={bulkApproveProducts}
                  categories={categories}
                  categoryWarrantyPolicy={categoryWarrantyPolicy}
                  compactId={compactId}
                  confirmDelete={confirmDelete}
                  currency={currency}
                  duplicateProduct={duplicateProduct}
                  editProduct={editProduct}
                  editingProductId={editingProductId}
                  exportProducts={exportProducts}
                  filteredProducts={filteredProducts}
                  groupedActiveVariantFields={groupedActiveVariantFields}
                  groupedProductSpecFields={groupedProductSpecFields}
                  handleProductSubmit={handleProductSubmit}
                  importProducts={importProducts}
                  patchAccessoryOffer={patchAccessoryOffer}
                  patchVariant={patchVariant}
                  productAttachedServiceChoices={productAttachedServiceChoices}
                  productForm={productForm}
                  productSpecFields={productSpecFields}
                  productStatusLabel={productStatusLabel}
                  productStatusOptions={productStatusOptions}
                  query={query}
                  reactivateProduct={reactivateProduct}
                  removeAccessoryOffer={removeAccessoryOffer}
                  removeAttachedService={removeAttachedService}
                  resetProductForm={resetProductForm}
                  rootCategories={rootCategories}
                  selectedCategory={selectedCategory}
                  selectedProductIds={selectedProductIds}
                  serviceGroupOptions={serviceGroupOptions}
                  setAccessoryBrandFilter={setAccessoryBrandFilter}
                  setAccessoryCategoryFilter={setAccessoryCategoryFilter}
                  setAccessorySearch={setAccessorySearch}
                  setAttachedServiceGroupFilter={setAttachedServiceGroupFilter}
                  setAttachedServiceSearch={setAttachedServiceSearch}
                  setAttachedServiceTypeFilter={setAttachedServiceTypeFilter}
                  setPreviewProduct={setPreviewProduct}
                  setProductForm={setProductForm}
                  setQuery={setQuery}
                  setSelectedProductIds={setSelectedProductIds}
                  subCategories={subCategories}
                  submitProduct={submitProduct}
                  toggleVariantSpecField={toggleVariantSpecField}
                  uploadFiles={uploadFiles}
                  variantFields={variantFields}
                />
              </Suspense>
            )}
            {tab === 'categories' && (
              <Suspense fallback={<div className="rounded-lg border border-slate-200 bg-white px-4 py-8 text-center text-sm font-semibold text-slate-500">?ang t?i danh m?c...</div>}>
                <AdminCategoriesTab
                  addCategoryFilter={addCategoryFilter}
                  addSpecField={addSpecField}
                  apiDb={apiDb}
                  categoryAuditLogs={categoryAuditLogs}
                  categoryForm={categoryForm}
                  categoryMetrics={categoryMetrics}
                  categoryMigrationJobs={categoryMigrationJobs}
                  categoryPanelBusy={categoryPanelBusy}
                  categoryParentMigrationHint={categoryParentMigrationHint}
                  categorySlugStatus={categorySlugStatus}
                  categorySlugTaken={categorySlugTaken}
                  categoryStatusOptions={categoryStatusOptions}
                  checkCategorySlug={checkCategorySlug}
                  compactId={compactId}
                  confirmDelete={confirmDelete}
                  derivedCategoryFilters={derivedCategoryFilters}
                  editCategory={editCategory}
                  editingCategory={editingCategory}
                  editingCategoryId={editingCategoryId}
                  filteredCategoryTree={filteredCategoryTree}
                  filteredRootCategories={filteredRootCategories}
                  handleCategorySubmit={handleCategorySubmit}
                  patchCategoryFilter={patchCategoryFilter}
                  patchSpecField={patchSpecField}
                  query={query}
                  reactivateCategory={reactivateCategory}
                  refreshCategoryWorkspace={refreshCategoryWorkspace}
                  reorderCategory={reorderCategory}
                  resetCategoryForm={resetCategoryForm}
                  rootCategories={rootCategories}
                  setCategoryForm={setCategoryForm}
                  setCategorySlugStatus={setCategorySlugStatus}
                  setQuery={setQuery}
                  slugifyText={slugifyText}
                  uploadFiles={uploadFiles}
                />
              </Suspense>
            )}
            {tab === 'brands' && (
              <AdminPanel title="Quản lý thương hiệu và logo" action={<div className="flex flex-col gap-2 sm:flex-row"><Select label="Trạng thái" value={brandStatusFilter} onChange={setBrandStatusFilter} options={[['all', 'Tất cả'], ['active', 'Đang hiển thị'], ['inactive', 'Đã ẩn']]} /><SearchBox value={query} onChange={setQuery} placeholder="Tìm thương hiệu, mã" /></div>}>
                <CollapsibleSection title={editingBrandId ? 'Đang chỉnh sửa thương hiệu' : 'Thêm thương hiệu mới'} description="Mở khi cần tạo hoặc cập nhật tên, mã và logo thương hiệu." defaultOpen={false} forceOpen={Boolean(editingBrandId)} forceOpenKey={editingBrandId} onClose={resetBrandForm}>
                  <form onSubmit={handleBrandSubmit} className="mb-5 grid gap-3 rounded-lg bg-slate-50 p-4 md:grid-cols-6">
                    <Input label="Tên thương hiệu" value={brandForm.name} required onChange={(value) => setBrandForm({ ...brandForm, name: value, slug: brandForm.slug || slugifyText(value) })} />
                    <Input label="Mã thương hiệu" value={brandForm.code} required onBlur={checkBrandCodeOnBlur} onChange={(value) => { setBrandCodeStatus('idle'); setBrandForm({ ...brandForm, code: value }); }} />
                    <Input label="Slug landing" value={brandForm.slug} onChange={(value) => setBrandForm({ ...brandForm, slug: value })} />
                    <Input label="Thứ tự" type="number" value={brandForm.order} onChange={(value) => setBrandForm({ ...brandForm, order: Number(value) })} />
                    <FileInput label="Logo từ máy tính" accept="image/*" onFiles={async (files) => setBrandForm({ ...brandForm, logoUrl: (await uploadFiles(files, 'brands'))[0] || brandForm.logoUrl })} />
                    <Input label="Alt text logo" value={brandForm.logoAltText} onChange={(value) => setBrandForm({ ...brandForm, logoAltText: value })} />
                    <Input label="Tiêu đề landing" value={brandForm.landingTitle} onChange={(value) => setBrandForm({ ...brandForm, landingTitle: value })} />
                    <Input label="SEO title" value={brandForm.seoTitle} onChange={(value) => setBrandForm({ ...brandForm, seoTitle: value })} />
                    <textarea className="min-h-16 rounded-md border border-slate-200 px-3 py-2 text-sm outline-none focus:border-red-500 md:col-span-3" placeholder="SEO description" value={brandForm.seoDescription} onChange={(event) => setBrandForm({ ...brandForm, seoDescription: event.target.value })} />
                    <div className="text-xs font-semibold text-slate-500 md:col-span-2">{brandCodeStatus === 'checking' ? 'Đang kiểm tra mã...' : brandCodeStatus === 'available' ? 'Mã có thể dùng' : brandCodeStatus === 'taken' ? 'Mã đã tồn tại' : ''}</div>
                    <SubmitButtons editing={Boolean(editingBrandId)} onCancel={resetBrandForm} />
                  </form>
                </CollapsibleSection>
                <CollapsibleSection title="Import thương hiệu hàng loạt" description="Upload CSV có cột: Tên, Mã, Logo URL, Thứ tự. Dữ liệu có dấu phẩy nên đặt trong dấu ngoặc kép." defaultOpen={false}>
                  <div className="mb-5 grid gap-3 rounded-lg bg-slate-50 p-4">
                    <Select label="Chế độ import" value={brandImportMode} onChange={setBrandImportMode} options={[['skip', 'Thêm mới, bỏ qua trùng'], ['upsert', 'Thêm mới, cập nhật theo mã']]} />
                    <FileInput label="File CSV" accept=".csv,text/csv" onFiles={handleBrandImportFile} />
                    {activeBrandImportJob && (
                      <div className="rounded-md bg-white p-3 text-sm text-slate-700">
                        <div className="mb-2 flex justify-between">
                          <span>Job {activeBrandImportJob.id}</span>
                          <span>{activeBrandImportJob.status} - {activeBrandImportJob.progress || 0}%</span>
                        </div>
                        <div className="h-2 overflow-hidden rounded-full bg-slate-100">
                          <div className="h-full bg-red-600" style={{ width: `${activeBrandImportJob.progress || 0}%` }} />
                        </div>
                        <div className="mt-2 text-xs text-slate-500">
                          Đã xử lý {activeBrandImportJob.processedRows || 0}/{activeBrandImportJob.totalRows || 0} dòng,
                          thêm {activeBrandImportJob.importedRows || 0}, cập nhật {activeBrandImportJob.updatedRows || 0}, bỏ qua {activeBrandImportJob.skippedRows || 0}
                        </div>
                        {activeBrandImportJob.errorMessage && <div className="mt-2 text-xs font-semibold text-red-600">{activeBrandImportJob.errorMessage}</div>}
                      </div>
                    )}
                    <div className="rounded-md bg-white p-3 text-xs text-slate-600">
                      {brandImportJobs.slice(0, 3).map((job) => (
                        <div key={job.id} className="border-b border-slate-100 py-2 last:border-0">
                          <div className="flex flex-wrap justify-between gap-2">
                            <span>{job.sourceFilename || 'Import thủ công'} - {job.mode} - {job.status}</span>
                            <span>Thêm {job.importedRows}, cập nhật {job.updatedRows}, bỏ qua {job.skippedRows}</span>
                          </div>
                          {Array.isArray(job.report) && job.report.length > 0 && (
                            <details className="mt-1">
                              <summary className="cursor-pointer font-semibold text-slate-500">Xem dòng bị bỏ qua</summary>
                              <div className="mt-1 space-y-1">
                                {job.report.slice(0, 5).map((item: any, index: number) => <div key={`${job.id}-${index}`}>Dòng {item.row}: {item.reason}</div>)}
                              </div>
                            </details>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                </CollapsibleSection>
                {selectedBrandIds.length > 0 && <div className="mb-3 flex gap-2"><button type="button" onClick={() => bulkUpdateBrandStatus(false)} className="rounded-md border border-slate-200 px-3 py-2 text-sm">Ẩn đã chọn</button><button type="button" onClick={() => bulkUpdateBrandStatus(true)} className="rounded-md border border-slate-200 px-3 py-2 text-sm">Khôi phục đã chọn</button></div>}
                <AdminTable headers={['', 'Logo', 'Thương hiệu', 'Mã', 'Landing', 'Sản phẩm', 'Số danh mục', 'Thứ tự', 'Cập nhật', 'Trạng thái', 'Thao tác']}>
                  {filteredBrands.map((brand) => (
                    <tr key={brand.id}>
                      <td className="px-4 py-3"><input type="checkbox" checked={selectedBrandIds.includes(brand.id)} onChange={(event) => setSelectedBrandIds((ids) => event.target.checked ? [...ids, brand.id] : ids.filter((id) => id !== brand.id))} /></td>
                      <td className="px-4 py-3"><BrandLogo brand={brand} /></td>
                      <td className="px-4 py-3 font-semibold text-slate-900">{brand.name}</td>
                      <td className="px-4 py-3 font-mono text-xs">{brand.code || '-'}</td>
                      <td className="px-4 py-3 text-xs text-red-600">{brand.slug ? `/brands/${brand.slug}` : '-'}</td>
                      <td className="px-4 py-3">{brand.productCount || 0}</td>
                      <td className="px-4 py-3">{brand.categoryIds?.length || 0}</td>
                      <td className="px-4 py-3">{brand.order || 0}</td>
                      <td className="px-4 py-3 text-xs">{brand.updatedAt ? new Date(brand.updatedAt).toLocaleString('vi-VN') : '-'}</td>
                      <td className="px-4 py-3"><AdminBadge tone={brand.isActive ? 'green' : 'slate'}>{brand.isActive ? 'ACTIVE' : 'INACTIVE'}</AdminBadge></td>
                      <td className="px-4 py-3"><RowActions onEdit={() => editBrand(brand)} onDelete={() => brand.isActive ? hideBrand(brand) : confirmDelete(brand.name, () => apiDb.adminDeleteBrand(brand.id))} onRestore={brand.isActive ? undefined : () => reactivateBrand(brand)} /></td>
                    </tr>
                  ))}
                </AdminTable>
                <div className="mt-4 flex items-center justify-between text-sm text-slate-600">
                  <span>Hiển thị {filteredBrands.length} / {brandTotal} thương hiệu</span>
                  <div className="flex gap-2">
                    <button type="button" disabled={brandPage <= 1} onClick={() => setBrandPage((page) => Math.max(1, page - 1))} className="rounded-md border border-slate-200 px-3 py-1 disabled:opacity-40">Trước</button>
                    <button type="button" disabled={brandPage * 10 >= brandTotal} onClick={() => setBrandPage((page) => page + 1)} className="rounded-md border border-slate-200 px-3 py-1 disabled:opacity-40">Sau</button>
                  </div>
                </div>
              </AdminPanel>
            )}

            {tab === 'services' && (
              <AdminPanel title="Quản lý dịch vụ đi kèm" action={<div className="flex flex-col gap-2 sm:flex-row sm:items-center"><SearchBox value={query} onChange={setQuery} placeholder="Tìm dịch vụ, mã, nhóm" /><button type="button" onClick={() => { resetServiceForm(); setServiceFormOpen(true); }} className="inline-flex h-10 items-center justify-center gap-2 rounded-xl bg-rose-200 px-4 text-sm font-bold text-slate-800 shadow-sm shadow-rose-50 transition hover:bg-rose-300"><Plus className="h-4 w-4" /> Thêm</button></div>}>
                {serviceFormOpen && (
                  <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-950/55 px-4 py-6 backdrop-blur-sm">
                    <div className="w-full max-w-5xl overflow-hidden rounded-lg bg-white shadow-2xl">
                      <div className="sticky top-0 z-10 flex items-start justify-between gap-4 border-b border-slate-200 bg-white px-5 py-4">
                        <div>
                          <h3 className="text-lg font-bold text-slate-950">{editingServiceId ? 'Đang chỉnh sửa dịch vụ' : 'Thêm dịch vụ đi kèm'}</h3>
                          <p className="mt-1 text-sm text-slate-500">Tạo các gói bảo hành, 1 đổi 1, lắp đặt, vệ sinh hoặc hỗ trợ để chọn trong form sản phẩm.</p>
                        </div>
                        <button type="button" onClick={resetServiceForm} title="Đóng popup" className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-slate-200 text-slate-600 transition hover:bg-slate-50 hover:text-slate-950">
                          <X className="h-4 w-4" />
                        </button>
                      </div>
                      <div className="max-h-[calc(100vh-150px)] overflow-y-auto p-5">
                        <form onSubmit={handleServiceSubmit} className="grid gap-3 rounded-lg bg-slate-50 p-4 md:grid-cols-4">
                  <Input label="Mã dịch vụ" value={serviceForm.code} required onChange={(value) => setServiceForm({ ...serviceForm, code: value })} />
                  <Input label="Tên dịch vụ" value={serviceForm.name} required onChange={(value) => setServiceForm({ ...serviceForm, name: value })} />
                  <Select label="Loại dịch vụ" value={serviceForm.serviceType} onChange={(value) => setServiceForm({ ...serviceForm, serviceType: value, attributeGroup: value === 'PRODUCT_SERVICE' && !serviceForm.attributeGroup ? 'WARRANTY' : serviceForm.attributeGroup, priceMode: value === 'PRODUCT_SERVICE' ? 'TIERED_AMOUNT' : serviceForm.priceMode, fixedPrice: value === 'PRODUCT_SERVICE' ? 0 : serviceForm.fixedPrice, percentValue: value === 'PRODUCT_SERVICE' ? 0 : serviceForm.percentValue, baseAmount: value === 'PRODUCT_SERVICE' ? 0 : serviceForm.baseAmount })} options={[['PRODUCT_SERVICE', 'Dịch vụ sản phẩm'], ['SUPPORT_SERVICE', 'Dịch vụ hỗ trợ']]} />
                  <Select label="Nhóm dịch vụ" value={serviceForm.attributeGroup} onChange={(value) => setServiceForm({ ...serviceForm, attributeGroup: value })} options={[['', 'Chọn nhóm'], ...serviceAttributeGroupOptions]} />
                  <Select label="Thời hạn" value={String(serviceForm.durationMonths || 0)} onChange={(value) => setServiceForm({ ...serviceForm, durationMonths: Number(value) })} options={warrantyDurationOptions} />
                  {serviceForm.serviceType === 'PRODUCT_SERVICE' ? (
                    <div className="rounded-md border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 md:col-span-4">Biểu phí theo chính sách</div>
                  ) : (
                    <>
                      <Select label="Cách tính giá" value={serviceForm.priceMode} onChange={(value) => setServiceForm({ ...serviceForm, priceMode: value })} options={[['FIXED', 'Giá cố định'], ['PERCENT', 'Theo % sản phẩm'], ['TIERED_AMOUNT', 'Theo định mức']]} />
                      <Input label="Giá cố định" type="number" value={serviceForm.fixedPrice} onChange={(value) => setServiceForm({ ...serviceForm, fixedPrice: Number(value) })} />
                      <Input label="Phần trăm" type="number" value={serviceForm.percentValue} onChange={(value) => setServiceForm({ ...serviceForm, percentValue: Number(value) })} />
                      <Input label="Định mức" type="number" value={serviceForm.baseAmount} onChange={(value) => setServiceForm({ ...serviceForm, baseAmount: Number(value) })} />
                    </>
                  )}
                  <Checkbox label="Đang bật" checked={serviceForm.isActive} onChange={(checked) => setServiceForm({ ...serviceForm, isActive: checked })} />
                  <SubmitButtons editing={Boolean(editingServiceId)} onCancel={resetServiceForm} />
                </form>
                      </div>
                    </div>
                  </div>
                )}
                <AdminTable headers={['Mã', 'Tên dịch vụ', 'Loại', 'Nhóm', 'Thời hạn', 'Giá', 'Trạng thái', 'Thao tác']}>
                  {attachedServices.filter((item) => matchesSearch(item, query, ['code', 'name', 'serviceType', 'attributeGroup'])).map((service) => (
                    <tr key={service.id}>
                      <td className="px-4 py-3 font-mono text-xs">{service.code}</td>
                      <td className="px-4 py-3 font-semibold text-slate-900">{service.name}</td>
                      <td className="px-4 py-3">{service.serviceType === 'PRODUCT_SERVICE' ? 'Dịch vụ sản phẩm' : 'Dịch vụ hỗ trợ'}</td>
                      <td className="px-4 py-3">{service.attributeGroup || '-'}</td>
                      <td className="px-4 py-3">{service.durationMonths ? `${service.durationMonths} thang` : '-'}</td>
                      <td className="px-4 py-3">{service.priceMode === 'PERCENT' ? `${service.percentValue || 0}%` : service.priceMode === 'TIERED_AMOUNT' ? 'Theo biểu phí' : currency.format(Number(service.fixedPrice || service.baseAmount || 0))}</td>
                      <td className="px-4 py-3"><AdminBadge tone={service.isActive ? 'green' : 'slate'}>{service.isActive ? 'ACTIVE' : 'INACTIVE'}</AdminBadge></td>
                      <td className="px-4 py-3"><RowActions onEdit={() => editService(service)} onDelete={() => apiDb.adminDeleteAttachedService(service.id).then(loadData)} /></td>
                    </tr>
                  ))}
                </AdminTable>
              </AdminPanel>
            )}

            {tab === 'orders' && (
              <Suspense fallback={<div className="rounded-lg border border-slate-200 bg-white px-4 py-8 text-center text-sm font-semibold text-slate-500">?ang t?i ??n h?ng...</div>}>
                <AdminOrdersTab
                  cancelledOrders={cancelledOrders}
                  compactId={compactId}
                  currency={currency}
                  filteredOrders={filteredOrders}
                  openOrderPanel={openOrderPanel}
                  orderDraft={orderDraft}
                  orderPanelBusy={orderPanelBusy}
                  orderPanelOpen={orderPanelOpen}
                  orderSaving={orderSaving}
                  orderStatusOptions={orderStatusOptions}
                  orderTransitionMap={orderTransitionMap}
                  orders={orders}
                  printOrderDocument={printOrderDocument}
                  query={query}
                  refundedOrders={refundedOrders}
                  saveOrderDraft={saveOrderDraft}
                  selectedOrder={selectedOrder}
                  setOrderDraft={setOrderDraft}
                  setOrderPanelOpen={setOrderPanelOpen}
                  setQuery={setQuery}
                  statusLabel={statusLabel}
                  updateOrderStatus={updateOrderStatus}
                />
              </Suspense>
            )}
            {tab === 'vouchers' && (
              <AdminPanel title="Quản lý voucher" action={<SearchBox value={query} onChange={setQuery} placeholder="Tìm mã voucher, loại, trạng thái" />}>
                <CollapsibleSection title={editingVoucherId ? 'Đang chỉnh sửa voucher' : 'Thêm voucher mới'} description="Mở khi cần thiết lập mã giảm giá, điều kiện đơn tối thiểu và giới hạn sử dụng." defaultOpen={false} forceOpen={Boolean(editingVoucherId)} forceOpenKey={editingVoucherId} onClose={resetVoucherForm}>
                  <form onSubmit={handleVoucherSubmit} className="mb-5 grid gap-3 rounded-lg bg-slate-50 p-4 md:grid-cols-6">
                    <Input label="Mã voucher" value={voucherForm.code} required onChange={(value) => setVoucherForm({ ...voucherForm, code: value.toUpperCase() })} />
                    <Select label="Mục tiêu" value={voucherForm.campaignType} onChange={(value) => setVoucherForm({ ...voucherForm, campaignType: value })} options={voucherCampaignOptions} />
                    <Select label="Đối tượng" value={voucherForm.audienceType} onChange={(value) => setVoucherForm({ ...voucherForm, audienceType: value, firstOrderOnly: value === 'NEW_CUSTOMER' || voucherForm.firstOrderOnly, hiddenCode: value === 'HIDDEN' || voucherForm.hiddenCode, abandonedCartOnly: value === 'ABANDONED_CART' || voucherForm.abandonedCartOnly })} options={voucherAudienceOptions} />
                    <Select label="Loại giảm" value={voucherForm.discountType} onChange={(value) => setVoucherForm({ ...voucherForm, discountType: value })} options={[['FIXED', 'Số tiền'], ['PERCENT', 'Phần trăm']]} />
                    <Input label="Giá trị" type="number" value={voucherForm.discountAmount} onChange={(value) => setVoucherForm({ ...voucherForm, discountAmount: Number(value) })} />
                    <Input label="Đơn tối thiểu" type="number" value={voucherForm.minOrderValue} onChange={(value) => setVoucherForm({ ...voucherForm, minOrderValue: Number(value) })} />
                    <Input label="Giảm tối đa" type="number" value={voucherForm.maxDiscount} onChange={(value) => setVoucherForm({ ...voucherForm, maxDiscount: Number(value) })} />
                    <Input label="Tổng lượt dùng" type="number" value={voucherForm.usageLimit} onChange={(value) => setVoucherForm({ ...voucherForm, usageLimit: Number(value) })} />
                    <Input label="Ngân sách tối đa" type="number" value={voucherForm.totalBudgetCap} onChange={(value) => setVoucherForm({ ...voucherForm, totalBudgetCap: Number(value) })} />
                    <Input label="Lượt/user" type="number" value={voucherForm.perUserLimit} onChange={(value) => setVoucherForm({ ...voucherForm, perUserLimit: Number(value) })} />
                    <Input label="Lượt/thiết bị" type="number" value={voucherForm.perDeviceLimit} onChange={(value) => setVoucherForm({ ...voucherForm, perDeviceLimit: Number(value) })} />
                    <Input label="Lượt/IP" type="number" value={voucherForm.perIpLimit} onChange={(value) => setVoucherForm({ ...voucherForm, perIpLimit: Number(value) })} />
                    <Input label="Bắt đầu" type="datetime-local" value={voucherForm.startsAt} onChange={(value) => setVoucherForm({ ...voucherForm, startsAt: value })} />
                    <Input label="Kết thúc" type="datetime-local" value={voucherForm.endsAt} onChange={(value) => setVoucherForm({ ...voucherForm, endsAt: value })} />
                    <Input label="Hạn sau khi lưu (ngày)" type="number" value={voucherForm.validityDaysAfterClaim} onChange={(value) => setVoucherForm({ ...voucherForm, validityDaysAfterClaim: Number(value) })} />
                    <Input label="User đăng ký sau" type="datetime-local" value={voucherForm.eligibleUserRegisteredAfter} onChange={(value) => setVoucherForm({ ...voucherForm, eligibleUserRegisteredAfter: value })} />
                    <Input label="User ID riêng" value={voucherForm.assignedUserId} onChange={(value) => setVoucherForm({ ...voucherForm, assignedUserId: value, audienceType: value ? 'SPECIFIC_USER' : voucherForm.audienceType })} />
                    <Select label="Trạng thái" value={voucherForm.status} onChange={(value) => setVoucherForm({ ...voucherForm, status: value })} options={[['ACTIVE', 'Đang chạy'], ['INACTIVE', 'Tạm dừng'], ['EXPIRED', 'Hết hạn']]} />
                    <Select label="Hoàn voucher" value={voucherForm.refundPolicy} onChange={(value) => setVoucherForm({ ...voucherForm, refundPolicy: value })} options={[['NEVER', 'Không hoàn'], ['SHOP_FAULT_ONLY', 'Hoàn khi lỗi shop'], ['ALWAYS', 'Luôn hoàn khi hủy']]} />
                    <div className="rounded-md border border-slate-200 bg-white p-3 md:col-span-3">
                      <div className="mb-2 text-xs font-bold text-slate-500">Hạng thành viên áp dụng</div>
                      <div className="flex flex-wrap gap-2">
                        {voucherTierOptions.map((tier) => (
                          <label key={tier} className={`inline-flex h-9 items-center gap-2 rounded-md border px-3 text-xs font-bold ${voucherForm.eligibleTiers.includes(tier) ? 'border-red-200 bg-red-50 text-red-700' : 'border-slate-200 bg-white text-slate-600'}`}>
                            <input type="checkbox" checked={voucherForm.eligibleTiers.includes(tier)} onChange={(event) => setVoucherForm({ ...voucherForm, eligibleTiers: event.target.checked ? [...voucherForm.eligibleTiers, tier] : voucherForm.eligibleTiers.filter((item) => item !== tier), audienceType: event.target.checked ? 'MEMBER_TIER' : voucherForm.audienceType })} className="h-4 w-4 accent-red-600" />
                            {tier}
                          </label>
                        ))}
                      </div>
                    </div>
                    <div className="grid gap-2 rounded-md border border-slate-200 bg-white p-3 md:col-span-3 sm:grid-cols-3">
                      <Checkbox label="Cộng dồn" checked={voucherForm.stackable} onChange={(checked) => setVoucherForm({ ...voucherForm, stackable: checked })} />
                      <Checkbox label="Đơn đầu tiên" checked={voucherForm.firstOrderOnly} onChange={(checked) => setVoucherForm({ ...voucherForm, firstOrderOnly: checked })} />
                      <Checkbox label="Mã ẩn" checked={voucherForm.hiddenCode} onChange={(checked) => setVoucherForm({ ...voucherForm, hiddenCode: checked })} />
                      <Checkbox label="Giỏ bỏ quên" checked={voucherForm.abandonedCartOnly} onChange={(checked) => setVoucherForm({ ...voucherForm, abandonedCartOnly: checked })} />
                    </div>
                    <textarea className="min-h-16 rounded-md border border-slate-200 px-3 py-2 text-sm outline-none focus:border-red-500 md:col-span-3" placeholder="Product IDs áp dụng, cách nhau bằng dấu phẩy" value={voucherForm.includeProductIds} onChange={(event) => setVoucherForm({ ...voucherForm, includeProductIds: event.target.value })} />
                    <textarea className="min-h-16 rounded-md border border-slate-200 px-3 py-2 text-sm outline-none focus:border-red-500 md:col-span-3" placeholder="Product IDs loại trừ" value={voucherForm.excludeProductIds} onChange={(event) => setVoucherForm({ ...voucherForm, excludeProductIds: event.target.value })} />
                    <textarea className="min-h-16 rounded-md border border-slate-200 px-3 py-2 text-sm outline-none focus:border-red-500 md:col-span-3" placeholder="Category IDs áp dụng" value={voucherForm.includeCategoryIds} onChange={(event) => setVoucherForm({ ...voucherForm, includeCategoryIds: event.target.value })} />
                    <textarea className="min-h-16 rounded-md border border-slate-200 px-3 py-2 text-sm outline-none focus:border-red-500 md:col-span-3" placeholder="Category IDs loại trừ" value={voucherForm.excludeCategoryIds} onChange={(event) => setVoucherForm({ ...voucherForm, excludeCategoryIds: event.target.value })} />
                    <textarea className="min-h-20 rounded-md border border-slate-200 px-3 py-2 text-sm outline-none focus:border-red-500 md:col-span-5" placeholder="Ghi chú nội bộ: lý do tạo, khách hàng được cấp, kênh gửi..." value={voucherForm.internalNote} onChange={(event) => setVoucherForm({ ...voucherForm, internalNote: event.target.value })} />
                    <SubmitButtons editing={Boolean(editingVoucherId)} onCancel={resetVoucherForm} />
                  </form>
                </CollapsibleSection>
                <AdminTable headers={['Mã', 'Chiến dịch', 'Đối tượng', 'Giá trị', 'Điều kiện', 'Lượt dùng', 'Trạng thái', 'Thao tác']}>
                  {filteredVouchers.map((voucher) => (
                    <tr key={voucher.id}>
                      <td className="px-4 py-3"><div className="font-mono font-bold text-slate-900">{voucher.code}</div>{voucher.hiddenCode && <div className="mt-1 text-xs font-bold text-amber-600">Mã ẩn</div>}</td>
                      <td className="px-4 py-3">{voucherCampaignOptions.find(([value]) => value === voucher.campaignType)?.[1] || voucher.campaignType || '-'}</td>
                      <td className="px-4 py-3">{voucherAudienceOptions.find(([value]) => value === voucher.audienceType)?.[1] || voucher.audienceType || '-'}</td>
                      <td className="px-4 py-3 font-semibold">{voucher.discountType === 'PERCENT' ? `${voucher.discountAmount}%` : currency.format(Number(voucher.discountAmount || 0))}</td>
                      <td className="px-4 py-3"><VoucherConditions voucher={voucher} /></td>
                      <td className="px-4 py-3">{voucher.usedCount || 0}/{voucher.usageLimit || '∞'}<div className="text-xs text-slate-500">/user: {voucher.perUserLimit || '∞'}</div>{voucher.totalBudgetCap ? <div className="text-xs text-slate-500">NS: {currency.format(Number(voucher.totalDiscountUsed || 0))}/{currency.format(Number(voucher.totalBudgetCap || 0))}</div> : null}</td>
                      <td className="px-4 py-3"><AdminBadge tone={voucher.status === 'ACTIVE' ? 'green' : 'slate'}>{voucher.status === 'ACTIVE' ? 'Đang chạy' : 'Tạm dừng'}</AdminBadge></td>
                      <td className="px-4 py-3"><RowActions onEdit={() => editVoucher(voucher)} onDelete={() => confirmDelete(voucher.code, () => apiDb.adminDeleteVoucher(voucher.id))} /></td>
                    </tr>
                  ))}
                </AdminTable>
              </AdminPanel>
            )}


            {tab === 'customers' && (
              <AdminPanel title={usePermission('sys:manage_users') ? 'Quản lý khách hàng và phân quyền' : 'Tra cứu khách hàng'} action={<SearchBox value={query} onChange={setQuery} placeholder="Tìm khách hàng, email, hạng" />}>
                {(canManageCustomerAccess || canManageCustomerProfile) && (
                  <div className="mb-4 flex flex-wrap items-center gap-2">
                    <button type="button" disabled={!selectedCustomerIds.length || !canManageCustomerAccess} onClick={() => void bulkSuspendCustomers()} className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-bold text-amber-800 disabled:cursor-not-allowed disabled:opacity-50">Khóa hàng loạt</button>
                    <button type="button" disabled={!selectedCustomerIds.length || !canManageCustomerProfile} onClick={() => void bulkApplyCustomerTags()} className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-bold text-slate-800 disabled:cursor-not-allowed disabled:opacity-50">Gán tag hàng loạt</button>
                    <span className="text-xs font-semibold text-slate-500">Đã chọn: {selectedCustomerIds.length} / Tổng: {customerTotal}</span>
                  </div>
                )}
                <AdminTable headers={['Chọn', 'Khách hàng', 'Email', 'Vai trò/Hạng', 'Điểm', 'Số đơn', 'Đã chi tiêu', 'Trạng thái', 'Chi tiết']}>
                  {filteredCustomers.length === 0 ? (
                    <tr><td colSpan={9} className="px-4 py-8 text-center text-sm font-medium text-slate-500">Không tìm thấy khách hàng phù hợp.</td></tr>
                  ) : filteredCustomers.map((item) => (
                    <tr key={item.id}>
                      <td className="px-4 py-3">
                        <input type="checkbox" checked={selectedCustomerIds.includes(item.id)} onChange={(event) => setSelectedCustomerIds((prev) => event.target.checked ? [...new Set([...prev, item.id])] : prev.filter((id) => id !== item.id))} className="h-4 w-4 rounded border-slate-300 text-red-600 focus:ring-red-500" />
                      </td>
                      <td className="px-4 py-3 font-semibold text-slate-900">{item.fullName || item.email}</td>
                      <td className="px-4 py-3">{item.email}</td>
                      <td className="px-4 py-3">
                        {item.role === 'SUPER_ADMIN' ? 'Super Admin' : item.role === 'STAFF_ADMIN' ? 'Staff Admin' : item.tier}
                      </td>
                      <td className="px-4 py-3">{item.points ?? 0}</td>
                      <td className="px-4 py-3">{item.orderCount || 0} đơn</td>
                      <td className="px-4 py-3">{currency.format(Number(item.totalSpent || 0))}</td>
                      <td className="px-4 py-3">
                        {canManageCustomerAccess ? (
                          <select value={item.status || 'ACTIVE'} onChange={(event) => updateUserAccess(item, { status: event.target.value })} className="h-9 rounded-md border border-slate-200 bg-white px-2 text-xs font-semibold outline-none focus:border-red-500">
                            <option value="ACTIVE">ACTIVE</option>
                            <option value="SUSPENDED">SUSPENDED</option>
                          </select>
                        ) : item.status}
                      </td>
                      <td className="px-4 py-3">
                        <button type="button" onClick={() => openCustomerDetail(item)} className="inline-flex items-center gap-2 rounded-md border border-sky-200 bg-sky-50 px-3 py-1.5 text-xs font-bold text-sky-800 transition hover:bg-sky-100">
                          <Eye className="h-4 w-4" /> Xem hồ sơ
                        </button>
                      </td>
                    </tr>
                  ))}
                </AdminTable>
                <div className="mt-4 flex items-center justify-between text-sm text-slate-500">
                  <span>Trang {customerPage} / {Math.max(1, Math.ceil(customerTotal / 20))}</span>
                  <div className="flex items-center gap-2">
                    <button type="button" disabled={customerPage <= 1} onClick={() => setCustomerPage((prev) => Math.max(1, prev - 1))} className="rounded-md border border-slate-200 px-3 py-1.5 font-semibold text-slate-700 disabled:cursor-not-allowed disabled:opacity-50">Trước</button>
                    <button type="button" disabled={customerPage >= Math.max(1, Math.ceil(customerTotal / 20))} onClick={() => setCustomerPage((prev) => prev + 1)} className="rounded-md border border-slate-200 px-3 py-1.5 font-semibold text-slate-700 disabled:cursor-not-allowed disabled:opacity-50">Sau</button>
                  </div>
                </div>
              </AdminPanel>
            )}
            {tab === 'inventory' && (
              <AdminPanel title="Quản lý tồn kho" action={
                <div className="flex flex-wrap items-center gap-2">
                  <Select value={inventoryCategoryFilter} onChange={setInventoryCategoryFilter} options={[['', 'Tất cả danh mục'], ...categories.map(c => [c.id, c.parentName ? `${c.parentName} / ${c.name}` : c.name])]} />
                  <Select value={inventoryBrandFilter} onChange={setInventoryBrandFilter} options={inventoryBrandOptions} />
                  <SearchBox value={query} onChange={setQuery} placeholder="Tìm sản phẩm, SKU, trạng thái kho" />
                  <button type="button" onClick={() => void exportInventorySnapshot()} className="inline-flex h-10 items-center gap-2 rounded-md border border-slate-200 bg-white px-3 text-sm font-bold text-slate-700 transition hover:bg-slate-50"><Download className="h-4 w-4" /> Xuất</button>
                </div>
              }>
                <AdminTable headers={['Sản phẩm', 'SKU / Biến thể', 'Tồn kho', 'Cảnh báo', 'Trạng thái', 'Điều chỉnh']}>
                  {filteredInventory.flatMap((product) => {
                    const inventorySettings = getInventorySettings(product);
                    const rows = [
                      <tr key={`${product.id}-base`}>
                        <td className="px-4 py-3 font-semibold text-slate-900">{product.name}</td>
                        <td className="px-4 py-3 font-mono text-xs">{product.sku || compactId(product.id)}</td>
                        <td className="px-4 py-3">{product.stock ?? 0}</td>
                        <td className="px-4 py-3">{Number(product.stock || 0) <= inventorySettings.minimumStock ? `Cần nhập thêm (min ${inventorySettings.minimumStock})` : 'Ổn định'}</td>
                        <td className="px-4 py-3">{Number(product.stock || 0) > 0 ? 'Còn hàng' : inventorySettings.blockSaleWhenOutOfStock ? 'Khóa bán khi hết' : 'Hết hàng'}</td>
                        <td className="px-4 py-3"><button type="button" onClick={() => openInventoryDialog(product)} className="rounded-md border border-amber-200 bg-amber-50 px-3 py-1.5 text-xs font-bold text-amber-800">Nhập/điều chỉnh</button></td>
                      </tr>,
                    ];
                    (product.variants || []).forEach((variant: any) => {
                      rows.push(
                        <tr key={`${product.id}-${variant.id}`} className="bg-slate-50/60">
                          <td className="px-4 py-3 pl-8 text-sm text-slate-600">{product.name}</td>
                          <td className="px-4 py-3 font-mono text-xs">{variant.sku || compactId(variant.id)} {variant.colorName ? `- ${variant.colorName}` : ''}</td>
                          <td className="px-4 py-3">{variant.stockQuantity ?? 0}</td>
                          <td className="px-4 py-3">{Number(variant.stockQuantity || 0) <= inventorySettings.minimumStock ? `Cần nhập thêm (min ${inventorySettings.minimumStock})` : 'Ổn định'}</td>
                          <td className="px-4 py-3">{variant.isActive === false ? 'Đã ẩn' : Number(variant.stockQuantity || 0) > 0 ? 'Còn hàng' : 'Hết hàng'}</td>
                          <td className="px-4 py-3"><button type="button" onClick={() => openInventoryDialog(product, variant)} className="rounded-md border border-amber-200 bg-amber-50 px-3 py-1.5 text-xs font-bold text-amber-800">Nhập/điều chỉnh</button></td>
                        </tr>,
                      );
                    });
                    return rows;
                  })}
                </AdminTable>
              </AdminPanel>
            )}
            {tab === 'reviews' && (
              <AdminPanel
                title="Quản lý đánh giá theo sản phẩm"
                action={(
                  <div className="flex flex-col gap-3 md:flex-row md:items-center">
                    <SearchBox value={query} onChange={setQuery} placeholder="Tìm sản phẩm, khách hàng, nội dung" />
                    <select value={reviewStarFilter} onChange={(event) => setReviewStarFilter(event.target.value)} className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700">
                      {reviewStarOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                    </select>
                    <select value={reviewStatusFilter} onChange={(event) => setReviewStatusFilter(event.target.value)} className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700">
                      {reviewStatusOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                    </select>
                  </div>
                )}
              >
                <div className="mb-5 grid gap-3 md:grid-cols-4">
                  <MiniMetric label="Tổng đánh giá" value={reviewMetrics.total} helper="Tất cả trạng thái" />
                  <MiniMetric label="Chờ duyệt" value={reviewMetrics.pending} helper="Kiểm duyệt trước khi public" />
                  <MiniMetric label="Đang hiển thị" value={reviewMetrics.published} helper="Đánh giá đang public" />
                  <MiniMetric label="Cần xem lại" value={reviewMetrics.flagged} helper="Bị báo xấu hoặc nghi spam" />
                </div>
                <div className="mb-6 overflow-x-auto rounded-2xl border border-slate-200 bg-slate-50/70">
                  {/* Snapshot report so admins can spot products with strong/weak sentiment without leaving the moderation screen. */}
                  <table className="min-w-full text-left text-sm">
                    <thead>
                      <tr className="border-b border-slate-200 text-xs font-bold uppercase tracking-wide text-slate-500">
                        <th className="px-4 py-3">Sản phẩm</th>
                        <th className="px-4 py-3">TB sao</th>
                        <th className="px-4 py-3">Đã public</th>
                        <th className="px-4 py-3">Chờ duyệt</th>
                        <th className="px-4 py-3">Bị gắn cờ</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200">
                      {reviewSummary.slice(0, 6).map((item) => (
                        <tr key={item.productId}>
                          <td className="px-4 py-3 font-semibold text-slate-900">{item.productName}</td>
                          <td className="px-4 py-3 font-bold text-amber-600">{item.averageRating ? `${item.averageRating}/5` : '-'}</td>
                          <td className="px-4 py-3">{item.publishedReviews || 0}</td>
                          <td className="px-4 py-3">{item.pendingReviews || 0}</td>
                          <td className="px-4 py-3">{item.flaggedReviews || 0}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <AdminTable headers={['Sản phẩm', 'Khách hàng', 'Điểm', 'Nội dung', 'Media / phản hồi', 'Ngày', 'Trạng thái', 'Thao tác']}>
                  {filteredReviews.length === 0 ? (
                    <tr><td colSpan={8} className="px-4 py-8 text-center text-sm font-medium text-slate-500">Không tìm thấy đánh giá phù hợp.</td></tr>
                  ) : filteredReviews.map((review) => (
                    <tr key={review.id}>
                      <td className="px-4 py-3 font-semibold text-slate-900">{review.productName}</td>
                      <td className="px-4 py-3">{review.userName}</td>
                      <td className="px-4 py-3 font-bold text-amber-600">{review.rating}/5</td>
                      <td className="max-w-md px-4 py-3 text-sm text-slate-600">{review.comment || '-'}</td>
                      <td className="px-4 py-3 text-sm text-slate-600">
                        <div>{Array.isArray(review.mediaUrls) && review.mediaUrls.length ? `${review.mediaUrls.length} tệp` : 'Không có media'}</div>
                        <div className="mt-1 text-xs">
                          {review.shopReply ? `Shop đã phản hồi` : 'Chưa phản hồi'}
                          {review.flaggedReason ? ` • Báo xấu` : ''}
                          {review.isSpam ? ` • Spam` : ''}
                          {review.orderOutcome ? ` • ${review.orderOutcome === 'DA_HOAN_TIEN' ? 'Đã hoàn tiền' : 'Đã trả hàng'}` : ''}
                        </div>
                      </td>
                      <td className="px-4 py-3">{review.createdAt ? new Date(review.createdAt).toLocaleDateString('vi-VN') : '-'}</td>
                      <td className="px-4 py-3">
                        <div className="flex flex-col gap-2">
                          <AdminBadge tone={review.status === 'PUBLISHED' ? 'green' : review.status === 'PENDING' ? 'blue' : review.status === 'REJECTED' ? 'red' : 'slate'}>{reviewStatusLabel[review.status] || review.status}</AdminBadge>
                          {review.flaggedReason && <span className="text-xs font-semibold text-amber-700">Báo xấu: {review.flaggedReason}</span>}
                          {review.moderationNote && <span className="text-xs text-slate-500">Ghi chú: {review.moderationNote}</span>}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap items-center gap-2">
                          {review.status === 'PENDING' ? (
                            <button type="button" onClick={() => updateReviewStatus(review, 'PUBLISHED')} className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-bold text-emerald-700 transition hover:bg-emerald-100">Duyệt</button>
                          ) : review.status === 'PUBLISHED' ? (
                            <button type="button" onClick={() => updateReviewStatus(review, 'HIDDEN')} className="rounded-md border border-slate-200 px-3 py-1.5 text-xs font-bold text-slate-700 transition hover:bg-slate-50">Ẩn</button>
                          ) : (
                            <button type="button" onClick={() => updateReviewStatus(review, 'PUBLISHED')} className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-bold text-emerald-700 transition hover:bg-emerald-100">Hiện lại</button>
                          )}
                          <button type="button" onClick={() => updateReviewStatus(review, 'REJECTED')} className="rounded-md border border-amber-200 bg-amber-50 px-3 py-1.5 text-xs font-bold text-amber-800 transition hover:bg-amber-100">Từ chối</button>
                          <button type="button" onClick={() => replyToReview(review)} className="rounded-md border border-blue-200 bg-blue-50 px-3 py-1.5 text-xs font-bold text-blue-700 transition hover:bg-blue-100">Phản hồi</button>
                          <button type="button" onClick={() => flagReview(review)} className="rounded-md border border-orange-200 bg-orange-50 px-3 py-1.5 text-xs font-bold text-orange-700 transition hover:bg-orange-100">Báo xấu</button>
                          <button type="button" onClick={() => markReviewSpam(review)} className="rounded-md border border-red-200 bg-red-50 px-3 py-1.5 text-xs font-bold text-red-700 transition hover:bg-red-100">Spam</button>
                          <button type="button" onClick={() => deleteReview(review)} className="rounded-md border border-red-200 bg-red-50 px-3 py-1.5 text-xs font-bold text-red-700 transition hover:bg-red-100">Xóa</button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </AdminTable>
              </AdminPanel>
            )}
            {tab === 'content' && (
              <AdminPanel
                title="Quản lý video"
                action={
                  <div className="flex flex-col gap-2 lg:flex-row lg:items-center">
                    <SearchBox value={query} onChange={setQuery} placeholder="Tìm tiêu đề, loại, mô tả" />
                    <select value={contentTypeFilter} onChange={(event) => setContentTypeFilter(event.target.value)} className="h-10 rounded-md border border-slate-200 bg-white px-3 text-sm font-semibold text-slate-700 outline-none focus:border-red-500">
                      <option value="all">Tất cả nhóm</option>
                      {videoCategoryOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                    </select>
                    <select value={contentStatusFilter} onChange={(event) => setContentStatusFilter(event.target.value)} className="h-10 rounded-md border border-slate-200 bg-white px-3 text-sm font-semibold text-slate-700 outline-none focus:border-red-500">
                      <option value="all">Tất cả trạng thái</option>
                      {contentStatusOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                    </select>
                  </div>
                }
              >
                {(canCreateContent || canUpdateContent) && <CollapsibleSection
                  title={editingContentId ? 'Đang chỉnh sửa nội dung' : 'Thêm video, banner hoặc trang marketing'}
                  description="Quản trị nội dung tập trung cho video, banner và bài marketing. Có thể gắn sản phẩm, danh mục, hẹn lịch đăng và nhập sẵn bình luận mẫu để kiểm duyệt."
                  defaultOpen={false}
                  forceOpen={Boolean(editingContentId)}
                  forceOpenKey={editingContentId}
                  onClose={resetContentForm}
                >
                  <form onSubmit={handleContentSubmit} className="grid gap-3 rounded-lg bg-slate-50 p-4 md:grid-cols-4">
                    <Input label="Tiêu đề" value={contentForm.title} required onChange={(value) => setContentForm({ ...contentForm, title: value })} />
                    <Select label="Nguồn video" value={contentForm.videoSource} onChange={(value) => setContentForm({ ...contentForm, videoSource: value, videoUrl: '' })} options={videoSourceOptions} />
                    <Select label="Nhóm nội dung" value={contentForm.videoCategory} onChange={(value) => setContentForm({ ...contentForm, videoCategory: value })} options={videoCategoryOptions} />
                    <Input label="Thứ tự hiển thị" type="number" value={contentForm.sortOrder} onChange={(value) => setContentForm({ ...contentForm, sortOrder: Number(value || 0) })} />
                    <Checkbox label="Đang hiển thị" checked={contentForm.isActive} onChange={(checked) => setContentForm({ ...contentForm, isActive: checked })} />
                    <div className="md:col-span-4">
                      <label className="block">
                        <span className="mb-1.5 block text-xs font-bold text-slate-500">Mô tả ngắn</span>
                        <textarea className="min-h-20 w-full rounded-md border border-slate-200 px-3 py-2 text-sm outline-none focus:border-red-500" value={contentForm.description} onChange={(event) => setContentForm({ ...contentForm, description: event.target.value })} />
                      </label>
                    </div>
                    {contentForm.videoSource === 'UPLOAD' ? (
                      <FileInput label="Upload video" accept="video/*" onFiles={async (files) => setContentForm({ ...contentForm, videoUrl: (await uploadFiles(files, 'content'))[0] || contentForm.videoUrl })} />
                    ) : (
                      <Input label="Link YouTube" value={contentForm.videoUrl} required onChange={(value) => setContentForm({ ...contentForm, videoUrl: value })} />
                    )}
                    <FileInput label="Upload thumbnail" accept="image/*" onFiles={async (files) => setContentForm({ ...contentForm, thumbnailUrl: (await uploadFiles(files, 'content'))[0] || contentForm.thumbnailUrl })} />
                    {contentForm.videoUrl && <div className="md:col-span-2"><VideoPreview title="Video đang chọn" url={contentForm.videoUrl} onRemove={() => setContentForm({ ...contentForm, videoUrl: '' })} /></div>}
                    {contentForm.thumbnailUrl && <div className="md:col-span-2"><MediaPreview title="Thumbnail đang chọn" items={[contentForm.thumbnailUrl]} onRemove={() => setContentForm({ ...contentForm, thumbnailUrl: '' })} /></div>}
                    <div className="md:col-span-4 rounded-lg border border-slate-200 bg-white p-3">
                      <div className="mb-3 text-xs font-bold text-slate-500">Sản phẩm liên kết</div>
                      <div className="grid gap-2 md:grid-cols-3">
                        <Input label="Tìm sản phẩm" value={videoProductSearch} onChange={setVideoProductSearch} />
                        <Select label="Lọc danh mục" value={videoProductCategoryFilter} onChange={setVideoProductCategoryFilter} options={[['all', 'Tất cả danh mục'], ...categories.map((category) => [String(category.id || category.code || category.slug), category.name] as [string, string])]} />
                        <Select label="Lọc thương hiệu" value={videoProductBrandFilter} onChange={setVideoProductBrandFilter} options={[['all', 'Tất cả thương hiệu'], ...brands.map((brand) => [String(brand.id || brand.name), brand.name] as [string, string])]} />
                      </div>
                      <div className="mt-3 grid max-h-72 gap-2 overflow-y-auto md:grid-cols-2">
                        {videoProductChoices.map((product) => (
                          <label key={product.id} className="flex cursor-pointer items-center gap-3 rounded-md border border-slate-200 p-2 text-sm transition hover:bg-slate-50">
                            <input type="checkbox" checked={selectedVideoProductIds.includes(product.id)} onChange={(event) => setVideoProductSelected(product.id, event.target.checked)} className="h-4 w-4 accent-red-600" />
                            {product.imageUrl && <img src={product.imageUrl} alt="" className="h-10 w-10 rounded bg-slate-50 object-contain" />}
                            <span className="min-w-0 flex-1">
                              <span className="block truncate font-semibold text-slate-900">{product.name}</span>
                              <span className="block truncate text-xs text-slate-500">{product.brand || product.categoryName || product.category || 'Sản phẩm'}</span>
                            </span>
                          </label>
                        ))}
                      </div>
                    </div>
                    <Input label="Lịch đăng" type="datetime-local" value={contentForm.scheduledAt} onChange={(value) => setContentForm({ ...contentForm, scheduledAt: value })} />
                    <Input label="Ngày public" type="datetime-local" value={contentForm.publishedAt} onChange={(value) => setContentForm({ ...contentForm, publishedAt: value })} />
                    <div className="md:col-span-4 rounded-md border border-dashed border-slate-200 bg-white p-3 text-xs text-slate-500">Lượt xem, lượt thích và bình luận được lấy từ tương tác thực tế của người dùng.</div>
                    <SubmitButtons editing={Boolean(editingContentId)} onCancel={resetContentForm} />
                  </form>
                </CollapsibleSection>}
                <AdminTable headers={['Tiêu đề', 'Media', 'Loại', 'Liên kết', 'Lịch & thứ tự', 'Tương tác', 'Trạng thái', 'Thao tác']}>
                  {filteredContentItems.length === 0 ? (
                    <tr><td colSpan={8} className="px-4 py-8 text-center text-sm font-medium text-slate-500">Không tìm thấy nội dung phù hợp.</td></tr>
                  ) : filteredContentItems.map((item) => (
                    <tr key={item.id}>
                      <td className="px-4 py-3">
                        <div className="font-semibold text-slate-900">{item.title}</div>
                        <div className="mt-1 text-xs text-slate-500">{item.description || '-'}</div>
                        {Array.isArray(item.comments) && item.comments.length > 0 && (
                          <div className="mt-3 max-w-xl rounded-lg border border-slate-200 bg-slate-50 p-2">
                            <div className="mb-2 text-xs font-bold text-slate-500">Bình luận video</div>
                            <div className="space-y-2">
                              {item.comments.slice(0, 4).map((comment: any) => (
                                <div key={comment.id} className={`rounded-md border bg-white p-2 text-xs ${comment.isHidden ? 'border-amber-200 opacity-70' : 'border-slate-200'}`}>
                                  <div className="flex items-start justify-between gap-2">
                                    <div className="min-w-0">
                                      <span className="font-bold text-slate-800">{comment.userName || 'Khách hàng'}</span>
                                      {comment.replyToUserName && <span className="ml-1 text-slate-500">trả lời @{comment.replyToUserName}</span>}
                                      <p className="mt-1 text-slate-600">{comment.content}</p>
                                      {comment.isHidden && <p className="mt-1 font-semibold text-amber-700">Đang ẩn{comment.moderationReason ? `: ${comment.moderationReason}` : ''}</p>}
                                    </div>
                                    <button type="button" onClick={() => toggleVideoCommentHidden(item, comment)} className="shrink-0 rounded border border-slate-200 px-2 py-1 font-bold text-slate-600 hover:bg-slate-50">{comment.isHidden ? 'Hiện' : 'Ẩn'}</button>
                                  </div>
                                  <div className="mt-2 flex gap-2">
                                    <input value={videoReplyDrafts[comment.id] || ''} onChange={(event) => setVideoReplyDrafts((drafts) => ({ ...drafts, [comment.id]: event.target.value }))} placeholder={`Trả lời ${comment.userName || 'khách hàng'}`} className="h-8 flex-1 rounded border border-slate-200 px-2 outline-none focus:border-red-400" />
                                    <button type="button" onClick={() => replyVideoComment(item, comment)} className="rounded bg-red-600 px-3 font-bold text-white">Gửi</button>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          {(item.thumbnailUrl || item.bannerImageUrl) ? (
                            <img src={item.thumbnailUrl || item.bannerImageUrl} alt="" className="h-14 w-20 rounded-md border border-slate-200 object-cover" />
                          ) : (
                            <div className="flex h-14 w-20 items-center justify-center rounded-md border border-dashed border-slate-200 text-[10px] font-bold text-slate-400">NO MEDIA</div>
                          )}
                          {item.videoUrl && (
                            <a href={item.videoUrl} target="_blank" rel="noreferrer" className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-slate-200 text-slate-600 transition hover:border-red-200 hover:bg-red-50 hover:text-red-700" title="Mở video">
                              <Eye className="h-4 w-4" />
                            </a>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <div>{videoCategoryOptions.find(([value]) => value === item.videoCategory)?.[1] || item.videoCategory || 'Video'}</div>
                        <div className="mt-1 text-xs text-slate-500">{item.videoSource === 'YOUTUBE' ? 'YouTube' : 'Upload'}</div>
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-600">
                        <div>{Array.isArray(item.products) && item.products.length ? `${item.products.length} sản phẩm` : 'Chưa gắn sản phẩm'}</div>
                        <div>{Array.isArray(item.categories) && item.categories.length ? `${item.categories.length} danh mục` : 'Chưa gắn danh mục'}</div>
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-600">
                        <div>Thứ tự: {item.sortOrder || 0}</div>
                        <div>{item.scheduledAt ? `Lên lịch: ${new Date(item.scheduledAt).toLocaleString('vi-VN')}` : 'Đăng ngay / không lịch'}</div>
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-600">
                        <div>{item.likeCount || 0} thích</div>
                        <div>{item.viewCount || 0} xem • {item.commentCount || 0} bình luận</div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex flex-col gap-2">
                          <AdminBadge tone={item.isActive ? 'green' : 'slate'}>{item.isActive ? 'Đang hiển thị' : 'Đã ẩn'}</AdminBadge>
                          {item.scheduledAt && new Date(item.scheduledAt).getTime() > Date.now() && <span className="text-xs font-semibold text-sky-700">Đang hẹn lịch</span>}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          {canUpdateContent && (
                            <button type="button" onClick={() => editContent(item)} className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-slate-200 text-slate-600 transition hover:border-sky-200 hover:bg-sky-50 hover:text-sky-700">
                              <Edit2 className="h-4 w-4" />
                            </button>
                          )}
                          {canDeleteContent && (
                            <button type="button" onClick={() => void confirmDelete(item.title, () => apiDb.adminDeleteVideo(item.id))} className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-slate-200 text-slate-600 transition hover:border-red-200 hover:bg-red-50 hover:text-red-700">
                              <Trash2 className="h-4 w-4" />
                            </button>
                          )}
                          {!canUpdateContent && !canDeleteContent && <span className="text-xs text-slate-400">Chỉ xem</span>}
                        </div>
                      </td>
                    </tr>
                  ))}
                </AdminTable>
              </AdminPanel>
            )}
            {tab === 'audit' && (
              <AdminPanel title="Nhật ký hoạt động Admin" action={<SearchBox value={query} onChange={setQuery} placeholder="Tìm event, resource, IP" />}>
                <AdminTable headers={['Thời gian', 'Sự kiện', 'Người thực hiện', 'IP', 'Tài nguyên', 'Kết quả']}>
                  {auditLogs
                    .filter((log) => matchesSearch({ ...log, resource: log.metadata?.resource, status: String(log.metadata?.status || '') }, query, ['eventType', 'userId', 'ipAddress', 'resource', 'status']))
                    .map((log) => (
                      <tr key={log.id}>
                        <td className="px-4 py-3">{log.createdAt ? new Date(log.createdAt).toLocaleString('vi-VN') : '-'}</td>
                        <td className="px-4 py-3 font-semibold text-slate-900">{log.eventType}</td>
                        <td className="px-4 py-3">{log.userId || log.email || '-'}</td>
                        <td className="px-4 py-3">{log.ipAddress || '-'}</td>
                        <td className="px-4 py-3">{log.metadata?.resource || log.metadata?.path || '-'}</td>
                        <td className="px-4 py-3"><AdminBadge tone={Number(log.metadata?.status || 0) >= 400 ? 'red' : 'green'}>{log.metadata?.status || 'OK'}</AdminBadge></td>
                      </tr>
                    ))}
                </AdminTable>
              </AdminPanel>
            )}
            {tab === 'permissions' && (
              <Suspense fallback={<div className="rounded-lg border border-slate-200 bg-white px-4 py-8 text-center text-sm font-semibold text-slate-500">?ang t?i ph?n quy?n...</div>}>
                <AdminPermissionsTab
                  addCustomerNote={addCustomerNote}
                  adjustCustomerPoints={adjustCustomerPoints}
                  auditLogs={auditLogs}
                  canManageCustomerAccess={canManageCustomerAccess}
                  canManageCustomerProfile={canManageCustomerProfile}
                  compactId={compactId}
                  createStaffAccount={createStaffAccount}
                  currency={currency}
                  customerActiveSection={customerActiveSection}
                  customerAuditLogs={customerAuditLogs}
                  customerDetailBusy={customerDetailBusy}
                  customerDetailOpen={customerDetailOpen}
                  customerLoyaltyHistory={customerLoyaltyHistory}
                  customerNoteDraft={customerNoteDraft}
                  customerNotes={customerNotes}
                  customerOrders={customerOrders}
                  customerPointDelta={customerPointDelta}
                  customerPointReason={customerPointReason}
                  customerTagDraft={customerTagDraft}
                  customerVoucherId={customerVoucherId}
                  customerVoucherNote={customerVoucherNote}
                  editingStaffAccessId={editingStaffAccessId}
                  issueCustomerVoucher={issueCustomerVoucher}
                  loadCustomerSection={loadCustomerSection}
                  openStaffPermissionEditor={openStaffPermissionEditor}
                  permissions={permissions}
                  permissionsByModule={permissionsByModule}
                  rolePermissionEditing={rolePermissionEditing}
                  rolePermissionMap={rolePermissionMap}
                  roles={roles}
                  saveCustomerTags={saveCustomerTags}
                  saveStaffPermissions={saveStaffPermissions}
                  selectedCustomer={selectedCustomer}
                  setCustomerActiveSection={setCustomerActiveSection}
                  setCustomerDetailOpen={setCustomerDetailOpen}
                  setCustomerNoteDraft={setCustomerNoteDraft}
                  setCustomerPointDelta={setCustomerPointDelta}
                  setCustomerPointReason={setCustomerPointReason}
                  setCustomerTagDraft={setCustomerTagDraft}
                  setCustomerVoucherId={setCustomerVoucherId}
                  setCustomerVoucherNote={setCustomerVoucherNote}
                  setEditingStaffAccessId={setEditingStaffAccessId}
                  setRolePermissionEditing={setRolePermissionEditing}
                  setStaffForm={setStaffForm}
                  setStaffPermissionDraft={setStaffPermissionDraft}
                  setStaffPermissionEditor={setStaffPermissionEditor}
                  staffBasePermissionCodes={staffBasePermissionCodes}
                  staffForm={staffForm}
                  staffPermissionDraft={staffPermissionDraft}
                  staffPermissionEditor={staffPermissionEditor}
                  staffUsers={staffUsers}
                  toggleRolePermission={toggleRolePermission}
                  updateUserAccess={updateUserAccess}
                  usePermission={usePermission}
                  vouchers={vouchers}
                />
              </Suspense>
            )}
            {inventoryDraft && (
              <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-950/55 px-4 py-6 backdrop-blur-sm">
                <form onSubmit={submitInventoryDraft} className="w-full max-w-3xl overflow-hidden rounded-lg bg-white shadow-2xl">
                  <div className="flex items-start justify-between gap-4 border-b border-slate-200 px-5 py-4">
                    <div>
                      <h3 className="text-lg font-bold text-slate-950">Nhập/điều chỉnh kho</h3>
                      <p className="mt-1 text-sm text-slate-500">{inventoryDraft.product.name}{inventoryDraft.variant?.sku ? ` / ${inventoryDraft.variant.sku}` : ''}</p>
                    </div>
                    <button type="button" onClick={() => setInventoryDraft(null)} title="Đóng popup" className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-slate-200 text-slate-600 transition hover:bg-slate-50 hover:text-slate-950">
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                  <div className="grid gap-3 p-5 md:grid-cols-2">
                    <Select label="Kiểu giao dịch" value={inventoryDraft.transactionType} onChange={(value) => setInventoryDraft({ ...inventoryDraft, transactionType: value })} options={inventoryTransactionOptions} />
                    <Input label="Số lượng thay đổi" type="number" value={inventoryDraft.delta} onChange={(value) => setInventoryDraft({ ...inventoryDraft, delta: Number(value) })} />
                    <Input label="Mã phiếu tham chiếu" value={inventoryDraft.referenceCode} required onChange={(value) => setInventoryDraft({ ...inventoryDraft, referenceCode: value })} />
                    <Input label="Lý do" value={inventoryDraft.reason} required onChange={(value) => setInventoryDraft({ ...inventoryDraft, reason: value })} />
                    <Input label="Nhà cung cấp" value={inventoryDraft.supplierName} onChange={(value) => setInventoryDraft({ ...inventoryDraft, supplierName: value })} />
                    <Input label="Giá nhập" type="number" value={inventoryDraft.unitCost} onChange={(value) => setInventoryDraft({ ...inventoryDraft, unitCost: Number(value) })} />
                    <Input label="Mã kho / chi nhánh" value={inventoryDraft.locationCode} onChange={(value) => setInventoryDraft({ ...inventoryDraft, locationCode: value })} />
                    <Input label="Tên kho / chi nhánh" value={inventoryDraft.locationName} onChange={(value) => setInventoryDraft({ ...inventoryDraft, locationName: value })} />
                    <Input label="Tồn kho tối thiểu" type="number" value={inventoryDraft.minimumStock} onChange={(value) => setInventoryDraft({ ...inventoryDraft, minimumStock: Math.max(0, Number(value)) })} />
                    <Input label="Chu kỳ kiểm kê (ngày)" type="number" value={inventoryDraft.cycleCountDays} onChange={(value) => setInventoryDraft({ ...inventoryDraft, cycleCountDays: Math.max(1, Number(value)) })} />
                    <label className="flex items-center gap-3 rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-medium text-slate-700 md:col-span-2">
                      <input type="checkbox" checked={inventoryDraft.blockSaleWhenOutOfStock} onChange={(event) => setInventoryDraft({ ...inventoryDraft, blockSaleWhenOutOfStock: event.target.checked })} className="h-4 w-4 rounded border-slate-300 text-red-600 focus:ring-red-500" />
                      Khóa bán khi hết hàng
                    </label>
                    <textarea className="min-h-20 rounded-md border border-slate-200 px-3 py-2 text-sm outline-none focus:border-red-500 md:col-span-2" placeholder="IMEI khi nhập kho, mỗi dòng một IMEI. Để trống hệ thống tự tạo từ SKU biến thể + 10 số ngẫu nhiên." value={inventoryDraft.imeis} onChange={(event) => setInventoryDraft({ ...inventoryDraft, imeis: event.target.value })} />
                    <textarea className="min-h-20 rounded-md border border-slate-200 px-3 py-2 text-sm outline-none focus:border-red-500 md:col-span-2" placeholder="Ghi chú kho" value={inventoryDraft.note} onChange={(event) => setInventoryDraft({ ...inventoryDraft, note: event.target.value })} />
                    <div className="rounded-md border border-slate-200 bg-slate-50 p-3 md:col-span-2">
                      <div className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-400">Lịch sử gần nhất</div>
                      {inventoryDraft.logs.length === 0 ? (
                        <div className="text-sm font-medium text-slate-500">Chưa có giao dịch kho.</div>
                      ) : (
                        <div className="max-h-52 overflow-y-auto divide-y divide-slate-200 rounded-md bg-white">
                          {inventoryDraft.logs.map((log) => (
                            <div key={log.id} className="grid gap-2 px-3 py-2 text-xs text-slate-600 md:grid-cols-[1fr_90px_100px]">
                              <span className="font-semibold text-slate-800">{log.referenceCode || '-'} · {log.transactionType}{log.locationCode ? ` · ${log.locationCode}` : ''}</span>
                              <span className={Number(log.delta || 0) >= 0 ? 'font-bold text-emerald-700' : 'font-bold text-red-700'}>{Number(log.delta || 0) >= 0 ? '+' : ''}{log.delta}</span>
                              <span>{log.createdAt ? new Date(log.createdAt).toLocaleDateString('vi-VN') : '-'}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                    <div className="flex justify-end gap-2 md:col-span-2">
                      <button type="button" onClick={() => setInventoryDraft(null)} className="h-10 rounded-md border border-slate-200 px-4 text-sm font-bold text-slate-700">Há»§y</button>
                      <button type="submit" className="h-10 rounded-md bg-amber-600 px-4 text-sm font-bold text-white">Lưu giao dịch</button>
                    </div>
                  </div>
                </form>
              </div>
            )}
            {previewProduct && (
              <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-950/55 px-4 py-6 backdrop-blur-sm">
                <div className="w-full max-w-4xl overflow-hidden rounded-lg bg-white shadow-2xl">
                  <div className="flex items-start justify-between gap-4 border-b border-slate-200 px-5 py-4">
                    <div>
                      <h3 className="text-lg font-bold text-slate-950">Preview sản phẩm</h3>
                      <p className="mt-1 text-sm text-slate-500">{previewProduct.status === 'ACTIVE' ? 'Bản đang public' : 'Bản xem trước trước khi public'}</p>
                    </div>
                    <button type="button" onClick={() => setPreviewProduct(null)} title="Đóng popup" className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-slate-200 text-slate-600 transition hover:bg-slate-50 hover:text-slate-950">
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                  <div className="grid gap-5 p-5 md:grid-cols-[260px_minmax(0,1fr)]">
                    <div className="rounded-md border border-slate-200 bg-slate-50 p-4">
                      {previewProduct.imageUrl ? <img src={previewProduct.imageUrl} alt="" className="h-56 w-full object-contain" /> : <Image className="mx-auto h-16 w-16 text-slate-300" />}
                      <div className="mt-3 flex flex-wrap gap-2">
                        {(previewProduct.images || []).slice(0, 4).map((url: string) => <img key={url} src={url} alt="" className="h-12 w-12 rounded-md border border-slate-200 object-contain" />)}
                      </div>
                    </div>
                    <div className="min-w-0">
                      <div className="mb-2 flex flex-wrap items-center gap-2">
                        <AdminBadge tone={previewProduct.status === 'ACTIVE' ? 'green' : previewProduct.status === 'PENDING' ? 'blue' : 'yellow'}>{productStatusLabel[previewProduct.status] || previewProduct.status}</AdminBadge>
                        <span className="text-xs font-semibold text-slate-500">{previewProduct.sku || compactId(previewProduct.id)}</span>
                      </div>
                      <h3 className="text-2xl font-black text-slate-950">{previewProduct.name}</h3>
                      <div className="mt-2 text-xl font-black text-red-600">{currency.format(Number(previewProduct.discountPrice || previewProduct.price || 0))}</div>
                      <p className="mt-4 whitespace-pre-line text-sm leading-6 text-slate-600">{previewProduct.description || 'Chưa có mô tả.'}</p>
                      <div className="mt-4 grid gap-3 sm:grid-cols-2">
                        <MiniMetric label="SEO title" value={previewProduct.seoMetadata?.title || previewProduct.specifications?._seoTitle || '-'} helper={previewProduct.seoMetadata?.description || previewProduct.specifications?._seoDescription || 'Chưa có meta description'} />
                        <MiniMetric
                          label="Mua kèm giảm giá"
                          value={(previewProduct.salesConfig?.accessoryOffers || []).map((item: any) => item.productName || item.productSku || item.productId).join(', ') || '-'}
                          helper="Cấu hình giảm giá và số lượng được giảm theo từng sản phẩm mua kèm"
                        />
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
