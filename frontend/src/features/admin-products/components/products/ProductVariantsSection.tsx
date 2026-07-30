import React from 'react';
import { Image, Plus, Trash2 } from 'lucide-react';
import { FileInput } from '../../../admin-shell/components/AdminDashboardParts';
import { productApi } from '../../../../services/productApi';

interface ProductVariantsSectionProps {
  productForm: any;
  setProductForm: React.Dispatch<React.SetStateAction<any>>;
  variantFields: any[];
  toggleVariantSpecField: (key: string, checked: boolean) => void;
  addVariant: () => void;
  activeVariantFields: any[];
  patchVariant: (index: number, patch: any) => void;
  uploadFiles: (files: FileList | null, type: string) => Promise<string[]>;
  editingProductId: string | null;
  confirmDelete: (name: string, onDelete: () => Promise<any>) => Promise<any>;
  currency: { format: (value: number) => string };
  compactId: (id: string) => string;
  readOnly?: boolean;
}

function specOptionValue(option: string, unit?: string) {
  const trimmedOption = String(option || '').trim();
  const trimmedUnit = String(unit || '').trim();
  if (!trimmedOption || !trimmedUnit) return trimmedOption;
  const normalizedOption = trimmedOption.toLowerCase();
  const normalizedUnit = trimmedUnit.toLowerCase();
  if (normalizedOption.endsWith(normalizedUnit.replace(/\s+/g, ''))) return trimmedOption;
  const unitParts = normalizedUnit.split('/').map((part) => part.trim()).filter(Boolean);
  if (unitParts.some((part) => normalizedOption.includes(part))) return trimmedOption;
  if (/[a-wyz]/i.test(trimmedOption) && /[a-z]/i.test(trimmedUnit)) return trimmedOption;
  return `${trimmedOption} ${trimmedUnit}`;
}

export default function ProductVariantsSection(props: ProductVariantsSectionProps) {
  const {
    productForm,
    setProductForm,
    variantFields,
    toggleVariantSpecField,
    addVariant,
    activeVariantFields,
    patchVariant,
    uploadFiles,
    editingProductId,
    confirmDelete,
    currency,
    compactId,
    readOnly = false,
  } = props;

  return (
    <>
      {/* Thuộc tính tạo biến thể */}
      <div className="rounded-md border border-slate-200 bg-white p-3 md:col-span-4">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <div>
            <div className="text-sm font-bold text-slate-700">
              Thuộc tính tạo biến thể
            </div>
            <p className="mt-1 text-xs font-medium text-slate-500">
              Màu sắc nhập ở từng dòng biến thể. Các thuộc tính còn lại được chọn từ
              thông số kỹ thuật của danh mục.
            </p>
          </div>
          <button
            type="button"
            onClick={addVariant}
            className={`${readOnly ? 'hidden ' : ''}inline-flex h-9 items-center gap-2 rounded-md border border-red-200 bg-red-100 px-3 text-sm font-bold text-red-800 transition hover:bg-red-200`}
          >
            <Plus className="h-4 w-4" /> Thêm biến thể
          </button>
        </div>
        <div className="grid gap-3 md:grid-cols-3">
          <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
            <div className="text-xs font-bold uppercase text-slate-500">Mặc định</div>
            <div className="mt-1 text-sm font-semibold text-slate-800">Màu sắc</div>
          </div>
          {variantFields.map((field: any) => (
            <label
              key={field.key}
              className="flex items-center gap-3 rounded-md border border-slate-200 bg-white p-3 text-sm font-semibold text-slate-700"
            >
              <input
                type="checkbox"
                checked={productForm.variantSpecKeys.includes(field.key)}
                onChange={(event) =>
                  toggleVariantSpecField(field.key, event.target.checked)
                }
                className="h-4 w-4 rounded border-slate-300 text-red-600 focus:ring-red-500"
              />
              {field.label || field.key}
            </label>
          ))}
          {variantFields.length === 0 && (
            <div className="rounded-md bg-slate-50 p-3 text-sm text-slate-500 md:col-span-2">
              Danh mục hiện chưa có thông số kỹ thuật nào được đánh dấu làm biến thể.
            </div>
          )}
        </div>
      </div>

      {/* Bảng biến thể */}
      <div className="rounded-md border border-slate-200 bg-white p-3 md:col-span-4">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <div>
            <div className="text-sm font-bold text-slate-700">
              Bảng biến thể (Flat Variants)
            </div>
            <p className="mt-1 text-xs font-medium text-slate-500">
              Mỗi tổ hợp thuộc tính là một dòng độc lập chứa SKU, giá và ảnh đại
              diện riêng.
            </p>
          </div>
          <div className={`${readOnly ? 'hidden ' : ''}flex flex-wrap items-center gap-2`}>
            <button
              type="button"
              onClick={() => {
                const price = window.prompt(
                  'Nhập giá gốc chung áp dụng cho tất cả biến thể:'
                );
                if (price !== null && !isNaN(Number(price))) {
                  setProductForm({
                    ...productForm,
                    variants: productForm.variants.map((v: any) => ({
                      ...v,
                      price: Number(price),
                    })),
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
                const salePrice = window.prompt(
                  'Nhập giá bán chung áp dụng cho tất cả biến thể:'
                );
                if (salePrice !== null && !isNaN(Number(salePrice))) {
                  setProductForm({
                    ...productForm,
                    variants: productForm.variants.map((v: any) => ({
                      ...v,
                      salePrice: Number(salePrice),
                    })),
                  });
                }
              }}
              className="inline-flex h-9 items-center gap-1.5 rounded-md border border-slate-200 bg-white px-3 text-xs font-bold text-slate-700 hover:bg-slate-50"
            >
              Áp dụng giá bán
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
                <th className="px-4 py-3 text-center">Mặc định</th>
                <th className="px-4 py-3 text-center">Bật bán</th>
                <th className="px-4 py-3">Thao tác</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {productForm.variants.map((variant: any, index: number) => {
                const variantImageSources = productForm.variants
                  .map((item: any, sourceIndex: number) => ({
                    item,
                    sourceIndex,
                  }))
                  .filter(
                    ({ item, sourceIndex }: any) =>
                      sourceIndex !== index && (item.imageUrl || item.images?.length)
                  );
                const sameColorImageSource = variantImageSources.find(
                  ({ item }: any) =>
                    variant.colorName &&
                    item.colorName &&
                    String(item.colorName).trim().toLowerCase() ===
                      String(variant.colorName).trim().toLowerCase()
                );
                const attrLabel =
                  Object.entries(variant.attributes || {})
                    .map(([k, v]) => `${k}: ${v}`)
                    .join(' / ') || 'Mặc định';
                const attrParts = [
                  variant.colorName ? `Màu sắc: ${variant.colorName}` : '',
                  ...activeVariantFields.map((field: any) =>
                    variant.specs?.[field.key]
                      ? `${field.label || field.key}: ${variant.specs[field.key]}`
                      : ''
                  ),
                ].filter(Boolean);
                const displayedAttrLabel = attrParts.join(' / ') || attrLabel;
                return (
                  <tr key={index} className="hover:bg-slate-50">
                    <td className="px-4 py-3">
                      <div className="font-semibold text-slate-900">
                        {displayedAttrLabel}
                      </div>
                      <div className="mt-2 grid min-w-[220px] gap-2">
                        <input
                          type="text"
                          value={variant.colorName || ''}
                          onChange={(e) =>
                            patchVariant(index, { colorName: e.target.value })
                          }
                          className="w-full rounded border border-slate-200 px-2 py-1 outline-none focus:border-red-500"
                          placeholder="Màu sắc"
                        />
                        {activeVariantFields.map((field: any) => {
                          const optionsList = field.options
                            ? field.options.split(',').map((x: string) => x.trim()).filter(Boolean)
                            : [];
                          const datalistId = `suggestions-${field.key}-${index}`;
                          return (
                            <div key={field.key} className="w-full">
                              <input
                                type={field.type === 'number' && !field.unit ? 'number' : 'text'}
                                list={optionsList.length > 0 ? datalistId : undefined}
                                value={variant.specs?.[field.key] || ''}
                                onChange={(e) =>
                                  patchVariant(index, {
                                    specs: {
                                      ...(variant.specs || {}),
                                      [field.key]: e.target.value,
                                    },
                                  })
                                }
                                className="w-full rounded border border-slate-200 px-2 py-1 text-xs outline-none focus:border-red-500"
                                placeholder={`${field.label || field.key}${field.unit ? ` (${field.unit})` : ''}`}
                              />
                              {optionsList.length > 0 && (
                                <datalist id={datalistId}>
                                  {optionsList.map((opt: string) => (
                                    <option key={opt} value={specOptionValue(opt, field.unit)} />
                                  ))}
                                </datalist>
                              )}
                              {optionsList.length > 0 && (
                                <div className={`${readOnly ? 'hidden ' : ''}mt-1 flex flex-wrap gap-1`}>
                                  {optionsList.map((opt: string) => {
                                    const value = specOptionValue(opt, field.unit);
                                    const selected = String(variant.specs?.[field.key] || '') === value;
                                    return (
                                      <button
                                        key={opt}
                                        type="button"
                                        onClick={() =>
                                          patchVariant(index, {
                                            specs: {
                                              ...(variant.specs || {}),
                                              [field.key]: value,
                                            },
                                          })
                                        }
                                        className={`rounded border px-1.5 py-0.5 text-[10px] font-semibold transition ${
                                          selected
                                            ? 'border-indigo-500 bg-indigo-50 text-indigo-700'
                                            : 'border-slate-200 bg-slate-100 text-slate-600 hover:bg-slate-200'
                                        }`}
                                      >
                                        {value}
                                      </button>
                                    );
                                  })}
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                      <div className="mt-1 flex items-center gap-2">
                        {variant.imageUrl ? (
                          <img
                            src={variant.imageUrl}
                            alt=""
                            className="h-8 w-8 rounded-md border border-slate-200 object-contain"
                          />
                        ) : (
                          <div className="flex h-8 w-8 items-center justify-center rounded-md border border-slate-200 bg-slate-50">
                            <Image className="h-3 w-3 text-slate-300" />
                          </div>
                        )}
                        <FileInput
                          label="Ảnh đại diện biến thể"
                          className={readOnly ? 'hidden' : ''}
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
                          className={readOnly ? 'hidden' : ''}
                          accept="image/*"
                          multiple
                          onFiles={async (files) => {
                            const urls = await uploadFiles(files, 'products');
                            patchVariant(index, {
                              images: [...(variant.images || []), ...urls].slice(
                                0,
                                20
                              ),
                            });
                          }}
                        />
                        <div className={`${readOnly ? 'hidden ' : ''}mt-2 flex flex-wrap items-center gap-2`}>
                          <button
                            type="button"
                            disabled={!sameColorImageSource}
                            onClick={() => {
                              if (!sameColorImageSource) return;
                              patchVariant(index, {
                                imageUrl:
                                  variant.imageUrl ||
                                  sameColorImageSource.item.imageUrl ||
                                  '',
                                images: [...(sameColorImageSource.item.images || [])],
                              });
                            }}
                            className="rounded-md border border-slate-200 px-2 py-1 text-xs font-semibold text-slate-600 hover:border-red-200 hover:text-red-600 disabled:cursor-not-allowed disabled:opacity-40"
                          >
                            Lấy ảnh cùng màu
                          </button>
                          {variantImageSources.length > 0 && (
                            <select
                              value=""
                              onChange={(event) => {
                                const sourceIndex = Number(event.target.value);
                                if (Number.isNaN(sourceIndex)) return;
                                const source = productForm.variants[sourceIndex];
                                if (!source) return;
                                patchVariant(index, {
                                  imageUrl: variant.imageUrl || source.imageUrl || '',
                                  images: [...(source.images || [])],
                                });
                              }}
                              className="max-w-[220px] rounded-md border border-slate-200 px-2 py-1 text-xs font-semibold text-slate-600 outline-none focus:border-red-500"
                            >
                              <option value="">Lấy ảnh từ biến thể khác</option>
                              {variantImageSources.map(
                                ({ item, sourceIndex }: any) => (
                                  <option key={sourceIndex} value={sourceIndex}>
                                    {item.colorName || 'Không màu'}{' '}
                                    {item.ram || item.specs?.ram || ''}{' '}
                                    {item.storage ||
                                      item.specs?.storage ||
                                      item.configuration ||
                                      ''}
                                  </option>
                                )
                              )}
                            </select>
                          )}
                        </div>
                        {variant.images?.length > 0 && (
                          <div className="mt-2 flex flex-wrap gap-2">
                            {variant.images.map((url: string) => (
                              <button
                                key={url}
                                type="button"
                                onClick={() =>
                                  patchVariant(index, {
                                    images: (variant.images || []).filter(
                                      (item: string) => item !== url
                                    ),
                                  })
                                }
                                className={`${readOnly ? 'pointer-events-none ' : ''}relative h-10 w-10 overflow-hidden rounded-md border border-slate-200 bg-white`}
                                title="Xóa ảnh khỏi bộ ảnh biến thể"
                              >
                                <img
                                  src={url}
                                  alt=""
                                  className="h-full w-full object-contain"
                                />
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
                        onChange={(e) =>
                          patchVariant(index, { price: Number(e.target.value) })
                        }
                        className="w-24 rounded border border-slate-200 px-2 py-1 outline-none focus:border-red-500"
                      />
                    </td>
                    <td className="px-4 py-3">
                      <input
                        type="number"
                        value={variant.salePrice}
                        onChange={(e) =>
                          patchVariant(index, {
                            salePrice: Number(e.target.value),
                          })
                        }
                        className="w-24 rounded border border-slate-200 px-2 py-1 outline-none focus:border-red-500"
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
                            variants: productForm.variants.map(
                              (v: any, i: number) => ({
                                ...v,
                                isDefault: i === index,
                              })
                            ),
                          });
                        }}
                        className="h-4 w-4 accent-red-600 cursor-pointer"
                      />
                    </td>
                    <td className="px-4 py-3 text-center">
                      <input
                        type="checkbox"
                        checked={Boolean(variant.isActive)}
                        onChange={(e) =>
                          patchVariant(index, { isActive: e.target.checked })
                        }
                        className="h-4 w-4 accent-red-600 cursor-pointer"
                      />
                    </td>
                    <td className="px-4 py-3">
                      <button
                        type="button"
                        disabled={productForm.variants.length <= 1}
                        onClick={() => {
                          if (variant.id) {
                            confirmDelete(`biến thể ${attrLabel}`, () =>
                              productApi.adminDeleteProductVariant(
                                editingProductId || '',
                                variant.id
                              )
                            ).then(() => {
                              setProductForm({
                                ...productForm,
                                variants: productForm.variants.filter(
                                  (_: any, i: number) => i !== index
                                ),
                              });
                            });
                          } else {
                            setProductForm({
                              ...productForm,
                              variants: productForm.variants.filter(
                                (_: any, i: number) => i !== index
                              ),
                            });
                          }
                        }}
                        className={`${readOnly ? 'hidden ' : ''}text-red-600 hover:text-red-800 disabled:opacity-50`}
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
    </>
  );
}
