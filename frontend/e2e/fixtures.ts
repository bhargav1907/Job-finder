import type { Page } from '@playwright/test'
import type {
  Job,
  RecommendationItem,
  RecommendationList,
  Resume,
} from '../src/types'

export const RESUME_ID = 7
export const FIRST_JOB_ID = 101

export const resume: Resume = {
  id: RESUME_ID,
  filename: 'asha-rao-resume.pdf',
  profile: {
    name: 'Asha Rao',
    email: 'asha.rao@example.com',
    phone: '+91 98450 11223',
    location: 'Bengaluru',
    summary:
      'Applied AI engineer building retrieval systems for customer support.',
    total_years_experience: 2.4,
    seniority: 'junior',
    target_roles: ['AI Engineer', 'ML Engineer'],
    preferred_locations: ['Bengaluru', 'Remote'],
    remote_ok: true,
    salary_min: 1_400_000,
    salary_max: 2_000_000,
    currency: 'INR',
    skills: [
      'python',
      'sql',
      'rag',
      'langchain',
      'docker',
      'fastapi',
      'pytorch',
      'vector search',
    ],
    canonical_skills: [
      'python',
      'sql',
      'rag',
      'langchain',
      'docker',
      'fastapi',
      'pytorch',
      'vector search',
    ],
    experience: [],
    education: [],
    certifications: [],
    projects: [],
  },
  parse_model: 'qwen3:4b',
  content_hash: 'demo-hash',
  created_at: '2026-11-10T09:00:00+00:00',
}

interface Seed {
  id: number
  title: string
  company: string
  location: string
  remote?: boolean
  salary: [number, number] | null
  skills: string[]
  score: number
  roleFamily?: string
  seniority?: string
  reasons: string[]
  gaps: string[]
  reranked?: boolean
  postedAt: string
}

const SEEDS: Seed[] = [
  {
    id: 101,
    title: 'AI Engineer, Retrieval',
    company: 'Karya Labs',
    location: 'Bengaluru, India',
    salary: [2_400_000, 3_200_000],
    skills: ['python', 'rag', 'vector search', 'fastapi'],
    score: 93,
    reasons: [
      'You have built retrieval pipelines with RAG, the core of this role.',
      'Your Python and FastAPI work matches the team serving stack.',
    ],
    gaps: ['kubernetes'],
    postedAt: '2026-11-08T06:30:00+00:00',
  },
  {
    id: 102,
    title: 'Machine Learning Engineer',
    company: 'Palava Analytics',
    location: 'Hyderabad, India',
    salary: [2_100_000, 2_800_000],
    skills: ['python', 'pytorch', 'mlops', 'sql'],
    score: 90,
    reasons: [
      'Your PyTorch and SQL background covers the modelling work here.',
      'The team ships models into production, which matches your stack.',
    ],
    gaps: ['mlflow'],
    postedAt: '2026-11-07T11:00:00+00:00',
  },
  {
    id: 103,
    title: 'Applied AI Engineer',
    company: 'Kestrel AI',
    location: 'Remote (India)',
    remote: true,
    salary: [1_800_000, 2_600_000],
    skills: ['python', 'rag', 'langchain', 'docker'],
    score: 88,
    reasons: [
      'You already work with LangChain and RAG in production settings.',
      'The role is remote-first, which fits your stated preference.',
    ],
    gaps: ['kubernetes', 'terraform'],
    postedAt: '2026-11-06T09:15:00+00:00',
  },
  {
    id: 104,
    title: 'Data Engineer, Analytics',
    company: 'Banyan Data',
    location: 'Bengaluru, India',
    salary: [1_500_000, 2_200_000],
    skills: ['sql', 'python', 'airflow', 'dbt'],
    score: 85,
    roleFamily: 'data',
    reasons: [
      'Strong SQL and Python are the two skills this pipeline team leans on.',
      'Your location matches the Bengaluru office.',
    ],
    gaps: ['dbt'],
    postedAt: '2026-11-05T14:20:00+00:00',
  },
  {
    id: 105,
    title: 'Backend Engineer, Python',
    company: 'Northline Systems',
    location: 'Pune, India',
    salary: [1_400_000, 2_000_000],
    skills: ['python', 'fastapi', 'postgres', 'docker'],
    score: 83,
    roleFamily: 'backend',
    reasons: [
      'You have shipped FastAPI services with Docker, as this team does.',
      'The role sits close to your salary range.',
    ],
    gaps: ['kafka'],
    postedAt: '2026-11-04T08:10:00+00:00',
  },
  {
    id: 106,
    title: 'AI Product Engineer',
    company: 'Roundhouse',
    location: 'Bengaluru, India',
    salary: [1_600_000, 2_400_000],
    skills: ['python', 'rag', 'react', 'sql'],
    score: 80,
    reasons: [
      'Your RAG work maps to the assistant this team is building.',
      'They want an engineer who can own retrieval end to end.',
    ],
    gaps: ['typescript'],
    postedAt: '2026-11-03T16:40:00+00:00',
  },
  {
    id: 107,
    title: 'Research Engineer, NLP',
    company: 'Meridian Health',
    location: 'Hyderabad, India',
    salary: [2_000_000, 2_900_000],
    skills: ['pytorch', 'transformers', 'python', 'sql'],
    score: 78,
    reasons: [
      'Your PyTorch experience is relevant to their clinical NLP work.',
      'They value SQL for cohort analysis alongside modelling.',
    ],
    gaps: ['distributed training'],
    postedAt: '2026-11-02T10:05:00+00:00',
  },
  {
    id: 108,
    title: 'Platform Engineer',
    company: 'Cobalt Works',
    location: 'Remote (India)',
    remote: true,
    salary: [1_700_000, 2_500_000],
    skills: ['docker', 'kubernetes', 'terraform', 'python'],
    score: 75,
    roleFamily: 'devops',
    reasons: [
      'Your Docker experience is a starting point for this platform team.',
      'They work remotely across India, matching your preference.',
    ],
    gaps: ['kubernetes', 'terraform'],
    postedAt: '2026-11-01T12:00:00+00:00',
  },
  {
    id: 109,
    title: 'ML Engineer, Search',
    company: 'Loom & Ledger',
    location: 'Gurugram, India',
    salary: [1_900_000, 2_700_000],
    skills: ['python', 'elasticsearch', 'rag', 'sql'],
    score: 72,
    reasons: [
      'Your retrieval background transfers to their search stack.',
      'They need someone comfortable evaluating ranking quality.',
    ],
    gaps: ['elasticsearch'],
    postedAt: '2026-10-30T09:45:00+00:00',
  },
  {
    id: 110,
    title: 'Solutions Engineer, AI',
    company: 'Pilot Fish',
    location: 'Mumbai, India',
    salary: [1_200_000, 1_800_000],
    skills: ['python', 'fastapi', 'docker', 'sql'],
    score: 69,
    roleFamily: 'other',
    reasons: [
      'Your Python and FastAPI skills cover the integration work.',
      'The role is a step toward customer-facing AI delivery.',
    ],
    gaps: ['customer discovery'],
    postedAt: '2026-10-29T15:30:00+00:00',
  },
  {
    id: 111,
    title: 'Junior Data Scientist',
    company: 'Areca Technologies',
    location: 'Bengaluru, India',
    salary: [900_000, 1_400_000],
    skills: ['python', 'pandas', 'sql', 'scikit-learn'],
    score: 66,
    roleFamily: 'data',
    reasons: [],
    gaps: [],
    reranked: false,
    postedAt: '2026-10-28T07:55:00+00:00',
  },
  {
    id: 112,
    title: 'AI Engineer, Evaluation',
    company: 'Tinker & Co',
    location: 'Remote (India)',
    remote: true,
    salary: [1_600_000, 2_300_000],
    skills: ['python', 'pytest', 'rag', 'sql'],
    score: 62,
    reasons: [],
    gaps: [],
    reranked: false,
    postedAt: '2026-10-27T13:10:00+00:00',
  },
  {
    id: 113,
    title: 'Founding AI Engineer',
    company: 'Fold Health',
    location: 'Bengaluru, India',
    salary: null,
    skills: ['python', 'rag', 'fastapi', 'docker'],
    score: 71,
    reasons: [
      'You have the retrieval and API skills a founding team needs.',
      'You are based in Bengaluru, where the team works in person.',
    ],
    gaps: ['kubernetes'],
    postedAt: '2026-11-08T08:00:00+00:00',
  },
  {
    id: 114,
    title: 'NLP Engineer',
    company: 'Varna Systems',
    location: 'Hyderabad, India',
    salary: null,
    skills: ['pytorch', 'transformers', 'python'],
    score: 64,
    reasons: [
      'Your PyTorch work is relevant to their document models.',
      'They are open to candidates without production NLP experience.',
    ],
    gaps: ['speech'],
    postedAt: '2026-11-04T10:30:00+00:00',
  },
  {
    id: 115,
    title: 'Data Analyst, Growth',
    company: 'Hearthside',
    location: 'Remote (India)',
    remote: true,
    salary: null,
    skills: ['sql', 'python', 'tableau'],
    score: 58,
    roleFamily: 'data',
    reasons: [],
    gaps: [],
    reranked: false,
    postedAt: '2026-10-31T11:20:00+00:00',
  },
  {
    id: 116,
    title: 'ML Intern',
    company: 'Areca Technologies',
    location: 'Bengaluru, India',
    salary: null,
    skills: ['python', 'sql', 'scikit-learn'],
    score: 51,
    reasons: [
      'This internship matches your Python and SQL foundation.',
      'It is a route into applied ML if you want more mentoring.',
    ],
    gaps: ['pytorch'],
    postedAt: '2026-10-26T06:00:00+00:00',
  },
]

function toItem(seed: Seed): RecommendationItem {
  const job: Job = {
    id: seed.id,
    title: seed.title,
    company: seed.company,
    location: seed.location,
    remote: seed.remote ?? false,
    seniority: seed.seniority ?? 'junior',
    role_family: seed.roleFamily ?? 'ai_ml',
    salary_min: seed.salary?.[0] ?? null,
    salary_max: seed.salary?.[1] ?? null,
    currency: 'INR',
    skills: seed.skills,
    posted_at: seed.postedAt,
    url: `https://example.com/jobs/${seed.id}`,
    source: 'demo',
  }

  return {
    job,
    score: seed.score,
    retrieval_score: seed.score / 100,
    matched_skills: job.skills
      .filter((skill) => resume.profile.canonical_skills.includes(skill))
      .slice(0, 2),
    reasons: seed.reasons,
    gaps: seed.gaps,
    reranked: seed.reranked ?? true,
  }
}

const items = SEEDS.filter((seed) => seed.salary !== null).map(toItem)
const itemsWithoutSalary = SEEDS.filter((seed) => seed.salary === null).map(
  toItem,
)

export const recommendations: RecommendationList = {
  resume_id: RESUME_ID,
  items,
  items_without_salary: itemsWithoutSalary,
  total: items.length,
  without_salary_total: itemsWithoutSalary.length,
  limit: 30,
  retrieval_version: 'v1',
  rerank_status: 'ok',
  rerank_version: 'rerank-v1@lfm3:1.7b',
}

export async function installRoutes(page: Page): Promise<void> {
  await page.route('**/api/resumes/7/recommendations*', (route) =>
    route.fulfill({ json: recommendations }),
  )
  await page.route('**/api/resumes/7', (route) =>
    route.fulfill({ json: resume }),
  )
  await page.route('**/api/jobs?*', (route) =>
    route.fulfill({
      json: { items: [], total: 16, limit: 1, offset: 0 },
    }),
  )
  await page.route('**/api/resumes', (route) =>
    route.request().method() === 'POST'
      ? route.fulfill({ json: resume })
      : route.fulfill({ status: 404, json: { detail: 'Not mocked' } }),
  )
}
