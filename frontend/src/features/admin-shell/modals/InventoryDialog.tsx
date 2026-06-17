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

export default function InventoryDialog(props: InventoryDialogProps) {
  const {
    inventoryDraft,
    setInventoryDraft,
    submitInventoryDraft,
    products,
    categories,
    brands,
    suppliers,
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
  } = props;

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
  const brandOptions: [string, string][] = [
    ['', 'Tất cả thương hiệu'],
    ...brands.map((brand: any) => [String(brand.id), brand.name] as [string, string]),
  ];
  const productOptions: [string, string][] = [
    ['', 'Chọn sản phẩm'],
    ...products.map((product: any) => [String(product.id), product.name] as [string, string]),
  ];
  const filteredPickerProducts = products.filter((product: any) => productMatchesReceiptFilters(product));
  const pickerProduct = resolveProduct(inventoryDraft.selectedProductId);
  const pickerVariants = pickerProduct?.variants || [];

  function handleSupplierChange(supplierId: string) {
    const supplier = activeSuppliers.find((item: any) => String(item.id) === supplierId);
    setInventoryDraft({ ...inventoryDraft, supplierId, supplierName: supplier?.name || '' });
  }

  function formatVariantName(variant: any) {
    return [variant.colorName, variant.configuration].filter(Boolean).join(' - ') || 'Biến thể';
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
              <Select label="Lý do nhập kho" value={inventoryDraft.receiptReasonCode || 'NK_MUA'} onChange={(value) => setInventoryDraft({ ...inventoryDraft, receiptReasonCode: value })} options={receiptReasonOptions} />
              <div className="mt-1 text-xs font-semibold text-slate-500">{receiptReasonDescriptions[inventoryDraft.receiptReasonCode || 'NK_MUA']}</div>
            </div>
            <Select label="Nhà cung cấp" value={inventoryDraft.supplierId} onChange={handleSupplierChange} options={supplierOptions} />
            <Input label="Ghi chú chung" value={inventoryDraft.note} onChange={(value) => setInventoryDraft({ ...inventoryDraft, note: value })} />
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
              <Select label="Danh mục" value={inventoryDraft.pickerCategoryId} onChange={(value) => setInventoryDraft({ ...inventoryDraft, pickerCategoryId: value, selectedProductId: '', selectedVariantIds: [] })} options={categoryOptions} />
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
              <table className="min-w-[1280px] w-full table-fixed text-left text-sm">
                <colgroup>
                  <col className="w-12" />
                  <col className="w-[430px]" />
                  <col className="w-[340px]" />
                  <col className="w-28" />
                  <col className="w-36" />
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
