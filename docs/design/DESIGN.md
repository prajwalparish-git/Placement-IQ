# PlacementIQ design system

How the interface looks and why. The values live in code: `piq/config.py` (`PALETTE`,
`SEMANTIC_COLORS`, `TOPIC_COLORS`, `BRAND_COLOR`) and `.streamlit/config.toml`, which
mirrors them because Streamlit reads only TOML. `tests/test_theme.py` checks that the two
agree and that every ratio below holds.

## Direction

A calm study-desk coach. The audience is an engineering student preparing for campus
placements, often anxious and on a 1366×768 laptop or a phone, and a faculty evaluator
watching on a projector. So the interface is quiet and exact: petrol teal and warm slate on
near-white (or deep slate in dark mode), one sentence of purpose on every page, numbers
large enough to read from the back of a room, and colour only where it carries meaning.

The one bold element is the **critic loop**. Every plan, quiz and interview question is
checked by a critic before the student sees it; the app shows that loop as a step-by-step
trail (generated, rejected with the critic's own words, regenerated, approved), because it
is what makes PlacementIQ different and what an evaluator needs to see.

Principles, in priority order:
1. One clear job per screen: a header with the title, one plain sentence and the primary
   action.
2. Hierarchy through type, weight and space before colour.
3. Show the adaptivity: week-over-week change, the "why" and critic rejections are content.
4. Calm density: an 8px rhythm, cards one level deep, no decoration that encodes nothing.
5. Legible at a distance: body 16px, nothing important below 14px, key numbers 36px.
6. Every state is designed: empty, loading, running, success, partial failure, error, mock.

## Colour

Both schemes follow Streamlit's light/dark setting. Ratios are WCAG 2 contrast against the
page background (bg) or the surface layer (sidebar, inputs, table headers).

### Neutrals and primary

| Token | Light | Ratio | Dark | Ratio | Use |
|---|---|---|---|---|---|
| background | `#FBFBFA` | | `#111A1C` | | Page |
| surface | `#F0F2F0` | | `#1A2528` | | Sidebar, inputs, table headers |
| text | `#1A2326` | 15.5 bg, 14.2 surface | `#E3EAE8` | 14.5, 12.8 | Body and headings |
| muted | `#566461` | 6.0, 5.5 | `#A0AEAB` | 7.7, 6.8 | Captions, secondary text |
| border | `#7A8582` | 3.7, 3.4 | `#64716E` | 3.5, 3.1 | Input edges (must be found) |
| hairline | `#DCE1DE` | 1.3 | `#2C383B` | 1.5 | Card and table rules (decorative) |
| primary | `#0D6670` | 6.4 bg; white label 6.7 | `#1F7F86` | 3.7 bg; white label 4.7 | Primary buttons, focus, progress, today's focus |
| primary text | `#0D6670` | 6.4 | `#6CCBC4` | 9.2 | Links and teal text |

The accent proposed at Checkpoint A (amber) was dropped: every warm hue sat too close to a
topic colour (amber vs Aptitude measured 0.038 OKLab in light, 0.023 in dark). Today's focus
and streaks use primary teal plus an icon instead.

### Status colours

Every status shows an icon and words; colour is never the only signal. Each status colour
sits at least 0.08 OKLab from every topic colour (the rejected amber failed this).

| Status | Light | bg / on its alert tint | Dark | bg / tint | Nearest topic (light, dark) |
|---|---|---|---|---|---|
| success | `#1B6F36` | 6.0 / 5.2 | `#5BBF7A` | 7.7 / 5.3 | 0.137, 0.120 |
| warning | `#784E00` | 7.0 / 6.1 | `#F0D45C` | 12.0 / 7.3 | 0.115, 0.107 |
| error | `#951B2C` | 8.2 / 6.9 | `#FF8675` | 7.5 / 5.3 | 0.101, 0.104 |
| info | `#0045D2` | 7.3 / 6.2 | `#A9BCF5` | 9.4 / 6.2 | 0.107, 0.096 |

Alert tints are Streamlit's own (10% of the colour over the background in light, 20% in
dark); the test also checks them over the surface layer, which is how the dark error red
was found too weak (4.06:1) and lightened.

### Topic colours

The six syllabus topics keep one colour each, everywhere: Okabe–Ito hues without yellow
(designed for colour-vision deficiency), lightness-tuned per scheme to at least 3:1 on the
background, and at least 0.10 OKLab apart.

| Topic | Light | bg | Dark | bg |
|---|---|---|---|---|
| Aptitude | `#C78100` | 3.1 | `#EFA71C` | 8.6 |
| DBMS | `#005D9C` | 6.7 | `#0975B6` | 3.6 |
| OS | `#A55582` | 4.8 | `#DF8BB9` | 7.2 |
| CN | `#009B71` | 3.4 | `#009B71` | 5.0 |
| DSA | `#B23D00` | 5.7 | `#D05900` | 4.3 |
| OOP | `#3799CC` | 3.1 | `#55B4E8` | 7.6 |

Rules: topic colours appear only as chart marks or as chips that show the topic name,
never as a status fill. Under simulated deuteranopia and protanopia the closest pairs drop
to about 0.06 OKLab, so charts also carry direct labels and tooltips.

### Brand

`BRAND_COLOR` `#278C93` is a single mid teal for the logo, because an image cannot follow
the light/dark switch. It keeps at least 3:1 on both backgrounds and both sidebars (3.5 to
4.4).

## Type

| Role | Font | Size | Weight |
|---|---|---|---|
| Page title (h1) | Bricolage Grotesque | 36px | 700 |
| Section (h2) | Bricolage Grotesque | 24px | 700 |
| Card title (h3) | Bricolage Grotesque | 18px | 600 |
| Body, labels | Atkinson Hyperlegible Next | 16px | 400, 700 for emphasis |
| Small, captions, code | Atkinson / JetBrains Mono | 14px | 400 |
| Key numbers (metrics) | Bricolage Grotesque, tabular digits | 36px | 700 |

- **Atkinson Hyperlegible Next** carries everything students read: it was designed to keep
  letters unambiguous for low-vision readers, which also helps on a projector. Its slashed
  zero makes USNs such as DEMO0001 unambiguous.
- **Bricolage Grotesque** gives headings a confident, slightly hand-made voice; its optical
  size axis tightens it at display sizes.
- **JetBrains Mono** is only for code and commands, not for small labels.

All three are OFL fonts, self-hosted as Latin-subset woff2 files in `static/fonts/` with
their licences (132 KB in total). No font CDN is called at runtime, so the app works
offline in a lab.

## Shape, space and icons

- One base radius and one button radius: 8px (`0.5rem`).
- Inputs keep the 3:1 border; cards and stat cards get a hairline (`static/app.css`),
  because their edge only groups content.
- 8px spacing rhythm; prose capped near 72 characters a line.
- Icons are Material Symbols (one rounded style) in navigation, buttons, headers and
  badges. No emoji are used as icons.

## Brand

`static/brand/mark.svg` is a geometric "IQ" monogram on a rounded tile: a bar for the I and,
for the Q, a ring drawn as a readiness gauge (a solid three-quarter arc over a faint track)
with a flat tail that echoes the wordmark's Q. `static/brand/wordmark.svg` is "PlacementIQ"
in Bricolage Grotesque Bold, converted to outlines so it needs no font. The sidebar shows the
wordmark (the tile when collapsed) and the tile is the browser icon. Two earlier ideas were
rejected after rendering them: a "P" on a tile reads as a parking sign, and a Q with a
diagonal tail reads as a search icon.

## Navigation

Sidebar navigation with two sections, **Prepare** (Home, Onboard, Weekly plan, Quiz, Mock
interview) and **Insights** (Dashboard, Results). A top bar was considered: it gives the
page more width, but folds the sections into menus, hiding pages from a projector audience,
and the student switcher needs the sidebar anyway. Under the navigation: the student picker,
their readiness at a glance and, in mock mode, a grey "Mock mode" badge.

## Components (`piq/ui.py`)

| Component | Use |
|---|---|
| `page_header(title, purpose, action)` | Opens every page: title, one sentence, the primary action |
| `empty_state(icon, title, body, action)` | An empty screen as an invitation: what is missing, the one next step |
| `stat_row([Stat(...)])` | Bordered, equal-height key numbers; they stack on phones |
| `topic_chip(topic)` | The topic's colour as a dot next to its name |
| `status_badge(state, text)` / `formatter.status_md` | Icon plus words for done, to do, warning, error, info |
| `run_agent` / `show_last_run` | The critic trail (below) |

**The critic trail.** Each agent run is a status box ("Quiz agent — done", "— failed" or
"— last run[ failed]", unchanged) holding native timeline steps (`st.status(type="step")`):
Generated the quiz, Critic rejected the quiz (with the reasons, numbered like the quiz),
Regenerated the quiz, Critic approved the quiz, or Stopped. A repeated rejection says "Same
reason as before." Every step has a line of content, because an empty step ends the
timeline. The box opens by itself after a retry or a failure.

## Charts (`piq/charts.py`)

- Builders are pure functions returning `alt.Chart`; tests check marks, encodings, scales,
  formats and titles.
- One shared look (`themed`): theme fonts, no frame, quiet axes.
- The takeaway is a sentence ("OS is your weakest topic"), shown as a heading above the
  chart rather than inside it: an in-canvas title is clipped on a phone, text wraps.
- Topic series use a fixed `TOPICS` domain and no range: the theme's per-scheme topic
  palette colours them, so OS is the same colour in every chart and both schemes.
- Vega text marks do not follow the light/dark switch (axis labels do), so values go into
  axis labels ("OS  43%"), and neutral marks such as a threshold line use
  `charts.NEUTRAL`, a grey that keeps 3:1 on both backgrounds.
- Direct labels instead of legends where possible, tooltips on every mark, consistent
  formats (`%`, `min`, `/5`) and an `alt` description for screen readers.

## The stylesheet (`static/app.css`)

Only what the theme cannot express, under 150 lines and 8 KB: hairline card edges, metric
values in the heading face, a prose measure, visible focus rings and reduced motion. It
selects by `data-testid` only (never generated class names) and writes colours as
`light-dark(light, dark)` pairs from `PALETTE`; Streamlit sets `color-scheme` on the app, so
they follow its own switch. `tests/test_theme.py` enforces all of this.

## Escaping

Resume, LLM and user text is shown literally: `formatter.md_escape` for every Markdown sink
(it keeps inline and fenced code readable), `html.escape` for every value in an HTML
builder. Tests feed `*p`, `__init__`, `![x](http://example.com/a.png)` and
`<script>alert(1)</script>` through them.

## Do and don't

| Do | Don't |
|---|---|
| State the takeaway in a chart title | Use a title that only names the axes |
| Pair every status colour with an icon and words | Mark right or wrong with colour alone |
| Use topic colours for topics | Colour weeks, systems or statuses with topic colours |
| Use sentence case and plain verbs ("Open Weekly plan") | Use hype ("Supercharge"), exclamation marks or Title Case |
| Keep cards one level deep | Put a card inside a card inside a card |
| Use Material Symbols | Use emoji as icons |

## Screenshot workflow

`python -m scripts.screenshots docs/design/after` captures every page with no student and
with the demo student, plus the key flows, at 1440, 1366 and 390 px in light and dark. Each
state must show its marker text before it is saved, so a wrong state fails the run; browser
console errors fail it too. Open the PNGs, critique them against the brief's rubric, fix,
and capture again. The full folders are git-ignored; a curated set is committed once.

## Known limitations

- Streamlit's data grid puts four keyboard stops (its toolbar) on every table, which stay
  invisible until hovered. This is left as Streamlit ships it.
- Until Phase 3 rebuilds them with `piq/charts.py`, the older pages' built-in charts take the
  topic palette for series that are not topics (weeks, systems).
- The trail's approved step uses the same neutral check as a draft: Streamlit sets step icons
  from the state (complete or error) and allows no custom icon.
