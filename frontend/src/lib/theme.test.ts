import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  applyTheme,
  getStoredTheme,
  resolveInitialTheme,
  saveTheme,
  THEME_KEY,
} from './theme'

describe('theme', () => {
  beforeEach(() => {
    localStorage.clear()
    document.documentElement.removeAttribute('data-theme')
    vi.restoreAllMocks()
  })

  it('defaults to dark when nothing is stored', () => {
    expect(resolveInitialTheme()).toBe('dark')
  })

  it('applies and persists a theme', () => {
    saveTheme('light')
    applyTheme('light')
    expect(getStoredTheme()).toBe('light')
    expect(document.documentElement.dataset.theme).toBe('light')
    expect(document.documentElement.style.colorScheme).toBe('light')
  })

  it('ignores an invalid stored value', () => {
    localStorage.setItem(THEME_KEY, 'sepia')
    expect(getStoredTheme()).toBeNull()
    expect(resolveInitialTheme()).toBe('dark')
  })
})
