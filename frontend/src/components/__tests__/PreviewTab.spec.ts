import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'

vi.mock('@/api/client', () => ({
  api: {
    me: vi.fn<() => Promise<never>>(),
    login: vi.fn<() => Promise<never>>(),
    register: vi.fn<() => Promise<never>>(),
    updateAgent: vi.fn<() => Promise<never>>(),
  },
  ApiError: class ApiError extends Error {},
  getStoredToken: () => '',
  API_BASE: 'http://localhost:8000',
}))

import type { Agent } from '@/api/types'
import type { ChatTheme } from '@/utils/themes'
import { useAgentsStore } from '@/stores/agents'
import { useAuthStore } from '@/stores/auth'
import { useChatStore } from '@/stores/chat'
import PreviewTab from '@/components/PreviewTab.vue'

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

describe('PreviewTab floating widget preview', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
    useAuthStore().token = 'jwt'
    useAgentsStore().current = { ...AGENT }
    window.__apwWidgets = {}
  })

  it('injects the real widget script with agent + theme attrs (auto-open desktop)', () => {
    const wrapper = mount(PreviewTab)
    const s = wrapper.find('script[data-agent-id]')
    expect(s.exists()).toBe(true)
    expect(s.attributes('data-token')).toBe('tok')
    expect(s.attributes('data-base-url')).toBe('http://localhost:8000')
    expect(s.attributes('data-auto-open')).toBe('desktop')
    const theme = JSON.parse(s.attributes('data-theme') || '{}')
    expect(theme.msgsBg).toBe('#f6f7f9')
    expect(theme.aiBubbleBg).toBe('#ffffff')
    wrapper.unmount()
  })

  it('pushes theme changes live into the running widget via the bridge', async () => {
    const setTheme = vi.fn<(t: ChatTheme) => void>()
    const setOpts = vi.fn<(s: boolean, t: boolean) => void>()
    window.__apwWidgets = { '1': { setTheme, setOpts, destroy: vi.fn<() => void>() } }
    const wrapper = mount(PreviewTab)
    const chat = useChatStore()
    chat.setThemeColors({ msgsBg: '#ff0000' })
    await flushPromises()
    expect(setTheme).toHaveBeenCalledWith(expect.objectContaining({ msgsBg: '#ff0000' }))
    wrapper.unmount()
  })

  it('pushes show thinking/tools toggles into the running widget', async () => {
    const setOpts = vi.fn<(s: boolean, t: boolean) => void>()
    window.__apwWidgets = {
      '1': { setTheme: vi.fn<(t: ChatTheme) => void>(), setOpts, destroy: vi.fn<() => void>() },
    }
    const wrapper = mount(PreviewTab)
    const chat = useChatStore()
    chat.setSetting('showThinking', false)
    await flushPromises()
    expect(setOpts).toHaveBeenCalledWith(false, true)
    wrapper.unmount()
  })

  it('destroys the widget bridge on unmount', () => {
    const destroy = vi.fn<() => void>()
    window.__apwWidgets = {
      '1': {
        setTheme: vi.fn<(t: ChatTheme) => void>(),
        setOpts: vi.fn<(s: boolean, t: boolean) => void>(),
        destroy,
      },
    }
    const wrapper = mount(PreviewTab)
    wrapper.unmount()
    expect(destroy).toHaveBeenCalled()
  })

  it('re-injects the widget when switching agents', async () => {
    const wrapper = mount(PreviewTab)
    useAgentsStore().current = { ...AGENT, id: 2, public_token: 'tok2' }
    await flushPromises()
    const s = wrapper.find('script[data-agent-id="2"]')
    expect(s.exists()).toBe(true)
    expect(s.attributes('data-token')).toBe('tok2')
    wrapper.unmount()
  })
})
