import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia } from 'pinia'

import LandingView from '../LandingView.vue'

function mountLanding() {
  return mount(LandingView, {
    global: {
      plugins: [createPinia()],
      stubs: {
        RouterLink: { template: '<a><slot /></a>' },
        // the scripted widget conversation is covered by its own spec; stub
        // it here so the smoke test stays synchronous
        WidgetMock: { template: '<div class="stub-widget" />' },
      },
    },
  })
}

describe('LandingView', () => {
  it('renders the hero value proposition', () => {
    const wrapper = mountLanding()
    expect(wrapper.find('h1').text()).toContain('Install a friendly agent')
    expect(wrapper.find('.lp-hero-cta').text()).toContain('Start free')
    expect(wrapper.text()).toContain('Effortless answers for your visitors')
  })

  it('tells the scroll story: problem stats, solution, usage, tour, FAQ, CTA', () => {
    const wrapper = mountLanding()
    const text = wrapper.text()
    expect(text).toContain('70%')
    expect(text).toContain('Baymard Institute')
    expect(text).toContain('Curious visitors leave too soon')
    expect(text).toContain('An agent that already knows your business')
    expect(text).toContain('Know who\u2019s asking, and from where')
    expect(text).toContain('Live on your website in minutes')
    expect(text).toContain('Questions, answered.')
    expect(text).toContain("Visitors stay. Questions don't.")
  })

  it('renders all six tour steps with their screens', () => {
    const wrapper = mountLanding()
    const verbs = wrapper.findAll('.lp-step-verb').map((v) => v.text().trim())
    expect(verbs).toEqual(['Create', 'Teach', 'Style', 'Install', 'Done', 'Track'])
    // each step mounts its screen (create / knowledge / theme / embed / live / usage)
    expect(wrapper.findAll('.lp-win').length).toBe(5)
    expect(wrapper.find('.lp-browser').exists()).toBe(true)
  })

  it('closes the tour with the usage analytics step (dashboard mockup)', () => {
    const wrapper = mountLanding()
    const steps = wrapper.findAll('.lp-step')
    const last = steps[steps.length - 1]!
    expect(last.text()).toContain('Track')
    expect(last.text()).toContain('Know who\u2019s asking, and from where')
    expect(last.find('.lp-usage-win').exists()).toBe(true)
    expect(last.text()).toContain('Indonesia')
    expect(last.text()).toContain('United States')
  })

  it('renders every FAQ answer', () => {
    const wrapper = mountLanding()
    const answers = wrapper.findAll('.lp-faq-a')
    expect(answers.length).toBeGreaterThanOrEqual(6)
    expect(wrapper.text()).toContain('How long does setup take?')
  })
})
