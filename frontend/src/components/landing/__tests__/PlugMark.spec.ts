import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'

import PlugMark from '../PlugMark.vue'

describe('PlugMark', () => {
  it('renders an svg at the requested size', () => {
    const wrapper = mount(PlugMark, { props: { size: 32 } })
    const svg = wrapper.find('svg')
    expect(svg.exists()).toBe(true)
    expect(svg.attributes('width')).toBe('32')
    expect(svg.attributes('height')).toBe('32')
    expect(svg.attributes('aria-hidden')).toBe('true')
  })

  it('is announced when used non-decoratively', () => {
    const wrapper = mount(PlugMark, { props: { decorative: false } })
    const svg = wrapper.find('svg')
    expect(svg.attributes('aria-hidden')).toBeUndefined()
    expect(svg.attributes('role')).toBe('img')
  })
})
