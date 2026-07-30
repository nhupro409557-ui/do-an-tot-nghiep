type MembershipTabProps = {
  points: number;
  nextTierInfo: {
    name: string;
    needed: number;
    percentage: number;
  };
  loyaltyPeriod?: {
    startedAt?: string;
    endsAt?: string;
    spendAmount?: number;
    expiringSoon?: number;
    nearestExpirationAt?: string;
    nearestExpirationAmount?: number;
    tier?: string;
  };
};

const tierLabels: Record<string, string> = { MEMBER: 'Thành viên', SILVER: 'Bạc', GOLD: 'Vàng', DIAMOND: 'Kim cương' };
const tierTargets: Record<string, number> = { MEMBER: 0, SILVER: 30_000_000, GOLD: 80_000_000, DIAMOND: 150_000_000 };

export function MembershipTab({ points, loyaltyPeriod }: MembershipTabProps) {
  const spendAmount = loyaltyPeriod?.spendAmount || 0;
  const currentTier = loyaltyPeriod?.tier || 'MEMBER';
  const maintainTarget = tierTargets[currentTier] || 0;
  const maintainNeeded = Math.max(maintainTarget - spendAmount, 0);
  const nextTarget = spendAmount < 30_000_000 ? { name: 'Bạc', amount: 30_000_000 }
    : spendAmount < 80_000_000 ? { name: 'Vàng', amount: 80_000_000 }
    : spendAmount < 150_000_000 ? { name: 'Kim cương', amount: 150_000_000 }
    : null;
  const formatCurrency = (value: number) => `${value.toLocaleString('vi-VN')}đ`;
  const formatDate = (value?: string) => value ? new Intl.DateTimeFormat('vi-VN').format(new Date(value)) : '—';
  const formatPeriodEnd = (value?: string) => value
    ? new Intl.DateTimeFormat('vi-VN').format(new Date(new Date(value).getTime() - 24 * 60 * 60 * 1000))
    : '—';
  const nearestExpirationDate = loyaltyPeriod?.nearestExpirationAt
    ? formatPeriodEnd(loyaltyPeriod.nearestExpirationAt)
    : null;
  return (
    <section className="bg-white rounded-xl shadow-sm p-6 space-y-5">
      <h3 className="font-bold text-gray-800 mb-4">Hạng thành viên</h3>
      <p className="text-sm text-gray-600">
        Bạn đang có <strong>{points.toLocaleString('vi-VN')} điểm</strong>.{' '}
        {nextTarget
          ? `Cần mua thêm ${formatCurrency(nextTarget.amount - spendAmount)} trong kỳ để đạt hạng ${nextTarget.name}.`
          : 'Bạn đã đạt hạng cao nhất.'}
      </p>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-lg bg-slate-50 p-4"><p className="text-xs text-slate-500">Kỳ hiện tại</p><p className="mt-1 text-sm font-semibold">{formatDate(loyaltyPeriod?.startedAt)} – {formatPeriodEnd(loyaltyPeriod?.endsAt)}</p></div>
        <div className="rounded-lg bg-slate-50 p-4"><p className="text-xs text-slate-500">Doanh số xét hạng trong kỳ</p><p className="mt-1 text-lg font-bold text-slate-900">{formatCurrency(spendAmount)}</p></div>
        <div className="rounded-lg bg-slate-50 p-4"><p className="text-xs text-slate-500">Duy trì {tierLabels[currentTier] || currentTier}</p><p className="mt-1 text-sm font-semibold">{maintainNeeded > 0 ? `Cần thêm ${formatCurrency(maintainNeeded)}` : 'Đã đủ điều kiện'}</p></div>
        <div className="rounded-lg bg-amber-50 p-4"><p className="text-xs text-amber-700">Sắp hết hạn trong 30 ngày</p><p className="mt-1 text-lg font-bold text-amber-800">{(loyaltyPeriod?.expiringSoon || 0).toLocaleString('vi-VN')} điểm</p></div>
      </div>
      {nearestExpirationDate && (loyaltyPeriod?.nearestExpirationAmount || 0) > 0 && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          <strong>{(loyaltyPeriod?.nearestExpirationAmount || 0).toLocaleString('vi-VN')} / {points.toLocaleString('vi-VN')} điểm</strong>{' '}
          sẽ hết hạn vào cuối ngày <strong>{nearestExpirationDate}</strong>.
        </div>
      )}
    </section>
  );
}
