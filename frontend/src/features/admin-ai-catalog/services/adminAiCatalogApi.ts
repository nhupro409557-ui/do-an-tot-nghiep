import { request } from '../../../services/apiClient';

export type AiCatalogRefreshJob = {
  id: string;
  status: 'queued' | 'running' | 'succeeded' | 'failed' | string;
  step: string;
  started_at?: string | null;
  finished_at?: string | null;
  output_tail?: string;
  error?: string | null;
  persistence_error?: string;
};

export type AiCatalogIndexStatus = {
  markdown?: {
    path?: string;
    exists?: boolean;
    documents?: number;
  };
  embedding_json?: {
    path?: string;
    exists?: boolean;
    documents?: number;
    complete?: boolean;
    model?: string | null;
    output_dimensionality?: number | null;
  };
  database?: {
    connected?: boolean;
    table_exists?: boolean;
    documents?: number;
    models?: string | null;
    min_dim?: number | null;
    max_dim?: number | null;
    complete_snapshot_documents?: number;
    last_updated_at?: string | null;
    vector_available?: boolean;
    vector_installed?: boolean;
    error?: string;
  };
  refresh_job?: AiCatalogRefreshJob | null;
  recent_refresh_jobs?: AiCatalogRefreshJob[];
};

export type AiCatalogRefreshResponse = {
  started: boolean;
  reason?: string;
  job?: AiCatalogRefreshJob | null;
};

export const adminAiCatalogApi = {
  getStatus: () => request<AiCatalogIndexStatus>('/admin/ai-catalog-index/status'),
  listJobs: (limit = 10) => request<{ items: AiCatalogRefreshJob[] }>(`/admin/ai-catalog-index/jobs?limit=${limit}`),
  refresh: () => request<AiCatalogRefreshResponse>('/admin/ai-catalog-index/refresh', { method: 'POST' }),
};
