import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { useAgentsStore } from '../agents'
import { useAuthStore } from '../auth'
import type { Agent } from '@/api/types'

vi.mock('@/api/client', () => ({
  api: {
    listAgents: vi.fn<(token: string) => Promise<Agent[]>>(),
    getAgent: vi.fn<(token: string, id: number) => Promise<Agent>>(),
    createAgent: vi.fn<(token: string, data: Partial<Agent>) => Promise<Agent>>(),
    updateAgent: vi.fn<(token: string, id: number, data: Partial<Agent>) => Promise<Agent>>(),
    deleteAgent: vi.fn<(token: string, id: number) => Promise<void>>(),
    regenerateToken: vi.fn<(token: string, id: number) => Promise<Agent>>(),
    uploadAgentAvatar: vi.fn<
      (token: string, id: number, file: File, kind: 'photo' | 'template') => Promise<Agent>
    >(),
    deleteAgentAvatar: vi.fn<(token: string, id: number) => Promise<Agent>>(),
    listSources: vi.fn<(token: string, agentId: number) => Promise<never[]>>(),
    addSources: vi.fn<(token: string, agentId: number, urls: string[]) => Promise<never[]>>(),
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

const AGENT: Agent = {
  id: 1,
  user_id: 1,
  name: 'Support Bot',
  description: '',
  system_prompt: null,
  welcome_message: 'Hi!',
  theme_color: '#4f46e5',
  avatar_emoji: '🤖',
  avatar_url: null,
  avatar_kind: 'photo',
  chat_theme: '',
  show_thinking: true,
  show_tools: true,
  public_token: 'tok-old',
  created_at: 'now',
  updated_at: 'now',
}

describe('agents store', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('regenerateToken rotates the public token on the current agent', async () => {
    useAuthStore().token = 'jwt'
    const store = useAgentsStore()
    store.current = { ...AGENT }

    vi.mocked(api.regenerateToken).mockResolvedValue({ ...AGENT, public_token: 'tok-new' })
    await store.regenerateToken()

    expect(api.regenerateToken).toHaveBeenCalledWith('jwt', 1)
    expect(store.current?.public_token).toBe('tok-new')
  })

  it('regenerateToken is a no-op without a current agent', async () => {
    useAuthStore().token = 'jwt'
    const store = useAgentsStore()
    await store.regenerateToken()
    expect(api.regenerateToken).not.toHaveBeenCalled()
  })

  it('uploadAvatar replaces the current agent avatar', async () => {
    useAuthStore().token = 'jwt'
    const store = useAgentsStore()
    store.current = { ...AGENT }
    const file = new File(['x'], 'logo.png', { type: 'image/png' })

    vi.mocked(api.uploadAgentAvatar).mockResolvedValue({
      ...AGENT,
      avatar_url: 'http://localhost:8000/api/public/agents/1/avatar',
    })
    await store.uploadAvatar(file, 'template')

    expect(api.uploadAgentAvatar).toHaveBeenCalledWith('jwt', 1, file, 'template')
    expect(store.current?.avatar_url).toContain('/api/public/agents/1/avatar')
  })

  it('removeAvatar clears the avatar URL', async () => {
    useAuthStore().token = 'jwt'
    const store = useAgentsStore()
    store.current = { ...AGENT, avatar_url: 'http://localhost:8000/api/public/agents/1/avatar' }

    vi.mocked(api.deleteAgentAvatar).mockResolvedValue({ ...AGENT, avatar_url: null })
    await store.removeAvatar()

    expect(api.deleteAgentAvatar).toHaveBeenCalledWith('jwt', 1)
    expect(store.current?.avatar_url).toBeNull()
  })
})
