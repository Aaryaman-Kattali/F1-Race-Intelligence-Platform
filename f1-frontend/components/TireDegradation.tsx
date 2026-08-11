"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { CIRCUITS, type Circuit } from "@/lib/circuits";

type CompoundRow = {
  compound: string;
  avg_degradation_per_lap: number;
  driver_count: number;
  avg_stint_length: number;
};

type DegradationData = {
  circuit_name: string;
  compounds: CompoundRow[];
  caveat: string;
  live: boolean;
};

type StintLap = { lap_number: number; tyre_life: number; lap_time_seconds: number };
type StintData = {
  driver_code: string;
  compound: string;
  laps: StintLap[];
  live: boolean;
};

const COMPOUND_ORDER = ["SOFT", "MEDIUM", "HARD"];

function interpolateColor(t: number): string {
  // t=0 fresh (cyan-tinted), t=1 worn (amber) — clamped
  const clamped = Math.max(0, Math.min(1, t));
  const from = [0, 229, 255]; // --cyan
  const to = [255, 176, 32]; // --amber
  const rgb = from.map((c, i) => Math.round(c + (to[i] - c) * clamped));
  return `rgb(${rgb[0]}, ${rgb[1]}, ${rgb[2]})`;
}

export default function TireDegradation() {
  const [circuit, setCircuit] = useState(CIRCUITS[0]);
  const [degradation, setDegradation] = useState<DegradationData | null>(null);
  const [stint, setStint] = useState<StintData | null>(null);
  const [lapIndex, setLapIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const requestId = useRef(0);

  // Async, so its first setState lands after the await rather than
  // synchronously inside the effect body (which would cascade renders).
  const loadCircuit = useCallback(async (c: Circuit) => {
    const thisRequest = ++requestId.current;
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_URL;
      const degRes = await fetch(
        `${baseUrl}/api/tire-degradation?circuit=${encodeURIComponent(c.name)}`
      );
      const degJson = await degRes.json();
      if (requestId.current !== thisRequest) return;
      setDegradation(degJson);

      // Default the scrubber to MEDIUM if present, else the first available
      // compound the frontend actually renders.
      const available: CompoundRow[] = degJson.compounds ?? [];
      const defaultCompound =
        available.find((x) => x.compound === "MEDIUM")?.compound ??
        available.find((x) => COMPOUND_ORDER.includes(x.compound))?.compound;

      if (defaultCompound) {
        const stintRes = await fetch(
          `${baseUrl}/api/stint-sample?circuit=${encodeURIComponent(
            c.name
          )}&compound=${defaultCompound}`
        );
        const stintJson = await stintRes.json();
        if (requestId.current === thisRequest) setStint(stintJson);
      }
      if (requestId.current === thisRequest) setLoading(false);
    } catch {
      if (requestId.current === thisRequest) setLoading(false);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadCircuit(CIRCUITS[0]);
  }, [loadCircuit]);

  function selectCircuit(c: Circuit) {
    setCircuit(c);
    setLoading(true);
    // Drop the outgoing circuit's data so nothing stale renders under the
    // newly selected circuit's name while the fetch is in flight.
    setDegradation(null);
    setStint(null);
    setLapIndex(0);
    loadCircuit(c);
  }

  const maxAbsDeg = degradation?.compounds.length
    ? Math.max(
        ...degradation.compounds.map((c) => Math.abs(c.avg_degradation_per_lap))
      )
    : 1;

  // The slider is clamped to the stint length, but lapIndex is reset
  // asynchronously, so guard the lookup against a stale index.
  const currentLap = stint?.laps[Math.min(lapIndex, (stint?.laps.length ?? 1) - 1)];
  const maxTyreLife = stint?.laps.length
    ? Math.max(...stint.laps.map((l) => l.tyre_life))
    : 1;

  return (
    <section className="min-h-screen bg-[var(--carbon)] px-6 py-20 md:px-16">
      <p className="font-mono text-[11px] tracking-[0.25em] text-[var(--cyan)] mb-2">
        SECTION 04
      </p>
      <h2 className="font-display text-4xl md:text-5xl text-[var(--off-white)] mb-10">
        TIRE DEGRADATION
      </h2>

      <div className="flex flex-wrap gap-2 mb-12">
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
        <p className="font-mono text-[12px] text-[var(--off-white-dim)] mb-8">
          QUERYING WAREHOUSE...
        </p>
      )}

      {/* diverging compound bars, zero-centered */}
      {!loading && degradation && (
        <div className="mb-6 max-w-xl">
          {COMPOUND_ORDER.filter((name) =>
            degradation.compounds.some((c) => c.compound === name)
          ).map((name) => {
            const row = degradation.compounds.find((c) => c.compound === name)!;
            const isWear = row.avg_degradation_per_lap > 0;
            const widthPct =
              (Math.abs(row.avg_degradation_per_lap) / maxAbsDeg) * 45;
            return (
              <div key={name} className="flex items-center gap-3 mb-3">
                <span className="font-mono text-[11px] text-[var(--off-white)] w-16">
                  {name}
                </span>
                <div className="relative flex-1 h-2 bg-[var(--panel)]">
                  <div className="absolute left-1/2 top-0 bottom-0 w-px bg-[var(--panel-line)]" />
                  <motion.div
                    className="absolute top-0 bottom-0"
                    style={{
                      [isWear ? "left" : "right"]: "50%",
                      backgroundColor: isWear ? "var(--amber)" : "var(--cyan)",
                    }}
                    initial={{ width: 0 }}
                    animate={{ width: `${widthPct}%` }}
                    transition={{ duration: 0.9, ease: [0.16, 1, 0.3, 1] }}
                  />
                </div>
                <span className="font-mono text-[11px] text-[var(--off-white-dim)] w-16 text-right">
                  {row.avg_degradation_per_lap > 0 ? "+" : ""}
                  {row.avg_degradation_per_lap.toFixed(3)}
                </span>
              </div>
            );
          })}

          {/* the honest caveat, as a real UI element, not a footnote */}
          <p className="font-mono text-[10px] leading-relaxed text-[var(--off-white-dim)] mt-6 border-l-2 border-[var(--panel-line)] pl-3">
            {degradation.caveat}
          </p>
        </div>
      )}

      {/* real-stint lap scrubber */}
      {!loading && stint && stint.laps.length > 0 && currentLap && (
        <div className="max-w-xl mt-16">
          <p className="font-mono text-[10px] tracking-[0.2em] text-[var(--off-white-dim)] mb-4">
            REAL STINT — {stint.driver_code} · {stint.compound}
          </p>
          <div className="flex items-center gap-6 mb-4">
            <div
              className="h-10 w-10 rounded-full border-2 transition-colors"
              style={{
                borderColor: interpolateColor(currentLap.tyre_life / maxTyreLife),
              }}
            />
            <div>
              <p className="font-mono text-2xl text-[var(--off-white)]">
                {currentLap.lap_time_seconds.toFixed(2)}s
              </p>
              <p className="font-mono text-[10px] text-[var(--off-white-dim)]">
                LAP {currentLap.lap_number} · TYRE LIFE {currentLap.tyre_life}
              </p>
            </div>
          </div>
          <input
            type="range"
            min={0}
            max={stint.laps.length - 1}
            value={Math.min(lapIndex, stint.laps.length - 1)}
            onChange={(e) => setLapIndex(Number(e.target.value))}
            className="w-full accent-[var(--cyan)]"
          />
        </div>
      )}
    </section>
  );
}
