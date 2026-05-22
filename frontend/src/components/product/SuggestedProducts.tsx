import React, { useEffect, useState } from 'react';
import { apiDb } from '../../services/apiDb';
import { ProductCard } from './ProductCard';
import { Sparkles } from 'lucide-react';

export function SuggestedProducts({ currentProductId, category }: { currentProductId?: string, category?: string }) {
  const [suggested, setSuggested] = useState<any[]>([]);

  useEffect(() => {
    apiDb.listProducts()
      .then(products => {
      const qs = category ? products.filter((product: any) => product.categorySlug === category) : products;
      
      const data = qs.filter((p: any) => p.id !== currentProductId).slice(0, 4);
      setSuggested(data);
      })
      .catch(err => {
      console.error(err);
      setSuggested([]);
      });
  }, [currentProductId, category]);

  if (suggested.length === 0) return null;

  return (
    <div className="mt-8 rounded-xl border border-gray-100 bg-white p-5 shadow-sm">
      <div className="mb-5 flex items-center gap-2">
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-red-50 text-primary">
          <Sparkles className="h-4 w-4" />
        </span>
        <h2 className="text-lg font-bold text-gray-900">Sản phẩm tương tự</h2>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {suggested.map((p, index) => (
          <ProductCard key={p.id} p={p} index={index} />
        ))}
      </div>
    </div>
  );
}
