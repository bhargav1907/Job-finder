import { formatYears } from '../lib/format'
import type { FilterState } from '../lib/filters'
import type { Resume } from '../types'
import { FilterPanel } from './FilterPanel'

interface CandidateStripProps {
  resume: Resume
  filters: FilterState
  onChange: (next: FilterState) => void
  onClear: () => void
  activeCount: number
}

export function CandidateStrip({
  resume,
  filters,
  onChange,
  onClear,
  activeCount,
}: CandidateStripProps) {
  const profile = resume.profile

  return (
    <div className="border-b border-line bg-sunken px-4 py-3 sm:px-6">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <span className="font-display text-xl leading-tight">
          {profile.name}
        </span>
        <span className="text-[11px] text-faint">
          {formatYears(profile.total_years_experience)},{' '}
          {profile.location || 'Location not stated'}
        </span>
      </div>

      <details className="mt-2">
        <summary className="cursor-pointer text-[12px] text-muted transition-colors hover:text-ink">
          Refine
          {activeCount > 0 ? (
            <span className="ml-1.5 text-faint">({activeCount})</span>
          ) : null}
        </summary>
        <div className="mt-4 max-w-sm pb-2">
          <FilterPanel
            idPrefix="strip"
            filters={filters}
            onChange={onChange}
            onClear={onClear}
            activeCount={activeCount}
          />
        </div>
      </details>
    </div>
  )
}
