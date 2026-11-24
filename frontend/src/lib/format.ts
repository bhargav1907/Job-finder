import type { Job } from '../types'

function trimDecimal(value: string): string {
  return value.endsWith('.0') ? value.slice(0, -2) : value
}

export function formatScore(score: number): string {
  const rounded = Math.round(Math.min(100, Math.max(0, score)))
  return String(rounded)
}

export function formatSalary(
  job: Pick<Job, 'salary_min' | 'salary_max' | 'currency'>,
): string {
  const { salary_min, salary_max, currency } = job
  if (salary_min === null || salary_max === null) return 'Pay not stated'

  if (currency.toUpperCase() === 'INR') {
    const low = trimDecimal((salary_min / 100_000).toFixed(1))
    const high = trimDecimal((salary_max / 100_000).toFixed(1))
    return low === high ? `₹${low} LPA` : `₹${low}–${high} LPA`
  }

  try {
    const formatter = new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
      maximumFractionDigits: 0,
      notation: 'compact',
    })
    const low = formatter.format(salary_min)
    const high = formatter.format(salary_max)
    return low === high ? low : `${low}–${high}`
  } catch {
    return salary_min === salary_max
      ? `${salary_min} ${currency}`
      : `${salary_min}–${salary_max} ${currency}`
  }
}

export function formatPosted(iso: string | null): string {
  if (!iso) return ''
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return ''
  const formatted = new Intl.DateTimeFormat('en-GB', {
    day: 'numeric',
    month: 'short',
  }).format(date)
  return `Posted ${formatted}`
}

export function formatYears(years: number): string {
  if (!Number.isFinite(years) || years <= 0) return 'Fresher'
  const rounded = Math.round(years * 10) / 10
  const value = Number.isInteger(rounded) ? String(rounded) : rounded.toFixed(1)
  return `${value} ${rounded === 1 ? 'year' : 'years'}`
}

const ROLE_LABELS: Record<string, string> = {
  ai_ml: 'AI & ML',
  data: 'Data',
  devops: 'DevOps',
  qa: 'QA',
  mobile: 'Mobile',
  frontend: 'Frontend',
  backend: 'Backend',
  fullstack: 'Full stack',
  product: 'Product',
  other: 'Other',
}

export function formatRoleFamily(family: string): string {
  return ROLE_LABELS[family] ?? family
}
