import { describe, expect, it } from 'vitest'
import { countryFlag, countryName } from '@/utils/country'

describe('country helpers', () => {
  it('maps an ISO alpha-2 code to a flag emoji (case-insensitive)', () => {
    expect(countryFlag('id')).toBe('🇮🇩')
    expect(countryFlag('US')).toBe('🇺🇸')
    expect(countryFlag('SG')).toBe('🇸🇬')
  })

  it('maps a code to its English region name', () => {
    expect(countryName('ID')).toBe('Indonesia')
    expect(countryName('US')).toBe('United States')
  })

  it('falls back to the raw code for unknown values', () => {
    expect(countryName('XX')).toBe('XX')
  })
})
