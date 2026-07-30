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
  runtime?: {
    metrics?: {
      window_hours?: number;
      total_responses?: number;
      gemini_responses?: number;
      fallback_responses?: number;
      fallback_rate?: number;
      verifier_failures?: number;
      verifier_failure_rate?: number;
      clarification_responses?: number;
      average_confidence?: number;
      shadow_evaluations?: number;
      shadow_matches?: number;
      shadow_match_rate?: number;
      total_feedback?: number;
      helpful_feedback?: number;
      helpful_rate?: number;
      error?: string;
    };
    circuit_breakers?: Array<{
      model: string;
      open: boolean;
      ttl_seconds: number;
      recent_failures: number;
      status?: string;
    }>;
    features?: Record<string, boolean | number>;
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
