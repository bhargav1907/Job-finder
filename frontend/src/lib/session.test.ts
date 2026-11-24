import { beforeEach, describe, expect, it } from 'vitest'
import {
  clearResumeId,
  getStoredResumeId,
  RESUME_KEY,
  saveResumeId,
} from './session'

describe('resume session', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('round-trips a valid resume id', () => {
    saveResumeId(12)
    expect(getStoredResumeId()).toBe(12)
    clearResumeId()
    expect(getStoredResumeId()).toBeNull()
  })

  it('ignores malformed stored ids', () => {
    localStorage.setItem(RESUME_KEY, 'not-a-number')
    expect(getStoredResumeId()).toBeNull()
    localStorage.setItem(RESUME_KEY, '0')
    expect(getStoredResumeId()).toBeNull()
    localStorage.setItem(RESUME_KEY, '-4')
    expect(getStoredResumeId()).toBeNull()
  })
})
