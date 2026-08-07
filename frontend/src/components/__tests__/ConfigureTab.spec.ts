import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn<() => void>() }),
}))

vi.mock('@/api/client', () => ({
  api: {
    updateAgent: vi.fn<(token: string, id: number, data: Partial<Agent>) => Promise<Agent>>(),
    regenerateToken: vi.fn<(token: string, id: number) => Promise<Agent>>(),
    deleteAgent: vi.fn<(token: string, id: number) => Promise<void>>(),
    uploadAgentAvatar:
      vi.fn<
        (token: string, id: number, file: File, kind: 'photo' | 'template') => Promise<Agent>
      >(),
    deleteAgentAvatar: vi.fn<(token: string, id: number) => Promise<Agent>>(),
  },
  ApiError: class ApiError extends Error {},
  getStoredToken: () => '',
  API_BASE: 'http://localhost:8000',
}))

import { api } from '@/api/client'
import type { Agent } from '@/api/types'
import ConfigureTab from '@/components/ConfigureTab.vue'
import { PERSONA_TEMPLATES } from '@/utils/personaTemplates'
import { useAgentsStore } from '@/stores/agents'
import { useAuthStore } from '@/stores/auth'

const AGENT: Agent = {
  id: 1,
  user_id: 1,
  name: 'Bot',
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

function mountTab(current: Agent) {
  setActivePinia(createPinia())
  useAuthStore().token = 'jwt'
  const store = useAgentsStore()
  store.current = { ...current }
  return { wrapper: mount(ConfigureTab), store }
}

/** The "Save changes" button (the first generic `.btn` is the upload-photo one). */
function saveButton(wrapper: ReturnType<typeof mount>) {
  const btn = wrapper.findAll('button').find((b) => b.text().includes('Save changes'))
  if (!btn) throw new Error('Save changes button not found')
  return btn
}

describe('ConfigureTab avatar photo/emoji exclusivity', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('emoji picker is enabled when no photo is set', () => {
    const { wrapper } = mountTab(AGENT)
    const options = wrapper.findAll('.avatar-option')
    expect(options.length).toBeGreaterThan(0)
    expect(options.every((o) => o.attributes('disabled') === undefined)).toBe(true)
    expect(wrapper.text()).toContain('Upload photo')
  })

  it('emoji picker is disabled while a photo is set', () => {
    const { wrapper } = mountTab({ ...AGENT, avatar_url: 'http://x/agents/1/avatar' })
    expect(wrapper.find('img.agent-avatar').attributes('src')).toBe('http://x/agents/1/avatar')
    expect(wrapper.text()).toContain('Replace photo')
    const options = wrapper.findAll('.avatar-option')
    expect(options.length).toBeGreaterThan(0)
    expect(options.every((o) => o.attributes('disabled') !== undefined)).toBe(true)
  })

  it('rejects an unsupported file type client-side without calling the api', async () => {
    const { wrapper } = mountTab(AGENT)
    const input = wrapper.find('input[type="file"]')
    const file = new File(['x'], 'anim.tiff', { type: 'image/tiff' })
    Object.defineProperty(input.element, 'files', { value: [file] })
    await input.trigger('change')
    await flushPromises()
    expect(api.uploadAgentAvatar).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('Only GIF, PNG or JPG')
  })

  it('uploads a picked file with kind photo', async () => {
    const { wrapper, store } = mountTab(AGENT)
    vi.mocked(api.uploadAgentAvatar).mockResolvedValue({
      ...AGENT,
      avatar_url: 'http://x/agents/1/avatar',
    })
    const input = wrapper.find('input[type="file"]')
    const file = new File(['x'], 'logo.png', { type: 'image/png' })
    Object.defineProperty(input.element, 'files', { value: [file] })
    await input.trigger('change')
    await flushPromises()
    const call = vi.mocked(api.uploadAgentAvatar).mock.calls[0]!
    expect(call.slice(0, 3)).toEqual(['jwt', 1, file])
    expect(call[3]).toBe('photo')
    expect(store.current?.avatar_url).toBe('http://x/agents/1/avatar')
  })

  it('applies a GIF template by fetching it and uploading as image/gif', async () => {
    const { wrapper } = mountTab(AGENT)
    globalThis.fetch = vi.fn<typeof fetch>().mockResolvedValue({
      ok: true,
      blob: async () => new Blob(['gif-bytes'], { type: 'image/gif' }),
    } as Response)
    vi.mocked(api.uploadAgentAvatar).mockResolvedValue({
      ...AGENT,
      avatar_url: 'http://x/agents/1/avatar',
    })

    await wrapper.find('.avatar-template').trigger('click')
    await flushPromises()

    expect(globalThis.fetch).toHaveBeenCalledWith('/avatars/templates/rocket.gif')
    const [token, id, file, kind] = vi.mocked(api.uploadAgentAvatar).mock.calls[0]!
    expect([token, id]).toEqual(['jwt', 1])
    expect(file.type).toBe('image/gif')
    expect(file.name).toBe('rocket.gif')
    expect(kind).toBe('template')
  })

  it('removing the photo re-enables the emoji picker', async () => {
    const { wrapper } = mountTab({ ...AGENT, avatar_url: 'http://x/agents/1/avatar' })
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    vi.mocked(api.deleteAgentAvatar).mockResolvedValue({ ...AGENT, avatar_url: null })
    await wrapper.find('.btn-danger').trigger('click')
    await flushPromises()
    expect(api.deleteAgentAvatar).toHaveBeenCalledWith('jwt', 1)
    expect(
      wrapper.findAll('.avatar-option').every((o) => o.attributes('disabled') === undefined),
    ).toBe(true)
    vi.restoreAllMocks()
  })
})

describe('ConfigureTab agent personality (persona)', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('renders every persona template chip', () => {
    const { wrapper } = mountTab(AGENT)
    const chips = wrapper.findAll('.persona-template')
    expect(chips.length).toBe(PERSONA_TEMPLATES.length)
    expect(wrapper.find('#c-persona').exists()).toBe(true)
  })

  it('selecting a template fills the textarea and highlights the chip', async () => {
    const { wrapper } = mountTab(AGENT)
    const t = PERSONA_TEMPLATES[0]!
    await wrapper.findAll('.persona-template')[0]!.trigger('click')
    const ta = wrapper.find('#c-persona').element as HTMLTextAreaElement
    expect(ta.value).toBe(t.prompt)
    expect(wrapper.findAll('.persona-template')[0]!.classes()).toContain('active')
  })

  it('editing the textarea by hand clears the active chip', async () => {
    const { wrapper } = mountTab(AGENT)
    await wrapper.findAll('.persona-template')[0]!.trigger('click')
    const ta = wrapper.find('#c-persona')
    await ta.setValue('my custom persona')
    expect(wrapper.findAll('.persona-template').every((c) => !c.classes().includes('active'))).toBe(
      true,
    )
  })

  it('saves an empty persona as null', async () => {
    const { wrapper } = mountTab(AGENT)
    vi.mocked(api.updateAgent).mockResolvedValue({ ...AGENT, persona_prompt: null })
    await saveButton(wrapper).trigger('click')
    await flushPromises()
    expect(vi.mocked(api.updateAgent).mock.calls[0]![2].persona_prompt).toBeNull()
  })

  it('saves the selected template prompt as the persona', async () => {
    const { wrapper } = mountTab(AGENT)
    const t = PERSONA_TEMPLATES[2]!
    vi.mocked(api.updateAgent).mockResolvedValue({ ...AGENT, persona_prompt: t.prompt })
    await wrapper.findAll('.persona-template')[2]!.trigger('click')
    await saveButton(wrapper).trigger('click')
    await flushPromises()
    expect(vi.mocked(api.updateAgent).mock.calls[0]![2].persona_prompt).toBe(t.prompt)
  })

  it('restores a saved template persona as the active chip', () => {
    const t = PERSONA_TEMPLATES[1]!
    const { wrapper } = mountTab({ ...AGENT, persona_prompt: t.prompt })
    expect(wrapper.findAll('.persona-template')[1]!.classes()).toContain('active')
    expect((wrapper.find('#c-persona').element as HTMLTextAreaElement).value).toBe(t.prompt)
  })
})
