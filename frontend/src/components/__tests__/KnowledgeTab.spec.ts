import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'

vi.mock('@/api/client', () => ({
  api: {
    listSources: vi.fn<(token: string, agentId: number) => Promise<Source[]>>(),
    addSources: vi.fn<(token: string, agentId: number, urls: string[]) => Promise<Source[]>>(),
    addTextSource: vi.fn<
      (token: string, agentId: number, data: { title?: string; content: string }) => Promise<Source>
    >(),
    uploadSourceFiles: vi.fn<(token: string, agentId: number, files: File[]) => Promise<Source[]>>(),
    deleteSource: vi.fn<(token: string, agentId: number, sourceId: number) => Promise<void>>(),
    getSourceFile: vi.fn<(token: string, agentId: number, sourceId: number) => Promise<Blob>>(),
    reindexSources: vi.fn<
      (token: string, agentId: number, onlyFailed?: boolean) => Promise<{ scheduled: number }>
    >(),
  },
  ApiError: class ApiError extends Error {},
  getStoredToken: () => '',
  API_BASE: 'http://localhost:8000',
}))

import { api } from '@/api/client'
import type { Agent, Source } from '@/api/types'
import KnowledgeTab from '@/components/KnowledgeTab.vue'
import { useAgentsStore } from '@/stores/agents'
import { useAuthStore } from '@/stores/auth'

const AGENT: Agent = {
  id: 1,
  user_id: 1,
  name: 'Bot',
  description: '',
  system_prompt: null,
  welcome_message: 'hi',
  theme_color: '#4f46e5',
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

function source(overrides: Partial<Source>): Source {
  return {
    id: 1,
    agent_id: 1,
    url: '',
    kind: 'url',
    file_name: null,
    file_size: null,
    status: 'ready',
    title: 'Docs',
    error: null,
    chunk_count: 3,
    created_at: '',
    updated_at: '',
    ...overrides,
  }
}

function mountTab(sources: Source[]) {
  setActivePinia(createPinia())
  useAuthStore().token = 'jwt'
  const store = useAgentsStore()
  store.current = { ...AGENT }
  store.sources = sources
  const wrapper = mount(KnowledgeTab)
  return { wrapper, store }
}

function refreshButton(wrapper: ReturnType<typeof mount>) {
  return wrapper.findAll('button').find((b) => b.text().includes('Refresh'))
}

describe('KnowledgeTab sources list', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
    vi.mocked(api.listSources).mockResolvedValue([])
  })

  it('keeps the Refresh button clickable when all sources are idle/ready', async () => {
    // onMounted reloads the list; resolve with the same idle source so the
    // sources card (and its Refresh button) stays rendered.
    vi.mocked(api.listSources).mockResolvedValue([source({})])
    const { wrapper } = mountTab([source({})])
    await flushPromises()

    const btn = refreshButton(wrapper)
    expect(btn).toBeDefined()
    // Regression: the button used to be :disabled="!hasRunning", freezing it
    // once no source was pending/fetching/indexing — so manual refresh was
    // impossible in the normal steady state.
    expect(btn!.attributes('disabled')).toBeUndefined()
    expect(btn!.text()).toContain('Refresh')

    await btn!.trigger('click')
    await flushPromises()
    expect(api.listSources).toHaveBeenCalledWith('jwt', 1)
  })

  it('shows busy feedback on the Refresh button while the fetch is in flight', async () => {
    let resolveFetch!: (v: Source[]) => void
    vi.mocked(api.listSources).mockReturnValue(new Promise((r) => (resolveFetch = r)))
    const { wrapper } = mountTab([source({})])
    await flushPromises()

    const btn = refreshButton(wrapper)!
    await btn.trigger('click')
    await flushPromises()
    expect(btn.attributes('disabled')).toBeDefined()
    expect(btn.html()).toContain('spinner')

    resolveFetch([source({})])
    await flushPromises()
    expect(btn.attributes('disabled')).toBeUndefined()
  })

  it('shows an error box when the manual refresh fails', async () => {
    vi.mocked(api.listSources).mockRejectedValue(new Error('boom'))
    const { wrapper } = mountTab([source({})])
    await flushPromises()

    const btn = refreshButton(wrapper)!
    await btn.trigger('click')
    await flushPromises()

    expect(wrapper.find('.error-box').text()).toContain('boom')
  })
})
