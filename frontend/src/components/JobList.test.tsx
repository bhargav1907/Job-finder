import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { makeItem, makeJob } from '../test/fixtures'
import { JobList } from './JobList'

const known = [makeItem(1, 91), makeItem(2, 84), makeItem(3, 77)]

function renderList(overrides: Partial<Parameters<typeof JobList>[0]> = {}) {
  return render(
    <JobList
      known={known}
      unstated={[]}
      selectedJobId={1}
      onSelect={vi.fn()}
      isLoading={false}
      error={null}
      onRetry={vi.fn()}
      onClearFilters={vi.fn()}
      activeCount={0}
      {...overrides}
    />,
  )
}

describe('JobList', () => {
  it('moves selection with arrow keys and announces the selected role', async () => {
    const onSelect = vi.fn()
    renderList({ onSelect })

    const first = screen.getByRole('button', { name: /job one/i })
    first.focus()
    await userEvent.keyboard('{ArrowDown}')
    expect(onSelect).toHaveBeenCalledWith(2)

    await userEvent.keyboard('{End}')
    expect(onSelect).toHaveBeenCalledWith(3)
  })

  it('shows the empty filtered state with a clear action', () => {
    renderList({ known: [], unstated: [], selectedJobId: null, activeCount: 2 })

    expect(
      screen.getByText(/no roles match these filters/i),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: /clear filters/i }),
    ).toBeInTheDocument()
  })

  it('separates roles with listed pay from roles without it', () => {
    renderList({
      unstated: [
        makeItem(4, 61, {
          job: makeJob(4, { salary_min: null, salary_max: null }),
        }),
      ],
    })

    expect(
      screen.getByRole('heading', { name: 'With listed pay' }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('heading', { name: 'Pay not stated' }),
    ).toBeInTheDocument()
  })
})
