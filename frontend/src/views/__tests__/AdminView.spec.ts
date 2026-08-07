import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'

import { api } from '@/api/client'
import type {
  AdminAgentDetail,
  AdminStats,
  AdminTokenResponse,
  AdminUserDetail,
  AdminUsersResponse,
  EmbedResponse,
  Source,
  UsageResponse,
} from '@/api/types'
import AdminAgentDetailView from '../AdminAgentDetailView.vue'
import AdminView from '../AdminView.vue'
import AdminUserView from '../AdminUserView.vue'

// jsdom has no canvas 2D context — stub the chart component.
vi.mock('vue-chartjs', () => ({
  Bar: {
    name: 'Bar',
    props: ['data', 'options'],
    template: '<div class="chartjs-bar" />',
  },
}))

vi.mock('@/api/client', () => ({
  api: {
    adminLogin:
      vi.fn<(data: { email: string; password: string }) => Promise<AdminTokenResponse>>(),
    adminMe: vi.fn<(token: string) => Promise<{ email: string }>>(),
    adminStats: vi.fn<(token: string, days?: number) => Promise<AdminStats>>(),
    adminUsers: vi.fn<
      (token: string, params?: { q?: string; page?: number; pageSize?: number }) => Promise<AdminUsersResponse>
    >(),
    adminUserDetail: vi.fn<(token: string, id: number) => Promise<AdminUserDetail>>(),
    adminUserUsage: vi.fn<
      (token: string, id: number, params?: { page?: number; pageSize?: number }) => Promise<UsageResponse>
    >(),
    adminAgent: vi.fn<(token: string, id: number) => Promise<AdminAgentDetail>>(),
    adminAgentSources: vi.fn<(token: string, id: number) => Promise<Source[]>>(),
    adminAgentUsage: vi.fn<
      (token: string, id: number, params?: { days?: number; page?: number; pageSize?: number }) => Promise<UsageResponse>
    >(),
    adminAgentEmbed: vi.fn<(token: string, id: number) => Promise<EmbedResponse>>(),
  },
  ApiError: class ApiError extends Error {},
  API_BASE: 'http://localhost:8000',
  getStoredToken: () => '',
}))

const STATS: AdminStats = {
  total_users: 3,
  total_agents: 5,
  total_requests: 120,
  total_input_tokens: 8000,
  total_output_tokens: 4000,
  total_tokens: 12000,
  series: [
    { date: '2026-08-01', requests: 10, input_tokens: 500, output_tokens: 250 },
    { date: '2026-08-02', requests: 12, input_tokens: 600, output_tokens: 300 },
  ],
}

const USER_ADA = {
  id: 1,
  email: 'ada@example.com',
  display_name: 'Ada',
  created_at: '2026-07-01T00:00:00Z',
  agent_count: 2,
  total_requests: 40,
  total_tokens: 5000,
  last_active: '2026-08-02T10:00:00Z',
}

const USERS: AdminUsersResponse = {
  items: [USER_ADA, {
      id: 2,
      email: 'bob@example.com',
      display_name: 'Bob',
      created_at: '2026-07-02T00:00:00Z',
      agent_count: 1,
      total_requests: 10,
      total_tokens: 900,
      last_active: null,
    },
  ],
  total: 2,
  page: 1,
  page_size: 20,
  pages: 1,
}

const DETAIL: AdminUserDetail = {
  user: USER_ADA,
  agents: [
    {
      id: 1,
      name: 'Admin Bot',
      description: 'desc',
      avatar_emoji: '🤖',
      avatar_url: null,
      chat_theme: '',
      created_at: '2026-07-01T00:00:00Z',
      source_count: 3,
      ready_sources: 2,
      total_requests: 40,
      total_tokens: 5000,
      last_active: '2026-08-02T10:00:00Z',
    },
  ],
}

const USAGE: UsageResponse = {
  summary: {
    total_requests: 40,
    total_input_tokens: 3000,
    total_output_tokens: 2000,
    total_tokens: 5000,
    series: [],
    countries: [],
  },
  items: [
    {
      id: 9,
      channel: 'widget',
      thread_id: 'a1:t',
      model: 'test-model',
      input_tokens: 100,
      output_tokens: 50,
      total_tokens: 150,
      cost: null,
      country: 'ID',
      status: 'completed',
      created_at: '2026-08-02T10:00:00Z',
      agent_id: 1,
      agent_name: 'Admin Bot',
    },
  ],
  total: 1,
  page: 1,
  page_size: 10,
  pages: 1,
}

function routes() {
  return createRouter({
    history: createWebHistory(),
    routes: [
      { path: '/admin', component: AdminView },
      { path: '/admin/users/:id', component: AdminUserView },
      { path: '/admin/agents/:id', component: AdminAgentDetailView },
    ],
  })
}

function mountView(component: unknown, router: ReturnType<typeof routes>) {
  return mount(component as never, { global: { plugins: [router, createPinia()] } })
}

describe('AdminView', () => {
  beforeEach(() => {
    localStorage.clear()
    localStorage.setItem('ap_admin_token', 'admin-token')
    setActivePinia(createPinia())
    vi.clearAllMocks()
    vi.mocked(api.adminStats).mockResolvedValue(STATS)
    vi.mocked(api.adminUsers).mockResolvedValue(USERS)
  })

  it('renders headline stats and user rows', async () => {
    const router = routes()
    await router.push('/admin')
    await router.isReady()
    const wrapper = mountView(AdminView, router)
    await flushPromises()

    expect(api.adminStats).toHaveBeenCalledWith('admin-token', 30)
    expect(api.adminUsers).toHaveBeenCalled()
    const text = wrapper.text()
    expect(text).toContain('Total users')
    expect(text).toContain('Total agents')
    expect(text).toContain('Ada')
    expect(text).toContain('bob@example.com')
    expect(text).toContain('5,000') // Ada tokens
  })

  it('search triggers a reload with the query and resets to page 1', async () => {
    const router = routes()
    await router.push('/admin')
    await router.isReady()
    const wrapper = mountView(AdminView, router)
    await flushPromises()
    vi.mocked(api.adminUsers).mockClear()

    await wrapper.find('input[aria-label="Search users"]').setValue('ada')
    await wrapper.find('form.admin-search').trigger('submit.prevent')
    await flushPromises()

    expect(api.adminUsers).toHaveBeenCalledWith(
      'admin-token',
      expect.objectContaining({ q: 'ada', page: 1 }),
    )
  })

  it('navigates to the next page', async () => {
    vi.mocked(api.adminUsers).mockResolvedValue({ ...USERS, total: 3, pages: 2, page: 1 })
    const router = routes()
    await router.push('/admin')
    await router.isReady()
    const wrapper = mountView(AdminView, router)
    await flushPromises()

    const next = wrapper.findAll('button').find((b) => b.text().includes('Next'))
    expect(next).toBeDefined()
    await next!.trigger('click')
    await flushPromises()

    expect(api.adminUsers).toHaveBeenLastCalledWith(
      'admin-token',
      expect.objectContaining({ page: 2 }),
    )
  })

  it('shows an error when users fail to load', async () => {
    vi.mocked(api.adminUsers).mockRejectedValue(new Error('Failed to load users'))
    const router = routes()
    await router.push('/admin')
    await router.isReady()
    const wrapper = mountView(AdminView, router)
    await flushPromises()

    expect(wrapper.text()).toContain('Failed to load users')
  })
})

describe('AdminUserView', () => {
  beforeEach(() => {
    localStorage.clear()
    localStorage.setItem('ap_admin_token', 'admin-token')
    setActivePinia(createPinia())
    vi.clearAllMocks()
    vi.mocked(api.adminUserDetail).mockResolvedValue(DETAIL)
    vi.mocked(api.adminUserUsage).mockResolvedValue(USAGE)
  })

  it('renders user profile, agent cards and usage history (read-only)', async () => {
    const router = routes()
    await router.push('/admin/users/1')
    await router.isReady()
    const wrapper = mountView(AdminUserView, router)
    await flushPromises()

    expect(api.adminUserDetail).toHaveBeenCalledWith('admin-token', 1)
    expect(api.adminUserUsage).toHaveBeenCalledWith('admin-token', 1, expect.objectContaining({ page: 1 }))
    const text = wrapper.text()
    expect(text).toContain('Ada')
    expect(text).toContain('ada@example.com')
    expect(text).toContain('Admin Bot')
    expect(text).toContain('2/3 sources')
    expect(text).toContain('Widget')
    expect(text).toContain('test-model')

    // agent card links to the admin agent detail page
    const card = wrapper.find('a.agent-card')
    expect(card.attributes('href')).toContain('/admin/agents/1')
  })

  it('shows an error when the user does not exist', async () => {
    vi.mocked(api.adminUserDetail).mockRejectedValue(new Error('User not found'))
    const router = routes()
    await router.push('/admin/users/999')
    await router.isReady()
    const wrapper = mountView(AdminUserView, router)
    await flushPromises()

    expect(wrapper.text()).toContain('User not found')
  })
})
