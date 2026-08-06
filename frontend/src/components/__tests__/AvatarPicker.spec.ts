import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'

import AvatarPicker from '../AvatarPicker.vue'

describe('AvatarPicker', () => {
  it('renders the preset emoji options', () => {
    const wrapper = mount(AvatarPicker, { props: { modelValue: '🤖' } })
    expect(wrapper.findAll('.avatar-option').length).toBeGreaterThanOrEqual(16)
  })

  it('highlights the current value as active', () => {
    const wrapper = mount(AvatarPicker, { props: { modelValue: '🚀' } })
    expect(wrapper.find('.avatar-option.active').text()).toBe('🚀')
  })

  it('emits update:modelValue with the clicked emoji', async () => {
    const wrapper = mount(AvatarPicker, { props: { modelValue: '🤖' } })
    await wrapper.findAll('.avatar-option')[1]!.trigger('click')
    expect(wrapper.emitted('update:modelValue')![0]).toEqual(['🦾'])
  })

  it('keeps a legacy custom emoji visible and selected', () => {
    const wrapper = mount(AvatarPicker, { props: { modelValue: '👾' } })
    const active = wrapper.find('.avatar-option.active')
    expect(active.exists()).toBe(true)
    expect(active.text()).toBe('👾')
  })
})
