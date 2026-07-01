import { useEffect, useReducer } from 'react';
import { Link, useParams } from 'react-router-dom';
import { adminBrandsApi } from '../../admin-brands/services/adminBrandsApi';
import { ProductCard } from '../components/ProductCard';

type BrandLandingState = {
  brand: any | null;
  products: any[];
  pagination: { page: number; limit: number; total: number };
  loading: boolean;
};

const initialBrandLandingState: BrandLandingState = {
  brand: null,
  products: [],
  pagination: { page: 1, limit: 24, total: 0 },
  loading: true,
};

function mergeBrandLandingState(state: BrandLandingState, patch: Partial<BrandLandingState>): BrandLandingState {
  return { ...state, ...patch };
}

export default function BrandLandingPage() {
  const { slug = '' } = useParams();
  const [{ brand, products, pagination, loading }, setPageState] = useReducer(
    mergeBrandLandingState,
    initialBrandLandingState,
  );

  useEffect(() => {
    let mounted = true;
    setPageState({ loading: true });
    adminBrandsApi.getBrandLanding(slug, { page: pagination.page, limit: pagination.limit })
      .then((data) => {
        if (!mounted) return;
        if (data.redirectTo) {
          window.location.replace(`/brands/${data.redirectTo}`);
          return;
        }
        setPageState({
          brand: data.brand,
          products: data.products || [],
          pagination: data.pagination || { page: 1, limit: 24, total: 0 },
        });
      })
      .finally(() => mounted && setPageState({ loading: false }));
    return () => {
      mounted = false;
    };
  }, [slug, pagination.limit, pagination.page]);

  useEffect(() => {
    if (!brand) return;
    const title = brand.landingTitle || `Sản phẩm ${brand.name}`;
    document.title = `${title} | ElectroMart VietNam`;
    let description = document.querySelector('meta[name="description"]');
    if (!description) {
      description = document.createElement('meta');
      description.setAttribute('name', 'description');
      document.head.appendChild(description);
    }
    description.setAttribute('content', `Khám phá sản phẩm chính hãng từ ${brand.name} tại ElectroMart VietNam.`);
  }, [brand]);

  if (loading) {
    return <div className="mx-auto max-w-7xl py-16 text-center text-sm text-slate-500">Đang tải thương hiệu...</div>;
  }

  if (!brand) {
    return (
      <div className="mx-auto max-w-4xl py-16 text-center">
        <h1 className="text-2xl font-bold text-slate-900">Không tìm thấy thương hiệu</h1>
        <Link className="mt-4 inline-flex rounded-md bg-red-600 px-4 py-2 text-sm font-semibold text-white" to="/products">Xem sản phẩm</Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl space-y-8 py-6">
      <section className="grid gap-6 rounded-lg border border-slate-200 bg-white p-6 md:grid-cols-[180px_1fr] md:items-center">
        <div className="flex h-32 w-32 items-center justify-center rounded-lg border border-slate-100 bg-slate-50">
          {brand.logoUrl ? <img className="max-h-24 max-w-24 object-contain" src={brand.logoUrl} alt={brand.logoAltText || `${brand.name} logo`} /> : <span className="text-3xl font-bold text-red-600">{String(brand.name).slice(0, 1)}</span>}
        </div>
        <div>
          <p className="text-sm font-semibold uppercase text-red-600">{brand.code}</p>
          <h1 className="mt-2 text-3xl font-bold text-slate-950">{brand.landingTitle || `Sản phẩm ${brand.name}`}</h1>
          <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-600">{`Danh sách sản phẩm ${brand.name} đang kinh doanh, được cập nhật theo danh mục và tình trạng bán hiện tại.`}</p>
        </div>
      </section>

      <section>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-xl font-bold text-slate-950">Sản phẩm {brand.name}</h2>
          <Link className="text-sm font-semibold text-red-600" to={`/products?brand=${encodeURIComponent(brand.name)}`}>Xem trong bộ lọc</Link>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {products.map((product) => <ProductCard key={product.id} p={product} />)}
        </div>
        {!products.length && <div className="rounded-lg border border-dashed border-slate-200 p-8 text-center text-sm text-slate-500">Chưa có sản phẩm đang hiển thị cho thương hiệu này.</div>}
        {pagination.total > pagination.limit && (
          <div className="mt-6 flex justify-center gap-2">
            <button type="button" disabled={pagination.page <= 1} onClick={() => setPageState({ pagination: { ...pagination, page: Math.max(1, pagination.page - 1) } })} className="rounded-md border border-slate-200 px-4 py-2 text-sm disabled:opacity-40">Trước</button>
            <button type="button" disabled={pagination.page * pagination.limit >= pagination.total} onClick={() => setPageState({ pagination: { ...pagination, page: pagination.page + 1 } })} className="rounded-md border border-slate-200 px-4 py-2 text-sm disabled:opacity-40">Sau</button>
          </div>
        )}
      </section>
    </div>
  );
}
