# F1 Race Intelligence Platform — Frontend

A six-section single-page visualization of the [F1 Race Intelligence
Platform](https://github.com/Aaryaman-Kattali/F1-Race-Intelligence-Platform)
warehouse. Next.js 16 (App Router) + TypeScript + Tailwind v4, with
react-three-fiber for the hero and framer-motion throughout.

**Every number rendered here comes from a live query against the BigQuery
warehouse** via the backend's FastAPI endpoints. Nothing on screen is mock
data. Where a value is a fallback (backend unreachable) the UI says so
explicitly rather than silently showing stale figures.

---

## Sections

| # | Section | Data source |
|---|---------|-------------|
| 1 | **Hero** — particle assembly into a wireframe car, pipeline stat readout | `GET /api/stats` |
| 2 | **Circuit Selector** — line-draw track outlines, top performers per circuit | `GET /api/circuit-performance` |
| 3 | **Driver Timing Tower** — odometer totals, per-circuit bars | `GET /api/driver-performance` |
| 4 | **Tire Degradation** — diverging compound bars, real-stint lap scrubber | `GET /api/tire-degradation`, `GET /api/stint-sample` |
| 5 | **Live Replay** — lap-by-lap running order on the circuit outline | `GET /api/race-replay` |
| 6 | **Pit Wall** — natural-language query console | `POST /api/ask` |

---

## Running locally

Requires **Node.js 18.18+** (Next.js 16 requirement) and the backend API
running.

```bash
npm install
cp .env.local.example .env.local   # then edit if your API isn't on :8000
npm run dev
```

Open http://localhost:3000.

### Environment

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

That is the only variable. If it is unset or the backend is unreachable, the
hero falls back to the last confirmed-real figures and flips its status
indicator from **LIVE FROM WAREHOUSE** (cyan, pulsing) to **CACHED** (grey) —
the page never shows zeros or crashes.

### Backend CORS

The API allows `http://localhost:3000` by default. If you serve this frontend
from any other origin, add it to `FRONTEND_ORIGIN` in the backend's `.env`
(comma-separated) or the browser will silently drop the responses.

```bash
npm run build   # production build
npm run lint    # ESLint, including React 19 rules
```

---

## Honest notes (documented, not hidden)

The backend README documents the pipeline's limitations. These are the
frontend's, in the same spirit — each is also surfaced in the UI itself, not
just here.

- **Track outlines are stylized schematics, not survey-accurate GPS traces.**
  The four SVG paths in `lib/circuits.ts` evoke each circuit's character
  (Hungaroring tight and twisty, Monza's long straights and chicanes, Spa
  asymmetric and undulating, Silverstone multi-apex) but are hand-drawn
  abstractions. Replace them with official outlines if you have them.

- **The hero car is a primitive-geometry construct, not a licensed model.**
  Built entirely from Three.js primitives — no imported mesh, no team livery.

- **Section 5 "Live Replay" is a replay, not live.** It plays back a complete,
  recorded historical race lap by lap from the warehouse. FastF1 does not
  provide true live in-race data. Dot positions map each driver's *running
  order* onto the track outline — they are not literal track positions.

- **Replay shows on-track order, not final classification.** Post-race
  penalties can change the podium (the 2024 Belgian GP is the obvious case:
  Russell leads at the flag in the lap data, was disqualified afterwards).

- **Lap coverage in the replay is uneven.** Some laps have times recorded for
  only a handful of cars, so the field visibly thins on those laps. The lap
  counter shows how many cars are recorded on the current lap rather than
  interpolating positions the warehouse never captured.

- **Tire degradation does not correct for fuel load.** It is a linear
  regression of lap time against tyre life within a stint, so durable
  compounds can show *negative* apparent degradation as fuel burns off. This
  caveat is rendered in Section 4 itself, not buried here. Stints under 8 laps
  are excluded — thin samples produce meaningless slopes.

- **Section 6 answers are LLM-generated SQL.** The generated query is shown
  with every reply so any answer can be checked against its source. The
  channel is read-only by construction (read-only service account, SELECT-only
  validation, dry-run cost check), and refusals render distinctly from
  answers. The agent can still be wrong about *interpretation* — read the SQL.

- **The backend's PySpark job is demonstrative at this data scale.** Noted
  here only because the pipeline it belongs to feeds these visuals; see the
  backend README for detail.

---

## Notes on the stack

- Fonts load via CSS `@import` rather than `next/font/google`, which fetches
  at build time and fails in restricted-network environments.
- The page is statically prerendered with a 5-minute revalidate matching the
  backend's own cache TTL.
