import { describe, expect, it } from 'vitest'
import {
  EMPTY_FILTERS,
  activeFilterCount,
  filtersToQuery,
  serializeFilters,
} from './filters'

describe('filters', () => {
  it('omits blank values', () => {
    expect(filtersToQuery(EMPTY_FILTERS)).toEqual({})
    expect(serializeFilters(EMPTY_FILTERS)).toBe('')
  })

  it('maps every control to the API contract', () => {
    const filters = {
      role: 'AI Engineer',
      location: 'Bengaluru',
      experienceYears: '3',
      salaryMin: '12',
      remote: true,
    }
    expect(filtersToQuery(filters)).toEqual({
      role: 'AI Engineer',
      location: 'Bengaluru',
      experienceYears: 3,
      salaryMin: 1_200_000,
      remote: true,
    })
    expect(activeFilterCount(filters)).toBe(5)
  })

  it('keeps a fresher experience filter', () => {
    expect(filtersToQuery({ ...EMPTY_FILTERS, experienceYears: '0' })).toEqual({
      experienceYears: 0,
    })
  })

  it('ignores invalid years and non-positive pay', () => {
    expect(
      filtersToQuery({
        ...EMPTY_FILTERS,
        experienceYears: 'abc',
        salaryMin: '-2',
      }),
    ).toEqual({})
    expect(
      filtersToQuery({ ...EMPTY_FILTERS, salaryMin: '0' }),
    ).toEqual({})
  })

  it('serializes deterministically for query keys', () => {
    const a = { ...EMPTY_FILTERS, role: 'AI', remote: true }
    const b = { ...EMPTY_FILTERS, remote: true, role: 'AI' }
    expect(serializeFilters(a)).toBe(serializeFilters(b))
  })
})
