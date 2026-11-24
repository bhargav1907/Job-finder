import type { RecommendationFilters } from '../api'

export interface FilterState {
  role: string
  location: string
  experienceYears: string
  salaryMin: string
  remote: boolean
}

export const EMPTY_FILTERS: FilterState = {
  role: '',
  location: '',
  experienceYears: '',
  salaryMin: '',
  remote: false,
}

function parseNonNegativeInt(value: string): number | null {
  const trimmed = value.trim()
  if (!/^\d+$/.test(trimmed)) return null
  const parsed = Number(trimmed)
  return Number.isSafeInteger(parsed) ? parsed : null
}

function parsePositiveInt(value: string): number | null {
  const parsed = parseNonNegativeInt(value)
  return parsed !== null && parsed > 0 ? parsed : null
}

export function filtersToQuery(filters: FilterState): RecommendationFilters {
  const query: RecommendationFilters = {}
  if (filters.role.trim()) query.role = filters.role.trim()
  if (filters.location.trim()) query.location = filters.location.trim()

  const years = parseNonNegativeInt(filters.experienceYears)
  if (years !== null) query.experienceYears = years

  const salaryLpa = parsePositiveInt(filters.salaryMin)
  if (salaryLpa !== null) query.salaryMin = salaryLpa * 100_000

  if (filters.remote) query.remote = true
  return query
}

export function activeFilterCount(filters: FilterState): number {
  return Object.keys(filtersToQuery(filters)).length
}

export function serializeFilters(filters: FilterState): string {
  const query = filtersToQuery(filters)
  return Object.keys(query)
    .sort()
    .map((key) => `${key}=${String(query[key as keyof RecommendationFilters])}`)
    .join('&')
}
