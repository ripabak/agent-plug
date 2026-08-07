import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { useAuthStore } from '../auth'
import type { Agent, EmbedResponse, Source, TokenResponse, User } from '@/api/types'

// Mock the api module so store tests never hit the network.
vi.mock('@/api/client', () => ({
  api: {
    login: vi.fn<(data: { email: string; password: string }) => Promise<TokenResponse>>(),
    register:
      vi.fn<
        (data: { email: string; display_name: string; password: string }) => Promise<TokenResponse>
      >(),
    me: vi.fn<(token: string) => Promise<User>>(),
    listAgents: vi.fn<(token: string) => Promise<Agent[]>>(),
    createAgent: vi.fn<(token: string, data: Partial<Agent>) => Promise<Agent>>(),
    getAgent: vi.fn<(token: string, id: number) => Promise<Agent>>(),
    updateAgent: vi.fn<(token: string, id: number, data: Partial<Agent>) => Promise<Agent>>(),
    deleteAgent: vi.fn<(token: string, id: number) => Promise<void>>(),
    regenerateToken: vi.fn<(token: string, id: number) => Promise<Agent>>(),
    getEmbed: vi.fn<(token: string, id: number) => Promise<EmbedResponse>>(),
    listSources: vi.fn<(token: string, agentId: number) => Promise<Source[]>>(),
    addSources: vi.fn<(token: string, agentId: number, urls: string[]) => Promise<Source[]>>(),
    deleteSource: vi.fn<(token: string, agentId: number, sourceId: number) => Promise<void>>(),
    reindexSources:
      vi.fn<
        (token: string, agentId: number, onlyFailed?: boolean) => Promise<{ scheduled: number }>
      >(),
  },
  ApiError: class ApiError extends Error {},
  getStoredToken: () => '',
  API_BASE: 'http://localhost:8000',
}))

import { api } from '@/api/client'

describe('auth store', () => {
  beforeEach(() => {
    localStorage.clear()
    sessionStorage.clear()
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('persists token + user after login', async () => {
    vi.mocked(api.login).mockResolvedValue({
      access_token: 'jwt-token',
      token_type: 'bearer',
      user: { id: 1, email: 'a@b.c', display_name: 'A', created_at: 'now' },
    })
    const store = useAuthStore()
    await store.login('a@b.c', 'secret123')

    expect(store.isAuthenticated).toBe(true)
    expect(store.user?.email).toBe('a@b.c')
    expect(localStorage.getItem('ap_token')).toBe('jwt-token')
  })

  it('registers and stores session', async () => {
    vi.mocked(api.register).mockResolvedValue({
      access_token: 't2',
      token_type: 'bearer',
      user: { id: 2, email: 'new@b.c', display_name: 'N', created_at: 'now' },
    })
    const store = useAuthStore()
    await store.register({ email: 'new@b.c', display_name: 'N', password: 'secret123' })
    expect(store.user?.display_name).toBe('N')
  })

  it('bootstrap restores user from token and logs out on 401', async () => {
    localStorage.setItem('ap_token', 'stored-token')
    const store = useAuthStore()

    vi.mocked(api.me).mockResolvedValue({
      id: 1,
      email: 'a@b.c',
      display_name: 'A',
      created_at: 'now',
    })
    await store.bootstrap()
    expect(store.user?.email).toBe('a@b.c')

    vi.mocked(api.me).mockRejectedValue(new Error('401'))
    store.logout() // simulate expired session next time
    expect(store.isAuthenticated).toBe(false)
  })

  it('logout clears token and user', async () => {
    localStorage.setItem('ap_token', 'x')
    const store = useAuthStore()
    store.logout()
    expect(store.token).toBe('')
    expect(store.user).toBeNull()
    expect(localStorage.getItem('ap_token')).toBeNull()
  })
})
