import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { apiDb } from '../services/apiDb';
import ProductDetail from '../components/product/ProductDetail';

export default function ProductPage() {
  const { id } = useParams<{ id: string }>();
  const [product, setProduct] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    apiDb.getProduct(id)
      .then(setProduct)
      .catch(() => setProduct(null))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <div className="flex items-center justify-center p-20">
        <div className="w-8 h-8 rounded-full border-4 border-[#d70018] border-t-transparent animate-spin"></div>
      </div>
    );
  }

  return (
    <div className="w-full">
      <ProductDetail product={product} />
    </div>
  );
}
