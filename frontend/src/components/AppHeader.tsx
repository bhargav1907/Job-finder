import { FileIcon, FolderMark, MoonIcon, SunIcon } from './icons'
import type { Resume } from '../types'
import type { Theme } from '../lib/theme'

interface AppHeaderProps {
  resume: Resume | null
  theme: Theme
  onToggleTheme: (theme: Theme) => void
  onReplace: () => void
}

export function AppHeader({
  resume,
  theme,
  onToggleTheme,
  onReplace,
}: AppHeaderProps) {
  return (
    <header className="sticky top-0 z-30 flex h-14 items-center justify-between gap-4 border-b border-line bg-desk px-4 sm:px-6">
      <a
        href="/"
        className="flex min-w-0 items-center gap-2.5 text-ink no-underline"
        aria-label="FLA Placement Office home"
      >
        <FolderMark className="h-7 w-7 shrink-0 text-brass-strong" />
        <span className="font-display text-[19px] leading-none tracking-[-0.01em]">
          FLA <span className="hidden text-muted sm:inline">Placement Office</span>
        </span>
      </a>

      <div className="flex shrink-0 items-center gap-3 sm:gap-4">
        <span
          className="hidden items-center gap-1.5 text-[11px] text-muted md:inline-flex"
          title="Seed listings from data/seed_jobs.json. Not live postings."
        >
          <span aria-hidden="true" className="h-1.5 w-1.5 bg-rust" />
          Demo data
        </span>

        {resume ? (
          <button
            type="button"
            onClick={onReplace}
            className="hidden items-center gap-1.5 border border-line px-2.5 py-1.5 text-[12px] text-muted transition-colors hover:border-line-strong hover:text-ink sm:inline-flex"
          >
            <FileIcon className="h-3.5 w-3.5" />
            Replace resume
          </button>
        ) : null}

        <div
          className="flex items-center border border-line p-0.5"
          role="group"
          aria-label="Theme"
        >
          <button
            type="button"
            aria-pressed={theme === 'dark'}
            aria-label="Use the dark theme"
            onClick={() => onToggleTheme('dark')}
            className={`flex items-center gap-1.5 px-2 py-1 text-[11px] transition-colors ${
              theme === 'dark'
                ? 'bg-raised text-ink'
                : 'text-muted hover:text-ink'
            }`}
          >
            <MoonIcon className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Night</span>
          </button>
          <button
            type="button"
            aria-pressed={theme === 'light'}
            aria-label="Use the light theme"
            onClick={() => onToggleTheme('light')}
            className={`flex items-center gap-1.5 px-2 py-1 text-[11px] transition-colors ${
              theme === 'light'
                ? 'bg-raised text-ink'
                : 'text-muted hover:text-ink'
            }`}
          >
            <SunIcon className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Day</span>
          </button>
        </div>
      </div>
    </header>
  )
}
