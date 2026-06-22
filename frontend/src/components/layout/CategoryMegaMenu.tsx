import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { ChevronRight, Flame, ShieldCheck, Truck, Zap } from 'lucide-react';
import { CatalogGroup } from '../../data/categories';
import { useCatalog } from '../../hooks/useCatalog';

type Props = {
  compact?: boolean;
  onNavigate?: () => void;
};

const defaultGroups: CatalogGroup[] = [
  { title: 'Phân khúc giá', items: ['Dưới 2 triệu', 'Từ 2 - 4 triệu', 'Từ 4 - 7 triệu', 'Từ 7 - 13 triệu', 'Từ 13 - 20 triệu', 'Trên 20 triệu'] },
  { title: 'Theo nhu cầu', items: ['Bán chạy', 'Sản phẩm mới', 'Cao cấp', 'Giá tốt'] },
];

const menuGroupsBySlug: Record<string, CatalogGroup[]> = {
  'dien-thoai': [
    { title: 'Phân khúc giá', items: ['Dưới 3 triệu', 'Từ 3 - 6 triệu', 'Từ 6 - 10 triệu', 'Từ 10 - 15 triệu', 'Trên 15 triệu'] },
    { title: 'Theo nhu cầu', items: ['Điện thoại gập', 'Điện thoại Gaming', 'Pin trâu', 'Chụp ảnh đẹp', 'Sạc nhanh', 'Mỏng nhẹ'] },
    { title: 'Dòng máy', items: ['iPhone', 'Samsung Galaxy S', 'Samsung Galaxy A', 'OPPO Reno', 'Xiaomi Redmi', 'HONOR Magic'] },
    { title: 'Cấu hình nổi bật', items: ['5G', 'RAM 8GB', 'RAM 12GB', 'Bộ nhớ 256GB', 'Màn hình AMOLED', 'Camera 50MP'] },
  ],
  'may-tinh-bang': [
    { title: 'Phân khúc giá', items: ['Dưới 5 triệu', 'Từ 5 - 10 triệu', 'Từ 10 - 15 triệu', 'Trên 15 triệu'] },
    { title: 'Theo nhu cầu', items: ['Học tập', 'Văn phòng', 'Giải trí', 'Vẽ thiết kế', 'Màn hình lớn', 'Có bút cảm ứng'] },
    { title: 'Dòng máy', items: ['iPad', 'Samsung Tab', 'Lenovo Tab', 'Xiaomi Pad', 'OPPO Pad'] },
  ],
  laptop: [
    { title: 'Phân khúc giá', items: ['Dưới 10 triệu', 'Từ 10 - 15 triệu', 'Từ 15 - 20 triệu', 'Từ 20 - 25 triệu', 'Từ 25 - 30 triệu', 'Trên 30 triệu'] },
    { title: 'Theo nhu cầu', items: ['Văn phòng', 'Gaming', 'Mỏng nhẹ', 'Đồ họa - kỹ thuật', 'Sinh viên', 'Cảm ứng', 'Laptop AI'] },
    { title: 'Dòng chip', items: ['Intel Core i3', 'Intel Core i5', 'Intel Core i7', 'Intel Core i9', 'Intel Core Ultra', 'AMD Ryzen', 'Apple M Series'] },
    { title: 'Kích thước màn hình', items: ['Laptop 13 inch', 'Laptop 14 inch', 'Laptop 15.6 inch', 'Laptop 16 inch', 'Laptop 17 inch'] },
  ],
  'phu-kien': [
    { title: 'Loại phụ kiện', items: ['Tai nghe', 'Sạc cáp', 'Ốp lưng', 'Dán màn hình', 'Pin dự phòng', 'Bàn phím', 'Chuột', 'Hub chuyển đổi'] },
    { title: 'Theo nhu cầu', items: ['Sạc nhanh', 'Chống ồn', 'Gaming', 'Văn phòng', 'Du lịch', 'Apple ecosystem'] },
    { title: 'Phân khúc giá', items: ['Dưới 300 nghìn', 'Từ 300 - 700 nghìn', 'Từ 700 nghìn - 1.5 triệu', 'Trên 1.5 triệu'] },
  ],
  'dong-ho-thong-minh': [
    { title: 'Theo nhu cầu', items: ['Theo dõi sức khỏe', 'Luyện tập thể thao', 'Pin lâu', 'Nghe gọi', 'Định vị GPS', 'Chống nước'] },
    { title: 'Dòng sản phẩm', items: ['Apple Watch', 'Samsung Watch', 'Garmin', 'Amazfit', 'Coros'] },
    { title: 'Phân khúc giá', items: ['Dưới 2 triệu', 'Từ 2 - 5 triệu', 'Từ 5 - 10 triệu', 'Trên 10 triệu'] },
  ],
  'may-anh': [
    { title: 'Theo nhu cầu', items: ['Du lịch', 'Quay vlog', 'Chụp chân dung', 'Chụp phong cảnh', 'Quay phim chuyên nghiệp'] },
    { title: 'Loại máy', items: ['Mirrorless', 'DSLR', 'Action camera', 'Gimbal camera', 'Ống kính'] },
    { title: 'Phân khúc giá', items: ['Dưới 10 triệu', 'Từ 10 - 20 triệu', 'Từ 20 - 40 triệu', 'Trên 40 triệu'] },
  ],
  camera: [
    { title: 'Theo nhu cầu', items: ['Camera trong nhà', 'Camera ngoài trời', 'Camera xoay 360', 'Camera pin sạc', 'Camera chống nước'] },
    { title: 'Tính năng', items: ['Độ phân giải 2K', 'Độ phân giải 4K', 'Đàm thoại 2 chiều', 'Nhận diện người', 'Lưu trữ cloud'] },
    { title: 'Phân khúc giá', items: ['Dưới 500 nghìn', 'Từ 500 nghìn - 1 triệu', 'Từ 1 - 2 triệu', 'Trên 2 triệu'] },
  ],
};

const menuGroupAliases: Record<string, string> = {
  smartphone: 'dien-thoai',
  phone: 'dien-thoai',
  mobile: 'dien-thoai',
  tablet: 'may-tinh-bang',
  'may-tinh-xach-tay': 'laptop',
  notebook: 'laptop',
  macbook: 'laptop',
  'phu-kien-cong-nghe': 'phu-kien',
  accessory: 'phu-kien',
  smartwatch: 'dong-ho-thong-minh',
  watch: 'dong-ho-thong-minh',
  'may-anh-camera': 'may-anh',
  camera: 'camera',
};

const million = 1000000;

const priceRangeByLabel: Record<string, { min?: number; max?: number }> = {
  'Dưới 300 nghìn': { min: 0, max: 300000 },
  'Dưới 500 nghìn': { min: 0, max: 500000 },
  'Từ 300 - 700 nghìn': { min: 300000, max: 700000 },
  'Từ 500 nghìn - 1 triệu': { min: 500000, max: million },
  'Từ 700 nghìn - 1.5 triệu': { min: 700000, max: 1.5 * million },
  'Từ 1 - 2 triệu': { min: million, max: 2 * million },
  'Dưới 2 triệu': { min: 0, max: 2 * million },
  'Dưới 3 triệu': { min: 0, max: 3 * million },
  'Dưới 5 triệu': { min: 0, max: 5 * million },
  'Dưới 10 triệu': { min: 0, max: 10 * million },
  'Từ 2 - 4 triệu': { min: 2 * million, max: 4 * million },
  'Từ 2 - 5 triệu': { min: 2 * million, max: 5 * million },
  'Từ 3 - 6 triệu': { min: 3 * million, max: 6 * million },
  'Từ 4 - 7 triệu': { min: 4 * million, max: 7 * million },
  'Từ 5 - 10 triệu': { min: 5 * million, max: 10 * million },
  'Từ 6 - 10 triệu': { min: 6 * million, max: 10 * million },
  'Từ 7 - 13 triệu': { min: 7 * million, max: 13 * million },
  'Từ 10 - 15 triệu': { min: 10 * million, max: 15 * million },
  'Từ 10 - 20 triệu': { min: 10 * million, max: 20 * million },
  'Từ 13 - 20 triệu': { min: 13 * million, max: 20 * million },
  'Từ 15 - 20 triệu': { min: 15 * million, max: 20 * million },
  'Từ 20 - 25 triệu': { min: 20 * million, max: 25 * million },
  'Từ 20 - 40 triệu': { min: 20 * million, max: 40 * million },
  'Từ 25 - 30 triệu': { min: 25 * million, max: 30 * million },
  'Trên 1.5 triệu': { min: 1.5 * million },
  'Trên 2 triệu': { min: 2 * million },
  'Trên 10 triệu': { min: 10 * million },
  'Trên 15 triệu': { min: 15 * million },
  'Trên 20 triệu': { min: 20 * million },
  'Trên 30 triệu': { min: 30 * million },
  'Trên 40 triệu': { min: 40 * million },
};

const getMenuItemLink = (categorySlug: string, groupTitle: string, item: string) => {
  if (groupTitle === 'Thương hiệu') {
    return `/products/${categorySlug}?brand=${encodeURIComponent(item)}`;
  }

  if (groupTitle === 'Phân khúc giá') {
    const range = priceRangeByLabel[item];
    if (range) {
      const search = new URLSearchParams();
      if (range.min !== undefined) search.set('min_price', String(range.min));
      if (range.max !== undefined) search.set('max_price', String(range.max));
      return `/products/${categorySlug}?${search.toString()}`;
    }
  }

  return `/search?q=${encodeURIComponent(item)}&category=${categorySlug}`;
};

const findConfiguredGroups = (slug: string) => {
  if (menuGroupsBySlug[slug]) return menuGroupsBySlug[slug];
  const alias = menuGroupAliases[slug];
  if (alias && menuGroupsBySlug[alias]) return menuGroupsBySlug[alias];
  return defaultGroups;
};

const getMenuGroups = (slug: string, subcategoryGroups: CatalogGroup[], brands: string[]) => {
  const brandGroup = brands.length ? [{ title: 'Thương hiệu', items: brands.slice(0, 14) }] : [];
  const configuredGroups = findConfiguredGroups(slug);
  const demandGroups = subcategoryGroups.length
    ? subcategoryGroups.map((group) => ({ ...group, title: group.title === 'Danh mục con' ? 'Theo nhu cầu' : group.title }))
    : [];

  return [...brandGroup, ...demandGroups, ...configuredGroups].filter((group) => group.items.length > 0);
};

const quickLinks = [
  { icon: Zap, title: 'Flash sale', text: 'Giá tốt hôm nay', href: '/flash-sale' },
  { icon: Truck, title: 'Giao nhanh', text: 'Nội thành 2 giờ', href: '/delivery-policy' },
  { icon: ShieldCheck, title: 'Bảo hành', text: 'Chính hãng rõ ràng', href: '/warranty' },
];

export function CategoryMegaMenu({ compact = false, onNavigate }: Props) {
  const { categories, loading } = useCatalog({ includeRankedFeatured: true });
  const [activeId, setActiveId] = useState<string | null>(null);

  const activeCategory = useMemo(
    () => categories.find(category => category.id === activeId || category.slug === activeId) || null,
    [activeId, categories]
  );

  useEffect(() => {
    if (!compact && !activeId && categories.length > 0) {
      setActiveId(categories[0].id);
    }
  }, [activeId, categories, compact]);

  if (loading) {
    return (
      <div className="w-[274px] rounded-xl bg-white border border-slate-100 shadow-sm p-4 text-sm text-slate-400">
        Đang tải danh mục...
      </div>
    );
  }

  if (categories.length === 0) {
    return (
      <div className="w-[274px] rounded-xl bg-white border border-slate-100 shadow-sm p-4 text-sm text-slate-400">
        Chưa có danh mục trong database.
      </div>
    );
  }

  const panelGroups = activeCategory
    ? getMenuGroups(activeCategory.slug, activeCategory.groups, activeCategory.brands)
    : [];

  const handleCategoryClick = (event: React.MouseEvent<HTMLAnchorElement>, category: typeof categories[number]) => {
    const isTouchLayout = window.matchMedia('(hover: none)').matches;

    if (compact && !isTouchLayout) {
      onNavigate?.();
      return;
    }

    if (isTouchLayout || activeCategory?.id !== category.id) {
      event.preventDefault();
      setActiveId(category.id);
    } else {
      onNavigate?.();
    }
  };

  return (
    <div
      onMouseLeave={() => {
        if (compact) setActiveId(null);
      }}
      className={`relative flex overflow-visible text-slate-900 ${
        compact ? 'h-full min-h-0 w-[274px]' : 'w-full'
      } ${compact ? '' : 'flex-col gap-3 md:flex-row md:gap-4'}`}
    >
      <nav className={`${compact ? 'h-full min-h-0 w-[274px]' : 'w-full md:max-h-[min(640px,calc(100vh-96px))] md:w-[248px] xl:w-[274px]'} flex shrink-0 flex-col overflow-hidden rounded-xl border border-slate-100 bg-white py-2 shadow-xl`}>
        <div className={`${compact ? 'flex flex-col' : ''} min-h-0 flex-1 overflow-y-auto`}>
          {categories.map((category) => {
            const Icon = category.icon;
            const isActive = activeCategory?.id === category.id;

            return (
              <Link
                key={category.id}
                to={`/products/${category.slug}`}
                onMouseEnter={() => setActiveId(category.id)}
                onFocus={() => setActiveId(category.id)}
                onClick={(event) => handleCategoryClick(event, category)}
                className={`flex min-w-[196px] items-center justify-between px-5 text-[15px] font-semibold transition md:min-w-0 ${
                  compact ? 'min-h-11 flex-1' : 'h-11'
                } ${
                  isActive ? 'bg-red-50 text-primary' : 'text-slate-800 hover:bg-slate-50 hover:text-primary'
                }`}
              >
                <span className="flex min-w-0 items-center gap-4">
                  <Icon className="h-5 w-5 shrink-0 text-primary" />
                  <span className="truncate">{category.name}</span>
                </span>
                <ChevronRight className={`h-5 w-5 shrink-0 ${isActive ? 'text-primary' : 'text-slate-400'}`} />
              </Link>
            );
          })}
        </div>

        <div className="mx-3 mt-2 grid shrink-0 gap-2 border-t border-slate-100 pt-3">
            {quickLinks.map((item) => {
              const Icon = item.icon;
              return (
                <Link key={item.title} to={item.href} className="flex items-center gap-2 rounded-lg bg-slate-50 px-3 py-2 transition hover:bg-red-50">
                  <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-white text-primary shadow-sm">
                    <Icon className="h-4 w-4" />
                  </span>
                  <span className="min-w-0">
                    <span className="block text-sm font-bold text-slate-800">{item.title}</span>
                    <span className="block truncate text-xs font-medium text-slate-500">{item.text}</span>
                  </span>
                </Link>
              );
            })}
        </div>
      </nav>

      {activeCategory && (
        <div className={`${compact ? 'absolute left-[274px] top-0 h-[min(640px,calc(100vh-96px))] w-[min(1000px,calc(100vw-322px))]' : 'h-[560px] max-h-[calc(100vh-236px)] min-h-[360px] flex-1 md:h-[min(640px,calc(100vh-96px))] md:max-h-none'} overflow-hidden rounded-xl border border-slate-100 bg-white shadow-xl`}>
          <div className="grid h-full grid-cols-1 gap-5 overflow-y-auto p-4 sm:p-5 lg:grid-cols-[1fr_260px]">
            <div className="grid grid-cols-1 gap-x-6 gap-y-5 sm:grid-cols-2 xl:grid-cols-4">
              {panelGroups.map((group) => (
                <section key={group.title} className="min-w-0">
                  <h3 className="mb-2 text-[15px] font-bold text-slate-950">{group.title}</h3>
                  <div className="space-y-2">
                    {group.items.slice(0, 12).map((item, index) => (
                      <Link
                        key={`${group.title}-${item}`}
                        to={getMenuItemLink(activeCategory.slug, group.title, item)}
                        onClick={onNavigate}
                        className="group flex min-h-6 items-start gap-2 text-sm leading-5 text-slate-500 transition hover:text-primary"
                      >
                        <span className="min-w-0 break-words">{item}</span>
                        {index === 0 && group.title === 'Theo nhu cầu' && (
                          <span className="mt-0.5 shrink-0 rounded bg-primary px-1 py-0.5 text-[9px] font-bold leading-none text-white">
                            HOT
                          </span>
                        )}
                      </Link>
                    ))}
                  </div>
                </section>
              ))}
            </div>

            <section className="min-w-0 border-t border-slate-100 pt-5 lg:border-l lg:border-t-0 lg:pl-6 lg:pt-0">
              <h3 className="mb-3 flex items-center gap-2 text-[15px] font-bold text-slate-950">
                Sản phẩm nổi bật <Flame className="h-4 w-4 text-orange-500" />
              </h3>
              <div className="space-y-2">
                {(activeCategory.featuredProducts || []).slice(0, 10).map((product) => (
                  <Link
                    key={product.id}
                    to={`/product/${product.id}`}
                    onClick={onNavigate}
                    className="block rounded-md border border-slate-100 px-3 py-2 text-sm font-medium leading-5 text-slate-700 transition hover:border-primary hover:text-primary"
                  >
                    {product.name}
                  </Link>
                ))}
              </div>
            </section>
          </div>
        </div>
      )}
    </div>
  );
}
