import { describe, expect, it } from 'vitest'

import { AVATAR_MAX_SIZE, validateAvatarFile } from '../avatar'

describe('validateAvatarFile', () => {
  it('accepts gif/jpeg/png/webp within the size limit', () => {
    for (const type of ['image/gif', 'image/jpeg', 'image/png', 'image/webp']) {
      const file = new File(['x'], 'avatar.' + type.split('/')[1], { type })
      expect(validateAvatarFile(file)).toEqual({ ok: true })
    }
  })

  it('rejects unsupported image types', () => {
    const file = new File(['x'], 'anim.tiff', { type: 'image/tiff' })
    expect(validateAvatarFile(file).ok).toBe(false)
    expect(validateAvatarFile(file).error).toContain('GIF, PNG or JPG')
  })

  it('falls back to the extension when the MIME type is empty', () => {
    for (const name of ['logo.png', 'logo.jpg', 'logo.gif', 'logo.webp', 'logo.JPEG']) {
      const file = new File(['x'], name, { type: '' })
      expect(validateAvatarFile(file)).toEqual({ ok: true })
    }
  })

  it('rejects an empty MIME type with an unknown extension', () => {
    const file = new File(['x'], 'photo.bmp', { type: '' })
    expect(validateAvatarFile(file).ok).toBe(false)
  })

  it('rejects oversized files', () => {
    // File.size is read-only; construct a real blob of the right size.
    const big = new Blob([new Uint8Array(AVATAR_MAX_SIZE + 1)], { type: 'image/png' })
    const file = new File([big], 'big.png', { type: 'image/png' })
    expect(validateAvatarFile(file).ok).toBe(false)
    expect(validateAvatarFile(file).error).toContain('5MB')
  })

  it('accepts a file exactly at the size limit', () => {
    const exact = new Blob([new Uint8Array(AVATAR_MAX_SIZE)], { type: 'image/png' })
    expect(validateAvatarFile(new File([exact], 'ok.png', { type: 'image/png' }))).toEqual({
      ok: true,
    })
  })
})
