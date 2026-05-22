import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { apiDb } from '../services/apiDb';
import { ImageWithFallback } from '../components/ui/ImageWithFallback';
import { motion, AnimatePresence } from 'motion/react';

// Danh sách các thông số cần hiển thị
const specKeys = [
  { key: 'screenSize', label: 'Màn hình' },
  { key: 'processor', label: 'Vi xử lý (CPU)' },
  { key: 'ram', label: 'Bộ nhớ RAM' },
  { key: 'storage', label: 'Ổ cứng' },
  { key: 'weight', label: 'Trọng lượng' },
  { key: 'battery', label: 'Pin' },
];

export default function ComparePage() {
  const location = useLocation();
  const searchParams = new URLSearchParams(location.search);
  const initialProductId = searchParams.get('product');

  const [products, setProducts] = useState<any[]>([]);
  const [selectedProductIds, setSelectedProductIds] = useState<string[]>(initialProductId ? [initialProductId] : []);
  const [loading, setLoading] = useState(true);
  const [showSelector, setShowSelector] = useState(false);

  useEffect(() => {
    apiDb.listProducts().then(setProducts).catch(() => setProducts([]));
    setLoading(false);
  }, []);

  const handleRemove = (id: string) => {
    setSelectedProductIds(prev => prev.filter(pid => pid !== id));
  };

  const handleAddProduct = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const val = e.target.value;
    if (val && !selectedProductIds.includes(val) && selectedProductIds.length < 3) {
      setSelectedProductIds([...selectedProductIds, val]);
      setShowSelector(false);
    }
  };

  const compareList = selectedProductIds.map(id => products.find(p => p.id === id)).filter(Boolean);

  // Lấy danh sách keys tổng hợp nếu có thông số ngoài specKeys mặc định (tuỳ chọn)
  const getAllSpecKeys = () => {
    const defaultKeys = specKeys.map(s => s.key);
    const addedKeys = new Set<string>();
    compareList.forEach(p => {
      if (p?.specs) {
        Object.keys(p.specs).forEach(k => {
          if (!defaultKeys.includes(k)) addedKeys.add(k);
        });
      }
    });
    return [...specKeys, ...Array.from(addedKeys).map(k => ({ key: k, label: k.charAt(0).toUpperCase() + k.slice(1) }))];
  };

  const currentSpecKeys = getAllSpecKeys();

  return (
    <div className="max-w-7xl mx-auto p-4 md:p-8 min-h-screen bg-gray-50">
      <div className="mb-8 flex flex-col md:flex-row justify-between items-start md:items-end gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2 font-display">So sánh sản phẩm</h1>
          <p className="text-gray-500 font-mono text-sm">So sánh chi tiết thông số kỹ thuật ({compareList.length}/3 sản phẩm)</p>
        </div>
        {compareList.length < 3 && (
          <div className="relative">
             {!showSelector ? (
                <button 
                  onClick={() => setShowSelector(true)}
                  className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-red-700 transition font-bold shadow-sm"
                >
                  + Thêm sản phẩm
                </button>
             ) : (
                <select 
                  className="px-4 py-2 bg-white border border-gray-300 pointer shadow-sm rounded-lg pr-8 focus:ring-1 focus:ring-primary outline-none"
                  value=""
                  onChange={handleAddProduct}
                  onBlur={() => setShowSelector(false)}
                  autoFocus
                >
                  <option value="" disabled>-- Chọn sản phẩm --</option>
                  {products.map(p => (
                     <option key={p.id} value={p.id} disabled={selectedProductIds.includes(p.id)}>{p.name}</option>
                  ))}
                </select>
             )}
          </div>
        )}
      </div>

      {compareList.length === 0 ? (
        <div className="text-center py-20 bg-white rounded-2xl border border-gray-200">
          <p className="text-gray-500 mb-4">Chưa có sản phẩm nào được chọn để so sánh.</p>
          <button 
             onClick={() => setShowSelector(!showSelector)}
             className="px-6 py-2.5 bg-primary text-white font-bold rounded-lg hover:bg-red-700"
          >
             Bắt đầu so sánh
          </button>
        </div>
      ) : (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-x-auto">
          <table className="w-full min-w-[800px] text-left border-collapse">
            {/* Header: Hình ảnh, Tên, Giá và Nút Xóa */}
            <thead>
              <tr>
                <th className="w-1/4 p-6 border-b border-gray-200 bg-gray-50 align-bottom">
                  <span className="text-gray-500 font-medium text-sm lg:text-base">Thông số nổi bật</span>
                </th>
                <AnimatePresence>
                  {compareList.map((product) => (
                    <motion.th 
                      key={`header-${product.id}`}
                      initial={{ opacity: 0, x: 20 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, scale: 0.9 }}
                      className="w-1/4 p-6 border-b border-gray-200 relative align-top"
                    >
                      <button 
                        onClick={() => handleRemove(product.id)}
                        className="absolute top-4 right-4 text-gray-400 hover:text-red-500 transition-colors bg-white rounded-full p-1 shadow-sm border border-gray-100"
                        title="Xóa khỏi danh sách"
                      >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                      </button>
                      <div className="h-40 w-full mb-4 flex items-center justify-center p-2">
                        <ImageWithFallback src={product.imageUrl} alt={product.name} className="max-h-full max-w-full object-contain" />
                      </div>
                      <Link to={`/product/${product.id}`} className="text-lg font-bold text-gray-900 line-clamp-2 hover:text-primary transition-colors">{product.name}</Link>
                      <p className="text-primary font-bold mt-2 text-xl">{(product.discountPrice || product.price)?.toLocaleString('vi-VN')}₫</p>
                      <button className="w-full mt-4 py-2 bg-gray-900 text-white font-bold rounded-lg hover:bg-gray-800 transition">
                        Mua ngay
                      </button>
                    </motion.th>
                  ))}
                </AnimatePresence>
                {/* Cột trống nếu chưa đủ 3 sản phẩm */}
                {Array.from({ length: 3 - compareList.length }).map((_, i) => (
                  <th key={`empty-${i}`} className="w-1/4 p-6 border-b border-gray-200 bg-gray-50/50">
                    <div className="h-full flex flex-col items-center justify-center text-gray-400 border-2 border-dashed border-gray-200 rounded-xl p-8 hover:bg-gray-100 transition cursor-pointer" onClick={() => setShowSelector(true)}>
                      <span className="text-4xl mb-2 font-light">+</span>
                      <span className="text-sm font-medium">Thêm sản phẩm</span>
                    </div>
                  </th>
                ))}
              </tr>
            </thead>

            {/* Body: Danh sách các thông số kỹ thuật */}
            <tbody>
              {currentSpecKeys.map((spec, index) => (
                <tr key={spec.key} className={index % 2 === 0 ? 'bg-white' : 'bg-gray-50/50 hover:bg-gray-50 transition-colors'}>
                  <td className="p-6 border-b border-gray-100 font-medium text-gray-600 text-sm">
                    {spec.label}
                  </td>
                  <AnimatePresence>
                    {compareList.map((product) => (
                      <motion.td 
                        key={`${product.id}-${spec.key}`}
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        // Sử dụng font-mono để các thông số điện tử dóng hàng chuẩn xác
                        className="p-6 border-b border-gray-100 font-mono text-gray-800 tracking-tight text-[13px] md:text-sm"
                      >
                        {product.specs?.[spec.key] || '-'}
                      </motion.td>
                    ))}
                  </AnimatePresence>
                  {/* Cột trống cho thông số nếu chưa đủ 3 sản phẩm */}
                  {Array.from({ length: 3 - compareList.length }).map((_, i) => (
                    <td key={`empty-spec-${i}`} className="p-6 border-b border-gray-100 bg-gray-50/50"></td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
