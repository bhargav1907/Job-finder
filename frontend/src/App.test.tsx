import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { App } from './App'
import { ApiError, getJobsCount, getRecommendations, getResume } from './api'
import { makeItem, makeResume } from './test/fixtures'

vi.mock('./api', async (orig) => ({
  ...(await orig<typeof import('./api')>()),
  getResume: vi.fn(),
  getRecommendations: vi.fn(),
  getJobsCount: vi.fn(),
}))

const EMPTY_RESULTS = {
  resume_id: 7,
  items: [],
  items_without_salary: [],
  total: 0,
  without_salary_total: 0,
  limit: 30,
  retrieval_version: 'v1',
  rerank_status: 'ok' as const,
  rerank_version: 'rerank-v1@lfm3:1.7b',
}

function renderApp() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, retryDelay: 0 } },
  })
  return render(
    <QueryClientProvider client={client}>
      <App />
    </QueryClientProvider>,
  )
}

describe('App', () => {
  it('restores a resume from the URL and shows the candidate file', async () => {
    window.history.replaceState({}, '', '/?resume=7')
    vi.mocked(getResume).mockResolvedValue(makeResume())
    vi.mocked(getRecommendations).mockResolvedValue(EMPTY_RESULTS)

    renderApp()

    expect(await screen.findByText('Asha Rao')).toBeInTheDocument()
    expect(await screen.findByText(/no openings loaded/i)).toBeInTheDocument()
  })

  it('offers a retry when the candidate file fails to open', async () => {
    window.history.replaceState({}, '', '/?resume=7')
    vi.mocked(getResume).mockRejectedValue(
      new ApiError(500, 'The server could not open that file.'),
    )
    vi.mocked(getRecommendations).mockResolvedValue(EMPTY_RESULTS)
    vi.mocked(getJobsCount).mockResolvedValue(0)

    renderApp()

    expect(
      await screen.findByText('The server could not open that file.'),
    ).toBeInTheDocument()

    const callsBeforeRetry = vi.mocked(getResume).mock.calls.length
    vi.mocked(getResume).mockResolvedValue(makeResume())
    await userEvent.click(screen.getByRole('button', { name: /retry/i }))

    expect(await screen.findByText('Asha Rao')).toBeInTheDocument()
    expect(getResume).toHaveBeenCalledTimes(callsBeforeRetry + 1)
  })

  it('opens a selected role in the case file and writes it to the URL', async () => {
    window.history.replaceState({}, '', '/?resume=7')
    vi.mocked(getResume).mockResolvedValue(makeResume())
    vi.mocked(getRecommendations).mockResolvedValue({
      ...EMPTY_RESULTS,
      items: [makeItem(1, 88)],
      total: 1,
    })

    renderApp()

    const row = await screen.findByRole('button', { name: /job one/i })
    await userEvent.click(row)

    expect(
      await screen.findByRole('heading', { name: 'Job one' }),
    ).toBeInTheDocument()
    expect(window.location.search).toContain('job=1')
  })
})
