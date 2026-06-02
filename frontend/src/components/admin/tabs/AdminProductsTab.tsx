import React from 'react';
import { CheckCircle2, Download, Image, Plus, Trash2, Upload } from 'lucide-react';
import { AdminBadge, AdminPagination, AdminPanel, AdminTable, Checkbox, CollapsibleSection, FileInput, Input, MediaPreview, RowActions, SearchBox, Select, SubmitButtons, VideoPreview } from '../AdminDashboardParts';
import { apiDb } from '../../../services/apiDb';

type AdminProductsTabProps = Record<string, any>;

export default function AdminProductsTab(props: AdminProductsTabProps) {
  const {
    productCategoryFilter,
    setProductCategoryFilter,
    productBrandFilter,
    setProductBrandFilter,
    productStatusFilter,
    setProductStatusFilter,
    productPage,
    setProductPage,
    productTotal,
    productTotalPages,
    productBrandOptions,
    accessoryBrandFilter,
    accessoryCategoryFilter,
    accessoryProductChoices,
    accessorySearch,
    addAccessoryOffer,
    addAttachedService,
    addVariant,
    approveProduct,
    archiveProduct,
    attachedServiceGroupFilter,
    attachedServiceSearch,
    attachedServiceTypeFilter,
    brands,
    buildVariantSku,
    bulkApproveProducts,
    categories,
    categoryWarrantyPolicy,
    compactId,
    confirmDelete,
    currency,
    editProduct,
    editingProductId,
    exportProducts,
    filteredProducts,
    groupedActiveVariantFields,
    groupedProductSpecFields,
    handleProductSubmit,
    importProducts,
    patchAccessoryOffer,
    patchVariant,
    productAttachedServiceChoices,
    productCloseSignal,
    productForm,
    productSpecFields,
    productStatusLabel,
    productStatusOptions,
    query,
    reactivateProduct,
    removeAccessoryOffer,
    removeAttachedService,
    resetProductForm,
    rootCategories,
    selectedCategory,
    selectedProductIds,
    serviceGroupOptions,
    setAccessoryBrandFilter,
    setAccessoryCategoryFilter,
    setAccessorySearch,
    setAttachedServiceGroupFilter,
    setAttachedServiceSearch,
    setAttachedServiceTypeFilter,
    setProductForm,
    setQuery,
    setSelectedProductIds,
    subCategories,
    submitProduct,
    toggleVariantSpecField,
    uploadFiles,
    activeVariantFields,
    variantFields,
    isSuperAdmin,
  } = props;
  return (
<AdminPanel
  title="Quản lý sản phẩm, media và biến thể"
  action={
    <div className="flex flex-wrap items-center gap-2">
      <button type="button" onClick={exportProducts} className="inline-flex h-10 items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 text-sm font-bold text-slate-700 transition hover:bg-slate-50"><Download className="h-4 w-4" />Xuất</button>
      <label className="inline-flex h-10 cursor-pointer items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 text-sm font-bold text-slate-700 transition hover:bg-slate-50">
        <Upload className="h-4 w-4" />Import
        <input type="file" accept=".csv,text/csv" className="hidden" onChange={(event) => importProducts(event.target.files)} />
      </label>
    </div>
  }
  filters={
    <>
      <Select noLabel={true} label="Danh mục" value={productCategoryFilter} onChange={setProductCategoryFilter} options={[['', 'Tất cả danh mục'], ...categories.map((c: any) => [String(c.id), c.parentName ? `${c.parentName} / ${c.name}` : c.name] as [string, string])]} />
      <Select noLabel={true} label="Thương hiệu" value={productBrandFilter} onChange={setProductBrandFilter} options={productBrandOptions || []} />
      <Select noLabel={true} label="Trạng thái" value={productStatusFilter} onChange={setProductStatusFilter} options={[['', 'Tất cả trạng thái'], ...productStatusOptions]} />
      <SearchBox value={query} onChange={setQuery} placeholder="Tìm sản phẩm, SKU, thương hiệu" />
    </>
  }
>
                <CollapsibleSection title={editingProductId ? 'Đang chỉnh sửa sản phẩm' : 'Thêm sản phẩm mới'} description="Mở popup khi cần nhập sản phẩm, media, thông số và biến thể. Bảng sản phẩm bên dưới vẫn luôn sẵn sàng để tìm kiếm." defaultOpen={false} forceOpen={Boolean(editingProductId)} forceOpenKey={editingProductId} closeSignal={productCloseSignal} onClose={resetProductForm}>
                  <form onSubmit={handleProductSubmit} className="mb-5 grid gap-3 rounded-lg bg-slate-50 p-4 md:grid-cols-4">
                    <Input label="Tên sản phẩm" value={productForm.name} required onChange={(value) => setProductForm({ ...productForm, name: value })} />
                    <Input label="Giá gốc chung" type="number" value={productForm.price} onChange={(value) => setProductForm({ ...productForm, price: Number(value) })} />
                    <Input label="Giá bán chung" type="number" value={productForm.discountPrice} onChange={(value) => setProductForm({ ...productForm, discountPrice: Number(value) })} />
                    <Select label="Danh mục cha" value={productForm.categoryId} onChange={(value) => {
                      const category = rootCategories.find((item) => item.id === value);
                      const nextWarranty = productForm.warrantyPolicy.inheritWarrantyPolicy ? categoryWarrantyPolicy(category) : productForm.warrantyPolicy;
                      setProductForm({ ...productForm, categoryId: value, category: (category?.code || category?.slug || productForm.category).toUpperCase(), warrantyPolicy: nextWarranty, specifications: {}, variantSpecKeys: [], variants: productForm.variants.map((variant) => ({ ...variant, specs: {} })) });
                    }} options={[['', 'Chưa chọn'], ...rootCategories.map((item) => [item.id, item.name] as [string, string])]} />
                    <Select label="Danh mục con" value={productForm.subcategoryId} onChange={(value) => {
                      const child = subCategories.find((item) => item.id === value);
                      const parent = rootCategories.find((item) => item.id === (child?.parentId || productForm.categoryId));
                      const nextWarranty = productForm.warrantyPolicy.inheritWarrantyPolicy ? categoryWarrantyPolicy(child || parent, parent) : productForm.warrantyPolicy;
                      setProductForm({ ...productForm, subcategoryId: value, warrantyPolicy: nextWarranty });
                    }} options={[['', 'Chưa chọn'], ...subCategories.map((item) => [item.id, `${item.parentName || 'Khác'} / ${item.name}`] as [string, string])]} />
                    <Select label="Thương hiệu" value={productForm.brandId} onChange={(value) => {
                      const brand = brands.find((item) => item.id === value);
                      setProductForm({ ...productForm, brandId: value, brand: brand?.name || productForm.brand });
                    }} options={[['', 'Nhập tay'], ...brands.map((item) => [item.id, item.name] as [string, string])]} />
                    <Select label="Trạng thái" value={productForm.status} onChange={(value) => setProductForm({ ...productForm, status: value })} options={productStatusOptions} />
                    <Input label="Thương hiệu nhập tay" value={productForm.brand} onChange={(value) => setProductForm({ ...productForm, brand: value })} />
                    <FileInput label="Ảnh đại diện chung" accept="image/*" onFiles={async (files) => setProductForm({ ...productForm, imageUrl: (await uploadFiles(files, 'products'))[0] || productForm.imageUrl })} />
                    <FileInput label="Bộ ảnh sản phẩm chung" accept="image/*" multiple onFiles={async (files) => {
                      const urls = await uploadFiles(files, 'products');
                      setProductForm({ ...productForm, images: [...(productForm.images || []), ...urls].slice(0, 20) });
                    }} />
                    <FileInput label="Video sản phẩm dùng chung" accept="video/*" onFiles={async (files) => setProductForm({ ...productForm, videoUrl: (await uploadFiles(files, 'products'))[0] || productForm.videoUrl })} />
                    <MediaPreview title="Ảnh đại diện chung" items={productForm.imageUrl ? [productForm.imageUrl] : []} onRemove={() => setProductForm({ ...productForm, imageUrl: '' })} />
                    <MediaPreview title="Bộ ảnh sản phẩm chung" items={productForm.images || []} onRemove={(url) => setProductForm({ ...productForm, images: (productForm.images || []).filter((item: string) => item !== url) })} />
                    {productForm.videoUrl && <VideoPreview title="Video sản phẩm dùng chung" url={productForm.videoUrl} onRemove={() => setProductForm({ ...productForm, videoUrl: '' })} />}
                    <div className="rounded-md border border-slate-200 bg-white p-3 md:col-span-4">
                      <div className="mb-3 text-sm font-bold text-slate-700">Bảo hành sản phẩm</div>
                      <div className="grid gap-3 md:grid-cols-5">
                        <Checkbox label="Theo danh mục" checked={productForm.warrantyPolicy.inheritWarrantyPolicy} onChange={(checked) => {
                          const parent = rootCategories.find((item) => item.id === productForm.categoryId);
                          const child = subCategories.find((item) => item.id === productForm.subcategoryId);
                          setProductForm({ ...productForm, warrantyPolicy: checked ? categoryWarrantyPolicy(child || parent, parent) : { ...productForm.warrantyPolicy, inheritWarrantyPolicy: false } });
                        }} />
                        <Checkbox label="Có bảo hành" checked={productForm.warrantyPolicy.hasWarranty} disabled={productForm.warrantyPolicy.inheritWarrantyPolicy} onChange={(checked) => setProductForm({ ...productForm, warrantyPolicy: { ...productForm.warrantyPolicy, hasWarranty: checked, inheritWarrantyPolicy: false } })} />
                        <Input label="Tháng bảo hành" type="number" disabled={productForm.warrantyPolicy.inheritWarrantyPolicy} value={productForm.warrantyPolicy.warrantyMonths} onChange={(value) => setProductForm({ ...productForm, warrantyPolicy: { ...productForm.warrantyPolicy, warrantyMonths: Math.max(0, Number(value)), inheritWarrantyPolicy: false } })} />
                        <Checkbox label="Có 1 đổi 1" checked={productForm.warrantyPolicy.allowOneForOne} disabled={productForm.warrantyPolicy.inheritWarrantyPolicy} onChange={(checked) => setProductForm({ ...productForm, warrantyPolicy: { ...productForm.warrantyPolicy, allowOneForOne: checked, inheritWarrantyPolicy: false } })} />
                        <Input label="Ngày 1 đổi 1" type="number" disabled={productForm.warrantyPolicy.inheritWarrantyPolicy} value={productForm.warrantyPolicy.oneForOneDays} onChange={(value) => setProductForm({ ...productForm, warrantyPolicy: { ...productForm.warrantyPolicy, oneForOneDays: Math.max(0, Number(value)), inheritWarrantyPolicy: false } })} />
                      </div>
                    </div>

                    {productSpecFields.length > 0 && (
                      <div className="rounded-md border border-slate-200 bg-white p-3 md:col-span-4">
                        <div className="mb-3">
                          <div className="text-sm font-bold text-slate-700">Thông số kỹ thuật theo danh mục</div>
                          <p className="mt-1 text-xs font-medium text-slate-500">Các trường này lấy từ form thông số của danh mục cha và áp dụng cho sản phẩm.</p>
                        </div>
                        <div className="space-y-4">
                          {groupedProductSpecFields.map((group) => (
                            <div key={group.title}>
                              <div className="mb-2 text-xs font-bold uppercase text-slate-500">{group.title}</div>
                              <div className="grid gap-3 md:grid-cols-3">
                                {group.fields.map((field) => <Input key={field.key} label={field.label || field.key} value={productForm.specifications[field.key] || ''} required={field.required} onChange={(value) => setProductForm({ ...productForm, specifications: { ...productForm.specifications, [field.key]: value } })} />)}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    <textarea className="min-h-20 rounded-md border border-slate-200 px-3 py-2 text-sm outline-none focus:border-red-500 md:col-span-4" placeholder="Mô tả ngắn" value={productForm.description} onChange={(event) => setProductForm({ ...productForm, description: event.target.value })} />

                    <div className="rounded-md border border-slate-200 bg-white p-3 md:col-span-4">
                      <div className="mb-3 text-sm font-bold text-slate-700">Sản phẩm bán kèm và dịch vụ đi kèm</div>
                      <div className="grid gap-3">
                        <div className="rounded-md border border-slate-200 bg-white p-3">
                          <div className="text-sm font-bold text-slate-800">Sản phẩm mua kèm giảm giá</div>
                          <div className="mt-1 text-xs font-medium text-slate-500">Chọn từ danh sách sản phẩm sau khi lọc. Giảm giá chỉ áp dụng trong số lượng admin đã cấu hình.</div>
                          <div className="mt-3 grid gap-3 md:grid-cols-3">
                            <Select label="Danh mục" value={accessoryCategoryFilter} onChange={setAccessoryCategoryFilter} options={[['', 'Tất cả'], ...categories.map((item) => [item.id, item.parentName ? `${item.parentName} / ${item.name}` : item.name] as [string, string])]} />
                            <Select label="Thương hiệu" value={accessoryBrandFilter} onChange={setAccessoryBrandFilter} options={[['', 'Tất cả'], ...brands.map((item) => [item.id, item.name] as [string, string])]} />
                            <Input label="Tìm sản phẩm" value={accessorySearch} onChange={setAccessorySearch} />
                          </div>
                          <div className="mt-2 rounded-md border border-slate-200">
                            {(accessoryCategoryFilter || accessoryBrandFilter || accessorySearch.trim()) ? (
                              accessoryProductChoices.length > 0 ? (
                                <>
                                  <button type="button" onClick={() => accessoryProductChoices.forEach((item) => addAccessoryOffer(item))} className="flex w-full items-center justify-between gap-3 border-b border-slate-100 bg-slate-50 px-3 py-2 text-left text-xs font-bold text-slate-700">
                                    Chọn tất cả sản phẩm đang lọc
                                    <Plus className="h-4 w-4" />
                                  </button>
                                  {accessoryProductChoices.map((item) => (
                                    <button
                                      key={item.id}
                                      type="button"
                                      onClick={() => addAccessoryOffer(item)}
                                      className="flex w-full items-center justify-between gap-3 border-b border-slate-100 px-3 py-2 text-left last:border-b-0 hover:bg-slate-50"
                                    >
                                      <div className="min-w-0">
                                        <div className="truncate text-sm font-semibold text-slate-800">{item.name}</div>
                                        <div className="text-xs text-slate-500">{item.sku || compactId(item.id)}</div>
                                      </div>
                                      <span className="text-xs font-bold text-red-600">Chọn</span>
                                    </button>
                                  ))}
                                </>
                              ) : (
                                <div className="px-3 py-4 text-sm font-medium text-slate-500">Không có sản phẩm phù hợp với bộ lọc.</div>
                              )
                            ) : (
                              <div className="px-3 py-4 text-sm font-medium text-slate-500">Chọn danh mục, thương hiệu hoặc nhập tên/SKU để hiện danh sách sản phẩm.</div>
                            )}
                          </div>
                          <div className="mt-3 space-y-3">
                            {productForm.accessoryOffers.length === 0 && <div className="rounded-md bg-slate-50 p-3 text-sm text-slate-500">Chưa có sản phẩm mua kèm giảm giá.</div>}
                            {productForm.accessoryOffers.map((item) => (
                              <div key={item.productId} className="rounded-md border border-slate-200 bg-slate-50 p-3">
                                <div className="flex items-start justify-between gap-3">
                                  <div className="flex items-center gap-3">
                                    {item.imageUrl ? <img src={item.imageUrl} alt="" className="h-12 w-12 rounded-md border border-slate-200 object-contain" /> : <div className="flex h-12 w-12 items-center justify-center rounded-md border border-slate-200 bg-white"><Image className="h-4 w-4 text-slate-300" /></div>}
                                    <div>
                                      <div className="text-sm font-bold text-slate-800">{item.productName || 'Sản phẩm mua kèm'}</div>
                                      <div className="text-xs text-slate-500">{item.productSku || compactId(item.productId)}</div>
                                    </div>
                                  </div>
                                  <button type="button" onClick={() => removeAccessoryOffer(item.productId)} className="text-red-600"><Trash2 className="h-4 w-4" /></button>
                                </div>
                                <div className="mt-3 grid gap-3 md:grid-cols-3">
                                  <Select label="Kiểu giảm" value={item.discountType} onChange={(value) => patchAccessoryOffer(item.productId, { discountType: value as 'FIXED' | 'PERCENT' })} options={[['PERCENT', 'Theo %'], ['FIXED', 'Theo tiền']]} />
                                  <Input label={item.discountType === 'PERCENT' ? 'Giảm giá (%)' : 'Giảm giá (VND)'} type="number" value={item.discountValue} onChange={(value) => patchAccessoryOffer(item.productId, { discountValue: Number(value) })} />
                                  <Input label="Số lượng được giảm" type="number" value={item.maxQuantity} onChange={(value) => patchAccessoryOffer(item.productId, { maxQuantity: Math.max(1, Number(value) || 1) })} />
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                        <div className="rounded-md border border-slate-200 bg-white p-3 md:col-span-3">
                          <div className="text-sm font-bold text-slate-800">Dịch vụ đi kèm</div>
                          <div className="mt-1 text-xs font-medium text-slate-500">Chọn từ danh sách dịch vụ admin đã tạo. Với cùng một nhóm bảo hành, hệ thống chỉ cho chọn một thời hạn.</div>
                          <div className="mt-3 grid gap-3 md:grid-cols-3">
                            <Select label="Loại dịch vụ" value={attachedServiceTypeFilter} onChange={setAttachedServiceTypeFilter} options={[['', 'Tất cả'], ['PRODUCT_SERVICE', 'Dịch vụ sản phẩm'], ['SUPPORT_SERVICE', 'Dịch vụ hỗ trợ']]} />
                            <Select label="Nhóm dịch vụ" value={attachedServiceGroupFilter} onChange={setAttachedServiceGroupFilter} options={[['', 'Tất cả'], ...serviceGroupOptions.map((item) => [item, item] as [string, string])]} />
                            <Input label="Tìm dịch vụ" value={attachedServiceSearch} onChange={setAttachedServiceSearch} />
                          </div>
                          <div className="mt-3 rounded-md border border-slate-200">
                            {productAttachedServiceChoices.length === 0 ? (
                              <div className="px-3 py-4 text-sm font-medium text-slate-500">Không có dịch vụ phù hợp hoặc tất cả dịch vụ trong bộ lọc đã được chọn.</div>
                            ) : productAttachedServiceChoices.map((service) => (
                              <button key={service.id} type="button" onClick={() => addAttachedService(service)} className="flex w-full items-center justify-between gap-3 border-b border-slate-100 px-3 py-2 text-left last:border-b-0 hover:bg-slate-50">
                                <div className="min-w-0">
                                  <div className="truncate text-sm font-semibold text-slate-800">{service.name} <span className="text-xs text-slate-400">({service.code})</span></div>
                                  <div className="text-xs text-slate-500">
                                    {service.serviceType === 'PRODUCT_SERVICE' ? 'Dịch vụ sản phẩm' : 'Dịch vụ hỗ trợ'}
                                    {service.attributeGroup ? ` · Nhóm ${service.attributeGroup}` : ''}
                                    {service.durationMonths ? ` · ${service.durationMonths} tháng` : ''}
                                    {service.priceMode === 'PERCENT' ? ` · ${service.percentValue || 0}%` : service.priceMode === 'TIERED_AMOUNT' ? ' · Theo biểu phí' : ` · ${currency.format(Number(service.fixedPrice || service.baseAmount || 0))}`}
                                  </div>
                                </div>
                                <Plus className="h-4 w-4 shrink-0 text-red-600" />
                              </button>
                            ))}
                          </div>
                          <div className="mt-3 space-y-2">
                            {productForm.attachedServices.length === 0 && <div className="rounded-md bg-slate-50 p-3 text-sm text-slate-500">Chưa chọn dịch vụ đi kèm.</div>}
                            {productForm.attachedServices.map((item) => (
                              <div key={item.serviceId} className="grid gap-3 rounded-md border border-slate-200 bg-slate-50 p-3 md:grid-cols-[1fr_40px]">
                                <div>
                                  <div className="text-sm font-bold text-slate-800">{item.name || item.code || 'Dịch vụ'}</div>
                                  <div className="text-xs text-slate-500">
                                    {item.serviceType === 'PRODUCT_SERVICE' ? 'Dịch vụ sản phẩm' : 'Dịch vụ hỗ trợ'}
                                    {item.attributeGroup ? ` · Nhóm ${item.attributeGroup}` : ''}
                                    {item.durationMonths ? ` · ${item.durationMonths} tháng` : ''}
                                    {item.priceMode === 'PERCENT' ? ` · ${item.percentValue || 0}%` : item.priceMode === 'TIERED_AMOUNT' ? ' · Theo biểu phí chính sách' : ` · ${currency.format(Number(item.fixedPrice || 0))}`}
                                  </div>
                                </div>
                                <button type="button" onClick={() => removeAttachedService(item.serviceId)} className="text-red-600"><Trash2 className="h-4 w-4" /></button>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>

                    <div className="rounded-md border border-slate-200 bg-white p-3 md:col-span-4">
                      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                        <div>
                          <div className="text-sm font-bold text-slate-700">Thuộc tính tạo biến thể</div>
                          <p className="mt-1 text-xs font-medium text-slate-500">Màu sắc nhập ở từng dòng biến thể. Các thuộc tính còn lại được chọn từ thông số kỹ thuật của danh mục.</p>
                        </div>
                        <button type="button" onClick={addVariant} className="inline-flex h-9 items-center gap-2 rounded-md border border-red-200 bg-red-100 px-3 text-sm font-bold text-red-800 transition hover:bg-red-200"><Plus className="h-4 w-4" /> Thêm biến thể</button>
                      </div>
                      <div className="grid gap-3 md:grid-cols-3">
                        <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
                          <div className="text-xs font-bold uppercase text-slate-500">Mặc định</div>
                          <div className="mt-1 text-sm font-semibold text-slate-800">Màu sắc</div>
                        </div>
                        {variantFields.map((field: any) => (
                          <label key={field.key} className="flex items-center gap-3 rounded-md border border-slate-200 bg-white p-3 text-sm font-semibold text-slate-700">
                            <input
                              type="checkbox"
                              checked={productForm.variantSpecKeys.includes(field.key)}
                              onChange={(event) => toggleVariantSpecField(field.key, event.target.checked)}
                              className="h-4 w-4 rounded border-slate-300 text-red-600 focus:ring-red-500"
                            />
                            {field.label || field.key}
                          </label>
                        ))}
                        {variantFields.length === 0 && (
                          <div className="rounded-md bg-slate-50 p-3 text-sm text-slate-500 md:col-span-2">Danh mục hiện chưa có thông số kỹ thuật nào được đánh dấu làm biến thể.</div>
                        )}
                      </div>
                    </div>

                    <div className="rounded-md border border-slate-200 bg-white p-3 md:col-span-4">
                      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                        <div>
                          <div className="text-sm font-bold text-slate-700">Bảng biến thể (Flat Variants)</div>
                          <p className="mt-1 text-xs font-medium text-slate-500">Mỗi tổ hợp thuộc tính là một dòng độc lập chứa SKU, giá, tồn kho và ảnh đại diện riêng.</p>
                        </div>
                        <div className="flex flex-wrap items-center gap-2">
                          <button
                            type="button"
                            onClick={() => {
                              const price = window.prompt("Nhập giá gốc chung áp dụng cho tất cả biến thể:");
                              if (price !== null && !isNaN(Number(price))) {
                                setProductForm({
                                  ...productForm,
                                  variants: productForm.variants.map((v: any) => ({ ...v, price: Number(price) }))
                                });
                              }
                            }}
                            className="inline-flex h-9 items-center gap-1.5 rounded-md border border-slate-200 bg-white px-3 text-xs font-bold text-slate-700 hover:bg-slate-50"
                          >
                            Áp dụng giá gốc
                          </button>
                          <button
                            type="button"
                            onClick={() => {
                              const salePrice = window.prompt("Nhập giá bán chung áp dụng cho tất cả biến thể:");
                              if (salePrice !== null && !isNaN(Number(salePrice))) {
                                setProductForm({
                                  ...productForm,
                                  variants: productForm.variants.map((v: any) => ({ ...v, salePrice: Number(salePrice) }))
                                });
                              }
                            }}
                            className="inline-flex h-9 items-center gap-1.5 rounded-md border border-slate-200 bg-white px-3 text-xs font-bold text-slate-700 hover:bg-slate-50"
                          >
                            Áp dụng giá bán
                          </button>
                          <button
                            type="button"
                            onClick={() => {
                              const stock = window.prompt("Nhập tồn kho chung áp dụng cho tất cả biến thể:");
                              if (stock !== null && !isNaN(Number(stock))) {
                                setProductForm({
                                  ...productForm,
                                  variants: productForm.variants.map((v: any) => ({ ...v, stockQuantity: Math.max(0, Number(stock)) }))
                                });
                              }
                            }}
                            className="inline-flex h-9 items-center gap-1.5 rounded-md border border-slate-200 bg-white px-3 text-xs font-bold text-slate-700 hover:bg-slate-50"
                          >
                            Áp dụng tồn kho
                          </button>
                        </div>
                      </div>

                      <div className="overflow-x-auto rounded-md border border-slate-200">
                        <table className="min-w-full divide-y divide-slate-200 bg-white text-left text-xs font-medium text-slate-700">
                          <thead className="bg-slate-50 text-slate-500 uppercase tracking-wider font-bold">
                            <tr>
                              <th className="px-4 py-3">Biến thể / Thuộc tính</th>
                              <th className="px-4 py-3">SKU</th>
                              <th className="px-4 py-3">Giá gốc (VND)</th>
                              <th className="px-4 py-3">Giá bán (VND)</th>
                              <th className="px-4 py-3">Tồn kho</th>
                              <th className="px-4 py-3 text-center">Mặc định</th>
                              <th className="px-4 py-3 text-center">Bật bán</th>
                              <th className="px-4 py-3">Thao tác</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-200">
                            {productForm.variants.map((variant: any, index: number) => {
                              const attrLabel = Object.entries(variant.attributes || {})
                                .map(([k, v]) => `${k}: ${v}`)
                                .join(' / ') || 'Mặc định';
                              const attrParts = [
                                variant.colorName ? `Màu sắc: ${variant.colorName}` : '',
                                ...activeVariantFields.map((field: any) => variant.specs?.[field.key] ? `${field.label || field.key}: ${variant.specs[field.key]}` : '')
                              ].filter(Boolean);
                              const displayedAttrLabel = attrParts.join(' / ') || attrLabel;
                              return (
                                <tr key={index} className="hover:bg-slate-50">
                                  <td className="px-4 py-3">
                                    <div className="font-semibold text-slate-900">{displayedAttrLabel}</div>
                                    <div className="mt-2 grid min-w-[220px] gap-2">
                                      <input
                                        type="text"
                                        value={variant.colorName || ''}
                                        onChange={(e) => patchVariant(index, { colorName: e.target.value })}
                                        className="w-full rounded border border-slate-200 px-2 py-1 outline-none focus:border-red-500"
                                        placeholder="Màu sắc"
                                      />
                                      {activeVariantFields.map((field: any) => (
                                        <input
                                          key={field.key}
                                          type="text"
                                          value={variant.specs?.[field.key] || ''}
                                          onChange={(e) => patchVariant(index, { specs: { ...(variant.specs || {}), [field.key]: e.target.value } })}
                                          className="w-full rounded border border-slate-200 px-2 py-1 outline-none focus:border-red-500"
                                          placeholder={field.label || field.key}
                                        />
                                      ))}
                                    </div>
                                    <div className="mt-1 flex items-center gap-2">
                                      {variant.imageUrl ? (
                                        <img src={variant.imageUrl} alt="" className="h-8 w-8 rounded-md border border-slate-200 object-contain" />
                                      ) : (
                                        <div className="flex h-8 w-8 items-center justify-center rounded-md border border-slate-200 bg-slate-50">
                                          <Image className="h-3 w-3 text-slate-300" />
                                        </div>
                                      )}
                                      <FileInput
                                        label="Ảnh đại diện biến thể"
                                        accept="image/*"
                                        onFiles={async (files) => {
                                          const urls = await uploadFiles(files, 'products');
                                          if (urls[0]) patchVariant(index, { imageUrl: urls[0] });
                                        }}
                                      />
                                    </div>
                                    <div className="mt-2">
                                      <FileInput
                                        label="Bộ ảnh biến thể"
                                        accept="image/*"
                                        multiple
                                        onFiles={async (files) => {
                                          const urls = await uploadFiles(files, 'products');
                                          patchVariant(index, { images: [...(variant.images || []), ...urls].slice(0, 20) });
                                        }}
                                      />
                                      {variant.images?.length > 0 && (
                                        <div className="mt-2 flex flex-wrap gap-2">
                                          {variant.images.map((url: string) => (
                                            <button
                                              key={url}
                                              type="button"
                                              onClick={() => patchVariant(index, { images: (variant.images || []).filter((item: string) => item !== url) })}
                                              className="relative h-10 w-10 overflow-hidden rounded-md border border-slate-200 bg-white"
                                              title="Xóa ảnh khỏi bộ ảnh biến thể"
                                            >
                                              <img src={url} alt="" className="h-full w-full object-contain" />
                                            </button>
                                          ))}
                                        </div>
                                      )}
                                    </div>
                                  </td>
                                  <td className="px-4 py-3">
                                    <input
                                      type="text"
                                      value={variant.sku || ''}
                                      onChange={(e) => patchVariant(index, { sku: e.target.value })}
                                      className="w-full rounded border border-slate-200 px-2 py-1 outline-none focus:border-red-500"
                                      placeholder="AUTO-SKU"
                                    />
                                  </td>
                                  <td className="px-4 py-3">
                                    <input
                                      type="number"
                                      value={variant.price}
                                      onChange={(e) => patchVariant(index, { price: Number(e.target.value) })}
                                      className="w-24 rounded border border-slate-200 px-2 py-1 outline-none focus:border-red-500"
                                    />
                                  </td>
                                  <td className="px-4 py-3">
                                    <input
                                      type="number"
                                      value={variant.salePrice}
                                      onChange={(e) => patchVariant(index, { salePrice: Number(e.target.value) })}
                                      className="w-24 rounded border border-slate-200 px-2 py-1 outline-none focus:border-red-500"
                                    />
                                  </td>
                                  <td className="px-4 py-3">
                                    <input
                                      type="number"
                                      value={variant.stockQuantity || 0}
                                      onChange={(e) => patchVariant(index, { stockQuantity: Number(e.target.value) })}
                                      className="w-16 rounded border border-slate-200 px-2 py-1 outline-none focus:border-red-500"
                                    />
                                  </td>
                                  <td className="px-4 py-3 text-center">
                                    <input
                                      type="radio"
                                      name="defaultVariant"
                                      checked={Boolean(variant.isDefault)}
                                      onChange={() => {
                                        setProductForm({
                                          ...productForm,
                                          variants: productForm.variants.map((v: any, i: number) => ({
                                            ...v,
                                            isDefault: i === index
                                          }))
                                        });
                                      }}
                                      className="h-4 w-4 accent-red-600 cursor-pointer"
                                    />
                                  </td>
                                  <td className="px-4 py-3 text-center">
                                    <input
                                      type="checkbox"
                                      checked={Boolean(variant.isActive)}
                                      onChange={(e) => patchVariant(index, { isActive: e.target.checked })}
                                      className="h-4 w-4 accent-red-600 cursor-pointer"
                                    />
                                  </td>
                                  <td className="px-4 py-3">
                                    <button
                                      type="button"
                                      disabled={productForm.variants.length <= 1}
                                      onClick={() => {
                                        if (variant.id) {
                                          confirmDelete(
                                            `biến thể ${attrLabel}`,
                                            () => apiDb.adminDeleteProductVariant(editingProductId || '', variant.id)
                                          ).then(() => {
                                            setProductForm({
                                              ...productForm,
                                              variants: productForm.variants.filter((_: any, i: number) => i !== index)
                                            });
                                          });
                                        } else {
                                          setProductForm({
                                            ...productForm,
                                            variants: productForm.variants.filter((_: any, i: number) => i !== index)
                                          });
                                        }
                                      }}
                                      className="text-red-600 hover:text-red-800 disabled:opacity-50"
                                    >
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

                    <SubmitButtons editing={Boolean(editingProductId)} onCancel={resetProductForm} />
                  </form>
                </CollapsibleSection>

                {selectedProductIds.length > 0 && (
                  <div className="mb-3 flex flex-wrap items-center justify-between gap-2 rounded-md border border-sky-100 bg-sky-50 px-3 py-2 text-sm font-semibold text-sky-800">
                    <span>Đã chọn {selectedProductIds.length} sản phẩm</span>
                    <button type="button" onClick={bulkApproveProducts} className="inline-flex h-9 items-center gap-2 rounded-md bg-sky-700 px-3 text-xs font-bold text-white"><CheckCircle2 className="h-4 w-4" />Duyệt hàng loạt</button>
                  </div>
                )}

                <AdminTable 
                  headers={['Chọn', 'Ảnh', 'Sản phẩm', 'Danh mục', 'Thương hiệu', 'Giá', 'Kho', 'Biến thể', 'Trạng thái', 'Thao tác']}
                  currentPage={productPage}
                  totalPages={Math.max(1, productTotalPages || 1)}
                  onPageChange={setProductPage}
                  totalCount={productTotal || filteredProducts.length}
                  itemName="sản phẩm"
                >
                  {filteredProducts.map((product) => (
                    <tr key={product.id}>
                      <td className="px-4 py-3"><input type="checkbox" checked={selectedProductIds.includes(product.id)} onChange={(event) => setSelectedProductIds((ids) => event.target.checked ? [...new Set([...ids, product.id])] : ids.filter((id) => id !== product.id))} className="h-4 w-4 rounded border-slate-300 text-red-600 focus:ring-red-500" /></td>
                      <td className="px-4 py-3">{product.imageUrl ? <img src={product.imageUrl} alt="" className="h-11 w-11 rounded-md object-contain" /> : <Image className="h-6 w-6 text-slate-300" />}</td>
                      <td className="px-4 py-3"><div className="font-semibold text-slate-900">{product.name}</div><div className="text-xs text-slate-500">{product.sku || compactId(product.id)}</div></td>
                      <td className="px-4 py-3">{product.categoryName || product.category || '-'}</td>
                      <td className="px-4 py-3">{product.brand || '-'}</td>
                      <td className="px-4 py-3 font-semibold text-red-600">{currency.format(Number(product.discountPrice || product.price || 0))}</td>
                      <td className="px-4 py-3">
                        <div className="font-semibold">{product.stock ?? 0}</div>
                        <AdminBadge tone={Number(product.stock || 0) > 0 ? 'green' : 'yellow'}>{Number(product.stock || 0) > 0 ? 'Còn hàng' : 'Hết hàng'}</AdminBadge>
                      </td>
                      <td className="px-4 py-3">{product.variants?.length || 0}</td>
                      <td className="px-4 py-3"><AdminBadge tone={product.status === 'ACTIVE' ? 'green' : product.status === 'PENDING' ? 'blue' : product.status === 'DRAFT' ? 'yellow' : 'slate'}>{productStatusLabel[product.status] || product.status || 'Nháp'}</AdminBadge></td>
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap items-center gap-2">
                          <RowActions onEdit={() => editProduct(product)} onDelete={() => confirmDelete(product.name, () => apiDb.adminDeactivateProduct(product.id))} onRestore={product.status !== 'ACTIVE' && product.status !== 'ARCHIVED' && product.status !== 'REVISION_DRAFT' ? () => reactivateProduct(product) : undefined} />
                          {(product.status === 'DRAFT' || product.status === 'REVISION_DRAFT') && (
                            <>
                              <button type="button" onClick={() => submitProduct(product)} className="rounded-md border border-sky-200 bg-sky-50 px-2.5 py-1.5 text-xs font-bold text-sky-700">Gửi duyệt</button>
                              {isSuperAdmin && (
                                <button type="button" onClick={() => approveProduct(product)} className="rounded-md border border-emerald-200 bg-emerald-50 px-2.5 py-1.5 text-xs font-bold text-emerald-700">Duyệt thẳng</button>
                              )}
                            </>
                          )}
                          {product.status === 'PENDING' && <button type="button" onClick={() => approveProduct(product)} className="rounded-md border border-emerald-200 bg-emerald-50 px-2.5 py-1.5 text-xs font-bold text-emerald-700">Duyệt</button>}
                          {(product.status === 'DRAFT' || product.status === 'REVISION_DRAFT' || product.status === 'INACTIVE') && <button type="button" onClick={() => archiveProduct(product)} className="rounded-md border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-xs font-bold text-slate-700">Lưu trữ</button>}
                        </div>
                      </td>
                    </tr>
                  ))}
                </AdminTable>
              </AdminPanel>
  );
}
