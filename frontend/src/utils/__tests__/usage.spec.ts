import { describe, expect, it } from 'vitest'

import { isPageUrl, pageLabel } from '../usage'

describe('pageLabel', () => {
  it('renders host + path for a valid URL', () => {
    expect(pageLabel('https://shop.example.com/items/42')).toBe('shop.example.com/items/42')
  })

  it('truncates long paths', () => {
    const long = 'https://example.com/' + 'a'.repeat(100)
    const label = pageLabel(long, 20)
    expect(label.startsWith('example.com/')).toBe(true)
    expect(label.endsWith('…')).toBe(true)
  })

  it('falls back to plain truncation for malformed values', () => {
    expect(pageLabel('not a url at all, just some long text here ok')).toMatch(/not a url/)
    expect(pageLabel('')).toBe('—')
    expect(pageLabel(null)).toBe('—')
    expect(pageLabel(undefined)).toBe('—')
  })
})

describe('isPageUrl', () => {
  it('accepts http(s) URLs only', () => {
    expect(isPageUrl('https://example.com/x')).toBe(true)
    expect(isPageUrl('http://example.com')).toBe(true)
    expect(isPageUrl('javascript:alert(1)')).toBe(false)
    expect(isPageUrl('ftp://example.com')).toBe(false)
    expect(isPageUrl('')).toBe(false)
    expect(isPageUrl(null)).toBe(false)
  })
})
