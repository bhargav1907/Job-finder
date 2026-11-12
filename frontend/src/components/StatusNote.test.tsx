import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { StatusNote } from './StatusNote'

describe('StatusNote', () => {
  it('announces errors as alerts', () => {
    render(
      <StatusNote tone="error" title="That file is too large">
        Choose a smaller file.
      </StatusNote>,
    )
    expect(screen.getByRole('alert')).toHaveTextContent(
      'That file is too large',
    )
  })

  it('announces progress as status', () => {
    render(
      <StatusNote tone="info" title="Reading your resume">
        This can take up to a minute.
      </StatusNote>,
    )
    expect(screen.getByRole('status')).toHaveTextContent('Reading your resume')
  })
})
