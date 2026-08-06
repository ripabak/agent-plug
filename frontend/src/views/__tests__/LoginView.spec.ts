import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'

import LoginView from '../LoginView.vue'
import DashboardView from '../DashboardView.vue'

vi.mock('@/api/client', () => ({
  api: {
    login: vi.fn<(data: { email: string; password: string }) => Promise<TokenResponse>>(),
    me: vi.fn<(token: string) => Promise<User>>(),
    listAgents: vi.fn<(token: string) => Promise<Agent[]>>(),
  },
  ApiError: class ApiError extends Error {},
  getStoredToken: () => '',
  API_BASE: 'http://localhost:8000',
}))

import { api } from '@/api/client'
import type { Agent, TokenResponse, User } from '@/api/types'

const routes = [
  { path: '/login', component: LoginView },
  { path: '/dashboard', component: DashboardView },
]

function makeRouter() {
  return createRouter({ history: createWebHistory(), routes })
}

describe('LoginView', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('logs in and navigates to dashboard', async () => {
    vi.mocked(api.login).mockResolvedValue({
      access_token: 't',
      token_type: 'bearer',
      user: { id: 1, email: 'a@b.c', display_name: 'A', created_at: 'now' },
    })
    vi.mocked(api.listAgents).mockResolvedValue([])

    const router = makeRouter()
    await router.push('/login')
    await router.isReady()

    const wrapper = mount(LoginView, { global: { plugins: [router] } })
    await wrapper.find('#email').setValue('a@b.c')
    await wrapper.find('#password').setValue('secret123')
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()

    expect(api.login).toHaveBeenCalledWith({ email: 'a@b.c', password: 'secret123' })
    expect(router.currentRoute.value.path).toBe('/dashboard')
  })

  it('shows error message on failed login', async () => {
    vi.mocked(api.login).mockRejectedValue(new Error('Invalid email or password'))
    const router = makeRouter()
    await router.push('/login')
    await router.isReady()

    const wrapper = mount(LoginView, { global: { plugins: [router] } })
    await wrapper.find('#email').setValue('a@b.c')
    await wrapper.find('#password').setValue('wrong')
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()

    expect(wrapper.text()).toContain('Invalid email or password')
    expect(router.currentRoute.value.path).toBe('/login')
  })
})
