import { useCallback, useEffect, useRef, useState } from 'react';
import { Download, LoaderCircle, Plus } from 'lucide-react';
import { adminReportsApi } from '../services/adminReportsApi';
import type { ReportExportJob, ReportFilters, ReportView } from '../types';

const reportLabels: Record<ReportExportJob['reportType'], string> = {
  revenue: 'Doanh thu',
  orders: 'Đơn hàng',
  customers: 'Khách hàng',
};

const statusLabels: Record<ReportExportJob['status'], string> = {
  PENDING: 'Đang chờ',
  PROCESSING: 'Đang xử lý',
  COMPLETED: 'Hoàn tất',
  FAILED: 'Thất bại',
  EXPIRED: 'Đã hết hạn',
};

type Props = {
  activeView: ReportView;
  filters: ReportFilters;
};

export default function ReportExportJobs({ activeView, filters }: Props) {
  const [jobs, setJobs] = useState<ReportExportJob[]>([]);
  const [creating, setCreating] = useState(false);
  const [message, setMessage] = useState('');
  const pollingDelay = useRef(3_000);
  const supportsBackgroundExport = activeView !== 'products' && activeView !== 'inventory';

  const loadJobs = useCallback(async (signal?: AbortSignal) => {
    try {
      setJobs(await adminReportsApi.getExportJobs(signal));
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') return;
      setMessage(error instanceof Error ? error.message : 'Không thể tải tác vụ xuất.');
    }
  }, []);

  useEffect(() => {
    if (!supportsBackgroundExport) return undefined;
    const controller = new AbortController();
    void loadJobs(controller.signal);
    return () => controller.abort();
  }, [loadJobs, supportsBackgroundExport]);

  useEffect(() => {
    if (!supportsBackgroundExport) return undefined;
    const hasActiveJob = jobs.some(
      (job) => job.status === 'PENDING' || job.status === 'PROCESSING',
    );
    if (!hasActiveJob) {
      pollingDelay.current = 3_000;
      return undefined;
    }
    const timer = window.setTimeout(() => {
      void loadJobs().finally(() => {
        pollingDelay.current = Math.min(pollingDelay.current * 2, 30_000);
      });
    }, pollingDelay.current);
    return () => window.clearTimeout(timer);
  }, [jobs, loadJobs, supportsBackgroundExport]);

  if (!supportsBackgroundExport) return null;

  async function createJob() {
    setCreating(true);
    setMessage('');
    try {
      await adminReportsApi.createExportJob(
        activeView as 'revenue' | 'orders' | 'customers',
        filters,
      );
      setMessage('Đã tạo tác vụ xuất nền.');
      await loadJobs();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Không thể tạo tác vụ xuất.');
    } finally {
      setCreating(false);
    }
  }

  async function downloadJob(job: ReportExportJob) {
    setMessage('');
    try {
      const blob = await adminReportsApi.downloadExportJob(job.id);
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = job.filename || `bao-cao-${job.reportType}.csv`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Không thể tải tệp báo cáo.');
    }
  }

  return (
    <section aria-labelledby="report-export-jobs-title" className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 id="report-export-jobs-title" className="font-bold text-slate-950">
            Xuất báo cáo nền
          </h3>
          <p className="text-sm text-slate-600">
            Dùng cho báo cáo lớn; tệp hoàn tất có hiệu lực trong 24 giờ.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void createJob()}
          disabled={creating}
          className="inline-flex h-9 items-center gap-2 rounded-md bg-slate-950 px-3 text-sm font-bold text-white hover:bg-slate-800 disabled:opacity-50"
        >
          {creating ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
          Tạo tác vụ
        </button>
      </div>
      {message ? (
        <p role="status" className="mt-3 text-sm font-semibold text-slate-700">{message}</p>
      ) : null}
      {jobs.length ? (
        <div className="mt-3 overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="border-b border-slate-200 text-left text-xs uppercase text-slate-500">
              <tr>
                <th className="px-3 py-2">Báo cáo</th>
                <th className="px-3 py-2">Trạng thái</th>
                <th className="px-3 py-2">Số dòng</th>
                <th className="px-3 py-2">Thời điểm tạo</th>
                <th className="px-3 py-2">Tệp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {jobs.slice(0, 5).map((job) => (
                <tr key={job.id}>
                  <td className="px-3 py-2 font-semibold">{reportLabels[job.reportType]}</td>
                  <td className="px-3 py-2">{statusLabels[job.status]}</td>
                  <td className="px-3 py-2">{job.totalRows.toLocaleString('vi-VN')}</td>
                  <td className="px-3 py-2">{new Date(job.createdAt).toLocaleString('vi-VN')}</td>
                  <td className="px-3 py-2">
                    {job.status === 'COMPLETED' ? (
                      <button
                        type="button"
                        onClick={() => void downloadJob(job)}
                        className="inline-flex items-center gap-1 font-bold text-emerald-700 hover:text-emerald-800"
                      >
                        <Download className="h-4 w-4" /> Tải CSV
                      </button>
                    ) : job.status === 'FAILED' ? (
                      <span className="text-xs text-red-700">{job.errorMessage || 'Không thể xuất.'}</span>
                    ) : job.status === 'EXPIRED' ? (
                      <span className="text-xs text-slate-500">Tệp đã được dọn sau 24 giờ.</span>
                    ) : (
                      <LoaderCircle className="h-4 w-4 animate-spin text-slate-500" aria-label="Đang xử lý" />
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}
