import type React from 'react';
import {
  BadgePercent,
  Boxes,
  Building2,
  ClipboardList,
  FolderTree,
  Image,
  KeyRound,
  LayoutDashboard,
  MessagesSquare,
  Megaphone,
  Package,
  ScrollText,
  ShieldCheck,
  ShoppingCart,
  Star,
  Truck,
  Users,
  Zap,
} from 'lucide-react';

export type AdminTab = 'overview' | 'products' | 'flashSales' | 'categories' | 'brands' | 'suppliers' | 'services' | 'orders' | 'vouchers' | 'customers' | 'inventoryReceipts' | 'inventory' | 'reviews' | 'interactions' | 'content' | 'banners' | 'audit' | 'permissions';
export type AdminTabGroup = 'Tổng quan' | 'Kinh doanh' | 'Catalog' | 'Vận hành' | 'Khách hàng' | 'Hệ thống';
export type SpecField = { key: string; label: string; group?: string; type: string; required: boolean; variant: boolean; isFilterable?: boolean; filterType?: string; filterEnabled?: boolean };
export type CategoryFilterField = { key: string; label: string; type: string; enabled: boolean; source?: string };
export type VariantForm = {
  id?: string;
  sku: string;
  colorName: string;
  colorCode: string;
  storage: string;
  ram: string;
  configuration: string;
  specs: Record<string, string>;
  imageUrl: string;
  images: string[];
  price: number;
  salePrice: number;
  stockQuantity?: number;
  isActive: boolean;
  compareAtPrice?: number;
  isDefault?: boolean;
  status?: string;
  attributes?: Record<string, any>;
};
export type AccessoryOfferForm = {
  productId: string;
  productName: string;
  productSku: string;
  imageUrl: string;
  discountType: 'FIXED' | 'PERCENT';
  discountValue: number;
  maxQuantity: number;
};
export type AttachedServiceForm = {
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
export type WarrantyPolicyForm = {
  inheritWarrantyPolicy: boolean;
  hasWarranty: boolean;
  warrantyMonths: number;
  allowOneForOne: boolean;
  oneForOneDays: number;
};

export const currency = new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 });
export const compactCurrency = new Intl.NumberFormat('vi-VN', { notation: 'compact', maximumFractionDigits: 1 });
export const percent = new Intl.NumberFormat('vi-VN', { style: 'percent', maximumFractionDigits: 1 });
export const categoryStatusOptions: [string, string][] = [
  ['DRAFT', 'Nháp'],
  ['PENDING_REVIEW', 'Chờ duyệt'],
  ['APPROVED', 'Đã duyệt'],
  ['ACTIVE', 'Đang hiển thị'],
  ['REJECTED', 'Từ chối'],
  ['INACTIVE', 'Tạm ẩn'],
];
export const reviewStatusOptions: [string, string][] = [
  ['all', 'Tất cả trạng thái'],
  ['PENDING', 'Chờ duyệt'],
  ['PUBLISHED', 'Đang hiển thị'],
  ['HIDDEN', 'Đã ẩn'],
  ['REJECTED', 'Từ chối'],
];
export const reviewStarOptions: [string, string][] = [
  ['all', 'Tất cả số sao'],
  ['5', '5 sao'],
  ['4', '4 sao'],
  ['3', '3 sao'],
  ['2', '2 sao'],
  ['1', '1 sao'],
];
export const warrantyDurationOptions: [string, string][] = [
  ['0', 'Không thời hạn'],
  ['3', '3 tháng'],
  ['6', '6 tháng'],
  ['9', '9 tháng'],
  ['12', '12 tháng'],
  ['18', '18 tháng'],
  ['24', '24 tháng'],
  ['36', '36 tháng'],
];
export const serviceAttributeGroupOptions: [string, string][] = [
  ['WARRANTY', 'Bảo hành'],
  ['EXTENDED_WARRANTY', 'Bảo hành mở rộng'],
  ['ONE_FOR_ONE', '1 đổi 1'],
  ['ACCIDENTAL_DAMAGE', 'Rơi vỡ - rơi nước'],
  ['INSTALLATION', 'Lắp đặt'],
  ['CLEANING', 'Vệ sinh'],
  ['SUPPORT', 'Hỗ trợ kỹ thuật'],
];
export const serviceAttributeGroupLabel: Record<string, string> = Object.fromEntries(serviceAttributeGroupOptions);

export const toNumber = (value: unknown) => Number(value || 0);
export const getOrderTotal = (order: any) => toNumber(order.totalAmount ?? order.total_amount ?? order.total ?? order.grandTotal);
export const reviewStatusLabel: Record<string, string> = {
  PENDING: 'Chờ duyệt',
  PUBLISHED: 'Đang hiển thị',
  HIDDEN: 'Đã ẩn',
  REJECTED: 'Từ chối',
};
export const getOrderDate = (order: any) => new Date(order.createdAt || order.created_at || order.updatedAt || order.updated_at || Date.now());
export const getProductStock = (product: any) => {
  const variantStock = Array.isArray(product.variants) ? product.variants.reduce((sum: number, variant: any) => sum + toNumber(variant.stock ?? variant.quantity), 0) : 0;
  return toNumber(product.stock ?? product.quantity ?? product.inventoryQuantity ?? variantStock);
};
export const getInventorySettings = (product: any) => {
  const salesConfig = product?.salesConfig && typeof product.salesConfig === 'object' ? product.salesConfig : {};
  return {
    minimumStock: toNumber(salesConfig.minimumStock),
    blockSaleWhenOutOfStock: salesConfig.blockSaleWhenOutOfStock !== false,
    cycleCountDays: toNumber(salesConfig.cycleCountDays || 30),
  };
};
export const getProductSold = (product: any) => toNumber(product.soldCount ?? product.sold_count ?? product.totalSold ?? product.salesCount ?? product.periodSoldCount);
export const getVoucherBudgetUsage = (voucher: any) => {
  const cap = toNumber(voucher.totalBudgetCap ?? voucher.total_budget_cap ?? voucher.budgetCap);
  const used = toNumber(voucher.usedBudget ?? voucher.used_budget ?? voucher.budgetUsed ?? voucher.discountUsed);
  return cap > 0 ? used / cap : 0;
};
export const slugifyText = (value: string) => value
  .replace(/\u0111/g, 'd')
  .replace(/\u0110/g, 'D')
  .normalize('NFD')
  .replace(/[\u0300-\u036f]/g, '')
  .toLowerCase()
  .replace(/[^a-z0-9]+/g, '-')
  .replace(/^-+|-+$/g, '');

export const defaultWarrantyPolicy: WarrantyPolicyForm = {
  inheritWarrantyPolicy: true,
  hasWarranty: false,
  warrantyMonths: 0,
  allowOneForOne: false,
  oneForOneDays: 0,
};

export function normalizeWarrantyPolicy(value: any): WarrantyPolicyForm {
  return {
    inheritWarrantyPolicy: value?.inheritWarrantyPolicy !== false,
    hasWarranty: Boolean(value?.hasWarranty),
    warrantyMonths: Number(value?.warrantyMonths || 0),
    allowOneForOne: Boolean(value?.allowOneForOne),
    oneForOneDays: Number(value?.oneForOneDays || 0),
  };
}

export function categoryWarrantyPolicy(category: any, parent?: any): WarrantyPolicyForm {
  const own = normalizeWarrantyPolicy(category?.warrantyPolicy || defaultWarrantyPolicy);
  if (category?.parentId && own.inheritWarrantyPolicy && parent) {
    return normalizeWarrantyPolicy(parent.warrantyPolicy || defaultWarrantyPolicy);
  }
  return own;
}

export const tabs: { id: AdminTab; label: string; icon: React.ElementType }[] = [
  { id: 'overview', label: 'Tổng quan', icon: LayoutDashboard },
  { id: 'products', label: 'Sản phẩm', icon: Package },
  { id: 'flashSales', label: 'Flash sale', icon: Zap },
  { id: 'categories', label: 'Danh mục', icon: FolderTree },
  { id: 'brands', label: 'Thương hiệu', icon: Building2 },
  { id: 'suppliers', label: 'Nhà cung cấp', icon: Truck },
  { id: 'services', label: 'Dịch vụ', icon: ShieldCheck },
  { id: 'orders', label: 'Đơn hàng', icon: ClipboardList },
  { id: 'vouchers', label: 'Voucher', icon: BadgePercent },
  { id: 'customers', label: 'Khách hàng', icon: Users },
  { id: 'inventoryReceipts', label: 'Nhập kho', icon: ShoppingCart },
  { id: 'inventory', label: 'Tồn kho', icon: Boxes },
  { id: 'reviews', label: 'Đánh giá', icon: Star },
  { id: 'interactions', label: 'Bình luận & hỏi đáp', icon: MessagesSquare },
  { id: 'content', label: 'Video & nội dung', icon: Megaphone },
  { id: 'banners', label: 'Banner', icon: Image },
  { id: 'audit', label: 'Nhật ký', icon: ScrollText },
  { id: 'permissions', label: 'Phân quyền', icon: KeyRound },
];

export const tabTone: Record<AdminTab, { active: string; item: string; icon: string; surface: string; label: string; title: string; description: string }> = {
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
  flashSales: {
    active: 'bg-red-600 text-white shadow-sm shadow-red-200',
    item: 'border-red-100 bg-red-50/70 text-red-950 hover:bg-red-100/80',
    icon: 'bg-red-50 text-red-700 ring-red-100',
    surface: 'border-red-100 bg-red-50/70 text-red-900',
    label: 'Kinh doanh',
    title: 'Quản lý flash sale',
    description: 'Cài đặt giá sale theo tiền hoặc phần trăm, kèm thời gian bắt đầu và kết thúc.',
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
  suppliers: {
    active: 'bg-red-600 text-white shadow-sm shadow-red-200',
    item: 'border-pink-100 bg-pink-50/70 text-pink-950 hover:bg-pink-100/80',
    icon: 'bg-red-50 text-red-700 ring-red-100',
    surface: 'border-red-100 bg-red-50/70 text-red-900',
    label: 'Quản lý',
    title: 'Quản lý nhà cung cấp',
    description: 'Khu vực quản lý hồ sơ nhà cung cấp, thông tin liên hệ và trạng thái hợp tác.',
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
  inventoryReceipts: {
    active: 'bg-amber-600 text-white shadow-sm shadow-amber-200',
    item: 'border-orange-100 bg-orange-50/75 text-orange-950 hover:bg-orange-100/80',
    icon: 'bg-amber-50 text-amber-700 ring-amber-100',
    surface: 'border-amber-100 bg-amber-50/80 text-amber-900',
    label: 'Vận hành',
    title: 'Quản lý nhập kho',
    description: 'Khu vực tạo phiếu nhập và theo dõi danh sách nhập kho theo nhà cung cấp, sản phẩm và biến thể.',
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
  interactions: {
    active: 'bg-sky-600 text-white shadow-sm shadow-sky-200',
    item: 'border-cyan-100 bg-cyan-50/75 text-cyan-950 hover:bg-cyan-100/80',
    icon: 'bg-sky-50 text-sky-700 ring-sky-100',
    surface: 'border-sky-100 bg-sky-50/80 text-sky-900',
    label: 'Khách hàng',
    title: 'Quản lý bình luận & hỏi đáp',
    description: 'Khu vực quản lý bình luận vui và hỏi đáp sản phẩm theo cấu trúc 2 tầng rõ ràng.',
  },
  content: {
    active: 'bg-teal-600 text-white shadow-sm shadow-teal-200',
    item: 'border-teal-100 bg-teal-50/75 text-teal-950 hover:bg-teal-100/80',
    icon: 'bg-teal-50 text-teal-700 ring-teal-100',
    surface: 'border-teal-100 bg-teal-50/80 text-teal-900',
    label: 'Nội dung',
    title: 'Video & nội dung',
    description: 'Khu vực quản lý video, bài viết và nội dung hiển thị riêng với dashboard.',
  },
  banners: {
    active: 'bg-teal-600 text-white shadow-sm shadow-teal-200',
    item: 'border-teal-100 bg-teal-50/75 text-teal-950 hover:bg-teal-100/80',
    icon: 'bg-teal-50 text-teal-700 ring-teal-100',
    surface: 'border-teal-100 bg-teal-50/80 text-teal-900',
    label: 'Nội dung',
    title: 'Quản lý banner',
    description: 'Khu vực quản lý banner trang chủ, liên kết danh mục và sản phẩm nổi bật.',
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

export const adminTabs: { id: AdminTab; label: string; group: AdminTabGroup; icon: React.ElementType }[] = [
  { id: 'overview', label: 'Tổng quan', group: 'Tổng quan', icon: LayoutDashboard },
  { id: 'orders', label: 'Đơn hàng', group: 'Kinh doanh', icon: ClipboardList },
  { id: 'vouchers', label: 'Voucher', group: 'Kinh doanh', icon: BadgePercent },
  { id: 'flashSales', label: 'Flash sale', group: 'Kinh doanh', icon: Zap },
  { id: 'products', label: 'Sản phẩm', group: 'Catalog', icon: Package },
  { id: 'categories', label: 'Danh mục', group: 'Catalog', icon: FolderTree },
  { id: 'brands', label: 'Thương hiệu', group: 'Catalog', icon: Building2 },
  { id: 'suppliers', label: 'Nhà cung cấp', group: 'Catalog', icon: Truck },
  { id: 'services', label: 'Dịch vụ', group: 'Catalog', icon: ShieldCheck },
  { id: 'inventoryReceipts', label: 'Nhập kho', group: 'Vận hành', icon: ShoppingCart },
  { id: 'inventory', label: 'Tồn kho', group: 'Vận hành', icon: Boxes },
  { id: 'content', label: 'Video & nội dung', group: 'Vận hành', icon: Megaphone },
  { id: 'banners', label: 'Banner', group: 'Vận hành', icon: Image },
  { id: 'customers', label: 'Khách hàng', group: 'Khách hàng', icon: Users },
  { id: 'reviews', label: 'Đánh giá', group: 'Khách hàng', icon: Star },
  { id: 'interactions', label: 'Bình luận & hỏi đáp', group: 'Khách hàng', icon: MessagesSquare },
  { id: 'audit', label: 'Nhật ký', group: 'Hệ thống', icon: ScrollText },
  { id: 'permissions', label: 'Phân quyền', group: 'Hệ thống', icon: KeyRound },
];

// This normalized tone map overrides legacy mojibake strings while keeping the old data flow intact.
export const adminTabTone: Partial<Record<AdminTab, { active: string; item: string; icon: string; surface: string; label: string; title: string; description: string }>> = {
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
  flashSales: {
    active: 'border-red-200 bg-red-100 text-slate-800 shadow-sm shadow-red-50',
    item: 'border-red-100 bg-red-50/70 text-slate-700 hover:bg-red-100/80',
    icon: 'bg-red-50 text-red-700 ring-red-100',
    surface: 'border-red-100 bg-red-50/70 text-red-900',
    label: 'Kinh doanh',
    title: 'Quản lý flash sale',
    description: 'Cài đặt giá sale theo tiền hoặc phần trăm, kèm thời gian bắt đầu và kết thúc.',
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
  suppliers: {
    active: 'border-rose-200 bg-rose-100 text-slate-800 shadow-sm shadow-rose-50',
    item: 'border-rose-100 bg-rose-50/70 text-slate-700 hover:bg-rose-100/80',
    icon: 'bg-rose-50 text-rose-700 ring-rose-100',
    surface: 'border-rose-100 bg-rose-50/70 text-rose-900',
    label: 'Quản lý',
    title: 'Quản lý nhà cung cấp',
    description: 'Khu vực quản lý hồ sơ nhà cung cấp, thông tin liên hệ và trạng thái hợp tác.',
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
  interactions: {
    active: 'border-cyan-200 bg-cyan-100 text-slate-800 shadow-sm shadow-cyan-50',
    item: 'border-cyan-100 bg-cyan-50/75 text-slate-700 hover:bg-cyan-100/80',
    icon: 'bg-sky-50 text-sky-700 ring-sky-100',
    surface: 'border-sky-100 bg-sky-50/80 text-sky-900',
    label: 'Khách hàng',
    title: 'Quản lý bình luận & hỏi đáp',
    description: 'Khu vực quản lý bình luận vui và hỏi đáp sản phẩm theo cấu trúc 2 tầng rõ ràng.',
  },
  content: {
    active: 'border-emerald-200 bg-emerald-100 text-slate-800 shadow-sm shadow-emerald-50',
    item: 'border-emerald-100 bg-emerald-50/75 text-slate-700 hover:bg-emerald-100/80',
    icon: 'bg-emerald-50 text-emerald-700 ring-emerald-100',
    surface: 'border-emerald-100 bg-emerald-50/80 text-emerald-900',
    label: 'Nội dung',
    title: 'Video và nội dung',
    description: 'Khu vực quản lý video, bài viết và nội dung hiển thị riêng với dashboard.',
  },
  banners: {
    active: 'border-emerald-200 bg-emerald-100 text-slate-800 shadow-sm shadow-emerald-50',
    item: 'border-emerald-100 bg-emerald-50/75 text-slate-700 hover:bg-emerald-100/80',
    icon: 'bg-emerald-50 text-emerald-700 ring-emerald-100',
    surface: 'border-emerald-100 bg-emerald-50/80 text-emerald-900',
    label: 'Nội dung',
    title: 'Quản lý banner',
    description: 'Khu vực quản lý banner trang chủ, liên kết danh mục và sản phẩm nổi bật.',
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

export const searchPlaceholderByTab: Record<AdminTab, string> = {
  overview: 'Tìm số liệu, cảnh báo hoặc khu vực cần theo dõi',
  products: 'Tìm sản phẩm, SKU, thương hiệu',
  flashSales: 'Tìm sản phẩm đang flash sale',
  categories: 'Tìm danh mục, slug, danh mục cha',
  brands: 'Tìm thương hiệu, mã hoặc SEO',
  suppliers: 'Tìm nhà cung cấp, mã, liên hệ hoặc số điện thoại',
  services: 'Tìm dịch vụ, mã, nhóm hoặc loại dịch vụ',
  orders: 'Tìm mã đơn, khách hàng, trạng thái',
  vouchers: 'Tìm mã voucher, loại, trạng thái',
  customers: 'Tìm khách hàng, email, hạng',
  inventoryReceipts: 'Tìm mã phiếu nhập, nhà cung cấp, sản phẩm hoặc SKU',
  inventory: 'Tìm sản phẩm, SKU, trạng thái kho',
  reviews: 'Tìm sản phẩm, khách hàng, nội dung',
  interactions: 'Tìm sản phẩm, khách hàng, bình luận hoặc câu hỏi',
  content: 'Tìm tiêu đề, loại, mô tả',
  banners: 'Tìm banner theo tiêu đề hoặc mô tả',
  audit: 'Tìm sự kiện, tài nguyên hoặc IP',
  permissions: 'Tìm vai trò, nhóm quyền hoặc thao tác',
};

export const statusLabel: Record<string, string> = {
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
  DISCONTINUED: 'Ngừng kinh doanh',
  DRAFT: 'Nháp thêm',
  REVISION_DRAFT: 'Nháp chỉnh sửa',
  ARCHIVED: 'Lưu trữ',
};

export const orderStatusOptions: [string, string][] = [
  ['PENDING', 'Chờ xử lý'],
  ['PROCESSING', 'Đang đóng gói'],
  ['SHIPPED', 'Đang giao'],
  ['COMPLETED', 'Đã giao'],
  ['CANCELLED', 'Đã hủy'],
  ['PAYMENT_FAILED', 'Thanh toán thất bại'],
  ['RETURNING', 'Đang hoàn hàng'],
  ['RETURNED', 'Đã nhận hàng hoàn'],
];

export const orderTransitionMap: Record<string, string[]> = {
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

export const productStatusOptions: [string, string][] = [
  ['DRAFT', 'Nháp thêm'],
  ['REVISION_DRAFT', 'Nháp chỉnh sửa'],
  ['PENDING', 'Chờ duyệt'],
  ['ACTIVE', 'Đang bán'],
  ['INACTIVE', 'Tạm ẩn'],
  ['DISCONTINUED', 'Ngừng kinh doanh'],
  ['ARCHIVED', 'Lưu trữ'],
];

export const productPublicationStatusOptions: [string, string][] = [
  ['ACTIVE', 'Đang bán'],
  ['INACTIVE', 'Tạm ẩn'],
  ['DISCONTINUED', 'Ngừng kinh doanh'],
];

export const productStatusLabel: Record<string, string> = {
  ...Object.fromEntries(productStatusOptions),
  DISCONTINUED: 'Ngừng kinh doanh',
};
export const contentTypeOptions: [string, string][] = [
  ['VIDEO', 'Video'],
  ['BANNER', 'Banner'],
  ['MARKETING_PAGE', 'Trang marketing'],
];
export const videoSourceOptions: [string, string][] = [
  ['UPLOAD', 'Upload file'],
  ['YOUTUBE', 'Link YouTube'],
];
export const videoCategoryOptions: [string, string][] = [
  ['PRODUCT', 'Liên quan sản phẩm'],
  ['NEWS', 'Tin tức'],
  ['TIPS', 'Mẹo hay'],
  ['SERVICE', 'Dịch vụ'],
  ['REVIEW', 'Đánh giá / trải nghiệm'],
  ['OTHER', 'Khác'],
];
export const contentStatusOptions: [string, string][] = [
  ['DRAFT', 'Nháp'],
  ['SCHEDULED', 'Chờ đăng'],
  ['PUBLISHED', 'Đã xuất bản'],
  ['ARCHIVED', 'Lưu trữ'],
];


export const emptyContentForm = {
  title: '',
  description: '',
  contentType: 'VIDEO',
  videoSource: 'UPLOAD',
  videoCategory: 'PRODUCT',
  status: 'ACTIVE',
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

export const inventoryTransactionOptions: [string, string][] = [
  ['RECEIPT', 'Nhập kho'],
  ['ADJUSTMENT', 'Điều chỉnh'],
  ['RETURN', 'Hoàn hàng'],
  ['REVERSAL', 'Đảo giao dịch'],
];

export const voucherCampaignOptions: [string, string][] = [
  ['ACQUISITION', 'Tân binh / đơn đầu tiên'],
  ['RETENTION', 'Giữ chân / mua lại'],
  ['LOYALTY', 'Theo hạng thành viên'],
  ['CONVERSION', 'Thúc đẩy chốt đơn'],
  ['FLASH_SALE', 'Flash sale ngắn hạn'],
  ['ABANDONED_CART', 'Giỏ hàng bị bỏ quên'],
  ['CUSTOMER_SERVICE', 'Chăm sóc / đền bù'],
];

export const voucherAudienceOptions: [string, string][] = [
  ['PUBLIC', 'Công khai'],
  ['NEW_CUSTOMER', 'Khách hàng mới'],
  ['MEMBER_TIER', 'Theo hạng thành viên'],
  ['SPECIFIC_USER', 'Một khách hàng cụ thể'],
  ['HIDDEN', 'Mã ẩn do admin cấp'],
  ['ABANDONED_CART', 'Khôi phục giỏ hàng'],
];

export const voucherTierOptions = ['MEMBER', 'SILVER', 'GOLD', 'PLATINUM', 'DIAMOND'];

export const emptyVariant: VariantForm = {
  sku: '',
  colorName: '',
  colorCode: '#111827',
  storage: '',
  ram: '',
  configuration: '',
  specs: {},
  imageUrl: '',
  images: [],
  price: 0,
  salePrice: 0,
  isActive: true,
  compareAtPrice: 0,
  isDefault: false,
  status: 'active',
  attributes: {},
};

export const emptyProduct = {
  name: '',
  price: 0,
  discountPrice: 0,
  stock: 0,
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
  imeiPolicy: { mode: 'CATEGORY', trackImei: false },
  serialPolicy: { mode: 'CATEGORY', trackSerialNumber: false },
  warrantyPolicy: defaultWarrantyPolicy,
  updatedAt: '',
  version: 1,
  variantSpecKeys: [] as string[],
  variants: [] as VariantForm[],
  options: [] as { name: string; values: string[] }[],
  status: 'DRAFT',
  isFeatured: false,
  isFlashSale: false,
};

export const productExtraKeys = ['_variantSpecKeys', '_seoTitle', '_seoDescription', '_seoSlug', '_accessoryProducts', '_accessoryOffers', '_attachedServices', '_warrantyPolicy', '_imeiPolicy', '_serialPolicy', '_targetProductStatus'];

export function buildVariantSku(productName: string, colorName: string, index: number) {
  const part = (value: string, fallback: string) => slugifyText(value || fallback).split('-').map((item) => item.charAt(0)).join('').slice(0, 5).toUpperCase() || fallback;
  return `${part(productName, 'SP')}-${part(colorName, `M${index + 1}`)}-${String(index + 1).padStart(2, '0')}`;
}

export function compactId(id?: string) {
  return id ? `#${id.slice(0, 8).toUpperCase()}` : '#';
}

export function matchesSearch(item: any, keyword: string, fields: string[]) {
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

export function sameId(left: unknown, right: unknown) {
  return String(left || '') !== '' && String(left || '') === String(right || '');
}

export function splitIds(value: string) {
  return value.split(/[\n,]/).map((item) => item.trim()).filter(Boolean);
}

export function groupSpecFields(fields: SpecField[]) {
  return fields.reduce<{ title: string; fields: SpecField[] }[]>((groups, field) => {
    const title = field.group?.trim() || 'Thông số chung';
    const existing = groups.find((group) => group.title === title);
    if (existing) existing.fields.push(field);
    else groups.push({ title, fields: [field] });
    return groups;
  }, []);
}
