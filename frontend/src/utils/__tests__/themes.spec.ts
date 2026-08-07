import { describe, expect, it } from 'vitest'

import {
  THEME_COLOR_KEYS,
  THEME_PRESETS,
  agentHeaderColor,
  applyThemeOverrides,
  cssVarName,
  defaultTheme,
  findPreset,
  softenColor,
  themeToCssVars,
} from '../themes'

const HEX = /^#[0-9a-fA-F]{6}$/

describe('chat themes', () => {
  it('defaultTheme covers every token with a valid hex color', () => {
    const t = defaultTheme()
    for (const key of THEME_COLOR_KEYS) {
      expect(HEX.test(t[key])).toBe(true)
    }
  })

  it('exposes at least 6 presets with unique names', () => {
    expect(THEME_PRESETS.length).toBeGreaterThanOrEqual(6)
    const names = new Set(THEME_PRESETS.map((p) => p.name))
    expect(names.size).toBe(THEME_PRESETS.length)
  })

  it('every preset covers the full token set with valid colors', () => {
    for (const p of THEME_PRESETS) {
      for (const key of THEME_COLOR_KEYS) {
        expect(HEX.test(p[key])).toBe(true)
      }
    }
  })

  it('monochrome is the default preset', () => {
    expect(THEME_PRESETS[0]?.name).toBe('monochrome')
    expect(THEME_PRESETS[0]?.label).toBe('Monochrome')
    expect(defaultTheme().headerBg).toBe('#211f1b')
  })

  it('findPreset locates presets by name and returns undefined otherwise', () => {
    expect(findPreset('emerald')?.headerBg).toBe('#059669')
    expect(findPreset('slate')?.msgsBg).toBe('#1e293b')
    expect(findPreset('nope')).toBeUndefined()
  })

  describe('agentHeaderColor', () => {
    it('falls back to theme_color when no theme is saved', () => {
      expect(agentHeaderColor({ theme_color: '#ff0000', chat_theme: '' })).toBe('#ff0000')
      expect(agentHeaderColor({ theme_color: '#ff0000', chat_theme: null })).toBe('#ff0000')
    })

    it('uses the saved preset header color once the theme is touched', () => {
      expect(
        agentHeaderColor({
          theme_color: '#ff0000',
          chat_theme: JSON.stringify({ preset: 'emerald', custom: {}, touched: true }),
        }),
      ).toBe('#059669')
    })

    it('lets a custom headerBg override the preset', () => {
      expect(
        agentHeaderColor({
          theme_color: '#ff0000',
          chat_theme: JSON.stringify({
            preset: 'emerald',
            custom: { headerBg: '#123456' },
            touched: true,
          }),
        }),
      ).toBe('#123456')
    })

    it('ignores an untouched theme and uses theme_color (reset state)', () => {
      expect(
        agentHeaderColor({
          theme_color: '#ff0000',
          chat_theme: JSON.stringify({ preset: 'monochrome', custom: {}, touched: false }),
        }),
      ).toBe('#ff0000')
    })

    it('tolerates malformed chat_theme', () => {
      expect(agentHeaderColor({ theme_color: '#ff0000', chat_theme: 'not-json{' })).toBe('#ff0000')
    })
  })

  it('applyThemeOverrides merges partial overrides on top of a base theme', () => {
    const t = applyThemeOverrides(defaultTheme(), { headerBg: '#ff0000', muted: '#999999' })
    expect(t.headerBg).toBe('#ff0000')
    expect(t.muted).toBe('#999999')
    // untouched tokens keep the base values
    expect(t.accent).toBe('#a9502a')
    expect(t.userBubbleBg).toBe('#211f1b')
  })

  it('themeToCssVars maps camelCase tokens to --chat-* variables', () => {
    const vars = themeToCssVars(defaultTheme())
    expect(vars['--chat-header-bg']).toBe('#211f1b')
    expect(vars['--chat-ai-bubble-text']).toBe('#211f1b')
    expect(vars['--chat-tool-success-border']).toBe('#cfe0cc')
    expect(Object.keys(vars).length).toBe(THEME_COLOR_KEYS.length)
  })

  it('cssVarName produces the kebab-case variable name', () => {
    expect(cssVarName('headerBg')).toBe('--chat-header-bg')
    expect(cssVarName('toolErrorBg')).toBe('--chat-tool-error-bg')
    expect(cssVarName('aiBubbleBorder')).toBe('--chat-ai-bubble-border')
  })

  it('softenColor derives a translucent rgba from a hex chip color', () => {
    expect(softenColor('#16a34a')).toBe('rgba(22, 163, 74, 0.12)')
    expect(softenColor('#16a34a', 0.2)).toBe('rgba(22, 163, 74, 0.2)')
    // 3-digit hex shorthand
    expect(softenColor('#abc')).toBe('rgba(170, 187, 204, 0.12)')
    // invalid input passes through unchanged
    expect(softenColor('nope')).toBe('nope')
  })
})
