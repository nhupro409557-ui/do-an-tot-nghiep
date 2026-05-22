import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useCart } from '../context/CartContext';
import { Trash2, Minus, Plus, ChevronLeft } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

export default function CartPage() {
  const { items, updateQuantity, removeFromCart, totalPrice } = useCart();
  const navigate = useNavigate();

  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 px-4 min-h-[60vh]">
        <div className="text-8xl mb-6">🛒</div>
        <p className="text-gray-800 font-bold mb-2 text-2xl font-display">Giỏ hàng của bạn đang trống.</p>
        <p className="text-gray-500 mb-8 text-sm">Hãy chọn thêm sản phẩm để mua sắm nhé!</p>
        <Link to="/" className="bg-[#d70018] hover:bg-[#c00015] text-white px-8 py-3.5 rounded-xl font-bold transition-colors w-full max-w-sm text-center shadow-md">
          Quay lại trang chủ
        </Link>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-[700px]">
      <div className="flex items-center gap-4 mb-6">
        <button onClick={() => navigate(-1)} className="text-gray-600 hover:text-gray-900">
          <ChevronLeft className="w-6 h-6" />
        </button>
        <h1 className="text-xl font-bold text-gray-800 flex-1 text-center pr-6">Giỏ hàng của bạn</h1>
      </div>

      <div className="bg-white rounded-2xl shadow-sm p-4 md:p-6 mb-6">
        <AnimatePresence mode="popLayout">
          {items.map((item) => (
            <motion.div 
              layout
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9, transition: { duration: 0.2 } }}
              key={item.productId} 
              className="flex gap-4 py-4 border-b border-gray-100 last:border-0 last:pb-0 first:pt-0"
            >
              <img src={item.imageUrl} alt={item.name} className="w-24 h-24 object-contain border border-gray-100 rounded-xl p-2" />
              
              <div className="flex-1 flex flex-col justify-between">
                <div>
                  <h3 className="text-sm font-bold text-gray-800 leading-snug mb-1">{item.name}</h3>
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-[#d70018] font-bold">{item.price.toLocaleString('vi-VN')}đ</span>
                    {item.originalPrice && (
                      <del className="text-xs text-gray-400">{item.originalPrice.toLocaleString('vi-VN')}đ</del>
                    )}
                  </div>
                </div>

                <div className="flex items-center justify-between mt-auto">
                  <div className="flex items-center border border-gray-200 rounded-lg overflow-hidden h-8">
                    <button onClick={() => updateQuantity(item.productId, item.quantity - 1)} className="px-3 bg-gray-50 hover:bg-gray-100 h-full flex items-center justify-center transition-colors text-gray-600">
                       <Minus className="w-3.5 h-3.5" />
                    </button>
                    <input type="number" value={item.quantity} readOnly className="w-10 text-center text-sm font-medium outline-none bg-white h-full border-x border-gray-200 pointer-events-none" />
                    <button onClick={() => updateQuantity(item.productId, item.quantity + 1)} className="px-3 bg-gray-50 hover:bg-gray-100 h-full flex items-center justify-center transition-colors text-gray-600">
                       <Plus className="w-3.5 h-3.5" />
                    </button>
                  </div>
                  
                  <button onClick={() => removeFromCart(item.productId)} className="text-gray-400 hover:text-red-500 transition-colors flex items-center gap-1 text-xs font-medium">
                    <Trash2 className="w-4 h-4" /> Xóa
                  </button>
                </div>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      <div className="bg-white rounded-2xl shadow-sm p-4 md:p-6 sticky bottom-[72px] md:bottom-4 border border-gray-100">
        <div className="flex justify-between text-sm text-gray-600 mb-2">
          <span>Tạm tính ({items.reduce((acc, curr) => acc + curr.quantity, 0)} sản phẩm):</span>
          <span className="font-medium text-gray-800">{totalPrice.toLocaleString('vi-VN')}đ</span>
        </div>
        <div className="flex justify-between items-end border-t border-gray-100 pt-4 mb-5">
          <span className="font-bold text-gray-800">Tổng tiền:</span>
          <span className="text-xl font-bold text-[#d70018]">{totalPrice.toLocaleString('vi-VN')}đ</span>
        </div>
        
        <Link to="/checkout" className="block w-full bg-[#d70018] hover:bg-[#c00015] text-white py-4 rounded-xl font-bold text-center transition-colors shadow-md">
           TIẾN HÀNH ĐẶT HÀNG
        </Link>
      </div>

    </div>
  );
}
