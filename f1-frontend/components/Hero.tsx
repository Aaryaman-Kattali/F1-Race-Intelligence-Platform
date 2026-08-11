"use client";

import { Suspense, useState } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import { motion, type Variants } from "framer-motion";
import WireframeCar from "./WireframeCar";
import type { PlatformStats } from "@/lib/api";

const readout: Variants = {
  hidden: { opacity: 0, y: 8 },
  show: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: {
      delay: 0.15 + i * 0.12,
      duration: 0.6,
      ease: [0.16, 1, 0.3, 1],
    },
  }),
};

function formatCount(n: number) {
  return n.toLocaleString("en-US");
}

export default function Hero({ stats }: { stats: PlatformStats }) {
  const [ready, setReady] = useState(false);
  const circuitCount = String(stats.circuits_ingested).padStart(2, "0");

  return (
    <section className="relative h-screen w-full overflow-hidden bg-[var(--carbon)]">
      {/* faint telemetry grid backdrop */}
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.07]"
        style={{
          backgroundImage:
            "linear-gradient(var(--cyan) 1px, transparent 1px), linear-gradient(90deg, var(--cyan) 1px, transparent 1px)",
          backgroundSize: "48px 48px",
        }}
      />

      <Canvas
        camera={{ position: [5, 2.2, 5], fov: 38 }}
        onCreated={() => setReady(true)}
        className="!absolute inset-0"
      >
        <Suspense fallback={null}>
          <ambientLight intensity={0.3} />
          <WireframeCar />
        </Suspense>
        <OrbitControls
          enablePan={false}
          enableZoom={false}
          autoRotate
          autoRotateSpeed={0.5}
          minPolarAngle={Math.PI / 2.6}
          maxPolarAngle={Math.PI / 1.9}
        />
      </Canvas>

      {/* top-left: identity */}
      <motion.div
        custom={0}
        initial="hidden"
        animate={ready ? "show" : "hidden"}
        variants={readout}
        className="absolute left-6 top-6 md:left-10 md:top-10"
      >
        <p className="font-mono text-[11px] tracking-[0.25em] text-[var(--cyan)]">
          F1 RACE INTELLIGENCE PLATFORM
        </p>
        <p className="font-mono text-[10px] tracking-[0.2em] text-[var(--off-white-dim)] mt-1">
          DATA ENGINEERING · AGENTIC AI
        </p>
      </motion.div>

      {/* top-right: pipeline status readout — real, live-fetched numbers */}
      <motion.div
        custom={1}
        initial="hidden"
        animate={ready ? "show" : "hidden"}
        variants={readout}
        className="absolute right-6 top-6 md:right-10 md:top-10 text-right"
      >
        <div className="flex items-center justify-end gap-1.5 mb-0.5">
          <span
            className={`h-1.5 w-1.5 rounded-full ${
              stats.live ? "bg-[var(--cyan)] animate-pulse" : "bg-[var(--off-white-dim)]"
            }`}
          />
          <p className="font-mono text-[10px] tracking-[0.2em] text-[var(--off-white-dim)]">
            {stats.live ? "LIVE FROM WAREHOUSE" : "CACHED"}
          </p>
        </div>
        <p className="font-mono text-[10px] tracking-[0.2em] text-[var(--off-white-dim)]">
          CIRCUITS INGESTED
        </p>
        <p className="font-mono text-lg text-[var(--cyan)]">{circuitCount}</p>
        <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--off-white-dim)] mt-2">
          {formatCount(stats.total_race_entries)} ENTRIES ·{" "}
          {formatCount(stats.total_laps_processed)} LAPS
        </p>
      </motion.div>

      {/* bottom-left: headline */}
      <motion.div
        custom={2}
        initial="hidden"
        animate={ready ? "show" : "hidden"}
        variants={readout}
        className="absolute left-6 bottom-8 md:left-10 md:bottom-12 max-w-md"
      >
        <h1 className="font-display text-5xl md:text-6xl leading-[0.95] text-[var(--off-white)]">
          BUILT FROM
          <br />
          <span className="text-[var(--cyan)]">RAW TELEMETRY.</span>
        </h1>
        <p className="mt-4 font-mono text-[12px] leading-relaxed text-[var(--off-white-dim)] max-w-[340px]">
          {formatCount(stats.total_laps_processed)} laps across {stats.season_range},
          pulled from FastF1, staged and deduplicated in BigQuery, modeled
          through dbt — this car is your pipeline, not a picture of one.
        </p>
      </motion.div>

      {/* bottom-right: scroll cue */}
      <motion.div
        custom={3}
        initial="hidden"
        animate={ready ? "show" : "hidden"}
        variants={readout}
        className="absolute right-6 bottom-8 md:right-10 md:bottom-12 flex flex-col items-end gap-2"
      >
        <span className="font-mono text-[10px] tracking-[0.2em] text-[var(--off-white-dim)]">
          SCROLL TO EXPLORE
        </span>
        <span className="h-8 w-px bg-gradient-to-b from-[var(--cyan)] to-transparent" />
      </motion.div>
    </section>
  );
}
