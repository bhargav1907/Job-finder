import { useEffect, useState } from 'react'
import {
  keepPreviousData,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query'
import { ApiError, getJobsCount, getRecommendations, getResume } from './api'
import { AppHeader } from './components/AppHeader'
import { CandidateRail } from './components/CandidateRail'
import { CandidateStrip } from './components/CandidateStrip'
import { JobDetail } from './components/JobDetail'
import { JobList } from './components/JobList'
import { StatusNote } from './components/StatusNote'
import { UploadView } from './components/UploadView'
import {
  activeFilterCount,
  EMPTY_FILTERS,
  filtersToQuery,
  serializeFilters,
  type FilterState,
} from './lib/filters'
import { clearResumeId, getStoredResumeId, saveResumeId } from './lib/session'
import { applyTheme, resolveInitialTheme, saveTheme } from './lib/theme'
import type { Theme } from './lib/theme'
import { useDebounced } from './lib/useDebounced'
import { useMediaQuery } from './lib/useMediaQuery'
import { useUrlSelection } from './lib/useUrlState'
import type { Resume } from './types'

export function App() {
  const queryClient = useQueryClient()
  const [theme, setTheme] = useState<Theme>(() => resolveInitialTheme())
  const [selection, setSelection] = useUrlSelection()
  const [filters, setFilters] = useState<FilterState>(EMPTY_FILTERS)
  const debouncedFilters = useDebounced(filters, 250)
  const activeCount = activeFilterCount(filters)
  const isDesktop = useMediaQuery('(min-width: 1280px)')
  const isWide = useMediaQuery('(min-width: 768px)')

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
    staleTime: 5 * 60_000,
    retry: 0,
  })

  const recommendationsQuery = useQuery({
    queryKey: ['recommendations', resumeId, serializeFilters(debouncedFilters)],
    queryFn: () =>
      getRecommendations(resumeId as number, filtersToQuery(debouncedFilters)),
    enabled: resumeId !== null,
    placeholderData: keepPreviousData,
    retry: 1,
  })

  useEffect(() => {
    const error = resumeQuery.error
    if (error instanceof ApiError && error.status === 404) {
      clearResumeId()
      setSelection({ resumeId: null, jobId: null }, 'replace')
    }
  }, [resumeQuery.error, setSelection])

  // A filtered result set can drop the role that was open.
  useEffect(() => {
    if (selection.resumeId === null || selection.jobId === null) return
    const data = recommendationsQuery.data
    if (!data) return
    const exists = [...data.items, ...data.items_without_salary].some(
      (item) => item.job.id === selection.jobId,
    )
    if (!exists) {
      setSelection({ resumeId: selection.resumeId, jobId: null }, 'replace')
    }
  }, [
    recommendationsQuery.data,
    selection.resumeId,
    selection.jobId,
    setSelection,
  ])

  const resume = resumeId !== null ? (resumeQuery.data ?? null) : null
  const results = recommendationsQuery.data
  const known = results?.items ?? []
  const unstated = results?.items_without_salary ?? []
  const selectedItem =
    [...known, ...unstated].find((item) => item.job.id === selection.jobId) ??
    null

  const recommendationError = recommendationsQuery.error
    ? recommendationsQuery.error instanceof ApiError
      ? recommendationsQuery.error.detail
      : 'Could not load recommendations.'
    : null

  function clearFilters() {
    setFilters(EMPTY_FILTERS)
  }

  function handleUploaded(uploaded: Resume) {
    queryClient.setQueryData(['resume', uploaded.id], uploaded)
    saveResumeId(uploaded.id)
    setFilters(EMPTY_FILTERS)
    queryClient.invalidateQueries({ queryKey: ['resume'] })
    queryClient.invalidateQueries({ queryKey: ['recommendations'] })
    setSelection({ resumeId: uploaded.id, jobId: null }, 'replace')
  }

  function replaceResume() {
    clearResumeId()
    queryClient.removeQueries({ queryKey: ['resume'] })
    queryClient.removeQueries({ queryKey: ['recommendations'] })
    setFilters(EMPTY_FILTERS)
    setSelection({ resumeId: null, jobId: null }, 'replace')
  }

  function selectJob(jobId: number) {
    if (resumeId === null) return
    setSelection({ resumeId, jobId }, 'push')
  }

  function backToShortlist() {
    if (resumeId === null) return
    setSelection({ resumeId, jobId: null }, 'replace')
  }

  return (
    <div className="flex min-h-screen flex-col bg-desk text-ink">
      <AppHeader
        resume={resume}
        theme={theme}
        onToggleTheme={changeTheme}
        onReplace={replaceResume}
      />

      <main className="flex flex-1 flex-col">
        {resumeId === null ? (
          <UploadView
            onUploaded={handleUploaded}
            corpusIsEmpty={corpusQuery.data === 0}
          />
        ) : resume ? (
          <>
            {!isDesktop ? (
              <CandidateStrip
                resume={resume}
                filters={filters}
                onChange={setFilters}
                onClear={clearFilters}
                activeCount={activeCount}
              />
            ) : null}

            <div className="workspace">
              {isDesktop ? (
                <CandidateRail
                  resume={resume}
                  filters={filters}
                  onChange={setFilters}
                  onClear={clearFilters}
                  activeCount={activeCount}
                />
              ) : null}

              <section
                className={`shortlist-pane border-r border-line px-5 py-6${
                  selectedItem && !isWide ? ' hidden' : ''
                }`}
                aria-labelledby="shortlist-heading"
              >
                <h1
                  id="shortlist-heading"
                  className="font-display text-2xl leading-tight"
                >
                  Shortlist for {resume.profile.name.split(' ')[0]}
                </h1>

                {results?.rerank_status === 'partial' ? (
                  <div className="mt-4">
                    <StatusNote
                      tone="info"
                      title="Some explanations are missing"
                    >
                      Some roles were ranked by retrieval only, so their fit
                      notes are incomplete.
                    </StatusNote>
                  </div>
                ) : null}

                {results?.rerank_status === 'unavailable' ? (
                  <div className="mt-4">
                    <StatusNote tone="info" title="Explanations unavailable">
                      The rerank model is offline. Roles are ranked by
                      retrieval only.
                    </StatusNote>
                  </div>
                ) : null}

                <JobList
                  known={known}
                  unstated={unstated}
                  selectedJobId={selection.jobId}
                  onSelect={selectJob}
                  isLoading={recommendationsQuery.isPending}
                  error={recommendationError}
                  onRetry={() => {
                    void recommendationsQuery.refetch()
                  }}
                  onClearFilters={clearFilters}
                  activeCount={activeCount}
                />
              </section>

              <section
                className={`case-pane px-5 py-6${
                  !isWide && !selectedItem ? ' hidden' : ''
                }`}
              >
                {selectedItem ? (
                  <JobDetail
                    item={selectedItem}
                    onBack={!isWide ? backToShortlist : undefined}
                  />
                ) : (
                  <p className="text-[13px] text-faint">
                    Select a role from the shortlist.
                  </p>
                )}
              </section>
            </div>
          </>
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
