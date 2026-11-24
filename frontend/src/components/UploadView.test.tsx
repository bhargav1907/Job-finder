import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { UploadView } from './UploadView'

vi.mock('../api', () => ({
  uploadResume: vi.fn(),
  ApiError: class ApiError extends Error {
    status = 0
    detail = ''
  },
}))

describe('UploadView', () => {
  it('rejects an unsupported file before calling the API', async () => {
    const onUploaded = vi.fn()
    render(<UploadView onUploaded={onUploaded} corpusIsEmpty={false} />)

    const file = new File(['hello'], 'resume.exe', {
      type: 'application/octet-stream',
    })
    await userEvent.upload(screen.getByLabelText(/choose a file/i), file)

    expect(
      await screen.findByText(/pdf, docx, or txt/i),
    ).toBeInTheDocument()
    const { uploadResume } = await import('../api')
    expect(uploadResume).not.toHaveBeenCalled()
    expect(onUploaded).not.toHaveBeenCalled()
  })

  it('shows the ingest instruction when the corpus is empty', () => {
    render(<UploadView onUploaded={vi.fn()} corpusIsEmpty />)
    expect(
      screen.getByText(/python -m app.cli ingest/),
    ).toBeInTheDocument()
  })
})
