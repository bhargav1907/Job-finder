import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach, beforeEach } from 'vitest'

if (!window.matchMedia) {
  window.matchMedia = (query: string) => {
    const minWidth = /min-width:\s*(\d+)px/.exec(query)
    const matches = window.innerWidth >= (minWidth ? Number(minWidth[1]) : 0)
    return {
      matches,
      media: query,
      onchange: null,
      addEventListener: () => {},
      removeEventListener: () => {},
      addListener: () => {},
      removeListener: () => {},
      dispatchEvent: () => false,
    } as MediaQueryList
  }
}

beforeEach(() => {
  localStorage.clear()
  window.history.replaceState({}, '', '/')
  document.documentElement.removeAttribute('data-theme')
})

afterEach(() => {
  cleanup()
})
