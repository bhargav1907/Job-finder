export type Theme = 'dark' | 'light'

export const THEME_KEY = 'fla.theme'

function isTheme(value: unknown): value is Theme {
  return value === 'dark' || value === 'light'
}

export function getStoredTheme(): Theme | null {
  try {
    const stored = localStorage.getItem(THEME_KEY)
    return isTheme(stored) ? stored : null
  } catch {
    return null
  }
}

export function resolveInitialTheme(): Theme {
  return getStoredTheme() ?? 'dark'
}

export function applyTheme(theme: Theme): void {
  document.documentElement.dataset.theme = theme
  document.documentElement.style.colorScheme = theme
}

export function saveTheme(theme: Theme): void {
  try {
    localStorage.setItem(THEME_KEY, theme)
  } catch {
    // Storage can be unavailable in private browsing; the theme still applies.
  }
}
