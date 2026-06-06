import React from 'react';
import { AdminPanel, AdminTable, SearchBox, Select } from '../../admin-shell/components/AdminDashboardParts';
import { Download } from 'lucide-react';
import { compactId, getInventorySettings } from '../../admin-shell/components/AdminDashboardConfig';

type AdminInventoryTabProps = Record<string, any>;

export default function AdminInventoryTab(props: AdminInventoryTabProps) {
  const {
    categories,
    exportInventorySnapshot,
    filteredInventory,
    inventoryBrandFilter,
    inventoryBrandOptions,
    inventoryCategoryFilter,
    openInventoryDialog,
    query,
    setInventoryBrandFilter,
    setInventoryCategoryFilter,
    setQuery,
  } = props;

  return (
    <AdminPanel 
      title="Quản lý tồn kho" 
      action={
        <button type="button" onClick={() => void exportInventorySnapshot()} className="inline-flex h-10 items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 text-sm font-bold text-slate-700 transition hover:bg-slate-50 shadow-sm"><Download className="h-4 w-4" /> Xuất</button>
      }
      filters={
        <>
          <Select noLabel={true} label="Danh mục" value={inventoryCategoryFilter} onChange={setInventoryCategoryFilter} options={[['', 'Tất cả danh mục'], ...categories.map((c: any) => [String(c.id), c.parentName ? `${c.parentName} / ${c.name}` : c.name] as [string, string])]} />
          <Select noLabel={true} label="Thương hiệu" value={inventoryBrandFilter} onChange={setInventoryBrandFilter} options={inventoryBrandOptions} />
          <SearchBox value={query} onChange={setQuery} placeholder="Tìm sản phẩm, SKU, trạng thái kho" />
        </>
      }
    >
      <AdminTable headers={['Sản phẩm', 'SKU / Biến thể', 'Tồn kho', 'Cảnh báo', 'Trạng thái', 'Điều chỉnh']}>
        {filteredInventory.flatMap((product: any) => {
          const inventorySettings = getInventorySettings(product);
          const rows = [
            <tr key={`${product.id}-base`}>
              <td className="px-4 py-3 font-semibold text-slate-900">{product.name}</td>
              <td className="px-4 py-3 font-mono text-xs">{product.sku || compactId(product.id)}</td>
              <td className="px-4 py-3">{product.stock ?? 0}</td>
              <td className="px-4 py-3">{Number(product.stock || 0) <= inventorySettings.minimumStock ? `Cần nhập thêm (min ${inventorySettings.minimumStock})` : 'Ổn định'}</td>
              <td className="px-4 py-3">{Number(product.stock || 0) > 0 ? 'Còn hàng' : inventorySettings.blockSaleWhenOutOfStock ? 'Khóa bán khi hết' : 'Hết hàng'}</td>
              <td className="px-4 py-3"><button type="button" onClick={() => openInventoryDialog(product)} className="rounded-md border border-amber-200 bg-amber-50 px-3 py-1.5 text-xs font-bold text-amber-800">Nhập/điều chỉnh</button></td>
            </tr>,
          ];
          (product.variants || []).forEach((variant: any) => {
            rows.push(
              <tr key={`${product.id}-${variant.id}`} className="bg-slate-50/60">
                <td className="px-4 py-3 pl-8 text-sm text-slate-600">{product.name}</td>
                <td className="px-4 py-3 font-mono text-xs">{variant.sku || compactId(variant.id)} {variant.colorName ? `- ${variant.colorName}` : ''}</td>
                <td className="px-4 py-3">{variant.stockQuantity ?? 0}</td>
                <td className="px-4 py-3">{Number(variant.stockQuantity || 0) <= inventorySettings.minimumStock ? `Cần nhập thêm (min ${inventorySettings.minimumStock})` : 'Ổn định'}</td>
                <td className="px-4 py-3">{variant.isActive === false ? 'Đã ẩn' : Number(variant.stockQuantity || 0) > 0 ? 'Còn hàng' : 'Hết hàng'}</td>
                <td className="px-4 py-3"><button type="button" onClick={() => openInventoryDialog(product, variant)} className="rounded-md border border-amber-200 bg-amber-50 px-3 py-1.5 text-xs font-bold text-amber-800">Nhập/điều chỉnh</button></td>
              </tr>,
            );
          });
          return rows;
        })}
      </AdminTable>
    </AdminPanel>
  );
}
