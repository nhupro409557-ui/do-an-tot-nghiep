import { useEffect, useMemo, useState } from 'react';
import { RefreshCw } from 'lucide-react';
import { storeInfoApi, type PublicStorePolicy } from '../../../services/storeInfoApi';


type PolicyTone = 'blue' | 'emerald' | 'fuchsia' | 'indigo' | 'rose' | 'sky';

const TONE_CLASSES: Record<PolicyTone, { border: string; badge: string; icon: string }> = {
  blue: { border: 'border-blue-200 bg-blue-50/50', badge: 'bg-blue-100 text-blue-700', icon: 'text-blue-600' },
  emerald: { border: 'border-emerald-200 bg-emerald-50/50', badge: 'bg-emerald-100 text-emerald-700', icon: 'text-emerald-600' },
  fuchsia: { border: 'border-fuchsia-200 bg-fuchsia-50/50', badge: 'bg-fuchsia-100 text-fuchsia-700', icon: 'text-fuchsia-600' },
  indigo: { border: 'border-indigo-200 bg-indigo-50/50', badge: 'bg-indigo-100 text-indigo-700', icon: 'text-indigo-600' },
  rose: { border: 'border-rose-200 bg-rose-50/50', badge: 'bg-rose-100 text-rose-700', icon: 'text-rose-600' },
  sky: { border: 'border-sky-200 bg-sky-50/50', badge: 'bg-sky-100 text-sky-700', icon: 'text-sky-600' },
};

interface LiveStorePolicySummaryProps {
  codes: string[];
  tone: PolicyTone;
}

export function LiveStorePolicySummary({ codes, tone }: LiveStorePolicySummaryProps) {
  const [policies, setPolicies] = useState<PublicStorePolicy[]>([]);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const codesKey = codes.join('|');
  const requestedCodes = useMemo(() => new Set(codes), [codesKey]);
  const classes = TONE_CLASSES[tone];

  useEffect(() => {
    let active = true;
    setLoading(true);
    setFailed(false);
    storeInfoApi.listPublicStorePolicies()
      .then((items) => {
        if (active) setPolicies(items.filter((item) => requestedCodes.has(item.code)));
      })
      .catch((error) => {
        console.error(error);
        if (active) setFailed(true);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [codesKey, requestedCodes]);

  if (loading) {
    return (
      <div aria-live="polite" className={`mb-6 flex items-center gap-3 rounded-xl border px-4 py-3 text-sm text-slate-600 ${classes.border}`}>
        <RefreshCw className={`h-4 w-4 animate-spin motion-reduce:animate-none ${classes.icon}`} aria-hidden="true" />
        Đang tải thông tin chính sách mới nhất...
      </div>
    );
  }

  if (failed || policies.length === 0) {
    return (
      <div role="status" className="mb-6 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
        Chưa thể tải bản tóm tắt cập nhật. Nội dung chi tiết bên dưới vẫn có thể xem bình thường.
      </div>
    );
  }

  const latestVersion = Math.max(...policies.map((policy) => policy.version));
  return (
    <section aria-labelledby={`live-policy-${codesKey}`} className={`mb-6 rounded-xl border p-5 ${classes.border}`}>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <h2 id={`live-policy-${codesKey}`} className="text-base font-bold text-slate-900">
          Thông tin chính sách cập nhật
        </h2>
        <span className={`rounded-full px-2.5 py-1 text-xs font-bold ${classes.badge}`}>
          Dữ liệu trực tiếp · Phiên bản {latestVersion}
        </span>
      </div>
      <div className="space-y-4">
        {policies.map((policy) => (
          <article key={policy.code}>
            <h3 className="text-sm font-bold text-slate-800">{policy.title}</h3>
            <p className="mt-1 whitespace-pre-line text-sm leading-6 text-slate-700">{policy.content}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
