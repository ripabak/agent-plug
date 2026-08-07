import { describe, expect, it } from 'vitest'
import { PERSONA_TEMPLATES, findPersonaTemplate } from '@/utils/personaTemplates'

describe('personaTemplates', () => {
  it('has unique ids and non-empty labels', () => {
    const ids = PERSONA_TEMPLATES.map((t) => t.id)
    expect(new Set(ids).size).toBe(ids.length)
    for (const t of PERSONA_TEMPLATES) {
      expect(t.label.length).toBeGreaterThan(0)
      expect(t.description.length).toBeGreaterThan(0)
      expect(t.prompt.trim().length).toBeGreaterThan(0)
      expect(t.emoji.length).toBeGreaterThan(0)
    }
  })

  it('includes the requested personas (Gen Z, friendly, supportive, professional)', () => {
    const labels = PERSONA_TEMPLATES.map((t) => t.label.toLowerCase())
    expect(labels).toContain('gen z')
    expect(labels).toContain('friendly')
    expect(labels).toContain('supportive')
    expect(labels).toContain('professional')
  })

  it('findPersonaTemplate matches a template prompt back to its template', () => {
    const t = PERSONA_TEMPLATES[0]!
    expect(findPersonaTemplate(t.prompt)?.id).toBe(t.id)
  })

  it('findPersonaTemplate returns undefined for empty/unknown prompts', () => {
    expect(findPersonaTemplate(null)).toBeUndefined()
    expect(findPersonaTemplate('')).toBeUndefined()
    expect(findPersonaTemplate('custom text that is not a template')).toBeUndefined()
  })
})
