import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'

import ColorPreview from '../ColorPreview.vue'
import { defaultTheme, type ChatTheme } from '@/utils/themes'

function themeWith(patch: Partial<ChatTheme>): ChatTheme {
  return { ...defaultTheme(), ...patch }
}

describe('ColorPreview', () => {
  it('renders the header mockup with the header tokens', () => {
    const theme = themeWith({ headerBg: '#112233', headerText: '#ffffff' })
    const wrapper = mount(ColorPreview, { props: { kind: 'header', theme } })
    expect(wrapper.find('.cvp-header').exists()).toBe(true)
    const header = wrapper.find('.cvp-header')
    // jsdom normalizes hex → rgb
    expect(header.attributes('style')).toContain('background: rgb(17, 34, 51)')
    expect(header.attributes('style')).toContain('color: rgb(255, 255, 255)')
    expect(header.find('.cvp-avatar').exists()).toBe(true)
  })

  it('renders the AI bubble mockup with its own tokens', () => {
    const theme = themeWith({
      aiBubbleBg: '#f0f0f0',
      aiBubbleText: '#101010',
      aiBubbleBorder: '#dddddd',
    })
    const wrapper = mount(ColorPreview, { props: { kind: 'aiBubble', theme } })
    const bubble = wrapper.find('.cvp-bubble')
    expect(bubble.classes()).toContain('cvp-left')
    expect(bubble.attributes('style')).toContain('background: rgb(240, 240, 240)')
    expect(bubble.attributes('style')).toContain('border-color: rgb(221, 221, 221)')
  })

  it('renders the user bubble on the right with user tokens', () => {
    const theme = themeWith({ userBubbleBg: '#4f46e5', userBubbleText: '#ffffff' })
    const wrapper = mount(ColorPreview, { props: { kind: 'userBubble', theme } })
    const bubble = wrapper.find('.cvp-bubble')
    expect(bubble.classes()).toContain('cvp-right')
    expect(bubble.attributes('style')).toContain('background: rgb(79, 70, 229)')
  })

  it('renders the toolbar mockup with input + send button tokens', () => {
    const theme = themeWith({ btnBg: '#059669', btnText: '#ffffff', inputBg: '#ffffff' })
    const wrapper = mount(ColorPreview, { props: { kind: 'toolbar', theme } })
    expect(wrapper.find('.cvp-toolbar').exists()).toBe(true)
    const send = wrapper.find('.cvp-send')
    expect(send.attributes('style')).toContain('background: rgb(5, 150, 105)')
    expect(send.text()).toBe('Send')
    expect(wrapper.find('.cvp-input').attributes('style')).toContain(
      'background: rgb(255, 255, 255)',
    )
  })

  it('renders the thinking and tools mockups with their tokens', () => {
    const thinking = themeWith({ thinkingBg: '#f6f7f9', thinkingText: '#6b7280' })
    const tw = mount(ColorPreview, { props: { kind: 'thinking', theme: thinking } })
    expect(tw.find('.cvp-think').attributes('style')).toContain('background: rgb(246, 247, 249)')
    // thinking label is plain text (no brain emoji)
    expect(tw.find('.cvp-think-label').text()).toBe('Reasoning')

    const tools = themeWith({
      toolSuccessBg: '#f0fdf4',
      toolErrorBg: '#fef2f2',
    })
    const ow = mount(ColorPreview, { props: { kind: 'tools', theme: tools } })
    // chips are plain pills, not wrapped in a chat bubble
    expect(ow.find('.cvp-tools').attributes('style')).toBeUndefined()
    // success + error chips, each referencing its own tokens
    const chips = ow.findAll('.cvp-tool')
    expect(chips.length).toBe(2)
    expect(chips[0]!.text()).toContain('search_knowledge_base')
    expect(chips[0]!.attributes('style')).toContain('background: rgb(240, 253, 244)') // toolSuccessBg
    expect(chips[1]!.text()).toContain('fetch_page')
    expect(chips[1]!.attributes('style')).toContain('background: rgb(254, 242, 242)') // toolErrorBg
  })
})
