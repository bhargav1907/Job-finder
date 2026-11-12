import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach, beforeEach } from 'vitest'

beforeEach(() => {
  localStorage.clear()
  window.history.replaceState({}, '', '/')
  document.documentElement.removeAttribute('data-theme')
})

afterEach(() => {
  cleanup()
})
