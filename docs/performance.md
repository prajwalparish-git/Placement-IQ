# Render performance: before and after the redesign

Server-side render time per page, measured with `scripts/perf.py` (Streamlit's AppTest,
MOCK_MODE, the seeded demo student, 1 warm-up and 7 timed runs per page, median).

## Method

- **Like for like.** The Phase 2 code (commit `3f5d695`, which differs from the
  `docs/design/perf-phase2.md` commit `dd40eec` only in documentation and the screenshot
  tool) and the finished redesign (`6723d41`) were checked out side by side on local disk.
  The same, current `scripts/perf.py` was run in both, alternating before, after, before,
  after. Each figure below is the mean of the two rounds' medians.
- **Two modes.** `--mode fresh` (the default, and what `perf-phase2.md` used) builds a new
  AppTest for every run. Each new AppTest first scans every installed package for
  Streamlit components, about 170 ms on this machine, which a running server does once at
  start. So fresh mode mostly measures the test harness: every page sits near the same
  ~235 ms floor. `--mode rerun` reuses one AppTest per page and measures the page's own
  render, as when a student moves between pages in one session.
- **Absolute numbers drift between sessions** with machine load (`perf-phase2.md` measured
  Weekly plan at 336 ms and the Dashboard at 525 ms in an earlier session; the same code
  measures 268 ms and 407 ms here). Only numbers taken in the same session are compared.

## Fresh mode (comparable with `perf-phase2.md`)

| Page | Phase 2 (ms) | Redesign (ms) | Change | DB calls Phase 2 → now |
|---|---|---|---|---|
| Home | 274 | 260 | −5% | 6 → 6 |
| Onboard | 233 | 249 | +7% | 2 → 2 |
| Weekly plan | 268 | 253 | −5% | 4 → 4 |
| Quiz | 240 | 240 | 0% | 3 → 3 |
| Mock interview | 240 | 242 | +1% | 2 → 2 |
| Dashboard | 407 | 271 | **−33%** | 7 → 8 |
| Results | 239 | 241 | +1% | 1 → 1 |

Cold start (fresh process to the first full render): 4663 → 4545 ms.

## Rerun mode (each page's own render)

| Page | Phase 2 (ms) | Redesign (ms) | Change |
|---|---|---|---|
| Home | 56 | 31 | −46% |
| Onboard | 17 | 27 | +10 ms |
| Weekly plan | 38 | 31 | −18% |
| Quiz | 17 | 23 | +6 ms |
| Mock interview | 16 | 21 | +5 ms |
| Dashboard | 189 | 51 | −73% |
| Results | 14 | 17 | +4 ms |

## Against the targets

| Target | Result |
|---|---|
| Dashboard at least 30% faster | Met: −33% fresh, −73% rerun, while showing four more charts (readiness, streak calendar, topic mastery) |
| Weekly plan at least 30% faster | **Not met**: −5% fresh, −18% rerun (see below) |
| No page more than 10% slower | Met in fresh mode (largest: Onboard +7%). In rerun mode the small pages take 4–10 ms longer because they now render more (two profile cards and a chart; the critic trail and question cards; feedback bars) |
| Fewer or equal queries per render | Met against the Phase 1 baseline (Dashboard 8 = 8); the Dashboard's extra call is the readiness history (F2). Streak, topic mastery and plan progress add no query |
| Static assets under 400 KB, CSS under 8 KB, woff2 Latin subsets | Met: 153.4 KB in total (fonts with their licences 142 KB, brand 7 KB, stylesheet 4.5 KB) |

**Why Weekly plan is not 30% faster.** In fresh mode about 85% of each measured render is
AppTest's own per-instance component scan, which no change to the page can reach: the page
script itself takes about 30-40 ms of the ~250 ms. Within the page, the redesign renders
more than before (a day-by-day list with check-off, two charts, the export) and still came
out 18% faster on its own render. The allowed techniques were applied; what is left would
mean dropping content, which the brief rules out.

## What made the difference

- **Cached chart specs** (`6559f0b`). Layering and validating an Altair chart cost 40-60 ms
  on every rerun. Builders still return `alt.Chart` (and are unit-tested), but the views
  render plain Vega-Lite built once per distinct data and kept as JSON text. This is most
  of the Dashboard's gain and why Home got faster.
- **No new queries for new features.** Streak, topic mastery and plan progress reuse rows
  the pages already read, or join onto an existing query.
- **Downloads built on click** (`6723d41`). The plan's CSV and calendar files and the
  quiz and interview notes were built on every render (about 6.6 ms on Weekly plan);
  `st.download_button` now gets a callable.
- **A fragment for the plan section** (`6723d41`). Choosing a week, ticking days, the table
  view and the export inputs rerun only that section. This shortens interactions; it does
  not change the full-render numbers above.
