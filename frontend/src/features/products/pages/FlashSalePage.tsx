import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Zap } from 'lucide-react';
import { publicApi } from '../../../services/publicApi';
import { FlashSaleCountdown } from '../../home/components/FlashSaleCountdown';
import { ProductCard } from '../components/ProductCard';
import { ProductSkeleton } from '../components/ProductSkeleton';

const getNearestEndTime = (products: any[]) => products.reduce<string | undefined>((nearest, product) => {
  const endsAt = product.flashSale?.endsAt;
  if (!endsAt) return nearest;
  if (!nearest) return endsAt;
  return new Date(endsAt).getTime() < new Date(nearest).getTime() ? endsAt : nearest;
}, undefined);

export default function FlashSalePage() {
  const [products, setProducts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    publicApi.listProducts({ flashSale: true })
      .then(setProducts)
      .catch((error) => {
        console.error(error);
        setProducts([]);
      })
      .finally(() => setLoading(false));
  }, []);

  const nearestEndTime = useMemo(() => getNearestEndTime(products), [products]);

  return (
    <div className="container mx-auto max-w-7xl px-4 py-6">
      <div className="mb-5 flex items-center gap-2 text-sm text-slate-500">
        <Link to="/" className="hover:text-primary">Trang chủ</Link>
        <span>/</span>
        <span className="font-bold text-slate-900">Flash Sale</span>
      </div>

      <section className="mb-6 overflow-hidden rounded-2xl bg-gradient-to-r from-red-700 via-primary to-orange-500 p-5 shadow-lg md:p-7">
        <div className="flex flex-col justify-between gap-5 md:flex-row md:items-center">
          <div className="text-white">
            <div className="mb-2 flex items-center gap-2">
              <Zap className="h-7 w-7 fill-current" />
              <h1 className="text-3xl font-black italic tracking-wider md:text-4xl">FLASH SALE</h1>
            </div>
            <p className="font-medium text-white/90">Sản phẩm đang giảm giá trong thời gian giới hạn.</p>
          </div>
          <FlashSaleCountdown endsAt={nearestEndTime} />
        </div>
      </section>

      <div className="mb-4 flex items-end justify-between gap-3">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Sản phẩm đang Flash Sale</h2>
          {!loading && <p className="text-sm text-slate-500">{products.length} sản phẩm đang được giảm giá</p>}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-3 xl:grid-cols-4">
        {loading ? (
          Array.from({ length: 8 }).map((_, index) => <ProductSkeleton key={index} />)
        ) : products.length > 0 ? (
          products.map((product, index) => <ProductCard key={product.id} p={product} index={index} />)
        ) : (
          <div className="col-span-full rounded-xl border border-slate-100 bg-white py-20 text-center text-slate-500">
            Hiện chưa có sản phẩm nào đang trong chương trình Flash Sale.
          </div>
        )}
      </div>
    </div>
  );
}
