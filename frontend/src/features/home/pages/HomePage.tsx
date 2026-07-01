import React, { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { ArrowRight, PackageSearch, Sparkles } from 'lucide-react';
import { publicApi } from '../../../services/publicApi';
import { ProductCard } from '../../products/components/ProductCard';
import { ProductSkeleton } from '../../products/components/ProductSkeleton';
import { HomeBanner } from '../components/HomeBanner';
import { FlashSale } from '../components/FlashSale';

export default function HomePage() {
  const [products, setProducts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchParams] = useSearchParams();
  const searchQuery = searchParams.get('search');

  useEffect(() => {
    const fetchProducts = async () => {
      try {
        setLoading(true);
        const data = await publicApi.listProducts({
          q: searchQuery || undefined,
          featured: searchQuery ? undefined : true,
          limit: 10,
        });
        setProducts(data);
      } catch (err) {
        console.error("Failed to load products", err);
      } finally {
        setLoading(false);
      }
    };
    fetchProducts();
  }, [searchQuery]);

  return (
    <div className="w-full">
      <HomeBanner />

      <FlashSale />

      <section className="mt-8">
        <div className="mb-4 flex items-end justify-between gap-3">
          <div>
            <div className="mb-1 inline-flex items-center gap-2 rounded-full border border-red-100 bg-red-50 px-3 py-1 text-xs font-bold uppercase text-primary">
              <Sparkles className="h-3.5 w-3.5" />
              Gợi ý hôm nay
            </div>
            <h2 className="text-xl font-extrabold uppercase tracking-tight text-slate-950 md:text-2xl">
              Đề xuất cho bạn
            </h2>
          </div>
          <Link
            to="/search"
            className="inline-flex h-10 shrink-0 items-center gap-1.5 rounded-lg border border-red-100 px-3 text-sm font-bold text-primary transition hover:border-primary hover:bg-red-50"
          >
            Xem tất cả
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-3 md:gap-4">
          {loading ? (
            Array.from({ length: 10 }).map((_, index) => <ProductSkeleton key={`home-product-skeleton-${index + 1}`} />)
          ) : products.map((p, i) => (
            <ProductCard key={p.id} p={p} index={i} />
          ))}
        </div>

        {!loading && products.length === 0 && (
          <div className="flex flex-col items-center justify-center rounded-xl border border-slate-100 bg-white px-4 py-16 text-center text-slate-500">
            <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-slate-100 text-slate-500">
              <PackageSearch className="h-7 w-7" />
            </div>
            <h3 className="text-base font-bold text-slate-900">Chưa có sản phẩm để hiển thị</h3>
            <p className="mt-2 max-w-sm text-sm leading-6">
              Hãy thử xem toàn bộ sản phẩm hoặc quay lại sau khi hệ thống cập nhật gợi ý mới.
            </p>
            <Link
              to="/products"
              className="mt-5 inline-flex h-10 items-center justify-center rounded-lg bg-primary px-4 text-sm font-bold text-white"
            >
              Xem sản phẩm
            </Link>
          </div>
        )}
      </section>
    </div>
  );
}
