import { formatYears } from '../lib/format'
import type { FilterState } from '../lib/filters'
import type { Resume } from '../types'
import { FilterPanel } from './FilterPanel'
import { FileIcon } from './icons'

interface CandidateRailProps {
  resume: Resume
  filters: FilterState
  onChange: (next: FilterState) => void
  onClear: () => void
  activeCount: number
}

export function CandidateRail({
  resume,
  filters,
  onChange,
  onClear,
  activeCount,
}: CandidateRailProps) {
  const profile = resume.profile
  const skills =
    profile.canonical_skills.length > 0
      ? profile.canonical_skills
      : profile.skills
  const visibleSkills = skills.slice(0, 10)
  const hiddenSkills = skills.length - visibleSkills.length

  return (
    <aside className="candidate-rail border-r border-line bg-sunken p-5">
      <p className="flex items-center gap-1.5 text-[11px] text-faint">
        <FileIcon className="h-3.5 w-3.5" />
        Candidate file
      </p>

      <h2 className="mt-3 font-display text-[28px] leading-[1.05] tracking-[-0.01em]">
        {profile.name}
      </h2>

      <dl className="mt-4 space-y-1.5 text-[12px]">
        <div className="flex justify-between gap-3">
          <dt className="text-faint">Experience</dt>
          <dd>{formatYears(profile.total_years_experience)}</dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt className="text-faint">Location</dt>
          <dd className="text-right">{profile.location || 'Not stated'}</dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt className="text-faint">Level</dt>
          <dd className="capitalize">{profile.seniority}</dd>
        </div>
      </dl>

      <section className="mt-5 border-t border-line pt-4">
        <h3 className="text-[11px] text-faint">Skills</h3>
        {visibleSkills.length > 0 ? (
          <ul className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1.5">
            {visibleSkills.map((skill) => (
              <li
                key={skill}
                className="border-b border-line pb-1 text-[12px] text-muted"
              >
                {skill}
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-2 text-[12px] text-muted">No skills extracted.</p>
        )}
        {hiddenSkills > 0 ? (
          <p className="mt-2 text-[11px] text-faint">
            +{hiddenSkills} more in your file
          </p>
        ) : null}
      </section>

      {profile.target_roles.length > 0 ? (
        <section className="mt-5 border-t border-line pt-4">
          <h3 className="text-[11px] text-faint">Target roles</h3>
          <p className="mt-2 text-[12px] text-muted">
            {profile.target_roles.join(', ')}
          </p>
        </section>
      ) : null}

      <p className="mt-5 text-[11px] text-faint">
        Parsed by {resume.parse_model}
      </p>

      <div className="mt-5 border-t border-line pt-4">
        <FilterPanel
          idPrefix="rail"
          filters={filters}
          onChange={onChange}
          onClear={onClear}
          activeCount={activeCount}
        />
      </div>
    </aside>
  )
}
