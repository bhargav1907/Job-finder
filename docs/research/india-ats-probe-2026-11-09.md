# India ATS discovery probe — 2026-11-09

Research question: if FLA Job Finder cannot use freehire's aggregator data in production,
which employer ATS boards can we crawl directly for Indian openings, and how much do they
yield?

Method: sampled freehire's India slice (500 postings at fixed offsets across its catalogue),
classified each posting's apply URL, then called each detected ATS's public board API once,
read-only. Nothing was written to FLA's database and no aggregator was crawled.

## What the sample showed

- freehire reports 206,181 India-located postings in total.
- Of the 500 sampled: **23% ATS-direct**, **74% aggregator**, **3% custom/unresolved**.
- The aggregator share was Naukri 171, Shine 142, Telegram 25, hirist 8, iimjobs 8,
  Himalayas 16. Those are not sources we may scrape.
- Resolving employer URLs produced **32 validated ATS boards**.

## Yield by ATS

| ATS | Boards | Live jobs | India-located |
| --- | ---: | ---: | ---: |
| SmartRecruiters | 5 | 10,146 | 204 (first 300 sampled) |
| Darwinbox | 8 | 2,855 | 500 (first 100 per board sampled) |
| Greenhouse | 7 | 674 | 71 |
| Keka | 3 | 98 | 95 |
| Manatal | 2 | 38 | 17 |
| Ashby | 1 | 31 | 3 |

India density is the point: Darwinbox and Keka boards are almost entirely Indian roles,
while Greenhouse and SmartRecruiters are mostly global boards that happen to carry an India
slice. Freshteam returned pages without parseable job links in this probe, so its zero is a
limitation of the probe, not a platform verdict.

Largest validated boards: PwC India (`pwc.darwinbox.com`, 1,252), AU Small Finance Bank
(`autalenthub.darwinbox.in`, 977), Kotak Life (231), PAPL (181), WNS via SmartRecruiters
(367), Mahindra Logistics (47), Softobiz on Keka (43), Bosch (5,084, 31 in India), and
Razorpay on Greenhouse (23, 20 in India).

## The gap

The fresher-heavy IT-services employers — TCS, Infosys, Wipro, HCLTech, Cognizant,
Capgemini India, LTIMindtree, Tech Mahindra, Mphasis — resolve to custom career portals with
no public ATS board. Accenture India is the exception (Workday). These employers are the
largest source of entry-level Indian hiring and need dedicated adapters or licensed
aggregator backfill; ATS boards alone will not cover them.

## Implications for FLA

1. Start with **Darwinbox, Keka, and Greenhouse** adapters behind the existing `JobSource`
   protocol. They are keyless, public, India-dense, and cover the boards already validated.
2. Add **SmartRecruiters** next; it has the largest raw yield and a simple public API.
3. Treat ATS-only coverage as smaller but higher quality than freehire's. Do not chase
   volume with aggregator scraping.
4. Use freehire only for internal research and coverage benchmarking. Its licence permits
   commercial product use only with an API plan (`docs/research` note in memory:
   `freehire-api-licence`).
5. Posting lifecycle (marking vanished postings closed) needs `last_seen_at`/`closed_at`
   columns; that is a schema change and is deferred until explicitly approved.

## Caveats

- India counts are location-string heuristics, not a census.
- The sample over-represents companies freehire already crawls.
- Board contents change; re-validate before relying on a specific hostname.
