"use client";

import { motion } from "framer-motion";
import type { Circuit } from "@/lib/circuits";

export default function CircuitOutline({
  circuit,
  active,
  onClick,
}: {
  circuit: Circuit;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="group flex flex-col items-center gap-3 p-4 transition-opacity"
      aria-pressed={active}
    >
      <svg
        viewBox={circuit.viewBox}
        className="w-32 h-24 md:w-40 md:h-28"
        fill="none"
      >
        <motion.path
          d={circuit.path}
          stroke={active ? "var(--cyan)" : "var(--off-white-dim)"}
          strokeWidth={active ? 3 : 2}
          initial={{ pathLength: 0, opacity: 0 }}
          whileInView={{ pathLength: 1, opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 1.4, ease: [0.16, 1, 0.3, 1] }}
        />
      </svg>
      <span
        className={`font-mono text-[11px] tracking-[0.15em] transition-colors ${
          active
            ? "text-[var(--cyan)]"
            : "text-[var(--off-white-dim)] group-hover:text-[var(--off-white)]"
        }`}
      >
        {circuit.name.toUpperCase()}
      </span>
    </button>
  );
}
