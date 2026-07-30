import React, { useEffect, useState } from 'react';
import { ClipboardList, Eye, ArrowLeft, Save, CheckCircle2, Wand2, Plus, X, Search } from 'lucide-react';
import { AdminPanel, AdminTable } from '../../admin-shell/components/AdminDashboardParts';
import { AdminBadge } from '../../admin-shell/components/AdminDashboardParts';
import { adminInventoryApi } from '../services/adminInventoryApi';

type AdminInventoryOutboundsTabProps = {
  usePermission?: (permission: string) => boolean;
  isSuperAdmin?: boolean;
  [key: string]: any;
};

const outboundStatusLabel: Record<string, string> = {
  DRAFT: 'Nháp',
  PICKING: 'Đang đóng hàng',
  PICKED: 'Đã đóng đủ hàng',
  COMPLETED: 'Đã xuất kho',
  CANCELLED: 'Đã hủy',
};

const outboundStatusTone: Record<string, any> = {
  DRAFT: 'slate',
  PICKING: 'amber',
  PICKED: 'blue',
  COMPLETED: 'green',
  CANCELLED: 'red',
};

export default function AdminInventoryOutboundsTab(props: AdminInventoryOutboundsTabProps) {
  const { isSuperAdmin } = props;

  // List state
  const [outbounds, setOutbounds] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  // Detail state
  const [selectedOutbound, setSelectedOutbound] = useState<any | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // Auxiliary state
  const [scannedInputs, setScannedInputs] = useState<Record<string, string>>({});
  const [identifierCatalog, setIdentifierCatalog] = useState<Record<string, { imeis: any[]; serialNumbers: any[]; identifierPairs: any[] }>>({});
  const [openSerialPicker, setOpenSerialPicker] = useState<string | null>(null);
  const [loadingSerialPicker, setLoadingSerialPicker] = useState<string | null>(null);
  const [cancelModalOpen, setCancelModalOpen] = useState(false);
  const [cancelReasonInput, setCancelReasonInput] = useState('');

  // Feedback messages
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  // Load outbounds list on mount
  useEffect(() => {
    void fetchOutbounds();
  }, []);

  const fetchOutbounds = async (filters?: {
    search?: string;
    status?: string;
    from?: string;
    to?: string;
  }) => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const data = await adminInventoryApi.adminGetOutbounds(
        filters?.search ?? searchQuery,
        filters?.status ?? statusFilter,
        filters?.from ?? dateFrom,
        filters?.to ?? dateTo,
      );
      setOutbounds(Array.isArray(data) ? data : []);
    } catch (err: any) {
      console.error('Lỗi khi tải danh sách phiếu xuất:', err);
      setErrorMsg('Không thể tải danh sách phiếu xuất kho từ hệ thống.');
    } finally {
      setLoading(false);
    }
  };

  const handleSearchSubmit = (e?: React.FormEvent) => {
    e?.preventDefault();
    void fetchOutbounds();
  };

  const handleResetFilters = () => {
    setSearchQuery('');
    setStatusFilter('');
    setDateFrom('');
    setDateTo('');
    void fetchOutbounds({ search: '', status: '', from: '', to: '' });
  };

  const loadDetail = async (documentNo: string) => {
    setDetailLoading(true);
    setErrorMsg(null);
    setSuccessMsg(null);
    try {
      const data = await adminInventoryApi.adminGetOutboundDetail(documentNo);

      const initialInputs: Record<string, string> = {};
      if (data && Array.isArray(data.lines)) {
        data.lines = data.lines.map((line: any) => {
          const allocations = Array.isArray(line.allocations) && line.allocations.length > 0
            ? line.allocations
            : [{
                locationId: line.locationId || '',
                quantity: line.approvedQuantity ?? line.quantity,
                imeis: line.imeis || [],
                secondaryImeis: line.secondaryImeis || [],
                serialNumbers: line.serialNumbers || []
              }];

          allocations.forEach((_: any, idx: number) => {
            initialInputs[`${line.id}_${idx}_imei`] = '';
            initialInputs[`${line.id}_${idx}_serial`] = '';
          });

          const shelfAllocations = allocations.map((allocation: any) => (
            String(allocation.locationCode || '').toUpperCase() === 'MAIN'
              ? { ...allocation, locationId: '', locationCode: '', locationName: '', imeis: [], secondaryImeis: [], serialNumbers: [] }
              : allocation
          ));

          return { ...line, allocations: shelfAllocations };
        });

        const catalogEntries = await Promise.all(data.lines
          .filter((line: any) => line.tracksImei || line.tracksSerialNumber)
          .map(async (line: any) => {
            try {
              const catalog = await adminInventoryApi.adminListIdentifiers(line.productId, line.variantId || null);
              return [line.id, {
                imeis: Array.isArray(catalog?.imeis) ? catalog.imeis : [],
                serialNumbers: Array.isArray(catalog?.serialNumbers) ? catalog.serialNumbers : [],
                identifierPairs: Array.isArray(catalog?.identifierPairs) ? catalog.identifierPairs : [],
              }] as const;
            } catch {
              return [line.id, { imeis: [], serialNumbers: [], identifierPairs: [] }] as const;
            }
          }));
        setIdentifierCatalog(Object.fromEntries(catalogEntries));
      }

      setSelectedOutbound(data);
      setScannedInputs(initialInputs);
    } catch (err) {
      console.error('Lỗi khi tải chi tiết phiếu xuất:', err);
      setErrorMsg('Không thể tải chi tiết phiếu xuất kho.');
    } finally {
      setDetailLoading(false);
    }
  };

  const addOutboundAllocation = (lineId: string) => {
    if (!selectedOutbound) return;
    const updatedLines = selectedOutbound.lines.map((line: any) => {
      if (line.id === lineId) {
        const currentAllocations = Array.isArray(line.allocations) ? [...line.allocations] : [];
        currentAllocations.push({
          locationId: '',
          quantity: 1,
          imeis: [],
          serialNumbers: []
        });

        // Khởi tạo scanned inputs mới cho allocation mới thêm
        const idx = currentAllocations.length - 1;
        setScannedInputs(prev => ({
          ...prev,
          [`${lineId}_${idx}_imei`]: '',
          [`${lineId}_${idx}_serial`]: ''
        }));

        return { ...line, allocations: currentAllocations };
      }
      return line;
    });
    setSelectedOutbound({ ...selectedOutbound, lines: updatedLines });
  };

  const removeOutboundAllocation = (lineId: string, allocIndex: number) => {
    if (!selectedOutbound) return;
    const updatedLines = selectedOutbound.lines.map((line: any) => {
      if (line.id === lineId) {
        const currentAllocations = Array.isArray(line.allocations) ? [...line.allocations] : [];
        currentAllocations.splice(allocIndex, 1);
        return { ...line, allocations: currentAllocations };
      }
      return line;
    });
    setSelectedOutbound({ ...selectedOutbound, lines: updatedLines });
  };

  const updateOutboundAllocation = (lineId: string, allocIndex: number, fields: any) => {
    if (!selectedOutbound) return;
    const updatedLines = selectedOutbound.lines.map((line: any) => {
      if (line.id === lineId) {
        const currentAllocations = Array.isArray(line.allocations) ? [...line.allocations] : [];
        currentAllocations[allocIndex] = { ...currentAllocations[allocIndex], ...fields };
        return { ...line, allocations: currentAllocations };
      }
      return line;
    });
    setSelectedOutbound({ ...selectedOutbound, lines: updatedLines });
  };

  const handleAddAllocIdentifier = async (lineId: string, allocIndex: number, type: 'imei' | 'serial', selectedValue?: string) => {
    if (!selectedOutbound) return;
    const inputKey = `${lineId}_${allocIndex}_${type}`;
    const rawVal = selectedValue ?? scannedInputs[inputKey] ?? '';
    const cleanVal = rawVal.trim();
    if (!cleanVal) return;

    const line = selectedOutbound.lines.find((l: any) => l.id === lineId);
    if (!line) return;

    const alloc = line.allocations?.[allocIndex];
    if (!alloc) return;

    const currentImeis = Array.isArray(alloc.imeis) ? [...alloc.imeis] : [];
    const currentSerials = Array.isArray(alloc.serialNumbers) ? [...alloc.serialNumbers] : [];

    if (line.tracksImei && line.tracksSerialNumber) {
      if (!alloc.locationId) {
        setErrorMsg('Vui lòng chọn kệ trước khi quét IMEI/Serial.');
        return;
      }
      try {
        const pair = await adminInventoryApi.adminResolveOutboundIdentifierPair({
          productId: line.productId,
          variantId: line.variantId || null,
          locationId: alloc.locationId,
          identifierType: type === 'imei' ? 'IMEI' : 'SERIAL',
          identifierValue: cleanVal,
        });
        const pairedImei = String(pair.imei || '').trim();
        const pairedSerial = String(pair.serialNumber || '').trim();
        if (!pairedImei || !pairedSerial) {
          setErrorMsg('Không tìm thấy đủ cặp IMEI/Serial cho mã vừa quét.');
          return;
        }
        if (currentImeis.includes(pairedImei) || currentSerials.includes(pairedSerial)) {
          setErrorMsg('Máy này đã được thêm vào kệ.');
          return;
        }
        if (currentImeis.length >= alloc.quantity || currentSerials.length >= alloc.quantity) {
          setErrorMsg(`Đã đủ số lượng máy cho kệ này (${alloc.quantity}).`);
          return;
        }
        currentImeis.push(pairedImei);
        currentSerials.push(pairedSerial);
      } catch (err: any) {
        setErrorMsg(err.message || 'Không thể tự tìm cặp IMEI/Serial cho mã vừa quét.');
        return;
      }
    } else if (type === 'imei') {
      if (currentImeis.includes(cleanVal)) {
        setErrorMsg('Mã IMEI này đã được thêm vào kệ.');
        return;
      }
      if (currentImeis.length >= alloc.quantity) {
        setErrorMsg(`Đã đủ số lượng IMEI cho kệ này (${alloc.quantity}).`);
        return;
      }
      currentImeis.push(cleanVal);
    } else {
      if (currentSerials.includes(cleanVal)) {
        setErrorMsg('Mã Serial này đã được thêm vào kệ.');
        return;
      }
      if (currentSerials.length >= alloc.quantity) {
        setErrorMsg(`Đã đủ số lượng Serial cho kệ này (${alloc.quantity}).`);
        return;
      }
      currentSerials.push(cleanVal);
    }

    const updatedLines = selectedOutbound.lines.map((l: any) => {
      if (l.id === lineId) {
        const allocs = [...l.allocations];
        allocs[allocIndex] = {
          ...allocs[allocIndex],
          imeis: currentImeis,
          serialNumbers: currentSerials,
        };
        return { ...l, allocations: allocs };
      }
      return l;
    });

    setSelectedOutbound({ ...selectedOutbound, lines: updatedLines });
    setScannedInputs(prev => ({
      ...prev,
      [`${lineId}_${allocIndex}_imei`]: '',
      [`${lineId}_${allocIndex}_serial`]: '',
    }));
    setErrorMsg(null);
    setOpenSerialPicker(null);
  };

  const handleRemoveAllocIdentifier = (lineId: string, allocIndex: number, type: 'imei' | 'serial', itemIndex: number) => {
    if (!selectedOutbound) return;
    const updatedLines = selectedOutbound.lines.map((line: any) => {
      if (line.id === lineId) {
        const allocs = [...line.allocations];
        const alloc = allocs[allocIndex];
        let currentImeis = Array.isArray(alloc.imeis) ? [...alloc.imeis] : [];
        let currentSerials = Array.isArray(alloc.serialNumbers) ? [...alloc.serialNumbers] : [];

        if (type === 'imei') {
          currentImeis.splice(itemIndex, 1);
        } else {
          currentSerials.splice(itemIndex, 1);
        }

        allocs[allocIndex] = {
          ...alloc,
          imeis: currentImeis,
          serialNumbers: currentSerials,
        };
        return { ...line, allocations: allocs };
      }
      return line;
    });
    setSelectedOutbound({ ...selectedOutbound, lines: updatedLines });
  };

  const handleRemoveAllocDevice = (lineId: string, allocIndex: number, itemIndex: number) => {
    if (!selectedOutbound) return;
    const updatedLines = selectedOutbound.lines.map((line: any) => {
      if (line.id !== lineId) return line;
      const allocations = [...line.allocations];
      const allocation = allocations[allocIndex];
      const imeis = [...(allocation.imeis || [])];
      const secondaryImeis = [...(allocation.secondaryImeis || [])];
      const serialNumbers = [...(allocation.serialNumbers || [])];
      imeis.splice(itemIndex, 1);
      secondaryImeis.splice(itemIndex, 1);
      serialNumbers.splice(itemIndex, 1);
      allocations[allocIndex] = { ...allocation, imeis, secondaryImeis, serialNumbers };
      return { ...line, allocations };
    });
    setSelectedOutbound({ ...selectedOutbound, lines: updatedLines });
  };

  const handleToggleDevicePicker = async (line: any, allocationIndex: number) => {
    const pickerKey = `${line.id}_${allocationIndex}_serial_picker`;
    if (openSerialPicker === pickerKey) {
      setOpenSerialPicker(null);
      return;
    }
    setOpenSerialPicker(pickerKey);
    setLoadingSerialPicker(pickerKey);
    setErrorMsg(null);
    try {
      const catalog = await adminInventoryApi.adminListIdentifiers(line.productId, line.variantId || null);
      setIdentifierCatalog((current) => ({
        ...current,
        [line.id]: {
          imeis: Array.isArray(catalog?.imeis) ? catalog.imeis : [],
          serialNumbers: Array.isArray(catalog?.serialNumbers) ? catalog.serialNumbers : [],
          identifierPairs: Array.isArray(catalog?.identifierPairs) ? catalog.identifierPairs : [],
        },
      }));
    } catch (error: any) {
      setOpenSerialPicker(null);
      setErrorMsg(error?.message || 'Không thể tải danh sách máy tại kệ. Vui lòng thử lại.');
    } finally {
      setLoadingSerialPicker(null);
    }
  };

  const buildOutboundPayload = () => {
    if (!selectedOutbound) return [];
    return selectedOutbound.lines.map((line: any) => {
      const allocations = line.allocations || [];
      return {
        lineId: line.id,
        locationId: allocations[0]?.locationId || line.locationId || null,
        approvedQuantity: allocations.reduce((sum: number, a: any) => sum + Number(a.quantity || 0), 0) || line.quantity,
        imeis: allocations[0]?.imeis || line.imeis || [],
        serialNumbers: allocations[0]?.serialNumbers || line.serialNumbers || [],
        allocations: allocations.map((a: any) => ({
          locationId: a.locationId,
          quantity: Number(a.quantity || 0),
          imeis: a.imeis || [],
          serialNumbers: a.serialNumbers || [],
        }))
      };
    });
  };

  const handleSaveDraft = async () => {
    if (!selectedOutbound) return;

    // Kiểm tra không cho phép lưu nháp nếu vượt quá số lượng yêu cầu
    for (const line of selectedOutbound.lines) {
      const allocations = line.allocations || [];
      const totalAllocated = allocations.reduce((sum: number, a: any) => sum + Number(a.quantity || 0), 0);
      if (totalAllocated > line.quantity) {
        setErrorMsg(`Sản phẩm "${line.productName}" có tổng số lượng đã chọn (${totalAllocated}) vượt quá số lượng yêu cầu (${line.quantity}).`);
        return;
      }
    }

    setActionLoading(true);
    setErrorMsg(null);
    setSuccessMsg(null);

    try {
      await adminInventoryApi.adminUpdateOutbound(selectedOutbound.document_no, buildOutboundPayload());
      setSuccessMsg('Đã cập nhật thông tin đóng hàng.');
      await loadDetail(selectedOutbound.document_no);
    } catch (err: any) {
      console.error(err);
      setErrorMsg(err.message || 'Lỗi khi lưu nháp.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleComplete = async () => {
    if (!selectedOutbound) return;

    for (const line of selectedOutbound.lines) {
      const allocations = line.allocations || [];
      if (allocations.length === 0) {
        setErrorMsg(`Sản phẩm "${line.productName}" chưa được chọn kệ xuất.`);
        return;
      }

      let totalAllocated = 0;
      const seenLocations = new Set<string>();

      for (const alloc of allocations) {
        if (!alloc.locationId) {
          setErrorMsg(`Sản phẩm "${line.productName}" có dòng đóng hàng chưa chọn kệ xuất.`);
          return;
        }
        if (seenLocations.has(alloc.locationId)) {
          setErrorMsg(`Sản phẩm "${line.productName}" bị chọn trùng kệ xuất.`);
          return;
        }
        seenLocations.add(alloc.locationId);

        const qty = Number(alloc.quantity || 0);
        if (qty <= 0) {
          setErrorMsg(`Sản phẩm "${line.productName}" có số lượng đóng hàng không hợp lệ.`);
          return;
        }
        totalAllocated += qty;

        if (line.tracksImei && (alloc.imeis || []).length !== qty) {
          setErrorMsg(`Sản phẩm "${line.productName}" yêu cầu quét đủ ${qty} IMEI tại kệ (Đang có ${(alloc.imeis || []).length}).`);
          return;
        }
        if (line.tracksSerialNumber && (alloc.serialNumbers || []).length !== qty) {
          setErrorMsg(`Sản phẩm "${line.productName}" yêu cầu quét đủ ${qty} mã Serial tại kệ (Đang có ${(alloc.serialNumbers || []).length}).`);
          return;
        }
      }

      if (totalAllocated !== line.quantity) {
        setErrorMsg(`Sản phẩm "${line.productName}" có tổng số lượng đã chọn (${totalAllocated}) khác số lượng yêu cầu (${line.quantity}).`);
        return;
      }
    }

    if (!window.confirm('Xác nhận xuất kho? Hệ thống sẽ lưu thông tin đóng hàng, trừ tồn kho thực tế và cập nhật đơn hàng sang "Đang giao hàng" (SHIPPED).')) return;

    setActionLoading(true);
    setErrorMsg(null);
    setSuccessMsg(null);

    try {
      await adminInventoryApi.adminUpdateOutbound(selectedOutbound.document_no, buildOutboundPayload());

      await adminInventoryApi.adminUpdateOutboundStatus(selectedOutbound.document_no, 'COMPLETED');
      setSuccessMsg('Đã xác nhận xuất kho thành công. Đơn hàng đã tự động chuyển sang Đang giao (SHIPPED).');
      await loadDetail(selectedOutbound.document_no);
      void fetchOutbounds();
    } catch (err: any) {
      console.error(err);
      setErrorMsg(err.message || 'Lỗi khi duyệt hoàn tất phiếu xuất kho.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleCancelOutboundClick = () => {
    setCancelReasonInput('');
    setCancelModalOpen(true);
  };

  const confirmCancelOutbound = async () => {
    if (!selectedOutbound) return;
    const reason = cancelReasonInput.trim();
    if (!reason) return;

    setActionLoading(true);
    setErrorMsg(null);
    setSuccessMsg(null);
    setCancelModalOpen(false);

    try {
      await adminInventoryApi.adminUpdateOutboundStatus(selectedOutbound.document_no, 'CANCELLED', reason);
      setSuccessMsg('Đã hủy phiếu xuất kho thành công.');
      await loadDetail(selectedOutbound.document_no);
      void fetchOutbounds();
    } catch (err: any) {
      console.error(err);
      setErrorMsg(err.message || 'Lỗi khi hủy phiếu xuất kho.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleAutoSuggest = async () => {
    if (!selectedOutbound) return;
    setActionLoading(true);
    setErrorMsg(null);
    setSuccessMsg(null);

    try {
      await adminInventoryApi.adminAutoSuggestOutbound(selectedOutbound.document_no);
      setSuccessMsg('Đã gợi ý kệ xuất theo tồn kho hiện có.');
      await loadDetail(selectedOutbound.document_no);
    } catch (err: any) {
      console.error(err);
      setErrorMsg(err.message || 'Lỗi khi gợi ý kệ xuất.');
    } finally {
      setActionLoading(false);
    }
  };

  const getLineStatus = (line: any) => {
    const approved = line.approvedQuantity ?? 0;
    return approved === line.quantity ? 'COMPLETED' : approved > 0 ? 'PARTIAL' : 'PENDING';
  };

  const renderLineStatusBadge = (line: any) => {
    const status = getLineStatus(line);
    if (status === 'COMPLETED') return <AdminBadge tone="green">Đủ số lượng</AdminBadge>;
    if (status === 'PARTIAL') return <AdminBadge tone="amber">Mới quét một phần</AdminBadge>;
    return <AdminBadge tone="slate">Chờ đóng hàng</AdminBadge>;
  };

  const getLineAvailableLocations = (line: any, alloc: any) => {
    const candidates = (Array.isArray(line.availableLocations) ? line.availableLocations : [])
      .filter((location: any) => String(location.locationCode || '').toUpperCase() !== 'MAIN');
    if (!alloc?.locationId || candidates.some((loc: any) => loc.locationId === alloc.locationId)) {
      return candidates;
    }
    return [
      {
        locationId: alloc.locationId,
        locationCode: alloc.locationCode || line.locationCode || 'Kệ đã chọn',
        locationName: alloc.locationName || line.locationName || '',
        availableQuantity: alloc.quantity || 0,
        onHandQuantity: alloc.quantity || 0,
      },
      ...candidates,
    ];
  };

  // Detail View Mode
  if (selectedOutbound) {
    const isCompleted = selectedOutbound.status === 'COMPLETED' || selectedOutbound.status === 'CANCELLED';
    return (
      <div className="space-y-6">
        {/* Back and actions header */}
        <div className="flex items-center justify-between border-b border-slate-200 pb-4">
          <button
            type="button"
            onClick={() => {
              setSelectedOutbound(null);
              setErrorMsg(null);
              setSuccessMsg(null);
              void fetchOutbounds();
            }}
            className="inline-flex items-center gap-2 text-sm font-semibold text-slate-600 transition hover:text-slate-900"
          >
            <ArrowLeft className="h-4 w-4" /> Quay lại danh sách phiếu
          </button>

          <div className="flex gap-2">
            {!isCompleted && (
              <>
                <button
                  type="button"
                  onClick={handleAutoSuggest}
                  disabled={actionLoading}
                  className="inline-flex items-center gap-2 rounded-md bg-blue-50 px-3 py-2 text-sm font-semibold text-blue-700 transition hover:bg-blue-100 disabled:opacity-50"
                >
                  <Wand2 className="h-4 w-4" /> Gợi ý kệ xuất
                </button>

                <button
                  type="button"
                  onClick={handleSaveDraft}
                  disabled={actionLoading}
                  className="inline-flex items-center gap-2 rounded-md bg-slate-950 px-3 py-2 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:opacity-50"
                >
                  <Save className="h-4 w-4" /> Cập nhật
                </button>

                <button
                  type="button"
                  onClick={handleComplete}
                  disabled={actionLoading || !isSuperAdmin}
                  className={`inline-flex items-center gap-2 rounded-md px-3 py-2 text-sm font-semibold text-white transition ${
                    isSuperAdmin
                      ? 'bg-emerald-600 hover:bg-emerald-700'
                      : 'bg-slate-300 cursor-not-allowed text-slate-500'
                  } disabled:opacity-50`}
                  title={
                    !isSuperAdmin
                      ? 'Yêu cầu tài khoản Super Admin phê duyệt'
                      : 'Hệ thống sẽ cập nhật thông tin đóng hàng trước khi xuất kho.'
                  }
                >
                  <CheckCircle2 className="h-4 w-4" /> Xác nhận xuất kho
                </button>

                <button
                  type="button"
                  onClick={handleCancelOutboundClick}
                  disabled={actionLoading}
                  className="inline-flex items-center gap-2 rounded-md bg-red-50 px-3 py-2 text-sm font-semibold text-red-700 transition hover:bg-red-100 disabled:opacity-50"
                >
                  <X className="h-4 w-4" /> Hủy phiếu
                </button>
              </>
            )}
          </div>
        </div>

        {/* Notices */}
        {errorMsg && (
          <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm font-medium text-red-800 flex items-start gap-2">
            <X className="h-4 w-4 mt-0.5 flex-shrink-0" />
            <div>{errorMsg}</div>
          </div>
        )}
        {successMsg && (
          <div className="rounded-md border border-emerald-200 bg-emerald-50 p-4 text-sm font-medium text-emerald-800 flex items-start gap-2">
            <CheckCircle2 className="h-4 w-4 mt-0.5 flex-shrink-0" />
            <div>{successMsg}</div>
          </div>
        )}

        {/* Outbound Info Panel */}
        <AdminPanel title={`Phiếu xuất kho: ${selectedOutbound.document_no}`}>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 p-4">
            <div className="space-y-3">
              <div>
                <span className="block text-xs font-bold uppercase text-slate-500">Mã đơn hàng liên kết</span>
                <span className="font-mono text-sm font-bold text-slate-900">{selectedOutbound.orderCode || '-'}</span>
              </div>
              {selectedOutbound.afterSalesRequestCode && (
                <div>
                  <span className="block text-xs font-bold uppercase text-slate-500">Hồ sơ hậu mãi liên kết</span>
                  <span className="font-mono text-sm font-bold text-slate-900">
                    {selectedOutbound.afterSalesRequestCode}
                  </span>
                </div>
              )}
              <div>
                <span className="block text-xs font-bold uppercase text-slate-500">Trạng thái phiếu</span>
                <div className="mt-1">
                  <AdminBadge tone={outboundStatusTone[selectedOutbound.status] || 'slate'}>
                    {outboundStatusLabel[selectedOutbound.status] || selectedOutbound.status}
                  </AdminBadge>
                </div>
              </div>
              <div>
                <span className="block text-xs font-bold uppercase text-slate-500">Ngày tạo phiếu</span>
                <span className="text-sm font-semibold text-slate-700">
                  {selectedOutbound.created_at ? new Date(selectedOutbound.created_at).toLocaleString('vi-VN') : '-'}
                </span>
              </div>
            </div>

            <div className="space-y-3">
              <div>
                <span className="block text-xs font-bold uppercase text-slate-500">Khách hàng nhận</span>
                <span className="text-sm font-bold text-slate-900">{selectedOutbound.recipientName || '-'}</span>
              </div>
              <div>
                <span className="block text-xs font-bold uppercase text-slate-500">Số điện thoại</span>
                <span className="text-sm font-semibold text-slate-700">{selectedOutbound.recipientPhone || '-'}</span>
              </div>
              <div>
                <span className="block text-xs font-bold uppercase text-slate-500">Địa chỉ giao hàng</span>
                <span className="text-sm font-semibold text-slate-700">{selectedOutbound.shippingAddress || '-'}</span>
              </div>
            </div>

            <div className="space-y-3">
              <div>
                <span className="block text-xs font-bold uppercase text-slate-500">Ghi chú phiếu / giao hàng</span>
                <span className="text-sm font-semibold text-slate-700">{selectedOutbound.note || 'Không có ghi chú'}</span>
              </div>
              {!isSuperAdmin && !isCompleted && (
                <div className="rounded-md bg-amber-50 border border-amber-200 p-2 text-xs text-amber-800">
                  ⚠️ Tài khoản hiện tại không có quyền duyệt hoàn tất phiếu xuất kho. Chỉ Quản trị viên cấp cao (Super Admin) mới được phép hoàn tất.
                </div>
              )}
            </div>
          </div>
        </AdminPanel>

        {/* Lines Table */}
        <div className="rounded-lg border border-slate-200 bg-white shadow-sm overflow-hidden">
          <div className="border-b border-slate-200 bg-slate-50/50 px-4 py-3">
            <h3 className="text-sm font-bold text-slate-900">Danh sách sản phẩm cần xuất</h3>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-left text-sm">
              <thead className="bg-slate-50 text-xs font-bold uppercase text-slate-500 border-b border-slate-200">
                <tr>
                  <th className="px-4 py-3 w-12">STT</th>
                  <th className="px-4 py-3 w-64">Sản phẩm</th>
                  <th className="px-4 py-3 w-32 text-center">SL yêu cầu</th>
                  <th className="px-4 py-3">Kệ xuất & mã định danh</th>
                  <th className="px-4 py-3 w-32">Trạng thái</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {selectedOutbound.lines.map((line: any, index: number) => {
                  const allocations = line.allocations || [];
                  const allocatedQty = allocations.reduce((sum: number, a: any) => sum + Number(a.quantity || 0), 0);
                  const isMatched = allocatedQty === line.quantity;
                  const hasIdentifier = line.tracksImei || line.tracksSerialNumber;

                  return (
                    <tr key={line.id} className="hover:bg-slate-50/50 transition">
                      <td className="px-4 py-4 text-slate-500 valign-top align-top">{index + 1}</td>
                      <td className="px-4 py-4 valign-top align-top">
                        <div className="font-semibold text-slate-900">{line.productName}</div>
                        <div className="text-xs text-slate-500 font-mono mt-0.5">
                          SKU: {line.variantSku || line.productSku}
                        </div>
                        {(line.variantColor || line.variantConfiguration) && (
                          <div className="text-xs text-slate-600 mt-1">
                            {line.variantColor} {line.variantConfiguration ? ` - ${line.variantConfiguration}` : ''}
                          </div>
                        )}
                        <div className={`mt-2 text-xs font-bold ${isMatched ? 'text-emerald-700' : 'text-amber-700'}`}>
                          Đã chọn {allocatedQty} / {line.quantity} cái {allocatedQty > line.quantity && <span className="text-red-600 block mt-1">(Vượt quá số lượng yêu cầu!)</span>}
                        </div>
                      </td>
                      <td className="px-4 py-4 font-bold text-slate-900 text-center valign-top align-top">
                        {line.quantity}
                      </td>
                      <td className="px-4 py-4 space-y-3">
                        {allocations.map((alloc: any, allocIdx: number) => {
                          const imeiInputKey = `${line.id}_${allocIdx}_imei`;
                          const serialInputKey = `${line.id}_${allocIdx}_serial`;
                          const serialPickerKey = `${line.id}_${allocIdx}_serial_picker`;
                          const availableLocations = getLineAvailableLocations(line, alloc);
                          const availableSerials = (identifierCatalog[line.id]?.serialNumbers || []).filter((item: any) => (
                            item.status === 'IN_STOCK'
                            && String(item.locationId || '') === String(alloc.locationId || '')
                            && !(alloc.serialNumbers || []).includes(item.value)
                          ));
                          const serialQuery = String(scannedInputs[serialInputKey] || '').trim().toLowerCase();
                          const availableDevices = (identifierCatalog[line.id]?.identifierPairs || []).filter((item: any) => (
                            String(item.locationId || '') === String(alloc.locationId || '')
                            && !(alloc.serialNumbers || []).includes(item.serialNumber)
                          ));
                          const visibleSerials = (line.tracksImei && line.tracksSerialNumber ? availableDevices : availableSerials)
                            .filter((item: any) => !serialQuery || String(item.value || '').toLowerCase().includes(serialQuery))
                            .slice(0, 10);
                          const visibleDevices = availableDevices
                            .filter((item: any) => !serialQuery || String(item.serialNumber || '').toLowerCase().includes(serialQuery))
                            .slice(0, 10);

                          return (
                            <div key={allocIdx} className="rounded-md border border-slate-100 bg-slate-50/30 p-3 space-y-2">
                              <div className="flex flex-wrap items-center gap-3">
                                <div className="flex-1 min-w-[200px]">
                                  {isCompleted ? (
                                    <span className="font-mono text-sm font-bold text-slate-800">
                                      Kệ: {alloc.locationCode || 'Mặc định (MAIN)'}
                                    </span>
                                  ) : (
                                    <select
                                      value={alloc.locationId || ''}
                                      onChange={(e) => updateOutboundAllocation(line.id, allocIdx, {
                                        locationId: e.target.value,
                                        imeis: [],
                                        secondaryImeis: [],
                                        serialNumbers: [],
                                      })}
                                      className="w-full rounded-md border border-slate-200 px-2 py-1.5 text-xs outline-none transition focus:border-blue-500 bg-white"
                                    >
                                      <option value="">-- Chọn kệ đang có sản phẩm --</option>
                                      {availableLocations.map((loc: any) => (
                                        <option key={loc.locationId} value={loc.locationId}>
                                          {loc.locationCode} - {loc.locationName} (Tồn: {loc.onHandQuantity ?? loc.availableQuantity ?? 0} | Khả dụng: {loc.availableQuantity ?? 0})
                                        </option>
                                      ))}
                                    </select>
                                  )}
                                </div>

                                <div className="w-24">
                                  {isCompleted ? (
                                    <span className="text-xs font-bold text-slate-800">SL: {alloc.quantity} cái</span>
                                  ) : (
                                    <input
                                      type="number"
                                      min={1}
                                      value={alloc.quantity}
                                      onChange={(e) => updateOutboundAllocation(line.id, allocIdx, { quantity: Math.max(1, parseInt(e.target.value) || 1) })}
                                      className="w-full rounded-md border border-slate-200 px-2.5 py-1 text-xs outline-none focus:border-blue-500 bg-white"
                                      placeholder="Số lượng"
                                    />
                                  )}
                                </div>

                                {!isCompleted && allocations.length > 1 && (
                                  <button
                                    type="button"
                                    onClick={() => removeOutboundAllocation(line.id, allocIdx)}
                                    className="inline-flex h-7 w-7 items-center justify-center rounded-md border border-red-200 text-red-600 hover:bg-red-50"
                                    title="Xóa kệ xuất này"
                                  >
                                    <X className="h-4 w-4" />
                                  </button>
                                )}
                              </div>

                              {/* Identifier scanning per shelf */}
                              {hasIdentifier && (
                                <div className="space-y-2 pt-1 border-t border-dashed border-slate-100">
                                  {!isCompleted && (
                                    <>
                                    {line.tracksImei && line.tracksSerialNumber && (
                                      <button
                                        type="button"
                                        disabled={!alloc.locationId}
                                        onClick={() => void handleToggleDevicePicker(line, allocIdx)}
                                        className="inline-flex h-9 cursor-pointer items-center gap-2 rounded-md border border-indigo-200 bg-indigo-50 px-3 text-xs font-bold text-indigo-700 transition hover:bg-indigo-100 disabled:cursor-not-allowed disabled:opacity-40"
                                      >
                                        <Search className="h-4 w-4" /> Tìm máy theo IMEI hoặc Serial
                                      </button>
                                    )}
                                    <div className="flex flex-wrap gap-2">
                                      {line.tracksImei && (
                                        <div className="flex-1 min-w-[150px] flex gap-1">
                                          <input
                                            type="text"
                                            placeholder={line.tracksSerialNumber ? 'Nhập IMEI → tự điền Serial' : 'Quét/Nhập IMEI...'}
                                            value={scannedInputs[imeiInputKey] || ''}
                                            disabled={line.tracksSerialNumber && !alloc.locationId}
                                            onChange={(e) => setScannedInputs(prev => ({ ...prev, [imeiInputKey]: e.target.value }))}
                                            onKeyDown={(e) => {
                                              if (e.key === 'Enter') {
                                                e.preventDefault();
                                                handleAddAllocIdentifier(line.id, allocIdx, 'imei');
                                              }
                                            }}
                                            className="flex-1 rounded-md border border-slate-200 px-2 py-1 text-xs outline-none focus:border-blue-500 bg-white disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400"
                                          />
                                          <button
                                            type="button"
                                            onClick={() => handleAddAllocIdentifier(line.id, allocIdx, 'imei')}
                                            disabled={line.tracksSerialNumber && !alloc.locationId}
                                            aria-label="Tìm máy theo IMEI"
                                            className="inline-flex items-center justify-center rounded-md bg-blue-50 px-2 text-blue-700 hover:bg-blue-100 disabled:cursor-not-allowed disabled:opacity-40"
                                          >
                                            <Plus className="h-3 w-3" />
                                          </button>
                                        </div>
                                      )}

                                      {line.tracksSerialNumber && (
                                        <div className="relative flex-1 min-w-[220px] flex gap-1">
                                          <div className="relative flex-1">
                                            <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
                                            <input
                                              type="search"
                                              placeholder={alloc.locationId ? 'Nhập Serial để tìm máy...' : 'Chọn kệ trước'}
                                              value={scannedInputs[serialInputKey] || ''}
                                              disabled={!alloc.locationId}
                                              onFocus={() => setOpenSerialPicker(serialPickerKey)}
                                              onChange={(e) => {
                                                setScannedInputs(prev => ({ ...prev, [serialInputKey]: e.target.value }));
                                                setOpenSerialPicker(serialPickerKey);
                                              }}
                                              onKeyDown={(e) => {
                                                if (e.key === 'Enter') {
                                                  e.preventDefault();
                                                  const singleResult = line.tracksImei ? visibleDevices[0]?.serialNumber : visibleSerials[0]?.value;
                                                  if ((line.tracksImei ? visibleDevices : visibleSerials).length === 1 && singleResult) {
                                                    void handleAddAllocIdentifier(line.id, allocIdx, 'serial', singleResult);
                                                  }
                                                }
                                                if (e.key === 'Escape') setOpenSerialPicker(null);
                                              }}
                                              className="h-9 w-full rounded-md border border-slate-200 bg-white py-1 pl-8 pr-2 text-xs outline-none transition focus:border-purple-500 focus:ring-2 focus:ring-purple-100 disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400"
                                            />
                                            {openSerialPicker === serialPickerKey && alloc.locationId && (
                                              <div className="mt-1 max-h-60 overflow-y-auto rounded-md border border-slate-200 bg-white p-1 shadow-sm">
                                                <div className="px-2 py-1.5 text-[11px] font-bold text-slate-500">
                                                  Chọn máy theo serial tại {availableLocations.find((location: any) => String(location.locationId) === String(alloc.locationId))?.locationCode || 'kệ hiện tại'}
                                                </div>
                                                {loadingSerialPicker === serialPickerKey ? (
                                                  <div className="px-3 py-4 text-center text-xs font-semibold text-slate-500">Đang tải danh sách máy...</div>
                                                ) : (line.tracksImei ? visibleDevices : visibleSerials).length > 0 ? (line.tracksImei ? visibleDevices : visibleSerials).map((item: any) => (
                                                  <button
                                                    key={item.id || item.value}
                                                    type="button"
                                                    onMouseDown={(event) => event.preventDefault()}
                                                    onClick={() => void handleAddAllocIdentifier(line.id, allocIdx, 'serial', line.tracksImei ? item.serialNumber : item.value)}
                                                    className="flex min-h-10 w-full cursor-pointer items-center justify-between rounded px-2 py-2 text-left text-xs transition hover:bg-purple-50 focus:bg-purple-50 focus:outline-none"
                                                  >
                                                    <span>
                                                      <span className="block font-mono font-bold text-slate-800">{line.tracksImei ? item.serialNumber : item.value}</span>
                                                      {line.tracksImei && <span className="mt-0.5 block font-mono text-[10px] text-slate-500">IMEI: {item.imei1}{item.imei2 ? ` · IMEI 2: ${item.imei2}` : ''}</span>}
                                                    </span>
                                                    <span className="ml-3 text-[10px] text-slate-500">{item.locationCode}</span>
                                                  </button>
                                                )) : (
                                                  <div className="px-3 py-4 text-center text-xs text-slate-500">
                                                    {(line.tracksImei ? availableDevices : availableSerials).length === 0 ? 'Kệ này không có máy khả dụng.' : 'Không tìm thấy máy phù hợp.'}
                                                  </div>
                                                )}
                                              </div>
                                            )}
                                          </div>
                                          <button
                                            type="button"
                                            onClick={() => handleAddAllocIdentifier(line.id, allocIdx, 'serial')}
                                            disabled={!alloc.locationId}
                                            aria-label="Thêm serial đã chọn"
                                            className="inline-flex h-9 min-w-9 self-start items-center justify-center rounded-md bg-purple-50 px-2 text-purple-700 hover:bg-purple-100 disabled:cursor-not-allowed disabled:opacity-40"
                                          >
                                            <Plus className="h-3 w-3" />
                                          </button>
                                        </div>
                                      )}
                                    </div>
                                    </>
                                  )}

                                  {!isCompleted && line.tracksSerialNumber && alloc.locationId && (
                                    <div className="text-[11px] text-slate-500">
                                      Có {line.tracksImei ? availableDevices.length : availableSerials.length} {line.tracksImei ? 'máy' : 'serial'} khả dụng tại kệ này. {line.tracksImei ? 'Nhập IMEI để tự lấy serial, hoặc nhập serial để tự lấy IMEI.' : 'Nhập vài ký tự để tìm và chọn nhanh.'}
                                    </div>
                                  )}

                                  {/* List of scanned identifiers */}
                                  <div className="flex flex-wrap gap-1">
                                    {line.tracksImei && line.tracksSerialNumber ? (alloc.serialNumbers || []).map((serial: string, i: number) => (
                                      <span key={`device-${i}`} className="inline-flex items-center gap-2 rounded-md border border-indigo-200 bg-indigo-50 px-2 py-1 text-[10px] font-semibold text-indigo-800">
                                        <span className="font-bold">Máy {i + 1}</span>
                                        <span>IMEI: {alloc.imeis?.[i] || '-'}</span>
                                        {alloc.secondaryImeis?.[i] && <span>IMEI 2: {alloc.secondaryImeis[i]}</span>}
                                        <span>SN: {serial}</span>
                                        {!isCompleted && (
                                          <button
                                            type="button"
                                            aria-label={`Xóa máy ${i + 1}`}
                                            onClick={() => handleRemoveAllocDevice(line.id, allocIdx, i)}
                                            className="inline-flex h-5 w-5 items-center justify-center rounded text-indigo-500 hover:bg-indigo-100 hover:text-indigo-900"
                                          >
                                            <X className="h-3 w-3" />
                                          </button>
                                        )}
                                      </span>
                                    )) : (alloc.imeis || []).map((imei: string, i: number) => (
                                      <span key={`imei-${i}`} className="inline-flex items-center gap-1 rounded bg-blue-50 px-2 py-0.5 text-[10px] font-semibold text-blue-700 border border-blue-100">
                                        IMEI: {imei}
                                        {!isCompleted && (
                                          <button
                                            type="button"
                                            onClick={() => handleRemoveAllocIdentifier(line.id, allocIdx, 'imei', i)}
                                            className="text-blue-500 hover:text-blue-900"
                                          >
                                            <X className="h-2.5 w-2.5" />
                                          </button>
                                        )}
                                      </span>
                                    ))}
                                    {!line.tracksSerialNumber && (alloc.secondaryImeis || []).map((imei: string, i: number) => (
                                      <span key={`imei2-${i}`} className="inline-flex items-center gap-1 rounded bg-cyan-50 px-2 py-0.5 text-[10px] font-semibold text-cyan-700 border border-cyan-100">
                                        IMEI2: {imei}
                                      </span>
                                    ))}
                                    {!line.tracksImei && (alloc.serialNumbers || []).map((serial: string, i: number) => (
                                      <span key={`serial-${i}`} className="inline-flex items-center gap-1 rounded bg-purple-50 px-2 py-0.5 text-[10px] font-semibold text-purple-700 border border-purple-100">
                                        SN: {serial}
                                        {!isCompleted && (
                                          <button
                                            type="button"
                                            onClick={() => handleRemoveAllocIdentifier(line.id, allocIdx, 'serial', i)}
                                            className="text-purple-500 hover:text-purple-900"
                                          >
                                            <X className="h-2.5 w-2.5" />
                                          </button>
                                        )}
                                      </span>
                                    ))}
                                    {((alloc.imeis || []).length === 0 && (alloc.serialNumbers || []).length === 0) && (
                                      <span className="text-[10px] italic text-slate-400">Chưa quét mã định danh</span>
                                    )}
                                  </div>

                                  <div className="text-[10px] text-slate-500 font-semibold">
                                    Đã quét: {
                                      line.tracksImei && line.tracksSerialNumber
                                        ? Math.max((alloc.imeis || []).length, (alloc.serialNumbers || []).length)
                                        : (line.tracksImei ? (alloc.imeis || []).length : (alloc.serialNumbers || []).length)
                                    } / {alloc.quantity}
                                  </div>
                                </div>
                              )}
                            </div>
                          );
                        })}

                        {!isCompleted && (
                          <button
                            type="button"
                            onClick={() => addOutboundAllocation(line.id)}
                            className="inline-flex h-8 items-center gap-1.5 rounded-md border border-slate-200 px-3 text-xs font-bold text-slate-700 transition hover:bg-slate-50"
                          >
                            <Plus className="h-3.5 w-3.5" /> Thêm kệ xuất
                          </button>
                        )}
                      </td>
                      <td className="px-4 py-4 valign-top align-top">
                        {renderLineStatusBadge(line)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    );
  }

  // List View Mode
  return (
    <div className="space-y-6">
      {/* Top search & filter panel */}
      <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <form onSubmit={handleSearchSubmit} className="grid grid-cols-1 gap-4 md:grid-cols-5">
          <div className="md:col-span-2">
            <label className="block text-xs font-bold uppercase text-slate-500 mb-1.5">Từ khóa tìm kiếm</label>
            <div className="relative">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Tìm mã phiếu, mã đơn hàng, khách hàng..."
                className="w-full rounded-md border border-slate-200 py-1.5 pl-8 pr-3 text-sm outline-none transition focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
              />
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-slate-400" />
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold uppercase text-slate-500 mb-1.5">Trạng thái phiếu</label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="w-full rounded-md border border-slate-200 px-2 py-1.5 text-sm outline-none transition focus:border-blue-500"
            >
              <option value="">Tất cả trạng thái</option>
              <option value="DRAFT">Nháp (Chờ đóng hàng)</option>
              <option value="PICKING">Đang đóng hàng</option>
              <option value="PICKED">Đã đóng đủ hàng (Chờ duyệt)</option>
              <option value="COMPLETED">Đã xuất kho</option>
              <option value="CANCELLED">Đã hủy</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-bold uppercase text-slate-500 mb-1.5">Từ ngày</label>
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="w-full rounded-md border border-slate-200 px-2.5 py-1 text-sm outline-none transition focus:border-blue-500"
            />
          </div>

          <div>
            <label className="block text-xs font-bold uppercase text-slate-500 mb-1.5">Đến ngày</label>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="w-full rounded-md border border-slate-200 px-2.5 py-1 text-sm outline-none transition focus:border-blue-500"
            />
          </div>
        </form>

        <div className="mt-4 flex justify-end gap-2 border-t border-slate-100 pt-3">
          <button
            type="button"
            onClick={handleResetFilters}
            className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
          >
            Nhập lại bộ lọc
          </button>
          <button
            type="button"
            onClick={handleSearchSubmit}
            className="rounded-md bg-slate-950 px-4 py-1.5 text-xs font-semibold text-white hover:bg-slate-800"
          >
            Tìm kiếm
          </button>
        </div>
      </div>

      {/* Main List Table */}
      {errorMsg && (
        <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm font-medium text-red-800">
          {errorMsg}
        </div>
      )}

      {loading ? (
        <div className="rounded-lg border border-slate-200 bg-white py-12 text-center text-sm font-semibold text-slate-500">
          Đang tải danh sách phiếu xuất kho...
        </div>
      ) : outbounds.length === 0 ? (
        <div className="rounded-lg border border-slate-200 bg-white py-12 text-center text-slate-500">
          <ClipboardList className="mx-auto h-12 w-12 text-slate-300" />
          <h3 className="mt-2 text-sm font-bold text-slate-900">Không tìm thấy phiếu xuất kho nào</h3>
          <p className="mt-1 text-xs text-slate-500">Thử thay đổi bộ lọc hoặc thêm đơn hàng mới.</p>
        </div>
      ) : (
        <AdminTable headers={['Mã phiếu xuất', 'Trạng thái', 'Đơn hàng liên kết', 'Khách hàng', 'Người tạo', 'Ngày tạo', 'Số dòng', 'Thao tác']}>
          {outbounds.map((item: any) => (
            <tr key={item.id} className="hover:bg-slate-50/50 transition">
              <td className="px-4 py-3.5 font-mono text-xs font-bold text-slate-800">
                {item.document_no}
              </td>
              <td className="px-4 py-3.5">
                <AdminBadge tone={outboundStatusTone[item.status] || 'slate'}>
                  {outboundStatusLabel[item.status] || item.status}
                </AdminBadge>
              </td>
              <td className="px-4 py-3.5 font-mono text-xs font-semibold text-slate-700">
                <div>{item.orderCode || '-'}</div>
                {item.afterSalesRequestCode && (
                  <div className="mt-1 text-[11px] font-bold text-cyan-700">
                    Hậu mãi: {item.afterSalesRequestCode}
                  </div>
                )}
              </td>
              <td className="px-4 py-3.5">
                <div className="text-sm font-bold text-slate-900">{item.recipientName || '-'}</div>
                {item.recipientPhone && (
                  <div className="text-xs text-slate-500 font-medium mt-0.5">{item.recipientPhone}</div>
                )}
              </td>
              <td className="px-4 py-3.5 text-sm text-slate-600">
                {item.createdByName || item.created_by || '-'}
              </td>
              <td className="px-4 py-3.5 text-xs text-slate-500">
                {item.created_at ? new Date(item.created_at).toLocaleString('vi-VN') : '-'}
              </td>
              <td className="px-4 py-3.5 text-sm font-bold text-slate-800 text-center">
                {item.lines?.length || 0}
              </td>
              <td className="px-4 py-3.5">
                <button
                  type="button"
                  onClick={() => void loadDetail(item.document_no)}
                  className="inline-flex h-8 items-center gap-1.5 rounded-md border border-slate-200 bg-white px-2.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 hover:text-slate-900 transition"
                >
                  <Eye className="h-3.5 w-3.5" /> Chi tiết
                </button>
              </td>
            </tr>
          ))}
        </AdminTable>
      )}

      {/* Modal Popup để nhập lý do hủy phiếu */}
      {cancelModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-2xl space-y-4 animate-in fade-in zoom-in-95 duration-200">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="text-base font-bold text-slate-900">Yêu cầu lý do hủy phiếu</h3>
              <button
                type="button"
                onClick={() => setCancelModalOpen(false)}
                className="rounded-md p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="space-y-2">
              <label htmlFor="cancel-reason-textarea" className="text-xs font-bold text-slate-700 block">
                Lý do hủy (bảt buộc)
              </label>
              <textarea
                id="cancel-reason-textarea"
                value={cancelReasonInput}
                onChange={(e) => setCancelReasonInput(e.target.value)}
                placeholder="Nhập lý do chi tiết..."
                className="w-full rounded-md border border-slate-200 p-2 text-sm focus:border-red-500 focus:outline-none focus:ring-1 focus:ring-red-500 min-h-[100px]"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setCancelModalOpen(false)}
                className="rounded-md border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 transition"
              >
                Hủy bỏ
              </button>
              <button
                type="button"
                onClick={confirmCancelOutbound}
                disabled={!cancelReasonInput.trim()}
                className="rounded-md bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Xác nhận hủy
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
