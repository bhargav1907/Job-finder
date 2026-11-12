import {
  formatPosted,
  formatRoleFamily,
  formatSalary,
} from '../lib/format'
import type { RecommendationItem } from '../types'
import { FitSeal } from './FitSeal'
import { ArrowLeftIcon, ExternalIcon } from './icons'

interface JobDetailProps {
  item: RecommendationItem
  onBack?: () => void
}

export function JobDetail({ item, onBack }: JobDetailProps) {
  const { job } = item
  const posted = formatPosted(job.posted_at)

  return (
    <article className="case-file">
      {onBack ? (
        <button
          type="button"
          onClick={onBack}
          className="mb-4 inline-flex items-center gap-1.5 text-[12px] text-muted transition-colors hover:text-ink md:hidden"
        >
          <ArrowLeftIcon className="h-3.5 w-3.5" />
          Back to shortlist
        </button>
      ) : null}

      <header className="flex items-start justify-between gap-5 border-b border-line-strong pb-5">
        <div className="min-w-0">
          <p className="text-[11px] text-faint">{job.company}</p>
          <h2 className="mt-1 font-display text-[30px] leading-[1.08] tracking-[-0.01em]">
            {job.title}
          </h2>
          <p className="mt-2 text-[12px] text-muted">
            {job.location || 'Location not stated'}
          </p>
        </div>
        <FitSeal score={item.score} size="lg" />
      </header>

      <dl className="case-ledger mt-4">
        <div>
          <dt>Pay</dt>
          <dd>{formatSalary(job)}</dd>
        </div>
        <div>
          <dt>Level</dt>
          <dd className="capitalize">{job.seniority}</dd>
        </div>
        <div>
          <dt>Field</dt>
          <dd>{formatRoleFamily(job.role_family)}</dd>
        </div>
        {job.remote ? (
          <div>
            <dt>Work</dt>
            <dd>Remote</dd>
          </div>
        ) : null}
        {posted ? (
          <div>
            <dt>Posted</dt>
            <dd>{posted.replace(/^Posted /, '')}</dd>
          </div>
        ) : null}
      </dl>

      <section className="mt-7">
        <h3 className="case-heading">Why this fits</h3>
        {!item.reranked ? (
          <p className="mt-2 text-[13px] text-muted">
            This role was ranked by retrieval only; no written explanation
            yet.
          </p>
        ) : item.reasons.length > 0 ? (
          <ul className="case-list mt-2">
            {item.reasons.map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
        ) : (
          <p className="mt-2 text-[13px] text-muted">
            No reasons were returned for this role.
          </p>
        )}
      </section>

      <section className="mt-6">
        <h3 className="case-heading">What to build next</h3>
        {item.gaps.length > 0 ? (
          <ul className="mt-2 flex flex-wrap gap-x-2 gap-y-1">
            {item.gaps.map((gap) => (
              <li
                key={gap}
                className="border border-line px-2 py-0.5 text-[12px] text-muted"
              >
                {gap}
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-2 text-[13px] text-muted">No skill gaps reported.</p>
        )}
      </section>

      <section className="mt-6">
        <h3 className="case-heading">Skills you match</h3>
        {item.matched_skills.length > 0 ? (
          <p className="mt-2 text-[13px] text-muted">
            {item.matched_skills.join(', ')}
          </p>
        ) : (
          <p className="mt-2 text-[13px] text-muted">
            No overlapping skills found.
          </p>
        )}
      </section>

      <section className="mt-6">
        <h3 className="case-heading">Role details</h3>
        <dl className="case-ledger mt-2">
          <div>
            <dt>Listed skills</dt>
            <dd className="text-right">
              {job.skills.length > 0 ? job.skills.join(', ') : 'Not stated'}
            </dd>
          </div>
          <div>
            <dt>Source</dt>
            <dd>{job.source}</dd>
          </div>
        </dl>
      </section>

      <a
        href={job.url}
        target="_blank"
        rel="noreferrer"
        className="mt-7 inline-flex items-center gap-1.5 border border-brass px-3 py-1.5 text-[12px] transition-colors hover:bg-brass hover:text-desk"
      >
        Open original posting
        <ExternalIcon className="h-3.5 w-3.5" />
      </a>
    </article>
  )
}
