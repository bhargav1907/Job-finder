import { useEffect, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ApiError, getJobsCount, getResume } from './api'
import { AppHeader } from './components/AppHeader'
import { CandidateRail } from './components/CandidateRail'
import { UploadView } from './components/UploadView'
import {
  activeFilterCount,
  EMPTY_FILTERS,
  type FilterState,
} from './lib/filters'
import { clearResumeId, getStoredResumeId, saveResumeId } from './lib/session'
import { applyTheme, resolveInitialTheme, saveTheme } from './lib/theme'
import type { Theme } from './lib/theme'
import { useUrlSelection } from './lib/useUrlState'
import type { Resume } from './types'

export function App() {
  const queryClient = useQueryClient()
  const [theme, setTheme] = useState<Theme>(() => resolveInitialTheme())
  const [selection, setSelection] = useUrlSelection()
  const [filters, setFilters] = useState<FilterState>(EMPTY_FILTERS)
  const activeCount = activeFilterCount(filters)

  useEffect(() => {
    applyTheme(theme)
  }, [theme])

  function changeTheme(next: Theme) {
    setTheme(next)
    saveTheme(next)
    applyTheme(next)
  }

  // A returning visitor has an id in localStorage but no query string.
  useEffect(() => {
    if (selection.resumeId !== null) return
    const stored = getStoredResumeId()
    if (stored === null) return
    setSelection({ resumeId: stored, jobId: selection.jobId }, 'replace')
  }, [selection.resumeId, selection.jobId, setSelection])

  const resumeId = selection.resumeId
  const resumeQuery = useQuery({
    queryKey: ['resume', resumeId],
    queryFn: () => getResume(resumeId as number),
    enabled: resumeId !== null,
    retry: 1,
  })

  const corpusQuery = useQuery({
    queryKey: ['jobs', 'count'],
    queryFn: getJobsCount,
    enabled: resumeId === null,
    staleTime: 5 * 60_000,
    retry: 0,
  })

  useEffect(() => {
    const error = resumeQuery.error
    if (error instanceof ApiError && error.status === 404) {
      clearResumeId()
      setSelection({ resumeId: null, jobId: null }, 'replace')
    }
  }, [resumeQuery.error, setSelection])

  const resume = resumeId !== null ? (resumeQuery.data ?? null) : null

  function handleUploaded(uploaded: Resume) {
    queryClient.setQueryData(['resume', uploaded.id], uploaded)
    saveResumeId(uploaded.id)
    setSelection({ resumeId: uploaded.id, jobId: null }, 'replace')
  }

  function replaceResume() {
    clearResumeId()
    queryClient.removeQueries({ queryKey: ['resume'] })
    queryClient.removeQueries({ queryKey: ['recommendations'] })
    setSelection({ resumeId: null, jobId: null }, 'replace')
  }

  return (
    <div className="flex min-h-screen flex-col bg-desk text-ink">
      <AppHeader
        resume={resume}
        theme={theme}
        onToggleTheme={changeTheme}
        onReplace={replaceResume}
      />

      <main className="flex-1">
        {resumeId === null ? (
          <UploadView
            onUploaded={handleUploaded}
            corpusIsEmpty={corpusQuery.data === 0}
          />
        ) : resume ? (
          <div className="workspace">
            <CandidateRail
              resume={resume}
              filters={filters}
              onChange={setFilters}
              onClear={() => setFilters(EMPTY_FILTERS)}
              activeCount={activeCount}
            />

            <section
              className="shortlist-pane border-r border-line px-5 py-6"
              aria-labelledby="shortlist-heading"
            >
              <h1
                id="shortlist-heading"
                className="font-display text-2xl leading-tight"
              >
                Shortlist for {resume.profile.name.split(' ')[0]}
              </h1>
              <p className="mt-2 text-[13px] text-muted">
                Ranking the openings…
              </p>
            </section>

            <section className="case-pane px-5 py-6">
              <p className="text-[13px] text-faint">
                Select a role from the shortlist.
              </p>
            </section>
          </div>
        ) : (
          <div className="mx-auto w-full max-w-xl px-4 py-10 sm:px-6">
            <div className="w-full max-w-xl border border-line bg-raised px-6 py-8">
              {resumeQuery.isPending ? (
                <p className="text-muted">Opening your candidate file…</p>
              ) : null}

              {resumeQuery.isError &&
              !(resumeQuery.error instanceof ApiError) ? (
                <p role="alert" className="text-rust">
                  Could not open your candidate file. Please retry.
                </p>
              ) : null}

              {resumeQuery.isError &&
              resumeQuery.error instanceof ApiError &&
              resumeQuery.error.status !== 404 ? (
                <p role="alert" className="text-rust">
                  {resumeQuery.error.detail}
                </p>
              ) : null}
            </div>
          </div>
        )}
      </main>

      <footer className="border-t border-line px-4 py-3 text-[11px] text-faint sm:px-6">
        Seed listings from data/seed_jobs.json. Not live postings.
      </footer>
    </div>
  )
}

export default App
