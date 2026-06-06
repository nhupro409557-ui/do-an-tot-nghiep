import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { publicApi } from '../../../services/publicApi';
import ProductDetail from '../components/ProductDetail';
import { useViewTracker } from '../../../hooks/useViewTracker';

export default function ProductPage() {
  const { id } = useParams<{ id: string }>();
  const [product, setProduct] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  useViewTracker(product?.id || id);

  useEffect(() => {
    if (!id) return;
    publicApi.getProduct(id)
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
