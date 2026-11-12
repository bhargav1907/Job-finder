# M5 — Frontend design

Date: 2026-11-12
Status: approved by Bhargav ("go with what you chose")

## Intent

Give FLA students a frontend for the existing matching API: upload a resume,
set preferences, and read a ranked shortlist with a fit score, reasons, and the
skills they are missing. The app is an internal demo over seed data. It must
not imply the listings are live.

The design job is to make a career-placement tool feel like it belongs to a
place with a memory — a placement office with candidate files — rather than a
generic SaaS dashboard. Dark is the default; a light mode is a first-class
alternative, not an afterthought.

## Goals

- Complete the core loop: upload → parse → filter → read ranked roles.
- Make the ranking legible: score, why it fits, what is missing.
- Feel specific to a job-placement office, not a template.
- Be usable on a laptop and a phone, with keyboard and screen-reader support.
- Verify visually in a real browser at desktop, tablet, and mobile widths.

## Non-goals

- Auth, accounts, saved applications, or multi-user state.
- Live job fetching from the browser. The API never fetches at runtime.
- Editing the resume profile in the UI.
- Charts, maps, or analytics. No data-viz canvas.
- A design-system package, Storybook, or a component-library skin.

## Anti-goals

- Purple/blue gradients, glass panels, neon-acid accents, glow.
- Identical rounded cards on every surface.
- A hero with a giant number and a gradient accent.
- All-caps eyebrow labels, `A · B · C` meta strings, arrows appended to buttons.
- Claiming live data, or hiding the demo badge.
- Faking parse progress we cannot observe.

## Approaches considered

1. **Placement desk (chosen).** Three panes: candidate file, shortlist, selected
   case file. A warm dark-green desk under a lamp, bone text, brass rules, serif
   titles, mono data, and a stamped fit score. Master-detail is proven for
   triage, and the dossier metaphor gives the visuals a reason to exist.
2. **The register.** One dense ledger of every role with the score in the margin
   and rows expanding in place. Fastest to compare, but a table alone gives the
   product no personality and nudges toward a spreadsheet aesthetic.
3. **Triage deck.** One role at a time with keep/pass and a progress rail. Good
   for deciding, bad for comparing 30 roles, and it adds saved-shortlist state
   that v1 does not need.

The placement desk keeps the comparison power of a list while making the
selected role feel like a file worth reading.

## Design direction

### Palette

Dark — "the desk under a lamp":

| Token | Hex | Use |
| --- | --- | --- |
| desk | `#14201B` | page base, deep green-black |
| raised | `#1B2A23` | selected row, panels |
| sunken | `#0F1814` | wells, rails |
| line | `#2E3D34` | rules and borders |
| line-strong | `#45574A` | selected rule, focus support |
| text | `#E8E0CB` | bone primary text |
| muted | `#9DA896` | secondary text |
| faint | `#6F7C6C` | timestamps, hints |
| brass | `#C9A55C` | accent, selected rules |
| brass-strong | `#E2C079` | focus, score, links |
| rust | `#C46F4E` | gaps, errors |
| green | `#8FAE82` | matched skills, success |

Light — "daylight on the same desk":

| Token | Hex |
| --- | --- |
| desk | `#F2EBDC` |
| raised | `#FBF6EA` |
| sunken | `#E7DECB` |
| line | `#D2C6AC` |
| line-strong | `#B5A78A` |
| text | `#1C231E` |
| muted | `#646E5E` |
| faint | `#8A9281` |
| brass | `#8A671F` |
| brass-strong | `#6F5215` |
| rust | `#9E4B30` |
| green | `#4D6A42` |

No decorative gradients. A fixed, very low-opacity SVG paper grain gives the
surfaces tooth. Contrast targets WCAG AA for body and UI text.

### Typography

- **Newsreader Variable** — candidate name, job titles, section headings,
  reasons. A reading serif with an editorial, printed-file character.
- **Recursive Variable** — UI labels, filters, metadata, buttons, and all
  numbers. The mono axis is reserved for scores, salaries, dates, and counts.

Two families, clearly distinct. Sentence case throughout. No tracked-out caps.
The score is the one place a large numeral earns its size.

### Layout

Desktop (≥ 1200px), within a 1600px frame:

```
┌────────────────────────────────────────────────────────────────┐
│ FLA Placement Office        Demo data   [Night|Day]   Replace  │
├───────────────┬──────────────────────────┬─────────────────────┤
│ CANDIDATE     │ SHORTLIST                │ CASE FILE           │
│ Asha Rao      │ 30 roles                 │ AI Engineer         │
│ 2.4 years     │                          │ Aurora Labs         │
│ Bengaluru     │ 87  AI Engineer          │ ┌──────────┐        │
│               │     Aurora Labs          │ │ 87  FIT  │        │
│ SKILLS        │     Bengaluru · 16–18 LPA│ └──────────┘        │
│ python  sql   │                          │ Why this fits       │
│ rag     docker│ 81  ML Engineer          │ ...                 │
│               │     Atlas · Remote       │ What to build next  │
│ REFINE        │                          │ ...                 │
│ role    [   ] │ 74  Backend Engineer     │ Skills you match    │
│ place   [   ] │     ...                  │ ...                 │
│ pay     [   ] │                          │ Role details        │
│ [x] remote    │ ── Pay not stated ──     │ ...                 │
└───────────────┴──────────────────────────┴─────────────────────┘
```

- 268px candidate rail / 396px shortlist / remaining detail.
- 900–1199px: the candidate rail collapses to a horizontal summary strip with a
  "Refine" disclosure; list and detail share the width.
- < 900px: one column. The shortlist is the index; selecting a role opens the
  case file with a back control. Filters live in a disclosure above the list.

The list is the spine: score and rank in a left margin, title and company in the
middle, pay on the right. Rows are separated by rules, not cards. The selected
row gets a brass margin rule and a slightly raised surface.

### The memorable element

A **fit seal** in the case-file header: a slightly rotated rectangle with a
double rule, the score in Recursive Mono, and the word "FIT". It stamps in when
a role is selected. Everything around it stays quiet.

### Copy

- Empty: "Open your candidate file" / "Drop a resume here, or choose a file.
  PDF, DOCX, or TXT up to 5 MB."
- Parsing: "Reading your resume" / "The local model is extracting experience
  and skills. This can take up to a minute."
- Results: "Shortlist for {first name}" / "{n} roles ranked by fit."
- Sections: "Why this fits", "What to build next", "Skills you match",
  "Role details".
- Demo: visible "Demo data" tag; footer note "Seed listings from
  data/seed_jobs.json. Not live postings."
- Ranking: "Ranked by the local model" or "Model ranking unavailable — showing
  retrieval order." Never pretend a fallback is a full rerank.

### Motion

- One load moment: the header rule draws and the first shortlist rows reveal
  with a short stagger. Not replayed on every filter change.
- The seal stamps on selection (scale 1.06 → 1, opacity, 160ms).
- No hover lift, shadow bloom, or floating cards.
- `prefers-reduced-motion` removes all of it.

## Technical design

### Stack

- Vite 8 + React 19 + TypeScript strict.
- Tailwind CSS v4 (`@tailwindcss/vite`) with tokens in `@theme`; repeated
  structures get small component classes in `@layer components`.
- TanStack Query 5 for server state (caching, retries, loading/error states).
- `@fontsource-variable/newsreader` and `@fontsource-variable/recursive`.
- No router: one screen, selection encoded in `?resume=&job=` with the History
  API. Deep links and back/forward work without a routing dependency.
- No icon library: the handful of glyphs (upload, sun, moon, arrow, external,
  close, check, search) are inline SVG components.
- No headless component library in v1: the only overlay is a mobile filter
  disclosure, built on native `<details>`/`<dialog>` semantics with visible
  labels. If a real combobox/dialog need appears, Base UI is the next step.

### Modules

```
frontend/
  src/
    api.ts              only module that calls the backend
    types.ts            mirrors the Pydantic response models
    App.tsx             screen composition and query wiring
    index.css           tokens, base styles, component classes
    components/
      AppHeader.tsx
      CandidateRail.tsx
      FilterPanel.tsx
      JobList.tsx
      JobRow.tsx
      JobDetail.tsx
      FitSeal.tsx
      UploadView.tsx
      StatusNote.tsx
      icons.tsx
    lib/
      format.ts         LPA, currency, dates, counts
      theme.ts          dark/light preference
      useDebounced.ts
      useUrlState.ts
    test/               Vitest setup and fixtures
  e2e/                  Playwright visual + flow checks
```

### Data flow

- `GET /api/resumes/{id}` validates a stored id and supplies the profile.
- `POST /api/resumes` (multipart) returns the parsed profile and id.
- `GET /api/resumes/{id}/recommendations` returns `items` (salary known) and
  `items_without_salary`, plus rerank status.
- `GET /api/jobs?limit=1` only to detect an empty corpus and show the ingest
  instruction.
- Resume id comes from the URL, then `localStorage`; a 404 clears both.
- Filters: role text, location text, experience years (0/1/2/3/5/8), salary
  minimum (LPA), remote checkbox. Text inputs debounce 350ms. Every filter maps
  to an existing query parameter; no filter is inferred from the resume.

### Score and salary semantics

- `score` is 0–100. Display rounded to an integer. The seal shows the integer;
  the list margin shows the same integer.
- INR salaries are annual rupees; display in LPA (`value / 100_000`, one
  decimal, trailing `.0` dropped). Non-INR uses `Intl.NumberFormat` with a
  compact suffix. Missing salary displays "Pay not stated", never a guess.
- `remote` is shown only when true. False is not relabeled "on-site" because
  the schema cannot distinguish on-site from hybrid.

### Theming

- `data-theme="dark|light"` on `<html>`; dark is the default.
- Preference stored in `localStorage` under `fla.theme`.
- A tiny inline script in `index.html` applies the stored theme before paint.
- Toggle is a two-button segmented control with `aria-pressed`.
- `color-scheme` is set for native controls and scrollbars.

### States

- **Boot:** restore resume id; validate; fetch recommendations.
- **Empty corpus:** explain `python -m app.cli ingest` in the UI.
- **Uploading/parsing:** honest indeterminate status with elapsed seconds; no
  invented step precision.
- **Upload errors:** 415 format, 413 size, 422 empty/unreadable, network; each
  with a concrete next action.
- **Ranking:** loading skeleton as ruled lines; empty filtered state with
  "Clear filters"; partial rerank shown as "Some roles ranked by retrieval
  only"; error with retry.
- **Stale resume id:** clear and return to upload.

### Accessibility

- Landmarks, skip link, one `h1`.
- Shortlist is a list of buttons with roving tabindex: ↑/↓ move, Home/End jump,
  Enter/Space select. `aria-current` marks the selected role.
- Result counts and parse status in `aria-live="polite"`.
- Visible focus ring (2px brass, 2px offset). Visible labels, no
  placeholder-only fields.
- Contrast checked in both themes. Reduced motion respected.

## Verification

- `npm run build` (typecheck + production build).
- `npm test` (Vitest + Testing Library): formatting, filter serialization,
  theme persistence, upload validation, list keyboard behavior.
- `npx playwright test` against a mocked API fixture: dark and light, desktop
  (1440×1000), tablet (1024×900), mobile (390×844); plus an axe accessibility
  scan.
- Inspect the screenshots myself and fix what reads as generic or broken.
- If the local DB and Ollama are available, one real upload against the real
  backend as an integration sanity check.

## Calls made without asking

- Dark is the default even when the OS prefers light.
- No router; URL query state is enough for one screen.
- No component library; native semantics plus custom CSS.
- TanStack Query is the only state dependency.
- Playwright + axe are dev-only and used for the visual/a11y gate.
- "Replace resume" overwrites the stored id in the browser but never deletes
  backend records (no delete endpoint exists).
