import React from 'react';
import { AdminBadge, MiniMetric } from '../components/AdminDashboardParts';
import { X, Image } from 'lucide-react';
import { compactId, productStatusLabel } from '../pages/AdminDashboardConfig';

type ProductPreviewModalProps = Record<string, any>;

export default function ProductPreviewModal(props: ProductPreviewModalProps) {
  const {
    currency,
    previewProduct,
    setPreviewProduct,
  } = props;

  if (!previewProduct) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-950/55 px-4 py-6 backdrop-blur-sm">
      <div className="w-full max-w-4xl overflow-hidden rounded-lg bg-white shadow-2xl">
        <div className="flex items-start justify-between gap-4 border-b border-slate-200 px-5 py-4">
          <div>
            <h3 className="text-lg font-bold text-slate-950">Preview sản phẩm</h3>
            <p className="mt-1 text-sm text-slate-500">{previewProduct.status === 'ACTIVE' ? 'Bản đang public' : 'Bản xem trước trước khi public'}</p>
          </div>
          <button type="button" onClick={() => setPreviewProduct(null)} title="Đóng popup" className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-slate-200 text-slate-600 transition hover:bg-slate-50 hover:text-slate-950">
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="grid gap-5 p-5 md:grid-cols-[260px_minmax(0,1fr)]">
          <div className="rounded-md border border-slate-200 bg-slate-50 p-4">
            {previewProduct.imageUrl ? <img src={previewProduct.imageUrl} alt="" className="h-56 w-full object-contain" /> : <Image className="mx-auto h-16 w-16 text-slate-300" />}
            <div className="mt-3 flex flex-wrap gap-2">
              {(previewProduct.images || []).slice(0, 4).map((url: string) => <img key={url} src={url} alt="" className="h-12 w-12 rounded-md border border-slate-200 object-contain" />)}
            </div>
          </div>
          <div className="min-w-0">
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <AdminBadge tone={previewProduct.status === 'ACTIVE' ? 'green' : previewProduct.status === 'PENDING' ? 'blue' : 'yellow'}>{productStatusLabel[previewProduct.status] || previewProduct.status}</AdminBadge>
              <span className="text-xs font-semibold text-slate-500">{previewProduct.sku || compactId(previewProduct.id)}</span>
            </div>
            <h3 className="text-2xl font-black text-slate-950">{previewProduct.name}</h3>
            <div className="mt-2 text-xl font-black text-red-600">{currency.format(Number(previewProduct.discountPrice || previewProduct.price || 0))}</div>
            <p className="mt-4 whitespace-pre-line text-sm leading-6 text-slate-600">{previewProduct.description || 'Chưa có mô tả.'}</p>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <MiniMetric label="SEO title" value={previewProduct.seoMetadata?.title || previewProduct.specifications?._seoTitle || '-'} helper={previewProduct.seoMetadata?.description || previewProduct.specifications?._seoDescription || 'Chưa có meta description'} />
              <MiniMetric
                label="Mua kèm giảm giá"
                value={(previewProduct.salesConfig?.accessoryOffers || []).map((item: any) => item.productName || item.productSku || item.productId).join(', ') || '-'}
                helper="Cấu hình giảm giá và số lượng được giảm theo từng sản phẩm mua kèm"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
