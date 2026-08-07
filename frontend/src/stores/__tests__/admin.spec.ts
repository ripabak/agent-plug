import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { useAdminStore } from '../admin'
import type { AdminTokenResponse } from '@/api/types'

// Mock the api module so store tests never hit the network.
vi.mock('@/api/client', () => ({
  api: {
    adminLogin: vi.fn<(data: { email: string; password: string }) => Promise<AdminTokenResponse>>(),
    adminMe: vi.fn<(token: string) => Promise<{ email: string }>>(),
  },
  ApiError: class ApiError extends Error {},
  getStoredToken: () => '',
  API_BASE: 'http://localhost:8000',
}))

import { api } from '@/api/client'

describe('admin store', () => {
  beforeEach(() => {
    localStorage.clear()
    sessionStorage.clear()
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('persists token + email after login', async () => {
    vi.mocked(api.adminLogin).mockResolvedValue({
      access_token: 'admin-jwt',
      token_type: 'bearer',
      email: 'admin@example.com',
    })
    const store = useAdminStore()
    await store.login('admin@example.com', 'secret123')

    expect(store.isAuthenticated).toBe(true)
    expect(store.email).toBe('admin@example.com')
    expect(localStorage.getItem('ap_admin_token')).toBe('admin-jwt')
  })

  it('bootstrap restores email from token and logs out on failure', async () => {
    localStorage.setItem('ap_admin_token', 'stored-token')
    const store = useAdminStore()

    vi.mocked(api.adminMe).mockResolvedValue({ email: 'admin@example.com' })
    await store.bootstrap()
    expect(store.email).toBe('admin@example.com')

    vi.mocked(api.adminMe).mockRejectedValue(new Error('401'))
    store.logout()
    expect(store.isAuthenticated).toBe(false)
  })

  it('logout clears token and email', async () => {
    localStorage.setItem('ap_admin_token', 'x')
    const store = useAdminStore()
    store.logout()
    expect(store.token).toBe('')
    expect(store.email).toBe('')
    expect(localStorage.getItem('ap_admin_token')).toBeNull()
  })
})
