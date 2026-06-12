import React from 'react';
import { AdminPanel, AdminTable, SearchBox } from '../../admin-shell/components/AdminDashboardParts';
import { Plus } from 'lucide-react';
import { currency } from '../../admin-shell/components/AdminDashboardConfig';

type AdminInventoryReceiptsTabProps = Record<string, any>;

export default function AdminInventoryReceiptsTab(props: AdminInventoryReceiptsTabProps) {
  const {
    inventoryReceipts,
    openReceiptDialog,
    query,
    setQuery,
  } = props;

  return (
    <AdminPanel
      title="Quản lý nhập kho"
      action={
        <button type="button" onClick={() => openReceiptDialog()} className="inline-flex h-10 items-center gap-2 rounded-xl bg-amber-600 px-4 text-sm font-bold text-white shadow-sm transition hover:bg-amber-700">
          <Plus className="h-4 w-4" /> Tạo phiếu nhập
        </button>
      }
      filters={<SearchBox value={query} onChange={setQuery} placeholder="Tìm mã phiếu, nhà cung cấp, sản phẩm hoặc SKU" />}
    >
      <AdminTable headers={['Mã phiếu', 'Nhà cung cấp', 'Ngày nhập', 'Số dòng', 'Tổng số lượng', 'Giá trị nhập', 'Sản phẩm']}>
        {(inventoryReceipts || []).map((receipt: any) => {
          const firstLines = (receipt.lines || []).slice(0, 3);
          return (
            <tr key={receipt.referenceCode}>
              <td className="px-4 py-3 font-mono text-xs font-bold text-slate-800">{receipt.referenceCode || '-'}</td>
              <td className="px-4 py-3 text-sm font-semibold text-slate-800">{receipt.supplierName || '-'}</td>
              <td className="px-4 py-3 text-sm text-slate-600">{receipt.createdAt ? new Date(receipt.createdAt).toLocaleString('vi-VN') : '-'}</td>
              <td className="px-4 py-3 text-sm font-semibold text-slate-800">{receipt.lineCount || 0}</td>
              <td className="px-4 py-3 text-sm font-semibold text-emerald-700">{receipt.totalQuantity || 0}</td>
              <td className="px-4 py-3 text-sm font-semibold text-slate-800">{currency.format(Number(receipt.totalCost || 0))}</td>
              <td className="px-4 py-3 text-sm text-slate-600">
                <div className="space-y-1">
                  {firstLines.map((line: any) => (
                    <div key={line.id} className="truncate">
                      {line.productName} {line.variantSku ? `- ${line.variantSku}` : ''} <span className="font-semibold text-slate-800">x{line.quantity}</span>
                    </div>
                  ))}
                  {(receipt.lines || []).length > firstLines.length && (
                    <div className="text-xs font-semibold text-slate-400">+{(receipt.lines || []).length - firstLines.length} dòng khác</div>
                  )}
                </div>
              </td>
            </tr>
          );
        })}
      </AdminTable>
    </AdminPanel>
  );
}
