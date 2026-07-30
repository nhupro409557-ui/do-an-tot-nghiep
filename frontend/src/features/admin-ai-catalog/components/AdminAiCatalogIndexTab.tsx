import React, { useEffect, useMemo, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Clock3,
  Database,
  FileText,
  Gauge,
  History,
  MessageSquareText,
  RefreshCw,
  Search,
  Server,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';
import { AdminBadge, AdminPanel, AdminTable } from '../../admin-shell/components/AdminDashboardParts';
import {
  adminAiCatalogApi,
  type AiCatalogIndexStatus,
  type AiCatalogRefreshJob,
} from '../services/adminAiCatalogApi';

type AdminAiCatalogIndexTabProps = {
  aiCatalogIndexStatus?: AiCatalogIndexStatus | null;
  aiCatalogIndexJobs?: AiCatalogRefreshJob[];
  busy?: boolean;
  query?: string;
  loadData?: (tab?: string, options?: { force?: boolean; silent?: boolean; prefetch?: boolean }) => Promise<void>;
};

const numberFormatter = new Intl.NumberFormat('vi-VN');
const percentFormatter = new Intl.NumberFormat('vi-VN', { style: 'percent', maximumFractionDigits: 1 });

function formatNumber(value: unknown) {
  const number = Number(value);
  return Number.isFinite(number) ? numberFormatter.format(number) : '-';
}

function formatPercent(value: unknown) {
  const number = Number(value);
  return Number.isFinite(number) ? percentFormatter.format(number) : '-';
}

function formatDate(value?: string | null) {
  return value ? new Date(value).toLocaleString('vi-VN') : '-';
}

function isRunningJob(job?: AiCatalogRefreshJob | null) {
  return Boolean(job && ['queued', 'running'].includes(job.status));
}

function jobTone(status?: string): 'slate' | 'green' | 'red' | 'yellow' | 'blue' | 'amber' {
  if (status === 'succeeded') return 'green';
  if (status === 'failed') return 'red';
  if (status === 'running') return 'blue';
  if (status === 'queued') return 'amber';
  return 'slate';
}

function statusLabel(status?: string) {
  const labels: Record<string, string> = {
    queued: 'Đang chờ',
    running: 'Đang chạy',
    succeeded: 'Thành công',
    failed: 'Thất bại',
  };
  return status ? labels[status] || status : 'Chưa có';
}

function StatusMetric({
  icon: Icon,
  label,
  value,
  caption,
  healthy = true,
}: {
  icon: React.ElementType;
  label: string;
  value: React.ReactNode;
  caption: string;
  healthy?: boolean;
}) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-bold uppercase tracking-wide text-slate-500">{label}</p>
          <div className="mt-2 text-2xl font-bold text-slate-950">{value}</div>
        </div>
        <span className={`inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${healthy ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'}`}>
          <Icon className="h-5 w-5" />
        </span>
      </div>
      <p className="mt-2 text-sm leading-6 text-slate-500">{caption}</p>
    </div>
  );
}

export default function AdminAiCatalogIndexTab({
  aiCatalogIndexStatus,
  aiCatalogIndexJobs = [],
  busy = false,
  query = '',
  loadData,
}: AdminAiCatalogIndexTabProps) {
  const [refreshing, setRefreshing] = useState(false);
  const [message, setMessage] = useState('');
  const status = aiCatalogIndexStatus || {};
  const currentJob = status.refresh_job || null;
  const running = isRunningJob(currentJob);
  const jobs = aiCatalogIndexJobs.length > 0 ? aiCatalogIndexJobs : status.recent_refresh_jobs || [];

  const filteredJobs = useMemo(() => {
    const keyword = query.trim().toLowerCase();
    if (!keyword) return jobs;
    return jobs.filter((job) => [job.id, job.status, job.step, job.error, job.output_tail]
      .some((value) => String(value || '').toLowerCase().includes(keyword)));
  }, [jobs, query]);

  useEffect(() => {
    if (!running || !loadData) return undefined;
    const timer = window.setInterval(() => {
      void loadData('aiCatalogIndex', { force: true, silent: true });
    }, 4000);
    return () => window.clearInterval(timer);
  }, [loadData, running]);

  async function reloadStatus() {
    setMessage('');
    await loadData?.('aiCatalogIndex', { force: true });
  }

  async function startRefresh() {
    setRefreshing(true);
    setMessage('');
    try {
      const result = await adminAiCatalogApi.refresh();
      setMessage(result.started ? 'Đã đưa tác vụ làm mới chỉ mục AI vào hàng chờ.' : result.reason || 'Tác vụ làm mới đang chạy.');
      await loadData?.('aiCatalogIndex', { force: true });
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Không thể bắt đầu làm mới chỉ mục AI.');
    } finally {
      setRefreshing(false);
    }
  }

  const database = status.database || {};
  const embeddingJson = status.embedding_json || {};
  const markdown = status.markdown || {};
  const runtime = status.runtime || {};
  const metrics = runtime.metrics || {};
  const circuits = runtime.circuit_breakers || [];
  const databaseReady = Boolean(database.connected && database.table_exists);
  const embeddingReady = Boolean(embeddingJson.exists && embeddingJson.complete);
  const fallbackHealthy = Number(metrics.fallback_rate || 0) <= 0.1;
  const verifierHealthy = Number(metrics.verifier_failure_rate || 0) <= 0.02;

  return (
    <div className="space-y-5">
      <AdminPanel
        title="Chỉ mục danh mục AI"
        action={(
          <>
            <button type="button" onClick={() => void reloadStatus()} className="inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-slate-200 bg-white px-3 text-sm font-bold text-slate-700 transition hover:bg-slate-50">
              <RefreshCw className="h-4 w-4" />
              <span>Làm mới</span>
            </button>
            <button type="button" disabled={busy || refreshing || running} onClick={() => void startRefresh()} className="inline-flex h-10 items-center justify-center gap-2 rounded-lg bg-slate-900 px-3 text-sm font-bold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300">
              <Sparkles className="h-4 w-4" />
              <span>Chạy làm mới</span>
            </button>
          </>
        )}
      >
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatusMetric icon={FileText} label="Markdown" value={formatNumber(markdown.documents)} caption={markdown.exists ? 'Tài liệu danh mục đã được tạo.' : 'Chưa tìm thấy thư mục Markdown index.'} healthy={Boolean(markdown.exists)} />
          <StatusMetric icon={Search} label="Embedding JSON" value={formatNumber(embeddingJson.documents)} caption={`${embeddingJson.model || 'Chưa có model'} · ${embeddingJson.output_dimensionality || '-'} chiều`} healthy={embeddingReady} />
          <StatusMetric icon={Database} label="PostgreSQL" value={formatNumber(database.documents)} caption={databaseReady ? `Snapshot DB ${database.min_dim || '-'}..${database.max_dim || '-'} chiều.` : database.error || 'Bảng embedding chưa sẵn sàng.'} healthy={databaseReady} />
          <StatusMetric icon={Server} label="pgvector" value={database.vector_installed ? 'Có' : 'Chưa có'} caption={database.vector_available ? 'Extension có thể dùng trong PostgreSQL.' : 'Đang dùng JSONB dự phòng cho embedding.'} healthy={Boolean(database.vector_installed)} />
        </div>

        <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-sm font-bold text-slate-900">Tác vụ hiện tại</p>
              <p className="mt-1 text-sm text-slate-500">{currentJob ? `Bước ${currentJob.step} · bắt đầu ${formatDate(currentJob.started_at)}` : 'Chưa có tác vụ làm mới đang được ghi nhận.'}</p>
            </div>
            <AdminBadge tone={jobTone(currentJob?.status)}>{statusLabel(currentJob?.status)}</AdminBadge>
          </div>
          {message && <p className="mt-3 text-sm font-semibold text-slate-700">{message}</p>}
          {currentJob?.error && <div className="mt-3 flex items-start gap-2 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700"><AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" /><span>{currentJob.error}</span></div>}
        </div>
      </AdminPanel>

      <AdminPanel title={`Vận hành chatbot · ${metrics.window_hours || 24} giờ gần nhất`}>
        {metrics.error ? (
          <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm font-semibold text-rose-700">{metrics.error}</div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <StatusMetric icon={Activity} label="Lượt trả lời" value={formatNumber(metrics.total_responses)} caption={`${formatNumber(metrics.gemini_responses)} lượt dùng Gemini`} />
            <StatusMetric icon={Gauge} label="Dự phòng DB" value={formatPercent(metrics.fallback_rate)} caption={`${formatNumber(metrics.fallback_responses)} lượt không dùng được model`} healthy={fallbackHealthy} />
            <StatusMetric icon={ShieldCheck} label="Verifier lỗi" value={formatPercent(metrics.verifier_failure_rate)} caption={`${formatNumber(metrics.verifier_failures)} câu không vượt kiểm chứng`} healthy={verifierHealthy} />
            <StatusMetric icon={MessageSquareText} label="Phản hồi hữu ích" value={metrics.total_feedback ? formatPercent(metrics.helpful_rate) : '-'} caption={`${formatNumber(metrics.helpful_feedback)}/${formatNumber(metrics.total_feedback)} đánh giá hữu ích`} healthy={!metrics.total_feedback || Number(metrics.helpful_rate || 0) >= 0.8} />
          </div>
        )}

        <div className="mt-4 grid gap-3 lg:grid-cols-2">
          {circuits.map((circuit) => (
            <div key={circuit.model} className="flex items-center justify-between gap-3 rounded-lg border border-slate-200 bg-white p-4">
              <div>
                <p className="font-mono text-sm font-bold text-slate-900">{circuit.model}</p>
                <p className="mt-1 text-xs text-slate-500">Lỗi gần đây: {circuit.recent_failures}{circuit.open ? ` · tự đóng sau ${circuit.ttl_seconds}s` : ''}</p>
              </div>
              <AdminBadge tone={circuit.open ? 'red' : circuit.status ? 'amber' : 'green'}>
                {circuit.open ? 'Đang ngắt' : circuit.status === 'LOCAL_FALLBACK' ? 'Bộ nhớ cục bộ' : circuit.status ? 'Thiếu Redis' : 'Bình thường'}
              </AdminBadge>
            </div>
          ))}
        </div>
        {Boolean(metrics.shadow_evaluations) && (
          <div className="mt-3 rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-800">
            Shadow đã đánh giá <strong>{formatNumber(metrics.shadow_evaluations)}</strong> lượt; V2 trùng intent V1 <strong>{formatPercent(metrics.shadow_match_rate)}</strong>. Tỷ lệ khác nhau là tín hiệu để xem mẫu log, không tự động xem là lỗi.
          </div>
        )}
      </AdminPanel>

      <AdminPanel title="Lịch sử làm mới">
        {filteredJobs.length === 0 ? (
          <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 px-4 py-8 text-center text-sm font-semibold text-slate-500">Chưa có tác vụ phù hợp.</div>
        ) : (
          <AdminTable headers={['Trạng thái', 'Bước', 'Bắt đầu', 'Kết thúc', 'Ghi chú']} itemName="tác vụ">
            {filteredJobs.map((job) => (
              <tr key={job.id}>
                <td className="px-4 py-3"><AdminBadge tone={jobTone(job.status)}>{job.status === 'succeeded' ? <CheckCircle2 className="mr-1 h-3.5 w-3.5" /> : null}{job.status === 'running' || job.status === 'queued' ? <Clock3 className="mr-1 h-3.5 w-3.5" /> : null}{job.status === 'failed' ? <AlertTriangle className="mr-1 h-3.5 w-3.5" /> : null}{statusLabel(job.status)}</AdminBadge></td>
                <td className="px-4 py-3 font-mono text-xs font-semibold text-slate-700">{job.step}</td>
                <td className="px-4 py-3">{formatDate(job.started_at)}</td>
                <td className="px-4 py-3">{formatDate(job.finished_at)}</td>
                <td className="max-w-md px-4 py-3">{job.error ? <span className="line-clamp-2 text-sm font-semibold text-rose-700">{job.error}</span> : <span className="inline-flex items-center gap-1 text-sm text-slate-500"><History className="h-3.5 w-3.5" />{job.output_tail ? 'Có log thực thi' : 'Không có lỗi'}</span>}</td>
              </tr>
            ))}
          </AdminTable>
        )}
      </AdminPanel>
    </div>
  );
}
