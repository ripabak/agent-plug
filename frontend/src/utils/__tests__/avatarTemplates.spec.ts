import { describe, expect, it } from 'vitest'

import { AVATAR_TEMPLATES } from '../avatarTemplates'

describe('avatar GIF templates', () => {
  it('exposes a non-empty, well-formed template list', () => {
    expect(AVATAR_TEMPLATES.length).toBeGreaterThan(0)
    for (const t of AVATAR_TEMPLATES) {
      expect(t.id).toBeTruthy()
      expect(t.label).toBeTruthy()
      expect(t.url).toMatch(/^\/avatars\/templates\/.+\.gif$/)
    }
  })

  it('has unique ids and urls', () => {
    const ids = AVATAR_TEMPLATES.map((t) => t.id)
    const urls = AVATAR_TEMPLATES.map((t) => t.url)
    expect(new Set(ids).size).toBe(ids.length)
    expect(new Set(urls).size).toBe(urls.length)
  })
})
