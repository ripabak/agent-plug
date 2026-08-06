import { afterEach, describe, expect, it, vi } from 'vitest'

import { api } from '../client'

const originalFetch = globalThis.fetch

afterEach(() => {
  globalThis.fetch = originalFetch
  vi.restoreAllMocks()
})

function mockFetch(status: number, body: unknown, headers: Record<string, string> = {}) {
  globalThis.fetch = vi.fn<typeof fetch>().mockResolvedValue(
    new Response(JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json', ...headers },
    }),
  )
}

describe('api client', () => {
  it('sends JSON body and parses response', async () => {
    mockFetch(201, { id: 1, name: 'Bot' })
    const res = await api.createAgent('tok123', { name: 'Bot' })
    expect(res).toEqual({ id: 1, name: 'Bot' })

    const calls = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls
    const [, init] = calls[0] as [RequestInfo | URL, RequestInit]
    const headers = init.headers as Record<string, string>
    expect(init.method).toBe('POST')
    expect(JSON.parse(init.body as string)).toEqual({ name: 'Bot' })
    expect(headers.Authorization).toBe('Bearer tok123')
    expect(headers['Content-Type']).toBe('application/json')
  })

  it('throws ApiError with server detail on 4xx', async () => {
    mockFetch(401, { detail: 'Invalid email or password' })
    await expect(api.login({ email: 'a@b.c', password: 'x' })).rejects.toMatchObject({
      name: 'ApiError',
      status: 401,
      message: 'Invalid email or password',
    })
  })

  it('throws ApiError on network failure', async () => {
    globalThis.fetch = vi.fn<typeof fetch>().mockRejectedValue(new TypeError('fetch failed'))
    await expect(api.me('t')).rejects.toMatchObject({
      name: 'ApiError',
      status: 0,
    })
  })

  it('handles 204 as undefined', async () => {
    globalThis.fetch = vi.fn<typeof fetch>().mockResolvedValue(new Response(null, { status: 204 }))
    const res = await api.deleteAgent('t', 1)
    expect(res).toBeUndefined()
  })

  it('uploads PDF files as multipart with auth header', async () => {
    mockFetch(201, [{ id: 1, kind: 'pdf', file_name: 'manual.pdf', status: 'pending' }])
    const file = new File(['pdf-bytes'], 'manual.pdf', { type: 'application/pdf' })

    const res = await api.uploadSourceFiles('tok123', 7, [file])
    expect(res[0]).toMatchObject({ kind: 'pdf', file_name: 'manual.pdf' })

    const [url, init] = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0] as [string, RequestInit]
    expect(url).toContain('/api/agents/7/sources/files')
    expect(init.method).toBe('POST')
    expect((init.headers as Record<string, string>).Authorization).toBe('Bearer tok123')
    expect(init.body).toBeInstanceOf(FormData)
  })

  it('throws ApiError with server detail when upload fails', async () => {
    mockFetch(422, { detail: 'manual.pdf is not a PDF' })
    const file = new File(['x'], 'notes.txt', { type: 'text/plain' })
    await expect(api.uploadSourceFiles('tok123', 7, [file])).rejects.toMatchObject({
      status: 422,
      message: 'manual.pdf is not a PDF',
    })
  })

  it('adds a text source with title + content', async () => {
    mockFetch(201, [{ id: 9, kind: 'text', title: 'FAQ', status: 'pending' }])
    const res = await api.addTextSource('tok123', 7, { title: 'FAQ', content: 'long content here' })
    expect(res[0]?.kind).toBe('text')
    const [, init] = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0] as [string, RequestInit]
    expect(init.method).toBe('POST')
    expect(JSON.parse(init.body as string)).toEqual({ title: 'FAQ', content: 'long content here' })
    expect((init.headers as Record<string, string>).Authorization).toBe('Bearer tok123')
  })
})
