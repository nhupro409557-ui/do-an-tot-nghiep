import React from 'react';
import { CheckCircle2, Image } from 'lucide-react';
import { AdminBadge, AdminTable, RowActions } from '../../AdminDashboardParts';
import { productApi } from '../../../../services/productApi';

interface ProductTableSectionProps {
  selectedProductIds: string[];
  setSelectedProductIds: React.Dispatch<React.SetStateAction<string[]>>;
  bulkApproveProducts: () => void;
  productPage: number;
  setProductPage: (page: number) => void;
  productTotalPages: number;
  productTotal: number;
  filteredProducts: any[];
  compactId: (id: string) => string;
  currency: { format: (value: number) => string };
  productStatusLabel: Record<string, string>;
  editProduct: (product: any) => void;
  confirmDelete: (name: string, onDelete: () => Promise<any>) => Promise<any>;
  reactivateProduct: (product: any) => void;
  submitProduct: (product: any) => void;
  isSuperAdmin: boolean;
  approveProduct: (product: any) => void;
  archiveProduct: (product: any) => void;
}

export default function ProductTableSection(props: ProductTableSectionProps) {
  const {
    selectedProductIds,
    setSelectedProductIds,
    bulkApproveProducts,
    productPage,
    setProductPage,
    productTotalPages,
    productTotal,
    filteredProducts,
    compactId,
    currency,
    productStatusLabel,
    editProduct,
    confirmDelete,
    reactivateProduct,
    submitProduct,
    isSuperAdmin,
    approveProduct,
    archiveProduct,
  } = props;

  return (
    <>
      {selectedProductIds.length > 0 && (
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2 rounded-md border border-sky-100 bg-sky-50 px-3 py-2 text-sm font-semibold text-sky-800">
          <span>Đã chọn {selectedProductIds.length} sản phẩm</span>
          <button
            type="button"
            onClick={bulkApproveProducts}
            className="inline-flex h-9 items-center gap-2 rounded-md bg-sky-700 px-3 text-xs font-bold text-white"
          >
            <CheckCircle2 className="h-4 w-4" />Duyệt hàng loạt
          </button>
        </div>
      )}

      <AdminTable
        headers={[
          'Chọn',
          'Ảnh',
          'Sản phẩm',
          'Danh mục',
          'Thương hiệu',
          'Giá',
          'Kho',
          'Biến thể',
          'Trạng thái',
          'Thao tác',
        ]}
        currentPage={productPage}
        totalPages={Math.max(1, productTotalPages || 1)}
        onPageChange={setProductPage}
        totalCount={productTotal || filteredProducts.length}
        itemName="sản phẩm"
      >
        {filteredProducts.map((product) => (
          <tr key={product.id}>
            <td className="px-4 py-3">
              <input
                type="checkbox"
                checked={selectedProductIds.includes(product.id)}
                onChange={(event) =>
                  setSelectedProductIds((ids) =>
                    event.target.checked
                      ? [...new Set([...ids, product.id])]
                      : ids.filter((id) => id !== product.id)
                  )
                }
                className="h-4 w-4 rounded border-slate-300 text-red-600 focus:ring-red-500"
              />
            </td>
            <td className="px-4 py-3">
              {product.imageUrl ? (
                <img
                  src={product.imageUrl}
                  alt=""
                  className="h-11 w-11 rounded-md object-contain"
                />
              ) : (
                <Image className="h-6 w-6 text-slate-300" />
              )}
            </td>
            <td className="px-4 py-3">
              <div className="font-semibold text-slate-900">{product.name}</div>
              <div className="text-xs text-slate-500">
                {product.sku || compactId(product.id)}
              </div>
            </td>
            <td className="px-4 py-3">
              {product.categoryName || product.category || '-'}
            </td>
            <td className="px-4 py-3">{product.brand || '-'}</td>
            <td className="px-4 py-3 font-semibold text-red-600">
              {currency.format(Number(product.discountPrice || product.price || 0))}
            </td>
            <td className="px-4 py-3">
              <div className="font-semibold">{product.stock ?? 0}</div>
              <AdminBadge tone={Number(product.stock || 0) > 0 ? 'green' : 'yellow'}>
                {Number(product.stock || 0) > 0 ? 'Còn hàng' : 'Hết hàng'}
              </AdminBadge>
            </td>
            <td className="px-4 py-3">{product.variants?.length || 0}</td>
            <td className="px-4 py-3">
              <AdminBadge
                tone={
                  product.status === 'ACTIVE'
                    ? 'green'
                    : product.status === 'PENDING'
                    ? 'blue'
                    : product.status === 'DRAFT'
                    ? 'yellow'
                    : 'slate'
                }
              >
                {productStatusLabel[product.status] || product.status || 'Nháp'}
              </AdminBadge>
            </td>
            <td className="px-4 py-3">
              <div className="flex flex-wrap items-center gap-2">
                {product.status === 'MERGED' ? (
                  <span className="text-xs font-semibold text-slate-500">
                    Đã áp dụng vào sản phẩm gốc
                  </span>
                ) : (
                  <RowActions
                    onEdit={() => editProduct(product)}
                    onDelete={() =>
                      confirmDelete(product.name, () =>
                        productApi.adminDeactivateProduct(product.id)
                      )
                    }
                    onRestore={
                      product.status === 'INACTIVE'
                        ? () => reactivateProduct(product)
                        : undefined
                    }
                  />
                )}
                {(product.status === 'DRAFT' || product.status === 'REVISION_DRAFT') && (
                  <>
                    <button
                      type="button"
                      onClick={() => submitProduct(product)}
                      className="rounded-md border border-sky-200 bg-sky-50 px-2.5 py-1.5 text-xs font-bold text-sky-700"
                    >
                      Gửi duyệt
                    </button>
                    {isSuperAdmin && (
                      <button
                        type="button"
                        onClick={() => approveProduct(product)}
                        className="rounded-md border border-emerald-200 bg-emerald-50 px-2.5 py-1.5 text-xs font-bold text-emerald-700"
                      >
                        Duyệt thẳng
                      </button>
                    )}
                  </>
                )}
                {product.status === 'PENDING' && (
                  <button
                    type="button"
                    onClick={() => approveProduct(product)}
                    className="rounded-md border border-emerald-200 bg-emerald-50 px-2.5 py-1.5 text-xs font-bold text-emerald-700"
                  >
                    Duyệt
                  </button>
                )}
                {(product.status === 'DRAFT' ||
                  product.status === 'REVISION_DRAFT' ||
                  product.status === 'INACTIVE') && (
                  <button
                    type="button"
                    onClick={() => archiveProduct(product)}
                    className="rounded-md border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-xs font-bold text-slate-700"
                  >
                    Lưu trữ
                  </button>
                )}
              </div>
            </td>
          </tr>
        ))}
      </AdminTable>
    </>
  );
}
