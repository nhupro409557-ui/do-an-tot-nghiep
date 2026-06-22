import React, { useEffect, useMemo, useState } from 'react';
import { Clock3 } from 'lucide-react';

const getRemainingTime = (endsAt?: string) => {
  const distance = endsAt ? Math.max(new Date(endsAt).getTime() - Date.now(), 0) : 0;
  return {
    days: Math.floor(distance / 86400000),
    hours: Math.floor((distance / 3600000) % 24),
    minutes: Math.floor((distance / 60000) % 60),
    seconds: Math.floor((distance / 1000) % 60),
  };
};

const TimeBox = ({ label, value }: { label: string; value: number }) => (
  <div className="min-w-11 rounded-lg bg-white px-2 py-1 text-center text-primary shadow-sm">
    <div className="text-base font-black leading-5">{String(value).padStart(2, '0')}</div>
    <div className="text-[9px] font-bold uppercase tracking-wide text-slate-500">{label}</div>
  </div>
);

export function FlashSaleCountdown({ endsAt }: { endsAt?: string }) {
  const [remaining, setRemaining] = useState(() => getRemainingTime(endsAt));

  useEffect(() => {
    setRemaining(getRemainingTime(endsAt));
    const timer = window.setInterval(() => setRemaining(getRemainingTime(endsAt)), 1000);
    return () => window.clearInterval(timer);
  }, [endsAt]);

  const endLabel = useMemo(() => {
    if (!endsAt) return '';
    return new Intl.DateTimeFormat('vi-VN', {
      hour: '2-digit',
      minute: '2-digit',
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    }).format(new Date(endsAt));
  }, [endsAt]);

  if (!endsAt) return null;

  return (
    <div className="flex flex-wrap items-center gap-2 rounded-xl bg-black/15 px-3 py-2 text-white">
      <div className="flex items-center gap-2">
        <Clock3 className="h-5 w-5" />
        <div>
          <div className="text-xs font-black uppercase tracking-wide">Ưu đãi gần nhất kết thúc sau</div>
          <div className="text-[10px] text-white/80">{endLabel}</div>
        </div>
      </div>
      <div className="flex gap-1.5">
        {remaining.days > 0 && <TimeBox label="Ngày" value={remaining.days} />}
        <TimeBox label="Giờ" value={remaining.hours} />
        <TimeBox label="Phút" value={remaining.minutes} />
        <TimeBox label="Giây" value={remaining.seconds} />
      </div>
    </div>
  );
}
