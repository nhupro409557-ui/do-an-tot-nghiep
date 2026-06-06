import React from 'react';
import { Link } from 'react-router-dom';

export default function NotFoundPage() {
  return (
    <div className="min-h-[70vh] flex flex-col items-center justify-center p-4 text-center">
      <div className="text-9xl font-black text-gray-100 font-mono mb-4 drop-shadow-sm">404</div>
      <h1 className="text-3xl font-bold text-gray-900 mb-2 font-display">Không tìm thấy trang</h1>
      <p className="text-gray-500 mb-8 max-w-md text-sm">
        Có vẻ như thiết bị hoặc trang bạn đang tìm kiếm không tồn tại, đã bị gỡ bỏ hoặc tạm thời không truy cập được.
      </p>
      <div className="flex gap-4">
        <Link to="/" className="px-6 py-2.5 bg-primary text-white font-bold rounded-lg hover:bg-red-700 transition shadow-sm">
          Về Trang Chủ
        </Link>
        <Link to="/category/all" className="px-6 py-2.5 bg-gray-100 text-gray-700 font-bold rounded-lg hover:bg-gray-200 transition">
          Xem Sản Phẩm
        </Link>
      </div>
    </div>
  );
}
