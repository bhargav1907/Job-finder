import { describe, expect, it } from 'vitest'
import { readSelection } from './useUrlState'

describe('readSelection', () => {
  it('reads resume and job ids', () => {
    expect(readSelection('?resume=7&job=42')).toEqual({
      resumeId: 7,
      jobId: 42,
    })
  })

  it('drops invalid ids', () => {
    expect(readSelection('?resume=abc&job=-3')).toEqual({
      resumeId: null,
      jobId: null,
    })
    expect(readSelection('')).toEqual({ resumeId: null, jobId: null })
    expect(readSelection('?resume=0&job=1.5')).toEqual({
      resumeId: null,
      jobId: null,
    })
  })
})
