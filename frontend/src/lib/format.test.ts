import { describe, expect, it } from 'vitest'
import {
  formatPosted,
  formatRoleFamily,
  formatSalary,
  formatScore,
  formatYears,
} from './format'

describe('format', () => {
  it('rounds and clamps scores', () => {
    expect(formatScore(87.4)).toBe('87')
    expect(formatScore(-1)).toBe('0')
    expect(formatScore(140)).toBe('100')
  })

  it('formats INR annual rupees as LPA', () => {
    expect(
      formatSalary({
        salary_min: 1_633_478,
        salary_max: 1_859_703,
        currency: 'INR',
      }),
    ).toBe('₹16.3–18.6 LPA')
    expect(
      formatSalary({
        salary_min: 1_600_000,
        salary_max: 1_600_000,
        currency: 'INR',
      }),
    ).toBe('₹16 LPA')
  })

  it('formats other currencies without the LPA convention', () => {
    expect(
      formatSalary({
        salary_min: 120_000,
        salary_max: 150_000,
        currency: 'USD',
      }),
    ).toBe('$120K–$150K')
  })

  it('does not invent missing pay', () => {
    expect(
      formatSalary({ salary_min: null, salary_max: null, currency: 'INR' }),
    ).toBe('Pay not stated')
    expect(
      formatSalary({ salary_min: 1_600_000, salary_max: null, currency: 'INR' }),
    ).toBe('Pay not stated')
  })

  it('formats dates and experience', () => {
    expect(formatPosted('2026-10-24T16:44:52+00:00')).toBe('Posted 24 Oct')
    expect(formatPosted(null)).toBe('')
    expect(formatYears(0)).toBe('Fresher')
    expect(formatYears(2.44)).toBe('2.4 years')
    expect(formatYears(1)).toBe('1 year')
  })

  it('humanizes role families', () => {
    expect(formatRoleFamily('ai_ml')).toBe('AI & ML')
    expect(formatRoleFamily('fullstack')).toBe('Full stack')
    expect(formatRoleFamily('quantum')).toBe('quantum')
  })
})
