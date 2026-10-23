# Render performance after Phase 2 (design system, shell, critic trail, Home)

Measured like-for-like: the pre-redesign commit (07f1be5) and the Phase 2 commit (dd40eec)
checked out side by side on local disk and measured with the same `scripts/perf.py`
(AppTest, MOCK_MODE, demo student, 1 warm-up + 7 runs per page), alternating
before, after, before, after. The table uses the second round, the steadier one.

`docs/design/perf-before.md` was measured hours earlier under lighter machine load; every
page measures 15–30% slower now on both commits, so its absolute numbers are not
comparable with these.

| Page | Before median (ms) | After median (ms) | Change | DB calls before → after |
|---|---|---|---|---|
| Home (new) | — | 369 | new page | — → 6 |
| Onboard | 313 | 314 | +0.3% | 3 → 2 |
| Weekly plan | 330 | 336 | +1.8% | 5 → 4 |
| Quiz | 298 | 308 | +3.4% | 3 → 3 |
| Mock interview | 290 | 305 | +5.2% | 2 → 2 |
| Dashboard | 532 | 525 | −1.3% | 8 → 7 |
| Results | 302 | 298 | −1.3% | 1 → 1 |

- No existing page is more than 10% slower; the largest change is +5.2%.
- Database calls per render are fewer or equal on every page.
- Cold start (fresh process to the first full render): 3888 → 4309 ms. The default page is
  now Home, whose first render imports Altair and draws a chart; Onboard drew none.
- `static/`: 150.9 KB (fonts 132 KB, brand 7 KB, stylesheet 2 KB); budget 400 KB.

The 30% target for the pages above 300 ms (Weekly plan, Dashboard) belongs to Phase 6 and
will be measured the same way.
