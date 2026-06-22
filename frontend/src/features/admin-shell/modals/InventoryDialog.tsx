import React from 'react';
import { Input, Select } from '../components/AdminDashboardParts';
import { Plus, Trash2, X } from 'lucide-react';

type InventoryDialogProps = Record<string, any>;

function TableSelect({
  label,
  value,
  options,
  disabled = false,
  onChange,
}: {
  label: string;
  value: string;
  options: [string, string][];
  disabled?: boolean;
  onChange: (value: string) => void;
}) {
  return (
    <select
      aria-label={label}
      value={value}
      disabled={disabled}
      onChange={(event) => onChange(event.target.value)}
      className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm font-semibold text-slate-800 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400"
    >
      {options.map(([optionValue, labelText]) => (
        <option key={optionValue || labelText} value={optionValue}>
          {labelText}
        </option>
      ))}
    </select>
  );
}

const receiptReasonOptions: [string, string][] = [
  ['NK_MUA', 'NK_MUA - Nhập mua từ nhà cung cấp'],
  ['NK_TRA_NCC', 'NK_TRA_NCC - Nhà cung cấp trả lại hàng'],
  ['NK_KH_TRA', 'NK_KH_TRA - Khách hàng trả hàng'],
  ['NK_BH', 'NK_BH - Nhập bảo hành'],
  ['NK_DIEUCHINH', 'NK_DIEUCHINH - Điều chỉnh tăng tồn kho'],
  ['NK_CHUYEN', 'NK_CHUYEN - Nhập từ kho khác'],
  ['NK_SANXUAT', 'NK_SANXUAT - Nhập thành phẩm'],
  ['NK_KHOI_TAO', 'NK_KHOI_TAO - Nhập kho khởi tạo'],
  ['NK_KHAC', 'NK_KHAC - Nhập khác'],
];

const receiptReasonDescriptions: Record<string, string> = {
  NK_MUA: 'Nhập hàng mới theo đơn mua hàng.',
  NK_TRA_NCC: 'NCC gửi lại hàng đã đổi hoặc bổ sung.',
  NK_KH_TRA: 'Khách trả hàng bán ra còn đủ điều kiện nhập lại.',
  NK_BH: 'Nhận sản phẩm khách gửi bảo hành.',
  NK_DIEUCHINH: 'Kiểm kê phát hiện dư hàng, nhập bổ sung.',
  NK_CHUYEN: 'Nhận hàng chuyển từ chi nhánh/kho khác.',
  NK_SANXUAT: 'Dùng khi doanh nghiệp tự sản xuất hoặc lắp ráp.',
  NK_KHOI_TAO: 'Khởi tạo tồn kho từ dữ liệu sản phẩm hiện có.',
  NK_KHAC: 'Các trường hợp đặc biệt, bắt buộc ghi rõ lý do trong ghi chú chung.',
};

const locationPurposeLabel: Record<string, string> = {
  STORAGE: 'Kệ lưu hàng bán',
  QC: 'Kệ QC',
  WARRANTY: 'Kệ bảo hành',
  DAMAGED: 'Kệ hàng lỗi',
  RETURN: 'Kệ hàng trả',
  VIRTUAL: 'Kệ hệ thống',
};

const receiptReasonLocationPurposes: Record<string, string[]> = {
  NK_MUA: ['STORAGE'],
  NK_TRA_NCC: ['STORAGE', 'QC'],
  NK_KH_TRA: ['RETURN', 'QC'],
  NK_BH: ['WARRANTY'],
  NK_DIEUCHINH: ['STORAGE'],
  NK_CHUYEN: ['STORAGE'],
  NK_SANXUAT: ['STORAGE'],
  NK_KHOI_TAO: ['STORAGE'],
  NK_KHAC: ['STORAGE', 'QC', 'WARRANTY', 'DAMAGED', 'RETURN', 'VIRTUAL'],
};

function getAllowedLocationPurposes(receiptReasonCode: string) {
  const normalized = String(receiptReasonCode || 'NK_MUA').toUpperCase();
  return receiptReasonLocationPurposes[normalized] || receiptReasonLocationPurposes.NK_MUA;
}

const qualityStatusOptions: [string, string][] = [
  ['PENDING', 'Chờ kiểm tra'],
  ['PASSED', 'Đạt'],
  ['FAILED', 'Không đạt'],
];

const attachmentTypeOptions: [string, string][] = [
  ['INVOICE', 'Hóa đơn'],
  ['DELIVERY_NOTE', 'Phiếu giao hàng'],
  ['GOODS_PHOTO', 'Ảnh hàng hóa'],
  ['OTHER', 'Khác'],
];

const discrepancyTypeOptions: [string, string][] = [
  ['SHORTAGE', 'Thiếu hàng'],
  ['OVERAGE', 'Thừa hàng'],
  ['DAMAGED', 'Hư hỏng'],
  ['WRONG_ITEM', 'Sai hàng'],
  ['OTHER', 'Khác'],
];

export default function InventoryDialog(props: InventoryDialogProps) {
  const {
    inventoryDraft,
    setInventoryDraft,
    submitInventoryDraft,
    products,
    categories,
    brands,
    suppliers,
    inventoryLocations,
    addReceiptLine,
    removeReceiptLine,
    updateReceiptLine,
    resolveProduct,
    categoryTracksImei,
    categoryTracksSerialNumber,
    productMatchesReceiptFilters,
    selectReceiptPickerProduct,
    toggleReceiptVariantSelection,
    clearReceiptVariantSelection,
    selectAllPickerVariants,
    addSelectedVariantsToReceipt,
    uploadFiles,
  } = props;

  const [isUploadingAttachment, setIsUploadingAttachment] = React.useState(false);

  if (!inventoryDraft) return null;

  const activeSuppliers = (suppliers || []).filter((supplier: any) => supplier.isActive !== false);
  const supplierOptions: [string, string][] = [
    ['', 'Chọn nhà cung cấp'],
    ...activeSuppliers.map((supplier: any) => [String(supplier.id), `${supplier.name}${supplier.code ? ` - ${supplier.code}` : ''}`] as [string, string]),
  ];
  const categoryOptions: [string, string][] = [
    ['', 'Tất cả danh mục'],
    ...categories.map((category: any) => [String(category.id), category.parentName ? `${category.parentName} / ${category.name}` : category.name] as [string, string]),
  ];
  function productMatchesPickerCategory(product: any, categoryId: string) {
    if (!categoryId) return true;
    const matchesCategory = String(product.categoryId) === categoryId || String(product.subcategoryId) === categoryId;
    const matchesChild = categories.some((category: any) => (
      String(category.parentId) === categoryId
      && (String(product.categoryId) === String(category.id) || String(product.subcategoryId) === String(category.id))
    ));
    return matchesCategory || matchesChild;
  }
  const pickerBrandIds = new Set(
    products
      .filter((product: any) => !productMatchesPickerCategory(product, inventoryDraft.pickerCategoryId) ? false : Boolean(product.brandId))
      .map((product: any) => String(product.brandId)),
  );
  const brandOptions: [string, string][] = [
    ['', 'Tất cả thương hiệu'],
    ...brands
      .filter((brand: any) => !inventoryDraft.pickerCategoryId || pickerBrandIds.has(String(brand.id)))
      .map((brand: any) => [String(brand.id), brand.name] as [string, string]),
  ];
  const productOptions: [string, string][] = [
    ['', 'Chọn sản phẩm'],
    ...products.map((product: any) => [String(product.id), product.name] as [string, string]),
  ];
  const filteredPickerProducts = products.filter((product: any) => productMatchesReceiptFilters(product));
  const pickerProduct = resolveProduct(inventoryDraft.selectedProductId);
  const pickerVariants = pickerProduct?.variants || [];
  const allowedLocationPurposes = getAllowedLocationPurposes(inventoryDraft.receiptReasonCode || 'NK_MUA');
  const activeLocations = (inventoryLocations || []).filter((location: any) => String(location.status || 'ACTIVE') === 'ACTIVE');
  const reasonMatchedLocations = activeLocations.filter((location: any) => allowedLocationPurposes.includes(String(location.purpose || 'STORAGE').toUpperCase()));
  const receiptReasonLocations = reasonMatchedLocations.length > 0 ? reasonMatchedLocations : activeLocations;
  const allowedLocationSummary = allowedLocationPurposes.map((purpose) => locationPurposeLabel[purpose] || purpose).join(', ');
  const formatLocationCapacity = (location: any) => {
    if (location.fillRatio == null || location.availableVolumeCm3 == null) return '';
    const fillPercent = Math.round(Number(location.fillRatio || 0) * 100);
    const available = Number(location.availableVolumeCm3 || 0).toLocaleString('vi-VN');
    return ` · đầy ${fillPercent}% · còn ${available} cm³`;
  };

  const reasonLocationOptions: [string, string][] = [
    ['', reasonMatchedLocations.length > 0 ? 'Chọn kệ theo lý do nhập' : 'Chọn kệ hàng'],
    ...receiptReasonLocations.map((location: any) => {
      const purpose = String(location.purpose || 'STORAGE').toUpperCase();
      const purposeLabel = locationPurposeLabel[purpose] || purpose;
      return [String(location.id), `${location.code} - ${location.name}${location.zone ? ` (${location.zone})` : ''} · ${purposeLabel}${formatLocationCapacity(location)}`] as [string, string];
    }),
  ];

  function handleSupplierChange(supplierId: string) {
    const supplier = activeSuppliers.find((item: any) => String(item.id) === supplierId);
    setInventoryDraft({ ...inventoryDraft, supplierId, supplierName: supplier?.name || '' });
  }

  function handleReceiptReasonChange(receiptReasonCode: string) {
    const nextAllowedPurposes = getAllowedLocationPurposes(receiptReasonCode);
    const nextAllowedLocationIds = new Set(
      activeLocations
        .filter((location: any) => nextAllowedPurposes.includes(String(location.purpose || 'STORAGE').toUpperCase()))
        .map((location: any) => String(location.id)),
    );
    setInventoryDraft({
      ...inventoryDraft,
      receiptReasonCode,
      lines: inventoryDraft.lines.map((line: any) => {
        if (!line.warehouseLocationId || nextAllowedLocationIds.has(String(line.warehouseLocationId))) return line;
        return {
          ...line,
          warehouseLocationId: '',
          storageLocationCode: '',
          storageLocationName: '',
        };
      }),
    });
  }

  function handlePickerCategoryChange(categoryId: string) {
    const nextBrandValid = !inventoryDraft.pickerBrandId || products.some((product: any) => (
      productMatchesPickerCategory(product, categoryId) && String(product.brandId) === inventoryDraft.pickerBrandId
    ));
    setInventoryDraft({
      ...inventoryDraft,
      pickerCategoryId: categoryId,
      pickerBrandId: nextBrandValid ? inventoryDraft.pickerBrandId : '',
      selectedProductId: '',
      selectedVariantIds: [],
    });
  }

  function formatVariantName(variant: any) {
    return [variant.colorName, variant.configuration].filter(Boolean).join(' - ') || 'Biến thể';
  }

  function addAttachment() {
    setInventoryDraft({
      ...inventoryDraft,
      attachments: [...(inventoryDraft.attachments || []), { type: 'INVOICE', name: '', url: '', note: '' }],
    });
  }

  function updateAttachment(index: number, patch: any) {
    setInventoryDraft({
      ...inventoryDraft,
      attachments: (inventoryDraft.attachments || []).map((item: any, itemIndex: number) => itemIndex === index ? { ...item, ...patch } : item),
    });
  }

  function removeAttachment(index: number) {
    setInventoryDraft({
      ...inventoryDraft,
      attachments: (inventoryDraft.attachments || []).filter((_: any, itemIndex: number) => itemIndex !== index),
    });
  }

  function addDiscrepancy() {
    setInventoryDraft({
      ...inventoryDraft,
      discrepancies: [...(inventoryDraft.discrepancies || []), { type: 'SHORTAGE', description: '', quantity: '', action: '' }],
    });
  }

  function updateDiscrepancy(index: number, patch: any) {
    setInventoryDraft({
      ...inventoryDraft,
      discrepancies: (inventoryDraft.discrepancies || []).map((item: any, itemIndex: number) => itemIndex === index ? { ...item, ...patch } : item),
    });
  }

  function removeDiscrepancy(index: number) {
    setInventoryDraft({
      ...inventoryDraft,
      discrepancies: (inventoryDraft.discrepancies || []).filter((_: any, itemIndex: number) => itemIndex !== index),
    });
  }

  async function handleAttachmentUpload(files: FileList | null) {
    if (!files || files.length === 0 || typeof uploadFiles !== 'function') return;
    setIsUploadingAttachment(true);
    try {
      const urls = await uploadFiles(files, 'inventory');
      if (urls.length > 0) {
        const nextAttachments = [
          ...(inventoryDraft.attachments || []),
          ...urls.map((url: string, index: number) => ({
            type: files[index]?.type?.startsWith('image/') ? 'GOODS_PHOTO' : 'OTHER',
            name: files[index]?.name || 'Chứng từ nhập hàng',
            url,
            note: '',
          })),
        ];
        setInventoryDraft({ ...inventoryDraft, attachments: nextAttachments });
      }
    } finally {
      setIsUploadingAttachment(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-950/55 px-4 py-6 backdrop-blur-sm">
      <form onSubmit={submitInventoryDraft} className="w-full max-w-7xl overflow-hidden rounded-lg bg-white shadow-2xl">
        <div className="flex items-start justify-between gap-4 border-b border-slate-200 px-5 py-4">
          <div>
            <h3 className="text-lg font-bold text-slate-950">Phiếu nhập kho</h3>
            <p className="mt-1 text-sm text-slate-500">Lập phiếu với số lượng dự kiến. IMEI được bổ sung ở bước xử lý riêng sau khi khóa số lượng.</p>
          </div>
          <button type="button" onClick={() => setInventoryDraft(null)} title="Đóng popup" className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-slate-200 text-slate-600 transition hover:bg-slate-50 hover:text-slate-950">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="space-y-4 p-5">
          <div className="grid gap-3 md:grid-cols-[180px_minmax(240px,1fr)_minmax(220px,1fr)_minmax(220px,1fr)]">
            <Input label="Mã phiếu nhập" value={inventoryDraft.referenceCode} disabled onChange={() => undefined} />
            <div>
              <Select label="Lý do nhập kho" value={inventoryDraft.receiptReasonCode || 'NK_MUA'} onChange={handleReceiptReasonChange} options={receiptReasonOptions} />
              <div className="mt-1 text-xs font-semibold text-slate-500">{receiptReasonDescriptions[inventoryDraft.receiptReasonCode || 'NK_MUA']}</div>
              <div className="mt-1 text-xs font-semibold text-emerald-700">Kệ gợi ý: {allowedLocationSummary}</div>
            </div>
            <Select label="Nhà cung cấp" value={inventoryDraft.supplierId} onChange={handleSupplierChange} options={supplierOptions} />
            <Input label="Ghi chú chung" value={inventoryDraft.note} onChange={(value) => setInventoryDraft({ ...inventoryDraft, note: value })} />
          </div>

          <div className="grid gap-3 rounded-lg border border-slate-200 bg-white p-3 lg:grid-cols-[220px_minmax(240px,1fr)_220px]">
            <Select label="Kiểm tra chất lượng" value={inventoryDraft.qualityStatus || 'PENDING'} onChange={(value) => setInventoryDraft({ ...inventoryDraft, qualityStatus: value })} options={qualityStatusOptions} />
            <Input label="Ghi chú QC" value={inventoryDraft.qualityNote || ''} placeholder="Ví dụ: đủ phụ kiện, tem seal nguyên vẹn" onChange={(value) => setInventoryDraft({ ...inventoryDraft, qualityNote: value })} />
            <div className="space-y-2">
              <label className="flex min-h-10 items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 text-sm font-bold text-slate-700">
                <input
                  type="checkbox"
                  checked={Boolean(inventoryDraft.quarantine)}
                  onChange={(event) => setInventoryDraft({ ...inventoryDraft, quarantine: event.target.checked })}
                  className="h-4 w-4 rounded border-slate-300 text-amber-600 focus:ring-amber-500"
                />
                Cách ly hàng
              </label>
              <Input label="Khu cách ly" value={inventoryDraft.quarantineLocation || ''} placeholder="Khu QC / Kệ cách ly" onChange={(value) => setInventoryDraft({ ...inventoryDraft, quarantineLocation: value })} />
            </div>
          </div>

          <div className="grid gap-3 lg:grid-cols-2">
            <div className="rounded-lg border border-slate-200 bg-white p-3">
              <div className="mb-3 flex items-center justify-between gap-3">
                <div>
                  <div className="text-sm font-bold text-slate-900">Chứng từ nhập hàng</div>
                  <div className="text-xs font-medium text-slate-500">Hóa đơn, phiếu giao hàng, ảnh hàng hóa hoặc đường dẫn file.</div>
                </div>
                <div className="flex flex-wrap gap-2">
                  <label className="inline-flex h-8 cursor-pointer items-center gap-1 rounded-md border border-indigo-200 bg-indigo-50 px-2.5 text-xs font-bold text-indigo-700">
                    {isUploadingAttachment ? 'Đang tải...' : 'Tải file'}
                    <input
                      type="file"
                      multiple
                      accept="image/*,.pdf,.doc,.docx,.xls,.xlsx"
                      disabled={isUploadingAttachment}
                      onChange={(event) => {
                        void handleAttachmentUpload(event.target.files);
                        event.currentTarget.value = '';
                      }}
                      className="hidden"
                    />
                  </label>
                  <button type="button" onClick={addAttachment} className="inline-flex h-8 items-center gap-1 rounded-md border border-slate-200 bg-white px-2.5 text-xs font-bold text-slate-700">
                    <Plus className="h-3.5 w-3.5" /> Thêm link
                  </button>
                </div>
              </div>
              <div className="space-y-2">
                {(inventoryDraft.attachments || []).length === 0 && <div className="rounded-md bg-slate-50 px-3 py-2 text-xs font-semibold text-slate-500">Chưa có chứng từ.</div>}
                {(inventoryDraft.attachments || []).map((item: any, index: number) => (
                  <div key={index} className="grid gap-2 rounded-md border border-slate-100 bg-slate-50 p-2 md:grid-cols-[150px_1fr_1fr_36px]">
                    <TableSelect label="Loại chứng từ" value={item.type || 'OTHER'} onChange={(value) => updateAttachment(index, { type: value })} options={attachmentTypeOptions} />
                    <Input label="Tên chứng từ" value={item.name || ''} placeholder="Số hóa đơn / ảnh kiện hàng" onChange={(value) => updateAttachment(index, { name: value })} noLabel />
                    <Input label="URL" value={item.url || ''} placeholder="https://... hoặc /uploads/..." onChange={(value) => updateAttachment(index, { url: value })} noLabel />
                    <button type="button" onClick={() => removeAttachment(index)} title="Xóa chứng từ" className="inline-flex h-10 w-9 items-center justify-center rounded-md border border-slate-200 bg-white text-slate-500 hover:bg-red-50 hover:text-red-700">
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-lg border border-slate-200 bg-white p-3">
              <div className="mb-3 flex items-center justify-between gap-3">
                <div>
                  <div className="text-sm font-bold text-slate-900">Biên bản sai lệch</div>
                  <div className="text-xs font-medium text-slate-500">Ghi thiếu, thừa, hư hỏng hoặc sai hàng khi tiếp nhận.</div>
                </div>
                <button type="button" onClick={addDiscrepancy} className="inline-flex h-8 items-center gap-1 rounded-md border border-slate-200 bg-white px-2.5 text-xs font-bold text-slate-700">
                  <Plus className="h-3.5 w-3.5" /> Thêm
                </button>
              </div>
              <div className="space-y-2">
                {(inventoryDraft.discrepancies || []).length === 0 && <div className="rounded-md bg-slate-50 px-3 py-2 text-xs font-semibold text-slate-500">Chưa ghi nhận sai lệch.</div>}
                {(inventoryDraft.discrepancies || []).map((item: any, index: number) => (
                  <div key={index} className="grid gap-2 rounded-md border border-slate-100 bg-slate-50 p-2 md:grid-cols-[140px_1fr_100px_1fr_36px]">
                    <TableSelect label="Loại sai lệch" value={item.type || 'OTHER'} onChange={(value) => updateDiscrepancy(index, { type: value })} options={discrepancyTypeOptions} />
                    <Input label="Mô tả" value={item.description || ''} placeholder="Ví dụ: vỡ hộp, thiếu phụ kiện" onChange={(value) => updateDiscrepancy(index, { description: value })} noLabel />
                    <Input label="SL" type="number" value={item.quantity || ''} onChange={(value) => updateDiscrepancy(index, { quantity: value })} noLabel />
                    <Input label="Xử lý" value={item.action || ''} placeholder="Đổi hàng / chờ NCC xác nhận" onChange={(value) => updateDiscrepancy(index, { action: value })} noLabel />
                    <button type="button" onClick={() => removeDiscrepancy(index)} title="Xóa sai lệch" className="inline-flex h-10 w-9 items-center justify-center rounded-md border border-slate-200 bg-white text-slate-500 hover:bg-red-50 hover:text-red-700">
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
            <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="text-sm font-bold text-slate-900">Thêm biến thể vào phiếu</div>
                <div className="text-xs font-medium text-slate-500">Chỉ những biến thể được tick mới sinh dòng nhập.</div>
              </div>
              <div className="flex flex-wrap gap-2">
                <button type="button" onClick={selectAllPickerVariants} disabled={!pickerProduct || pickerVariants.length === 0} className="h-9 rounded-md border border-slate-200 bg-white px-3 text-xs font-bold text-slate-700 disabled:cursor-not-allowed disabled:opacity-50">Chọn tất cả biến thể</button>
                <button type="button" onClick={clearReceiptVariantSelection} className="h-9 rounded-md border border-slate-200 bg-white px-3 text-xs font-bold text-slate-700">Bỏ chọn</button>
                <button type="button" onClick={addSelectedVariantsToReceipt} disabled={!pickerProduct || (pickerVariants.length > 0 && inventoryDraft.selectedVariantIds.length === 0)} className="inline-flex h-9 items-center gap-2 rounded-md bg-amber-600 px-3 text-xs font-bold text-white disabled:cursor-not-allowed disabled:opacity-50">
                  <Plus className="h-4 w-4" /> Thêm biến thể
                </button>
              </div>
            </div>

            <div className="grid gap-3 md:grid-cols-[minmax(180px,1fr)_minmax(180px,1fr)_minmax(220px,1.2fr)]">
              <Select label="Danh mục" value={inventoryDraft.pickerCategoryId} onChange={handlePickerCategoryChange} options={categoryOptions} />
              <Select label="Thương hiệu" value={inventoryDraft.pickerBrandId} onChange={(value) => setInventoryDraft({ ...inventoryDraft, pickerBrandId: value, selectedProductId: '', selectedVariantIds: [] })} options={brandOptions} />
              <Input label="Tìm sản phẩm" value={inventoryDraft.pickerSearch} placeholder="Tên sản phẩm" onChange={(value) => setInventoryDraft({ ...inventoryDraft, pickerSearch: value })} />
            </div>

            <div className="mt-3 grid gap-3 lg:grid-cols-[minmax(320px,1fr)_minmax(340px,1fr)]">
              <div className="max-h-72 overflow-y-auto rounded-md border border-slate-200 bg-white">
                {filteredPickerProducts.length === 0 ? (
                  <div className="px-3 py-4 text-sm font-medium text-slate-500">Không có sản phẩm phù hợp.</div>
                ) : (
                  filteredPickerProducts.slice(0, 80).map((product: any) => {
                    const selected = String(product.id) === inventoryDraft.selectedProductId;
                    return (
                      <button key={product.id} type="button" onClick={() => selectReceiptPickerProduct(String(product.id))} className={`flex w-full items-center gap-3 border-b border-slate-100 px-3 py-2 text-left text-sm last:border-b-0 ${selected ? 'bg-amber-50' : 'hover:bg-slate-50'}`}>
                        <span className="min-w-0 flex-1">
                          <span className="block truncate font-semibold text-slate-800">{product.name}</span>
                          <span className="block truncate text-xs text-slate-500">{(product.variants || []).length || 0} biến thể</span>
                        </span>
                        {categoryTracksImei(product) && <span className="shrink-0 rounded-full bg-indigo-50 px-2 py-1 text-xs font-bold text-indigo-700">Cần IMEI</span>}
                        {categoryTracksSerialNumber(product) && <span className="shrink-0 rounded-full bg-cyan-50 px-2 py-1 text-xs font-bold text-cyan-700">Cần serial</span>}
                      </button>
                    );
                  })
                )}
              </div>

              <div className="max-h-72 overflow-y-auto rounded-md border border-slate-200 bg-white">
                {!pickerProduct ? (
                  <div className="px-3 py-4 text-sm font-medium text-slate-500">Chọn một sản phẩm để xem biến thể.</div>
                ) : pickerVariants.length === 0 ? (
                  <label className="flex cursor-pointer items-center gap-3 px-3 py-3 text-sm hover:bg-slate-50">
                    <input type="checkbox" checked={inventoryDraft.selectedProductId !== ''} readOnly className="h-4 w-4 rounded border-slate-300 text-amber-600 focus:ring-amber-500" />
                    <span className="font-semibold text-slate-800">{pickerProduct.name}</span>
                  </label>
                ) : (
                  pickerVariants.map((variant: any) => {
                    const checked = inventoryDraft.selectedVariantIds.includes(String(variant.id));
                    return (
                      <label key={variant.id} className="flex cursor-pointer items-center gap-3 border-b border-slate-100 px-3 py-2 text-sm last:border-b-0 hover:bg-slate-50">
                        <input type="checkbox" checked={checked} onChange={() => toggleReceiptVariantSelection(String(variant.id))} className="h-4 w-4 rounded border-slate-300 text-amber-600 focus:ring-amber-500" />
                        <span className="min-w-0 flex-1">
                          <span className="block truncate font-semibold text-slate-800">{formatVariantName(variant)}</span>
                        </span>
                        <span className="shrink-0 text-xs font-bold text-slate-500">Tồn {variant.stockQuantity ?? 0}</span>
                      </label>
                    );
                  })
                )}
              </div>
            </div>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between gap-3">
              <div>
                <div className="text-sm font-bold text-slate-900">Danh sách sản phẩm nhập</div>
                <div className="text-xs font-medium text-slate-500">Số lượng ở bước này là số lượng dự kiến; sau khi khóa phiếu mới xử lý IMEI và số lượng thực nhận.</div>
              </div>
              <button type="button" onClick={addReceiptLine} className="inline-flex h-9 items-center gap-2 rounded-md border border-amber-200 bg-amber-50 px-3 text-sm font-bold text-amber-800 transition hover:bg-amber-100">
                <Plus className="h-4 w-4" /> Thêm dòng trống
              </button>
            </div>

            <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
              <table className="min-w-[1480px] w-full table-fixed text-left text-sm">
                <colgroup>
                  <col className="w-12" />
                  <col className="w-[430px]" />
                  <col className="w-[340px]" />
                  <col className="w-28" />
                  <col className="w-36" />
                  <col className="w-64" />
                  <col className="w-48" />
                  <col className="w-56" />
                  <col className="w-16" />
                </colgroup>
                <thead className="bg-slate-50 text-xs font-bold uppercase text-slate-500">
                  <tr>
                    <th className="px-3 py-3 whitespace-nowrap">#</th>
                    <th className="px-3 py-3 whitespace-nowrap">Sản phẩm</th>
                    <th className="px-3 py-3 whitespace-nowrap">Biến thể</th>
                    <th className="px-3 py-3 whitespace-nowrap">Số lượng</th>
                    <th className="px-3 py-3 whitespace-nowrap">Giá nhập</th>
                    <th className="px-3 py-3 whitespace-nowrap">Kệ hàng</th>
                    <th className="px-3 py-3 whitespace-nowrap">Lý do</th>
                    <th className="px-3 py-3 whitespace-nowrap">Ghi chú</th>
                    <th className="px-3 py-3"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {inventoryDraft.lines.map((line: any, index: number) => {
                    const product = resolveProduct(line.productId);
                    const variants = product?.variants || [];
                    const variantOptions: [string, string][] = [
                      ['', variants.length > 1 ? 'Chọn biến thể' : 'Tự chọn biến thể duy nhất'],
                      ...variants.map((variant: any) => [String(variant.id), formatVariantName(variant)] as [string, string]),
                    ];

                    return (
                      <tr key={line.id} className="align-top">
                        <td className="px-3 py-3 text-xs font-bold text-slate-400">{index + 1}</td>
                        <td className="px-3 py-3">
                          <TableSelect label="Sản phẩm" value={line.productId} onChange={(value) => updateReceiptLine(line.id, { productId: value })} options={productOptions} />
                        </td>
                        <td className="px-3 py-3">
                          <TableSelect label="Biến thể" value={line.variantId} disabled={!product || variants.length <= 1} onChange={(value) => updateReceiptLine(line.id, { variantId: value })} options={variantOptions} />
                        </td>
                        <td className="px-3 py-3"><Input label="Số lượng" type="number" value={line.quantity} onChange={(value) => updateReceiptLine(line.id, { quantity: Math.max(1, Number(value)) })} noLabel /></td>
                        <td className="px-3 py-3"><Input label="Giá nhập" type="number" value={line.unitCost} onChange={(value) => updateReceiptLine(line.id, { unitCost: Number(value) })} noLabel /></td>
                        <td className="px-3 py-3">
                          <TableSelect
                            label="Kệ hàng"
                            value={line.warehouseLocationId || ''}
                            onChange={(value) => {
                              const location = (inventoryLocations || []).find((item: any) => String(item.id) === value);
                              updateReceiptLine(line.id, {
                                warehouseLocationId: value,
                                storageLocationCode: location?.code || '',
                                storageLocationName: location?.name || '',
                              });
                            }}
                            options={reasonLocationOptions}
                          />
                        </td>
                        <td className="px-3 py-3"><Input label="Lý do" value={line.reason} onChange={(value) => updateReceiptLine(line.id, { reason: value })} noLabel /></td>
                        <td className="px-3 py-3"><Input label="Ghi chú" value={line.note} onChange={(value) => updateReceiptLine(line.id, { note: value })} noLabel /></td>
                        <td className="px-3 py-3">
                          <button type="button" onClick={() => removeReceiptLine(line.id)} disabled={inventoryDraft.lines.length <= 1} className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-slate-200 bg-white text-slate-500 transition hover:bg-red-50 hover:text-red-700 disabled:cursor-not-allowed disabled:opacity-40" title="Xóa dòng">
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          <div className="flex flex-wrap justify-end gap-2">
            <button type="button" onClick={() => setInventoryDraft(null)} className="h-10 rounded-md border border-slate-200 px-4 text-sm font-bold text-slate-700">Hủy</button>
            <button type="submit" className="h-10 rounded-md bg-amber-600 px-4 text-sm font-bold text-white">Lưu nháp</button>
          </div>
        </div>
      </form>
    </div>
  );
}
