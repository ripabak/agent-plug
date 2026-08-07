/** Country display helpers (ISO alpha-2 code -> flag emoji / English name). */

const regionNames = new Intl.DisplayNames(['en'], { type: 'region' })

/** 'ID' -> '🇮🇩' (flag emoji from the ISO alpha-2 code). */
export function countryFlag(code: string): string {
  return code.toUpperCase().replace(/./g, (c) => String.fromCodePoint(127397 + c.charCodeAt(0)))
}

/** 'ID' -> 'Indonesia' (built-in Intl, no lookup table needed). */
export function countryName(code: string): string {
  try {
    return regionNames.of(code) ?? code
  } catch {
    return code
  }
}
