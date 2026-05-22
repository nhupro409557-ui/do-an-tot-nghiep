import React, { useEffect, useMemo, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { SlidersHorizontal, X } from 'lucide-react';
import { apiDb } from '../services/apiDb';
import { ProductCard } from '../components/product/ProductCard';
import { ProductSkeleton } from '../components/product/ProductSkeleton';
import { priceRanges } from '../data/categories';
import { useCatalog } from '../hooks/useCatalog';
import { analyzeProductSearch, intentFromAiParser, searchProductsByIntent } from '../utils/smartProductSearch';

export default function ProductListPage() {
  const { categoryName } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const [products, setProducts] = useState<any[]>([]);
  const [activeBrands, setActiveBrands] = useState<any[]>([]);
  const [aiIntent, setAiIntent] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const { categories, findCategoryById, loading: catalogLoading } = useCatalog();

  const keyword = searchParams.get('q') || '';
  const categoryFilter = searchParams.get('category') || categoryName || 'all';
  const brandFilter = searchParams.get('brand') || 'all';
  const priceFilter = searchParams.get('price') || 'all';
  const sort = searchParams.get('sort') || 'default';
  const selectedCategory = findCategoryById(categoryFilter);

  useEffect(() => {
    setLoading(true);
    Promise.all([apiDb.listProducts(), apiDb.listBrands().catch(() => [])])
      .then(([productData, brandData]) => {
        setProducts(productData);
        setActiveBrands(brandData);
      })
      .catch(err => {
        console.error(err);
        setProducts([]);
        setActiveBrands([]);
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    const keywordText = keyword.trim();
    if (!keywordText || categories.length === 0) {
      setAiIntent(null);
      return;
    }

    const hasComplexIntent = keywordText.split(/\s+/).length >= 5 || /sinh viên|code|lập trình|gaming|đổ lại|củ/i.test(keywordText);
    if (!hasComplexIntent) {
      setAiIntent(null);
      return;
    }

    let cancelled = false;
    const timer = window.setTimeout(() => {
      const brandsForParser = Array.from(new Set(products.map((product) => product.brand).filter(Boolean)));
      apiDb.parseSearchIntent({
        query: keywordText,
        categories,
        brands: brandsForParser,
      })
        .then((intent) => {
          if (!cancelled) setAiIntent(intent);
        })
        .catch(() => {
          if (!cancelled) setAiIntent(null);
        });
    }, 250);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [categories, keyword, products]);

  const updateFilter = (key: string, value: string) => {
    const next = new URLSearchParams(searchParams);
    if (value === 'all' || value === '') next.delete(key);
    else next.set(key, value);
    setSearchParams(next);
  };

  const brands = useMemo(() => {
    const activeBrandNames = activeBrands.map((brand) => brand.name).filter(Boolean).sort();
    if (selectedCategory?.brands.length) {
      return selectedCategory.brands.filter((brand) => activeBrandNames.includes(brand));
    }
    return activeBrandNames;
  }, [activeBrands, selectedCategory]);

  const filteredProducts = useMemo(() => {
    const range = priceRanges.find(item => item.id === priceFilter);
    const localIntent = analyzeProductSearch(keyword, products, categories);
    const intent = intentFromAiParser(keyword, aiIntent, localIntent);
    const result = searchProductsByIntent(products, intent, selectedCategory, brandFilter, range);

    return result.sort((a, b) => {
      const priceA = Number(a.price || 0);
      const priceB = Number(b.price || 0);
      if (sort === 'price-asc') return priceA - priceB;
      if (sort === 'price-desc') return priceB - priceA;
      if (sort === 'name-asc') return String(a.name || '').localeCompare(String(b.name || ''), 'vi');
      return 0;
    });
  }, [aiIntent, brandFilter, categories, keyword, priceFilter, products, selectedCategory, sort]);

  const title = keyword
    ? `Tìm kiếm: ${keyword}`
    : selectedCategory?.name || 'Tất cả sản phẩm';

  return (
    <div className="container mx-auto px-4 py-6 max-w-7xl">
      <div className="flex items-center text-sm text-slate-500 mb-5 flex-wrap gap-2">
        <Link to="/" className="hover:text-primary">Trang chủ</Link>
        <span>/</span>
        <span className="text-slate-900 font-bold">{title}</span>
      </div>

      <div className="flex flex-col lg:flex-row gap-6">
        <aside className="w-full lg:w-72 shrink-0">
          <div className="bg-white rounded-xl border border-slate-100 shadow-sm overflow-hidden">
            <div className="flex items-center gap-2 px-4 py-3 border-b border-slate-100 font-bold text-slate-800">
              <SlidersHorizontal className="h-4 w-4" />
              Bộ lọc
            </div>

            <div className="p-4 border-b border-slate-100">
              <h3 className="font-bold text-sm mb-3">Danh mục</h3>
              <div className="space-y-1">
                <button
                  onClick={() => updateFilter('category', 'all')}
                  className={`w-full text-left px-3 py-2 rounded-lg text-sm ${!selectedCategory ? 'bg-red-50 text-primary font-bold' : 'hover:bg-slate-50'}`}
                >
                  Tất cả
                </button>
                {catalogLoading && <div className="text-sm text-slate-400 px-3 py-2">Đang tải danh mục...</div>}
                {!catalogLoading && categories.map(category => (
                  <button
                    key={category.id}
                    onClick={() => updateFilter('category', category.id)}
                    className={`w-full text-left px-3 py-2 rounded-lg text-sm ${selectedCategory?.id === category.id ? 'bg-red-50 text-primary font-bold' : 'hover:bg-slate-50'}`}
                  >
                    {category.name}
                  </button>
                ))}
              </div>
            </div>

            <div className="p-4 border-b border-slate-100">
              <h3 className="font-bold text-sm mb-3">Hãng</h3>
              <div className="flex flex-wrap gap-2">
                <button onClick={() => updateFilter('brand', 'all')} className={`px-3 py-2 rounded-lg border text-sm ${brandFilter === 'all' ? 'border-primary text-primary' : 'border-slate-200'}`}>Tất cả</button>
                {brands.map(brand => (
                  <button key={brand} onClick={() => updateFilter('brand', brand)} className={`px-3 py-2 rounded-lg border text-sm ${brandFilter === brand ? 'border-primary text-primary' : 'border-slate-200'}`}>
                    {brand}
                  </button>
                ))}
              </div>
            </div>

            <div className="p-4">
              <h3 className="font-bold text-sm mb-3">Mức giá</h3>
              <div className="flex flex-wrap gap-2">
                <button onClick={() => updateFilter('price', 'all')} className={`px-3 py-2 rounded-full border text-sm ${priceFilter === 'all' ? 'border-primary text-primary' : 'border-slate-200'}`}>Tất cả</button>
                {priceRanges.map(range => (
                  <button key={range.id} onClick={() => updateFilter('price', range.id)} className={`px-3 py-2 rounded-full border text-sm ${priceFilter === range.id ? 'border-primary text-primary' : 'border-slate-200'}`}>
                    {range.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </aside>

        <section className="flex-1">
          <div className="bg-white rounded-xl border border-slate-100 shadow-sm px-4 py-3 mb-4 flex flex-col md:flex-row md:items-center justify-between gap-3">
            <div>
              <h1 className="text-2xl font-bold text-slate-900">{title}</h1>
              <p className="text-sm text-slate-500">{filteredProducts.length} sản phẩm phù hợp</p>
            </div>
            <div className="flex items-center gap-2">
              {(keyword || selectedCategory || brandFilter !== 'all' || priceFilter !== 'all') && (
                <Link to="/products" className="h-10 px-3 rounded-lg border border-slate-200 text-sm flex items-center gap-1 hover:border-primary hover:text-primary">
                  <X className="h-4 w-4" />
                  Xóa lọc
                </Link>
              )}
              <select value={sort} onChange={(e) => updateFilter('sort', e.target.value)} className="h-10 rounded-lg border border-slate-200 bg-white px-3 text-sm outline-none focus:border-primary">
                <option value="default">Sắp xếp mặc định</option>
                <option value="price-asc">Giá thấp đến cao</option>
                <option value="price-desc">Giá cao đến thấp</option>
                <option value="name-asc">Tên A-Z</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {loading ? (
              Array.from({ length: 8 }).map((_, i) => <ProductSkeleton key={i} />)
            ) : filteredProducts.length > 0 ? (
              filteredProducts.map((p, i) => <ProductCard key={p.id} p={p} index={i} />)
            ) : (
              <div className="col-span-full text-center py-20 text-slate-500 bg-white rounded-xl border border-slate-100">
                Không tìm thấy sản phẩm phù hợp.
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
