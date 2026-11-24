import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { makeItem } from '../test/fixtures'
import { JobDetail } from './JobDetail'

describe('JobDetail', () => {
  it('shows score, reasons, gaps, and pay', () => {
    render(
      <JobDetail
        item={makeItem(1, 87, {
          reasons: ['Your RAG work matches'],
          gaps: ['kubernetes'],
          reranked: true,
        })}
      />,
    )

    expect(
      screen.getByLabelText(/fit score 87 out of 100/i),
    ).toBeInTheDocument()
    expect(screen.getByText('Your RAG work matches')).toBeInTheDocument()
    expect(screen.getByText('kubernetes')).toBeInTheDocument()
    expect(screen.getByText('₹16.3–18.6 LPA')).toBeInTheDocument()
  })

  it('explains the absence of a written explanation', () => {
    render(
      <JobDetail
        item={makeItem(2, 61, { reasons: [], gaps: [], reranked: false })}
      />,
    )

    expect(screen.getByText(/ranked by retrieval only/i)).toBeInTheDocument()
    expect(screen.getByText(/no skill gaps reported/i)).toBeInTheDocument()
  })
})
