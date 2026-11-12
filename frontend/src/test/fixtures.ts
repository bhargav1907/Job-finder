import type { Job, RecommendationItem, Resume, ResumeProfile } from '../types'

const TITLES = ['Job one', 'Job two', 'Job three', 'Job four', 'Job five']

const BASE_PROFILE: ResumeProfile = {
  name: 'Asha Rao',
  email: 'asha@example.com',
  phone: '+91 90000 00000',
  location: 'Bengaluru',
  summary: 'Applied AI engineer focused on retrieval systems.',
  total_years_experience: 2.4,
  seniority: 'junior',
  target_roles: ['AI Engineer'],
  preferred_locations: ['Bengaluru'],
  remote_ok: true,
  salary_min: 1_200_000,
  salary_max: 1_800_000,
  currency: 'INR',
  skills: ['python', 'sql', 'rag', 'docker'],
  canonical_skills: ['python', 'sql', 'rag', 'docker'],
  experience: [],
  education: [],
  certifications: [],
  projects: [],
}

export function makeResume(overrides: Partial<Resume> = {}): Resume {
  const base: Resume = {
    id: 7,
    filename: 'asha-rao-resume.txt',
    profile: BASE_PROFILE,
    parse_model: 'qwen3:4b',
    content_hash: 'abc123',
    created_at: '2026-11-01T10:00:00+00:00',
  }

  return {
    ...base,
    ...overrides,
    profile: { ...BASE_PROFILE, ...(overrides.profile ?? {}) },
  }
}

export function makeJob(id: number, overrides: Partial<Job> = {}): Job {
  const base: Job = {
    id,
    title: TITLES[id - 1] ?? `Job ${id}`,
    company: 'Aurora Labs',
    location: 'Bengaluru, India',
    remote: false,
    seniority: 'junior',
    role_family: 'ai_ml',
    salary_min: 1_633_478,
    salary_max: 1_859_703,
    currency: 'INR',
    skills: ['python', 'rag', 'docker'],
    posted_at: '2026-10-24T16:44:52+00:00',
    url: 'https://example.com/jobs/1',
    source: 'demo',
  }

  return { ...base, ...overrides }
}

export function makeItem(
  id: number,
  score = 80,
  overrides: Partial<RecommendationItem> = {},
): RecommendationItem {
  const job = overrides.job ?? makeJob(id)
  const base: RecommendationItem = {
    job,
    score,
    retrieval_score: score / 100,
    matched_skills: job.skills.slice(0, 2),
    reasons: ['Your retrieval work matches the team stack.'],
    gaps: ['kubernetes'],
    reranked: true,
  }

  return { ...base, ...overrides }
}
