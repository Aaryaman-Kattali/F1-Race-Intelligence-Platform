"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { DRIVERS, type DriverMeta } from "@/lib/drivers";
import NumberTicker from "./NumberTicker";

type CircuitRow = {
  circuit_name: string;
  races_at_circuit: number;
  avg_finish: number;
  wins: number;
  podiums: number;
};

type DriverData = {
  driver_code: string;
  circuits: CircuitRow[];
  totals: { total_races: number; total_wins: number; total_podiums: number };
  live: boolean;
};

export default function DriverPerformance() {
  const [selected, setSelected] = useState(DRIVERS[0]); // HAM — real, verified default
  const [data, setData] = useState<DriverData | null>(null);
  const [loading, setLoading] = useState(true);
  const requestId = useRef(0);

  // Async, so its first setState lands after the await rather than
  // synchronously inside the effect body (which would cascade renders).
  const fetchDriver = useCallback(async (code: string) => {
    const thisRequest = ++requestId.current;
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_URL;
      const res = await fetch(`${baseUrl}/api/driver-performance?driver=${code}`);
      const json = await res.json();
      // Stale responses from rapid switching are dropped, so the name on
      // screen and the stats under it can never disagree.
      if (requestId.current === thisRequest) {
        setData(json);
        setLoading(false);
      }
    } catch {
      if (requestId.current === thisRequest) {
        setData({
          driver_code: code,
          circuits: [],
          totals: { total_races: 0, total_wins: 0, total_podiums: 0 },
          live: false,
        });
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchDriver(DRIVERS[0].code);
  }, [fetchDriver]);

  function selectDriver(driver: DriverMeta) {
    setSelected(driver);
    setLoading(true);
    // Drop the outgoing driver's numbers immediately. Without this the
    // tickers would animate to the previous driver's totals underneath the
    // newly selected driver's name until the fetch resolves.
    setData(null);
    fetchDriver(driver.code);
  }

  const maxAvgFinish = data?.circuits.length
    ? Math.max(...data.circuits.map((c) => c.avg_finish))
    : 1;

  return (
    <section className="min-h-screen bg-[var(--carbon)] px-6 py-20 md:px-16">
      <p className="font-mono text-[11px] tracking-[0.25em] text-[var(--cyan)] mb-2">
        SECTION 03
      </p>
      <h2 className="font-display text-4xl md:text-5xl text-[var(--off-white)] mb-10">
        DRIVER TIMING TOWER
      </h2>

      {/* driver pill selector */}
      <div className="flex flex-wrap gap-2 mb-14">
        {DRIVERS.map((d) => (
          <button
            key={d.code}
            onClick={() => selectDriver(d)}
            aria-pressed={selected.code === d.code}
            className={`font-mono text-[11px] tracking-[0.1em] px-3 py-1.5 border transition-colors ${
              selected.code === d.code
                ? "border-[var(--cyan)] text-[var(--cyan)]"
                : "border-[var(--panel-line)] text-[var(--off-white-dim)] hover:border-[var(--off-white-dim)]"
            }`}
          >
            {d.code}
          </button>
        ))}
      </div>

      <AnimatePresence mode="wait">
        <motion.div
          key={selected.code}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.3 }}
        >
          {/* headline totals */}
          <div className="flex flex-wrap gap-10 mb-12 border-b border-[var(--panel-line)] pb-8">
            <div>
              <p className="font-mono text-[10px] tracking-[0.2em] text-[var(--off-white-dim)] mb-1">
                {selected.name.toUpperCase()} — TOTAL WINS
              </p>
              <NumberTicker
                value={data?.totals.total_wins ?? 0}
                className="font-display text-5xl text-[var(--cyan)]"
              />
            </div>
            <div>
              <p className="font-mono text-[10px] tracking-[0.2em] text-[var(--off-white-dim)] mb-1">
                TOTAL PODIUMS
              </p>
              <NumberTicker
                value={data?.totals.total_podiums ?? 0}
                className="font-display text-5xl text-[var(--off-white)]"
              />
            </div>
            <div>
              <p className="font-mono text-[10px] tracking-[0.2em] text-[var(--off-white-dim)] mb-1">
                RACES (4 CIRCUITS)
              </p>
              <NumberTicker
                value={data?.totals.total_races ?? 0}
                className="font-display text-5xl text-[var(--off-white-dim)]"
              />
            </div>
          </div>

          {/* per-circuit timing-tower bars */}
          {loading && (
            <p className="font-mono text-[12px] text-[var(--off-white-dim)]">
              QUERYING WAREHOUSE...
            </p>
          )}
          {!loading && data?.circuits.length === 0 && (
            <p className="font-mono text-[12px] text-[var(--off-white-dim)]">
              No ingested data for this driver yet.
            </p>
          )}
          {!loading &&
            data?.circuits.map((c) => {
              // Inverse-scaled: lower avg_finish (better) = longer bar.
              const widthPct = Math.max(
                15,
                100 - ((c.avg_finish - 1) / maxAvgFinish) * 80
              );
              return (
                <div key={c.circuit_name} className="mb-4">
                  <div className="flex items-baseline justify-between mb-1">
                    <span className="font-mono text-[11px] text-[var(--off-white)]">
                      {c.circuit_name.toUpperCase()}
                    </span>
                    <span className="font-mono text-[11px] text-[var(--off-white-dim)]">
                      {c.races_at_circuit} races · {c.wins}W · {c.podiums}P ·{" "}
                      <span className="text-[var(--cyan)]">
                        {c.avg_finish.toFixed(2)}
                      </span>
                    </span>
                  </div>
                  <div className="h-1.5 bg-[var(--panel)]">
                    <motion.div
                      className="h-full bg-[var(--cyan)]"
                      initial={{ width: 0 }}
                      animate={{ width: `${widthPct}%` }}
                      transition={{ duration: 0.9, ease: [0.16, 1, 0.3, 1] }}
                    />
                  </div>
                </div>
              );
            })}
        </motion.div>
      </AnimatePresence>
    </section>
  );
}
