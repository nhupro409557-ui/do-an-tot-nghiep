import React, { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Activity,
  AlertTriangle,
  BadgePercent,
  BarChart3,
  Bell,
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
  Home,
  Image,
  LayoutDashboard,
  LogOut,
  Menu,
  Megaphone,
  MoreHorizontal,
  Package,
  Plus,
  RefreshCw,
  RotateCcw,
  Search,
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
import { Area, AreaChart, Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { useAuth } from '../context/AuthContext';
import { apiDb } from '../services/apiDb';
import { signOut } from '../services/authDb';

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
  overridePrice: number | '';
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
  { id: 'content', label: 'Video & nội dung', group: 'Vận hành', icon: Megaphone },
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
  const [contentItems, setContentItems] = useState<any[]>([]);
  const [contentForm, setContentForm] = useState(emptyContentForm);
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [permissions, setPermissions] = useState<any[]>([]);
  const [roles, setRoles] = useState<any[]>([]);
  const [rolePermissionMap, setRolePermissionMap] = useState<Record<string, string[]>>({});
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
  const filteredProducts = useMemo(() => {
    return products.filter((product) => matchesSearch(product, query, ['name', 'brand', 'categoryName', 'category', 'sku', 'status']));
  }, [products, query]);
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
    return brands.filter((brand) => matchesSearch(brand, query, ['name', 'code']));
  }, [brands, query]);
  const filteredOrders = useMemo(() => {
    return orders.filter((order) => matchesSearch(order, query, ['id', 'orderCode', 'userId', 'user_id', 'recipientName', 'recipientPhone', 'paymentMethod', 'payment_method', 'trackingCode', 'status']));
  }, [orders, query]);
  const filteredVouchers = useMemo(() => {
    return vouchers.filter((voucher) => matchesSearch(voucher, query, ['code', 'discountType', 'status']));
  }, [vouchers, query]);
  const filteredCustomers = useMemo(() => customers, [customers]);
  const filteredInventory = useMemo(() => {
    return products.filter((product) => matchesSearch(product, query, ['name', 'sku', 'brand', 'categoryName', 'status']));
  }, [products, query]);
  const filteredReviews = useMemo(() => {
    return reviews.filter((review) => {
      const matchesQuery = matchesSearch(review, query, ['productName', 'userName', 'status', 'comment', 'moderationNote', 'shopReply', 'flaggedReason', 'spamReason', 'orderOutcome']);
      const matchesStatus = reviewStatusFilter === 'all' || review.status === reviewStatusFilter;
      const matchesStars = reviewStarFilter === 'all' || String(review.rating) === reviewStarFilter;
      return matchesQuery && matchesStatus && matchesStars;
    });
  }, [reviews, query, reviewStatusFilter, reviewStarFilter]);
  const filteredContentItems = useMemo(() => {
    return contentItems.filter((item) => matchesSearch(item, query, ['title', 'description', 'status']));
  }, [contentItems, query]);
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

  useEffect(() => {
    if (canAccessAdmin) loadData();
  }, [canAccessAdmin]);

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
    if (canAccessAdmin && tab === 'brands') loadData();
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
        await loadData();
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
      void loadData();
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

  async function loadData() {
    setBusy(true);
    try {
      const [overviewData, orderData, productData, categoryData, brandData, serviceData, voucherData, customerData, reviewData, reviewSummaryData, contentData, auditData, permissionData, roleData] = await Promise.all([
        apiDb.adminOverview().catch(() => ({})),
        apiDb.listOrders().catch(() => []),
        apiDb.adminListProducts().catch(() => apiDb.listProducts()),
        apiDb.adminListCategories().catch(() => apiDb.listCategories()),
        apiDb.adminListBrands({ page: brandPage, limit: 10, search: query, status: brandStatusFilter }).catch(() => apiDb.listBrands().then((items) => ({ items, total: items.length, page: 1, limit: items.length || 10 }))),
        apiDb.adminListAttachedServices().catch(() => []),
        apiDb.adminListVouchers().catch(() => []),
        apiDb.adminListCustomers({ search: query, page: customerPage, limit: 20 }).catch(() => ({ items: [], total: 0, page: 1, limit: 20 })),
        apiDb.adminListReviews().catch(() => []),
        apiDb.adminListReviewSummary().catch(() => []),
        apiDb.adminListContent().catch(() => []),
        apiDb.adminListAuditLogs({ limit: 100 }).catch(() => []),
        apiDb.adminListPermissions().catch(() => []),
        apiDb.adminListRoles().catch(() => []),
      ]);
      setOverview(overviewData);
      setOrders(orderData);
      setProducts(productData);
      setCategories(categoryData);
      setBrands(Array.isArray(brandData) ? brandData : brandData.items || []);
      setAttachedServices(serviceData);
      setBrandTotal(Array.isArray(brandData) ? brandData.length : brandData.total || 0);
      setBrandImportJobs(tab === 'brands' ? await apiDb.adminListBrandImportJobs().catch(() => []) : brandImportJobs);
      setVouchers(voucherData);
      setCustomers(Array.isArray(customerData) ? customerData : customerData.items || []);
      setCustomerTotal(Array.isArray(customerData) ? customerData.length : customerData.total || 0);
      setReviews(reviewData);
      setReviewSummary(reviewSummaryData);
      setContentItems(contentData);
      setAuditLogs(auditData);
      setPermissions(permissionData);
      setRoles(roleData);
      const roleEntries = await Promise.all((roleData || []).map(async (role: any) => {
        const detail = await apiDb.adminGetRolePermissions(role.id).catch(() => ({ permissionCodes: [] }));
        return [role.id, detail.permissionCodes || []] as const;
      }));
      setRolePermissionMap(Object.fromEntries(roleEntries));
    } finally {
      setBusy(false);
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
        overridePrice: item.overridePrice === '' ? null : Number(item.overridePrice),
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
    await loadData();
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
    await loadData();
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
    await loadData();
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
    await loadData();
  }


  async function handleContentSubmit(event: React.FormEvent) {
    event.preventDefault();
    const payload = {
      ...contentForm,
      productIds: splitIds(contentForm.productIds),
      categoryIds: splitIds(contentForm.categoryIds),
      comments: serializeContentComments(contentForm.commentsText),
      likeCount: Number(contentForm.likeCount || 0),
      viewCount: Number(contentForm.viewCount || 0),
      sortOrder: Number(contentForm.sortOrder || 0),
      scheduledAt: contentForm.scheduledAt || null,
      publishedAt: contentForm.publishedAt || null,
      videoUrl: contentForm.videoUrl || null,
      thumbnailUrl: contentForm.thumbnailUrl || null,
      bannerImageUrl: contentForm.bannerImageUrl || null,
      ctaLabel: contentForm.ctaLabel || null,
      ctaUrl: contentForm.ctaUrl || null,
      version: editingContentId ? Number(contentForm.version || 1) : undefined,
    };
    if (editingContentId) await apiDb.adminUpdateContent(editingContentId, payload);
    else await apiDb.adminCreateContent(payload);
    resetContentForm();
    await loadData();
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
        overridePrice: item.overridePrice ?? '',
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

  async function confirmDelete(label: string, action: () => Promise<unknown>) {
    if (!window.confirm(`Bạn có chắc muốn xóa ${label}? Nếu mục này đã có dữ liệu liên quan, hệ thống sẽ ẩn thay vì xóa để giữ lịch sử.`)) return;
    try {
      const result = await action() as { action?: string };
      await loadData();
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
    await loadData();
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
    await loadData();
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
    await loadData();
  }

  async function approveProduct(product: any) {
    await apiDb.adminApproveProduct(product.id);
    await loadData();
  }

  async function duplicateProduct(product: any) {
    const result = await apiDb.adminDuplicateProduct(product.id);
    await loadData();
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
    await loadData();
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
    await loadData();
  }

  async function reactivateCategory(category: any) {
    await apiDb.adminRestoreCategory(category.id);
    await refreshCategoryWorkspace(category.id);
    window.alert('Danh mục đã được khôi phục. Các sản phẩm thuộc danh mục này vẫn đang ở trạng thái Ẩn. Vui lòng vào Quản lý sản phẩm để kích hoạt lại nếu cần.');
  }

  async function reactivateBrand(brand: any) {
    await apiDb.adminUpdateBrandStatus(brand.id, true);
    await loadData();
  }

  async function hideBrand(brand: any) {
    if (!window.confirm(`Ẩn thương hiệu ${brand.name}? Thương hiệu sẽ không hiển thị ở storefront.`)) return;
    await apiDb.adminUpdateBrandStatus(brand.id, false);
    await loadData();
  }

  async function bulkUpdateBrandStatus(isActive: boolean) {
    if (!selectedBrandIds.length) return;
    if (!window.confirm(`${isActive ? 'Khôi phục' : 'Ẩn'} ${selectedBrandIds.length} thương hiệu đã chọn?`)) return;
    const result = await apiDb.adminUpdateBrandsStatus(selectedBrandIds, isActive);
    setSelectedBrandIds([]);
    await loadData();
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
    setAccessorySuggestions([]);
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
            overridePrice: '',
          },
        ],
      });
  }

  function patchAttachedService(serviceId: string, patch: Partial<AttachedServiceForm>) {
    setProductForm((prev) => ({
      ...prev,
      attachedServices: prev.attachedServices.map((item) => (item.serviceId === serviceId ? { ...item, ...patch } : item)),
    }));
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
      priceMode: service.priceMode || 'FIXED',
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
    if (editingServiceId) await apiDb.adminUpdateAttachedService(editingServiceId, serviceForm);
    else await apiDb.adminCreateAttachedService(serviceForm);
    resetServiceForm();
    await loadData();
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
    await loadData();
  }

  async function replyToReview(review: any) {
    const nextReply = window.prompt(`Phản hồi đánh giá cho ${review.userName || 'khách hàng'}`, review.shopReply || '');
    if (nextReply === null) return;
    await apiDb.adminUpdateReview(review.id, { shopReply: nextReply });
    await loadData();
  }

  async function flagReview(review: any) {
    const reason = window.prompt(`Lý do báo cáo/đánh dấu đánh giá của ${review.userName || 'khách hàng'}`, review.flaggedReason || 'Có dấu hiệu nội dung xấu hoặc cần xem xét thêm');
    if (reason === null) return;
    await apiDb.adminUpdateReview(review.id, { flaggedReason: reason, status: review.status === 'PUBLISHED' ? 'HIDDEN' : review.status });
    await loadData();
  }

  async function markReviewSpam(review: any) {
    const reason = window.prompt(`Lý do đánh dấu spam cho đánh giá của ${review.userName || 'khách hàng'}`, review.spamReason || 'Spam hoặc nội dung lặp bất thường');
    if (reason === null) return;
    await apiDb.adminUpdateReview(review.id, { isSpam: true, spamReason: reason, status: 'REJECTED', moderationNote: 'Đánh dấu spam bởi quản trị viên.' });
    await loadData();
  }

  async function deleteReview(review: any) {
    if (!window.confirm(`Xóa vĩnh viễn đánh giá của ${review.userName || 'khách hàng'} cho sản phẩm ${review.productName}?`)) return;
    await apiDb.adminDeleteReview(review.id);
    await loadData();
  }

  async function updateUserAccess(customer: any, patch: { role?: string; status?: string }) {
    if (!usePermission('sys:manage_users')) return;
    await apiDb.adminUpdateUserRole(customer.id, {
      role: patch.role || customer.role || 'CUSTOMER',
      status: patch.status || customer.status || 'ACTIVE',
    });
    await loadData();
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
    await loadData();
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
    await loadData();
  }

  async function bulkApplyCustomerTags() {
    if (!selectedCustomerIds.length || !canManageCustomerProfile) return;
    const tags = customerTagDraft.split(',').map((item) => item.trim()).filter(Boolean);
    await apiDb.adminBulkUpdateCustomerTags(selectedCustomerIds, tags);
    setSelectedCustomerIds([]);
    await loadData();
  }

  async function toggleRolePermission(roleId: string, code: string, checked: boolean) {
    const current = rolePermissionMap[roleId] || [];
    const next = checked ? [...new Set([...current, code])] : current.filter((item) => item !== code);
    setRolePermissionMap((prev) => ({ ...prev, [roleId]: next }));
    await apiDb.adminUpdateRolePermissions(roleId, next);
    await loadData();
  }

  if (loading || !canAccessAdmin) return <div className="flex min-h-[60vh] items-center justify-center text-sm font-semibold text-slate-500">Đang kiểm tra quyền truy cập...</div>;

  const revenueByDay = Array.from(
    orders.reduce((map: Map<string, number>, order) => {
      const key = getOrderDate(order).toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit' });
      map.set(key, (map.get(key) || 0) + getOrderTotal(order));
      return map;
    }, new Map<string, number>()),
    ([date, total]) => ({ date, total }),
  ).slice(-14);
  const revenueByMonth = Array.from(
    orders.reduce((map: Map<string, number>, order) => {
      const key = getOrderDate(order).toLocaleDateString('vi-VN', { month: '2-digit', year: 'numeric' });
      map.set(key, (map.get(key) || 0) + getOrderTotal(order));
      return map;
    }, new Map<string, number>()),
    ([month, total]) => ({ month, total }),
  ).slice(-6);
  const topProducts = [...products]
    .sort((a, b) => getProductSold(b) - getProductSold(a) || toNumber(b.periodRevenue) - toNumber(a.periodRevenue))
    .slice(0, 5);
  const cancelledOrders = orders.filter((item) => ['CANCELLED', 'CANCELED'].includes(String(item.status).toUpperCase())).length;
  const refundedOrders = orders.filter((item) => ['REFUNDED', 'RETURNED', 'RETURNING'].includes(String(item.status).toUpperCase())).length;
  const riskyVouchers = vouchers.filter((item) => item.status === 'ACTIVE' && getVoucherBudgetUsage(item) >= 0.8);
  const negativeStockProducts = products.filter((item) => getProductStock(item) < 0);
  const lowStockProducts = products.filter((item) => {
    const threshold = getInventorySettings(item).minimumStock;
    const stock = getProductStock(item);
    return stock >= 0 && stock <= threshold;
  });
  const roleDashboards = [
    { role: 'Nhân viên kho', metric: `${lowStockProducts.length + negativeStockProducts.length} cảnh báo`, helper: 'Thiếu hàng, tồn kho âm hoặc cần kiểm kê', icon: Boxes },
    { role: 'CSKH', metric: `${orders.filter((item) => ['PENDING', 'PROCESSING'].includes(String(item.status).toUpperCase())).length} đơn cần theo dõi`, helper: 'Ưu tiên đơn chờ xử lý và phản hồi mới', icon: UserCircle },
    { role: 'Quản lý', metric: currency.format(revenue), helper: 'Theo dõi doanh thu, tỉ lệ hủy và ngân sách voucher', icon: ShieldCheck },
  ];

  const stats = [
    { label: 'Doanh thu', value: currency.format(revenue), icon: WalletCards, tone: 'emerald', caption: `${orders.length} đơn đã ghi nhận` },
    { label: 'Sản phẩm', value: overview.products ?? products.length, icon: Package, tone: 'red', caption: `${products.filter((item) => item.status === 'ACTIVE').length} đang bán` },
    { label: 'Đơn hàng', value: overview.orders ?? orders.length, icon: Truck, tone: 'sky', caption: `${orders.filter((item) => item.status === 'PENDING').length} chờ xử lý` },
    { label: 'Voucher', value: overview.vouchers ?? vouchers.length, icon: BadgePercent, tone: 'amber', caption: `${vouchers.filter((item) => item.status === 'ACTIVE').length} đang chạy` },
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
        <AdminTopBar onRefresh={loadData} query={query} setQuery={setQuery} sidebarOpen={sidebarOpen} searchPlaceholder={searchPlaceholderByTab[tab]} onToggleSidebar={() => setSidebarOpen((value) => !value)} />
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
              <div className="space-y-5">
                <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                  {stats.map((item) => {
                    const Icon = item.icon;
                    return (
                      <StatCard key={item.label} label={item.label} value={item.value} caption={item.caption} icon={Icon} tone={item.tone as StatTone} />
                    );
                  })}
                </div>
                <div className="grid gap-5 xl:grid-cols-[1.15fr_0.85fr]">
                  <AdminPanel title="Nhịp vận hành hôm nay" action={<Activity className="h-5 w-5 text-red-600" />}>
                    <div className="grid gap-3 md:grid-cols-3">
                      <MiniMetric label="Đơn chờ xử lý" value={orders.filter((item) => item.status === 'PENDING').length} helper="Cần xác nhận sớm" />
                      <MiniMetric label="Sản phẩm sắp hết" value={lowStockProducts.length} helper="Ưu tiên nhập kho" />
                      <MiniMetric label="Đánh giá mới" value={reviews.length} helper="Theo dõi trải nghiệm" />
                    </div>
                  </AdminPanel>
                  <AdminPanel title="Danh mục dữ liệu" action={<ShoppingBag className="h-5 w-5 text-red-600" />}>
                    <div className="space-y-3">
                      {[
                        ['Danh mục', categories.length, FolderTree],
                        ['Thương hiệu', brands.length, Building2],
                        ['Khách hàng', customers.length, Users],
                      ].map(([label, value, Icon]: [string, number, any]) => (
                        <div key={label} className="flex items-center justify-between rounded-md border border-slate-100 bg-slate-50 px-3 py-2">
                          <span className="flex items-center gap-2 text-sm font-semibold text-slate-600">
                            <Icon className="h-4 w-4 text-slate-400" />
                            {label}
                          </span>
                          <span className="font-mono text-sm font-bold text-slate-900">{value}</span>
                        </div>
                      ))}
                    </div>
                  </AdminPanel>
                </div>
                <div className="grid gap-5 xl:grid-cols-[1.25fr_0.75fr]">
                  <AdminPanel title="Doanh thu theo ngày" action={<TrendingUp className="h-5 w-5 text-emerald-600" />}>
                    <div className="h-72">
                      <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={revenueByDay} margin={{ top: 10, right: 12, left: 0, bottom: 0 }}>
                          <defs>
                            <linearGradient id="adminRevenue" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="5%" stopColor="#10b981" stopOpacity={0.28} />
                              <stop offset="95%" stopColor="#10b981" stopOpacity={0.02} />
                            </linearGradient>
                          </defs>
                          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                          <XAxis dataKey="date" tick={{ fontSize: 12 }} stroke="#64748b" />
                          <YAxis tickFormatter={(value) => compactCurrency.format(Number(value))} tick={{ fontSize: 12 }} stroke="#64748b" width={48} />
                          <Tooltip formatter={(value) => currency.format(Number(value))} labelFormatter={(label) => `Ngày ${label}`} />
                          <Area type="monotone" dataKey="total" stroke="#059669" strokeWidth={3} fill="url(#adminRevenue)" />
                        </AreaChart>
                      </ResponsiveContainer>
                    </div>
                  </AdminPanel>
                  <AdminPanel title="Doanh thu theo tháng" action={<BarChart3 className="h-5 w-5 text-sky-600" />}>
                    <div className="h-72">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={revenueByMonth} margin={{ top: 10, right: 12, left: 0, bottom: 0 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                          <XAxis dataKey="month" tick={{ fontSize: 12 }} stroke="#64748b" />
                          <YAxis tickFormatter={(value) => compactCurrency.format(Number(value))} tick={{ fontSize: 12 }} stroke="#64748b" width={48} />
                          <Tooltip formatter={(value) => currency.format(Number(value))} />
                          <Bar dataKey="total" fill="#2563eb" radius={[6, 6, 0, 0]} />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </AdminPanel>
                </div>
                <div className="grid gap-5 xl:grid-cols-3">
                  <AdminPanel title="Top sản phẩm bán chạy" action={<ShoppingBag className="h-5 w-5 text-red-600" />}>
                    <div className="space-y-3">
                      {topProducts.map((product, index) => (
                        <div key={product.id || product.name} className="flex items-center gap-3 rounded-md border border-slate-100 bg-slate-50 px-3 py-2">
                          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-red-100 text-sm font-black text-red-700">{index + 1}</span>
                          <div className="min-w-0 flex-1">
                            <div className="truncate text-sm font-bold text-slate-800">{product.name}</div>
                            <div className="text-xs font-semibold text-slate-500">{getProductSold(product)} đã bán</div>
                          </div>
                          <span className="text-xs font-bold text-slate-700">{compactCurrency.format(toNumber(product.periodRevenue))}</span>
                        </div>
                      ))}
                      {topProducts.length === 0 && <EmptyState text="Chưa có dữ liệu bán chạy." />}
                    </div>
                  </AdminPanel>
                  <AdminPanel title="Tỉ lệ hủy và hoàn đơn" action={<RotateCcw className="h-5 w-5 text-amber-600" />}>
                    <div className="grid gap-3">
                      <MiniMetric label="Tỉ lệ hủy đơn" value={orders.length ? percent.format(cancelledOrders / orders.length) : '0%'} helper={`${cancelledOrders} đơn đã hủy`} />
                      <MiniMetric label="Tỉ lệ hoàn đơn" value={orders.length ? percent.format(refundedOrders / orders.length) : '0%'} helper={`${refundedOrders} đơn hoàn / trả`} />
                    </div>
                  </AdminPanel>
                  <AdminPanel title="Cảnh báo điều hành" action={<AlertTriangle className="h-5 w-5 text-amber-600" />}>
                    <div className="space-y-3">
                      <AlertRow label="Voucher gần hết ngân sách" value={riskyVouchers.length} detail="Đã dùng từ 80% ngân sách" />
                      <AlertRow label="Tồn kho âm" value={negativeStockProducts.length} detail="Cần đối soát lệch kho" />
                      <AlertRow label="Sắp hết hàng" value={lowStockProducts.length} detail="Dựa trên ngưỡng tối thiểu từng sản phẩm" />
                    </div>
                  </AdminPanel>
                </div>
                <AdminPanel title="Dashboard theo vai trò" action={<ShieldCheck className="h-5 w-5 text-slate-600" />}>
                  <div className="grid gap-3 md:grid-cols-3">
                    {roleDashboards.map((item) => {
                      const Icon = item.icon;
                      return (
                        <div key={item.role} className="rounded-md border border-slate-100 bg-white p-4 shadow-sm">
                          <div className="flex items-center gap-3">
                            <span className="flex h-10 w-10 items-center justify-center rounded-md bg-slate-100 text-slate-700">
                              <Icon className="h-5 w-5" />
                            </span>
                            <div>
                              <div className="text-sm font-black text-slate-900">{item.role}</div>
                              <div className="text-xs font-semibold text-slate-500">{item.metric}</div>
                            </div>
                          </div>
                          <p className="mt-3 text-sm font-medium leading-5 text-slate-600">{item.helper}</p>
                        </div>
                      );
                    })}
                  </div>
                </AdminPanel>
              </div>
            )}

            {tab === 'products' && (
              <AdminPanel title="Quản lý sản phẩm, media và biến thể" action={
                <div className="flex flex-wrap items-center gap-2">
                  <SearchBox value={query} onChange={setQuery} placeholder="Tìm sản phẩm, SKU, thương hiệu" />
                  <button type="button" onClick={exportProducts} className="inline-flex h-10 items-center gap-2 rounded-md border border-slate-200 bg-white px-3 text-xs font-bold text-slate-700"><Download className="h-4 w-4" />Xuất</button>
                  <label className="inline-flex h-10 cursor-pointer items-center gap-2 rounded-md border border-slate-200 bg-white px-3 text-xs font-bold text-slate-700">
                    <Upload className="h-4 w-4" />Import
                    <input type="file" accept=".csv,text/csv" className="hidden" onChange={(event) => importProducts(event.target.files)} />
                  </label>
                </div>
              }>
                <CollapsibleSection title={editingProductId ? 'Đang chỉnh sửa sản phẩm' : 'Thêm sản phẩm mới'} description="Mở popup khi cần nhập sản phẩm, media, thông số và biến thể. Bảng sản phẩm bên dưới vẫn luôn sẵn sàng để tìm kiếm." defaultOpen={false} forceOpen={Boolean(editingProductId)} forceOpenKey={editingProductId} onClose={resetProductForm}>
                  <form onSubmit={handleProductSubmit} className="mb-5 grid gap-3 rounded-lg bg-slate-50 p-4 md:grid-cols-4">
                    <Input label="Tên sản phẩm" value={productForm.name} required onChange={(value) => setProductForm({ ...productForm, name: value })} />
                    <Input label="Giá gốc chung" type="number" value={productForm.price} onChange={(value) => setProductForm({ ...productForm, price: Number(value) })} />
                    <Input label="Giá bán chung" type="number" value={productForm.discountPrice} onChange={(value) => setProductForm({ ...productForm, discountPrice: Number(value) })} />
                    <Select label="Danh mục cha" value={productForm.categoryId} onChange={(value) => {
                      const category = rootCategories.find((item) => item.id === value);
                      const nextWarranty = productForm.warrantyPolicy.inheritWarrantyPolicy ? categoryWarrantyPolicy(category) : productForm.warrantyPolicy;
                      setProductForm({ ...productForm, categoryId: value, category: (category?.code || category?.slug || productForm.category).toUpperCase(), warrantyPolicy: nextWarranty, specifications: {}, variantSpecKeys: [], variants: productForm.variants.map((variant) => ({ ...variant, specs: {} })) });
                    }} options={[['', 'Chưa chọn'], ...rootCategories.map((item) => [item.id, item.name] as [string, string])]} />
                    <Select label="Danh mục con" value={productForm.subcategoryId} onChange={(value) => {
                      const child = subCategories.find((item) => item.id === value);
                      const parent = rootCategories.find((item) => item.id === (child?.parentId || productForm.categoryId));
                      const nextWarranty = productForm.warrantyPolicy.inheritWarrantyPolicy ? categoryWarrantyPolicy(child || parent, parent) : productForm.warrantyPolicy;
                      setProductForm({ ...productForm, subcategoryId: value, warrantyPolicy: nextWarranty });
                    }} options={[['', 'Chưa chọn'], ...subCategories.map((item) => [item.id, `${item.parentName || 'Khác'} / ${item.name}`] as [string, string])]} />
                    <Select label="Thương hiệu" value={productForm.brandId} onChange={(value) => {
                      const brand = brands.find((item) => item.id === value);
                      setProductForm({ ...productForm, brandId: value, brand: brand?.name || productForm.brand });
                    }} options={[['', 'Nhập tay'], ...brands.map((item) => [item.id, item.name] as [string, string])]} />
                    <Select label="Trạng thái" value={productForm.status} onChange={(value) => setProductForm({ ...productForm, status: value })} options={productStatusOptions} />
                    <Input label="Thương hiệu nhập tay" value={productForm.brand} onChange={(value) => setProductForm({ ...productForm, brand: value })} />
                    <FileInput label="Ảnh đại diện chung" accept="image/*" onFiles={async (files) => setProductForm({ ...productForm, imageUrl: (await uploadFiles(files, 'products'))[0] || productForm.imageUrl })} />
                    <FileInput label="Video sản phẩm dùng chung" accept="video/*" onFiles={async (files) => setProductForm({ ...productForm, videoUrl: (await uploadFiles(files, 'products'))[0] || productForm.videoUrl })} />
                    <MediaPreview title="Ảnh đại diện chung" items={productForm.imageUrl ? [productForm.imageUrl] : []} onRemove={() => setProductForm({ ...productForm, imageUrl: '' })} />
                    {productForm.videoUrl && <VideoPreview title="Video sản phẩm dùng chung" url={productForm.videoUrl} onRemove={() => setProductForm({ ...productForm, videoUrl: '' })} />}
                    <div className="rounded-md border border-slate-200 bg-white p-3 md:col-span-4">
                      <div className="mb-3 text-sm font-bold text-slate-700">Bảo hành sản phẩm</div>
                      <div className="grid gap-3 md:grid-cols-5">
                        <Checkbox label="Theo danh mục" checked={productForm.warrantyPolicy.inheritWarrantyPolicy} onChange={(checked) => {
                          const parent = rootCategories.find((item) => item.id === productForm.categoryId);
                          const child = subCategories.find((item) => item.id === productForm.subcategoryId);
                          setProductForm({ ...productForm, warrantyPolicy: checked ? categoryWarrantyPolicy(child || parent, parent) : { ...productForm.warrantyPolicy, inheritWarrantyPolicy: false } });
                        }} />
                        <Checkbox label="Có bảo hành" checked={productForm.warrantyPolicy.hasWarranty} disabled={productForm.warrantyPolicy.inheritWarrantyPolicy} onChange={(checked) => setProductForm({ ...productForm, warrantyPolicy: { ...productForm.warrantyPolicy, hasWarranty: checked, inheritWarrantyPolicy: false } })} />
                        <Input label="Tháng bảo hành" type="number" disabled={productForm.warrantyPolicy.inheritWarrantyPolicy} value={productForm.warrantyPolicy.warrantyMonths} onChange={(value) => setProductForm({ ...productForm, warrantyPolicy: { ...productForm.warrantyPolicy, warrantyMonths: Math.max(0, Number(value)), inheritWarrantyPolicy: false } })} />
                        <Checkbox label="Có 1 đổi 1" checked={productForm.warrantyPolicy.allowOneForOne} disabled={productForm.warrantyPolicy.inheritWarrantyPolicy} onChange={(checked) => setProductForm({ ...productForm, warrantyPolicy: { ...productForm.warrantyPolicy, allowOneForOne: checked, inheritWarrantyPolicy: false } })} />
                        <Input label="Ngày 1 đổi 1" type="number" disabled={productForm.warrantyPolicy.inheritWarrantyPolicy} value={productForm.warrantyPolicy.oneForOneDays} onChange={(value) => setProductForm({ ...productForm, warrantyPolicy: { ...productForm.warrantyPolicy, oneForOneDays: Math.max(0, Number(value)), inheritWarrantyPolicy: false } })} />
                      </div>
                    </div>

                    {productSpecFields.length > 0 && (
                      <div className="rounded-md border border-slate-200 bg-white p-3 md:col-span-4">
                        <div className="mb-3">
                          <div className="text-sm font-bold text-slate-700">Thông số kỹ thuật theo danh mục</div>
                          <p className="mt-1 text-xs font-medium text-slate-500">Các trường này lấy từ form thông số của danh mục cha và áp dụng cho sản phẩm.</p>
                        </div>
                        <div className="space-y-4">
                          {groupedProductSpecFields.map((group) => (
                            <div key={group.title}>
                              <div className="mb-2 text-xs font-bold uppercase text-slate-500">{group.title}</div>
                              <div className="grid gap-3 md:grid-cols-3">
                                {group.fields.map((field) => <Input key={field.key} label={field.label || field.key} value={productForm.specifications[field.key] || ''} required={field.required} onChange={(value) => setProductForm({ ...productForm, specifications: { ...productForm.specifications, [field.key]: value } })} />)}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    <textarea className="min-h-20 rounded-md border border-slate-200 px-3 py-2 text-sm outline-none focus:border-red-500 md:col-span-4" placeholder="Mô tả ngắn" value={productForm.description} onChange={(event) => setProductForm({ ...productForm, description: event.target.value })} />

                    <div className="rounded-md border border-slate-200 bg-white p-3 md:col-span-4">
                      <div className="mb-3 text-sm font-bold text-slate-700">Sản phẩm bán kèm và dịch vụ đi kèm</div>
                      <div className="grid gap-3">
                        <div className="rounded-md border border-slate-200 bg-white p-3">
                          <div className="text-sm font-bold text-slate-800">Sản phẩm mua kèm giảm giá</div>
                          <div className="mt-1 text-xs font-medium text-slate-500">Chọn từ danh sách sản phẩm sau khi lọc. Giảm giá chỉ áp dụng trong số lượng admin đã cấu hình.</div>
                          <div className="mt-3 grid gap-3 md:grid-cols-3">
                            <Select label="Danh mục" value={accessoryCategoryFilter} onChange={setAccessoryCategoryFilter} options={[['', 'Tất cả'], ...categories.map((item) => [item.id, item.parentName ? `${item.parentName} / ${item.name}` : item.name] as [string, string])]} />
                            <Select label="Thương hiệu" value={accessoryBrandFilter} onChange={setAccessoryBrandFilter} options={[['', 'Tất cả'], ...brands.map((item) => [item.id, item.name] as [string, string])]} />
                            <Input label="Tìm sản phẩm" value={accessorySearch} onChange={setAccessorySearch} />
                          </div>
                          <div className="mt-2 rounded-md border border-slate-200">
                            {(accessoryCategoryFilter || accessoryBrandFilter || accessorySearch.trim()) ? (
                              accessoryProductChoices.length > 0 ? (
                                <>
                                  <button type="button" onClick={() => accessoryProductChoices.forEach((item) => addAccessoryOffer(item))} className="flex w-full items-center justify-between gap-3 border-b border-slate-100 bg-slate-50 px-3 py-2 text-left text-xs font-bold text-slate-700">
                                    Chọn tất cả sản phẩm đang lọc
                                    <Plus className="h-4 w-4" />
                                  </button>
                                  {accessoryProductChoices.map((item) => (
                                    <button
                                      key={item.id}
                                      type="button"
                                      onClick={() => addAccessoryOffer(item)}
                                      className="flex w-full items-center justify-between gap-3 border-b border-slate-100 px-3 py-2 text-left last:border-b-0 hover:bg-slate-50"
                                    >
                                      <div className="min-w-0">
                                        <div className="truncate text-sm font-semibold text-slate-800">{item.name}</div>
                                        <div className="text-xs text-slate-500">{item.sku || compactId(item.id)}</div>
                                      </div>
                                      <span className="text-xs font-bold text-red-600">Chọn</span>
                                    </button>
                                  ))}
                                </>
                              ) : (
                                <div className="px-3 py-4 text-sm font-medium text-slate-500">Không có sản phẩm phù hợp với bộ lọc.</div>
                              )
                            ) : (
                              <div className="px-3 py-4 text-sm font-medium text-slate-500">Chọn danh mục, thương hiệu hoặc nhập tên/SKU để hiện danh sách sản phẩm.</div>
                            )}
                          </div>
                          <div className="mt-3 space-y-3">
                            {productForm.accessoryOffers.length === 0 && <div className="rounded-md bg-slate-50 p-3 text-sm text-slate-500">Chưa có sản phẩm mua kèm giảm giá.</div>}
                            {productForm.accessoryOffers.map((item) => (
                              <div key={item.productId} className="rounded-md border border-slate-200 bg-slate-50 p-3">
                                <div className="flex items-start justify-between gap-3">
                                  <div className="flex items-center gap-3">
                                    {item.imageUrl ? <img src={item.imageUrl} alt="" className="h-12 w-12 rounded-md border border-slate-200 object-contain" /> : <div className="flex h-12 w-12 items-center justify-center rounded-md border border-slate-200 bg-white"><Image className="h-4 w-4 text-slate-300" /></div>}
                                    <div>
                                      <div className="text-sm font-bold text-slate-800">{item.productName || 'Sản phẩm mua kèm'}</div>
                                      <div className="text-xs text-slate-500">{item.productSku || compactId(item.productId)}</div>
                                    </div>
                                  </div>
                                  <button type="button" onClick={() => removeAccessoryOffer(item.productId)} className="text-red-600"><Trash2 className="h-4 w-4" /></button>
                                </div>
                                <div className="mt-3 grid gap-3 md:grid-cols-3">
                                  <Select label="Kiểu giảm" value={item.discountType} onChange={(value) => patchAccessoryOffer(item.productId, { discountType: value as 'FIXED' | 'PERCENT' })} options={[['PERCENT', 'Theo %'], ['FIXED', 'Theo tiền']]} />
                                  <Input label={item.discountType === 'PERCENT' ? 'Giảm giá (%)' : 'Giảm giá (VND)'} type="number" value={item.discountValue} onChange={(value) => patchAccessoryOffer(item.productId, { discountValue: Number(value) })} />
                                  <Input label="Số lượng được giảm" type="number" value={item.maxQuantity} onChange={(value) => patchAccessoryOffer(item.productId, { maxQuantity: Math.max(1, Number(value) || 1) })} />
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                        <div className="rounded-md border border-slate-200 bg-white p-3 md:col-span-3">
                          <div className="text-sm font-bold text-slate-800">Dịch vụ đi kèm</div>
                          <div className="mt-1 text-xs font-medium text-slate-500">Chọn từ danh sách dịch vụ admin đã tạo. Với cùng một nhóm bảo hành, hệ thống chỉ cho chọn một thời hạn.</div>
                          <div className="mt-3 grid gap-3 md:grid-cols-3">
                            <Select label="Loại dịch vụ" value={attachedServiceTypeFilter} onChange={setAttachedServiceTypeFilter} options={[['', 'Tất cả'], ['PRODUCT_SERVICE', 'Dịch vụ sản phẩm'], ['SUPPORT_SERVICE', 'Dịch vụ hỗ trợ']]} />
                            <Select label="Nhóm dịch vụ" value={attachedServiceGroupFilter} onChange={setAttachedServiceGroupFilter} options={[['', 'Tất cả'], ...serviceGroupOptions.map((item) => [item, item] as [string, string])]} />
                            <Input label="Tìm dịch vụ" value={attachedServiceSearch} onChange={setAttachedServiceSearch} />
                          </div>
                          <div className="mt-3 rounded-md border border-slate-200">
                            {productAttachedServiceChoices.length === 0 ? (
                              <div className="px-3 py-4 text-sm font-medium text-slate-500">Không có dịch vụ phù hợp hoặc tất cả dịch vụ trong bộ lọc đã được chọn.</div>
                            ) : productAttachedServiceChoices.map((service) => (
                              <button key={service.id} type="button" onClick={() => addAttachedService(service)} className="flex w-full items-center justify-between gap-3 border-b border-slate-100 px-3 py-2 text-left last:border-b-0 hover:bg-slate-50">
                                <div className="min-w-0">
                                  <div className="truncate text-sm font-semibold text-slate-800">{service.name} <span className="text-xs text-slate-400">({service.code})</span></div>
                                  <div className="text-xs text-slate-500">
                                    {service.serviceType === 'PRODUCT_SERVICE' ? 'Dịch vụ sản phẩm' : 'Dịch vụ hỗ trợ'}
                                    {service.attributeGroup ? ` · Nhóm ${service.attributeGroup}` : ''}
                                    {service.durationMonths ? ` · ${service.durationMonths} tháng` : ''}
                                    {service.priceMode === 'PERCENT' ? ` · ${service.percentValue || 0}%` : service.priceMode === 'TIERED_AMOUNT' ? ' · Theo biểu phí' : ` · ${currency.format(Number(service.fixedPrice || service.baseAmount || 0))}`}
                                  </div>
                                </div>
                                <Plus className="h-4 w-4 shrink-0 text-red-600" />
                              </button>
                            ))}
                          </div>
                          <div className="mt-3 space-y-2">
                            {productForm.attachedServices.length === 0 && <div className="rounded-md bg-slate-50 p-3 text-sm text-slate-500">Chưa chọn dịch vụ đi kèm.</div>}
                            {productForm.attachedServices.map((item) => (
                              <div key={item.serviceId} className="grid gap-3 rounded-md border border-slate-200 bg-slate-50 p-3 md:grid-cols-[1fr_180px_40px]">
                                <div>
                                  <div className="text-sm font-bold text-slate-800">{item.name || item.code || 'Dịch vụ'}</div>
                                  <div className="text-xs text-slate-500">
                                    {item.serviceType === 'PRODUCT_SERVICE' ? 'Dịch vụ sản phẩm' : 'Dịch vụ hỗ trợ'}
                                    {item.attributeGroup ? ` · Nhóm ${item.attributeGroup}` : ''}
                                    {item.durationMonths ? ` · ${item.durationMonths} tháng` : ''}
                                    {item.fixedPrice ? ` · ${currency.format(Number(item.fixedPrice || 0))}` : ''}
                                  </div>
                                </div>
                                <Input label="Giá riêng cho sản phẩm" type="number" value={item.overridePrice} onChange={(value) => patchAttachedService(item.serviceId, { overridePrice: value === '' ? '' : Number(value) })} />
                                <button type="button" onClick={() => removeAttachedService(item.serviceId)} className="mt-5 text-red-600"><Trash2 className="h-4 w-4" /></button>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>

                    <div className="rounded-md border border-slate-200 bg-white p-3 md:col-span-4">
                      <div className="mb-3 flex items-center justify-between">
                        <div>
                          <div className="text-sm font-bold text-slate-700">Biến thể sản phẩm</div>
                          <p className="mt-1 text-xs font-medium text-slate-500">Chọn thông số nào của danh mục sẽ dùng để tách biến thể cho riêng sản phẩm này.</p>
                        </div>
                        <button type="button" onClick={addVariant} className="inline-flex h-9 items-center gap-2 rounded-md border border-rose-200 bg-rose-100 px-3 text-sm font-bold text-rose-800 transition hover:bg-rose-200"><Plus className="h-4 w-4" /> Thêm biến thể</button>
                      </div>
                      <div className="mb-3 rounded-md border border-slate-200 bg-slate-50 p-3">
                        <div className="text-xs font-bold uppercase tracking-wide text-slate-400">Chọn cách dùng thông số có thể tạo biến thể</div>
                        {selectedCategory ? (
                          variantFields.length > 0 ? (
                            <div className="mt-3 grid gap-2 md:grid-cols-2">
                              {variantFields.map((field) => {
                                const checked = productForm.variantSpecKeys.includes(field.key);
                                return (
                                  <label key={field.key} className={`flex items-center justify-between gap-3 rounded-md border px-3 py-2 transition ${checked ? 'border-red-200 bg-red-50' : 'border-slate-200 bg-white'}`}>
                                    <div>
                                      <div className="text-sm font-bold text-slate-800">{field.label || field.key}</div>
                                      <div className="mt-0.5 text-xs font-medium text-slate-500">{checked ? 'Đang dùng làm biến thể' : 'Dùng chung trong thông số sản phẩm'}</div>
                                    </div>
                                    <div className="flex items-center gap-2 text-xs font-bold text-slate-600">
                                      <span>{checked ? 'Dùng biến thể' : 'Dùng chung'}</span>
                                      <input type="checkbox" checked={checked} onChange={(event) => toggleVariantSpecField(field.key, event.target.checked)} className="h-4 w-4 accent-red-600" />
                                    </div>
                                  </label>
                                );
                              })}
                            </div>
                          ) : (
                            <p className="mt-2 text-sm font-medium text-amber-700">Danh mục này chưa có thông số nào được đánh dấu dùng cho biến thể.</p>
                          )
                        ) : (
                          <p className="mt-2 text-sm font-medium text-slate-500">Chọn danh mục cha để hệ thống nạp danh sách thông số cho biến thể.</p>
                        )}
                      </div>
                      <div className="space-y-3">
                        {productForm.variants.map((variant, index) => (
                          <div key={index} className="rounded-md bg-slate-50 p-3">
                            <div className="mb-3 flex items-center justify-between">
                              <span className="text-sm font-bold text-slate-700">Biến thể {index + 1}</span>
                              <button type="button" onClick={() => setProductForm({ ...productForm, variants: productForm.variants.filter((_, i) => i !== index) })} className="text-red-600"><Trash2 className="h-4 w-4" /></button>
                            </div>
                            <div className="grid gap-3 md:grid-cols-4">
                              <Input label="SKU biến thể" value={variant.sku || buildVariantSku(productForm.name, variant.colorName, index)} onChange={(value) => patchVariant(index, { sku: value })} />
                              <Input label="Màu sắc chính" value={variant.colorName} onChange={(value) => patchVariant(index, { colorName: value, sku: variant.sku || buildVariantSku(productForm.name, value, index) })} />
                              <Input label="Mã màu" value={variant.colorCode} type="color" onChange={(value) => patchVariant(index, { colorCode: value })} />
                              <Input label="Giá gốc riêng" value={variant.price} type="number" onChange={(value) => patchVariant(index, { price: Number(value) })} />
                              <Input label="Giá bán riêng" value={variant.salePrice} type="number" onChange={(value) => patchVariant(index, { salePrice: Number(value) })} />
                              <FileInput label="Ảnh riêng biến thể" accept="image/*" onFiles={async (files) => patchVariant(index, { imageUrl: (await uploadFiles(files, 'products'))[0] || variant.imageUrl })} />
                              {variant.imageUrl && <MediaPreview title={`Xem trước ảnh màu ${variant.colorName || index + 1}`} items={[variant.imageUrl]} onRemove={() => patchVariant(index, { imageUrl: '' })} />}
                              {groupedActiveVariantFields.map((group) => (
                                <div key={group.title} className="md:col-span-4">
                                  <div className="mb-2 text-xs font-bold uppercase text-slate-500">{group.title}</div>
                                  <div className="grid gap-3 md:grid-cols-4">
                                    {group.fields.map((field) => <Input key={field.key} label={`${field.label || field.key} (biến thể)`} value={variant.specs[field.key] || ''} required={field.required} onChange={(value) => patchVariant(index, { specs: { ...variant.specs, [field.key]: value } })} />)}
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        ))}
                        {productForm.variants.length === 0 && <div className="rounded-md bg-slate-50 p-4 text-sm text-slate-500">Chưa có biến thể. Sản phẩm vẫn dùng giá và ảnh chung.</div>}
                      </div>
                    </div>

                    <SubmitButtons editing={Boolean(editingProductId)} onCancel={resetProductForm} />
                  </form>
                </CollapsibleSection>

                {selectedProductIds.length > 0 && (
                  <div className="mb-3 flex flex-wrap items-center justify-between gap-2 rounded-md border border-sky-100 bg-sky-50 px-3 py-2 text-sm font-semibold text-sky-800">
                    <span>Đã chọn {selectedProductIds.length} sản phẩm</span>
                    <button type="button" onClick={bulkApproveProducts} className="inline-flex h-9 items-center gap-2 rounded-md bg-sky-700 px-3 text-xs font-bold text-white"><CheckCircle2 className="h-4 w-4" />Duyệt hàng loạt</button>
                  </div>
                )}

                <AdminTable headers={['Chọn', 'Ảnh', 'Sản phẩm', 'Danh mục', 'Thương hiệu', 'Giá', 'Kho', 'Biến thể', 'Trạng thái', 'Thao tác']}>
                  {filteredProducts.map((product) => (
                    <tr key={product.id}>
                      <td className="px-4 py-3"><input type="checkbox" checked={selectedProductIds.includes(product.id)} onChange={(event) => setSelectedProductIds((ids) => event.target.checked ? [...new Set([...ids, product.id])] : ids.filter((id) => id !== product.id))} className="h-4 w-4 rounded border-slate-300 text-red-600 focus:ring-red-500" /></td>
                      <td className="px-4 py-3">{product.imageUrl ? <img src={product.imageUrl} alt="" className="h-11 w-11 rounded-md object-contain" /> : <Image className="h-6 w-6 text-slate-300" />}</td>
                      <td className="px-4 py-3"><div className="font-semibold text-slate-900">{product.name}</div><div className="text-xs text-slate-500">{product.sku || compactId(product.id)}</div></td>
                      <td className="px-4 py-3">{product.categoryName || product.category || '-'}</td>
                      <td className="px-4 py-3">{product.brand || '-'}</td>
                      <td className="px-4 py-3 font-semibold text-red-600">{currency.format(Number(product.discountPrice || product.price || 0))}</td>
                      <td className="px-4 py-3">
                        <div className="font-semibold">{product.stock ?? 0}</div>
                        <AdminBadge tone={Number(product.stock || 0) > 0 ? 'green' : 'yellow'}>{Number(product.stock || 0) > 0 ? 'Còn hàng' : 'Hết hàng'}</AdminBadge>
                      </td>
                      <td className="px-4 py-3">{product.variants?.length || 0}</td>
                      <td className="px-4 py-3"><AdminBadge tone={product.status === 'ACTIVE' ? 'green' : product.status === 'PENDING' ? 'blue' : product.status === 'DRAFT' ? 'yellow' : 'slate'}>{productStatusLabel[product.status] || product.status || 'Nháp'}</AdminBadge></td>
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap items-center gap-2">
                          <RowActions onEdit={() => editProduct(product)} onDelete={() => confirmDelete(product.name, () => apiDb.adminDeactivateProduct(product.id))} onRestore={product.status !== 'ACTIVE' && product.status !== 'ARCHIVED' ? () => reactivateProduct(product) : undefined} />
                          <button type="button" onClick={() => setPreviewProduct(product)} className="rounded-md border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-bold text-slate-700"><Eye className="inline h-3.5 w-3.5" /> Preview</button>
                          <button type="button" onClick={() => duplicateProduct(product)} className="rounded-md border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-bold text-slate-700"><Copy className="inline h-3.5 w-3.5" /> Sao chép</button>
                          {product.status === 'DRAFT' && <button type="button" onClick={() => submitProduct(product)} className="rounded-md border border-sky-200 bg-sky-50 px-2.5 py-1.5 text-xs font-bold text-sky-700">Gửi duyệt</button>}
                          {product.status === 'PENDING' && <button type="button" onClick={() => approveProduct(product)} className="rounded-md border border-emerald-200 bg-emerald-50 px-2.5 py-1.5 text-xs font-bold text-emerald-700">Duyệt</button>}
                          {(product.status === 'DRAFT' || product.status === 'INACTIVE') && <button type="button" onClick={() => archiveProduct(product)} className="rounded-md border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-xs font-bold text-slate-700">Lưu trữ</button>}
                        </div>
                      </td>
                    </tr>
                  ))}
                </AdminTable>
              </AdminPanel>
            )}

            {tab === 'categories' && (
              <AdminPanel title="Quản lý danh mục và form thông số" action={<SearchBox value={query} onChange={setQuery} placeholder="Tìm danh mục, slug, danh mục cha" />}>
                <CollapsibleSection title={editingCategoryId ? 'Đang chỉnh sửa danh mục' : 'Thêm danh mục và form thông số'} description="Mở khi cần tạo danh mục cha, danh mục con hoặc cấu hình form thông số kỹ thuật cho danh mục cha." defaultOpen={false} forceOpen={Boolean(editingCategoryId)} forceOpenKey={editingCategoryId} onClose={resetCategoryForm}>
                  <form onSubmit={handleCategorySubmit} className="mb-5 grid gap-3 rounded-lg bg-slate-50 p-4 md:grid-cols-5">
                    <Input label="Tên danh mục" value={categoryForm.name} required onChange={(value) => setCategoryForm({ ...categoryForm, name: value, slug: categoryForm.slug || slugifyText(value) })} />
                    <Input label="Slug" value={categoryForm.slug} onBlur={checkCategorySlug} onChange={(value) => {
                      setCategorySlugStatus('idle');
                      setCategoryForm({ ...categoryForm, slug: slugifyText(value) });
                    }} />
                    <Input label="Icon" value={categoryForm.icon} onChange={(value) => setCategoryForm({ ...categoryForm, icon: value })} />
                    <Select label="Danh mục cha" value={categoryForm.parentId} onChange={(value) => setCategoryForm({ ...categoryForm, parentId: value })} options={[['', 'Là danh mục cha'], ...rootCategories.map((item) => [item.id, item.name] as [string, string])]} />
                    <Input label="Thứ tự" type="number" value={categoryForm.order} onChange={(value) => setCategoryForm({ ...categoryForm, order: Number(value) })} />
                    <Select label="Trạng thái" value={categoryForm.status} onChange={(value) => setCategoryForm({ ...categoryForm, status: value, isActive: ['ACTIVE', 'APPROVED'].includes(value) })} options={categoryStatusOptions} />
                    {categoryParentMigrationHint && <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm font-semibold text-amber-800 md:col-span-5">Danh mục này đang có sản phẩm. Nếu đổi danh mục cha, hệ thống sẽ tạo tác vụ nền để chuẩn hóa lại thông số sản phẩm theo cây mới.</div>}
                    {(categorySlugTaken || categorySlugStatus !== 'idle') && (
                      <div className={`rounded-md border px-3 py-2 text-sm font-semibold md:col-span-5 ${categorySlugStatus === 'available' ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : 'border-red-200 bg-red-50 text-red-700'}`}>
                        {categorySlugStatus === 'checking' ? 'Đang kiểm tra slug...' : categorySlugStatus === 'available' ? 'Slug có thể sử dụng.' : 'Slug này đã tồn tại. Hãy đổi slug trước khi lưu.'}
                      </div>
                    )}
                    <FileInput label="Icon/hình danh mục" accept="image/*" onFiles={async (files) => setCategoryForm({ ...categoryForm, iconUrl: (await uploadFiles(files, 'categories'))[0] || categoryForm.iconUrl })} />
                    <FileInput label="Banner danh mục" accept="image/*" onFiles={async (files) => setCategoryForm({ ...categoryForm, bannerUrl: (await uploadFiles(files, 'categories'))[0] || categoryForm.bannerUrl })} />
                    {(categoryForm.iconUrl || categoryForm.bannerUrl) && (
                      <div className="grid gap-3 md:col-span-3 md:grid-cols-2">
                        {categoryForm.iconUrl && <img src={categoryForm.iconUrl} alt="" className="h-24 w-full rounded-md border border-slate-200 object-cover" />}
                        {categoryForm.bannerUrl && <img src={categoryForm.bannerUrl} alt="" className="h-24 w-full rounded-md border border-slate-200 object-cover" />}
                      </div>
                    )}
                    <div className="rounded-md border border-slate-200 bg-white p-3 md:col-span-5">
                      <div className="mb-3 text-sm font-bold text-slate-700">SEO Metadata</div>
                      <div className="grid gap-3 md:grid-cols-3">
                        <Input label="Meta Title" value={categoryForm.seoTitle} onChange={(value) => setCategoryForm({ ...categoryForm, seoTitle: value })} />
                        <Input label="Keywords" value={categoryForm.seoKeywords} onChange={(value) => setCategoryForm({ ...categoryForm, seoKeywords: value })} />
                        <textarea className="min-h-16 rounded-md border border-slate-200 px-3 py-2 text-sm outline-none focus:border-red-500 md:col-span-3" placeholder="Meta Description" value={categoryForm.seoDescription} onChange={(event) => setCategoryForm({ ...categoryForm, seoDescription: event.target.value })} />
                      </div>
                    </div>
                    <div className="rounded-md border border-slate-200 bg-white p-3 md:col-span-5">
                      <div className="mb-3 text-sm font-bold text-slate-700">Tồn kho và bảo hành mặc định</div>
                      <div className="grid gap-3 md:grid-cols-5">
                        <Checkbox label="Theo IMEI của cha" checked={Boolean(categoryForm.inventoryPolicy.inheritImeiPolicy)} onChange={(checked) => setCategoryForm({ ...categoryForm, inventoryPolicy: { ...categoryForm.inventoryPolicy, inheritImeiPolicy: checked } })} />
                        <Checkbox label="Quản lý IMEI" checked={Boolean(categoryForm.inventoryPolicy.trackImei)} disabled={Boolean(categoryForm.inventoryPolicy.inheritImeiPolicy && categoryForm.parentId)} onChange={(checked) => setCategoryForm({ ...categoryForm, inventoryPolicy: { ...categoryForm.inventoryPolicy, trackImei: checked } })} />
                        <Checkbox label="Theo bảo hành của cha" checked={Boolean(categoryForm.warrantyPolicy.inheritWarrantyPolicy)} onChange={(checked) => setCategoryForm({ ...categoryForm, warrantyPolicy: { ...categoryForm.warrantyPolicy, inheritWarrantyPolicy: checked } })} />
                        <Checkbox label="Có bảo hành" checked={Boolean(categoryForm.warrantyPolicy.hasWarranty)} disabled={Boolean(categoryForm.warrantyPolicy.inheritWarrantyPolicy && categoryForm.parentId)} onChange={(checked) => setCategoryForm({ ...categoryForm, warrantyPolicy: { ...categoryForm.warrantyPolicy, hasWarranty: checked } })} />
                        <Input label="Tháng bảo hành" type="number" value={Number(categoryForm.warrantyPolicy.warrantyMonths || 0)} onChange={(value) => setCategoryForm({ ...categoryForm, warrantyPolicy: { ...categoryForm.warrantyPolicy, warrantyMonths: Math.max(0, Number(value)) } })} />
                        <Checkbox label="Có 1 đổi 1" checked={Boolean(categoryForm.warrantyPolicy.allowOneForOne)} disabled={Boolean(categoryForm.warrantyPolicy.inheritWarrantyPolicy && categoryForm.parentId)} onChange={(checked) => setCategoryForm({ ...categoryForm, warrantyPolicy: { ...categoryForm.warrantyPolicy, allowOneForOne: checked } })} />
                        <Input label="Ngày 1 đổi 1" type="number" value={Number(categoryForm.warrantyPolicy.oneForOneDays || 0)} onChange={(value) => setCategoryForm({ ...categoryForm, warrantyPolicy: { ...categoryForm.warrantyPolicy, oneForOneDays: Math.max(0, Number(value)) } })} />
                      </div>
                    </div>
                    <div className="rounded-md border border-slate-200 bg-white p-3 md:col-span-5">
                      <div className="mb-3 flex items-center justify-between">
                        <div>
                          <span className="text-sm font-bold text-slate-700">Form thông số kỹ thuật</span>
                          <p className="mt-1 text-xs font-medium text-slate-500">{categoryForm.parentId ? 'Danh mục con kế thừa thông số chung từ danh mục cha và có thể thêm thông số đặc thù riêng.' : 'Danh mục cha lưu thông số chung. Danh mục con có thể cộng thêm thông số riêng nếu cần.'}</p>
                        </div>
                        <button type="button" onClick={addSpecField} className="inline-flex h-9 items-center gap-2 rounded-md border border-rose-200 bg-rose-100 px-3 text-sm font-bold text-rose-800 transition hover:bg-rose-200"><Plus className="h-4 w-4" /> Thêm trường</button>
                      </div>
                      <div className="space-y-2">
                        {categoryForm.specFields.map((field, index) => (
                          <div key={index} className="grid gap-2 rounded-md bg-slate-50 p-2 md:grid-cols-[1fr_1fr_1fr_130px_90px_100px_110px_130px_40px]">
                            <Input label="Mã trường" value={field.key} onChange={(value) => patchSpecField(index, { key: value })} />
                            <Input label="Tên hiển thị" value={field.label} onChange={(value) => patchSpecField(index, { label: value })} />
                            <Input label="Nhóm cha" value={field.group || ''} onChange={(value) => patchSpecField(index, { group: value })} />
                            <Select label="Kiểu" value={field.type} onChange={(value) => patchSpecField(index, { type: value })} options={[['text', 'Chữ'], ['number', 'Số'], ['select', 'Lựa chọn'], ['color', 'Màu']]} />
                            <Checkbox label="Bắt buộc" checked={field.required} onChange={(checked) => patchSpecField(index, { required: checked })} />
                            <Checkbox label="Dùng cho biến thể" checked={field.variant} onChange={(checked) => patchSpecField(index, { variant: checked })} />
                            <Checkbox label="Dùng làm lọc" checked={Boolean(field.isFilterable)} onChange={(checked) => patchSpecField(index, { isFilterable: checked })} />
                            <Select label="Kiểu lọc" value={field.filterType || (field.type === 'number' ? 'range' : 'checkbox')} onChange={(value) => patchSpecField(index, { filterType: value })} options={[['checkbox', 'Checkbox'], ['range', 'Khoảng'], ['select', 'Danh sách']]} />
                            <button type="button" onClick={() => setCategoryForm({ ...categoryForm, specFields: categoryForm.specFields.filter((_, i) => i !== index) })} className="mt-5 text-red-600"><Trash2 className="h-4 w-4" /></button>
                          </div>
                        ))}
                        {categoryForm.specFields.length === 0 && <div className="rounded-md border border-dashed border-slate-200 bg-slate-50 p-4 text-sm font-medium text-slate-500">Chưa có trường thông số. Hãy thêm các trường như màn hình, chip, pin, camera, chất liệu...</div>}
                      </div>
                    </div>
                    <div className="rounded-md border border-slate-200 bg-white p-3 md:col-span-5">
                      <div className="mb-3 flex items-center justify-between">
                        <div>
                          <span className="text-sm font-bold text-slate-700">Bộ lọc hiển thị ngoài trang khách hàng</span>
                          <p className="mt-1 text-xs font-medium text-slate-500">Chọn các thuộc tính sẽ xuất hiện ở sidebar/bộ lọc của trang danh mục.</p>
                        </div>
                        <button type="button" onClick={addCategoryFilter} className="inline-flex h-9 items-center gap-2 rounded-md border border-rose-200 bg-rose-100 px-3 text-sm font-bold text-rose-800 transition hover:bg-rose-200"><Plus className="h-4 w-4" /> Thêm bộ lọc</button>
                      </div>
                      <div className="space-y-2">
                        {derivedCategoryFilters.map((field, index) => {
                          const manualIndex = categoryForm.filterConfig.findIndex((item) => item.key === field.key && item.source !== 'attribute');
                          const isAttributeFilter = field.source === 'attribute';
                          return (
                            <div key={`${field.source || 'manual'}-${field.key}-${index}`} className="grid gap-2 rounded-md bg-slate-50 p-2 md:grid-cols-[1fr_1fr_150px_110px_110px_40px]">
                              <Input label="Mã lọc" value={field.key} disabled={isAttributeFilter} onChange={(value) => manualIndex >= 0 && patchCategoryFilter(manualIndex, { key: value })} />
                              <Input label="Tên hiển thị" value={field.label} disabled={isAttributeFilter} onChange={(value) => manualIndex >= 0 && patchCategoryFilter(manualIndex, { label: value })} />
                              <Select label="Kiểu lọc" value={field.type} disabled={isAttributeFilter} onChange={(value) => manualIndex >= 0 && patchCategoryFilter(manualIndex, { type: value })} options={[['checkbox', 'Checkbox'], ['range', 'Khoảng giá/số'], ['select', 'Danh sách']]} />
                              <Checkbox label="Hiển thị" checked={field.enabled} disabled={isAttributeFilter} onChange={(checked) => manualIndex >= 0 && patchCategoryFilter(manualIndex, { enabled: checked })} />
                              <span className="mt-5 rounded-md bg-slate-200 px-2 py-1 text-center text-xs font-bold text-slate-700">{isAttributeFilter ? 'Từ thông số' : 'Thủ công'}</span>
                              <button type="button" disabled={isAttributeFilter} onClick={() => manualIndex >= 0 && setCategoryForm({ ...categoryForm, filterConfig: categoryForm.filterConfig.filter((_, i) => i !== manualIndex) })} className="mt-5 text-red-600 disabled:text-slate-300"><Trash2 className="h-4 w-4" /></button>
                            </div>
                          );
                        })}
                        {derivedCategoryFilters.length === 0 && <div className="rounded-md border border-dashed border-slate-200 bg-slate-50 p-4 text-sm font-medium text-slate-500">Chưa có bộ lọc. Đánh dấu "Dùng làm lọc" ở thông số kỹ thuật hoặc thêm bộ lọc thủ công.</div>}
                      </div>
                    </div>
                    <SubmitButtons editing={Boolean(editingCategoryId)} onCancel={resetCategoryForm} />
                  </form>
                </CollapsibleSection>
                <div className="mb-5 rounded-lg border border-slate-200 bg-slate-50 p-4">
                  <div className="mb-3 flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
                    <div>
                      <h3 className="text-sm font-bold text-slate-900">Quản lý form thông số theo danh mục cha</h3>
                      <p className="text-xs font-medium text-slate-500">Chỉ danh mục cha có form thông số; danh mục con kế thừa khi tạo sản phẩm.</p>
                    </div>
                    <AdminBadge tone="blue">{filteredRootCategories.length}/{rootCategories.length} danh mục cha</AdminBadge>
                  </div>
                  <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">
                    {filteredRootCategories.map((category) => (
                      <button key={category.id} type="button" onClick={() => editCategory(category)} className="flex items-center justify-between rounded-md border border-slate-200 bg-white px-3 py-3 text-left transition hover:border-red-200 hover:bg-red-50">
                        <div className="min-w-0">
                          <div className="truncate text-sm font-bold text-slate-900">{category.name}</div>
                          <div className="mt-1 text-xs font-medium text-slate-500">{category.slug || category.id}</div>
                        </div>
                        <span className="ml-3 rounded-md bg-slate-100 px-2 py-1 text-xs font-bold text-slate-700">{category.specFields?.length || 0} trường</span>
                      </button>
                    ))}
                  </div>
                </div>
                <div className="mb-5 grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
                  <div className="rounded-lg border border-slate-200 bg-white p-4">
                    <div className="mb-3 flex items-center justify-between">
                      <div>
                        <h3 className="text-sm font-bold text-slate-900">Tình trạng vận hành danh mục</h3>
                        <p className="text-xs font-medium text-slate-500">Theo dõi cache, job di trú và các cảnh báo tự phục hồi của cây danh mục.</p>
                      </div>
                      <button type="button" onClick={() => refreshCategoryWorkspace()} className="inline-flex h-9 items-center gap-2 rounded-md border border-slate-200 px-3 text-sm font-bold text-slate-700">
                        <RefreshCw className={`h-4 w-4 ${categoryPanelBusy ? 'animate-spin' : ''}`} />
                        Làm mới
                      </button>
                    </div>
                    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                      <MetricCard label="Tỉ lệ cache hit" value={`${Math.round(Number(categoryMetrics.cacheHitRatio ?? 0) * 100)}%`} tone="emerald" />
                      <MetricCard label="P99 đọc danh mục" value={`${Number(categoryMetrics.latencyP99Ms ?? 0)} ms`} tone="sky" />
                      <MetricCard label="Job đang chạy" value={String(categoryMetrics.migrationRunningJobs ?? 0)} tone="amber" />
                      <MetricCard label="Job stale đã cứu" value={String(categoryMetrics.migrationWatchdogRecoveredJobs ?? 0)} tone="slate" />
                    </div>
                  </div>
                  <div className="rounded-lg border border-slate-200 bg-white p-4">
                    <div className="mb-3">
                      <h3 className="text-sm font-bold text-slate-900">Nhật ký danh mục đang chọn</h3>
                      <p className="text-xs font-medium text-slate-500">{editingCategory ? `Đang xem: ${editingCategory.name}` : 'Chọn một danh mục để xem lịch sử thay đổi và job nền.'}</p>
                    </div>
                    {editingCategory ? (
                      <div className="space-y-4">
                        <div>
                          <div className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-500">Migration jobs</div>
                          <div className="space-y-2">
                            {categoryMigrationJobs.length === 0 && <div className="rounded-md border border-dashed border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-500">Chưa có job di trú nào cho danh mục này.</div>}
                            {categoryMigrationJobs.slice(0, 4).map((job) => (
                              <div key={job.id} className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2">
                                <div className="flex items-center justify-between gap-3">
                                  <span className="font-mono text-xs text-slate-500">{compactId(job.id)}</span>
                                  <AdminBadge tone={job.status === 'COMPLETED' ? 'green' : job.status === 'FAILED' ? 'red' : 'amber'}>{job.status}</AdminBadge>
                                </div>
                                <div className="mt-1 text-xs text-slate-600">Đã xử lý {job.processedProducts || 0}/{job.totalProducts || 0} sản phẩm</div>
                                {job.errorMessage && <div className="mt-1 text-xs font-medium text-red-600">{job.errorMessage}</div>}
                              </div>
                            ))}
                          </div>
                        </div>
                        <div>
                          <div className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-500">Audit gần nhất</div>
                          <div className="space-y-2">
                            {categoryAuditLogs.length === 0 && <div className="rounded-md border border-dashed border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-500">Chưa có lịch sử thay đổi gần đây.</div>}
                            {categoryAuditLogs.slice(0, 5).map((log) => (
                              <div key={log.id} className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2">
                                <div className="flex items-center justify-between gap-3">
                                  <div className="text-sm font-semibold text-slate-800">{String(log.actionType || '').replaceAll('_', ' ')}</div>
                                  <div className="text-xs text-slate-500">{new Date(log.createdAt).toLocaleString('vi-VN')}</div>
                                </div>
                                <div className="mt-1 text-xs text-slate-500">Actor: {compactId(log.actorId)}</div>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="rounded-md border border-dashed border-slate-200 bg-slate-50 px-3 py-6 text-sm text-slate-500">Danh sách lịch sử và job nền sẽ hiện ở đây khi bạn mở một danh mục để chỉnh sửa.</div>
                    )}
                  </div>
                </div>
                <AdminTable headers={['Sắp xếp', 'Ảnh', 'Tên', 'Slug', 'Loại', 'Danh mục cha', 'Thông số / lọc', 'Trạng thái', 'Thao tác']}>
                  {filteredCategoryTree.flatMap((category) => [category, ...(category.children || [])]).map((category) => (
                    <CategoryTableRow
                      key={category.id}
                      category={category}
                      level={category.parentId ? 1 : 0}
                      onEdit={() => editCategory(category)}
                      onDelete={() => confirmDelete(category.name, () => apiDb.adminDeleteCategory(category.id))}
                      onRestore={category.isActive ? undefined : () => reactivateCategory(category)}
                      onReorder={reorderCategory}
                    />
                  ))}
                </AdminTable>
              </AdminPanel>
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
                  <Select label="Loại dịch vụ" value={serviceForm.serviceType} onChange={(value) => setServiceForm({ ...serviceForm, serviceType: value, attributeGroup: value === 'PRODUCT_SERVICE' && !serviceForm.attributeGroup ? 'WARRANTY' : serviceForm.attributeGroup })} options={[['PRODUCT_SERVICE', 'Dịch vụ sản phẩm'], ['SUPPORT_SERVICE', 'Dịch vụ hỗ trợ']]} />
                  <Select label="Nhóm dịch vụ" value={serviceForm.attributeGroup} onChange={(value) => setServiceForm({ ...serviceForm, attributeGroup: value })} options={[['', 'Chọn nhóm'], ...serviceAttributeGroupOptions]} />
                  <Select label="Thời hạn" value={String(serviceForm.durationMonths || 0)} onChange={(value) => setServiceForm({ ...serviceForm, durationMonths: Number(value) })} options={warrantyDurationOptions} />
                  <Select label="Cách tính giá" value={serviceForm.priceMode} onChange={(value) => setServiceForm({ ...serviceForm, priceMode: value })} options={[['FIXED', 'Giá cố định'], ['PERCENT', 'Theo % sản phẩm'], ['TIERED_AMOUNT', 'Theo định mức']]} />
                  <Input label="Giá cố định" type="number" value={serviceForm.fixedPrice} onChange={(value) => setServiceForm({ ...serviceForm, fixedPrice: Number(value) })} />
                  <Input label="Phần trăm" type="number" value={serviceForm.percentValue} onChange={(value) => setServiceForm({ ...serviceForm, percentValue: Number(value) })} />
                  <Input label="Định mức" type="number" value={serviceForm.baseAmount} onChange={(value) => setServiceForm({ ...serviceForm, baseAmount: Number(value) })} />
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
              <AdminPanel title="Quản lý đơn hàng" action={<SearchBox value={query} onChange={setQuery} placeholder="Tìm mã đơn, khách hàng, trạng thái" />}>
                <div className="mb-4 grid gap-3 md:grid-cols-4">
                  <MetricCard label="Chờ xử lý" value={String(orders.filter((item) => item.status === 'PENDING').length)} tone="amber" />
                  <MetricCard label="Đang giao" value={String(orders.filter((item) => item.status === 'SHIPPED').length)} tone="sky" />
                  <MetricCard label="Đã hủy" value={String(cancelledOrders)} tone="slate" />
                  <MetricCard label="Đã hoàn tiền" value={String(refundedOrders)} tone="emerald" />
                </div>
                <AdminTable headers={['Mã đơn', 'Khách hàng', 'Tổng tiền', 'Thanh toán', 'Trạng thái', 'Theo dõi', 'Thao tác']}>
                  {filteredOrders.map((order) => (
                    <tr key={order.id}>
                      <td className="px-4 py-3">
                        <div className="font-mono text-xs">{order.orderCode || compactId(order.id)}</div>
                        <div className="mt-1 text-xs text-slate-500">{order.createdAt ? new Date(order.createdAt).toLocaleString('vi-VN') : '-'}</div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="font-semibold text-slate-900">{order.recipientName || order.userId || order.user_id || 'Khách lẻ'}</div>
                        <div className="mt-1 text-xs text-slate-500">{order.recipientPhone || 'Không có số điện thoại'}</div>
                      </td>
                      <td className="px-4 py-3 font-semibold text-red-600">{currency.format(Number(order.totalAmount || order.total_amount || 0))}</td>
                      <td className="px-4 py-3">
                        <div>{order.paymentMethod || order.payment_method || '-'}</div>
                        <div className="mt-1 text-xs text-slate-500">{order.paymentStatus || order.payment_status || '-'}</div>
                      </td>
                      <td className="px-4 py-3"><AdminBadge tone={order.status === 'COMPLETED' ? 'green' : order.status === 'CANCELLED' ? 'red' : 'yellow'}>{statusLabel[order.status] || order.status}</AdminBadge></td>
                      <td className="px-4 py-3 text-xs">
                        <div>{order.shippingProvider || 'Chưa gán đơn vị vận chuyển'}</div>
                        <div className="mt-1 font-mono text-slate-500">{order.trackingCode || 'Chưa có mã vận đơn'}</div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <button type="button" onClick={() => openOrderPanel(order.id)} className="inline-flex h-8 items-center justify-center gap-2 rounded-md border border-slate-200 px-3 text-sm font-semibold text-slate-700 transition hover:border-red-200 hover:bg-red-50 hover:text-red-700">
                            <Eye className="h-4 w-4" /> Chi tiết
                          </button>
                          <select className="h-9 rounded-md border border-slate-200 px-2 text-sm outline-none" value={order.status} onChange={(event) => updateOrderStatus(order.id, event.target.value)}>
                            {(orderTransitionMap[order.status] || orderStatusOptions.map(([value]) => value)).map((value) => <option key={value} value={value}>{statusLabel[value] || value}</option>)}
                          </select>
                        </div>
                      </td>
                    </tr>
                  ))}
                </AdminTable>
                {orderPanelOpen && (
                  <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-950/55 px-4 py-6 backdrop-blur-sm">
                    <div className="w-full max-w-5xl overflow-hidden rounded-lg bg-white shadow-2xl">
                      <div className="flex items-start justify-between gap-4 border-b border-slate-200 px-5 py-4">
                        <div>
                          <h3 className="text-lg font-bold text-slate-950">Chi tiết đơn hàng</h3>
                          <p className="mt-1 text-sm text-slate-500">{selectedOrder?.orderCode || compactId(selectedOrder?.id)} · {selectedOrder ? (statusLabel[selectedOrder.status] || selectedOrder.status) : ''}</p>
                        </div>
                        <button type="button" onClick={() => setOrderPanelOpen(false)} className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-slate-200 text-slate-600 transition hover:bg-slate-50"><X className="h-4 w-4" /></button>
                      </div>
                      <div className="max-h-[calc(100vh-120px)] overflow-y-auto p-5">
                        {orderPanelBusy || !selectedOrder ? <EmptyState text="Đang tải chi tiết đơn hàng..." /> : (
                          <div className="space-y-5">
                            <div className="grid gap-4 md:grid-cols-4">
                              <MetricCard label="Tổng tiền" value={currency.format(Number(selectedOrder.totalAmount || 0))} tone="amber" />
                              <MetricCard label="Thanh toán" value={selectedOrder.paymentStatus || '-'} tone="sky" />
                              <MetricCard label="Điểm cộng" value={String(selectedOrder.pointsEarned || 0)} tone="emerald" />
                              <MetricCard label="Điểm dùng" value={String(selectedOrder.pointsUsed || 0)} tone="slate" />
                            </div>
                            <div className="grid gap-5 lg:grid-cols-[1.05fr_0.95fr]">
                              <div className="space-y-5">
                                <AdminPanel title="Thông tin nhận hàng" action={<Truck className="h-5 w-5 text-red-600" />}>
                                  <div className="grid gap-3 md:grid-cols-2">
                                    <Input label="Người nhận" value={selectedOrder.recipientName || ''} onChange={() => { }} disabled />
                                    <Input label="Số điện thoại" value={selectedOrder.recipientPhone || ''} onChange={() => { }} disabled />
                                    <div className="md:col-span-2"><label className="block"><span className="mb-1.5 block text-xs font-bold text-slate-500">Địa chỉ</span><textarea value={selectedOrder.shippingAddress || ''} readOnly className="min-h-[92px] w-full rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700 outline-none" /></label></div>
                                  </div>
                                </AdminPanel>
                                <AdminPanel title="Sản phẩm trong đơn" action={<ShoppingBag className="h-5 w-5 text-red-600" />}>
                                  <AdminTable headers={['Sản phẩm', 'SL', 'Đơn giá', 'Thành tiền']}>
                                    {(selectedOrder.items || []).map((item: any) => (
                                      <tr key={item.id}>
                                        <td className="px-4 py-3 font-semibold text-slate-900">{item.productName}</td>
                                        <td className="px-4 py-3">{item.quantity}</td>
                                        <td className="px-4 py-3">{currency.format(Number(item.price || 0))}</td>
                                        <td className="px-4 py-3 font-semibold text-red-600">{currency.format(Number(item.totalPrice || 0))}</td>
                                      </tr>
                                    ))}
                                  </AdminTable>
                                </AdminPanel>
                              </div>
                              <div className="space-y-5">
                                <AdminPanel title="Điều phối xử lý" action={<ClipboardList className="h-5 w-5 text-red-600" />}>
                                  <div className="grid gap-3 md:grid-cols-2">
                                    <Select label="Trạng thái" value={orderDraft.status} onChange={(value) => setOrderDraft({ ...orderDraft, status: value })} options={(orderTransitionMap[selectedOrder.status] || [selectedOrder.status]).map((value) => [value, statusLabel[value] || value]) as [string, string][]} />
                                    <Input label="Nhân viên xử lý" value={orderDraft.assignedStaffName} onChange={(value) => setOrderDraft({ ...orderDraft, assignedStaffName: value })} />
                                    <Input label="Đơn vị vận chuyển" value={orderDraft.shippingProvider} onChange={(value) => setOrderDraft({ ...orderDraft, shippingProvider: value })} />
                                    <Input label="Mã vận đơn" value={orderDraft.trackingCode} onChange={(value) => setOrderDraft({ ...orderDraft, trackingCode: value })} />
                                    <div className="md:col-span-2"><label className="block"><span className="mb-1.5 block text-xs font-bold text-slate-500">Ghi chú nội bộ</span><textarea value={orderDraft.internalNote} onChange={(event) => setOrderDraft({ ...orderDraft, internalNote: event.target.value })} className="min-h-[110px] w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 outline-none transition focus:border-red-500 focus:ring-2 focus:ring-red-100" /></label></div>
                                    <div className="md:col-span-2"><label className="block"><span className="mb-1.5 block text-xs font-bold text-slate-500">Lý do hủy</span><textarea value={orderDraft.cancellationReason} onChange={(event) => setOrderDraft({ ...orderDraft, cancellationReason: event.target.value })} placeholder="Bắt buộc khi chuyển sang trạng thái đã hủy" className="min-h-[92px] w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 outline-none transition focus:border-red-500 focus:ring-2 focus:ring-red-100" /></label></div>
                                    <div className="md:col-span-2"><Checkbox label="Đánh dấu hoàn tiền cho giao dịch online" checked={orderDraft.refundPayment} onChange={(checked) => setOrderDraft({ ...orderDraft, refundPayment: checked })} disabled={selectedOrder.paymentMethod === 'COD'} /></div>
                                  </div>
                                  <div className="mt-4 flex flex-wrap gap-2">
                                    <button type="button" onClick={() => saveOrderDraft()} disabled={orderSaving} className="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-red-600 px-4 text-sm font-bold text-white shadow-sm transition hover:bg-red-700 disabled:opacity-50"><CheckCircle2 className="h-4 w-4" />Lưu cập nhật</button>
                                    <button type="button" onClick={() => printOrderDocument(selectedOrder, 'invoice')} className="inline-flex h-10 items-center justify-center gap-2 rounded-md border border-slate-200 px-4 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"><Download className="h-4 w-4" />In hóa đơn</button>
                                    <button type="button" onClick={() => printOrderDocument(selectedOrder, 'delivery')} className="inline-flex h-10 items-center justify-center gap-2 rounded-md border border-slate-200 px-4 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"><FileText className="h-4 w-4" />In phiếu giao hàng</button>
                                  </div>
                                </AdminPanel>
                                <AdminPanel title="Dấu mốc đơn hàng" action={<Activity className="h-5 w-5 text-red-600" />}>
                                  <div className="space-y-2 text-sm text-slate-600">
                                    <div>Tạo đơn: {selectedOrder.createdAt ? new Date(selectedOrder.createdAt).toLocaleString('vi-VN') : '-'}</div>
                                    <div>Giao vận: {selectedOrder.shippedAt ? new Date(selectedOrder.shippedAt).toLocaleString('vi-VN') : 'Chưa giao vận'}</div>
                                    <div>Hoàn tất: {selectedOrder.completedAt ? new Date(selectedOrder.completedAt).toLocaleString('vi-VN') : 'Chưa hoàn tất'}</div>
                                    <div>Hủy đơn: {selectedOrder.cancelledAt ? new Date(selectedOrder.cancelledAt).toLocaleString('vi-VN') : 'Không có'}</div>
                                    <div>Hoàn tiền: {selectedOrder.refundedAt ? new Date(selectedOrder.refundedAt).toLocaleString('vi-VN') : 'Chưa hoàn tiền'}</div>
                                  </div>
                                </AdminPanel>
                                <AdminPanel title="Lịch sử thao tác" action={<ScrollText className="h-5 w-5 text-red-600" />}>
                                  <div className="space-y-3">
                                    {(selectedOrder.historyLogs || []).length === 0 && <EmptyState text="Chưa có lịch sử thao tác." />}
                                    {(selectedOrder.historyLogs || []).map((log: any) => (
                                      <div key={log.id} className="rounded-md border border-slate-200 bg-slate-50 p-3">
                                        <div className="flex items-center justify-between gap-3">
                                          <div className="text-sm font-bold text-slate-900">
                                            {(statusLabel[log.oldStatus] || log.oldStatus || 'Khởi tạo')} → {statusLabel[log.newStatus] || log.newStatus}
                                          </div>
                                          <div className="text-xs text-slate-500">{log.createdAt ? new Date(log.createdAt).toLocaleString('vi-VN') : '-'}</div>
                                        </div>
                                        <div className="mt-1 text-xs font-semibold text-slate-500">Thực hiện bởi: {log.changedBy || 'Hệ thống'}</div>
                                        {log.note && <div className="mt-2 text-sm text-slate-600">{log.note}</div>}
                                      </div>
                                    ))}
                                  </div>
                                </AdminPanel>
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </AdminPanel>
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
                        {canManageCustomerAccess ? (
                          <select value={item.role || 'CUSTOMER'} onChange={(event) => updateUserAccess(item, { role: event.target.value })} className="h-9 rounded-md border border-slate-200 bg-white px-2 text-xs font-semibold outline-none focus:border-red-500">
                            <option value="CUSTOMER">Customer</option>
                            <option value="STAFF_ADMIN">Staff Admin</option>
                            <option value="SUPER_ADMIN">Super Admin</option>
                          </select>
                        ) : (
                          item.role === 'SUPER_ADMIN' ? 'Super Admin' : item.role === 'STAFF_ADMIN' ? 'Staff Admin' : item.tier
                        )}
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
              <AdminPanel title="Quản lý tồn kho" action={<div className="flex items-center gap-2"><SearchBox value={query} onChange={setQuery} placeholder="Tìm sản phẩm, SKU, trạng thái kho" /><button type="button" onClick={() => void exportInventorySnapshot()} className="inline-flex h-10 items-center gap-2 rounded-md border border-slate-200 bg-white px-3 text-sm font-bold text-slate-700 transition hover:bg-slate-50"><Download className="h-4 w-4" /> Xuất Excel</button></div>}>
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
              <AdminPanel title="Quản lý video và nội dung" action={<SearchBox value={query} onChange={setQuery} placeholder="Tìm tiêu đề, loại, mô tả" />}>
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
                    <Select label="Loại nội dung" value={contentForm.contentType} onChange={(value) => setContentForm({ ...contentForm, contentType: value })} options={contentTypeOptions} />
                    <Input label="Thứ tự hiển thị" type="number" value={contentForm.sortOrder} onChange={(value) => setContentForm({ ...contentForm, sortOrder: Number(value || 0) })} />
                    <Checkbox label="Đang hiển thị" checked={contentForm.isActive} onChange={(checked) => setContentForm({ ...contentForm, isActive: checked })} />
                    <div className="md:col-span-4">
                      <label className="block">
                        <span className="mb-1.5 block text-xs font-bold text-slate-500">Mô tả ngắn</span>
                        <textarea className="min-h-20 w-full rounded-md border border-slate-200 px-3 py-2 text-sm outline-none focus:border-red-500" value={contentForm.description} onChange={(event) => setContentForm({ ...contentForm, description: event.target.value })} />
                      </label>
                    </div>
                    <FileInput label="Upload video" accept="video/*" onFiles={async (files) => setContentForm({ ...contentForm, videoUrl: (await uploadFiles(files, 'content'))[0] || contentForm.videoUrl })} />
                    <FileInput label="Upload thumbnail" accept="image/*" onFiles={async (files) => setContentForm({ ...contentForm, thumbnailUrl: (await uploadFiles(files, 'content'))[0] || contentForm.thumbnailUrl })} />
                    <FileInput label="Upload banner" accept="image/*" onFiles={async (files) => setContentForm({ ...contentForm, bannerImageUrl: (await uploadFiles(files, 'content'))[0] || contentForm.bannerImageUrl })} />
                    <Input label="CTA URL" value={contentForm.ctaUrl} onChange={(value) => setContentForm({ ...contentForm, ctaUrl: value })} />
                    <Input label="CTA label" value={contentForm.ctaLabel} onChange={(value) => setContentForm({ ...contentForm, ctaLabel: value })} />
                    <Input label="Sản phẩm liên kết" value={contentForm.productIds} onChange={(value) => setContentForm({ ...contentForm, productIds: value })} />
                    <Input label="Danh mục liên kết" value={contentForm.categoryIds} onChange={(value) => setContentForm({ ...contentForm, categoryIds: value })} />
                    <Input label="Lịch đăng" type="datetime-local" value={contentForm.scheduledAt} onChange={(value) => setContentForm({ ...contentForm, scheduledAt: value })} />
                    <Input label="Ngày public" type="datetime-local" value={contentForm.publishedAt} onChange={(value) => setContentForm({ ...contentForm, publishedAt: value })} />
                    <Input label="Lượt thích" type="number" value={contentForm.likeCount} onChange={(value) => setContentForm({ ...contentForm, likeCount: Number(value || 0) })} />
                    <Input label="Lượt xem" type="number" value={contentForm.viewCount} onChange={(value) => setContentForm({ ...contentForm, viewCount: Number(value || 0) })} />
                    <div className="md:col-span-4">
                      <label className="block">
                        <span className="mb-1.5 block text-xs font-bold text-slate-500">Nội dung dài / landing content</span>
                        <textarea className="min-h-32 w-full rounded-md border border-slate-200 px-3 py-2 text-sm outline-none focus:border-red-500" value={contentForm.contentBody} onChange={(event) => setContentForm({ ...contentForm, contentBody: event.target.value })} />
                      </label>
                    </div>
                    <div className="md:col-span-4">
                      <label className="block">
                        <span className="mb-1.5 block text-xs font-bold text-slate-500">Bình luận video</span>
                        <textarea className="min-h-28 w-full rounded-md border border-slate-200 px-3 py-2 text-sm outline-none focus:border-red-500" placeholder="Mỗi dòng theo mẫu: Tên khách: Nội dung bình luận" value={contentForm.commentsText} onChange={(event) => setContentForm({ ...contentForm, commentsText: event.target.value })} />
                      </label>
                    </div>
                    <div className="md:col-span-4 rounded-md border border-dashed border-slate-200 bg-white p-3 text-xs text-slate-500">
                      Gợi ý: danh sách sản phẩm/danh mục bên dưới dùng ID, có thể nhập nhiều mục bằng dấu phẩy hoặc xuống dòng.
                    </div>
                    <SubmitButtons editing={Boolean(editingContentId)} onCancel={resetContentForm} />
                  </form>
                </CollapsibleSection>}
                <AdminTable headers={['Tiêu đề', 'Loại', 'Liên kết', 'Lịch & thứ tự', 'Tương tác', 'Trạng thái', 'Thao tác']}>
                  {filteredContentItems.length === 0 ? (
                    <tr><td colSpan={7} className="px-4 py-8 text-center text-sm font-medium text-slate-500">Không tìm thấy nội dung phù hợp.</td></tr>
                  ) : filteredContentItems.map((item) => (
                    <tr key={item.id}>
                      <td className="px-4 py-3">
                        <div className="font-semibold text-slate-900">{item.title}</div>
                        <div className="mt-1 text-xs text-slate-500">{item.description || '-'}</div>
                      </td>
                      <td className="px-4 py-3">{item.contentType || (item.videoUrl ? 'VIDEO' : 'MARKETING_PAGE')}</td>
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
                            <button type="button" onClick={() => void confirmDelete(item.title, () => apiDb.adminDeleteContent(item.id))} className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-slate-200 text-slate-600 transition hover:border-red-200 hover:bg-red-50 hover:text-red-700">
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
              <AdminPanel title="Ma trận phân quyền theo vai trò" action={<RefreshCw className="h-5 w-5 text-red-600" />}>
                <div className="overflow-x-auto">
                  <table className="min-w-full text-left text-sm">
                    <thead>
                      <tr className="border-b border-slate-200 bg-slate-50 text-xs font-bold uppercase tracking-wide text-slate-500">
                        <th className="sticky left-0 z-10 bg-slate-50 px-4 py-3">Quyền</th>
                        {roles.filter((role) => role.code !== 'CUSTOMER').map((role) => (
                          <th key={role.id} className="px-4 py-3">{role.name || role.code}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {permissions.map((permission) => (
                        <tr key={permission.code} className="hover:bg-slate-50/70">
                          <td className="sticky left-0 z-10 bg-white px-4 py-3">
                            <div className="font-semibold text-slate-900">{permission.code}</div>
                            <div className="text-xs text-slate-500">{permission.description || permission.module}</div>
                          </td>
                          {roles.filter((role) => role.code !== 'CUSTOMER').map((role) => {
                            const checked = (rolePermissionMap[role.id] || []).includes(permission.code);
                            const locked = role.code === 'SUPER_ADMIN';
                            return (
                              <td key={`${role.id}-${permission.code}`} className="px-4 py-3">
                                <input
                                  type="checkbox"
                                  checked={checked || locked}
                                  disabled={locked}
                                  onChange={(event) => toggleRolePermission(role.id, permission.code, event.target.checked)}
                                  className="h-4 w-4 rounded border-slate-300 text-red-600 focus:ring-red-500"
                                />
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="mt-5 rounded-lg border border-slate-200 bg-slate-50 p-4">
                  <div className="mb-3 text-sm font-bold text-slate-900">Nhật ký đổi quyền gần đây</div>
                  <div className="space-y-2">
                    {auditLogs
                      .filter((log) => ['admin_user_access_updated', 'admin_role_permissions_updated'].includes(log.eventType))
                      .slice(0, 8)
                      .map((log) => (
                        <div key={log.id} className="rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700">
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <span className="font-semibold text-slate-900">{log.eventType === 'admin_user_access_updated' ? 'Đổi vai trò / trạng thái user' : 'Cập nhật ma trận quyền'}</span>
                            <span className="text-xs text-slate-500">{log.createdAt ? new Date(log.createdAt).toLocaleString('vi-VN') : '-'}</span>
                          </div>
                          <div className="mt-1 text-xs text-slate-600">
                            {log.eventType === 'admin_user_access_updated'
                              ? `User: ${log.metadata?.targetUserId || '-'} | Vai trò mới: ${log.metadata?.after?.role || '-'} | Trạng thái mới: ${log.metadata?.after?.status || '-'}`
                              : `Role: ${log.metadata?.roleCode || '-'} | Số user bị ảnh hưởng: ${log.metadata?.affectedUsers || 0}`}
                          </div>
                        </div>
                      ))}
                  </div>
                </div>
              </AdminPanel>
            )}
            {customerDetailOpen && (
              <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-950/55 px-4 py-6 backdrop-blur-sm">
                <div className="w-full max-w-6xl overflow-hidden rounded-lg bg-white shadow-2xl">
                  <div className="sticky top-0 z-10 flex items-start justify-between gap-4 border-b border-slate-200 bg-white px-5 py-4">
                    <div>
                      <h3 className="text-lg font-bold text-slate-950">Hồ sơ khách hàng</h3>
                      <p className="mt-1 text-sm text-slate-500">{selectedCustomer?.fullName || selectedCustomer?.email || 'Đang tải dữ liệu khách hàng'}</p>
                    </div>
                    <button type="button" onClick={() => setCustomerDetailOpen(false)} className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-slate-200 text-slate-600 transition hover:bg-slate-50 hover:text-slate-950">
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                  <div className="max-h-[calc(100vh-150px)] overflow-y-auto p-5">
                    {customerDetailBusy || !selectedCustomer ? (
                      <EmptyState text="Đang tải hồ sơ khách hàng..." />
                    ) : (
                      <div className="space-y-5">
                        <div className="flex flex-wrap gap-2">
                          {[
                            ['summary', 'Tổng quan'],
                            ['orders', 'Đơn hàng'],
                            ['loyalty', 'Điểm thưởng'],
                            ['notes', 'Ghi chú CSKH'],
                            ['audit', 'Nhật ký'],
                          ].map(([sectionId, label]) => (
                            <button
                              key={sectionId}
                              type="button"
                              onClick={() => sectionId === 'summary' ? setCustomerActiveSection('summary') : void loadCustomerSection(sectionId as 'orders' | 'loyalty' | 'notes' | 'audit')}
                              className={`rounded-md px-3 py-2 text-sm font-bold transition ${customerActiveSection === sectionId ? 'bg-slate-950 text-white' : 'border border-slate-200 bg-white text-slate-700 hover:bg-slate-50'}`}
                            >
                              {label}
                            </button>
                          ))}
                        </div>
                        <div className="grid gap-3 md:grid-cols-4">
                          <MetricCard label="Tổng chi tiêu" value={currency.format(Number(selectedCustomer.totalSpent || 0))} tone="sky" />
                          <MetricCard label="Điểm hiện có" value={String(selectedCustomer.points || 0)} tone="amber" />
                          <MetricCard label="Số đơn" value={String(selectedCustomer.orderCount || 0)} tone="emerald" />
                          <MetricCard label="Voucher đã giữ" value={String(selectedCustomer.voucherCount || 0)} />
                        </div>
                        <div className="grid gap-5 lg:grid-cols-[1.1fr_0.9fr]">
                          <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                            <div className="text-sm font-bold text-slate-900">Thông tin chung</div>
                            <div className="mt-3 grid gap-3 md:grid-cols-2">
                              <div><div className="text-xs font-bold text-slate-500">Email</div><div className="mt-1 text-sm text-slate-900">{selectedCustomer.email}</div></div>
                              <div><div className="text-xs font-bold text-slate-500">Điện thoại</div><div className="mt-1 text-sm text-slate-900">{selectedCustomer.phone || '-'}</div></div>
                              <div><div className="text-xs font-bold text-slate-500">Vai trò</div><div className="mt-1 text-sm text-slate-900">{selectedCustomer.role || '-'}</div></div>
                              <div><div className="text-xs font-bold text-slate-500">Hạng thành viên</div><div className="mt-1 text-sm text-slate-900">{selectedCustomer.tier || '-'}</div></div>
                              <div><div className="text-xs font-bold text-slate-500">Trạng thái</div><div className="mt-1 text-sm text-slate-900">{selectedCustomer.status || '-'}</div></div>
                              <div><div className="text-xs font-bold text-slate-500">Ngày tạo</div><div className="mt-1 text-sm text-slate-900">{selectedCustomer.createdAt ? new Date(selectedCustomer.createdAt).toLocaleString('vi-VN') : '-'}</div></div>
                            </div>
                          </div>
                          <div className="rounded-lg border border-slate-200 bg-white p-4">
                            <div className="text-sm font-bold text-slate-900">Tag khách hàng</div>
                            <p className="mt-1 text-xs text-slate-500">Nhập tag cách nhau bởi dấu phẩy để phục vụ CSKH và phân nhóm thủ công.</p>
                            <textarea value={customerTagDraft} onChange={(event) => setCustomerTagDraft(event.target.value)} className="mt-3 min-h-24 w-full rounded-md border border-slate-200 px-3 py-2 text-sm outline-none focus:border-red-500" />
                            {canManageCustomerProfile && (
                              <button type="button" onClick={() => void saveCustomerTags()} className="mt-3 rounded-md bg-slate-950 px-4 py-2 text-sm font-bold text-white transition hover:bg-slate-800">Lưu tag</button>
                            )}
                          </div>
                        </div>
                        {usePermission('customer:loyalty_adjust') && (
                          <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
                            <div className="text-sm font-bold text-amber-900">Cộng / trừ điểm thủ công</div>
                            <div className="mt-3 grid gap-3 md:grid-cols-[160px_1fr_auto]">
                              <Input label="Số điểm" value={customerPointDelta} onChange={setCustomerPointDelta} type="number" />
                              <Input label="Lý do" value={customerPointReason} onChange={setCustomerPointReason} />
                              <div className="flex items-end">
                                <button type="button" onClick={() => void adjustCustomerPoints()} className="inline-flex h-10 items-center justify-center rounded-md bg-amber-600 px-4 text-sm font-bold text-white transition hover:bg-amber-700">Cập nhật điểm</button>
                              </div>
                            </div>
                          </div>
                        )}
                        {usePermission('customer:issue_voucher') && (
                          <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4">
                            <div className="text-sm font-bold text-emerald-900">Gửi voucher riêng</div>
                            <div className="mt-3 grid gap-3 md:grid-cols-[1fr_1fr_auto]">
                              <Select label="Voucher" value={customerVoucherId} onChange={setCustomerVoucherId} options={[['', 'Chọn voucher'], ...vouchers.filter((voucher) => voucher.status === 'ACTIVE').map((voucher) => [voucher.id, `${voucher.code} - ${voucher.discountType === 'PERCENT' ? `${voucher.discountValue}%` : currency.format(Number(voucher.discountValue || 0))}`] as [string, string])]} />
                              <Input label="Ghi chú nội bộ" value={customerVoucherNote} onChange={setCustomerVoucherNote} />
                              <div className="flex items-end">
                                <button type="button" onClick={() => void issueCustomerVoucher()} className="inline-flex h-10 items-center justify-center rounded-md bg-emerald-600 px-4 text-sm font-bold text-white transition hover:bg-emerald-700">Gá»­i voucher</button>
                              </div>
                            </div>
                          </div>
                        )}
                        {customerActiveSection === 'summary' && (
                          <div className="grid gap-5 xl:grid-cols-2">
                            <AdminPanel title="Lịch sử đơn hàng">
                              <AdminTable headers={['Mã đơn', 'Trạng thái', 'Thanh toán', 'Tổng tiền', 'Ngày tạo']}>
                                {customerOrders.length === 0 ? <tr><td colSpan={5} className="px-4 py-6 text-center text-sm text-slate-500">Chưa có đơn hàng.</td></tr> : customerOrders.map((order) => (
                                  <tr key={order.id}>
                                    <td className="px-4 py-3 font-mono text-xs">{order.orderCode || compactId(order.id)}</td>
                                    <td className="px-4 py-3">{order.status}</td>
                                    <td className="px-4 py-3">{order.paymentStatus || order.paymentMethod || '-'}</td>
                                    <td className="px-4 py-3">{currency.format(Number(order.totalAmount || 0))}</td>
                                    <td className="px-4 py-3">{order.createdAt ? new Date(order.createdAt).toLocaleString('vi-VN') : '-'}</td>
                                  </tr>
                                ))}
                              </AdminTable>
                            </AdminPanel>
                            <AdminPanel title="Lịch sử điểm thưởng">
                              <AdminTable headers={['Loại', 'Điểm', 'Số dư trước/sau', 'Lý do', 'Thời gian']}>
                                {customerLoyaltyHistory.length === 0 ? <tr><td colSpan={5} className="px-4 py-6 text-center text-sm text-slate-500">Chưa có lịch sử điểm.</td></tr> : customerLoyaltyHistory.map((item) => (
                                  <tr key={item.id}>
                                    <td className="px-4 py-3">{item.type}</td>
                                    <td className="px-4 py-3 font-semibold">{item.metadata?.delta ?? item.points}</td>
                                    <td className="px-4 py-3">{item.balanceBefore} / {item.balanceAfter}</td>
                                    <td className="px-4 py-3 text-sm text-slate-600">{item.reason}</td>
                                    <td className="px-4 py-3">{item.createdAt ? new Date(item.createdAt).toLocaleString('vi-VN') : '-'}</td>
                                  </tr>
                                ))}
                              </AdminTable>
                            </AdminPanel>
                          </div>
                        )}
                        {customerActiveSection === 'orders' && (
                          <AdminPanel title="Lịch sử đơn hàng">
                            <AdminTable headers={['Mã đơn', 'Trạng thái', 'Thanh toán', 'Tổng tiền', 'Ngày tạo']}>
                              {customerOrders.length === 0 ? <tr><td colSpan={5} className="px-4 py-6 text-center text-sm text-slate-500">Chưa có đơn hàng.</td></tr> : customerOrders.map((order) => (
                                <tr key={order.id}>
                                  <td className="px-4 py-3 font-mono text-xs">{order.orderCode || compactId(order.id)}</td>
                                  <td className="px-4 py-3">{order.status}</td>
                                  <td className="px-4 py-3">{order.paymentStatus || order.paymentMethod || '-'}</td>
                                  <td className="px-4 py-3">{currency.format(Number(order.totalAmount || 0))}</td>
                                  <td className="px-4 py-3">{order.createdAt ? new Date(order.createdAt).toLocaleString('vi-VN') : '-'}</td>
                                </tr>
                              ))}
                            </AdminTable>
                          </AdminPanel>
                        )}
                        {customerActiveSection === 'loyalty' && (
                          <AdminPanel title="Lịch sử điểm thưởng">
                            <AdminTable headers={['Loại', 'Điểm', 'Số dư trước/sau', 'Lý do', 'Thời gian']}>
                              {customerLoyaltyHistory.length === 0 ? <tr><td colSpan={5} className="px-4 py-6 text-center text-sm text-slate-500">Chưa có lịch sử điểm.</td></tr> : customerLoyaltyHistory.map((item) => (
                                <tr key={item.id}>
                                  <td className="px-4 py-3">{item.type}</td>
                                  <td className="px-4 py-3 font-semibold">{item.metadata?.delta ?? item.points}</td>
                                  <td className="px-4 py-3">{item.balanceBefore} / {item.balanceAfter}</td>
                                  <td className="px-4 py-3 text-sm text-slate-600">{item.reason}</td>
                                  <td className="px-4 py-3">{item.createdAt ? new Date(item.createdAt).toLocaleString('vi-VN') : '-'}</td>
                                </tr>
                              ))}
                            </AdminTable>
                          </AdminPanel>
                        )}
                        {(customerActiveSection === 'notes' || customerActiveSection === 'audit' || customerActiveSection === 'summary') && (
                          <div className="grid gap-5 xl:grid-cols-2">
                            <AdminPanel title="Ghi chú CSKH" action={canManageCustomerProfile ? <button type="button" onClick={() => void addCustomerNote()} className="rounded-md bg-slate-950 px-4 py-2 text-sm font-bold text-white transition hover:bg-slate-800">Thêm ghi chú</button> : undefined}>
                              {canManageCustomerProfile && <textarea value={customerNoteDraft} onChange={(event) => setCustomerNoteDraft(event.target.value)} placeholder="Ghi lại ngữ cảnh CSKH, lưu ý xử lý, cam kết hỗ trợ..." className="mb-4 min-h-24 w-full rounded-md border border-slate-200 px-3 py-2 text-sm outline-none focus:border-red-500" />}
                              <div className="space-y-3">
                                {customerNotes.length === 0 ? <EmptyState text="Chưa có ghi chú CSKH." /> : customerNotes.map((note) => (
                                  <div key={note.id} className="rounded-md border border-slate-200 bg-slate-50 px-3 py-3">
                                    <div className="flex flex-wrap items-center justify-between gap-2">
                                      <span className="text-xs font-bold uppercase tracking-wide text-slate-500">{note.authorName || note.authorId || 'Admin'}</span>
                                      <span className="text-xs text-slate-500">{note.createdAt ? new Date(note.createdAt).toLocaleString('vi-VN') : '-'}</span>
                                    </div>
                                    <div className="mt-2 text-sm leading-6 text-slate-700">{note.content}</div>
                                  </div>
                                ))}
                              </div>
                            </AdminPanel>
                            <AdminPanel title="Nhật ký thay đổi quyền và tác động">
                              <div className="space-y-3">
                                {customerAuditLogs.length === 0 ? <EmptyState text="Chưa có nhật ký liên quan khách hàng này." /> : customerAuditLogs.map((log) => (
                                  <div key={log.id} className="rounded-md border border-slate-200 bg-slate-50 px-3 py-3 text-sm text-slate-700">
                                    <div className="flex flex-wrap items-center justify-between gap-2">
                                      <span className="font-semibold text-slate-900">{log.eventType}</span>
                                      <span className="text-xs text-slate-500">{log.createdAt ? new Date(log.createdAt).toLocaleString('vi-VN') : '-'}</span>
                                    </div>
                                    <div className="mt-2 text-xs text-slate-600">{JSON.stringify(log.metadata || {})}</div>
                                  </div>
                                ))}
                              </div>
                            </AdminPanel>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </div>
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

function AdminTopBar({ onRefresh, query, setQuery, sidebarOpen, searchPlaceholder, onToggleSidebar }: { onRefresh: () => void; query: string; setQuery: (value: string) => void; sidebarOpen: boolean; searchPlaceholder: string; onToggleSidebar: () => void }) {
  const navigate = useNavigate();
  const [profileOpen, setProfileOpen] = useState(false);

  async function handleSignOut() {
    await signOut();
    navigate('/admin/login');
  }

  return (
    <header className="sticky top-0 z-40 mb-5 rounded-[24px] border border-rose-200/80 bg-rose-50/95 shadow-[0_18px_45px_rgba(127,29,29,0.08)] backdrop-blur">
      <div className="flex flex-col gap-3 p-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex min-w-0 items-center gap-3">
          <button type="button" onClick={onToggleSidebar} title={sidebarOpen ? 'Ẩn menu quản trị' : 'Hiện menu quản trị'} className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl border border-slate-200 text-slate-700 transition hover:bg-slate-50 hover:text-slate-950">
            <Menu className="h-5 w-5" />
          </button>
          <div className="min-w-0">
            <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.18em] text-indigo-600"><ShieldCheck className="h-4 w-4" /> Admin Console</div>
            <h1 className="truncate text-xl font-bold text-slate-950 sm:text-2xl">Quản lý cửa hàng</h1>
            <p className="mt-1 text-sm text-slate-500">Bảng điều khiển sáng hơn, ưu tiên dữ liệu và thao tác quan trọng.</p>
          </div>
        </div>

        <div className="flex min-w-0 flex-1 flex-col gap-2 sm:flex-row sm:items-center lg:justify-end">
          <div className="min-w-0 flex-1">
            <SearchBox value={query} onChange={setQuery} placeholder={searchPlaceholder} />
          </div>
          <Link to="/" className="inline-flex h-11 items-center justify-center gap-2 rounded-2xl bg-red-600 px-4 text-sm font-semibold text-white shadow-sm transition hover:bg-red-700">
            <Home className="h-4 w-4" />
            <span>Trang chủ</span>
          </Link>
          <button type="button" onClick={onRefresh} title="Làm mới dữ liệu" className="inline-flex h-11 items-center justify-center gap-2 rounded-2xl border border-slate-200 bg-white px-4 text-sm font-semibold text-slate-700 transition hover:bg-slate-50">
            <RefreshCw className="h-4 w-4" />
            <span className="hidden xl:inline">Làm mới</span>
          </button>
          <button type="button" title="Thông báo" className="relative inline-flex h-11 w-11 items-center justify-center rounded-2xl border border-slate-200 text-slate-700 transition hover:bg-slate-50">
            <Bell className="h-5 w-5" />
            <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-red-600"></span>
          </button>
          <div className="relative">
            <button type="button" title="Hồ sơ admin" onClick={() => setProfileOpen((value) => !value)} className="inline-flex h-11 items-center gap-2 rounded-2xl border border-slate-200 bg-slate-50 px-4 text-sm font-semibold text-slate-700 transition hover:bg-white">
              <UserCircle className="h-5 w-5" />
              <span>Admin</span>
            </button>
            {profileOpen && (
              <div className="absolute right-0 top-12 z-50 w-56 overflow-hidden rounded-lg border border-slate-200 bg-white p-1 shadow-xl">
                <Link to="/change-password" onClick={() => setProfileOpen(false)} className="flex items-center gap-2 rounded-md px-3 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 hover:text-slate-950">
                  <KeyRound className="h-4 w-4" />
                  Đổi mật khẩu
                </Link>
                <button type="button" onClick={handleSignOut} className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm font-semibold text-red-600 transition hover:bg-red-50">
                  <LogOut className="h-4 w-4" />
                  Đăng xuất
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}

function HeaderPanel({ onRefresh }: { onRefresh: () => void }) {
  return (
    <div className="mb-5 overflow-hidden rounded-lg border border-slate-200/80 bg-white shadow-[0_18px_45px_rgba(15,23,42,0.08)]">
      <div className="flex flex-col gap-4 border-b border-slate-100 p-5 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.2em] text-red-600"><ShieldCheck className="h-4 w-4" /> Admin Console</div>
          <h1 className="mt-2 font-display text-3xl font-bold text-slate-950">Quản lý cửa hàng</h1>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-500">Điều phối danh mục, thương hiệu, đơn hàng, voucher, nội dung và tồn kho trong một bảng quản trị gọn, rõ, dễ thao tác.</p>
        </div>
        <button onClick={onRefresh} className="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-slate-950 px-4 text-sm font-semibold text-white shadow-sm transition hover:bg-slate-800"><RefreshCw className="h-4 w-4" />Làm mới dữ liệu</button>
      </div>
      <div className="grid gap-3 bg-slate-50/70 px-5 py-3 text-xs font-semibold text-slate-500 sm:grid-cols-3">
        <span>Chuẩn dữ liệu: sản phẩm, biến thể, media</span>
        <span>Vận hành: đơn hàng, tồn kho, voucher</span>
        <span>Bảo mật: chỉ tài khoản admin truy cập</span>
      </div>
    </div>
  );
}

type StatTone = 'emerald' | 'red' | 'sky' | 'amber';

function StatCard({ label, value, caption, icon: Icon, tone }: { label: string; value: string | number; caption: string; icon: React.ElementType; tone: StatTone }) {
  const tones: Record<StatTone, { shell: string; badge: string; trend: string }> = {
    emerald: { shell: 'from-emerald-50 to-white', badge: 'bg-emerald-100 text-emerald-700 ring-emerald-200', trend: 'bg-emerald-100 text-emerald-700' },
    red: { shell: 'from-rose-50 to-white', badge: 'bg-rose-100 text-rose-700 ring-rose-200', trend: 'bg-rose-100 text-rose-700' },
    sky: { shell: 'from-sky-50 to-white', badge: 'bg-sky-100 text-sky-700 ring-sky-200', trend: 'bg-sky-100 text-sky-700' },
    amber: { shell: 'from-amber-50 to-white', badge: 'bg-amber-100 text-amber-700 ring-amber-200', trend: 'bg-amber-100 text-amber-700' },
  };
  const currentTone = tones[tone];
  return (
    <div className={`rounded-[24px] border border-slate-200/80 bg-gradient-to-br ${currentTone.shell} p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <span className="text-sm font-semibold text-slate-500">{label}</span>
          <div className="mt-2 text-3xl font-bold tracking-tight text-slate-950">{value}</div>
          <span className={`mt-3 inline-flex items-center rounded-full px-2.5 py-1 text-[11px] font-bold ${currentTone.trend}`}>
            <TrendingUp className="mr-1 h-3.5 w-3.5" />
            Theo dõi sát
          </span>
        </div>
        <span className={`inline-flex h-12 w-12 items-center justify-center rounded-2xl ring-1 ${currentTone.badge}`}><Icon className="h-6 w-6" /></span>
      </div>
      <p className="mt-3 text-xs font-medium leading-5 text-slate-500">{caption}</p>
    </div>
  );
}

function MiniMetric({ label, value, helper }: { label: string; value: string | number; helper: string }) {
  return (
    <div className="rounded-2xl border border-slate-100 bg-slate-50/90 p-5">
      <div className="text-xs font-bold uppercase tracking-wide text-slate-400">{label}</div>
      <div className="mt-2 text-3xl font-bold text-slate-950">{value}</div>
      <div className="mt-1 text-xs font-medium text-slate-500">{helper}</div>
    </div>
  );
}

function MetricCard({ label, value, tone = 'slate' }: { label: string; value: string; tone?: 'emerald' | 'sky' | 'amber' | 'slate' }) {
  const tones = {
    emerald: 'border-emerald-100 bg-emerald-50 text-emerald-900',
    sky: 'border-sky-100 bg-sky-50 text-sky-900',
    amber: 'border-amber-100 bg-amber-50 text-amber-900',
    slate: 'border-slate-200 bg-slate-50 text-slate-900',
  };
  return (
    <div className={`rounded-md border p-4 ${tones[tone]}`}>
      <div className="text-xs font-bold uppercase tracking-wide opacity-70">{label}</div>
      <div className="mt-2 text-2xl font-bold">{value}</div>
    </div>
  );
}

function AlertRow({ label, value, detail }: { label: string; value: number; detail: string }) {
  return (
    <div className={`rounded-md border px-3 py-2 ${value > 0 ? 'border-amber-200 bg-amber-50' : 'border-emerald-100 bg-emerald-50'}`}>
      <div className="flex items-center justify-between gap-3">
        <span className={`text-sm font-bold ${value > 0 ? 'text-amber-900' : 'text-emerald-800'}`}>{label}</span>
        <span className={`font-mono text-sm font-black ${value > 0 ? 'text-amber-700' : 'text-emerald-700'}`}>{value}</span>
      </div>
      <div className={`mt-1 text-xs font-semibold ${value > 0 ? 'text-amber-700' : 'text-emerald-700'}`}>{detail}</div>
    </div>
  );
}

function EmptyState({ text }: { text: string }) {
  return <div className="rounded-md border border-dashed border-slate-200 bg-slate-50 px-3 py-6 text-center text-sm font-semibold text-slate-500">{text}</div>;
}

function CollapsibleSection({ title, description, children, defaultOpen = false, forceOpen = false, forceOpenKey, onClose }: { title: string; description?: string; children: React.ReactNode; defaultOpen?: boolean; forceOpen?: boolean; forceOpenKey?: string | null; onClose?: () => void }) {
  const [open, setOpen] = useState(defaultOpen);

  useEffect(() => {
    if (forceOpen) setOpen(true);
  }, [forceOpen, forceOpenKey]);

  const closePopup = () => {
    setOpen(false);
    onClose?.();
  };

  return (
    <div className="mb-5 rounded-lg border border-slate-200 bg-slate-50 p-3">
      <div className="flex w-full flex-col gap-3 rounded-md bg-white px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <div className="text-sm font-bold text-slate-950">{title}</div>
          {description && <div className="mt-1 text-xs font-medium leading-5 text-slate-500">{description}</div>}
        </div>
        <button type="button" onClick={() => setOpen(true)} className="inline-flex shrink-0 items-center justify-center gap-2 rounded-xl bg-rose-200 px-4 py-2 text-sm font-bold text-slate-800 shadow-sm shadow-rose-50 transition hover:bg-rose-300">
          <Plus className="h-4 w-4" /> Thêm
        </button>
      </div>
      {open && (
        <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-950/55 px-4 py-6 backdrop-blur-sm">
          <div className="w-full max-w-6xl overflow-hidden rounded-lg bg-white shadow-2xl">
            <div className="sticky top-0 z-10 flex items-start justify-between gap-4 border-b border-slate-200 bg-white px-5 py-4">
              <div>
                <h3 className="text-lg font-bold text-slate-950">{title}</h3>
                {description && <p className="mt-1 text-sm text-slate-500">{description}</p>}
              </div>
              <button type="button" onClick={closePopup} title="Đóng popup" className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-slate-200 text-slate-600 transition hover:bg-slate-50 hover:text-slate-950">
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="max-h-[calc(100vh-150px)] overflow-y-auto p-5">{children}</div>
          </div>
        </div>
      )}
    </div>
  );
}

function AdminBadge({ children, tone = 'slate' }: { children: React.ReactNode; tone?: 'slate' | 'green' | 'red' | 'yellow' | 'blue' | 'amber' }) {
  const tones = { slate: 'bg-slate-100 text-slate-700 ring-slate-200', green: 'bg-emerald-50 text-emerald-700 ring-emerald-100', red: 'bg-red-50 text-red-700 ring-red-100', yellow: 'bg-amber-50 text-amber-700 ring-amber-100', blue: 'bg-sky-50 text-sky-700 ring-sky-100', amber: 'bg-amber-50 text-amber-700 ring-amber-100' };
  return <span className={`inline-flex items-center rounded-md px-2.5 py-1 text-xs font-bold ring-1 ${tones[tone]}`}>{children}</span>;
}

function AdminPanel({ title, action, children }: { title: string; action?: React.ReactNode; children: React.ReactNode }) {
  return <div className="rounded-lg border border-slate-200/80 bg-white p-4 shadow-sm"><div className="mb-4 flex flex-col gap-3 border-b border-slate-100 pb-4 sm:flex-row sm:items-center sm:justify-between"><h2 className="text-lg font-bold text-slate-950">{title}</h2>{action}</div>{children}</div>;
}

function AdminTable({ headers, children }: { headers: string[]; children: React.ReactNode }) {
  const rowCount = React.Children.count(children);
  return <div className="overflow-hidden rounded-[20px] border border-rose-100 bg-white shadow-sm"><div className="overflow-x-auto"><table className="min-w-full text-left text-sm"><thead className="bg-rose-50 text-xs font-bold uppercase tracking-wide text-slate-500"><tr className="border-b border-rose-100">{headers.map((header) => <th key={header} className="whitespace-nowrap px-4 py-3.5">{header}</th>)}</tr></thead><tbody className="divide-y divide-slate-100 bg-white text-slate-700 [&_tr:hover]:bg-rose-50/40">{children}</tbody></table></div><div className="flex flex-col gap-3 border-t border-rose-100 bg-rose-50/60 px-4 py-3 text-sm text-slate-500 sm:flex-row sm:items-center sm:justify-between"><span>Đang xem {rowCount} dòng trong bảng hiện tại.</span><div className="flex items-center gap-2"><button type="button" disabled className="inline-flex h-9 items-center justify-center rounded-xl border border-rose-200 bg-white px-3 text-sm font-semibold text-slate-400">Trang trước</button><span className="rounded-lg bg-white px-3 py-1.5 font-semibold text-slate-600">Trang 1/1</span><button type="button" disabled className="inline-flex h-9 items-center justify-center rounded-xl border border-rose-200 bg-white px-3 text-sm font-semibold text-slate-400">Trang sau</button></div></div></div>;
}

function BrandLogo({ brand }: { brand: any }) {
  const initial = String(brand.name || brand.code || '?').trim().charAt(0).toUpperCase() || '?';

  if (brand.logoUrl) {
    return (
      <span className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-slate-200 bg-white p-1 shadow-sm">
        <img src={brand.logoUrl} alt={brand.logoAltText || (brand.name ? `${brand.name} logo` : 'Brand logo')} className="h-full w-full rounded-full object-contain" />
      </span>
    );
  }

  return (
    <span className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-slate-100 text-sm font-bold text-slate-700 ring-1 ring-slate-200">
      {initial}
    </span>
  );
}

function VoucherConditions({ voucher }: { voucher: any }) {
  const conditions = [
    Number(voucher.minOrderValue || 0) > 0 ? `Tối thiểu ${currency.format(Number(voucher.minOrderValue || 0))}` : '',
    Number(voucher.maxDiscount || 0) > 0 ? `Giảm tối đa ${currency.format(Number(voucher.maxDiscount || 0))}` : '',
    voucher.stackable ? 'Cho cộng dồn' : 'Không cộng dồn',
    Number(voucher.validityDaysAfterClaim || 0) > 0 ? `Hạn sau lưu: ${voucher.validityDaysAfterClaim} ngày` : '',
    voucher.firstOrderOnly ? 'Chỉ đơn đầu tiên' : '',
    voucher.abandonedCartOnly ? 'Chỉ giỏ bỏ quên' : '',
    Number(voucher.perDeviceLimit || 0) > 0 ? `Thiết bị: ${voucher.perDeviceLimit}` : '',
    Number(voucher.perIpLimit || 0) > 0 ? `IP: ${voucher.perIpLimit}` : '',
    Array.isArray(voucher.eligibleTiers) && voucher.eligibleTiers.length ? `Hạng: ${voucher.eligibleTiers.join(', ')}` : '',
    Array.isArray(voucher.includeProductIds) && voucher.includeProductIds.length ? `SP áp dụng: ${voucher.includeProductIds.length}` : '',
    Array.isArray(voucher.excludeProductIds) && voucher.excludeProductIds.length ? `SP loại trừ: ${voucher.excludeProductIds.length}` : '',
    Array.isArray(voucher.includeCategoryIds) && voucher.includeCategoryIds.length ? `DM áp dụng: ${voucher.includeCategoryIds.length}` : '',
    Array.isArray(voucher.excludeCategoryIds) && voucher.excludeCategoryIds.length ? `DM loại trừ: ${voucher.excludeCategoryIds.length}` : '',
    voucher.assignedUserId ? `User: ${String(voucher.assignedUserId).slice(0, 8)}` : '',
    voucher.startsAt || voucher.endsAt ? `${voucher.startsAt ? new Date(voucher.startsAt).toLocaleDateString('vi-VN') : '...'} - ${voucher.endsAt ? new Date(voucher.endsAt).toLocaleDateString('vi-VN') : '...'}` : '',
  ].filter(Boolean);

  if (conditions.length === 0) return <span className="text-slate-400">Không ràng buộc</span>;
  return <div className="max-w-xs space-y-1 text-xs font-semibold text-slate-600">{conditions.map((item) => <div key={item}>{item}</div>)}</div>;
}

function Input({ label, value, onChange, onBlur, type = 'text', required = false, disabled = false }: { label: string; value: string | number; onChange: (value: string) => void; onBlur?: () => void; type?: string; required?: boolean; disabled?: boolean }) {
  return <label className="block"><span className="mb-1.5 block text-xs font-bold text-slate-500">{label}</span><input disabled={disabled} required={required} type={type} value={value} onBlur={onBlur} onChange={(event) => onChange(event.target.value)} className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm text-slate-800 outline-none transition focus:border-red-500 focus:ring-2 focus:ring-red-100 disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400" /></label>;
}

function Select({ label, value, onChange, options, disabled = false }: { label: string; value: string; onChange: (value: string) => void; options: [string, string][]; disabled?: boolean }) {
  return <label className="block"><span className="mb-1.5 block text-xs font-bold text-slate-500">{label}</span><select disabled={disabled} value={value} onChange={(event) => onChange(event.target.value)} className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm text-slate-800 outline-none transition focus:border-red-500 focus:ring-2 focus:ring-red-100 disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400">{options.map(([optionValue, labelText]) => <option key={optionValue || labelText} value={optionValue}>{labelText}</option>)}</select></label>;
}

function Checkbox({ label, checked, onChange, disabled = false }: { label: string; checked: boolean; onChange: (checked: boolean) => void; disabled?: boolean }) {
  return <label className="mt-5 flex h-10 items-center gap-2 text-sm font-semibold text-slate-700"><input type="checkbox" checked={checked} disabled={disabled} onChange={(event) => onChange(event.target.checked)} className="h-4 w-4 accent-red-600 disabled:opacity-40" /> {label}</label>;
}

function FileInput({ label, accept, multiple = false, onFiles }: { label: string; accept: string; multiple?: boolean; onFiles: (files: FileList | null) => void }) {
  return <label className="block"><span className="mb-1.5 block text-xs font-bold text-slate-500">{label}</span><span className="flex h-10 cursor-pointer items-center gap-2 rounded-md border border-dashed border-slate-300 bg-white px-3 text-sm font-semibold text-slate-600 transition hover:border-red-200 hover:bg-red-50 hover:text-red-700"><Upload className="h-4 w-4" /> Chọn file</span><input className="hidden" type="file" accept={accept} multiple={multiple} onChange={(event) => onFiles(event.target.files)} /></label>;
}

function RichTextEditor({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  const editorRef = React.useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (editorRef.current && editorRef.current.innerHTML !== value) {
      editorRef.current.innerHTML = value || '<p></p>';
    }
  }, [value]);

  function apply(command: string, commandValue?: string) {
    editorRef.current?.focus();
    document.execCommand(command, false, commandValue);
    onChange(editorRef.current?.innerHTML || '<p></p>');
  }

  return (
    <div className="block">
      <span className="mb-1.5 block text-xs font-bold text-slate-500">{label}</span>
      <div className="overflow-hidden rounded-md border border-slate-200 bg-white">
        <div className="flex flex-wrap gap-2 border-b border-slate-200 bg-slate-50 p-2">
          <button type="button" onClick={() => apply('bold')} className="rounded border border-slate-200 px-2 py-1 text-xs font-bold text-slate-700">Bold</button>
          <button type="button" onClick={() => apply('italic')} className="rounded border border-slate-200 px-2 py-1 text-xs font-bold text-slate-700">Italic</button>
          <button type="button" onClick={() => apply('formatBlock', 'h2')} className="rounded border border-slate-200 px-2 py-1 text-xs font-bold text-slate-700">H2</button>
          <button type="button" onClick={() => apply('insertUnorderedList')} className="rounded border border-slate-200 px-2 py-1 text-xs font-bold text-slate-700">List</button>
          <button type="button" onClick={() => { const link = window.prompt('Nhập URL liên kết'); if (link) apply('createLink', link); }} className="rounded border border-slate-200 px-2 py-1 text-xs font-bold text-slate-700">Link</button>
        </div>
        <div ref={editorRef} contentEditable suppressContentEditableWarning onInput={() => onChange(editorRef.current?.innerHTML || '<p></p>')} className="prose min-h-48 max-w-none px-4 py-3 text-sm outline-none" />
      </div>
    </div>
  );
}

function MultiSelectBox({ label, options, values, onChange }: { label: string; options: { value: string; label: string }[]; values: string[]; onChange: (values: string[]) => void }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-bold text-slate-500">{label}</span>
      <select multiple value={values} onChange={(event) => onChange(Array.from(event.target.selectedOptions).map((option) => option.value))} className="min-h-36 w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 outline-none transition focus:border-red-500 focus:ring-2 focus:ring-red-100">
        {options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
      </select>
    </label>
  );
}

function SubmitButtons({ editing, onCancel }: { editing: boolean; onCancel: () => void }) {
  return <div className="flex items-end gap-2"><button className="inline-flex h-10 items-center justify-center gap-2 rounded-xl bg-rose-200 px-4 text-sm font-bold text-slate-800 shadow-sm shadow-rose-50 transition hover:bg-rose-300"><Plus className="h-4 w-4" /> {editing ? 'Lưu' : 'Thêm'}</button>{editing && <button type="button" onClick={onCancel} title="Hủy chỉnh sửa" className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200 text-slate-600 transition hover:bg-slate-50 hover:text-slate-900"><X className="h-4 w-4" /></button>}</div>;
}

function SearchBox({ value, onChange, placeholder = 'Tìm kiếm nhanh' }: { value: string; onChange: (value: string) => void; placeholder?: string }) {
  return <label className="relative block w-full"><Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" /><input value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} className="h-11 w-full rounded-2xl border border-rose-200 bg-white/90 pl-9 pr-3 text-sm outline-none transition focus:border-rose-400 focus:ring-2 focus:ring-rose-100" /></label>;
}

function RowActions({ onEdit, onDelete, onRestore }: { onEdit: () => void; onDelete: () => void; onRestore?: () => void }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="relative flex items-center gap-2">
      <button type="button" onClick={onEdit} title="Sửa" className="inline-flex h-8 w-8 items-center justify-center rounded-xl border border-rose-200 bg-white/90 text-slate-600 transition hover:border-rose-300 hover:bg-rose-50 hover:text-rose-700">
        <Edit2 className="h-4 w-4" />
      </button>
      <button type="button" onClick={() => setOpen((value) => !value)} title="Thao tác khác" className="inline-flex h-8 w-8 items-center justify-center rounded-xl border border-slate-200 bg-white/90 text-slate-600 transition hover:border-slate-300 hover:bg-slate-50 hover:text-slate-900">
        <MoreHorizontal className="h-4 w-4" />
      </button>
      {open && (
        <div className="absolute right-0 top-10 z-20 min-w-[150px] overflow-hidden rounded-xl border border-slate-200 bg-white shadow-lg">
          <button type="button" onClick={() => { setOpen(false); onDelete(); }} className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm font-semibold text-red-600 transition hover:bg-red-50">
            <Trash2 className="h-4 w-4" /> Xóa / ẩn
          </button>
          {onRestore && (
            <button type="button" onClick={() => { setOpen(false); onRestore(); }} className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm font-semibold text-emerald-700 transition hover:bg-emerald-50">
              <RotateCcw className="h-4 w-4" /> Bật lại
            </button>
          )}
        </div>
      )}
    </div>
  );
}

function CategoryTableRow({ category, level, onEdit, onDelete, onRestore, onReorder }: { category: any; level: number; onEdit: () => void; onDelete: () => void; onRestore?: () => void; onReorder: (draggedId: string, targetId: string) => void }) {
  return (
    <tr draggable onDragStart={(event) => event.dataTransfer.setData('categoryId', category.id)} onDragOver={(event) => event.preventDefault()} onDrop={(event) => onReorder(event.dataTransfer.getData('categoryId'), category.id)}>
      <td className="px-4 py-3 text-slate-400"><GripVertical className="h-4 w-4" /></td>
      <td className="px-4 py-3">
        {category.iconUrl ? <img src={category.iconUrl} alt="" className="h-10 w-10 rounded-md border border-slate-200 object-cover" /> : <span className="text-xs font-semibold text-slate-400">{category.icon || '-'}</span>}
      </td>
      <td className="px-4 py-3 font-semibold text-slate-900">
        <div className="flex items-center gap-2" style={{ paddingLeft: level * 24 }}>
          {level > 0 && <span className="h-px w-4 bg-slate-300" />}
          <span>{category.name}</span>
        </div>
      </td>
      <td className="px-4 py-3 font-mono text-xs">{category.slug}</td>
      <td className="px-4 py-3">{category.parentId ? 'Danh mục con' : 'Danh mục cha'}</td>
      <td className="px-4 py-3">{category.parentName || '-'}</td>
      <td className="px-4 py-3">{category.specFields?.length || 0} trường / {category.filterConfig?.length || 0} lọc</td>
      <td className="px-4 py-3">
        <div className="flex flex-col items-start gap-1">
          <AdminBadge tone={category.status === 'DRAFT' || category.status === 'PENDING_REVIEW' ? 'yellow' : category.isActive ? 'green' : category.status === 'REJECTED' ? 'red' : 'slate'}>{category.status || (category.isActive ? 'ACTIVE' : 'INACTIVE')}</AdminBadge>
          {category.workflowStatus && <span className="text-xs font-semibold text-slate-500">Duyệt: {category.workflowStatus}</span>}
          {category.hiddenByParent && <span className="text-xs font-semibold text-amber-600">Ẩn theo danh mục cha</span>}
        </div>
      </td>
      <td className="px-4 py-3"><RowActions onEdit={onEdit} onDelete={onDelete} onRestore={onRestore} /></td>
    </tr>
  );
}

function MediaPreview({ title, items, onRemove }: { title: string; items: string[]; onRemove: (url: string) => void }) {
  if (items.length === 0) return null;
  return <div className="md:col-span-4"><div className="mb-2 text-xs font-bold text-slate-500">{title}</div><div className="flex flex-wrap gap-2">{items.map((item) => <div key={item} className="relative h-16 w-16 rounded-md border border-slate-200 bg-white p-1 shadow-sm"><img src={item} alt="" className="h-full w-full object-contain" /><button type="button" onClick={() => onRemove(item)} title="Xóa ảnh" className="absolute -right-2 -top-2 rounded-full bg-red-600 p-1 text-white shadow-sm"><X className="h-3 w-3" /></button></div>)}</div></div>;
}

function VideoPreview({ title, url, onRemove }: { title: string; url: string; onRemove: () => void }) {
  return (
    <div className="md:col-span-4">
      <div className="mb-2 text-xs font-bold text-slate-500">{title}</div>
      <div className="rounded-xl border border-slate-200 bg-slate-950 p-3 shadow-sm">
        <video src={url} controls className="max-h-72 w-full rounded-lg bg-black" />
        <div className="mt-3 flex justify-end">
          <button type="button" onClick={onRemove} className="rounded-md bg-red-50 px-3 py-2 text-sm font-bold text-red-700">Xóa video đã chọn</button>
        </div>
      </div>
    </div>
  );
}

function SimpleList({ title, icon: Icon, headers, rows, emptyText, action }: { title: string; icon: React.ElementType; headers: string[]; rows: (string | number)[][]; emptyText: string; action?: React.ReactNode }) {
  return <AdminPanel title={title} action={<div className="flex flex-col gap-2 sm:flex-row sm:items-center"><Icon className="hidden h-5 w-5 text-red-600 sm:block" />{action}</div>}><AdminTable headers={headers}>{rows.length === 0 ? <tr><td colSpan={headers.length} className="px-4 py-8 text-center text-sm font-medium text-slate-500">{emptyText}</td></tr> : rows.map((row, index) => <tr key={index}>{row.map((cell, cellIndex) => <td key={`${index}-${cellIndex}`} className={`px-4 py-3 ${cellIndex === 0 ? 'font-semibold text-slate-900' : ''}`}>{cell}</td>)}</tr>)}</AdminTable></AdminPanel>;
}



