import { useEffect, useRef, useState } from 'react'
import type { ChangeEvent, DragEvent } from 'react'
import { ApiError, uploadResume } from '../api'
import type { Resume } from '../types'
import { FileIcon, UploadIcon } from './icons'
import { StatusNote } from './StatusNote'

const MAX_BYTES = 5 * 1024 * 1024
const ALLOWED = new Set(['pdf', 'docx', 'txt'])

interface UploadViewProps {
  onUploaded: (resume: Resume) => void
  corpusIsEmpty: boolean
}

function extensionOf(name: string): string {
  return name.split('.').pop()?.toLowerCase() ?? ''
}

export function UploadView({ onUploaded, corpusIsEmpty }: UploadViewProps) {
  const [status, setStatus] = useState<'idle' | 'uploading' | 'error'>('idle')
  const [message, setMessage] = useState('')
  const [fileName, setFileName] = useState('')
  const [elapsed, setElapsed] = useState(0)
  const [dragActive, setDragActive] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (status !== 'uploading') return
    setElapsed(0)
    const timer = window.setInterval(() => {
      setElapsed((seconds) => seconds + 1)
    }, 1000)
    return () => window.clearInterval(timer)
  }, [status])

  async function handleFile(file: File) {
    if (!ALLOWED.has(extensionOf(file.name))) {
      setStatus('error')
      setMessage('Choose a PDF, DOCX, or TXT file.')
      return
    }
    if (file.size === 0) {
      setStatus('error')
      setMessage('That file is empty. Choose another one.')
      return
    }
    if (file.size > MAX_BYTES) {
      setStatus('error')
      setMessage('That file is larger than 5 MB. Choose a smaller file.')
      return
    }

    setStatus('uploading')
    setFileName(file.name)
    setMessage('')

    try {
      const resume = await uploadResume(file)
      onUploaded(resume)
    } catch (error) {
      setStatus('error')
      if (error instanceof ApiError) {
        if (error.status === 415) {
          setMessage(
            'That format is not supported. Choose a PDF, DOCX, or TXT file.',
          )
        } else if (error.status === 413) {
          setMessage('That file is larger than 5 MB. Choose a smaller file.')
        } else if (error.status === 422) {
          setMessage(
            'That file could not be read. Try another copy, or export it as a PDF.',
          )
        } else {
          setMessage(error.detail)
        }
      } else {
        setMessage('Something went wrong while reading the file. Try again.')
      }
    }
  }

  function onInputChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    if (file) void handleFile(file)
    event.target.value = ''
  }

  function onDrop(event: DragEvent<HTMLElement>) {
    event.preventDefault()
    setDragActive(false)
    const file = event.dataTransfer.files?.[0]
    if (file) void handleFile(file)
  }

  return (
    <div className="mx-auto w-full max-w-2xl px-4 py-10 sm:px-6 sm:py-14">
      <header className="max-w-xl">
        <h1 className="font-display text-4xl leading-[1.05] tracking-[-0.02em] sm:text-5xl">
          Open your candidate file
        </h1>
        <p className="mt-4 max-w-md text-[15px] leading-relaxed text-muted">
          Drop a resume and the placement office will rank the openings that
          fit you, with the reasons why and the skills to build next.
        </p>
      </header>

      <div
        className={`upload-folder mt-12 ${dragActive ? 'is-dragging' : ''}`}
        onDragOver={(event) => {
          event.preventDefault()
          setDragActive(true)
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={onDrop}
      >
        <div className="flex flex-col items-start gap-5 p-6 sm:p-8">
          <FileIcon className="h-8 w-8 text-brass-strong" />
          <div>
            <p className="font-display text-2xl leading-tight">
              {status === 'uploading'
                ? 'Reading your resume'
                : 'Drop a resume here'}
            </p>
            <p className="mt-1 text-[13px] text-muted">
              PDF, DOCX, or TXT up to 5 MB.
            </p>
          </div>

          <input
            ref={inputRef}
            id="resume-file"
            type="file"
            accept=".pdf,.docx,.txt"
            className="sr-only"
            onChange={onInputChange}
          />
          <label htmlFor="resume-file" className="upload-button">
            <UploadIcon className="h-4 w-4" />
            Choose a file
          </label>

          <p className="text-[12px] text-faint">
            Parsed by the local model on this machine.
          </p>
        </div>
      </div>

      <div className="mt-5" aria-live="polite">
        {status === 'uploading' ? (
          <StatusNote tone="info" title="Reading your resume">
            <p>
              The local model is extracting experience and skills. This can
              take up to a minute.
            </p>
            <p className="mt-2 font-data text-[11px] text-faint">
              {fileName} · {elapsed}s elapsed
            </p>
          </StatusNote>
        ) : null}

        {status === 'error' ? (
          <StatusNote tone="error" title="That file could not be opened">
            <p>{message}</p>
          </StatusNote>
        ) : null}
      </div>

      {corpusIsEmpty ? (
        <div className="mt-8">
          <StatusNote tone="info" title="No openings loaded">
            <p>The database is empty. Load the demo listings first:</p>
            <code className="mt-2 block w-fit border border-line bg-sunken px-2 py-1 font-data text-[12px] text-ink">
              python -m app.cli ingest
            </code>
          </StatusNote>
        </div>
      ) : null}
    </div>
  )
}
