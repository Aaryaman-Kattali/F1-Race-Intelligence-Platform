"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { CIRCUITS, type Circuit } from "@/lib/circuits";

type LapDriver = {
  driver_code: string;
  position: number;
  lap_time_seconds: number;
};
type Lap = { lap_number: number; drivers: LapDriver[] };
type ReplayData = {
  circuit_name: string;
  season_year: number | null;
  total_laps: number;
  laps: Lap[];
  live: boolean;
};

export default function LiveReplay() {
  const [circuit, setCircuit] = useState(CIRCUITS[0]);
  const [data, setData] = useState<ReplayData | null>(null);
  const [lapIdx, setLapIdx] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1); // laps per second
  const [loading, setLoading] = useState(true);
  const requestId = useRef(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Points sampled evenly along the track outline. Measured in the <path>'s
  // ref callback (which runs after commit) rather than read from a ref during
  // render — reading refs mid-render is both a lint error and genuinely
  // unsafe, and it would have painted the first frame with every dot at 0,0.
  const [pathPoints, setPathPoints] = useState<{ x: number; y: number }[] | null>(
    null
  );

  const measurePath = useCallback((el: SVGPathElement | null) => {
    if (!el) return;
    const total = el.getTotalLength();
    const SAMPLES = 200;
    const pts = Array.from({ length: SAMPLES + 1 }, (_, i) => {
      const p = el.getPointAtLength((i / SAMPLES) * total);
      return { x: p.x, y: p.y };
    });
    setPathPoints(pts);
  }, []);

  // Async, so its first setState lands after the await rather than
  // synchronously inside the effect body (which would cascade renders).
  const loadCircuit = useCallback(async (c: Circuit) => {
    const thisRequest = ++requestId.current;
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_URL;
      const res = await fetch(
        `${baseUrl}/api/race-replay?circuit=${encodeURIComponent(c.name)}`
      );
      const json = await res.json();
      if (requestId.current === thisRequest) {
        setData(json);
        setLoading(false);
      }
    } catch {
      if (requestId.current === thisRequest) {
        setData({
          circuit_name: c.name,
          season_year: null,
          total_laps: 0,
          laps: [],
          live: false,
        });
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadCircuit(CIRCUITS[0]);
  }, [loadCircuit]);

  function selectCircuit(c: Circuit) {
    setCircuit(c);
    setPlaying(false);
    setLoading(true);
    // Drop the outgoing race so no stale lap renders under the new circuit.
    setData(null);
    setLapIdx(0);
    loadCircuit(c);
  }

  useEffect(() => {
    if (playing && data?.laps.length) {
      intervalRef.current = setInterval(() => {
        setLapIdx((i) => {
          if (i >= data.laps.length - 1) {
            setPlaying(false);
            return i;
          }
          return i + 1;
        });
      }, 1000 / speed);
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [playing, speed, data]);

  function getDotPosition(
    position: number,
    totalDrivers: number,
    points: { x: number; y: number }[]
  ): { x: number; y: number } {
    const fraction = (position - 1) / Math.max(totalDrivers - 1, 1);
    const idx = Math.round(fraction * (points.length - 1));
    return points[Math.max(0, Math.min(idx, points.length - 1))];
  }

  const currentLap = data?.laps[Math.min(lapIdx, (data?.laps.length ?? 1) - 1)];

  return (
    <section className="min-h-screen bg-[var(--carbon)] px-6 py-20 md:px-16">
      <p className="font-mono text-[11px] tracking-[0.25em] text-[var(--cyan)] mb-2">
        SECTION 05
      </p>
      <h2 className="font-display text-4xl md:text-5xl text-[var(--off-white)] mb-2">
        LIVE REPLAY
      </h2>
      <p className="font-mono text-[10px] leading-relaxed text-[var(--off-white-dim)] mb-10 max-w-xl">
        {data?.season_year
          ? `${data.circuit_name.toUpperCase()} · ${data.season_year} SEASON`
          : ""}
        {" — "}real recorded race, replayed lap by lap. Dot positions map
        running order onto the circuit outline; not literal GPS traces.
      </p>

      <div className="flex flex-wrap gap-2 mb-8">
        {CIRCUITS.map((c) => (
          <button
            key={c.slug}
            onClick={() => selectCircuit(c)}
            aria-pressed={circuit.slug === c.slug}
            className={`font-mono text-[11px] px-3 py-1.5 border transition-colors ${
              circuit.slug === c.slug
                ? "border-[var(--cyan)] text-[var(--cyan)]"
                : "border-[var(--panel-line)] text-[var(--off-white-dim)]"
            }`}
          >
            {c.name.toUpperCase()}
          </button>
        ))}
      </div>

      {loading && (
        <p className="font-mono text-[12px] text-[var(--off-white-dim)]">
          QUERYING WAREHOUSE...
        </p>
      )}

      {!loading && data && data.laps.length === 0 && (
        <p className="font-mono text-[12px] text-[var(--off-white-dim)]">
          No replayable race for this circuit yet.
        </p>
      )}

      {!loading && data && data.laps.length > 0 && currentLap && (
        <>
          <svg viewBox={circuit.viewBox} className="w-full max-w-2xl h-64">
            <path
              // keyed so switching circuits remounts the path and re-fires
              // the ref callback against the new outline
              key={circuit.slug}
              ref={measurePath}
              d={circuit.path}
              stroke="var(--panel-line)"
              strokeWidth={2}
              fill="none"
            />
            {pathPoints &&
              currentLap.drivers.map((d) => {
                const { x, y } = getDotPosition(
                  d.position,
                  currentLap.drivers.length,
                  pathPoints
                );
                const leader = d.position <= 3;
                return (
                  <circle
                    key={d.driver_code}
                    cx={x}
                    cy={y}
                    r={leader ? 5 : 3}
                    fill={leader ? "var(--cyan)" : "var(--off-white-dim)"}
                  />
                );
              })}
          </svg>

          <p className="font-mono text-[10px] leading-relaxed text-[var(--off-white-dim)] mt-3 mb-2 max-w-xl border-l-2 border-[var(--panel-line)] pl-3">
            Shows on-track running order at each lap, not final official
            classification — podium order can differ due to post-race penalties
            (e.g. 2024 Belgian GP).
          </p>

          <div className="flex items-center gap-4 mt-6 mb-6 max-w-2xl">
            <button
              onClick={() => setPlaying((p) => !p)}
              className="font-mono text-[11px] px-4 py-2 border border-[var(--cyan)] text-[var(--cyan)]"
            >
              {playing ? "PAUSE" : "PLAY"}
            </button>
            <input
              type="range"
              min={0}
              max={data.laps.length - 1}
              value={Math.min(lapIdx, data.laps.length - 1)}
              onChange={(e) => {
                setPlaying(false);
                setLapIdx(Number(e.target.value));
              }}
              className="flex-1 accent-[var(--cyan)]"
            />
            {/* Car count is shown because coverage is genuinely uneven: some
                laps have times recorded for only a handful of cars, and
                without this the field looks like it vanished mid-race. */}
            <span className="font-mono text-[11px] text-[var(--off-white-dim)] w-32">
              LAP {currentLap.lap_number}/{data.total_laps}
              <br />
              <span className="text-[10px]">
                {currentLap.drivers.length} cars recorded
              </span>
            </span>
            <select
              value={speed}
              onChange={(e) => setSpeed(Number(e.target.value))}
              className="font-mono text-[11px] bg-transparent border border-[var(--panel-line)] text-[var(--off-white-dim)]"
            >
              <option value={0.5}>0.5x</option>
              <option value={1}>1x</option>
              <option value={2}>2x</option>
              <option value={4}>4x</option>
            </select>
          </div>

          {/* leader board for the current lap */}
          <div className="font-mono text-[11px] text-[var(--off-white-dim)] grid grid-cols-2 gap-x-8 gap-y-1 max-w-md">
            {[...currentLap.drivers]
              .sort((a, b) => a.position - b.position)
              .slice(0, 10)
              .map((d) => (
                <div key={d.driver_code} className="flex justify-between">
                  <span className={d.position <= 3 ? "text-[var(--cyan)]" : ""}>
                    P{d.position} {d.driver_code}
                  </span>
                  <span>{d.lap_time_seconds.toFixed(1)}s</span>
                </div>
              ))}
          </div>
        </>
      )}
    </section>
  );
}
