/** Thin typed fetch wrapper around the Agent-Plug backend API. */

import type { Agent, EmbedResponse, Source, TokenResponse, UsageResponse, User } from './types'

export const API_BASE: string =
  (import.meta.env.VITE_API_BASE as string | undefined) || 'http://localhost:8000'

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
    this.name = 'ApiError'
  }
}

interface FetchOptions {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE'
  body?: unknown
  token?: string
}

async function request<T>(path: string, options: FetchOptions = {}): Promise<T> {
  const headers: Record<string, string> = {}
  if (options.body !== undefined) headers['Content-Type'] = 'application/json'
  if (options.token) headers['Authorization'] = `Bearer ${options.token}`

  let res: Response
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method: options.method ?? 'GET',
      headers,
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    })
  } catch {
    throw new ApiError(0, 'Cannot reach the server. Is the backend running?')
  }

  if (!res.ok) {
    let message = `Request failed (${res.status})`
    try {
      const data = await res.json()
      if (typeof data.detail === 'string') message = data.detail
      else if (Array.isArray(data.detail) && data.detail[0]?.msg) message = data.detail[0].msg
    } catch {
      /* keep default message */
    }
    throw new ApiError(res.status, message)
  }
  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}

/** Read the auth token from localStorage (source of truth for the auth store). */
export function getStoredToken(): string {
  return localStorage.getItem('ap_token') ?? ''
}

export const api = {
  // --- auth ---
  register: (data: { email: string; display_name: string; password: string }) =>
    request<TokenResponse>('/api/auth/register', { method: 'POST', body: data }),
  login: (data: { email: string; password: string }) =>
    request<TokenResponse>('/api/auth/login', { method: 'POST', body: data }),
  me: (token: string) => request<User>('/api/auth/me', { token }),

  // --- agents ---
  listAgents: (token: string) => request<Agent[]>('/api/agents', { token }),
  createAgent: (token: string, data: Partial<Agent>) =>
    request<Agent>('/api/agents', { method: 'POST', body: data, token }),
  getAgent: (token: string, id: number) => request<Agent>(`/api/agents/${id}`, { token }),
  updateAgent: (token: string, id: number, data: Partial<Agent>) =>
    request<Agent>(`/api/agents/${id}`, { method: 'PATCH', body: data, token }),
  deleteAgent: (token: string, id: number) =>
    request<void>(`/api/agents/${id}`, { method: 'DELETE', token }),
  regenerateToken: (token: string, id: number) =>
    request<Agent>(`/api/agents/${id}/regenerate-token`, { method: 'POST', token }),
  getEmbed: (token: string, id: number) =>
    request<EmbedResponse>(`/api/agents/${id}/embed`, { token }),

  // --- sources (RAG) ---
  listSources: (token: string, agentId: number) =>
    request<Source[]>(`/api/agents/${agentId}/sources`, { token }),
  addSources: (token: string, agentId: number, urls: string[]) =>
    request<Source[]>(`/api/agents/${agentId}/sources`, { method: 'POST', body: { urls }, token }),
  addTextSource: (token: string, agentId: number, data: { title?: string; content: string }) =>
    request<Source[]>(`/api/agents/${agentId}/sources/text`, { method: 'POST', body: data, token }),
  uploadSourceFiles: async (token: string, agentId: number, files: File[]) => {
    const form = new FormData()
    for (const f of files) form.append('files', f)
    const res = await fetch(`${API_BASE}/api/agents/${agentId}/sources/files`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      body: form,
    })
    if (!res.ok) {
      let message = `Upload failed (${res.status})`
      try {
        const data = await res.json()
        if (typeof data.detail === 'string') message = data.detail
      } catch {
        /* keep default */
      }
      throw new ApiError(res.status, message)
    }
    return (await res.json()) as Source[]
  },
  deleteSource: (token: string, agentId: number, sourceId: number) =>
    request<void>(`/api/agents/${agentId}/sources/${sourceId}`, { method: 'DELETE', token }),
  reindexSources: (token: string, agentId: number, onlyFailed = false) =>
    request<{ scheduled: number }>(`/api/agents/${agentId}/sources/reindex`, {
      method: 'POST',
      body: { only_failed: onlyFailed },
      token,
    }),

  // --- usage (dashboard tab) ---
  getUsage: (
    token: string,
    agentId: number,
    params: { days?: number; page?: number; pageSize?: number } = {},
  ) => {
    const q = new URLSearchParams()
    if (params.days !== undefined) q.set('days', String(params.days))
    q.set('page', String(params.page ?? 1))
    q.set('page_size', String(params.pageSize ?? 10))
    return request<UsageResponse>(`/api/agents/${agentId}/usage?${q}`, { token })
  },
}
