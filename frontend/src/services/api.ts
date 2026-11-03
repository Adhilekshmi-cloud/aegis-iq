/* API client for Aegis Knowledge System backend */

const API_BASE = '/api';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.text().catch(() => 'Unknown error');
    throw new Error(`API error ${res.status}: ${err}`);
  }
  return res.json();
}

export const api = {
  health: () => request<{ status: string }>('/health'),

  ingestDocuments: () => request<{ status: string; message: string }>('/ingest', { method: 'POST' }),

  getIngestionStatus: () => request<any>('/ingest/status'),

  submitQuery: (question: string) =>
    request<any>('/query', {
      method: 'POST',
      body: JSON.stringify({ question }),
    }),

  getEntities: (search?: string) => {
    const params = search ? `?search=${encodeURIComponent(search)}` : '';
    return request<any>(`/entities${params}`);
  },

  getEntity: (id: string) => request<any>(`/entities/${id}`),

  getFacts: (params?: { entity_id?: string; predicate?: string; status?: string }) => {
    const searchParams = new URLSearchParams();
    if (params?.entity_id) searchParams.set('entity_id', params.entity_id);
    if (params?.predicate) searchParams.set('predicate', params.predicate);
    if (params?.status) searchParams.set('verification_status', params.status);
    const qs = searchParams.toString();
    return request<any>(`/facts${qs ? '?' + qs : ''}`);
  },

  getFact: (id: string) => request<any>(`/facts/${id}`),

  getConflicts: () => request<any>('/conflicts'),

  getDocuments: () => request<any>('/documents'),

  runEvaluation: () => request<any>('/evaluate', { method: 'POST' }),

  getEvaluationResults: () => request<any>('/evaluate/results'),
};
