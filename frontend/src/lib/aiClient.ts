/**
 * Small client for the Python AI service (FastAPI, default http://localhost:8000).
 * Sends the same JWT the Nest backend issued at login.
 */
import { getCookieToken } from '@/lib/auth';
import type { ProcessedAnalytics } from '@/lib/analytics';

export const AI_URL = (process.env.NEXT_PUBLIC_AI_URL || 'http://localhost:8000').replace(/\/$/, '');

export class AiServiceError extends Error {
  status: number;
  code: string;
  constructor(message: string, status = 0, code = 'AI_ERROR') {
    super(message);
    this.name = 'AiServiceError';
    this.status = status;
    this.code = code;
  }
}

export interface ChatReply {
  answer: string;
  intent?: string;
  sources?: string[];
  conversationId?: string;
}

function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return getCookieToken() || localStorage.getItem('token');
}

/** fetch() with the Bearer token attached and uniform, human-readable errors. */
export async function fetchWithAuth(path: string, init: RequestInit = {}): Promise<Response> {
  const token = getToken();
  if (!token) throw new AiServiceError('You are signed out. Please log in again.', 401, 'NOT_AUTHENTICATED');

  const headers = new Headers(init.headers);
  headers.set('Authorization', `Bearer ${token}`);

  let res: Response;
  try {
    res = await fetch(`${AI_URL}${path}`, { ...init, headers });
  } catch {
    throw new AiServiceError(
      `Cannot reach the AI service at ${AI_URL}. Make sure it is running (./scripts/start-all.sh).`,
      0,
      'NETWORK_ERROR',
    );
  }

  if (!res.ok) {
    let message = `AI service error (${res.status}).`;
    let code = 'HTTP_ERROR';
    try {
      const body = await res.json();
      if (body?.message) message = body.message;
      if (body?.code) code = body.code;
    } catch {
      // non-JSON error body
    }
    if (res.status === 401) message = 'Your session is not valid for the AI service. Please log in again.';
    throw new AiServiceError(message, res.status, code);
  }
  return res;
}

/** Upload a CSV; resolves with the fast-phase analytics (status "enriching"). */
export async function analyzeDataset(file: File, businessName?: string): Promise<ProcessedAnalytics> {
  const form = new FormData();
  form.append('file', file);
  if (businessName) form.append('business_name', businessName);
  const res = await fetchWithAuth('/ai/v1/datasets/analyze', { method: 'POST', body: form });
  return res.json();
}

export async function getDataset(datasetId: string): Promise<ProcessedAnalytics> {
  const res = await fetchWithAuth(`/ai/v1/datasets/${encodeURIComponent(datasetId)}`);
  return res.json();
}

export async function deleteDataset(datasetId: string): Promise<void> {
  await fetchWithAuth(`/ai/v1/datasets/${encodeURIComponent(datasetId)}`, { method: 'DELETE' });
}

export async function sendChat(datasetId: string, message: string, conversationId?: string): Promise<ChatReply> {
  const res = await fetchWithAuth('/ai/v1/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ datasetId, message, conversationId }),
  });
  return res.json();
}

/**
 * Poll GET /datasets/{id} every `intervalMs` until status is "ready" or "failed"
 * (or `maxMs` passes). Calls `onUpdate` with each response. Abort via `signal`.
 */
export async function pollDataset(
  datasetId: string,
  onUpdate: (data: ProcessedAnalytics) => void,
  opts: { intervalMs?: number; maxMs?: number; signal?: AbortSignal } = {},
): Promise<ProcessedAnalytics | null> {
  const { intervalMs = 3000, maxMs = 120000, signal } = opts;
  const started = Date.now();
  while (Date.now() - started < maxMs) {
    await new Promise((r) => setTimeout(r, intervalMs));
    if (signal?.aborted) return null;
    const data = await getDataset(datasetId);
    if (signal?.aborted) return null;
    onUpdate(data);
    if (data.status === 'ready' || data.status === 'failed') return data;
  }
  return null;
}

/* ---------- Knowledge documents (PDF / TXT / MD for document Q&A) ---------- */

export interface KnowledgeDoc {
  id: string;
  fileName: string;
  scope: string;
  datasetId?: string | null;
  chunks: number;
  shared: boolean;
  createdAt: string;
}

export async function listKnowledgeDocs(): Promise<KnowledgeDoc[]> {
  const res = await fetchWithAuth('/ai/v1/rag/documents');
  return res.json();
}

export async function uploadKnowledgeDoc(file: File): Promise<void> {
  const form = new FormData();
  form.append('file', file);
  form.append('scope', 'user');
  await fetchWithAuth('/ai/v1/rag/documents', { method: 'POST', body: form });
}

export async function deleteKnowledgeDoc(id: string): Promise<void> {
  await fetchWithAuth(`/ai/v1/rag/documents/${encodeURIComponent(id)}`, { method: 'DELETE' });
}