import type { JobList, RecommendationList, Resume } from './types'

export interface RecommendationFilters {
  location?: string
  remote?: boolean
  experienceYears?: number
  role?: string
  salaryMin?: number
  limit?: number
}

export class ApiError extends Error {
  readonly status: number
  readonly detail: string

  constructor(status: number, detail: string) {
    super(detail)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(path, init)
  } catch {
    throw new ApiError(
      0,
      'The backend is not responding. Is it running on port 8000?',
    )
  }

  if (!response.ok) {
    let detail = response.statusText || `Request failed (${response.status})`
    try {
      const body = (await response.json()) as { detail?: unknown }
      if (typeof body.detail === 'string') detail = body.detail
    } catch {
      // Keep the status-based fallback when the body is not JSON.
    }
    throw new ApiError(response.status, detail)
  }

  return (await response.json()) as T
}

export async function uploadResume(file: File): Promise<Resume> {
  const form = new FormData()
  form.append('file', file)
  return request<Resume>('/api/resumes', { method: 'POST', body: form })
}

export async function getResume(id: number): Promise<Resume> {
  return request<Resume>(`/api/resumes/${id}`)
}

function recommendationQuery(filters: RecommendationFilters): URLSearchParams {
  const params = new URLSearchParams()
  if (filters.location?.trim()) params.set('location', filters.location.trim())
  if (filters.remote !== undefined) params.set('remote', String(filters.remote))
  if (filters.experienceYears !== undefined) {
    params.set('experience_years', String(filters.experienceYears))
  }
  if (filters.role?.trim()) params.set('role', filters.role.trim())
  if (filters.salaryMin !== undefined) {
    params.set('salary_min', String(filters.salaryMin))
  }
  if (filters.limit !== undefined) params.set('limit', String(filters.limit))
  return params
}

export async function getRecommendations(
  id: number,
  filters: RecommendationFilters,
): Promise<RecommendationList> {
  const params = recommendationQuery(filters)
  const query = params.toString()
  return request<RecommendationList>(
    `/api/resumes/${id}/recommendations${query ? `?${query}` : ''}`,
  )
}

export async function getJobsCount(): Promise<number> {
  const data = await request<JobList>('/api/jobs?limit=1')
  return data.total
}
