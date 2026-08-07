/** Helpers for rendering usage rows: where the widget was called from. */

/** Human-readable label for a usage page_url (host + truncated path). */
export function pageLabel(url: string | null | undefined, maxPath = 40): string {
  if (!url) return '—'
  try {
    const u = new URL(url)
    const path = u.pathname.length > maxPath ? u.pathname.slice(0, maxPath) + '…' : u.pathname
    return u.hostname + path
  } catch {
    return url.length > 60 ? url.slice(0, 60) + '…' : url
  }
}

/** True when the page_url is an openable http(s) link. */
export function isPageUrl(url: string | null | undefined): url is string {
  if (!url) return false
  try {
    return ['http:', 'https:'].includes(new URL(url).protocol)
  } catch {
    return false
  }
}
