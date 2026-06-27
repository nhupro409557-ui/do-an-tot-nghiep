import { useEffect, useMemo, useState } from 'react';
import { customerCenterApi } from '../services/customerCenterApi';

const statusLabel: Record<string, string> = {
  SUBMITTED: 'Đã gửi yêu cầu',
  RECEIVED: 'Kho đã tiếp nhận',
  QC_IN_PROGRESS: 'Đang kiểm tra QC',
  QC_APPROVED: 'Đã duyệt đổi trả',
  WARRANTY_ACCEPTED: 'Đã nhận bảo hành',
  REPAIRING: 'Đang sửa chữa',
  REPLACEMENT_APPROVED: 'Đã duyệt thay máy',
  WAITING_FOR_STOCK: 'Đang chờ hàng',
  EXCHANGE_PROCESSING: 'Đang xử lý đổi máy',
  REPLACEMENT_PROCESSING: 'Đang xử lý máy thay thế',
  REFUND_PROCESSING: 'Đang hoàn tiền',
  READY_TO_RETURN: 'Sẵn sàng trả máy',
  COMPLETED: 'Hoàn tất xử lý',
  REJECTED: 'Bị từ chối',
  CANCELLED: 'Đã hủy',
  CLOSED_EXPIRED: 'Đã hết hạn',
};

const statusStyles: Record<string, { bg: string; text: string; border: string }> = {
  SUBMITTED: { bg: 'bg-slate-50', text: 'text-slate-600', border: 'border-slate-200' },
  RECEIVED: { bg: 'bg-indigo-50', text: 'text-indigo-700', border: 'border-indigo-200' },
  QC_IN_PROGRESS: { bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200' },
  QC_APPROVED: { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200' },
  WARRANTY_ACCEPTED: { bg: 'bg-teal-50', text: 'text-teal-700', border: 'border-teal-200' },
  REPAIRING: { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200' },
  REPLACEMENT_APPROVED: { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200' },
  WAITING_FOR_STOCK: { bg: 'bg-rose-50', text: 'text-rose-700', border: 'border-rose-200' },
  EXCHANGE_PROCESSING: { bg: 'bg-cyan-50', text: 'text-cyan-700', border: 'border-cyan-200' },
  REPLACEMENT_PROCESSING: { bg: 'bg-cyan-50', text: 'text-cyan-700', border: 'border-cyan-200' },
  REFUND_PROCESSING: { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200' },
  READY_TO_RETURN: { bg: 'bg-purple-50', text: 'text-purple-700', border: 'border-purple-200' },
  COMPLETED: { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200' },
  REJECTED: { bg: 'bg-rose-50', text: 'text-rose-700', border: 'border-rose-200' },
  CANCELLED: { bg: 'bg-slate-100', text: 'text-slate-500', border: 'border-slate-250' },
  CLOSED_EXPIRED: { bg: 'bg-slate-100', text: 'text-slate-500', border: 'border-slate-250' },
};

type Props = {
  kind: 'return' | 'warranty';
  orders: any[];
};

export function AfterSalesTab({ kind, orders }: Props) {
  const isReturn = kind === 'return';
  const api = isReturn ? customerCenterApi.listReturns : customerCenterApi.listWarranties;
  const createApi = isReturn ? customerCenterApi.createReturn : customerCenterApi.createWarranty;
  const cancelApi = isReturn ? customerCenterApi.cancelReturn : customerCenterApi.cancelWarranty;
  const uploadApi = isReturn ? customerCenterApi.uploadReturnFiles : customerCenterApi.uploadWarrantyFiles;

  const [items, setItems] = useState<any[]>([]);
  const [orderId, setOrderId] = useState('');
  const [orderItemId, setOrderItemId] = useState('');
  const [reason, setReason] = useState('');
  const [imei, setImei] = useState('');
  const [serialNumber, setSerialNumber] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [filePreviews, setFilePreviews] = useState<{ url: string; type: string; name: string }[]>([]);
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);

  // Chỉ cho phép chọn đơn hàng đã giao thành công (COMPLETED) hoặc đang giao (SHIPPED)
  const validOrders = useMemo(() => {
    return (orders || []).filter(order => ['COMPLETED', 'SHIPPED'].includes(order.status));
  }, [orders]);

  const selectedOrder = useMemo(() => {
    return validOrders.find(order => String(order.id) === orderId);
  }, [validOrders, orderId]);

  async function load() {
    try {
      const data = await api({ page: 1, limit: 50 });
      setItems(data.items || []);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Không thể tải yêu cầu hậu mãi.');
    }
  }

  useEffect(() => {
    void load();
  }, [kind]);

  // Sinh previews cho file đính kèm
  useEffect(() => {
    if (!files.length) {
      setFilePreviews([]);
      return;
    }
    const urls = files.map(file => ({
      url: URL.createObjectURL(file),
      type: file.type,
      name: file.name
    }));
    setFilePreviews(urls);

    return () => {
      urls.forEach(item => URL.revokeObjectURL(item.url));
    };
  }, [files]);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(event.target.files || []);
    // Khống chế tối đa 5 files
    setFiles(prev => [...prev, ...selectedFiles].slice(0, 5));
  };

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!orderId || !orderItemId) {
      setMessage('Vui lòng chọn đơn hàng và sản phẩm.');
      return;
    }
    setBusy(true);
    setMessage('');
    try {
      const created = await createApi({
        order_id: orderId,
        reason,
        items: [{
          order_item_id: orderItemId,
          quantity: 1,
          imei: imei.trim() || null,
          serial_number: serialNumber.trim() || null,
        }],
      });
      if (files.length) {
        await uploadApi(created.id, files);
      }
      setReason('');
      setImei('');
      setSerialNumber('');
      setFiles([]);
      setMessage(`Đã gửi thành công yêu cầu ${created.requestCode}.`);
      await load();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Không thể tạo yêu cầu.');
    } finally {
      setBusy(false);
    }
  }

  async function cancel(id: string) {
    if (!window.confirm('Bạn có chắc chắn muốn hủy yêu cầu này?')) return;
    try {
      await cancelApi(id);
      await load();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Không thể hủy yêu cầu.');
    }
  }

  // Lấy tiến trình stepper tương ứng với status hiện tại
  const getProgressSteps = (status: string) => {
    // 4 Mốc lớn
    const stepsList = [
      { key: 'SUBMITTED', label: 'Gửi yêu cầu' },
      { key: 'QC', label: 'Kiểm QC' },
      { key: 'PROCESSING', label: 'Xử lý' },
      { key: 'COMPLETED', label: 'Hoàn tất' }
    ];

    const qcStatuses = ['RECEIVED', 'QC_IN_PROGRESS'];
    const processingStatuses = [
      'QC_APPROVED', 'WARRANTY_ACCEPTED', 'REPAIRING', 'REPLACEMENT_APPROVED',
      'WAITING_FOR_STOCK', 'EXCHANGE_PROCESSING', 'REPLACEMENT_PROCESSING',
      'REFUND_PROCESSING', 'READY_TO_RETURN'
    ];

    let currentStepIndex = 0;
    if (qcStatuses.includes(status)) {
      currentStepIndex = 1;
    } else if (processingStatuses.includes(status)) {
      currentStepIndex = 2;
    } else if (status === 'COMPLETED') {
      currentStepIndex = 3;
    }

    if (['REJECTED', 'CANCELLED', 'CLOSED_EXPIRED'].includes(status)) {
      return { isSpecial: true, statusText: statusLabel[status] || status };
    }

    return {
      isSpecial: false,
      currentStepIndex,
      steps: stepsList
    };
  };

  return (
    <div className="space-y-8">
      {/* Form Tạo Yêu Cầu */}
      <form onSubmit={submit} className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm">
        <h3 className="text-lg font-extrabold text-slate-900 border-b border-slate-50 pb-3">
          Tạo yêu cầu {isReturn ? 'đổi trả hàng' : 'bảo hành thiết bị'}
        </h3>
        
        <div className="mt-5 grid gap-5 md:grid-cols-2">
          {/* Dropdown Đơn hàng */}
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Đơn hàng của bạn</label>
            <select 
              value={orderId} 
              onChange={event => { setOrderId(event.target.value); setOrderItemId(''); }} 
              className="rounded-xl border border-slate-200 bg-slate-50/50 p-3 text-sm focus:border-slate-900 focus:bg-white focus:outline-none transition-colors" 
              required
            >
              <option value="">-- Chọn đơn hàng hợp lệ --</option>
              {validOrders.map(order => (
                <option key={order.id} value={order.id}>
                  #{order.orderCode} ({order.status === 'COMPLETED' ? 'Đã giao' : 'Đang giao'})
                </option>
              ))}
            </select>
          </div>

          {/* Dropdown Sản phẩm */}
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Sản phẩm lỗi</label>
            <select 
              value={orderItemId} 
              onChange={event => setOrderItemId(event.target.value)} 
              className="rounded-xl border border-slate-200 bg-slate-50/50 p-3 text-sm focus:border-slate-900 focus:bg-white focus:outline-none transition-colors disabled:opacity-60" 
              required 
              disabled={!selectedOrder}
            >
              <option value="">-- Chọn sản phẩm cần bảo trì --</option>
              {(selectedOrder?.items || []).map((item: any) => (
                <option key={item.id} value={item.id}>{item.productName}</option>
              ))}
            </select>
          </div>

          {/* Nhập IMEI */}
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Mã IMEI</label>
            <input 
              value={imei} 
              onChange={event => setImei(event.target.value)} 
              placeholder="Nhập IMEI (Thường ghi trên thân máy/vỏ hộp)" 
              className="rounded-xl border border-slate-200 bg-slate-50/50 p-3 text-sm focus:border-slate-900 focus:bg-white focus:outline-none transition-colors" 
            />
          </div>

          {/* Nhập Serial Number */}
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Mã Serial Number (S/N)</label>
            <input 
              value={serialNumber} 
              onChange={event => setSerialNumber(event.target.value)} 
              placeholder="Nhập Serial number (nếu có)" 
              className="rounded-xl border border-slate-200 bg-slate-50/50 p-3 text-sm focus:border-slate-900 focus:bg-white focus:outline-none transition-colors" 
            />
          </div>
        </div>

        {/* Lý do và mô tả chi tiết */}
        <div className="mt-5 flex flex-col gap-1.5">
          <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Mô tả tình trạng lỗi của sản phẩm</label>
          <textarea 
            value={reason} 
            onChange={event => setReason(event.target.value)} 
            minLength={10} 
            required 
            placeholder="Vui lòng cung cấp chi tiết lỗi của máy để kỹ thuật viên kiểm tra QC nhanh nhất (ví dụ: màn hình sọc ngang, loa rè, không sạc được pin, ...)" 
            className="min-h-28 w-full rounded-xl border border-slate-200 bg-slate-50/50 p-3 text-sm focus:border-slate-900 focus:bg-white focus:outline-none transition-colors" 
          />
        </div>

        {/* Upload file và Preview */}
        <div className="mt-5 flex flex-col gap-1.5">
          <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Hình ảnh / Video minh chứng lỗi (Tối đa 5 tệp)</label>
          <div className="mt-1 flex items-center justify-center w-full">
            <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-slate-200 border-dashed rounded-xl cursor-pointer bg-slate-50/50 hover:bg-slate-100/50 transition-colors">
              <div className="flex flex-col items-center justify-center pt-5 pb-6">
                <svg className="w-8 h-8 mb-2.5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
                <p className="mb-1 text-sm text-slate-500 font-medium">Click để chọn ảnh hoặc video minh họa</p>
                <p className="text-xs text-slate-400">Chấp nhận JPG, PNG, WEBP, MP4, MOV (Dưới 20MB)</p>
              </div>
              <input 
                type="file" 
                multiple 
                accept="image/jpeg,image/png,image/webp,video/mp4,video/webm,video/quicktime" 
                onChange={handleFileChange} 
                className="hidden" 
              />
            </label>
          </div>

          {/* Preview Zone */}
          {filePreviews.length > 0 && (
            <div className="mt-4 grid grid-cols-5 gap-3">
              {filePreviews.map((preview, index) => (
                <div key={index} className="relative group rounded-lg overflow-hidden border border-slate-200 bg-slate-100 aspect-square">
                  {preview.type.startsWith('video/') ? (
                    <div className="flex h-full w-full items-center justify-center bg-slate-900 text-white">
                      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                        <path strokeLinecap="round" strokeLinejoin="round" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    </div>
                  ) : (
                    <img src={preview.url} alt={preview.name} className="h-full w-full object-cover" />
                  )}
                  <button 
                    type="button" 
                    onClick={() => removeFile(index)} 
                    className="absolute -top-1 -right-1 m-1.5 h-5 w-5 bg-rose-500 text-white rounded-full flex items-center justify-center text-xs font-bold opacity-90 hover:opacity-100 shadow-sm"
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Nút gửi */}
        <div className="mt-6 flex justify-end">
          <button 
            disabled={busy} 
            className="inline-flex items-center justify-center rounded-xl bg-slate-900 px-6 py-3 text-sm font-bold text-white shadow-md hover:bg-slate-800 focus:outline-none transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {busy ? (
              <>
                <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Đang gửi yêu cầu...
              </>
            ) : 'Gửi yêu cầu bảo hành/đổi trả'}
          </button>
        </div>

        {message && (
          <div className="mt-4 rounded-xl bg-slate-50 border border-slate-100 p-3.5 text-sm text-slate-700 font-medium">
            {message}
          </div>
        )}
      </form>

      {/* Lịch Sử Yêu Cầu */}
      <section className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm">
        <h3 className="text-lg font-extrabold text-slate-900 border-b border-slate-50 pb-3">
          Lịch sử yêu cầu đã gửi
        </h3>
        
        <div className="mt-5 space-y-4">
          {items.map(item => {
            const progress = getProgressSteps(item.status);
            const style = statusStyles[item.status] || { bg: 'bg-slate-50', text: 'text-slate-700', border: 'border-slate-200' };

            return (
              <article key={item.id} className="rounded-xl border border-slate-150 p-5 hover:border-slate-350 transition-colors">
                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-50 pb-3 mb-4">
                  <div>
                    <div className="font-extrabold text-slate-900 text-base">{item.requestCode}</div>
                    <div className="text-xs text-slate-400 mt-0.5">
                      Đơn hàng #{item.orderCode} · Đã gửi ngày {new Date(item.createdAt).toLocaleString('vi-VN')}
                    </div>
                  </div>
                  <span className={`inline-flex items-center rounded-lg px-2.5 py-1 text-xs font-bold border ${style.bg} ${style.text} ${style.border}`}>
                    {statusLabel[item.status] || item.status}
                  </span>
                </div>

                <div className="space-y-2">
                  <p className="text-sm leading-relaxed text-slate-650 bg-slate-50 p-3 rounded-lg border border-slate-100">
                    <span className="font-bold text-slate-800 text-xs block mb-1 uppercase tracking-wide">Mô tả lỗi:</span>
                    {item.reason}
                  </p>
                  
                  <div className="text-xs text-slate-400 flex flex-wrap gap-1.5 items-center mt-2.5">
                    <span className="font-bold text-slate-500">Sản phẩm lỗi:</span>
                    {(item.items || []).map((line: any, idx: number) => (
                      <span key={line.id} className="inline-flex items-center bg-slate-100 border border-slate-200 px-2 py-0.5 rounded text-slate-600 font-medium">
                        {line.productName}
                        {line.imei && ` (IMEI: ${line.imei})`}
                        {line.replacementImei && ` ➔ Đã đổi sang máy: ${line.replacementImei}`}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Timeline Stepper rút gọn cho khách */}
                {!progress.isSpecial && progress.steps && (
                  <div className="mt-5 border-t border-slate-50 pt-5">
                    <div className="flex items-center justify-between relative max-w-xl mx-auto">
                      {/* Line nền */}
                      <div className="absolute top-[13px] left-[16px] right-[16px] h-0.5 bg-slate-100 z-0" />
                      
                      {/* Line tiến độ */}
                      <div 
                        className="absolute top-[13px] left-[16px] h-0.5 bg-emerald-500 z-0 transition-all duration-300"
                        style={{ width: `${(progress.currentStepIndex / (progress.steps.length - 1)) * 100}%` }}
                      />

                      {progress.steps.map((step, idx) => {
                        const isDone = idx < (progress.currentStepIndex ?? 0);
                        const isActive = idx === progress.currentStepIndex;
                        return (
                          <div key={idx} className="flex flex-col items-center z-10">
                            <div 
                              className={`h-7 w-7 rounded-full flex items-center justify-center border text-xs font-bold transition-all duration-300 ${
                                isDone 
                                  ? 'bg-emerald-500 border-emerald-500 text-white ring-4 ring-emerald-50'
                                  : isActive
                                  ? 'bg-slate-900 border-slate-900 text-white ring-4 ring-slate-100 animate-pulse'
                                  : 'bg-white border-slate-200 text-slate-400'
                              }`}
                            >
                              {isDone ? '✓' : idx + 1}
                            </div>
                            <span className={`text-[10px] font-bold mt-1.5 ${
                              isActive ? 'text-slate-900' : isDone ? 'text-emerald-600' : 'text-slate-400'
                            }`}>
                              {step.label}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Phản hồi từ chối hoặc hủy đặc biệt */}
                {progress.isSpecial && (
                  <div className="mt-4 border-t border-slate-50 pt-4 text-xs text-slate-500">
                    Hồ sơ đã đóng với trạng thái: <strong className="text-slate-700">{progress.statusText}</strong>
                  </div>
                )}

                {/* Hủy yêu cầu (chỉ khi chưa xử lý) */}
                {['SUBMITTED', 'WAITING_FOR_STOCK'].includes(item.status) && (
                  <div className="mt-4 border-t border-slate-50 pt-4 flex justify-end">
                    <button 
                      type="button" 
                      onClick={() => void cancel(item.id)} 
                      className="text-xs font-bold text-rose-600 hover:text-rose-700 bg-rose-50 hover:bg-rose-100 px-3 py-1.5 rounded-lg transition-colors"
                    >
                      Hủy yêu cầu
                    </button>
                  </div>
                )}
              </article>
            );
          })}
          {!items.length && (
            <div className="py-12 text-center text-sm text-slate-400 font-medium">
              Chưa có yêu cầu đổi trả hoặc bảo hành nào được tạo.
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
