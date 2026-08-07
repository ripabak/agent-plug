import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { useChatStore } from '../chat'
import type { Agent, TokenResponse, User } from '@/api/types'

vi.mock('@/api/client', () => ({
  api: {
    me: vi.fn<(token: string) => Promise<User>>(),
    login: vi.fn<(data: { email: string; password: string }) => Promise<TokenResponse>>(),
    register:
      vi.fn<
        (data: { email: string; display_name: string; password: string }) => Promise<TokenResponse>
      >(),
    updateAgent: vi.fn<() => Promise<never>>(),
  },
  ApiError: class ApiError extends Error {},
  getStoredToken: () => '',
  API_BASE: 'http://localhost:8000',
}))

const AGENT: Agent = {
  id: 1,
  user_id: 1,
  name: 'Bot',
  description: '',
  system_prompt: null,
  persona_prompt: null,
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

describe('chat display-config store', () => {
  beforeEach(() => {
    localStorage.clear()
    sessionStorage.clear()
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('initializes display config from the agent (server truth)', () => {
    const chat = useChatStore()
    chat.setSetting('showThinking', false)
    const agent = {
      ...AGENT,
      chat_theme: JSON.stringify({
        preset: 'slate',
        custom: { headerBg: '#123456' },
        touched: true,
      }),
      show_thinking: false,
      show_tools: true,
    }
    chat.initFromAgent(agent)
    expect(chat.settings.showThinking).toBe(false)
    expect(chat.settings.showTools).toBe(true)
    expect(chat.themePresetName).toBe('slate')
    expect(chat.themeColors.headerBg).toBe('#123456')
    expect(chat.themeColors.msgsBg).toBe('#1e293b') // slate preset value
  })

  it('sets several tokens at once (merged chip border+text + soft bg)', () => {
    const chat = useChatStore()
    chat.setThemeColors({
      toolSuccessBorder: '#16a34a',
      toolSuccessText: '#16a34a',
      toolSuccessBg: 'rgba(22, 163, 74, 0.12)',
    })
    expect(chat.themeColors.toolSuccessBorder).toBe('#16a34a')
    expect(chat.themeColors.toolSuccessText).toBe('#16a34a')
    expect(chat.themeColors.toolSuccessBg).toBe('rgba(22, 163, 74, 0.12)')
    expect(chat.themeCustomized).toBe(true)
    // untouched tokens keep the preset values
    expect(chat.themeColors.headerBg).toBe('#211f1b')
  })

  it('persists theme preset + custom color overrides across reloads', () => {
    const chat = useChatStore()
    chat.setThemePreset('emerald')
    expect(chat.themePresetName).toBe('emerald')
    expect(chat.themeColors.headerBg).toBe('#059669')

    // tweaking one token keeps the preset as the base
    chat.setThemeColor('headerBg', '#123456')
    expect(chat.themeCustomized).toBe(true)
    expect(chat.themeColors.headerBg).toBe('#123456')
    expect(chat.themeColors.userBubbleBg).toBe('#059669')

    // a "reload" (fresh pinia) reads the same state from localStorage
    setActivePinia(createPinia())
    const reloaded = useChatStore()
    expect(reloaded.themePresetName).toBe('emerald')
    expect(reloaded.themeColors.headerBg).toBe('#123456')

    reloaded.resetTheme()
    expect(reloaded.themeCustomized).toBe(false)
    expect(reloaded.themeColors.headerBg).toBe('#211f1b')
  })

  it('persists Show thinking/Show tools toggles across reloads', () => {
    const chat = useChatStore()
    chat.setSetting('showThinking', false)
    chat.setSetting('showTools', false)
    setActivePinia(createPinia())
    const reloaded = useChatStore()
    expect(reloaded.settings.showThinking).toBe(false)
    expect(reloaded.settings.showTools).toBe(false)
  })
})
