import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'

import WidgetMock from '../WidgetMock.vue'

describe('WidgetMock', () => {
  beforeEach(() => {
    // jsdom has no matchMedia; simulate prefers-reduced-motion so the
    // scripted conversation renders instantly instead of using real timers.
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: vi.fn<() => { matches: boolean }>().mockReturnValue({ matches: true }),
    })
  })

  it('renders the widget chrome (header, name, toolbar)', () => {
    const wrapper = mount(WidgetMock, { props: { mode: 'brief' } })
    expect(wrapper.find('.lp-widget').exists()).toBe(true)
    expect(wrapper.find('.lp-widget-name').text()).toBe('Senja Coffee')
    expect(wrapper.find('.lp-widget-toolbar').exists()).toBe(true)
  })

  it('plays the full conversation instantly under reduced motion', async () => {
    const wrapper = mount(WidgetMock, { props: { mode: 'full' } })
    // the conversation is scheduled in onMounted; flush the reactive update
    await nextTick()
    const bubbles = wrapper.findAll('.lp-wm-bubble')
    // full plan: 2 user + 2 bot + 2 thinking + 1 tool chip + 1 sources block
    expect(bubbles.length).toBe(4)
    expect(wrapper.findAll('.lp-wm-think').length).toBe(2)
    expect(wrapper.findAll('.lp-wm-tool').length).toBe(1)
    expect(wrapper.findAll('.lp-wm-sources').length).toBe(1)
    expect(bubbles.some((b) => b.text().includes('gluten-free'))).toBe(true)
  })
})
