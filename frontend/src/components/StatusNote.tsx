import type { ReactNode } from 'react'

type Tone = 'info' | 'error' | 'success'

interface StatusNoteProps {
  tone: Tone
  title: string
  children?: ReactNode
  action?: ReactNode
}

const TONES: Record<Tone, string> = {
  info: 'border-brass text-brass-strong',
  error: 'border-rust text-rust',
  success: 'border-ok text-ok',
}

export function StatusNote({
  tone,
  title,
  children,
  action,
}: StatusNoteProps) {
  return (
    <div
      role={tone === 'error' ? 'alert' : 'status'}
      className={`border-l-2 bg-raised px-4 py-3 ${TONES[tone]}`}
    >
      <p className="font-display text-lg leading-tight">{title}</p>
      {children ? (
        <div className="mt-1 text-[13px] leading-relaxed text-muted">
          {children}
        </div>
      ) : null}
      {action ? <div className="mt-3">{action}</div> : null}
    </div>
  )
}
