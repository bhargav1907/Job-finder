import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { EMPTY_FILTERS } from '../lib/filters'
import { makeResume } from '../test/fixtures'
import { CandidateRail } from './CandidateRail'

describe('CandidateRail', () => {
  it('shows the candidate profile and the model that parsed it', () => {
    render(
      <CandidateRail
        resume={makeResume()}
        filters={EMPTY_FILTERS}
        onChange={vi.fn()}
        onClear={vi.fn()}
        activeCount={0}
      />,
    )

    expect(screen.getByText('Asha Rao')).toBeInTheDocument()
    expect(screen.getByText('2.4 years')).toBeInTheDocument()
    expect(screen.getByText('Bengaluru')).toBeInTheDocument()
    expect(screen.getByText('python')).toBeInTheDocument()
    expect(screen.getByText(/qwen3:4b/)).toBeInTheDocument()
  })
})
