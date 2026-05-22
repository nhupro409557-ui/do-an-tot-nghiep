import React, { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { ChevronRight, Flame } from 'lucide-react';
import { useCatalog } from '../../hooks/useCatalog';

type Props = {
  compact?: boolean;
  onNavigate?: () => void;
};

export function CategoryMegaMenu({ compact = false, onNavigate }: Props) {
  const { categories, loading } = useCatalog();
  const [activeId, setActiveId] = useState<string | null>(null);

  const activeCategory = useMemo(
    () => categories.find(category => category.id === activeId || category.slug === activeId) || null,
    [activeId, categories]
  );

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

  const panelGroups = activeCategory?.groups.length
    ? activeCategory.groups
    : [{ title: 'Sản phẩm nổi bật', items: [] }];

  return (
    <div
      onMouseLeave={() => setActiveId(null)}
      className={`relative flex overflow-visible text-slate-900 ${
        compact ? 'w-[274px]' : 'w-full'
      }`}
    >
      <nav className="w-[274px] shrink-0 overflow-hidden rounded-xl border border-slate-100 bg-white py-2 shadow-xl">
        {categories.map((category) => {
          const Icon = category.icon;
          const isActive = activeCategory?.id === category.id;

          return (
            <Link
              key={category.id}
              to={`/products/${category.slug}`}
              onMouseEnter={() => setActiveId(category.id)}
              onFocus={() => setActiveId(category.id)}
              onClick={onNavigate}
              className={`flex h-[50px] items-center justify-between px-5 text-[15px] font-semibold transition ${
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
      </nav>

      {activeCategory && (
      <div className={`${compact ? 'absolute left-[282px] top-0 w-[min(900px,calc(100vw-330px))]' : 'flex-1'} min-h-[480px] rounded-xl border border-slate-100 bg-white p-5 shadow-xl`}>
        <div className="grid grid-cols-1 gap-7 lg:grid-cols-3">
          <div className="lg:col-span-2 grid grid-cols-1 md:grid-cols-2 gap-7">
            {panelGroups.map((group) => (
              <section key={group.title}>
                <h3 className="mb-3 text-base font-bold text-slate-950">{group.title}</h3>
                {group.items.length ? (
                  <div className="flex flex-wrap gap-3">
                    {group.items.slice(0, 12).map((item, index) => (
                      <Link
                        key={`${group.title}-${item}`}
                        to={`/search?q=${encodeURIComponent(item)}&category=${activeCategory.slug}`}
                        onClick={onNavigate}
                        className="relative min-h-11 rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-900 transition hover:border-primary hover:text-primary"
                      >
                        {item}
                        {index === 0 && (
                          <span className="absolute -right-2 -top-2 rounded bg-primary px-1.5 py-0.5 text-[9px] font-bold text-white">
                            Hot
                          </span>
                        )}
                      </Link>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-slate-400">Chưa có dữ liệu cho nhóm này.</p>
                )}
              </section>
            ))}
          </div>

          <div className="space-y-7">
            <section>
              <h3 className="mb-3 text-base font-bold text-slate-950">Chọn theo thương hiệu</h3>
              {activeCategory.brands.length > 0 ? (
                <div className="grid grid-cols-2 gap-3">
                  {activeCategory.brands.slice(0, 12).map((brand) => (
                    <Link
                      key={brand}
                      to={`/products/${activeCategory.slug}?brand=${encodeURIComponent(brand)}`}
                      onClick={onNavigate}
                      className="flex h-12 items-center justify-center rounded-lg border border-slate-200 bg-white px-3 text-sm font-black tracking-wide transition hover:border-primary hover:text-primary"
                    >
                      {brand}
                    </Link>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-slate-400">Chưa có thương hiệu trong database.</p>
              )}
            </section>

            <section>
              <h3 className="mb-3 flex items-center gap-2 text-base font-bold text-slate-950">
                Sản phẩm nổi bật <Flame className="h-4 w-4 text-orange-500" />
              </h3>
              <div className="flex flex-wrap gap-3">
                {(activeCategory.featuredProducts || []).slice(0, 8).map((product) => (
                  <Link
                    key={product.name}
                    to={`/product/${product.id}`}
                    onClick={onNavigate}
                    className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium transition hover:border-primary hover:text-primary"
                  >
                    {product.name}
                  </Link>
                ))}
              </div>
            </section>
          </div>
        </div>
      </div>
      )}
    </div>
  );
}
