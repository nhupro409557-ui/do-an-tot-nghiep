import { useEffect, useMemo, useState } from 'react';
import {
  BadgeCheck,
  ClipboardCheck,
  Eye,
  FilePenLine,
  Plus,
  RefreshCw,
  ScrollText,
  Search,
  Send,
} from 'lucide-react';
import { AdminPanel } from '../../admin-shell/parts/AdminPanel';
import { adminUsedProductsApi } from '../services/adminUsedProductsApi';
import DeviceHistoryModal from './DeviceHistoryModal';
import InspectionModal from './InspectionModal';
import IntakeModal from './IntakeModal';
import ListingModal from './ListingModal';
import ReinspectionModal from './ReinspectionModal';
import type {
  SourceProduct,
  UsedProductDevice,
  UsedProductHistory,
  UsedProductInspectionDraft,
  UsedProductIntake,
  UsedProductIntakeDraft,
  UsedProductListing,
  UsedProductListingDraft,
} from '../types';

const money = new Intl.NumberFormat('vi-VN', {
  style: 'currency',
  currency: 'VND',
  maximumFractionDigits: 0,
});

const statusLabels: Record<string, string> = {
  SUBMITTED: 'Mới tiếp nhận',
  RECEIVED: 'Đã nhận máy',
  INSPECTING: 'Đang thẩm định',
  APPRAISED: 'Đã định giá',
  REPAIR_REQUIRED: 'Cần sửa chữa',
  ACCEPTED: 'Đã thu mua',
  REJECTED: 'Từ chối',
  CANCELLED: 'Đã hủy',
  READY_FOR_PRICING: 'Chờ hoàn thiện giá',
  LISTING_DRAFT: 'Bài đăng nháp',
  LISTING_REVIEW: 'Bài đăng chờ duyệt',
  READY_FOR_SALE: 'Sẵn sàng bán',
  RESERVED: 'Đang giữ',
  SOLD: 'Đã bán',
  RETURNED_QC: 'Hoàn về chờ QC',
  REPAIRING: 'Đang sửa chữa',
  RETIRED: 'Ngừng kinh doanh',
  DRAFT: 'Nháp',
  PENDING_APPROVAL: 'Chờ duyệt',
  PUBLISHED: 'Đang bán',
  HIDDEN: 'Đã ẩn',
};

const statusTone: Record<string, string> = {
  SUBMITTED: 'bg-slate-100 text-slate-700',
  RECEIVED: 'bg-sky-50 text-sky-700',
  INSPECTING: 'bg-amber-50 text-amber-700',
  APPRAISED: 'bg-emerald-50 text-emerald-700',
  ACCEPTED: 'bg-teal-50 text-teal-700',
  REPAIR_REQUIRED: 'bg-orange-50 text-orange-700',
  REJECTED: 'bg-red-50 text-red-700',
  CANCELLED: 'bg-slate-100 text-slate-500',
  READY_FOR_PRICING: 'bg-indigo-50 text-indigo-700',
  LISTING_DRAFT: 'bg-slate-100 text-slate-700',
  LISTING_REVIEW: 'bg-amber-50 text-amber-700',
  READY_FOR_SALE: 'bg-emerald-50 text-emerald-700',
  RESERVED: 'bg-sky-50 text-sky-700',
  SOLD: 'bg-slate-100 text-slate-700',
  RETURNED_QC: 'bg-purple-50 text-purple-700',
  REPAIRING: 'bg-orange-50 text-orange-700',
  RETIRED: 'bg-red-50 text-red-700',
  DRAFT: 'bg-slate-100 text-slate-700',
  PENDING_APPROVAL: 'bg-amber-50 text-amber-700',
  PUBLISHED: 'bg-emerald-50 text-emerald-700',
  HIDDEN: 'bg-slate-100 text-slate-500',
};

const emptyIntake: UsedProductIntakeDraft = {
  sourceType: 'USER_BUYBACK',
  productId: '',
  variantId: '',
  imei: '',
  serialNumber: '',
  sellerName: '',
  sellerPhone: '',
  expectedPrice: '',
  note: '',
};

const emptyInspection: UsedProductInspectionDraft = {
  outcome: 'APPRAISED',
  conditionGrade: 'B',
  conditionScore: '80',
  batteryHealth: '85',
  repairCostEstimate: '0',
  proposedAcquisitionPrice: '',
  proposedSalePrice: '',
  note: '',
  evidence: [] as { url: string; name?: string }[],
  checklist: {
    screen: true,
    camera: true,
    connectivity: true,
    biometric: true,
    accountUnlocked: true,
  },
};

const emptyListing: UsedProductListingDraft = {
  title: '',
  description: '',
  highlightsText: '',
  images: [] as string[],
  warrantyMonths: '3',
  priceComparisonNote: '',
};

type AdminUsedProductsTabProps = {
  usePermission?: (permission: string) => boolean;
  uploadFiles?: (files: FileList | null | File[], folder?: string) => Promise<string[]>;
};

export default function AdminUsedProductsTab({ usePermission = () => false, uploadFiles }: AdminUsedProductsTabProps) {
  const canManage = usePermission('used_product:manage');
  const canApprove = usePermission('used_product:approve');
  const [section, setSection] = useState<'intakes' | 'devices' | 'listings'>('intakes');
  const [intakes, setIntakes] = useState<UsedProductIntake[]>([]);
  const [devices, setDevices] = useState<UsedProductDevice[]>([]);
  const [listings, setListings] = useState<UsedProductListing[]>([]);
  const [products, setProducts] = useState<SourceProduct[]>([]);
  const [statusFilter, setStatusFilter] = useState('');
  const [search, setSearch] = useState('');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [intakeOpen, setIntakeOpen] = useState(false);
  const [inspectionOpen, setInspectionOpen] = useState(false);
  const [reinspectionOpen, setReinspectionOpen] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [listingOpen, setListingOpen] = useState(false);
  const [selectedIntake, setSelectedIntake] = useState<UsedProductIntake | null>(null);
  const [selectedDevice, setSelectedDevice] = useState<UsedProductDevice | null>(null);
  const [intakeDraft, setIntakeDraft] = useState<UsedProductIntakeDraft>({ ...emptyIntake });
  const [inspectionDraft, setInspectionDraft] = useState<UsedProductInspectionDraft>({ ...emptyInspection });
  const [listingDraft, setListingDraft] = useState<UsedProductListingDraft>({ ...emptyListing });
  const [deviceHistory, setDeviceHistory] = useState<UsedProductHistory | null>(null);

  const selectedProduct = useMemo(
    () => products.find((product) => String(product.id) === intakeDraft.productId),
    [products, intakeDraft.productId],
  );

  async function loadData() {
    setBusy(true);
    setMessage('');
    try {
      const [intakeResult, deviceResult, listingResult, productResult] = await Promise.all([
        adminUsedProductsApi.listIntakes(section === 'intakes' ? statusFilter : '', search),
        adminUsedProductsApi.listDevices(section === 'devices' ? statusFilter : '', search),
        adminUsedProductsApi.listListings(section === 'listings' ? statusFilter : '', search),
        products.length ? Promise.resolve(products) : adminUsedProductsApi.listSourceProducts(),
      ]);
      setIntakes(intakeResult.items || []);
      setDevices(deviceResult || []);
      setListings(listingResult || []);
      setProducts(productResult || []);
    } catch (error: any) {
      setMessage(error?.message || 'Không thể tải dữ liệu hàng cũ.');
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    void loadData();
  }, [section, statusFilter]);

  async function submitIntake(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setMessage('');
    try {
      await adminUsedProductsApi.createIntake({
        ...intakeDraft,
        variantId: intakeDraft.variantId || null,
        serialNumber: intakeDraft.serialNumber || null,
        sellerName: intakeDraft.sellerName || null,
        sellerPhone: intakeDraft.sellerPhone || null,
        expectedPrice: intakeDraft.expectedPrice === '' ? null : Number(intakeDraft.expectedPrice),
        note: intakeDraft.note || null,
      });
      setIntakeOpen(false);
      setIntakeDraft({ ...emptyIntake });
      setMessage('Đã tạo hồ sơ tiếp nhận hàng cũ.');
      await loadData();
    } catch (error: any) {
      setMessage(error?.message || 'Không thể tạo hồ sơ tiếp nhận.');
    } finally {
      setBusy(false);
    }
  }

  async function changeStatus(intake: UsedProductIntake, status: string) {
    setBusy(true);
    setMessage('');
    try {
      await adminUsedProductsApi.updateIntakeStatus(intake.id, { status });
      setMessage(status === 'ACCEPTED' ? 'Đã xác nhận thu mua và tạo thiết bị trong kho hàng cũ.' : 'Đã cập nhật trạng thái hồ sơ.');
      await loadData();
    } catch (error: any) {
      setMessage(error?.message || 'Không thể cập nhật trạng thái.');
    } finally {
      setBusy(false);
    }
  }

  function openInspection(intake: UsedProductIntake) {
    setSelectedIntake(intake);
    setInspectionDraft({
      ...emptyInspection,
      proposedAcquisitionPrice: intake.expectedPrice ? String(intake.expectedPrice) : '',
    });
    setInspectionOpen(true);
  }

  async function submitInspection(event: React.FormEvent) {
    event.preventDefault();
    if (!selectedIntake) return;
    setBusy(true);
    setMessage('');
    try {
      await adminUsedProductsApi.inspectIntake(selectedIntake.id, {
        ...inspectionDraft,
        conditionScore: inspectionDraft.conditionScore === '' ? null : Number(inspectionDraft.conditionScore),
        batteryHealth: inspectionDraft.batteryHealth === '' ? null : Number(inspectionDraft.batteryHealth),
        repairCostEstimate: Number(inspectionDraft.repairCostEstimate || 0),
        proposedAcquisitionPrice: inspectionDraft.proposedAcquisitionPrice === ''
          ? null
          : Number(inspectionDraft.proposedAcquisitionPrice),
        proposedSalePrice: inspectionDraft.proposedSalePrice === ''
          ? null
          : Number(inspectionDraft.proposedSalePrice),
        evidence: inspectionDraft.evidence,
      });
      setInspectionOpen(false);
      setMessage('Đã lưu kết quả thẩm định.');
      await loadData();
    } catch (error: any) {
      setMessage(error?.message || 'Không thể lưu kết quả thẩm định.');
    } finally {
      setBusy(false);
    }
  }

  function openReinspection(device: UsedProductDevice) {
    setSelectedDevice(device);
    setInspectionDraft({
      ...emptyInspection,
      outcome: 'APPRAISED',
      conditionGrade: device.conditionGrade || 'B',
      conditionScore: String(device.conditionScore ?? 80),
      batteryHealth: String(device.batteryHealth ?? 85),
      repairCostEstimate: String(device.refurbishmentCost || 0),
      proposedAcquisitionPrice: '',
      proposedSalePrice: String(device.approvedSalePrice || ''),
      note: '',
      evidence: [],
      checklist: device.inspectionChecklist || emptyInspection.checklist,
    });
    setReinspectionOpen(true);
  }

  async function submitReinspection(event: React.FormEvent) {
    event.preventDefault();
    if (!selectedDevice) return;
    setBusy(true);
    setMessage('');
    try {
      await adminUsedProductsApi.reinspectDevice(selectedDevice.id, {
        ...inspectionDraft,
        conditionScore: inspectionDraft.conditionScore === '' ? null : Number(inspectionDraft.conditionScore),
        batteryHealth: inspectionDraft.batteryHealth === '' ? null : Number(inspectionDraft.batteryHealth),
        repairCostEstimate: Number(inspectionDraft.repairCostEstimate || 0),
        proposedAcquisitionPrice: null,
        proposedSalePrice: inspectionDraft.proposedSalePrice === ''
          ? null
          : Number(inspectionDraft.proposedSalePrice),
        evidence: inspectionDraft.evidence,
      });
      setReinspectionOpen(false);
      setMessage('Đã lưu kết quả QC lại thiết bị hoàn.');
      await loadData();
    } catch (error: any) {
      setMessage(error?.message || 'Không thể lưu kết quả QC lại.');
    } finally {
      setBusy(false);
    }
  }

  async function uploadInspectionEvidence(files: FileList | null) {
    if (!files?.length || !uploadFiles) return;
    setBusy(true);
    try {
      const urls = await uploadFiles(files, 'used-products');
      setInspectionDraft((current) => ({
        ...current,
        evidence: [
          ...current.evidence,
          ...urls.map((url, index) => ({ url, name: files[index]?.name || `Ảnh ${current.evidence.length + index + 1}` })),
        ],
      }));
    } catch (error: any) {
      setMessage(error?.message || 'Không thể tải ảnh thẩm định.');
    } finally {
      setBusy(false);
    }
  }

  function openListing(device: UsedProductDevice) {
    const evidenceImages = (device.inspectionEvidence || []).map((item) => item.url).filter(Boolean);
    setSelectedDevice(device);
    setListingDraft({
      title: device.listingTitle || `${device.productName} cũ hạng ${device.conditionGrade}`,
      description: device.listingDescription || `Thiết bị đã được kiểm tra chức năng, tình trạng ${device.conditionScore}/100 và sức khỏe pin ${device.batteryHealth ?? '-'}%.`,
      highlightsText: (device.listingHighlights || []).join('\n'),
      images: device.listingImages?.length ? device.listingImages : evidenceImages,
      warrantyMonths: String(device.listingWarrantyMonths ?? 3),
      priceComparisonNote: device.priceComparisonNote || '',
    });
    setListingOpen(true);
  }

  async function uploadListingImages(files: FileList | null) {
    if (!files?.length || !uploadFiles) return;
    setBusy(true);
    try {
      const urls = await uploadFiles(files, 'used-products');
      setListingDraft((current) => ({ ...current, images: [...current.images, ...urls] }));
    } catch (error: any) {
      setMessage(error?.message || 'Không thể tải ảnh bài đăng.');
    } finally {
      setBusy(false);
    }
  }

  async function submitListing(event: React.FormEvent) {
    event.preventDefault();
    if (!selectedDevice) return;
    setBusy(true);
    setMessage('');
    try {
      await adminUsedProductsApi.saveListing(selectedDevice.id, {
        title: listingDraft.title,
        description: listingDraft.description,
        highlights: listingDraft.highlightsText.split('\n').map((item) => item.trim()).filter(Boolean),
        images: listingDraft.images,
        warrantyMonths: Number(listingDraft.warrantyMonths || 0),
        priceComparisonNote: listingDraft.priceComparisonNote || null,
      });
      setListingOpen(false);
      setMessage('Đã lưu bài đăng nháp.');
      await loadData();
    } catch (error: any) {
      setMessage(error?.message || 'Không thể lưu bài đăng.');
    } finally {
      setBusy(false);
    }
  }

  async function changeListingStatus(listing: UsedProductListing, status: string) {
    setBusy(true);
    setMessage('');
    try {
      await adminUsedProductsApi.updateListingStatus(listing.id, { status });
      setMessage(status === 'PUBLISHED' ? 'Đã duyệt và đăng bán thiết bị.' : 'Đã cập nhật trạng thái bài đăng.');
      await loadData();
    } catch (error: any) {
      setMessage(error?.message || 'Không thể cập nhật bài đăng.');
    } finally {
      setBusy(false);
    }
  }

  async function changeDeviceStatus(device: UsedProductDevice, status: string, note: string) {
    setBusy(true);
    setMessage('');
    try {
      await adminUsedProductsApi.updateDeviceStatus(device.id, { status, note });
      setMessage(status === 'READY_FOR_PRICING' ? 'Đã đưa thiết bị về bước hoàn thiện giá và soạn bài lại.' : 'Đã cập nhật trạng thái thiết bị.');
      await loadData();
    } catch (error: any) {
      setMessage(error?.message || 'Không thể cập nhật trạng thái thiết bị.');
    } finally {
      setBusy(false);
    }
  }

  async function openDeviceHistory(device: UsedProductDevice) {
    setBusy(true);
    setMessage('');
    try {
      const history = await adminUsedProductsApi.getDeviceHistory(device.id);
      setDeviceHistory(history);
      setHistoryOpen(true);
    } catch (error: any) {
      setMessage(error?.message || 'Không thể tải lịch sử thiết bị.');
    } finally {
      setBusy(false);
    }
  }

  function intakeActions(item: UsedProductIntake) {
    if (!canManage) return null;
    if (item.status === 'SUBMITTED') {
      return (
        <button type="button" onClick={() => void changeStatus(item, 'RECEIVED')} className="h-8 rounded-md border border-sky-200 bg-sky-50 px-2.5 text-xs font-bold text-sky-700">
          Tiếp nhận máy
        </button>
      );
    }
    if (item.status === 'RECEIVED') {
      return (
        <button type="button" onClick={() => void changeStatus(item, 'INSPECTING')} className="h-8 rounded-md border border-amber-200 bg-amber-50 px-2.5 text-xs font-bold text-amber-700">
          Bắt đầu thẩm định
        </button>
      );
    }
    if (['INSPECTING', 'REPAIR_REQUIRED'].includes(item.status)) {
      return (
        <button type="button" onClick={() => openInspection(item)} className="inline-flex h-8 items-center gap-1.5 rounded-md bg-amber-600 px-2.5 text-xs font-bold text-white">
          <ClipboardCheck className="h-3.5 w-3.5" /> Ghi kết quả
        </button>
      );
    }
    if (item.status === 'APPRAISED' && canApprove) {
      return (
        <button type="button" onClick={() => void changeStatus(item, 'ACCEPTED')} className="inline-flex h-8 items-center gap-1.5 rounded-md bg-emerald-600 px-2.5 text-xs font-bold text-white">
          <BadgeCheck className="h-3.5 w-3.5" /> Xác nhận thu mua
        </button>
      );
    }
    return null;
  }

  return (
    <AdminPanel
      title="Quản lý hàng cũ"
      action={canManage ? (
        <button type="button" onClick={() => setIntakeOpen(true)} className="inline-flex h-9 items-center gap-2 rounded-md bg-emerald-700 px-3 text-sm font-bold text-white hover:bg-emerald-800">
          <Plus className="h-4 w-4" /> Tạo hồ sơ
        </button>
      ) : undefined}
      filters={(
        <>
          <div className="inline-flex h-9 rounded-md border border-slate-200 bg-white p-1">
            <button type="button" onClick={() => { setSection('intakes'); setStatusFilter(''); }} className={`rounded px-3 text-xs font-bold ${section === 'intakes' ? 'bg-slate-900 text-white' : 'text-slate-600'}`}>
              Tiếp nhận
            </button>
            <button type="button" onClick={() => { setSection('devices'); setStatusFilter(''); }} className={`rounded px-3 text-xs font-bold ${section === 'devices' ? 'bg-slate-900 text-white' : 'text-slate-600'}`}>
              Kho hàng cũ
            </button>
            <button type="button" onClick={() => { setSection('listings'); setStatusFilter(''); }} className={`rounded px-3 text-xs font-bold ${section === 'listings' ? 'bg-slate-900 text-white' : 'text-slate-600'}`}>
              Bài đăng
            </button>
          </div>
          <label className="relative min-w-56 flex-1">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
            <input aria-label="Tìm hàng cũ" value={search} onChange={(event) => setSearch(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter') void loadData(); }} placeholder="Mã hồ sơ, sản phẩm, IMEI" className="h-9 w-full rounded-md border border-slate-200 bg-white pl-9 pr-3 text-sm outline-none focus:border-emerald-500" />
          </label>
          <select aria-label="Lọc trạng thái hàng cũ" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)} className="h-9 rounded-md border border-slate-200 bg-white px-3 text-sm font-semibold text-slate-700">
            <option value="">Tất cả trạng thái</option>
            {(section === 'intakes'
              ? ['SUBMITTED', 'RECEIVED', 'INSPECTING', 'APPRAISED', 'REPAIR_REQUIRED', 'ACCEPTED', 'REJECTED']
              : section === 'devices'
                ? ['READY_FOR_PRICING', 'LISTING_DRAFT', 'LISTING_REVIEW', 'READY_FOR_SALE', 'RESERVED', 'SOLD', 'RETURNED_QC', 'REPAIRING']
                : ['DRAFT', 'PENDING_APPROVAL', 'PUBLISHED', 'HIDDEN']
            ).map((status) => <option key={status} value={status}>{statusLabels[status]}</option>)}
          </select>
          <button type="button" title="Làm mới dữ liệu hàng cũ" onClick={() => void loadData()} className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-slate-200 bg-white text-slate-600 hover:bg-slate-50">
            <RefreshCw className={`h-4 w-4 ${busy ? 'animate-spin' : ''}`} />
          </button>
        </>
      )}
    >
      {message && <div className="mb-4 rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-700">{message}</div>}

      {section === 'intakes' ? (
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
              <tr>
                <th className="px-3 py-2.5">Hồ sơ</th>
                <th className="px-3 py-2.5">Thiết bị</th>
                <th className="px-3 py-2.5">Người bán</th>
                <th className="px-3 py-2.5">Thẩm định</th>
                <th className="px-3 py-2.5">Trạng thái</th>
                <th className="px-3 py-2.5 text-right">Thao tác</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {intakes.map((item) => (
                <tr key={item.id} className="align-top hover:bg-slate-50/70">
                  <td className="px-3 py-3">
                    <div className="font-bold text-slate-900">{item.requestCode}</div>
                    <div className="mt-1 text-xs text-slate-500">{item.sourceType === 'RETURNED_USED' ? 'Máy hoàn đã sử dụng' : 'Thu mua từ người dùng'}</div>
                  </td>
                  <td className="px-3 py-3">
                    <div className="font-semibold text-slate-800">{item.productName}</div>
                    <div className="mt-1 text-xs text-slate-500">{[item.colorName, item.storage, item.ram].filter(Boolean).join(' / ') || item.variantSku || '-'}</div>
                    <div className="mt-1 font-mono text-xs text-slate-600">IMEI: {item.imei}</div>
                  </td>
                  <td className="px-3 py-3">
                    <div className="font-semibold text-slate-700">{item.sellerName || '-'}</div>
                    <div className="mt-1 text-xs text-slate-500">{item.sellerPhone || '-'}</div>
                    <div className="mt-1 text-xs text-slate-500">Mong muốn: {item.expectedPrice == null ? '-' : money.format(Number(item.expectedPrice))}</div>
                  </td>
                  <td className="px-3 py-3">
                    {item.conditionGrade ? (
                      <>
                        <div className="font-bold text-slate-800">Hạng {item.conditionGrade} · {item.conditionScore}/100</div>
                        <div className="mt-1 text-xs text-slate-500">Pin {item.batteryHealth ?? '-'}% · Giá bán {money.format(Number(item.proposedSalePrice || 0))}</div>
                      </>
                    ) : <span className="text-slate-400">Chưa có kết quả</span>}
                  </td>
                  <td className="px-3 py-3">
                    <span className={`inline-flex rounded-md px-2 py-1 text-xs font-bold ${statusTone[item.status] || 'bg-slate-100 text-slate-700'}`}>
                      {statusLabels[item.status] || item.status}
                    </span>
                  </td>
                  <td className="px-3 py-3 text-right">{intakeActions(item)}</td>
                </tr>
              ))}
              {!busy && intakes.length === 0 && <tr><td colSpan={6} className="px-3 py-10 text-center text-slate-500">Chưa có hồ sơ hàng cũ phù hợp.</td></tr>}
            </tbody>
          </table>
        </div>
      ) : section === 'devices' ? (
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
              <tr>
                <th className="px-3 py-2.5">Thiết bị</th>
                <th className="px-3 py-2.5">Tình trạng</th>
                <th className="px-3 py-2.5">Giá máy mới</th>
                <th className="px-3 py-2.5">Giá hàng cũ</th>
                <th className="px-3 py-2.5">Vị trí</th>
                <th className="px-3 py-2.5">Trạng thái</th>
                <th className="px-3 py-2.5 text-right">Bài đăng</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {devices.map((device) => {
                const snapshot = device.originalSnapshot || {};
                const savings = Math.max(0, Number(snapshot.newReferencePrice || 0) - Number(device.approvedSalePrice || 0));
                return (
                  <tr key={device.id} className="hover:bg-slate-50/70">
                    <td className="px-3 py-3">
                      <div className="font-bold text-slate-900">{device.deviceCode}</div>
                      <div className="mt-1 font-semibold text-slate-700">{device.productName}</div>
                      <div className="mt-1 font-mono text-xs text-slate-500">{device.imei}</div>
                    </td>
                    <td className="px-3 py-3">
                      <div className="font-bold text-slate-800">Hạng {device.conditionGrade}</div>
                      <div className="text-xs text-slate-500">{device.conditionScore}/100 · Pin {device.batteryHealth ?? '-'}%</div>
                    </td>
                    <td className="px-3 py-3 font-semibold text-slate-700">{money.format(Number(snapshot.newReferencePrice || 0))}</td>
                    <td className="px-3 py-3">
                      <div className="font-bold text-emerald-700">{money.format(Number(device.approvedSalePrice || 0))}</div>
                      <div className="text-xs text-slate-500">Tiết kiệm {money.format(savings)}</div>
                    </td>
                    <td className="px-3 py-3"><div className="font-semibold text-slate-700">{device.locationCode}</div><div className="text-xs text-slate-500">{device.locationName}</div></td>
                    <td className="px-3 py-3"><span className={`inline-flex rounded-md px-2 py-1 text-xs font-bold ${statusTone[device.status] || 'bg-slate-100 text-slate-700'}`}>{statusLabels[device.status] || device.status}</span></td>
                    <td className="px-3 py-3 text-right">
                      <div className="flex flex-wrap justify-end gap-2">
                      <button type="button" onClick={() => void openDeviceHistory(device)} className="inline-flex h-9 items-center gap-1.5 rounded-md border border-slate-200 bg-white px-2.5 text-xs font-bold text-slate-700 hover:bg-slate-50">
                        <ScrollText className="h-3.5 w-3.5" /> Lịch sử
                      </button>
                      {canManage && device.status === 'RETURNED_QC' && (
                        <button type="button" onClick={() => openReinspection(device)} className="inline-flex h-9 items-center gap-1.5 rounded-md bg-purple-700 px-2.5 text-xs font-bold text-white hover:bg-purple-800">
                          <ClipboardCheck className="h-3.5 w-3.5" /> QC lại
                        </button>
                      )}
                      {canManage && device.status === 'REPAIRING' && (
                        <button type="button" onClick={() => void changeDeviceStatus(device, 'RETURNED_QC', 'Đã sửa xong, chuyển lại QC trước khi bán.')} className="inline-flex h-9 items-center gap-1.5 rounded-md border border-sky-200 bg-sky-50 px-2.5 text-xs font-bold text-sky-700 hover:bg-sky-100">
                          <ClipboardCheck className="h-3.5 w-3.5" /> Chờ QC
                        </button>
                      )}
                      {canApprove && device.status === 'REPAIRING' && (
                        <button type="button" onClick={() => void changeDeviceStatus(device, 'RETIRED', 'Thiết bị không đủ điều kiện bán lại sau hoàn hàng.')} className="h-9 rounded-md border border-red-200 bg-red-50 px-2.5 text-xs font-bold text-red-700 hover:bg-red-100">
                          Ngừng bán
                        </button>
                      )}
                      {canManage && !['RESERVED', 'SOLD', 'RETURNED_QC', 'RETIRED'].includes(device.status) && (
                        <button type="button" onClick={() => openListing(device)} className="inline-flex h-9 items-center gap-1.5 rounded-md border border-emerald-200 bg-emerald-50 px-2.5 text-xs font-bold text-emerald-700 hover:bg-emerald-100">
                          <FilePenLine className="h-3.5 w-3.5" /> {device.listingId ? 'Sửa bài' : 'Soạn bài'}
                        </button>
                      )}
                      </div>
                    </td>
                  </tr>
                );
              })}
              {!busy && devices.length === 0 && <tr><td colSpan={7} className="px-3 py-10 text-center text-slate-500">Kho hàng cũ chưa có thiết bị.</td></tr>}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
              <tr>
                <th className="px-3 py-2.5">Bài đăng</th>
                <th className="px-3 py-2.5">Thiết bị</th>
                <th className="px-3 py-2.5">Giá bán</th>
                <th className="px-3 py-2.5">Media</th>
                <th className="px-3 py-2.5">Trạng thái</th>
                <th className="px-3 py-2.5 text-right">Thao tác</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {listings.map((listing) => (
                <tr key={listing.id} className="align-top hover:bg-slate-50/70">
                  <td className="px-3 py-3">
                    <div className="font-bold text-slate-900">{listing.title}</div>
                    <div className="mt-1 text-xs text-slate-500">/{listing.slug}</div>
                  </td>
                  <td className="px-3 py-3">
                    <div className="font-semibold text-slate-700">{listing.deviceCode} · Hạng {listing.conditionGrade}</div>
                    <div className="mt-1 font-mono text-xs text-slate-500">{listing.imei}</div>
                  </td>
                  <td className="px-3 py-3 font-bold text-emerald-700">{money.format(Number(listing.salePrice || 0))}</td>
                  <td className="px-3 py-3 text-sm font-semibold text-slate-600">{listing.images?.length || 0} ảnh</td>
                  <td className="px-3 py-3"><span className={`inline-flex rounded-md px-2 py-1 text-xs font-bold ${statusTone[listing.status] || 'bg-slate-100 text-slate-700'}`}>{statusLabels[listing.status] || listing.status}</span></td>
                  <td className="px-3 py-3">
                    <div className="flex justify-end gap-2">
                      {listing.status === 'PUBLISHED' && <a href={`/used-products/${listing.slug}`} target="_blank" rel="noreferrer" title="Xem bài đăng" className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-slate-200 text-slate-600 hover:bg-slate-50"><Eye className="h-4 w-4" /></a>}
                      {canManage && listing.status === 'DRAFT' && <button type="button" onClick={() => void changeListingStatus(listing, 'PENDING_APPROVAL')} className="inline-flex h-9 items-center gap-1.5 rounded-md bg-amber-600 px-3 text-xs font-bold text-white"><Send className="h-3.5 w-3.5" /> Gửi duyệt</button>}
                      {canApprove && listing.status === 'PENDING_APPROVAL' && <button type="button" onClick={() => void changeListingStatus(listing, 'PUBLISHED')} className="inline-flex h-9 items-center gap-1.5 rounded-md bg-emerald-700 px-3 text-xs font-bold text-white"><BadgeCheck className="h-3.5 w-3.5" /> Đăng bán</button>}
                      {canManage && listing.status === 'PUBLISHED' && <button type="button" onClick={() => void changeListingStatus(listing, 'HIDDEN')} className="h-9 rounded-md border border-slate-200 px-3 text-xs font-bold text-slate-600">Ẩn bài</button>}
                      {canManage && listing.status === 'HIDDEN' && <button type="button" onClick={() => void changeListingStatus(listing, 'PENDING_APPROVAL')} className="h-9 rounded-md border border-amber-200 bg-amber-50 px-3 text-xs font-bold text-amber-700">Gửi duyệt lại</button>}
                    </div>
                  </td>
                </tr>
              ))}
              {!busy && listings.length === 0 && <tr><td colSpan={6} className="px-3 py-10 text-center text-slate-500">Chưa có bài đăng hàng cũ phù hợp.</td></tr>}
            </tbody>
          </table>
        </div>
      )}

      {historyOpen && deviceHistory && (
        <DeviceHistoryModal
          deviceHistory={deviceHistory}
          money={money}
          statusLabels={statusLabels}
          onClose={() => setHistoryOpen(false)}
        />
      )}

      {intakeOpen && (
        <IntakeModal
          busy={busy}
          intakeDraft={intakeDraft}
          products={products}
          selectedProduct={selectedProduct}
          onClose={() => setIntakeOpen(false)}
          onSubmit={submitIntake}
          setIntakeDraft={setIntakeDraft}
        />
      )}

      {inspectionOpen && selectedIntake && (
        <InspectionModal
          busy={busy}
          inspectionDraft={inspectionDraft}
          selectedIntake={selectedIntake}
          onClose={() => setInspectionOpen(false)}
          onSubmit={submitInspection}
          setInspectionDraft={setInspectionDraft}
          uploadInspectionEvidence={uploadInspectionEvidence}
        />
      )}

      {reinspectionOpen && selectedDevice && (
        <ReinspectionModal
          busy={busy}
          inspectionDraft={inspectionDraft}
          selectedDevice={selectedDevice}
          onClose={() => setReinspectionOpen(false)}
          onSubmit={submitReinspection}
          setInspectionDraft={setInspectionDraft}
          uploadInspectionEvidence={uploadInspectionEvidence}
        />
      )}

      {listingOpen && selectedDevice && (
        <ListingModal
          busy={busy}
          listingDraft={listingDraft}
          money={money}
          selectedDevice={selectedDevice}
          onClose={() => setListingOpen(false)}
          onSubmit={submitListing}
          setListingDraft={setListingDraft}
          uploadListingImages={uploadListingImages}
        />
      )}
    </AdminPanel>
  );
}
