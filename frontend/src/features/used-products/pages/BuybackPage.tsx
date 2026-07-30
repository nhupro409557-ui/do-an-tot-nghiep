import { useEffect, useState, useMemo } from 'react';
import { useAuth } from '../../../context/AuthContext';
import { publicApi } from '../../../services/publicApi';
import { usedProductsApi } from '../services/usedProductsApi';
import { Smartphone, CheckCircle, Info, ChevronDown } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';

function SearchableProductSelect({ products, value, onChange }: { products: any[], value: string, onChange: (id: string) => void }) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  
  const selected = products.find(p => p.id === value);
  const filtered = products.filter(p => p.name.toLowerCase().includes(search.toLowerCase()));

  return (
    <div className="relative mt-1">
      <button 
        type="button" 
        onClick={() => setOpen(!open)}
        className="flex h-11 w-full items-center justify-between rounded-md border border-slate-300 bg-white px-3 shadow-sm focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
      >
        <span className={selected ? 'text-slate-900' : 'text-slate-500'}>
          {selected ? selected.name : 'Tìm hoặc chọn dòng máy...'}
        </span>
        <ChevronDown className="h-4 w-4 text-slate-400" />
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute z-20 mt-1 w-full overflow-hidden rounded-md border border-slate-200 bg-white shadow-lg">
            <div className="border-b border-slate-100 p-2">
              <input 
                autoFocus
                type="text" 
                placeholder="Nhập tên máy..." 
                value={search}
                onChange={e => setSearch(e.target.value)}
                className="h-9 w-full rounded-md border border-slate-200 px-3 text-sm focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
              />
            </div>
            <ul className="max-h-60 overflow-y-auto p-1">
              {filtered.length === 0 ? (
                <li className="p-3 text-center text-sm text-slate-500">Không tìm thấy sản phẩm.</li>
              ) : (
                filtered.map(p => (
                  <li 
                    key={p.id}
                    onClick={() => { onChange(p.id); setOpen(false); setSearch(''); }}
                    className={`cursor-pointer rounded-md px-3 py-2 text-sm hover:bg-emerald-50 hover:text-emerald-700 ${value === p.id ? 'bg-emerald-50 font-medium text-emerald-700' : 'text-slate-700'}`}
                  >
                    {p.name}
                  </li>
                ))
              )}
            </ul>
          </div>
        </>
      )}
    </div>
  );
}

export default function BuybackPage() {
  const { user, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  
  const [loadingProducts, setLoadingProducts] = useState(true);
  const [products, setProducts] = useState<any[]>([]);
  
  const [busy, setBusy] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');
  
  const [draft, setDraft] = useState({
    productId: '',
    variantId: '',
    imei: '',
    expectedPrice: '',
    note: '',
  });

  useEffect(() => {
    let active = true;
    publicApi.listProducts({ limit: 100 })
      .then((res: any) => {
        if (active) setProducts(res.items.map((i: any) => i.product));
      })
      .catch(() => {})
      .finally(() => {
        if (active) setLoadingProducts(false);
      });
    return () => { active = false; };
  }, []);

  const selectedProduct = useMemo(() => {
    return products.find(p => p.id === draft.productId);
  }, [products, draft.productId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user) {
      navigate('/login?redirect=/thu-cu-doi-moi');
      return;
    }
    setError('');
    setBusy(true);
    try {
      await usedProductsApi.createBuybackRequest({
        productId: draft.productId,
        variantId: draft.variantId || null,
        imei: draft.imei,
        expectedPrice: draft.expectedPrice ? Number(draft.expectedPrice) : null,
        note: draft.note || null,
      });
      setSuccess(true);
    } catch (err: any) {
      setError(err.message || 'Không thể tạo yêu cầu thu cũ.');
    } finally {
      setBusy(false);
    }
  };

  if (authLoading || loadingProducts) {
    return <div className="flex min-h-[60vh] items-center justify-center"><div className="h-8 w-8 animate-spin rounded-full border-4 border-slate-200 border-t-emerald-600"></div></div>;
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-8 text-center">
        <h1 className="text-3xl font-bold tracking-tight text-slate-900">Thu cũ đổi mới</h1>
        <p className="mt-2 text-slate-500">Định giá máy cũ nhanh chóng, lên đời máy mới dễ dàng.</p>
      </div>

      {success ? (
        <div className="rounded-xl border border-emerald-100 bg-emerald-50 p-8 text-center">
          <CheckCircle className="mx-auto h-16 w-16 text-emerald-500" />
          <h2 className="mt-4 text-xl font-bold text-slate-900">Gửi yêu cầu thành công!</h2>
          <p className="mt-2 text-slate-600">Chúng tôi đã tiếp nhận thông tin thiết bị của bạn. Vui lòng mang máy đến cửa hàng gần nhất hoặc đợi nhân viên liên hệ để hoàn tất quá trình định giá.</p>
          <div className="mt-6 flex justify-center gap-4">
            <Link to="/account/buyback" className="rounded-lg bg-emerald-600 px-6 py-2.5 text-sm font-semibold text-white hover:bg-emerald-700">Theo dõi yêu cầu</Link>
            <button onClick={() => { setSuccess(false); setDraft({ productId: '', variantId: '', imei: '', expectedPrice: '', note: '' }); }} className="rounded-lg border border-slate-300 bg-white px-6 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50">Định giá máy khác</button>
          </div>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          <div className="border-b border-slate-200 bg-slate-50 px-6 py-4">
            <h2 className="font-semibold text-slate-800">Thông tin thiết bị</h2>
          </div>
          <div className="grid gap-6 p-6 sm:grid-cols-2">
            {!user && (
              <div className="col-span-full rounded-md bg-amber-50 p-4 text-sm text-amber-800 flex items-start">
                <Info className="mr-2 h-5 w-5 flex-shrink-0" />
                <p>Bạn cần <Link to="/login?redirect=/thu-cu-doi-moi" className="font-semibold underline">đăng nhập</Link> để có thể gửi yêu cầu và theo dõi tiến độ thu cũ đổi mới.</p>
              </div>
            )}
            
            {error && (
              <div className="col-span-full rounded-md bg-red-50 p-4 text-sm text-red-800">{error}</div>
            )}

            <div className="col-span-full">
              <label className="block text-sm font-medium text-slate-700">Dòng máy <span className="text-red-500">*</span></label>
              <SearchableProductSelect 
                products={products} 
                value={draft.productId} 
                onChange={(id) => setDraft({ ...draft, productId: id, variantId: '' })} 
              />
              <input type="hidden" required value={draft.productId} />
            </div>

            <label className="block text-sm font-medium text-slate-700">Phiên bản / Dung lượng
              <select value={draft.variantId} onChange={e => setDraft({ ...draft, variantId: e.target.value })} className="mt-1 block h-11 w-full rounded-md border border-slate-300 bg-white px-3 shadow-sm focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500 disabled:bg-slate-50 disabled:text-slate-500" disabled={!selectedProduct || !selectedProduct.variants?.length}>
                <option value="">Không xác định</option>
                {(selectedProduct?.variants || []).map((v: any) => (
                  <option key={v.id} value={v.id}>{[v.colorName, v.storage, v.ram].filter(Boolean).join(' - ') || v.sku}</option>
                ))}
              </select>
            </label>

            <label className="block text-sm font-medium text-slate-700">Số IMEI <span className="text-red-500">*</span>
              <input required type="text" pattern="\d{15}" title="IMEI phải gồm 15 chữ số" placeholder="Ví dụ: 351234567890123" value={draft.imei} onChange={e => setDraft({ ...draft, imei: e.target.value.replace(/\D/g, '').slice(0, 15) })} className="mt-1 block h-11 w-full rounded-md border border-slate-300 px-3 shadow-sm focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500 font-mono" />
            </label>

            <label className="block text-sm font-medium text-slate-700">Giá mong muốn (VNĐ)
              <input type="number" min="0" placeholder="Để trống nếu muốn cửa hàng định giá" value={draft.expectedPrice} onChange={e => setDraft({ ...draft, expectedPrice: e.target.value })} className="mt-1 block h-11 w-full rounded-md border border-slate-300 px-3 shadow-sm focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500" />
            </label>

            <label className="block text-sm font-medium text-slate-700">Tình trạng máy / Ghi chú
              <textarea placeholder="Mô tả qua về tình trạng ngoại hình, pin, lỗi (nếu có)..." value={draft.note} onChange={e => setDraft({ ...draft, note: e.target.value })} rows={3} className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 shadow-sm focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500" />
            </label>
          </div>
          
          <div className="bg-slate-50 px-6 py-4 text-right">
            <button type="submit" disabled={busy || !user} className="inline-flex h-11 items-center justify-center gap-2 rounded-lg bg-emerald-600 px-8 text-sm font-bold text-white shadow-sm hover:bg-emerald-700 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2 disabled:opacity-50">
              {busy ? <div className="h-5 w-5 animate-spin rounded-full border-2 border-white border-t-transparent" /> : <Smartphone className="h-5 w-5" />}
              Gửi yêu cầu
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
