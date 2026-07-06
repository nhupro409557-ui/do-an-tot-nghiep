import React from 'react';
import { Download, Upload } from 'lucide-react';
import { AdminPanel, CollapsibleSection, SearchBox, Select } from '../../admin-shell/components/AdminDashboardParts';
import ProductFormSection from './products/ProductFormSection';
import ProductTableSection from './products/ProductTableSection';

type AdminProductsTabProps = Record<string, any>;

export default function AdminProductsTab(props: AdminProductsTabProps) {
  const {
    productCategoryFilter,
    setProductCategoryFilter,
    productBrandFilter,
    setProductBrandFilter,
    productStatusFilter,
    setProductStatusFilter,
    productBrandOptions,
    categories,
    productStatusOptions,
    query,
    setQuery,

    editingProductId,
    productViewOnly,
    productCloseSignal,
    productFormOpen,
    setProductFormOpen,
    openNewProductForm,
    resetProductForm,
    exportProducts,
    importProducts,
    usePermission,
  } = props;
  const canCreateProduct = usePermission('product:create');
  const canUpdateProduct = usePermission('product:update');
  const canDeleteProduct = usePermission('product:delete');

  return (
    <AdminPanel
      title="Quản lý sản phẩm, media và biến thể"
      action={
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={exportProducts}
            className="inline-flex h-10 items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 text-sm font-bold text-slate-700 transition hover:bg-slate-50"
          >
            <Download className="h-4 w-4" />Xuất
          </button>
          {canCreateProduct && (
            <label className="inline-flex h-10 cursor-pointer items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 text-sm font-bold text-slate-700 transition hover:bg-slate-50">
              <Upload className="h-4 w-4" />Import
              <input
                type="file"
                accept=".csv,text/csv"
                className="hidden"
                onChange={(event) => importProducts(event.target.files)}
              />
            </label>
          )}
        </div>
      }
      filters={
        <>
          <Select
            noLabel={true}
            label="Danh mục"
            value={productCategoryFilter}
            onChange={(value) => {
              setProductCategoryFilter(value);
              setProductBrandFilter('');
            }}
            options={[
              ['', 'Tất cả danh mục'],
              ...categories.map((c: any) => [
                String(c.id),
                c.parentName ? `${c.parentName} / ${c.name}` : c.name,
              ] as [string, string]),
            ]}
          />
          <Select
            noLabel={true}
            label="Thương hiệu"
            value={productBrandFilter}
            onChange={setProductBrandFilter}
            options={productBrandOptions || []}
          />
          <Select
            noLabel={true}
            label="Trạng thái"
            value={productStatusFilter}
            onChange={setProductStatusFilter}
            options={[['', 'Tất cả trạng thái'], ...productStatusOptions]}
          />
          <SearchBox
            value={query}
            onChange={setQuery}
            placeholder="Tìm sản phẩm, SKU, thương hiệu"
          />
        </>
      }
    >
      {(canCreateProduct || canUpdateProduct || productViewOnly) && (
        <CollapsibleSection
          title={productViewOnly ? 'Đang xem thông tin sản phẩm' : editingProductId ? 'Đang chỉnh sửa sản phẩm' : 'Thêm sản phẩm mới'}
          description="Mở popup khi cần nhập sản phẩm, media, thông số và biến thể. Bảng sản phẩm bên dưới vẫn luôn sẵn sàng để tìm kiếm."
          defaultOpen={false}
          closeSignal={productCloseSignal}
          open={productFormOpen}
          onOpenChange={(open) => {
            if (open) {
              if (canCreateProduct) openNewProductForm();
              return;
            }
            setProductFormOpen(false);
          }}
          onClose={resetProductForm}
        >
          <ProductFormSection {...(props as any)} />
        </CollapsibleSection>
      )}

      <ProductTableSection {...(props as any)} canCreateProduct={canCreateProduct} canUpdateProduct={canUpdateProduct} canDeleteProduct={canDeleteProduct} />
    </AdminPanel>
  );
}
