import type { KeyboardEvent, RefCallback } from 'react'
import { formatSalary, formatScore } from '../lib/format'
import type { RecommendationItem } from '../types'

interface JobRowProps {
  item: RecommendationItem
  rank: number
  selected: boolean
  onSelect: (jobId: number) => void
  onKeyDown: (event: KeyboardEvent<HTMLLIElement>) => void
  rowRef: RefCallback<HTMLButtonElement>
}

export function JobRow({
  item,
  rank,
  selected,
  onSelect,
  onKeyDown,
  rowRef,
}: JobRowProps) {
  const { job } = item
  const place = job.location ? `${job.company}, ${job.location}` : job.company

  return (
    <li onKeyDown={onKeyDown}>
      <button
        type="button"
        ref={rowRef}
        onClick={() => onSelect(job.id)}
        tabIndex={selected ? 0 : -1}
        aria-current={selected ? 'true' : undefined}
        className={`job-row${selected ? ' is-selected' : ''}`}
      >
        <span className="job-row-mark" aria-hidden="true">
          <span className="job-row-rank">
            {String(rank).padStart(2, '0')}
          </span>
          <span className="job-row-score">{formatScore(item.score)}</span>
        </span>

        <span className="min-w-0">
          <span className="job-row-title">{job.title}</span>
          <span className="job-row-place">{place}</span>
          <span className="job-row-pay">{formatSalary(job)}</span>
        </span>

        {job.remote ? <span className="job-row-tag">Remote</span> : null}
      </button>
    </li>
  )
}
