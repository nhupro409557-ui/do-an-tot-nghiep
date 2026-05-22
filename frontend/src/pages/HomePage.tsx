import React, { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { apiDb } from '../services/apiDb';
import { ProductCard } from '../components/product/ProductCard';
import { ProductSkeleton } from '../components/product/ProductSkeleton';
import { HomeBanner } from '../components/home/HomeBanner';
import { FlashSale } from '../components/home/FlashSale';

export default function HomePage() {
  const [products, setProducts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchParams] = useSearchParams();
  const searchQuery = searchParams.get('search');

  useEffect(() => {
    const fetchProducts = async () => {
      try {
        setLoading(true);
        let data = await apiDb.listProducts();
        if (searchQuery) {
          data = data.filter((p: any) => p.name.toLowerCase().includes(searchQuery.toLowerCase()));
        }
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
      {/* Khu vực Banner và Menu */}
      <HomeBanner />

      {/* Khu vực Flash Sale */}
      <FlashSale />

      {/* Khu vực Sản phẩm nổi bật */}
      <div className="mt-8">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl md:text-2xl font-bold uppercase text-gray-800 font-display">
            🌟 Đề Xuất Cho Bạn
          </h2>
          <Link to="/search" className="text-primary font-bold text-sm tracking-tight hover:underline">Xem Tất Cả &rsaquo;</Link>
        </div>
        
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-3 md:gap-4">
          {loading ? (
            Array.from({ length: 10 }).map((_, i) => <ProductSkeleton key={i} />)
          ) : products.map((p, i) => (
            <ProductCard key={p.id} p={p} index={i} />
          ))}
        </div>

        {!loading && products.length === 0 && (
          <div className="py-16 text-center text-slate-500 bg-white rounded-xl border border-slate-100">
            Chưa có sản phẩm để hiển thị.
          </div>
        )}
      </div>
    </div>
  );
}
