export const RESUME_KEY = 'fla.resumeId'

export function getStoredResumeId(): number | null {
  try {
    const raw = localStorage.getItem(RESUME_KEY)
    if (!raw || !/^\d+$/.test(raw)) return null
    const id = Number(raw)
    return Number.isSafeInteger(id) && id > 0 ? id : null
  } catch {
    return null
  }
}

export function saveResumeId(id: number): void {
  try {
    localStorage.setItem(RESUME_KEY, String(id))
  } catch {
    // Storage can be unavailable; the URL still carries the id.
  }
}

export function clearResumeId(): void {
  try {
    localStorage.removeItem(RESUME_KEY)
  } catch {
    // Nothing to clear when storage is unavailable.
  }
}
