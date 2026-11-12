export type Seniority = 'intern' | 'junior' | 'mid' | 'senior' | 'lead'

export interface Job {
  id: number
  title: string
  company: string
  location: string
  remote: boolean
  seniority: string
  role_family: string
  salary_min: number | null
  salary_max: number | null
  currency: string
  skills: string[]
  posted_at: string | null
  url: string
  source: string
}

export interface ExperienceEntry {
  title: string
  company: string
  start: string
  end: string
  highlights: string[]
}

export interface EducationEntry {
  degree: string
  institution: string
  year: string
}

export interface ResumeProfile {
  name: string
  email: string
  phone: string
  location: string
  summary: string
  total_years_experience: number
  seniority: Seniority
  target_roles: string[]
  preferred_locations: string[]
  remote_ok: boolean
  salary_min: number | null
  salary_max: number | null
  currency: string
  skills: string[]
  canonical_skills: string[]
  experience: ExperienceEntry[]
  education: EducationEntry[]
  certifications: string[]
  projects: string[]
}

export interface Resume {
  id: number
  filename: string
  profile: ResumeProfile
  parse_model: string
  content_hash: string
  created_at: string
}

export interface RecommendationItem {
  job: Job
  score: number
  retrieval_score: number
  matched_skills: string[]
  reasons: string[]
  gaps: string[]
  reranked: boolean
}

export type RerankStatus = 'ok' | 'partial' | 'unavailable'

export interface RecommendationList {
  resume_id: number
  items: RecommendationItem[]
  items_without_salary: RecommendationItem[]
  total: number
  without_salary_total: number
  limit: number
  retrieval_version: string
  rerank_status: RerankStatus
  rerank_version: string
}

export interface JobList {
  items: Job[]
  total: number
  limit: number
  offset: number
}
