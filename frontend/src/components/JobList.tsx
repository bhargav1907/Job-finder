import { useRef } from 'react'
import type { KeyboardEvent } from 'react'
import type { RecommendationItem } from '../types'
import { JobRow } from './JobRow'

interface JobListProps {
  known: RecommendationItem[]
  unstated: RecommendationItem[]
  selectedJobId: number | null
  onSelect: (jobId: number) => void
  isLoading: boolean
  error: string | null
  onRetry: () => void
  onClearFilters: () => void
  activeCount: number
}

export function JobList({
  known,
  unstated,
  selectedJobId,
  onSelect,
  isLoading,
  error,
  onRetry,
  onClearFilters,
  activeCount,
}: JobListProps) {
  const rowRefs = useRef(new Map<number, HTMLButtonElement>())
  const rows = [...known, ...unstated]
  const selected = rows.find((item) => item.job.id === selectedJobId)
  const total = rows.length

  function handleKeyDown(
    event: KeyboardEvent<HTMLLIElement>,
    jobId: number,
  ) {
    const index = rows.findIndex((item) => item.job.id === jobId)
    if (index === -1) return

    let next = index
    if (event.key === 'ArrowDown') next = Math.min(total - 1, index + 1)
    else if (event.key === 'ArrowUp') next = Math.max(0, index - 1)
    else if (event.key === 'Home') next = 0
    else if (event.key === 'End') next = total - 1
    else return

    const target = rows[next]
    if (!target) return

    event.preventDefault()
    onSelect(target.job.id)
    rowRefs.current.get(target.job.id)?.focus()
  }

  if (isLoading) {
    return (
      <section aria-busy="true">
        <p className="sr-only">Loading openings</p>
        <ul className="mt-4">
          {[0, 1, 2, 3].map((row) => (
            <li key={row} className="skeleton-row" aria-hidden="true">
              <span className="skeleton-mark" />
              <span className="min-w-0 flex-1">
                <span className="skeleton-bar w-3/4" />
                <span className="skeleton-bar mt-2 w-1/2" />
              </span>
            </li>
          ))}
        </ul>
      </section>
    )
  }

  if (error) {
    return (
      <div className="mt-4 border-l-2 border-rust pl-4">
        <p role="alert" className="text-[13px] text-rust">
          {error}
        </p>
        <button
          type="button"
          onClick={onRetry}
          className="mt-3 border border-line-strong px-3 py-1.5 text-[12px] text-ink transition-colors hover:border-brass hover:text-brass-strong"
        >
          Retry
        </button>
      </div>
    )
  }

  if (total === 0) {
    return (
      <div className="mt-6 border-t border-line pt-6">
        {activeCount > 0 ? (
          <>
            <p className="font-display text-xl leading-tight">
              No roles match these filters.
            </p>
            <p className="mt-2 text-[13px] text-muted">
              Try a broader role, location, or pay floor.
            </p>
            <button
              type="button"
              onClick={onClearFilters}
              className="mt-4 border border-brass px-3 py-1.5 text-[12px] text-brass-strong transition-colors hover:bg-brass hover:text-desk"
            >
              Clear filters
            </button>
          </>
        ) : (
          <>
            <p className="font-display text-xl leading-tight">
              No openings loaded.
            </p>
            <p className="mt-2 text-[13px] text-muted">
              Load the demo corpus from the backend:
            </p>
            <code className="mt-2 block border border-line px-3 py-2 font-data text-[12px] text-muted">
              python -m app.cli ingest
            </code>
          </>
        )}
      </div>
    )
  }

  return (
    <>
      <p className="sr-only" aria-live="polite">
        {selected ? `${selected.job.title} selected.` : ''}
      </p>

      <p className="mt-2 text-[11px] text-faint" aria-live="polite">
        {total} {total === 1 ? 'role' : 'roles'} shown
      </p>

      {known.length > 0 ? (
        <section className="mt-4" aria-labelledby="known-pay-heading">
          <div className="flex items-baseline justify-between border-b border-line-strong pb-1.5">
            <h2
              id="known-pay-heading"
              className="text-[12px] font-medium text-ink"
            >
              With listed pay
            </h2>
            <span className="text-[11px] text-faint">{known.length}</span>
          </div>
          <ul>
            {known.map((item, index) => (
              <JobRow
                key={item.job.id}
                item={item}
                rank={index + 1}
                selected={item.job.id === selectedJobId}
                onSelect={onSelect}
                onKeyDown={(event) => handleKeyDown(event, item.job.id)}
                rowRef={(element) => {
                  if (element) rowRefs.current.set(item.job.id, element)
                  else rowRefs.current.delete(item.job.id)
                }}
              />
            ))}
          </ul>
        </section>
      ) : null}

      {unstated.length > 0 ? (
        <section className="mt-6" aria-labelledby="unstated-pay-heading">
          <div className="flex items-baseline justify-between border-b border-line-strong pb-1.5">
            <h2
              id="unstated-pay-heading"
              className="text-[12px] font-medium text-ink"
            >
              Pay not stated
            </h2>
            <span className="text-[11px] text-faint">{unstated.length}</span>
          </div>
          <ul>
            {unstated.map((item, index) => (
              <JobRow
                key={item.job.id}
                item={item}
                rank={known.length + index + 1}
                selected={item.job.id === selectedJobId}
                onSelect={onSelect}
                onKeyDown={(event) => handleKeyDown(event, item.job.id)}
                rowRef={(element) => {
                  if (element) rowRefs.current.set(item.job.id, element)
                  else rowRefs.current.delete(item.job.id)
                }}
              />
            ))}
          </ul>
        </section>
      ) : null}
    </>
  )
}
