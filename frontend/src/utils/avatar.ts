/** Client-side avatar (photo/logo) validation — mirrors backend limits. */

export const AVATAR_MAX_SIZE = 5 * 1024 * 1024 // 5 MB raw upload (backend default)
export const AVATAR_CONTENT_TYPES = ['image/gif', 'image/jpeg', 'image/png', 'image/webp']

/** Normalize the file type: trust the MIME type, fall back to the extension
 *  (some browsers/files report an empty `type` for common images). */
export function detectImageType(file: File): string {
  if (file.type) return file.type
  const ext = file.name.toLowerCase().split('.').pop() ?? ''
  if (ext === 'jpg' || ext === 'jpeg') return 'image/jpeg'
  if (ext === 'png') return 'image/png'
  if (ext === 'gif') return 'image/gif'
  if (ext === 'webp') return 'image/webp'
  return ''
}

export interface AvatarValidation {
  ok: boolean
  error?: string
}

/** Validate a picked file BEFORE uploading (type + size). */
export function validateAvatarFile(file: File): AvatarValidation {
  if (!AVATAR_CONTENT_TYPES.includes(detectImageType(file))) {
    return { ok: false, error: 'Only GIF, PNG or JPG images are supported.' }
  }
  if (file.size > AVATAR_MAX_SIZE) {
    return { ok: false, error: 'Image exceeds the 5MB limit.' }
  }
  return { ok: true }
}
