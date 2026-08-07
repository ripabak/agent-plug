import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'

import { api } from '@/api/client'
import type {
  AdminAgentDetail,
  AdminUserRow,
  Agent,
  EmbedResponse,
  Source,
  UsageResponse,
} from '@/api/types'
import AdminAgentDetailView from '../AdminAgentDetailView.vue'

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

const OWNER: AdminUserRow = {
  id: 7,
  email: 'ada@example.com',
  display_name: 'Ada',
  created_at: '2026-07-01T00:00:00Z',
  agent_count: 2,
  total_requests: 40,
  total_tokens: 5000,
  last_active: '2026-08-02T10:00:00Z',
}

const AGENT: Agent = {
  id: 1,
  user_id: 7,
  name: 'Admin Bot',
  description: 'A monitored agent',
  persona_prompt: 'Be concise.',
  welcome_message: 'Hi!',
  avatar_emoji: '🤖',
  avatar_url: null,
  avatar_kind: 'photo',
  chat_theme: '',
  show_thinking: true,
  show_tools: true,
  public_token: 'pub-tok',
  created_at: '2026-07-01T00:00:00Z',
  updated_at: '2026-07-05T00:00:00Z',
}

const DETAIL: AdminAgentDetail = { agent: AGENT, user: OWNER }

const SOURCES: Source[] = [
  {
    id: 1,
    agent_id: 1,
    url: 'https://example.com/docs',
    kind: 'url',
    file_name: null,
    file_size: null,
    status: 'ready',
    title: 'Docs',
    error: null,
    chunk_count: 4,
    created_at: '2026-07-02T00:00:00Z',
    updated_at: '2026-07-02T00:00:00Z',
  },
  {
    id: 2,
    agent_id: 1,
    url: 'https://example.com/broken.pdf',
    kind: 'pdf',
    file_name: 'broken.pdf',
    file_size: 2048,
    status: 'failed',
    title: null,
    error: 'fetch failed',
    chunk_count: 0,
    created_at: '2026-07-03T00:00:00Z',
    updated_at: '2026-07-03T00:00:00Z',
  },
]

const USAGE: UsageResponse = {
  summary: {
    total_requests: 40,
    total_input_tokens: 3000,
    total_output_tokens: 2000,
    total_tokens: 5000,
    series: [
      { date: '2026-08-01', requests: 2, input_tokens: 100, output_tokens: 50 },
      { date: '2026-08-02', requests: 1, input_tokens: 50, output_tokens: 25 },
    ],
    countries: [{ country: 'ID', requests: 30 }],
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
      page_url: 'https://shop.example.com/items/42',
    },
  ],
  total: 1,
  page: 1,
  page_size: 10,
  pages: 1,
}

const EMBED: EmbedResponse = {
  html: '<script data-agent-id="1" data-token="pub-tok" data-base-url="http://localhost:8000"></script>',
  agent_id: 1,
  public_token: 'pub-tok',
}

function routes() {
  return createRouter({
    history: createWebHistory(),
    routes: [{ path: '/admin/agents/:id', component: AdminAgentDetailView }],
  })
}

async function mountView() {
  const router = routes()
  await router.push('/admin/agents/1')
  await router.isReady()
  const wrapper = mount(AdminAgentDetailView, {
    global: { plugins: [router, createPinia()] },
  })
  await flushPromises()
  return { wrapper, router }
}

describe('AdminAgentDetailView', () => {
  beforeEach(() => {
    localStorage.clear()
    localStorage.setItem('ap_admin_token', 'admin-token')
    setActivePinia(createPinia())
    vi.clearAllMocks()
    vi.mocked(api.adminAgent).mockResolvedValue(DETAIL)
    vi.mocked(api.adminAgentSources).mockResolvedValue(SOURCES)
    vi.mocked(api.adminAgentUsage).mockResolvedValue(USAGE)
    vi.mocked(api.adminAgentEmbed).mockResolvedValue(EMBED)
  })

  it('renders the agent header + read-only settings', async () => {
    const { wrapper } = await mountView()

    expect(api.adminAgent).toHaveBeenCalledWith('admin-token', 1)
    const text = wrapper.text()
    expect(text).toContain('Admin Bot')
    expect(text).toContain('A monitored agent')
    expect(text).toContain('owned by Ada')
    // persona is shown; the legacy system_prompt column is DEAD (not used
    // by build_system_prompt) and must NOT appear on this page
    expect(text).toContain('Be concise.')
    expect(text).not.toContain('You are a helpful assistant.')
    // header color derives from the saved theme (no legacy theme_color)
    expect(text).toContain('#211f1b')
    expect(text).toContain('Thinking on')
  })

  it('knowledge tab lists sources read-only (no remove buttons)', async () => {
    const { wrapper } = await mountView()

    await wrapper.findAll('button.tab').find((b) => b.text() === 'Knowledge')!.trigger('click')
    await flushPromises()

    expect(api.adminAgentSources).toHaveBeenCalledWith('admin-token', 1)
    const text = wrapper.text()
    expect(text).toContain('Docs')
    expect(text).toContain('broken.pdf')
    expect(text).toContain('Failed')
    expect(text).toContain('fetch failed')
    expect(wrapper.findAll('button').some((b) => b.text() === 'Remove')).toBe(false)
  })

  it('usage tab loads charts + history with pagination', async () => {
    const { wrapper } = await mountView()

    await wrapper.findAll('button.tab').find((b) => b.text() === 'Usage')!.trigger('click')
    await flushPromises()

    expect(api.adminAgentUsage).toHaveBeenCalledWith(
      'admin-token',
      1,
      expect.objectContaining({ days: 30, page: 1 }),
    )
    const text = wrapper.text()
    expect(text).toContain('Requests')
    expect(text).toContain('Total tokens')
    expect(text).toContain('test-model')
    expect(text).toContain('Widget')
    // where the widget was called from + top countries (parity with UsageTab)
    expect(text).toContain('shop.example.com/items/42')
    expect(text).toContain('Top countries')
    expect(text).toContain('Indonesia')
  })

  it('embed tab shows the snippet and demo link', async () => {
    const { wrapper } = await mountView()

    await wrapper.findAll('button.tab').find((b) => b.text() === 'Embed')!.trigger('click')
    await flushPromises()

    expect(api.adminAgentEmbed).toHaveBeenCalledWith('admin-token', 1)
    expect(wrapper.get('[data-testid="admin-embed-code"]').text()).toContain('data-token="pub-tok"')
    expect(wrapper.get('a.btn-secondary').attributes('href')).toContain('demo.html')
  })

  it('preview tab mounts the real widget with the agent token', async () => {
    const { wrapper } = await mountView()

    await wrapper.findAll('button.tab').find((b) => b.text() === 'Preview')!.trigger('click')
    await flushPromises()

    // read-only mirror of the dashboard preview panel: display + theme
    const text = wrapper.text()
    expect(text).toContain('Thinking on')
    expect(text).toContain('Tools on')
    expect(text).toContain('Default')

    // jsdom doesn't execute the external script, but the <script> tag must be
    // attached to the host with the agent id + public token (flush: 'post'
    // watcher — this regressed when the host div was v-if'd by the tab).
    const script = wrapper.find('.preview-widget-host script')
    expect(script.exists()).toBe(true)
    expect(script.attributes('data-agent-id')).toBe('1')
    expect(script.attributes('data-token')).toBe('pub-tok')
    expect(script.attributes('data-base-url')).toBeTruthy()
  })

  it('shows an error when the agent is not found', async () => {
    vi.mocked(api.adminAgent).mockRejectedValue(new Error('Agent not found'))
    const { wrapper } = await mountView()
    expect(wrapper.text()).toContain('Agent not found')
  })
})
