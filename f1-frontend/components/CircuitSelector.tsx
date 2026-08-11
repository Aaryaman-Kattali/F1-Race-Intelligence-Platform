"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import CircuitOutline from "./CircuitOutline";
import { CIRCUITS, type Circuit } from "@/lib/circuits";

type DriverRow = {
  driver_code: string;
  races_at_circuit: number;
  avg_finish: number;
  wins: number;
  podiums: number;
};

export default function CircuitSelector() {
  const [selected, setSelected] = useState(CIRCUITS[0]);
  const [drivers, setDrivers] = useState<DriverRow[] | null>(null);
  // Starts true: the mount effect below fetches immediately, so the panel
  // should read as loading from the very first paint rather than flashing
  // the "no data" empty state for a frame.
  const [loading, setLoading] = useState(true);

  // Clicking through circuits quickly can land responses out of order, which
  // would leave the panel showing another circuit's drivers. Only the newest
  // request is allowed to write state.
  const requestId = useRef(0);

  // Async, so its first setState lands after the await rather than
  // synchronously inside the effect body (which would cascade renders).
  const fetchDrivers = useCallback(async (circuit: Circuit) => {
    const id = ++requestId.current;
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_URL;
      const res = await fetch(
        `${baseUrl}/api/circuit-performance?circuit=${encodeURIComponent(circuit.name)}`
      );
      const data = await res.json();
      if (id === requestId.current) setDrivers(data.drivers ?? []);
    } catch {
      if (id === requestId.current) setDrivers([]);
    } finally {
      if (id === requestId.current) setLoading(false);
    }
  }, []);

  function selectCircuit(circuit: Circuit) {
    setSelected(circuit);
    setLoading(true);
    setDrivers(null);
    fetchDrivers(circuit);
  }

  // Load the first circuit on mount, matching the behavior of clicking it.
  // fetchDrivers only touches state after its await, so this does not actually
  // cascade renders — the rule is static and can't see across the async
  // boundary. The cascade-free alternative is fetching the first circuit on the
  // server in page.tsx and passing it in as a prop, which would remove this
  // effect entirely.
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchDrivers(CIRCUITS[0]);
  }, [fetchDrivers]);

  return (
    <section className="min-h-screen bg-[var(--carbon)] px-6 py-20 md:px-16">
      <p className="font-mono text-[11px] tracking-[0.25em] text-[var(--cyan)] mb-2">
        SECTION 02
      </p>
      <h2 className="font-display text-4xl md:text-5xl text-[var(--off-white)] mb-12">
        FOUR CIRCUITS.<br className="md:hidden" /> REAL HISTORY.
      </h2>

      <div className="flex flex-wrap gap-4 mb-16">
        {CIRCUITS.map((c) => (
          <CircuitOutline
            key={c.slug}
            circuit={c}
            active={selected.slug === c.slug}
            onClick={() => selectCircuit(c)}
          />
        ))}
      </div>

      <AnimatePresence mode="wait">
        <motion.div
          key={selected.slug}
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -12 }}
          transition={{ duration: 0.4 }}
          className="border-t border-[var(--panel-line)] pt-6 max-w-xl"
        >
          <p className="font-mono text-[10px] tracking-[0.2em] text-[var(--off-white-dim)] mb-4">
            TOP PERFORMERS — {selected.name.toUpperCase()}
          </p>
          {loading && (
            <p className="font-mono text-[12px] text-[var(--off-white-dim)]">
              QUERYING WAREHOUSE...
            </p>
          )}
          {!loading && drivers?.length === 0 && (
            <p className="font-mono text-[12px] text-[var(--off-white-dim)]">
              No ingested data for this circuit yet.
            </p>
          )}
          {!loading &&
            drivers?.map((d, i) => (
              <div
                key={d.driver_code}
                className="flex items-center justify-between py-2 border-b border-[var(--panel-line)]"
              >
                <span className="font-mono text-sm text-[var(--off-white)]">
                  {String(i + 1).padStart(2, "0")} — {d.driver_code}
                </span>
                <span className="font-mono text-xs text-[var(--off-white-dim)]">
                  {d.races_at_circuit} races · {d.wins}W · {d.podiums}P
                </span>
                <span className="font-mono text-sm text-[var(--cyan)]">
                  {d.avg_finish.toFixed(2)}
                </span>
              </div>
            ))}
        </motion.div>
      </AnimatePresence>
    </section>
  );
}
