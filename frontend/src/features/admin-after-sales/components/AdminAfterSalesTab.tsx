import { useEffect, useMemo, useState } from 'react';
import { adminAfterSalesApi } from '../services/adminAfterSalesApi';

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

const actionLabel: Record<string, string> = {
  RECEIVED: 'Tiếp nhận máy',
  QC_IN_PROGRESS: 'Bắt đầu kiểm QC',
  QC_APPROVED: 'Duyệt đổi trả',
  WARRANTY_ACCEPTED: 'Chấp nhận bảo hành',
  REPAIRING: 'Bắt đầu sửa chữa',
  READY_TO_RETURN: 'Sẵn sàng trả khách',
  REPLACEMENT_APPROVED: 'Duyệt đổi máy mới',
  REPLACEMENT_PROCESSING: 'Đang đổi máy',
  EXCHANGE_PROCESSING: 'Đang đổi máy',
  REFUND_PROCESSING: 'Đang hoàn tiền',
  COMPLETED: 'Hoàn tất hồ sơ',
  REJECTED: 'Từ chối yêu cầu',
};

const actionStyles: Record<string, string> = {
  RECEIVED: 'bg-indigo-50 text-indigo-700 hover:bg-indigo-100 border border-indigo-200',
  QC_IN_PROGRESS: 'bg-blue-50 text-blue-700 hover:bg-blue-100 border border-blue-200',
  QC_APPROVED: 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100 border border-emerald-200',
  WARRANTY_ACCEPTED: 'bg-teal-50 text-teal-700 hover:bg-teal-100 border border-teal-200',
  REPAIRING: 'bg-amber-50 text-amber-700 hover:bg-amber-100 border border-amber-200',
  READY_TO_RETURN: 'bg-purple-50 text-purple-700 hover:bg-purple-100 border border-purple-200',
  REPLACEMENT_APPROVED: 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100 border border-emerald-200',
  REPLACEMENT_PROCESSING: 'bg-cyan-50 text-cyan-700 hover:bg-cyan-100 border border-cyan-200',
  EXCHANGE_PROCESSING: 'bg-cyan-50 text-cyan-700 hover:bg-cyan-100 border border-cyan-200',
  REFUND_PROCESSING: 'bg-amber-50 text-amber-700 hover:bg-amber-100 border border-amber-200',
  COMPLETED: 'bg-slate-900 text-white hover:bg-slate-800 shadow-sm',
  REJECTED: 'bg-rose-50 text-rose-700 hover:bg-rose-100 border border-rose-200',
};

const dispositionStatusLabels: Record<string, string> = {
  DEFECTIVE_RETURNED: 'Lỗi trả về',
  INSPECTION_PENDING: 'Chờ thẩm định QC',
  RTV_PENDING: 'Chờ trả NCC (RTV)',
  LIQUIDATION_PENDING: 'Chờ thanh lý',
  RTV_COMPLETED: 'Đã trả NCC (RTV xong)',
  LIQUIDATED: 'Đã thanh lý',
  SCRAP: 'Hủy phế phẩm (Scrap)',
  OUT_OF_SYSTEM: 'Đã xuất khỏi HT',
};

const completedDispositionStatuses = ['RTV_COMPLETED', 'LIQUIDATED', 'SCRAP', 'OUT_OF_SYSTEM'];

const statusStyles: Record<string, { bg: string; text: string; border: string }> = {
  SUBMITTED: { bg: 'bg-slate-50', text: 'text-slate-650', border: 'border-slate-200' },
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
  CANCELLED: { bg: 'bg-slate-100', text: 'text-slate-500', border: 'border-slate-200' },
  CLOSED_EXPIRED: { bg: 'bg-slate-100', text: 'text-slate-500', border: 'border-slate-200' },
};

const returnActions: Record<string, string[]> = {
  SUBMITTED: ['RECEIVED', 'REJECTED'],
  RECEIVED: ['QC_IN_PROGRESS', 'REJECTED'],
  QC_IN_PROGRESS: ['QC_APPROVED', 'REJECTED'],
  QC_APPROVED: ['EXCHANGE_PROCESSING', 'REFUND_PROCESSING'],
  WAITING_FOR_STOCK: ['QC_APPROVED', 'EXCHANGE_PROCESSING'],
  EXCHANGE_PROCESSING: ['COMPLETED'],
  REFUND_PROCESSING: ['COMPLETED'],
};

const warrantyActions: Record<string, string[]> = {
  SUBMITTED: ['RECEIVED', 'REJECTED'],
  RECEIVED: ['QC_IN_PROGRESS', 'REJECTED'],
  QC_IN_PROGRESS: ['WARRANTY_ACCEPTED', 'REPLACEMENT_APPROVED', 'REJECTED'],
  WARRANTY_ACCEPTED: ['REPAIRING', 'READY_TO_RETURN'],
  REPAIRING: ['READY_TO_RETURN'],
  REPLACEMENT_APPROVED: ['REPLACEMENT_PROCESSING'],
  WAITING_FOR_STOCK: ['REPLACEMENT_APPROVED', 'REPLACEMENT_PROCESSING'],
  REPLACEMENT_PROCESSING: ['READY_TO_RETURN', 'COMPLETED'],
  READY_TO_RETURN: ['COMPLETED'],
};

export default function AdminAfterSalesTab() {
  const [section, setSection] = useState<'returns' | 'warranties' | 'defective'>('returns');
  const [returns, setReturns] = useState<any[]>([]);
  const [warranties, setWarranties] = useState<any[]>([]);
  const [defective, setDefective] = useState<any[]>([]);
  const [defectiveReport, setDefectiveReport] = useState<any>({ summary: {}, byStatus: [], byBrand: [], topProducts: [] });
  const [message, setMessage] = useState('');

  // States dành cho Modal xử lý đổi trạng thái
  const [showAdvanceModal, setShowAdvanceModal] = useState(false);
  const [modalRequest, setModalRequest] = useState<any>(null);
  const [modalTargetStatus, setModalTargetStatus] = useState('');
  const [note, setNote] = useState('');
  const [replacementImei, setReplacementImei] = useState('');
  const [depreciationFee, setDepreciationFee] = useState('');
  const [repairDiagnosis, setRepairDiagnosis] = useState('');
  const [repairAction, setRepairAction] = useState('');
  const [repairParts, setRepairParts] = useState('');
  const [repairCost, setRepairCost] = useState('');
  const [busy, setBusy] = useState(false);

  // States dành cho Modal xem chi tiết
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [detailRequest, setDetailRequest] = useState<any>(null);
  const [detailEvents, setDetailEvents] = useState<any[]>([]);
  const [detailEventsLoading, setDetailEventsLoading] = useState(false);
  const [timelineNote, setTimelineNote] = useState('');
  const [timelineNoteBusy, setTimelineNoteBusy] = useState(false);

  // States dành cho Modal xử lý IMEI lỗi (Disposition)
  const [showDispositionModal, setShowDispositionModal] = useState(false);
  const [selectedDefective, setSelectedDefective] = useState<any>(null);
  const [dispositionEvents, setDispositionEvents] = useState<any[]>([]);
  const [dispositionEventsLoading, setDispositionEventsLoading] = useState(false);
  const [dispStatus, setDispStatus] = useState('INSPECTION_PENDING');
  const [dispReason, setDispReason] = useState('');
  const [docRef, setDocRef] = useState('');
  const [partner, setPartner] = useState('');
  const [recoveryVal, setRecoveryVal] = useState('0');
  const [defectiveQuery, setDefectiveQuery] = useState('');
  const [defectiveStatusFilter, setDefectiveStatusFilter] = useState('all');
  const [defectiveQuickFilter, setDefectiveQuickFilter] = useState<'all' | 'processing' | 'completed' | 'documented' | 'recovered'>('all');

  async function load() {
    try {
      const [returnData, warrantyData, defectiveData, defectiveReportData] = await Promise.all([
        adminAfterSalesApi.listReturns(),
        adminAfterSalesApi.listWarranties(),
        adminAfterSalesApi.listDefectiveIdentifiers(),
        adminAfterSalesApi.getDefectiveDispositionReport(),
      ]);
      setReturns(returnData.items || []);
      setWarranties(warrantyData.items || []);
      setDefective(defectiveData || []);
      setDefectiveReport(defectiveReportData || { summary: {}, byStatus: [], byBrand: [], topProducts: [] });
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Không thể tải dữ liệu hậu mãi.');
    }
  }

  useEffect(() => {
    void load();
  }, []);

  // Mở modal để đổi trạng thái
  const handleOpenAdvanceModal = (item: any, status: string) => {
    setModalRequest(item);
    setModalTargetStatus(status);
    setNote('');
    setReplacementImei('');
    setDepreciationFee(String(item.depreciationFee || ''));
    setRepairDiagnosis(String(item.repairSummary?.diagnosis || ''));
    setRepairAction(String(item.repairSummary?.action || ''));
    setRepairParts(String(item.repairSummary?.parts || ''));
    setRepairCost(item.repairSummary?.cost ? String(item.repairSummary.cost) : '');
    setShowAdvanceModal(true);
  };

  // Xác nhận đổi trạng thái từ Modal
  const handleConfirmAdvance = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!modalRequest) return;

    // Validate IMEI thay thế nếu hoàn tất đổi máy
    const needsImei = modalTargetStatus === 'COMPLETED' && ['EXCHANGE_PROCESSING', 'REPLACEMENT_PROCESSING'].includes(modalRequest.status);
    if (needsImei && !replacementImei.trim()) {
      alert('Vui lòng nhập số IMEI của máy mới thay thế.');
      return;
    }

    setBusy(true);
    try {
      const resolutionType = modalTargetStatus === 'QC_APPROVED' ? 'EXCHANGE' :
                             modalTargetStatus === 'REFUND_PROCESSING' ? 'REFUND' :
                             modalTargetStatus === 'REPLACEMENT_APPROVED' ? 'REPLACEMENT' : undefined;

      const api = section === 'returns' ? adminAfterSalesApi.updateReturn : adminAfterSalesApi.updateWarranty;
      await api(modalRequest.id, {
        status: modalTargetStatus,
        resolution_type: resolutionType,
        note: note.trim() || undefined,
        replacement_imei: replacementImei.trim() || undefined,
        depreciation_fee: section === 'returns' ? Number(depreciationFee || 0) : 0,
        repair_diagnosis: section === 'warranties' ? repairDiagnosis.trim() || undefined : undefined,
        repair_action: section === 'warranties' ? repairAction.trim() || undefined : undefined,
        repair_parts: section === 'warranties' ? repairParts.trim() || undefined : undefined,
        repair_cost: section === 'warranties' ? Number(repairCost || 0) : 0,
      });

      setShowAdvanceModal(false);
      await load();

      // Cập nhật lại chi tiết nếu đang mở xem chi tiết
      if (detailRequest && detailRequest.id === modalRequest.id) {
        const list = section === 'returns' ? returns : warranties;
        const updated = list.find(r => r.id === modalRequest.id);
        if (updated) setDetailRequest(updated);
      }
    } catch (error) {
      alert(error instanceof Error ? error.message : 'Không thể cập nhật trạng thái.');
    } finally {
      setBusy(false);
    }
  };

  // Xem chi tiết hồ sơ
  async function loadDetailEvents(item: any) {
    setDetailEventsLoading(true);
    try {
      const loader = section === 'returns' ? adminAfterSalesApi.listReturnEvents : adminAfterSalesApi.listWarrantyEvents;
      const events = await loader(item.id);
      setDetailEvents(Array.isArray(events) ? events : []);
    } catch (error) {
      console.error('Không thể tải timeline hậu mãi:', error);
      setDetailEvents([]);
    } finally {
      setDetailEventsLoading(false);
    }
  }

  const handleOpenDetailModal = async (item: any) => {
    setDetailRequest(item);
    setDetailEvents([]);
    setTimelineNote('');
    setShowDetailModal(true);
    await loadDetailEvents(item);
  };

  async function handleAddTimelineNote() {
    if (!detailRequest || timelineNote.trim().length < 3) return;
    setTimelineNoteBusy(true);
    try {
      const api = section === 'returns' ? adminAfterSalesApi.addReturnEvent : adminAfterSalesApi.addWarrantyEvent;
      await api(detailRequest.id, { note: timelineNote.trim() });
      setTimelineNote('');
      await loadDetailEvents(detailRequest);
    } catch (error) {
      alert(error instanceof Error ? error.message : 'Không thể thêm ghi chú timeline.');
    } finally {
      setTimelineNoteBusy(false);
    }
  };

  // Mở modal Disposition IMEI lỗi
  async function loadDispositionEvents(item: any) {
    setDispositionEventsLoading(true);
    try {
      const rows = await adminAfterSalesApi.listDispositionEvents(String(item.id));
      setDispositionEvents(Array.isArray(rows) ? rows : []);
    } catch (error) {
      console.error('Không thể tải lịch sử định đoạt IMEI:', error);
      setDispositionEvents([]);
    } finally {
      setDispositionEventsLoading(false);
    }
  }

  const handleOpenDispositionModal = (item: any) => {
    setSelectedDefective(item);
    setDispositionEvents([]);
    setDispStatus(item.status);
    setDispReason('');
    setDocRef('');
    setPartner('');
    setRecoveryVal('0');
    setShowDispositionModal(true);
    void loadDispositionEvents(item);
  };

  // Xác nhận Disposition IMEI lỗi
  const handleConfirmDisposition = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedDefective) return;

    setBusy(true);
    try {
      await adminAfterSalesApi.updateDisposition(selectedDefective.id, {
        status: dispStatus,
        reason: dispReason.trim() || 'Xử lý định đoạt IMEI lỗi.',
        document_reference: docRef.trim() || undefined,
        partner_name: partner.trim() || undefined,
        recovery_value: parseFloat(recoveryVal) || 0
      });
      await loadDispositionEvents(selectedDefective);
      setShowDispositionModal(false);
      await load();
    } catch (error) {
      alert(error instanceof Error ? error.message : 'Không thể cập nhật định đoạt.');
    } finally {
      setBusy(false);
    }
  };

  const requests = section === 'returns' ? returns : warranties;
  const actions = section === 'returns' ? returnActions : warrantyActions;
  const filteredDefective = useMemo(() => {
    const query = defectiveQuery.trim().toLowerCase();

    return defective.filter(item => {
      const latest = item.latestDisposition || {};
      const recoveryValue = Number(latest.recoveryValue || 0);
      const matchesStatus = defectiveStatusFilter === 'all' || item.status === defectiveStatusFilter;
      const matchesQuickFilter =
        defectiveQuickFilter === 'all'
        || (defectiveQuickFilter === 'processing' && !completedDispositionStatuses.includes(item.status))
        || (defectiveQuickFilter === 'completed' && completedDispositionStatuses.includes(item.status))
        || (defectiveQuickFilter === 'documented' && Boolean(latest.documentReference))
        || (defectiveQuickFilter === 'recovered' && recoveryValue > 0);
      const searchable = [
        item.identifier,
        item.productName,
        item.status,
        latest.documentReference,
        latest.partnerName,
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase();

      return matchesStatus && matchesQuickFilter && (!query || searchable.includes(query));
    });
  }, [defective, defectiveQuery, defectiveQuickFilter, defectiveStatusFilter]);

  const defectiveQuickCounts = useMemo(() => {
    return defective.reduce(
      (summary, item) => {
        const latest = item.latestDisposition || {};
        const recoveryValue = Number(latest.recoveryValue || 0);
        const completed = completedDispositionStatuses.includes(item.status);

        summary.all += 1;
        if (!completed) summary.processing += 1;
        if (completed) summary.completed += 1;
        if (latest.documentReference) summary.documented += 1;
        if (recoveryValue > 0) summary.recovered += 1;
        return summary;
      },
      { all: 0, processing: 0, completed: 0, documented: 0, recovered: 0 },
    );
  }, [defective]);

  const defectiveSummary = useMemo(() => {
    return filteredDefective.reduce(
      (summary, item) => {
        const latest = item.latestDisposition || {};
        const averageUnitCost = Number(item.averageUnitCost || 0);
        const recoveryValue = Number(latest.recoveryValue || 0);

        summary.total += 1;
        summary.inventoryValue += averageUnitCost;
        summary.recoveryValue += recoveryValue;
        if (latest.documentReference) summary.documented += 1;
        if (completedDispositionStatuses.includes(item.status)) {
          summary.completed += 1;
        }
        return summary;
      },
      { total: 0, inventoryValue: 0, recoveryValue: 0, documented: 0, completed: 0 },
    );
  }, [filteredDefective]);

  const reportSummary = defectiveReport?.summary || {};
  const reportByStatus = Array.isArray(defectiveReport?.byStatus) ? defectiveReport.byStatus : [];
  const reportByBrand = Array.isArray(defectiveReport?.byBrand) ? defectiveReport.byBrand : [];
  const reportTopProducts = Array.isArray(defectiveReport?.topProducts) ? defectiveReport.topProducts : [];
  const recoveryRate = Number(reportSummary.inventoryValue || 0) > 0
    ? Math.round((Number(reportSummary.recoveryValue || 0) / Number(reportSummary.inventoryValue || 0)) * 100)
    : 0;

  function handleExportDefectiveCsv() {
    if (!filteredDefective.length) return;

    const escapeCsv = (value: unknown) => {
      const text = String(value ?? '');
      return `"${text.replace(/"/g, '""')}"`;
    };
    const headers = [
      'IMEI',
      'Sản phẩm',
      'Trạng thái',
      'Giá trị trung bình',
      'Chứng từ',
      'Đối tác',
      'Giá trị thu hồi',
      'Cập nhật gần nhất',
    ];
    const rows = filteredDefective.map(item => {
      const latest = item.latestDisposition || {};
      return [
        item.identifier,
        item.productName,
        dispositionStatusLabels[item.status] || item.status,
        Number(item.averageUnitCost || 0),
        latest.documentReference || '',
        latest.partnerName || '',
        Number(latest.recoveryValue || 0),
        latest.createdAt ? new Date(latest.createdAt).toLocaleString('vi-VN') : '',
      ];
    });
    const csv = [headers, ...rows].map(row => row.map(escapeCsv).join(',')).join('\r\n');
    const blob = new Blob([`\uFEFF${csv}`], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `imei-loi-${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-6">
      {/* Tab Selector */}
      <div className="flex flex-wrap gap-2 border-b border-slate-100 pb-3">
        {([
          ['returns', 'Yêu cầu đổi trả'],
          ['warranties', 'Yêu cầu bảo hành'],
          ['defective', 'Quản lý IMEI lỗi']
        ] as const).map(([id, label]) => (
          <button
            key={id}
            onClick={() => setSection(id)}
            className={`rounded-xl px-5 py-2.5 text-xs font-bold transition-all ${
              section === id
                ? 'bg-slate-900 text-white shadow-sm'
                : 'bg-white text-slate-500 hover:bg-slate-50 border border-slate-100'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {message && (
        <div className="rounded-xl bg-rose-50 border border-rose-100 p-4 text-sm text-rose-850 font-medium">
          {message}
        </div>
      )}

      {/* Tables list */}
      {section !== 'defective' ? (
        <div className="overflow-x-auto rounded-2xl border border-slate-100 bg-white shadow-sm">
          <table className="w-full text-left text-sm divide-y divide-slate-100">
            <thead>
              <tr className="bg-slate-50/50 text-slate-500 font-bold">
                <th className="p-4 text-xs uppercase tracking-wider">Mã hồ sơ</th>
                <th className="p-4 text-xs uppercase tracking-wider">Đơn hàng</th>
                <th className="p-4 text-xs uppercase tracking-wider">Sản phẩm cần xử lý</th>
                <th className="p-4 text-xs uppercase tracking-wider text-center">Trạng thái</th>
                <th className="p-4 text-xs uppercase tracking-wider">Hạn xử lý (SLA)</th>
                <th className="p-4 text-xs uppercase tracking-wider text-right">Hành động</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {requests.map(item => {
                const style = statusStyles[item.status] || { bg: 'bg-slate-50', text: 'text-slate-700', border: 'border-slate-200' };
                const isOverSLA = item.slaBreachedAt || (item.slaDueAt && new Date(item.slaDueAt) < new Date());

                return (
                  <tr key={item.id} className="hover:bg-slate-50/50 transition-colors align-middle">
                    <td className="p-4 font-bold text-slate-900">{item.requestCode}</td>
                    <td className="p-4 text-slate-500 font-medium">#{item.orderCode}</td>
                    <td className="p-4">
                      {(item.items || []).map((line: any) => (
                        <div key={line.id} className="text-xs font-semibold text-slate-700">
                          {line.productName}
                          {line.imei && <span className="text-[10px] text-slate-400 font-normal ml-1">(IMEI: {line.imei})</span>}
                        </div>
                      ))}
                      {section === 'warranties' && item.repairSummary?.diagnosis && (
                        <div className="mt-1 rounded-lg bg-amber-50 px-2 py-1 text-[10px] font-semibold text-amber-800">
                          Chẩn đoán: {item.repairSummary.diagnosis}
                        </div>
                      )}
                    </td>
                    <td className="p-4 text-center">
                      <span className={`inline-flex items-center rounded-lg px-2.5 py-0.5 text-xs font-bold border ${style.bg} ${style.text} ${style.border}`}>
                        {statusLabel[item.status] || item.status}
                      </span>
                    </td>
                    <td className="p-4">
                      {isOverSLA ? (
                        <span className="text-xs font-bold text-rose-600 bg-rose-50 border border-rose-100 px-2 py-0.5 rounded-lg">Trễ SLA</span>
                      ) : item.slaDueAt ? (
                        <span className="text-xs text-slate-500 font-medium">{new Date(item.slaDueAt).toLocaleString('vi-VN')}</span>
                      ) : (
                        <span className="text-slate-300">-</span>
                      )}
                    </td>
                    <td className="p-4 text-right space-x-2">
                      <button
                        onClick={() => void handleOpenDetailModal(item)}
                        className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-bold text-slate-650 hover:bg-slate-50 hover:text-slate-900 transition-colors"
                      >
                        Chi tiết
                      </button>
                      <div className="inline-flex gap-1.5">
                        {(actions[item.status] || []).map(status => (
                          <button
                            key={status}
                            onClick={() => handleOpenAdvanceModal(item, status)}
                            className={`rounded-lg px-3 py-1.5 text-xs font-bold transition-all ${
                              actionStyles[status] || 'bg-slate-800 text-white hover:bg-slate-750'
                            }`}
                          >
                            {actionLabel[status] || status}
                          </button>
                        ))}
                      </div>
                    </td>
                  </tr>
                );
              })}
              {!requests.length && (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-sm text-slate-400 font-medium">
                    Không tìm thấy yêu cầu hậu mãi nào.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      ) : (
        /* Defective IMEI identifiers tab */
        <div className="space-y-3">
          <section className="rounded-xl border border-slate-100 bg-white p-4 shadow-sm">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <div>
                <h3 className="text-sm font-extrabold text-slate-900">Báo cáo hàng lỗi và giá trị thu hồi</h3>
                <p className="mt-1 text-xs font-semibold text-slate-500">Tổng hợp theo dữ liệu định đoạt IMEI lỗi, RTV, thanh lý và hủy phế phẩm.</p>
              </div>
              <span className="rounded-lg border border-emerald-100 bg-emerald-50 px-3 py-1.5 text-xs font-bold text-emerald-700">
                Tỷ lệ thu hồi {recoveryRate}%
              </span>
            </div>
            <div className="grid gap-3 md:grid-cols-4">
              <div className="rounded-lg border border-slate-100 bg-slate-50/60 p-3">
                <div className="text-xs font-bold uppercase tracking-wider text-slate-400">Tổng IMEI lỗi</div>
                <div className="mt-2 text-2xl font-extrabold text-slate-900">{Number(reportSummary.total || 0)}</div>
                <div className="mt-1 text-xs font-semibold text-slate-500">Đang xử lý: {Number(reportSummary.processing || 0)}</div>
              </div>
              <div className="rounded-lg border border-slate-100 bg-slate-50/60 p-3">
                <div className="text-xs font-bold uppercase tracking-wider text-slate-400">Đã định đoạt</div>
                <div className="mt-2 text-2xl font-extrabold text-slate-900">{Number(reportSummary.completed || 0)}</div>
                <div className="mt-1 text-xs font-semibold text-slate-500">Có chứng từ: {Number(reportSummary.documented || 0)}</div>
              </div>
              <div className="rounded-lg border border-emerald-100 bg-emerald-50/60 p-3">
                <div className="text-xs font-bold uppercase tracking-wider text-emerald-700">Giá trị thu hồi</div>
                <div className="mt-2 text-lg font-extrabold text-emerald-800">{Number(reportSummary.recoveryValue || 0).toLocaleString('vi-VN')}đ</div>
                <div className="mt-1 text-xs font-semibold text-emerald-700">Có thu hồi: {Number(reportSummary.recovered || 0)}</div>
              </div>
              <div className="rounded-lg border border-rose-100 bg-rose-50/60 p-3">
                <div className="text-xs font-bold uppercase tracking-wider text-rose-700">Tổn thất ròng</div>
                <div className="mt-2 text-lg font-extrabold text-rose-800">{Number(reportSummary.netLossValue || 0).toLocaleString('vi-VN')}đ</div>
                <div className="mt-1 text-xs font-semibold text-rose-700">Vốn: {Number(reportSummary.inventoryValue || 0).toLocaleString('vi-VN')}đ</div>
              </div>
            </div>
            <div className="mt-4 grid gap-4 lg:grid-cols-3">
              <div className="rounded-lg border border-slate-100 p-3">
                <div className="mb-2 text-xs font-bold uppercase tracking-wider text-slate-400">Theo trạng thái</div>
                <div className="space-y-2">
                  {reportByStatus.slice(0, 6).map((row: any) => (
                    <div key={row.status} className="flex items-center justify-between gap-3 text-xs">
                      <span className="font-bold text-slate-700">{dispositionStatusLabels[row.status] || row.status}</span>
                      <span className="font-mono font-bold text-slate-900">{row.count}</span>
                    </div>
                  ))}
                  {!reportByStatus.length && <div className="text-xs font-semibold text-slate-400">Chưa có dữ liệu.</div>}
                </div>
              </div>
              <div className="rounded-lg border border-slate-100 p-3">
                <div className="mb-2 text-xs font-bold uppercase tracking-wider text-slate-400">Brand lỗi nhiều</div>
                <div className="space-y-2">
                  {reportByBrand.slice(0, 6).map((row: any) => (
                    <div key={row.brandName} className="flex items-center justify-between gap-3 text-xs">
                      <span className="font-bold text-slate-700">{row.brandName}</span>
                      <span className="font-mono font-bold text-slate-900">{row.count}</span>
                    </div>
                  ))}
                  {!reportByBrand.length && <div className="text-xs font-semibold text-slate-400">Chưa có dữ liệu.</div>}
                </div>
              </div>
              <div className="rounded-lg border border-slate-100 p-3">
                <div className="mb-2 text-xs font-bold uppercase tracking-wider text-slate-400">Sản phẩm cần chú ý</div>
                <div className="space-y-2">
                  {reportTopProducts.slice(0, 5).map((row: any) => (
                    <div key={row.productId} className="text-xs">
                      <div className="flex items-center justify-between gap-3">
                        <span className="truncate font-bold text-slate-700">{row.productName}</span>
                        <span className="font-mono font-bold text-slate-900">{row.count}</span>
                      </div>
                      <div className="mt-0.5 text-[11px] font-semibold text-slate-400">
                        Tổn thất {Number(row.netLossValue || 0).toLocaleString('vi-VN')}đ
                      </div>
                    </div>
                  ))}
                  {!reportTopProducts.length && <div className="text-xs font-semibold text-slate-400">Chưa có dữ liệu.</div>}
                </div>
              </div>
            </div>
          </section>

          <div className="flex flex-col gap-3 rounded-xl border border-slate-100 bg-white p-4 shadow-sm md:flex-row md:items-center md:justify-between">
            <div className="flex-1">
              <label className="mb-1.5 block text-xs font-bold uppercase tracking-wider text-slate-400">Tìm IMEI lỗi</label>
              <input
                value={defectiveQuery}
                onChange={event => setDefectiveQuery(event.target.value)}
                placeholder="IMEI, sản phẩm, chứng từ hoặc đối tác"
                className="w-full rounded-xl border border-slate-200 bg-slate-50/50 px-3 py-2.5 text-sm font-medium text-slate-700 outline-none transition-colors focus:border-slate-900 focus:bg-white"
              />
            </div>
            <div className="w-full md:w-64">
              <label className="mb-1.5 block text-xs font-bold uppercase tracking-wider text-slate-400">Trạng thái</label>
              <select
                value={defectiveStatusFilter}
                onChange={event => setDefectiveStatusFilter(event.target.value)}
                className="w-full rounded-xl border border-slate-200 bg-slate-50/50 px-3 py-2.5 text-sm font-bold text-slate-700 outline-none transition-colors focus:border-slate-900 focus:bg-white"
              >
                <option value="all">Tất cả trạng thái</option>
                {Object.entries(dispositionStatusLabels).map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex flex-wrap items-center gap-2">
              {([
                ['all', 'Tất cả', defectiveQuickCounts.all],
                ['processing', 'Đang xử lý', defectiveQuickCounts.processing],
                ['completed', 'Đã hoàn tất', defectiveQuickCounts.completed],
                ['documented', 'Có chứng từ', defectiveQuickCounts.documented],
                ['recovered', 'Có thu hồi', defectiveQuickCounts.recovered],
              ] as const).map(([value, label, count]) => (
                <button
                  key={value}
                  onClick={() => setDefectiveQuickFilter(value)}
                  className={`rounded-lg border px-3 py-1.5 text-xs font-bold transition-colors ${
                    defectiveQuickFilter === value
                      ? 'border-slate-900 bg-slate-900 text-white'
                      : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  {label} <span className={defectiveQuickFilter === value ? 'text-white/70' : 'text-slate-400'}>{count}</span>
                </button>
              ))}
              {(defectiveQuery || defectiveStatusFilter !== 'all' || defectiveQuickFilter !== 'all') && (
                <button
                  onClick={() => {
                    setDefectiveQuery('');
                    setDefectiveStatusFilter('all');
                    setDefectiveQuickFilter('all');
                  }}
                  className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-bold text-slate-500 transition-colors hover:bg-slate-50 hover:text-slate-900"
                >
                  Xóa bộ lọc
                </button>
              )}
            </div>
            <button
              onClick={handleExportDefectiveCsv}
              disabled={!filteredDefective.length}
              className="w-full rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-bold text-emerald-700 transition-colors hover:bg-emerald-100 disabled:cursor-not-allowed disabled:border-slate-200 disabled:bg-slate-50 disabled:text-slate-350 lg:w-auto"
            >
              Xuất CSV
            </button>
          </div>

          <div className="grid gap-3 md:grid-cols-4">
            <div className="rounded-xl border border-slate-100 bg-white p-4 shadow-sm">
              <div className="text-xs font-bold uppercase tracking-wider text-slate-400">IMEI lỗi</div>
              <div className="mt-2 text-2xl font-extrabold text-slate-900">{defectiveSummary.total}</div>
            </div>
            <div className="rounded-xl border border-slate-100 bg-white p-4 shadow-sm">
              <div className="text-xs font-bold uppercase tracking-wider text-slate-400">Giá trị vốn</div>
              <div className="mt-2 text-lg font-extrabold text-slate-900">{defectiveSummary.inventoryValue.toLocaleString('vi-VN')}đ</div>
            </div>
            <div className="rounded-xl border border-emerald-100 bg-emerald-50/60 p-4 shadow-sm">
              <div className="text-xs font-bold uppercase tracking-wider text-emerald-700">Thu hồi dự kiến</div>
              <div className="mt-2 text-lg font-extrabold text-emerald-800">{defectiveSummary.recoveryValue.toLocaleString('vi-VN')}đ</div>
            </div>
            <div className="rounded-xl border border-slate-100 bg-white p-4 shadow-sm">
              <div className="text-xs font-bold uppercase tracking-wider text-slate-400">Đã có chứng từ</div>
              <div className="mt-2 text-2xl font-extrabold text-slate-900">
                {defectiveSummary.documented}/{defectiveSummary.total}
              </div>
              <div className="mt-1 text-xs font-semibold text-slate-400">Hoàn tất: {defectiveSummary.completed}</div>
            </div>
          </div>

          <div className="overflow-x-auto rounded-2xl border border-slate-100 bg-white shadow-sm">
            <table className="w-full text-left text-sm divide-y divide-slate-100">
              <thead>
                <tr className="bg-slate-50/50 text-slate-500 font-bold">
                  <th className="p-4 text-xs uppercase tracking-wider">Mã IMEI lỗi</th>
                  <th className="p-4 text-xs uppercase tracking-wider">Sản phẩm</th>
                  <th className="p-4 text-xs uppercase tracking-wider">Trạng thái định đoạt</th>
                  <th className="p-4 text-xs uppercase tracking-wider">Giá trị trung bình</th>
                  <th className="p-4 text-xs uppercase tracking-wider">Chứng từ / thu hồi</th>
                  <th className="p-4 text-xs uppercase tracking-wider text-right">Xử lý</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredDefective.map(item => {
                  const latest = item.latestDisposition || {};
                  const recoveryValue = Number(latest.recoveryValue || 0);

                  return (
                    <tr key={item.id} className="hover:bg-slate-50/50 transition-colors">
                      <td className="p-4 font-mono font-bold text-slate-850">{item.identifier}</td>
                      <td className="p-4 font-medium text-slate-700">{item.productName}</td>
                      <td className="p-4">
                        <span className="inline-flex items-center rounded-lg bg-rose-50 border border-rose-100 px-2.5 py-0.5 text-xs font-bold text-rose-700">
                          {dispositionStatusLabels[item.status] || item.status}
                        </span>
                      </td>
                      <td className="p-4 text-slate-600 font-medium">
                        {Number(item.averageUnitCost || 0).toLocaleString('vi-VN')}đ
                      </td>
                      <td className="p-4 text-xs text-slate-600">
                        {latest.documentReference || latest.partnerName || recoveryValue > 0 ? (
                          <div className="space-y-0.5">
                            {latest.documentReference && <div className="font-mono font-bold text-slate-800">{latest.documentReference}</div>}
                            {latest.partnerName && <div>{latest.partnerName}</div>}
                            {recoveryValue > 0 && <div className="font-bold text-emerald-700">{recoveryValue.toLocaleString('vi-VN')}đ</div>}
                          </div>
                        ) : '-'}
                      </td>
                      <td className="p-4 text-right">
                        <button
                          onClick={() => handleOpenDispositionModal(item)}
                          className="rounded-lg bg-slate-900 text-white px-3 py-1.5 text-xs font-bold hover:bg-slate-800 transition-colors"
                        >
                          Định đoạt
                        </button>
                      </td>
                    </tr>
                  );
                })}
                {!filteredDefective.length && (
                  <tr>
                    <td colSpan={6} className="py-12 text-center text-sm text-slate-400 font-medium">
                      {defective.length ? 'Không có IMEI lỗi khớp bộ lọc hiện tại.' : 'Không có danh sách IMEI lỗi cần xử lý.'}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ================= MODAL CẬP NHẬT TRẠNG THÁI (ADVANCE STATUS) ================= */}
      {showAdvanceModal && modalRequest && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4">
          <div className="relative w-full max-w-2xl rounded-2xl bg-white p-6 shadow-xl border border-slate-100 animate-in fade-in zoom-in-95 duration-200">
            <h3 className="text-base font-extrabold text-slate-900">
              Cập nhật hồ sơ {modalRequest.requestCode}
            </h3>
            <p className="mt-1.5 text-xs text-slate-400 font-medium">
              Chuyển trạng thái từ <span className="underline">{statusLabel[modalRequest.status]}</span> sang <span className="font-bold text-slate-900">{actionLabel[modalTargetStatus]}</span>.
            </p>

            <form onSubmit={handleConfirmAdvance} className="mt-5 space-y-4">
              {/* Nếu là trạng thái đổi máy, yêu cầu nhập IMEI mới */}
              {modalTargetStatus === 'COMPLETED' && ['EXCHANGE_PROCESSING', 'REPLACEMENT_PROCESSING'].includes(modalRequest.status) && (
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">IMEI Thiết bị Thay thế *</label>
                  <input
                    type="text"
                    value={replacementImei}
                    onChange={e => setReplacementImei(e.target.value)}
                    placeholder="Nhập mã IMEI của máy mới cấp"
                    className="rounded-xl border border-slate-200 p-3 text-sm focus:border-slate-900 focus:outline-none transition-colors"
                    required
                  />
                  <span className="text-[10px] text-slate-400">Thiết bị thay thế phải có sẵn trong kho hàng.</span>
                </div>
              )}

              {/* Ghi chú xử lý */}
              {section === 'returns' && (modalTargetStatus === 'REFUND_PROCESSING' || (modalTargetStatus === 'COMPLETED' && modalRequest.status === 'REFUND_PROCESSING')) && (
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Phí khấu hao / nhập lại</label>
                  <input
                    type="number"
                    min={0}
                    value={depreciationFee}
                    onChange={(event) => setDepreciationFee(event.target.value)}
                    placeholder="0"
                    className="rounded-xl border border-slate-200 p-3 text-sm focus:border-slate-900 focus:outline-none transition-colors"
                  />
                  <span className="text-[10px] text-slate-400">Khoản phí này sẽ được trừ khỏi số tiền hoàn thực tế.</span>
                </div>
              )}

              {section === 'warranties' && ['WARRANTY_ACCEPTED', 'REPAIRING', 'READY_TO_RETURN', 'COMPLETED'].includes(modalTargetStatus) && (
                <div className="rounded-xl border border-amber-100 bg-amber-50/40 p-3">
                  <div className="mb-3 text-xs font-bold uppercase tracking-wider text-amber-800">Chi tiết sửa chữa / bảo hành</div>
                  <div className="space-y-3">
                    <label className="flex flex-col gap-1.5">
                      <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Chẩn đoán lỗi</span>
                      <textarea
                        value={repairDiagnosis}
                        onChange={e => setRepairDiagnosis(e.target.value)}
                        placeholder="Ví dụ: lỗi main, mất nguồn, pin chai, lỗi màn hình..."
                        className="min-h-16 rounded-xl border border-slate-200 p-3 text-sm focus:border-slate-900 focus:outline-none transition-colors"
                      />
                    </label>
                    <label className="flex flex-col gap-1.5">
                      <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Hướng xử lý</span>
                      <textarea
                        value={repairAction}
                        onChange={e => setRepairAction(e.target.value)}
                        placeholder="Sửa chữa, thay linh kiện, vệ sinh, cập nhật phần mềm, trả máy..."
                        className="min-h-16 rounded-xl border border-slate-200 p-3 text-sm focus:border-slate-900 focus:outline-none transition-colors"
                      />
                    </label>
                    <div className="grid gap-3 sm:grid-cols-[1fr_140px]">
                      <label className="flex flex-col gap-1.5">
                        <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Linh kiện / vật tư</span>
                        <input
                          value={repairParts}
                          onChange={e => setRepairParts(e.target.value)}
                          placeholder="Pin, màn hình, cáp sạc..."
                          className="rounded-xl border border-slate-200 p-3 text-sm focus:border-slate-900 focus:outline-none transition-colors"
                        />
                      </label>
                      <label className="flex flex-col gap-1.5">
                        <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Chi phí</span>
                        <input
                          type="number"
                          min={0}
                          value={repairCost}
                          onChange={e => setRepairCost(e.target.value)}
                          placeholder="0"
                          className="rounded-xl border border-slate-200 p-3 text-sm focus:border-slate-900 focus:outline-none transition-colors"
                        />
                      </label>
                    </div>
                  </div>
                </div>
              )}

              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Ghi chú Xử lý (Nội bộ)</label>
                <textarea
                  value={note}
                  onChange={e => setNote(e.target.value)}
                  placeholder="Điền thông tin ghi chú cho hành động này (tùy chọn)"
                  className="min-h-24 rounded-xl border border-slate-200 p-3 text-sm focus:border-slate-900 focus:outline-none transition-colors"
                />
              </div>

              {/* Action buttons */}
              <div className="mt-6 flex justify-end gap-3.5 border-t border-slate-50 pt-4">
                <button
                  type="button"
                  onClick={() => setShowAdvanceModal(false)}
                  className="rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-xs font-bold text-slate-500 hover:bg-slate-50 transition-colors"
                >
                  Hủy bỏ
                </button>
                <button
                  type="submit"
                  disabled={busy}
                  className="rounded-xl bg-slate-900 px-4 py-2.5 text-xs font-bold text-white hover:bg-slate-800 transition-colors disabled:opacity-50"
                >
                  {busy ? 'Đang cập nhật...' : 'Xác nhận Chuyển'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ================= MODAL XEM CHI TIẾT HỒ SƠ & MINH CHỨNG ================= */}
      {showDetailModal && detailRequest && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4">
          <div className="relative w-full max-w-2xl rounded-2xl bg-white p-6 shadow-xl border border-slate-100 flex flex-col max-h-[85vh] overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            {/* Header */}
            <div className="flex items-center justify-between border-b border-slate-50 pb-3 shrink-0">
              <div>
                <h3 className="text-lg font-extrabold text-slate-900">Chi tiết Hồ sơ Hậu mãi</h3>
                <p className="text-xs text-slate-400 mt-0.5">Mã yêu cầu: <span className="font-mono font-bold">{detailRequest.requestCode}</span></p>
              </div>
              <button
                onClick={() => setShowDetailModal(false)}
                className="h-8 w-8 rounded-full hover:bg-slate-50 flex items-center justify-center text-slate-400 hover:text-slate-800 transition-colors text-lg"
              >
                ×
              </button>
            </div>

            {/* Scrollable Content */}
            <div className="mt-4 flex-1 overflow-y-auto space-y-6 pr-1">

              {/* Thông tin đơn hàng & Khách hàng */}
              <div className="grid gap-4 sm:grid-cols-2 bg-slate-50/50 p-4 rounded-xl border border-slate-100 text-xs">
                <div>
                  <span className="font-bold text-slate-400 uppercase tracking-wide">Mã Đơn hàng</span>
                  <p className="font-bold text-slate-900 text-sm mt-0.5">#{detailRequest.orderCode}</p>
                </div>
                <div>
                  <span className="font-bold text-slate-400 uppercase tracking-wide">Trạng thái hiện tại</span>
                  <p className="mt-0.5">
                    <span className={`inline-flex items-center rounded-lg px-2 py-0.5 text-[10px] font-bold border ${
                      statusStyles[detailRequest.status]?.bg || 'bg-slate-50'
                    } ${statusStyles[detailRequest.status]?.text || 'text-slate-700'} ${
                      statusStyles[detailRequest.status]?.border || 'border-slate-200'
                    }`}>
                      {statusLabel[detailRequest.status] || detailRequest.status}
                    </span>
                  </p>
                </div>
                <div>
                  <span className="font-bold text-slate-400 uppercase tracking-wide">Ngày gửi yêu cầu</span>
                  <p className="font-semibold text-slate-700 mt-0.5">{new Date(detailRequest.createdAt).toLocaleString('vi-VN')}</p>
                </div>
                <div>
                  <span className="font-bold text-slate-400 uppercase tracking-wide">Thời hạn xử lý (SLA)</span>
                  <p className="font-semibold text-slate-700 mt-0.5">
                    {detailRequest.slaDueAt ? new Date(detailRequest.slaDueAt).toLocaleString('vi-VN') : '-'}
                  </p>
                </div>
              </div>

              {/* Sản phẩm lỗi */}
              <div>
                <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Sản phẩm cần kiểm QC</h4>
                <div className="divide-y divide-slate-100 rounded-xl border border-slate-100 px-4 py-1">
                  {(detailRequest.items || []).map((line: any) => (
                    <div key={line.id} className="py-3 flex justify-between items-center text-xs">
                      <div>
                        <p className="font-bold text-slate-800">{line.productName}</p>
                        <div className="mt-1 flex flex-wrap gap-2 text-[10px] text-slate-400">
                          {line.imei && <span>IMEI: <strong>{line.imei}</strong></span>}
                          {line.serialNumber && <span>Serial: <strong>{line.serialNumber}</strong></span>}
                        </div>
                      </div>
                      <div className="text-right font-semibold text-slate-500">
                        Số lượng: {line.quantity}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Mô tả của khách */}
              <div>
                <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Mô tả tình trạng lỗi từ khách hàng</h4>
                <div className="text-xs leading-relaxed text-slate-700 bg-amber-50/20 border border-amber-100 rounded-xl p-4">
                  {detailRequest.reason}
                </div>
              </div>

              <div>
                <h4 className="mb-2 text-xs font-bold uppercase tracking-wider text-slate-500">Timeline xử lý</h4>
                <div className="rounded-xl border border-slate-100 bg-slate-50/60 p-4">
                  <div className="mb-4 rounded-xl border border-slate-200 bg-white p-3">
                    <label className="mb-1 block text-xs font-bold uppercase tracking-wider text-slate-500">Thêm ghi chú timeline</label>
                    <textarea
                      value={timelineNote}
                      onChange={event => setTimelineNote(event.target.value)}
                      placeholder="Ghi nhận cuộc gọi, hẹn lịch, yêu cầu bổ sung ảnh, cập nhật kỹ thuật..."
                      className="min-h-16 w-full rounded-lg border border-slate-200 p-2 text-xs text-slate-700 focus:border-slate-900 focus:outline-none"
                    />
                    <div className="mt-2 flex justify-end">
                      <button
                        type="button"
                        onClick={() => void handleAddTimelineNote()}
                        disabled={timelineNote.trim().length < 3 || timelineNoteBusy}
                        className="rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-bold text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {timelineNoteBusy ? 'Đang thêm...' : 'Thêm ghi chú'}
                      </button>
                    </div>
                  </div>
                  {detailEventsLoading ? (
                    <div className="text-xs font-semibold text-slate-500">Đang tải timeline...</div>
                  ) : detailEvents.length === 0 ? (
                    <div className="text-xs font-semibold text-slate-500">Chưa có sự kiện xử lý.</div>
                  ) : (
                    <div className="space-y-3">
                      {detailEvents.map((event) => {
                        const repair = event.metadata?.repair;
                        return (
                          <div key={event.id} className="border-l-2 border-slate-300 pl-3">
                            <div className="flex flex-wrap items-center justify-between gap-2">
                              <div className="text-xs font-bold text-slate-800">
                                {event.oldStatus ? `${statusLabel[event.oldStatus] || event.oldStatus} → ` : ''}
                                {statusLabel[event.newStatus] || event.newStatus}
                              </div>
                              <div className="text-[10px] font-semibold text-slate-400">
                                {event.createdAt ? new Date(event.createdAt).toLocaleString('vi-VN') : '-'}
                              </div>
                            </div>
                            <div className="mt-1 text-[11px] font-semibold text-slate-500">
                              {event.actorName || 'Hệ thống'}{event.note ? ` · ${event.note}` : ''}
                            </div>
                            {repair && (
                              <div className="mt-2 rounded-lg border border-amber-100 bg-white px-3 py-2 text-[11px] text-slate-700">
                                {repair.diagnosis && <div><strong>Chẩn đoán:</strong> {repair.diagnosis}</div>}
                                {repair.action && <div><strong>Hướng xử lý:</strong> {repair.action}</div>}
                                {repair.parts && <div><strong>Linh kiện:</strong> {repair.parts}</div>}
                                {Number(repair.cost || 0) > 0 && <div><strong>Chi phí:</strong> {Number(repair.cost || 0).toLocaleString('vi-VN')}đ</div>}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>

              {section === 'warranties' && detailRequest.repairSummary && Object.keys(detailRequest.repairSummary).length > 0 && (
                <div>
                  <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Chi tiết sửa chữa / bảo hành</h4>
                  <div className="grid gap-3 rounded-xl border border-amber-100 bg-amber-50/30 p-4 text-xs sm:grid-cols-2">
                    <div>
                      <span className="font-bold uppercase tracking-wide text-amber-700">Chẩn đoán</span>
                      <p className="mt-1 font-semibold text-slate-800">{detailRequest.repairSummary.diagnosis || '-'}</p>
                    </div>
                    <div>
                      <span className="font-bold uppercase tracking-wide text-amber-700">Hướng xử lý</span>
                      <p className="mt-1 font-semibold text-slate-800">{detailRequest.repairSummary.action || '-'}</p>
                    </div>
                    <div>
                      <span className="font-bold uppercase tracking-wide text-amber-700">Linh kiện</span>
                      <p className="mt-1 font-semibold text-slate-800">{detailRequest.repairSummary.parts || '-'}</p>
                    </div>
                    <div>
                      <span className="font-bold uppercase tracking-wide text-amber-700">Chi phí</span>
                      <p className="mt-1 font-semibold text-slate-800">{Number(detailRequest.repairSummary.cost || 0).toLocaleString('vi-VN')}đ</p>
                    </div>
                  </div>
                </div>
              )}

              {/* Trình duyệt Minh chứng (Hình ảnh/Video đính kèm) */}
              <div>
                <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Tệp đính kèm / Minh chứng</h4>

                {/* Giả lập xem các file hình ảnh/video minh họa vì DB chưa lưu liên kết trực tiếp */}
                <div className="grid grid-cols-3 gap-3">
                  {/* Trình bày mẫu Demo để nhân viên QC kiểm thử giao diện minh chứng */}
                  <div className="relative group rounded-xl overflow-hidden border border-slate-200 aspect-video flex flex-col bg-slate-50 items-center justify-center p-2 text-center">
                    <svg className="h-6 w-6 text-slate-400 mb-1" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                    <span className="text-[9px] text-slate-400">Minh chứng lỗi màn hình.jpg</span>
                    <a href="#" onClick={(e) => { e.preventDefault(); alert('Xem hình ảnh chi tiết lỗi đính kèm.'); }} className="absolute inset-0 bg-slate-900/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center text-[10px] font-bold text-white">Xem ảnh</a>
                  </div>

                  <div className="relative group rounded-xl overflow-hidden border border-slate-200 aspect-video flex flex-col bg-slate-50 items-center justify-center p-2 text-center">
                    <svg className="h-6 w-6 text-slate-400 mb-1" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    </svg>
                    <span className="text-[9px] text-slate-400">Video quay chi tiết lỗi.mp4</span>
                    <a href="#" onClick={(e) => { e.preventDefault(); alert('Phát video quay lỗi của sản phẩm.'); }} className="absolute inset-0 bg-slate-900/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center text-[10px] font-bold text-white">Phát video</a>
                  </div>

                  <div className="rounded-xl border border-slate-100 border-dashed flex flex-col items-center justify-center text-center p-2">
                    <span className="text-[9px] text-slate-350 italic">Không còn tệp đính kèm nào khác</span>
                  </div>
                </div>
              </div>

              {/* Lịch sử nhật ký xử lý của admin */}
              {detailRequest.adminNote && (
                <div>
                  <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Ghi chú xử lý nội bộ của Admin</h4>
                  <div className="text-xs leading-relaxed text-slate-700 bg-slate-50 border border-slate-200 rounded-xl p-4">
                    {detailRequest.adminNote}
                  </div>
                </div>
              )}
            </div>

            {/* Footer buttons */}
            <div className="mt-5 border-t border-slate-100 pt-4 flex justify-between items-center shrink-0">
              <div className="flex gap-1">
                {(actions[detailRequest.status] || []).map(status => (
                  <button
                    key={status}
                    onClick={() => {
                      handleOpenAdvanceModal(detailRequest, status);
                    }}
                    className={`rounded-xl px-3 py-2 text-xs font-bold transition-all ${
                      actionStyles[status] || 'bg-slate-800 text-white'
                    }`}
                  >
                    {actionLabel[status]}
                  </button>
                ))}
              </div>
              <button
                type="button"
                onClick={() => setShowDetailModal(false)}
                className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-xs font-bold text-slate-550 hover:bg-slate-50 transition-colors"
              >
                Đóng
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ================= MODAL ĐỊNH ĐOẠT IMEI LỖI (DISPOSITION) ================= */}
      {showDispositionModal && selectedDefective && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4">
          <div className="relative w-full max-w-2xl rounded-2xl bg-white p-6 shadow-xl border border-slate-100 animate-in fade-in zoom-in-95 duration-200">
            <h3 className="text-base font-extrabold text-slate-900">
              Xử lý định đoạt IMEI: {selectedDefective.identifier}
            </h3>
            <p className="mt-1 text-xs text-slate-400 font-medium">Sản phẩm: {selectedDefective.productName}</p>

            <div className="mt-4 rounded-xl border border-slate-100 bg-slate-50/70 p-3">
              <div className="mb-2 text-xs font-bold uppercase tracking-wider text-slate-500">Lịch sử định đoạt</div>
              {dispositionEventsLoading ? (
                <div className="text-xs font-semibold text-slate-500">Đang tải lịch sử...</div>
              ) : dispositionEvents.length === 0 ? (
                <div className="text-xs font-semibold text-slate-500">Chưa có lịch sử định đoạt.</div>
              ) : (
                <div className="max-h-48 space-y-2 overflow-y-auto pr-1">
                  {dispositionEvents.map((event) => (
                    <div key={event.id} className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <span className="font-bold text-slate-800">
                          {event.oldStatus ? `${dispositionStatusLabels[event.oldStatus] || event.oldStatus} → ` : ''}
                          {dispositionStatusLabels[event.newStatus] || event.newStatus}
                        </span>
                        <span className="text-[10px] font-semibold text-slate-400">
                          {event.createdAt ? new Date(event.createdAt).toLocaleString('vi-VN') : '-'}
                        </span>
                      </div>
                      <div className="mt-1 text-slate-600">{event.reason}</div>
                      {(event.documentReference || event.partnerName || Number(event.recoveryValue || 0) > 0) && (
                        <div className="mt-1 flex flex-wrap gap-2 text-[11px] font-semibold text-slate-500">
                          {event.documentReference && <span>Chứng từ: {event.documentReference}</span>}
                          {event.partnerName && <span>Đối tác: {event.partnerName}</span>}
                          {Number(event.recoveryValue || 0) > 0 && <span className="text-emerald-700">Thu hồi: {Number(event.recoveryValue || 0).toLocaleString('vi-VN')}đ</span>}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            <form onSubmit={handleConfirmDisposition} className="mt-5 space-y-4">
              {/* Trạng thái định đoạt */}
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Chọn Trạng thái định đoạt *</label>
                <select
                  value={dispStatus}
                  onChange={e => setDispStatus(e.target.value)}
                  className="rounded-xl border border-slate-200 bg-slate-50/50 p-3 text-sm focus:border-slate-900 focus:bg-white focus:outline-none transition-colors"
                  required
                >
                  <option value="INSPECTION_PENDING">Đang chờ thẩm định (QC)</option>
                  <option value="RTV_PENDING">Chờ trả về nhà sản xuất (RTV)</option>
                  <option value="LIQUIDATION_PENDING">Chờ thanh lý</option>
                  <option value="RTV_COMPLETED">Đã trả về nhà cung cấp (RTV xong)</option>
                  <option value="LIQUIDATED">Đã thanh lý</option>
                  <option value="SCRAP">Hủy phế phẩm (Scrap)</option>
                  <option value="OUT_OF_SYSTEM">Loại khỏi hệ thống</option>
                </select>
              </div>

              {/* Tài liệu tham chiếu */}
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Chứng từ / Tài liệu tham chiếu</label>
                <input
                  type="text"
                  value={docRef}
                  onChange={e => setDocRef(e.target.value)}
                  placeholder="Mã phiếu xuất/hóa đơn thanh lý"
                  className="rounded-xl border border-slate-200 p-3 text-sm focus:border-slate-900 focus:outline-none transition-colors"
                />
              </div>

              {/* Tên đối tác */}
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Đối tác thu hồi / Thanh lý</label>
                <input
                  type="text"
                  value={partner}
                  onChange={e => setPartner(e.target.value)}
                  placeholder="Tên đối tác hoặc nhà phân phối"
                  className="rounded-xl border border-slate-200 p-3 text-sm focus:border-slate-900 focus:outline-none transition-colors"
                />
              </div>

              {/* Giá trị thu hồi */}
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Giá trị thu hồi (VNĐ)</label>
                <input
                  type="number"
                  value={recoveryVal}
                  onChange={e => setRecoveryVal(e.target.value)}
                  placeholder="Số tiền thu về (nếu có)"
                  className="rounded-xl border border-slate-200 p-3 text-sm focus:border-slate-900 focus:outline-none transition-colors"
                />
              </div>

              {/* Lý do định đoạt */}
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Lý do / Mô tả chi tiết *</label>
                <textarea
                  value={dispReason}
                  onChange={e => setDispReason(e.target.value)}
                  placeholder="Mô tả lý do định đoạt và kết quả kiểm định"
                  className="min-h-20 rounded-xl border border-slate-200 p-3 text-sm focus:border-slate-900 focus:outline-none transition-colors"
                  required
                />
              </div>

              {/* Action buttons */}
              <div className="mt-6 flex justify-end gap-3 border-t border-slate-55 pt-4">
                <button
                  type="button"
                  onClick={() => setShowDispositionModal(false)}
                  className="rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-xs font-bold text-slate-500 hover:bg-slate-50 transition-colors"
                >
                  Hủy bỏ
                </button>
                <button
                  type="submit"
                  disabled={busy}
                  className="rounded-xl bg-slate-900 px-4 py-2.5 text-xs font-bold text-white hover:bg-slate-800 transition-colors disabled:opacity-50"
                >
                  {busy ? 'Đang cập nhật...' : 'Xác nhận xử lý'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
