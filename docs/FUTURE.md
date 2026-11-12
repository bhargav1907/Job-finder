# Future plans and ideas

> Living backlog for work beyond V1. This is not a commitment or a schedule.
> `PROGRESS.md` is the active milestone; this file holds everything deferred.

## Scope decisions already made

- **V1 is India-only.** Seed demo data is Indian; live ATS boards are chosen for India density.
- **V2+ adds other countries.** The course has students in India, the US, the UK, Australia,
  and other countries still to be confirmed. Do not hardcode India into the data model.
- **Production data comes from employers' own public ATS boards**, not aggregator scraping.
  freehire may be used for research and coverage checks, not as the production feed.

## Multi-country expansion (V2)

The India-only assumption currently lives in board selection, not in a country field. Before
adding a second country, make the country explicit and testable.

- [ ] Confirm the full country list and launch order with Bhargav.
- [ ] Add a country code to each board (`data/boards.json`) or resolve it during discovery.
- [ ] Normalize locations per country: city/state aliases, "remote (India)" variants, and
  country names in local forms.
- [ ] Handle currency and pay period properly: annual vs monthly vs hourly, minor units,
  and never compare salaries across currencies.
- [ ] Add country to the resume profile, filters, and ranking; a salary floor applies only
  within the same currency.
- [ ] Localize role-family and skill dictionaries beyond the current English/India set.
- [ ] Frontend: country selector, salary formatting, and country-aware empty states.
- [ ] Review each country's ATS terms and privacy rules before enabling its boards.
- [ ] Add per-country regression fixtures so India behavior does not drift when the US or
  UK is added.

Country-specific source candidates to evaluate when the time comes: Workday (Accenture
India already resolves there), SuccessFactors, SmartRecruiters, Lever, Ashby, and local
providers. Do not assume one adapter covers every country.

## Source expansion after V1

- [ ] **SmartRecruiters** — largest raw yield in the probe (WNS, RHG, Colliers, Bosch,
  TurnerTownsend); mostly global boards with an India slice.
- [ ] **Freshteam** — probe returned pages without parseable job links; investigate the
  portal before writing the adapter.
- [ ] Workable, Ashby, Lever, Manatal, Comeet, Pinpoint — smaller but cheap keyless APIs.
- [ ] **Workday and SuccessFactors** — needed for MNCs and IT services; heavier adapters.
- [ ] **IT-services fresher portals** — TCS, Infosys, Wipro, HCLTech, Cognizant, Capgemini
  India, LTIMindtree, Tech Mahindra, Mphasis. These are custom portals and the biggest
  entry-level coverage gap.
- [ ] Automated board discovery from public company lists plus careers-page ATS detection.
- [ ] A licensed aggregator (for example Adzuna) only as backfill if ATS coverage is
  insufficient. Never scrape LinkedIn, Indeed, or Naukri.
- [ ] Board-level country tagging and an "India only" filter once the country model exists.
  Prefer board selection over dropping individual jobs at fetch time.

## Posting lifecycle and ingestion health

- [ ] `last_seen_at` and `closed_at` columns; soft-close postings absent from a successful
  crawl. This is a schema change and needs explicit approval.
- [ ] Decide whether an edited posting updates its stored row or keeps the first-seen
  snapshot. Today `(source, external_id)` means it is skipped.
- [ ] Per-board run report: fetched, inserted, skipped, failed, duration.
- [ ] Rate limits, backoff, and a crawl budget per provider.
- [ ] Distinguish "board is empty" from "board is broken" in the ingest output.

## Data quality

- [ ] Parse structured pay ranges where the provider supplies them (Greenhouse
  `pay_input_ranges`, Ashby compensation tiers) with explicit period detection. Never
  guess a currency or period.
- [ ] Cross-board dedupe tuning and a canonical apply URL.
- [ ] HTML-cleaning edge cases: nested lists, tables, and twice-encoded bodies.
- [ ] Validate that every fetched posting has a stable id and title before ingest.

## Product and platform

- [ ] Authentication and student accounts.
- [ ] Postgres + pgvector migration; move embeddings out of SQLite BLOBs.
- [ ] Saved searches, alerts, and application tracking.
- [ ] Deployment plan for the student-facing product.
- [ ] Model upgrades within the 16 GB machine limit; keep rerank cache keys model-aware.
- [ ] Evaluation set for match quality, separate from unit tests.

## Open questions

- Final country list and launch order.
- Does V1 ship live ATS data, or remain a seed-data demo with the demo badge?
- Which country-specific ATS matters most for the first non-India launch?
- Is there budget for a licensed aggregator or API plan if ATS coverage is too thin?
