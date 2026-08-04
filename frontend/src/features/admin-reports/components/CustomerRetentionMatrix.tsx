import type { CustomerRetentionReport } from '../types';

const MAX_VISIBLE_OFFSETS = 12;

function monthParts(value: string) {
  const [year, month] = value.slice(0, 7).split('-').map(Number);
  return { year, month };
}

function currentMonthParts(timezone: string) {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: timezone,
    year: 'numeric',
    month: '2-digit',
  }).formatToParts(new Date());
  return {
    year: Number(parts.find((part) => part.type === 'year')?.value),
    month: Number(parts.find((part) => part.type === 'month')?.value),
  };
}

function monthDistance(from: { year: number; month: number }, to: {
  year: number;
  month: number;
}) {
  return (to.year - from.year) * 12 + to.month - from.month;
}

export default function CustomerRetentionMatrix({
  report,
}: {
  report: CustomerRetentionReport | null;
}) {
  if (!report?.cohorts.length) {
    return (
      <div role="status" className="rounded-lg border border-slate-200 bg-white p-6 text-center text-sm text-slate-500">
        Chưa có cohort khách hàng để phân tích giữ chân.
      </div>
    );
  }

  const currentMonth = currentMonthParts(report.timezone);
  const largestAge = Math.max(
    0,
    ...report.cohorts.map((cohort) => (
      monthDistance(monthParts(cohort.cohortMonth), currentMonth)
    )),
  );
  const visibleOffsets = Array.from(
    { length: Math.min(MAX_VISIBLE_OFFSETS, largestAge + 1) },
    (_, index) => index,
  );

  return (
    <section aria-labelledby="customer-retention-title" className="rounded-lg border border-slate-200 bg-white">
      <div className="border-b border-slate-200 px-4 py-3">
        <h3 id="customer-retention-title" className="font-bold text-slate-950">
          Giữ chân theo cohort đăng ký
        </h3>
        <p className="mt-1 text-xs text-slate-500">
          M0 là tháng đăng ký. Ô tháng hiện tại được đánh dấu đang diễn ra.
        </p>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead className="border-b border-slate-200 bg-slate-50 text-left text-xs uppercase text-slate-500">
            <tr>
              <th className="sticky left-0 bg-slate-50 px-4 py-3">Cohort</th>
              <th className="px-3 py-3 text-right">Quy mô</th>
              {visibleOffsets.map((offset) => (
                <th key={offset} className="px-3 py-3 text-center">M{offset}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {report.cohorts.map((cohort) => {
              const cohortMonth = monthParts(cohort.cohortMonth);
              const age = monthDistance(cohortMonth, currentMonth);
              const periods = new Map(
                cohort.periods.map((period) => [period.monthOffset, period]),
              );
              return (
                <tr key={cohort.cohortMonth}>
                  <th className="sticky left-0 bg-white px-4 py-3 text-left font-semibold text-slate-900">
                    {cohort.cohortMonth.slice(0, 7)}
                  </th>
                  <td className="px-3 py-3 text-right">{cohort.cohortSize}</td>
                  {visibleOffsets.map((offset) => {
                    if (offset > age) {
                      return <td key={offset} className="px-3 py-3 text-center text-slate-300">—</td>;
                    }
                    const period = periods.get(offset);
                    const isCurrent = offset === age;
                    return (
                      <td
                        key={offset}
                        className={`px-3 py-3 text-center ${isCurrent ? 'bg-amber-50' : ''}`}
                        title={isCurrent ? 'Tháng đang diễn ra, số liệu chưa hoàn tất' : undefined}
                      >
                        <div className="font-semibold text-slate-900">
                          {Number(period?.retentionRate || 0).toFixed(2)}%
                        </div>
                        <div className="text-xs text-slate-500">
                          {period?.customers || 0} khách
                          {isCurrent ? ' · đang diễn ra' : ''}
                        </div>
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
