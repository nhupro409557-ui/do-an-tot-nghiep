import React, { useEffect, useState } from 'react';
import { CheckCircle2, Info, TriangleAlert, X } from 'lucide-react';
import { ADMIN_NOTICE_EVENT, type AdminNotice } from '../utils/adminNotice';

function noticeTone(type: AdminNotice['type']) {
  if (type === 'error') {
    return {
      border: 'border-red-200',
      icon: <TriangleAlert className="mt-0.5 h-5 w-5 shrink-0 text-red-600" />,
      title: 'Có lỗi xảy ra',
      titleClass: 'text-red-700',
    };
  }
  if (type === 'info') {
    return {
      border: 'border-sky-200',
      icon: <Info className="mt-0.5 h-5 w-5 shrink-0 text-sky-600" />,
      title: 'Thông báo',
      titleClass: 'text-sky-700',
    };
  }
  return {
    border: 'border-emerald-200',
    icon: <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-emerald-600" />,
    title: 'Thành công',
    titleClass: 'text-emerald-700',
  };
}

export function AdminNoticeHost() {
  const [notice, setNotice] = useState<AdminNotice | null>(null);

  useEffect(() => {
    const onNotice = (event: Event) => {
      const detail = (event as CustomEvent<Omit<AdminNotice, 'id'>>).detail;
      if (!detail?.message) return;
      const nextNotice = { ...detail, id: Date.now() };
      setNotice(nextNotice);
      window.setTimeout(() => {
        setNotice((current) => (current?.id === nextNotice.id ? null : current));
      }, 3500);
    };

    window.addEventListener(ADMIN_NOTICE_EVENT, onNotice);
    return () => window.removeEventListener(ADMIN_NOTICE_EVENT, onNotice);
  }, []);

  if (!notice) return null;
  const tone = noticeTone(notice.type);

  return (
    <div className={`fixed right-5 top-5 z-[80] flex w-[min(380px,calc(100vw-40px))] items-start gap-3 rounded-lg border ${tone.border} bg-white px-4 py-3 text-sm font-semibold text-slate-800 shadow-2xl`}>
      {tone.icon}
      <div className="min-w-0 flex-1">
        <div className={`text-sm font-bold ${tone.titleClass}`}>{notice.title || tone.title}</div>
        <div className="mt-0.5 leading-5 text-slate-600">{notice.message}</div>
      </div>
      <button
        type="button"
        onClick={() => setNotice(null)}
        title="Đóng thông báo"
        className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}
