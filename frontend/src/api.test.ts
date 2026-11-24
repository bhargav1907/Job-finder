import { afterEach, describe, expect, it, vi } from 'vitest'
import { getJobsCount, getRecommendations, uploadResume } from './api'

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('api', () => {
  it('uploads the file as multipart form data', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ id: 3 }))
    vi.stubGlobal('fetch', fetchMock)
    const file = new File(['resume text'], 'cv.txt', { type: 'text/plain' })

    await uploadResume(file)

    expect(fetchMock).toHaveBeenCalledTimes(1)
    const init = fetchMock.mock.calls[0]?.[1] as RequestInit
    expect(fetchMock.mock.calls[0]?.[0]).toBe('/api/resumes')
    expect(init.method).toBe('POST')
    expect(init.body).toBeInstanceOf(FormData)
    expect((init.body as FormData).get('file')).toBe(file)
  })

  it('builds recommendation query parameters in API order', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ items: [] }))
    vi.stubGlobal('fetch', fetchMock)

    await getRecommendations(7, {
      location: 'Bengaluru',
      remote: true,
      experienceYears: 3,
      role: 'AI Engineer',
      salaryMin: 1_200_000,
    })

    expect(fetchMock.mock.calls[0]?.[0]).toBe(
      '/api/resumes/7/recommendations?location=Bengaluru&remote=true&experience_years=3&role=AI+Engineer&salary_min=1200000',
    )
  })

  it('surfaces FastAPI detail in ApiError', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse({ detail: 'Resume not found' }, 404)),
    )

    await expect(getRecommendations(9, {})).rejects.toMatchObject({
      name: 'ApiError',
      status: 404,
      detail: 'Resume not found',
    })
  })

  it('returns the corpus total', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValue(
          jsonResponse({ items: [], total: 98, limit: 1, offset: 0 }),
        ),
    )

    await expect(getJobsCount()).resolves.toBe(98)
  })
})
