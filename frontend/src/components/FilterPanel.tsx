import type { FilterState } from '../lib/filters'
import { ChevronDownIcon } from './icons'

interface FilterPanelProps {
  idPrefix: string
  filters: FilterState
  onChange: (next: FilterState) => void
  onClear: () => void
  activeCount: number
}

const EXPERIENCE = [
  { value: '', label: 'Any experience' },
  { value: '0', label: 'Fresher' },
  { value: '1', label: '1 year' },
  { value: '2', label: '2 years' },
  { value: '3', label: '3 years' },
  { value: '5', label: '5 years' },
  { value: '8', label: '8+ years' },
]

export function FilterPanel({
  idPrefix,
  filters,
  onChange,
  onClear,
  activeCount,
}: FilterPanelProps) {
  const update = (patch: Partial<FilterState>) =>
    onChange({ ...filters, ...patch })

  return (
    <div>
      <div className="flex items-baseline justify-between gap-3">
        <p className="font-display text-lg leading-none">Refine</p>
        {activeCount > 0 ? (
          <button
            type="button"
            onClick={onClear}
            className="text-[11px] text-muted underline decoration-line-strong underline-offset-2 transition-colors hover:text-ink"
          >
            Clear filters
          </button>
        ) : null}
      </div>

      <div className="mt-4 space-y-4">
        <div className="filter-field">
          <label htmlFor={`${idPrefix}-role`}>Role</label>
          <input
            id={`${idPrefix}-role`}
            className="filter-input"
            value={filters.role}
            onChange={(event) => update({ role: event.target.value })}
            placeholder="AI Engineer"
            autoComplete="off"
          />
        </div>

        <div className="filter-field">
          <label htmlFor={`${idPrefix}-location`}>Location</label>
          <input
            id={`${idPrefix}-location`}
            className="filter-input"
            value={filters.location}
            onChange={(event) => update({ location: event.target.value })}
            placeholder="Bengaluru"
            autoComplete="off"
          />
        </div>

        <div className="filter-field">
          <label htmlFor={`${idPrefix}-experience`}>Experience</label>
          <div className="filter-select-wrap">
            <select
              id={`${idPrefix}-experience`}
              className="filter-input filter-select"
              value={filters.experienceYears}
              onChange={(event) =>
                update({ experienceYears: event.target.value })
              }
            >
              {EXPERIENCE.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            <ChevronDownIcon />
          </div>
        </div>

        <div className="filter-field">
          <label htmlFor={`${idPrefix}-salary`}>Minimum pay</label>
          <div className="relative">
            <input
              id={`${idPrefix}-salary`}
              className="filter-input pr-10"
              type="number"
              min="0"
              inputMode="numeric"
              value={filters.salaryMin}
              onChange={(event) => update({ salaryMin: event.target.value })}
              placeholder="Any"
            />
            <span className="filter-suffix">LPA</span>
          </div>
        </div>

        <label className="flex items-center gap-2 text-[12px] text-muted">
          <input
            type="checkbox"
            checked={filters.remote}
            onChange={(event) => update({ remote: event.target.checked })}
            style={{ accentColor: 'var(--color-brass)' }}
          />
          Remote only
        </label>
      </div>
    </div>
  )
}
