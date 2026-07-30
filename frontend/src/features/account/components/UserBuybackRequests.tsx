import { useEffect, useState } from 'react';
import { Smartphone } from 'lucide-react';
import { usedProductsApi } from '../../used-products/services/usedProductsApi';
import { Link } from 'react-router-dom';

const STATUS_MAP: Record<string, { label: string; color: string }> = {
  SUBMITTED: { label: 'Đã gửi yêu cầu', color: 'bg-blue-100 text-blue-700' },
  RECEIVED: { label: 'Đã tiếp nhận', color: 'bg-purple-100 text-purple-700' },
  INSPECTING: { label: 'Đang kiểm tra', color: 'bg-amber-100 text-amber-700' },
  APPRAISED: { label: 'Đã định giá', color: 'bg-emerald-100 text-emerald-700' },
  ACCEPTED: { label: 'Đã chấp nhận', color: 'bg-green-100 text-green-700' },
  REPAIR_REQUIRED: { label: 'Cần sửa chữa', color: 'bg-orange-100 text-orange-700' },
  REJECTED: { label: 'Từ chối thu mua', color: 'bg-red-100 text-red-700' },
  CANCELLED: { label: 'Đã huỷ', color: 'bg-slate-100 text-slate-700' },
};

export default function UserBuybackRequests() {
  const [loading, setLoading] = useState(true);
  const [requests, setRequests] = useState<any[]>([]);

  useEffect(() => {
    let active = true;
    usedProductsApi.listBuybackRequests()
      .then((res: any) => {
        if (active) setRequests(res || []);
      })
      .catch(() => {})
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, []);

  if (loading) {
    return <div className="py-10 text-center"><div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-slate-200 border-t-emerald-600"></div></div>;
  }

  if (requests.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-slate-300 bg-slate-50 py-16 px-4 text-center">
        <Smartphone className="mb-4 h-12 w-12 text-slate-300" />
        <h3 className="text-lg font-medium text-slate-900">Bạn chưa có yêu cầu thu cũ nào</h3>
        <p className="mt-1 text-sm text-slate-500">Định giá máy cũ nhanh chóng để lên đời máy mới.</p>
        <Link to="/thu-cu-doi-moi" className="mt-6 rounded-md bg-emerald-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-emerald-700">Tạo yêu cầu ngay</Link>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {requests.map(req => {
        const statusObj = STATUS_MAP[req.status] || { label: req.status, color: 'bg-slate-100 text-slate-700' };
        return (
          <div key={req.id} className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-100 pb-4">
              <div>
                <div className="text-sm font-medium text-slate-900">{req.productName}</div>
                <div className="text-xs text-slate-500">Mã hồ sơ: {req.requestCode}</div>
              </div>
              <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${statusObj.color}`}>
                {statusObj.label}
              </span>
            </div>
            
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <div>
                <span className="block text-xs font-medium text-slate-500">Số IMEI</span>
                <span className="block text-sm font-mono text-slate-900">{req.imei}</span>
              </div>
              <div>
                <span className="block text-xs font-medium text-slate-500">Giá đề xuất ban đầu</span>
                <span className="block text-sm font-semibold text-emerald-600">{req.expectedPrice ? new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(req.expectedPrice) : 'Chưa nhập'}</span>
              </div>
              {req.proposedAcquisitionPrice && (
                <div className="sm:col-span-2">
                  <span className="block text-xs font-medium text-emerald-600">Giá thu mua cuối cùng</span>
                  <span className="block text-lg font-bold text-emerald-700">{new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(req.proposedAcquisitionPrice)}</span>
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
