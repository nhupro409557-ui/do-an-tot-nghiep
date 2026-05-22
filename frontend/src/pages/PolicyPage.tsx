import React from 'react';
import DOMPurify from 'dompurify';
import { apiDb } from '../services/apiDb';

export default function PolicyPage() {
  const [policies, setPolicies] = React.useState<any[]>([]);
  const [loading, setLoading] = React.useState(true);
  const sanitizedPolicies = React.useMemo(
    () => policies.map((policy) => ({ ...policy, safeContent: DOMPurify.sanitize(policy.content || '<p>Chưa có nội dung.</p>') })),
    [policies],
  );

  React.useEffect(() => {
    let active = true;
    apiDb.listStorefrontPolicies()
      .then((items) => {
        if (active) setPolicies(items || []);
      })
      .catch(() => {
        if (active) setPolicies([]);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="mx-auto max-w-5xl px-4 py-8 md:px-8 md:py-12">
        <div className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-100 md:p-10">
          <div className="border-b border-slate-100 pb-5">
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-red-600">Chính sách cửa hàng</p>
            <h1 className="mt-2 text-3xl font-black text-slate-950 md:text-4xl">Chính sách & quy định</h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-500">
              Các nội dung dưới đây được đồng bộ trực tiếp từ khu vực quản trị, bao gồm bản đang công khai và đã tới lịch hiển thị.
            </p>
          </div>

          {loading && <div className="py-10 text-sm font-semibold text-slate-500">Đang tải nội dung chính sách...</div>}
          {!loading && sanitizedPolicies.length === 0 && <div className="py-10 text-sm font-semibold text-slate-500">Hiện chưa có chính sách công khai.</div>}

          <div className="mt-8 space-y-8">
            {sanitizedPolicies.map((policy, index) => (
              <section key={policy.id || policy.code} className="rounded-2xl border border-slate-100 bg-slate-50/70 p-5 md:p-7">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-xs font-bold uppercase tracking-[0.18em] text-slate-400">{String(policy.code || `policy-${index + 1}`).replace(/-/g, ' ')}</p>
                    <h2 className="mt-2 text-2xl font-black text-slate-900">{policy.title}</h2>
                    {policy.summary && <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-500">{policy.summary}</p>}
                  </div>
                  <div className="rounded-full bg-white px-3 py-1 text-xs font-bold text-slate-500 ring-1 ring-slate-200">
                    {policy.updatedAt ? `Cập nhật ${new Date(policy.updatedAt).toLocaleDateString('vi-VN')}` : 'Đang áp dụng'}
                  </div>
                </div>
                <div className="prose prose-slate mt-5 max-w-none text-sm leading-7 md:text-base" dangerouslySetInnerHTML={{ __html: policy.safeContent }} />
              </section>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
