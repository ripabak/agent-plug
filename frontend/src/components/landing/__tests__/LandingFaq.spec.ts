import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'

import LandingFaq from '../LandingFaq.vue'

describe('LandingFaq', () => {
  it('renders every question and answer', () => {
    const wrapper = mount(LandingFaq)
    const buttons = wrapper.findAll('.lp-faq-q')
    expect(buttons.length).toBeGreaterThanOrEqual(6)
    expect(buttons[0]!.text()).toContain('What does my agent know?')
    // answers exist in the DOM (first item open by default)
    expect(wrapper.findAll('.lp-faq-a').length).toBe(buttons.length)
  })

  it('opens the first item by default and exposes it via aria-expanded', () => {
    const wrapper = mount(LandingFaq)
    const first = wrapper.find('.lp-faq-q')
    expect(first.attributes('aria-expanded')).toBe('true')
    expect(wrapper.find('.lp-faq-panel.open').exists()).toBe(true)
  })

  it('toggles an item open and closed on click', async () => {
    const wrapper = mount(LandingFaq)
    const buttons = wrapper.findAll('.lp-faq-q')

    // open the second item
    await buttons[1]!.trigger('click')
    expect(buttons[1]!.attributes('aria-expanded')).toBe('true')
    expect(wrapper.findAll('.lp-faq-panel.open').length).toBe(1)

    // closing the second item collapses everything again
    await buttons[1]!.trigger('click')
    expect(buttons[1]!.attributes('aria-expanded')).toBe('false')
    expect(wrapper.findAll('.lp-faq-panel.open').length).toBe(0)
  })
})
