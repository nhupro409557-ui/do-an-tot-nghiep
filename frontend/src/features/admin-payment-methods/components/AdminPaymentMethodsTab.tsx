import React, { useEffect, useState } from 'react';
import { CreditCard, Edit2, ShieldAlert, CheckCircle, AlertCircle } from 'lucide-react';
import { adminPaymentMethodsApi, type PaymentMethodData } from '../services/adminPaymentMethodsApi';
import { notifyAdmin } from '../../admin-shell/utils/adminNotice';

type AdminPaymentMethodsTabProps = Record<string, any>;

export default function AdminPaymentMethodsTab(props: AdminPaymentMethodsTabProps) {
  const [methods, setMethods] = useState<PaymentMethodData[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingMethod, setEditingMethod] = useState<PaymentMethodData | null>(null);
  
  // Form states
  const [isActive, setIsActive] = useState(true);
  const [maintenanceMessage, setMaintenanceMessage] = useState('');
  const [startsAt, setStartsAt] = useState('');
  const [endsAt, setEndsAt] = useState('');

  const loadData = async () => {
    setLoading(true);
    try {
      const data = await adminPaymentMethodsApi.adminListPaymentMethods();
      setMethods(data);
    } catch (err) {
      console.error(err);
      notifyAdmin('Không thể tải danh sách phương thức thanh toán.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadData();
  }, []);

  const handleEdit = (method: PaymentMethodData) => {
    setEditingMethod(method);
    setIsActive(method.is_active);
    setMaintenanceMessage(method.maintenance_message || '');
    setStartsAt(method.maintenance_starts_at ? method.maintenance_starts_at.slice(0, 16) : '');
    setEndsAt(method.maintenance_ends_at ? method.maintenance_ends_at.slice(0, 16) : '');
  };

  const handleCancel = () => {
    setEditingMethod(null);
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!editingMethod) return;

    try {
      await adminPaymentMethodsApi.adminUpdatePaymentMethod(editingMethod.id, {
        is_active: isActive,
        maintenance_message: maintenanceMessage || null,
        maintenance_starts_at: startsAt || null,
        maintenance_ends_at: endsAt || null,
      });
      notifyAdmin('Đã cập nhật cấu hình phương thức thanh toán thành công.');
      setEditingMethod(null);
      void loadData();
    } catch (err) {
      console.error(err);
      notifyAdmin('Có lỗi xảy ra khi lưu cấu hình.');
    }
  };

  // Helper checking if currently in maintenance window
  const isCurrentlyInMaintenance = (method: PaymentMethodData) => {
    if (!method.maintenance_starts_at || !method.maintenance_ends_at) return false;
    const now = new Date();
    const start = new Date(method.maintenance_starts_at);
    const end = new Date(method.maintenance_ends_at);
    return now >= start && now <= end;
  };

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <span className="text-sm font-semibold text-slate-500">Đang tải dữ liệu phương thức thanh toán...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Edit Form (if editing) */}
      {editingMethod && (
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="mb-4 flex items-center gap-2 border-b border-slate-100 pb-3">
            <CreditCard className="h-5 w-5 text-red-600" />
            <h2 className="text-base font-bold text-slate-900">
              Cấu hình phương thức: <span className="text-red-600">{editingMethod.name} ({editingMethod.code})</span>
            </h2>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              {/* Active Toggle */}
              <div>
                <label className="mb-1.5 block text-xs font-bold uppercase text-slate-500">Trạng thái hoạt động</label>
                <div className="flex items-center gap-3">
                  <label className="relative inline-flex cursor-pointer items-center">
                    <input
                      type="checkbox"
                      checked={isActive}
                      onChange={(event) => setIsActive(event.target.checked)}
                      className="peer sr-only"
                    />
                    <div className="peer h-6 w-11 rounded-full bg-slate-200 after:absolute after:left-[2px] after:top-[2px] after:h-5 after:w-5 after:rounded-full after:border after:border-gray-300 after:bg-white after:transition-all after:content-[''] peer-checked:bg-red-600 peer-checked:after:translate-x-full peer-checked:after:border-white peer-focus:outline-none"></div>
                  </label>
                  <span className="text-sm font-bold text-slate-700">
                    {isActive ? 'Kích hoạt (Cho phép thanh toán)' : 'Tắt (Khóa thanh toán)'}
                  </span>
                </div>
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              {/* Maintenance Start Time */}
              <label className="block">
                <span className="mb-1.5 block text-xs font-bold uppercase text-slate-500">Bắt đầu bảo trì (Không bắt buộc)</span>
                <input
                  type="datetime-local"
                  value={startsAt}
                  onChange={(event) => setStartsAt(event.target.value)}
                  className="h-10 w-full rounded-xl border border-slate-200 px-3 text-sm text-slate-800 outline-none transition focus:border-red-500"
                />
              </label>

              {/* Maintenance End Time */}
              <label className="block">
                <span className="mb-1.5 block text-xs font-bold uppercase text-slate-500">Kết thúc bảo trì (Không bắt buộc)</span>
                <input
                  type="datetime-local"
                  value={endsAt}
                  onChange={(event) => setEndsAt(event.target.value)}
                  className="h-10 w-full rounded-xl border border-slate-200 px-3 text-sm text-slate-800 outline-none transition focus:border-red-500"
                />
              </label>
            </div>

            {/* Maintenance Message */}
            <label className="block">
              <span className="mb-1.5 block text-xs font-bold uppercase text-slate-500">Thông báo lỗi / Thông báo bảo trì hiển thị với khách hàng</span>
              <textarea
                value={maintenanceMessage}
                onChange={(event) => setMaintenanceMessage(event.target.value)}
                placeholder="Ví dụ: Cổng thanh toán MoMo đang bảo dưỡng định kỳ từ 1h đến 3h sáng. Quý khách vui lòng chọn phương thức COD hoặc ZaloPay."
                className="min-h-20 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-800 outline-none transition focus:border-red-500"
              />
            </label>

            {/* Buttons */}
            <div className="flex justify-end gap-2 border-t border-slate-100 pt-3">
              <button
                type="button"
                onClick={handleCancel}
                className="inline-flex h-10 items-center justify-center rounded-xl border border-slate-200 bg-white px-5 text-sm font-bold text-slate-700 transition hover:bg-slate-50"
              >
                Hủy
              </button>
              <button
                type="submit"
                className="inline-flex h-10 items-center justify-center rounded-xl bg-red-600 px-5 text-sm font-bold text-white shadow-sm transition hover:bg-red-700"
              >
                Lưu cấu hình
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Methods List Cards (Rich Aesthetics) */}
      <div className="grid gap-4 md:grid-cols-2">
        {methods.map((method) => {
          const currentlyMaintenance = isCurrentlyInMaintenance(method);
          const hasTimeConfig = Boolean(method.maintenance_starts_at && method.maintenance_ends_at);
          
          return (
            <div
              key={method.id}
              className={`rounded-xl border p-5 transition ${
                !method.is_active
                  ? 'border-slate-200 bg-slate-50 opacity-80'
                  : currentlyMaintenance
                  ? 'border-amber-200 bg-amber-50/30'
                  : 'border-slate-200 bg-white hover:border-slate-300'
              }`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-2">
                  <CreditCard className={`h-5 w-5 ${!method.is_active ? 'text-slate-400' : 'text-slate-900'}`} />
                  <span className="font-mono text-xs font-bold text-slate-400">{method.code}</span>
                </div>

                {/* Status Badges */}
                <div className="flex items-center gap-1.5">
                  {!method.is_active ? (
                    <span className="inline-flex items-center gap-1 rounded bg-slate-100 px-2 py-0.5 text-[10px] font-bold text-slate-600">
                      <ShieldAlert className="h-3 w-3" /> Đã tắt
                    </span>
                  ) : currentlyMaintenance ? (
                    <span className="inline-flex items-center gap-1 rounded bg-amber-100 px-2 py-0.5 text-[10px] font-bold text-amber-800">
                      <AlertCircle className="h-3 w-3" /> Đang bảo trì
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 rounded bg-emerald-100 px-2 py-0.5 text-[10px] font-bold text-emerald-800">
                      <CheckCircle className="h-3 w-3" /> Hoạt động
                    </span>
                  )}
                </div>
              </div>

              {/* Title & Desc */}
              <div className="mt-3">
                <h3 className="text-sm font-extrabold text-slate-900">{method.name}</h3>
                <p className="mt-1 text-xs text-slate-500">{method.description}</p>
              </div>

              {/* Maintenance Time Info */}
              {hasTimeConfig && (
                <div className="mt-3 rounded-lg bg-slate-100/70 p-2.5 text-xs text-slate-600">
                  <div className="font-semibold text-slate-700">Lịch bảo trì cấu hình:</div>
                  <div className="mt-1">
                    Bắt đầu: {new Date(method.maintenance_starts_at!).toLocaleString('vi-VN')}
                  </div>
                  <div>
                    Kết thúc: {new Date(method.maintenance_ends_at!).toLocaleString('vi-VN')}
                  </div>
                </div>
              )}

              {/* Maintenance message preview */}
              {method.maintenance_message && (
                <div className="mt-2 text-xs text-rose-600 font-medium">
                  <strong>Thông báo:</strong> "{method.maintenance_message}"
                </div>
              )}

              {/* Edit button */}
              <div className="mt-4 flex justify-end border-t border-slate-100 pt-3">
                <button
                  type="button"
                  onClick={() => handleEdit(method)}
                  className="inline-flex items-center gap-1.5 text-xs font-bold text-slate-600 hover:text-slate-900"
                >
                  <Edit2 className="h-3 w-3" /> Cấu hình
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
