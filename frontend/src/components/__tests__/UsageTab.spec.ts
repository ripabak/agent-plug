import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'

import { api } from '@/api/client'
import type { Agent, UsageResponse } from '@/api/types'
import { useAgentsStore } from '@/stores/agents'
import { useAuthStore } from '@/stores/auth'
import UsageTab from '../UsageTab.vue'

// jsdom has no canvas 2D context — stub the chart component and assert on
// the data it receives instead of the rendered canvas.
vi.mock('vue-chartjs', () => ({
  Bar: {
    name: 'Bar',
    props: ['data', 'options'],
    template:
      '<div class="chartjs-bar" :data-labels="JSON.stringify(data.labels || [])" ' +
      ':data-datasets="JSON.stringify((data.datasets || []).map((d) => ({ label: d.label, data: d.data })))" ' +
      ':data-options="JSON.stringify(options)" />',
  },
}))

vi.mock('@/api/client', () => ({
  api: {
    getUsage:
      vi.fn<
        (
          token: string,
          agentId: number,
          params?: { days?: number; page?: number; pageSize?: number },
        ) => Promise<UsageResponse>
      >(),
  },
  ApiError: class ApiError extends Error {},
  API_BASE: 'http://localhost:8000',
  getStoredToken: () => '',
}))

const AGENT: Agent = {
  id: 1,
  user_id: 1,
  name: 'Usage Bot',
  description: '',
  persona_prompt: null,
  welcome_message: 'hi',
  avatar_emoji: '🤖',
  avatar_url: null,
  avatar_kind: 'photo',
  chat_theme: '',
  show_thinking: true,
  show_tools: true,
  public_token: 'tok',
  created_at: '',
  updated_at: '',
}

function fixture(overrides: Partial<UsageResponse> = {}): UsageResponse {
  return {
    summary: {
      total_requests: 3,
      total_input_tokens: 300,
      total_output_tokens: 150,
      total_tokens: 450,
      series: [
        { date: '2026-07-06', requests: 1, input_tokens: 100, output_tokens: 50 },
        { date: '2026-07-07', requests: 0, input_tokens: 0, output_tokens: 0 },
        { date: '2026-07-08', requests: 2, input_tokens: 200, output_tokens: 100 },
      ],
      countries: [
        { country: 'ID', requests: 2 },
        { country: 'US', requests: 1 },
      ],
    },
    items: [
      {
        id: 3,
        thread_id: 'a1:t3',
        model: 'test-model',
        input_tokens: 100,
        output_tokens: 50,
        total_tokens: 150,
        cost: null,
        country: 'ID',
        status: 'completed',
        created_at: '2026-07-08T10:00:00Z',
      },
      {
        id: 2,
        thread_id: 'u1:t2',
        model: 'test-model',
        input_tokens: 100,
        output_tokens: 50,
        total_tokens: 150,
        cost: null,
        country: 'US',
        status: 'failed',
        created_at: '2026-07-06T10:00:00Z',
      },
      {
        id: 1,
        thread_id: 'u1:t1',
        model: null,
        input_tokens: 100,
        output_tokens: 50,
        total_tokens: 150,
        cost: null,
        country: null,
        status: 'cancelled',
        created_at: '2026-07-05T10:00:00Z',
      },
    ],
    total: 3,
    page: 1,
    page_size: 10,
    pages: 1,
    ...overrides,
  }
}

describe('UsageTab.vue', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
    vi.clearAllMocks()
    const auth = useAuthStore()
    auth.token = 'jwt'
    const agents = useAgentsStore()
    agents.current = { ...AGENT }
    vi.mocked(api.getUsage).mockResolvedValue(fixture())
  })

  async function mountTab() {
    const wrapper = mount(UsageTab)
    await flushPromises()
    return wrapper
  }

  it('renders headline stats and the two Chart.js charts', async () => {
    const wrapper = await mountTab()
    expect(wrapper.text()).toContain('Requests')
    expect(wrapper.text()).toContain('300')
    expect(wrapper.text()).toContain('150')
    // two chart stubs: requests (1 dataset) + tokens (2 datasets)
    const charts = wrapper.findAll('.chartjs-bar')
    expect(charts).toHaveLength(2)
    const datasets = charts.map((c) => JSON.parse(c.attributes('data-datasets') ?? '[]'))
    expect(datasets[0]).toHaveLength(1)
    expect(datasets[0][0].label).toBe('Requests')
    expect(datasets[1]).toHaveLength(2)
    expect(datasets[1].map((d: { label: string }) => d.label)).toEqual(['Input', 'Output'])
    const labels = JSON.parse(charts[0]!.attributes('data-labels') ?? '[]')
    expect(labels).toHaveLength(3)
    // the tokens legend is HTML (outside the canvas) so both plot areas stay equal
    const legendItems = wrapper.findAll('.legend-item')
    expect(legendItems.map((i) => i.text())).toEqual(['Input', 'Output'])
    // y-axis max is pinned to each chart's tallest bar (requests = value,
    // tokens = Input+Output stacked sum), keeping the plots aligned
    const opts = charts.map((c) => JSON.parse(c.attributes('data-options') ?? '{}'))
    expect(opts[0].scales.y.max).toBe(2) // max requests in the fixture
    expect(opts[0].scales.y.stacked).toBe(true)
    expect(opts[1].scales.y.max).toBe(300) // max Input+Output per day (200+100)
  })

  it('renders the paginated history list', async () => {
    const wrapper = await mountTab()
    const rows = wrapper.findAll('tbody tr')
    expect(rows).toHaveLength(3)
    expect(wrapper.text()).toContain('Completed')
    expect(wrapper.text()).toContain('Failed')
    expect(wrapper.text()).toContain('Cancelled')
  })

  it('shows the client country per request and a ranked top-countries list', async () => {
    const wrapper = await mountTab()
    // ranked list: rank, flag, name, bar, count, percentage of all requests
    const rows = wrapper.findAll('.usage-country-row')
    expect(rows).toHaveLength(2)
    expect(rows[0]!.text()).toContain('1')
    expect(rows[0]!.text()).toContain('🇮🇩')
    expect(rows[0]!.text()).toContain('Indonesia')
    expect(rows[0]!.text()).toContain('2')
    expect(rows[0]!.text()).toContain('67%') // 2 of 3 requests
    expect(rows[1]!.text()).toContain('🇺🇸')
    expect(rows[1]!.text()).toContain('United States')
    expect(rows[1]!.text()).toContain('33%') // 1 of 3 requests
    // bar width reflects the share
    const fill = rows[0]!.find('.usage-country-bar-fill')
    expect(fill!.attributes('style')).toContain('width: 67%')
    // history rows carry country (or a dash when unknown)
    const countryCells = wrapper.findAll('tbody .usage-country')
    expect(countryCells[0]!.text()).toContain('🇮🇩')
    expect(countryCells[1]!.text()).toContain('🇺🇸')
    expect(countryCells[2]!.text()).toContain('—')
  })

  it('refetches with the new page when navigating pagination', async () => {
    vi.mocked(api.getUsage).mockResolvedValue(
      fixture({
        items: [
          {
            id: 1,
            thread_id: 'u1:t1',
            model: null,
            input_tokens: 100,
            output_tokens: 50,
            total_tokens: 150,
            cost: null,
            country: null,
            status: 'completed',
            created_at: '2026-07-05T10:00:00Z',
          },
        ],
        total: 3,
        page: 2,
        page_size: 2,
        pages: 2,
      }),
    )
    const wrapper = await mountTab()
    vi.mocked(api.getUsage).mockClear()
    vi.mocked(api.getUsage).mockResolvedValue(
      fixture({
        items: [],
        total: 3,
        page: 2,
        page_size: 2,
        pages: 2,
      }),
    )

    const next = wrapper.findAll('button').find((b) => b.text() === 'Next →')
    expect(next).toBeTruthy()
    await next!.trigger('click')
    await flushPromises()

    expect(vi.mocked(api.getUsage)).toHaveBeenCalledTimes(1)
    expect(vi.mocked(api.getUsage).mock.calls[0]![2]).toMatchObject({ page: 2 })
    expect(wrapper.text()).toContain('Page 2 of 2')
  })

  it('shows the empty state when there is no usage yet', async () => {
    vi.mocked(api.getUsage).mockResolvedValue(
      fixture({
        summary: {
          total_requests: 0,
          total_input_tokens: 0,
          total_output_tokens: 0,
          total_tokens: 0,
          series: [{ date: '2026-07-06', requests: 0, input_tokens: 0, output_tokens: 0 }],
          countries: [],
        },
        items: [],
        total: 0,
        page: 1,
        page_size: 10,
        pages: 1,
      }),
    )
    const wrapper = await mountTab()
    expect(wrapper.text()).toContain('No usage yet')
    expect(wrapper.findAll('tbody tr')).toHaveLength(0)
  })

  it('switching the days window refetches with the new window', async () => {
    const wrapper = await mountTab()
    vi.mocked(api.getUsage).mockClear()
    vi.mocked(api.getUsage).mockResolvedValue(fixture())

    const btn7 = wrapper.findAll('button').find((b) => b.text() === '7d')
    expect(btn7).toBeTruthy()
    await btn7!.trigger('click')
    await flushPromises()

    expect(vi.mocked(api.getUsage).mock.calls[0]![2]).toMatchObject({ days: 7, page: 1 })
  })
})
