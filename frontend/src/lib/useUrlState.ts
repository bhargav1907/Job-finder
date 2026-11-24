import { useCallback, useEffect, useState } from 'react'

export interface Selection {
  resumeId: number | null
  jobId: number | null
}

function parseId(value: string | null): number | null {
  if (!value || !/^\d+$/.test(value)) return null
  const id = Number(value)
  return Number.isSafeInteger(id) && id > 0 ? id : null
}

export function readSelection(search: string = window.location.search): Selection {
  const params = new URLSearchParams(search)
  return {
    resumeId: parseId(params.get('resume')),
    jobId: parseId(params.get('job')),
  }
}

export function writeSelection(
  next: Selection,
  mode: 'push' | 'replace' = 'push',
): void {
  const params = new URLSearchParams(window.location.search)
  if (next.resumeId === null) params.delete('resume')
  else params.set('resume', String(next.resumeId))
  if (next.jobId === null) params.delete('job')
  else params.set('job', String(next.jobId))

  const query = params.toString()
  const url = `${window.location.pathname}${query ? `?${query}` : ''}${window.location.hash}`
  if (mode === 'replace') window.history.replaceState({}, '', url)
  else window.history.pushState({}, '', url)
}

export function useUrlSelection(): [
  Selection,
  (next: Selection, mode?: 'push' | 'replace') => void,
] {
  const [selection, setSelection] = useState<Selection>(() => readSelection())

  useEffect(() => {
    const onPopState = () => setSelection(readSelection())
    window.addEventListener('popstate', onPopState)
    return () => window.removeEventListener('popstate', onPopState)
  }, [])

  const update = useCallback(
    (next: Selection, mode: 'push' | 'replace' = 'push') => {
      writeSelection(next, mode)
      setSelection(next)
    },
    [],
  )

  return [selection, update]
}
