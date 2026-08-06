import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'

import StatusBadge from '../StatusBadge.vue'
import type { SourceStatus } from '@/api/types'

describe('StatusBadge', () => {
  it.each<[SourceStatus, string]>([
    ['pending', 'Queued'],
    ['fetching', 'Fetching'],
    ['indexing', 'Indexing'],
    ['ready', 'Ready'],
    ['failed', 'Failed'],
  ])('renders label for status %s', (status, label) => {
    const wrapper = mount(StatusBadge, { props: { status } })
    expect(wrapper.text()).toContain(label)
    expect(wrapper.classes()).toContain(`badge-${status}`)
  })

  it('shows a spinner for running states', () => {
    const wrapper = mount(StatusBadge, { props: { status: 'indexing' } })
    expect(wrapper.find('.spinner').exists()).toBe(true)
  })

  it('hides spinner for terminal states', () => {
    const wrapper = mount(StatusBadge, { props: { status: 'ready' } })
    expect(wrapper.find('.spinner').exists()).toBe(false)
  })
})
