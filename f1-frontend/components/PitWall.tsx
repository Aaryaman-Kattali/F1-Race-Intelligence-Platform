"use client";

import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

// Shape confirmed against the live endpoint, not assumed: /api/ask wraps its
// payload in {success, data:{...}} and names the byte count
// `estimated_bytes_scanned`.
type AskPayload = {
  question: string;
  generated_sql: string;
  natural_language_answer: string;
  estimated_bytes_scanned: number;
  execution_time_ms: number;
  model: string;
  backend: string;
  // Present instead of an answer when a guardrail rejects the generated SQL
  // (non-SELECT, or over the dry-run cost cap). Still arrives as success:true.
  error?: string;
};

type Message = {
  role: "operator" | "engineer";
  text: string;
  fullText?: string;
  truncated?: boolean;
  sql?: string;
  estimatedBytes?: number;
  elapsedMs?: number;
  rejected?: boolean;
  timestamp: string;
};

const STARTER_QUESTIONS = [
  "How has Lewis Hamilton performed at the British Grand Prix?",
  "Which driver has the best average finish at the Hungarian Grand Prix?",
  "What's the tire degradation like on soft compounds at Monza?",
];

function nowStamp() {
  return new Date().toLocaleTimeString("en-GB", { hour12: false });
}

// The agent sometimes emits its internal deliberation before its actual
// answer, which can run to thousands of characters. Show the conclusion (the
// tail) inline and keep the verbatim response one click away — nothing is
// hidden, but the transcript stays readable.
const MAX_INLINE_CHARS = 800;

function condense(text: string): { shown: string; truncated: boolean } {
  if (text.length <= MAX_INLINE_CHARS) return { shown: text, truncated: false };
  // Take whole trailing sentences rather than a raw character slice, so the
  // conclusion doesn't open mid-clause.
  const sentences = text.trim().split(/(?<=[.!?])\s+/);
  const shown = sentences.slice(-3).join(" ").trim();
  return { shown: shown || text.slice(-400).trim(), truncated: true };
}

export default function PitWall() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [showSql, setShowSql] = useState<Record<number, boolean>>({});
  const [showRaw, setShowRaw] = useState<Record<number, boolean>>({});
  const requestId = useRef(0);
  const transcriptRef = useRef<HTMLDivElement>(null);

  // Follow the newest message — without this a reply lands below the
  // transcript's fold and looks like nothing happened.
  useEffect(() => {
    const el = transcriptRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, loading]);

  async function send(question: string) {
    if (!question.trim() || loading) return;
    const thisRequest = ++requestId.current;
    setMessages((m) => [
      ...m,
      { role: "operator", text: question, timestamp: nowStamp() },
    ]);
    setInput("");
    setLoading(true);
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_URL;
      const res = await fetch(`${baseUrl}/api/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      const json = await res.json();
      if (requestId.current !== thisRequest) return;

      // Non-2xx (FastAPI raises 500/501 with a `detail` string).
      if (!res.ok || !json?.success) {
        setMessages((m) => [
          ...m,
          {
            role: "engineer",
            text: json?.detail ?? "The agent could not answer that.",
            rejected: true,
            timestamp: nowStamp(),
          },
        ]);
        return;
      }

      const payload: AskPayload = json.data;
      // Two rejection shapes, both arriving as success:true. Either no query
      // was ever built (empty generated_sql), or a guardrail rejected the SQL
      // after generation and returned `error` in place of an answer.
      const rejected = !payload.generated_sql?.trim() || !!payload.error;
      const { shown, truncated } = condense(
        payload.error ?? payload.natural_language_answer ?? "No response."
      );

      setMessages((m) => [
        ...m,
        {
          role: "engineer",
          text: shown,
          fullText: payload.natural_language_answer,
          truncated,
          sql: payload.generated_sql || undefined,
          estimatedBytes: payload.estimated_bytes_scanned,
          elapsedMs: payload.execution_time_ms,
          rejected,
          timestamp: nowStamp(),
        },
      ]);
    } catch {
      if (requestId.current === thisRequest) {
        setMessages((m) => [
          ...m,
          {
            role: "engineer",
            text: "Link lost — pit wall unreachable.",
            rejected: true,
            timestamp: nowStamp(),
          },
        ]);
      }
    } finally {
      if (requestId.current === thisRequest) setLoading(false);
    }
  }

  return (
    <section className="min-h-screen bg-[var(--carbon)] px-6 py-20 md:px-16">
      <p className="font-mono text-[11px] tracking-[0.25em] text-[var(--cyan)] mb-2">
        SECTION 06
      </p>
      <h2 className="font-display text-4xl md:text-5xl text-[var(--off-white)] mb-2">
        PIT WALL
      </h2>
      <p className="font-mono text-[10px] leading-relaxed text-[var(--off-white-dim)] mb-10 max-w-xl">
        Ask the warehouse directly. Read-only channel — no transmission can
        modify race data, by design. Answers are generated by an LLM writing
        SQL against the warehouse; the query it ran is shown with every reply.
      </p>

      {messages.length === 0 && (
        <div className="flex flex-wrap gap-2 mb-8">
          {STARTER_QUESTIONS.map((q) => (
            <button
              key={q}
              onClick={() => send(q)}
              className="font-mono text-[11px] px-3 py-1.5 border border-[var(--panel-line)] text-[var(--off-white-dim)] hover:border-[var(--cyan)] hover:text-[var(--cyan)] transition-colors"
            >
              {q}
            </button>
          ))}
        </div>
      )}

      <div
        ref={transcriptRef}
        className="max-w-2xl border border-[var(--panel-line)] bg-[var(--panel)] p-4 mb-4 min-h-[300px] max-h-[500px] overflow-y-auto"
      >
        <AnimatePresence initial={false}>
          {messages.map((m, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              className="mb-4 font-mono text-[12px]"
            >
              <div className="flex items-baseline gap-2 mb-1">
                <span
                  className={
                    m.role === "operator"
                      ? "text-[var(--off-white)]"
                      : m.rejected
                        ? "text-[var(--amber)]"
                        : "text-[var(--cyan)]"
                  }
                >
                  {m.role === "operator"
                    ? "PIT WALL"
                    : m.rejected
                      ? "ENGINEER — REJECTED"
                      : "ENGINEER"}
                </span>
                <span className="text-[var(--off-white-dim)] text-[10px]">
                  {m.timestamp}
                </span>
              </div>
              <p className="text-[var(--off-white)] leading-relaxed whitespace-pre-wrap">
                {m.text}
              </p>

              {m.truncated && m.fullText && (
                <div className="mt-2">
                  <p className="text-[10px] text-[var(--amber)]">
                    Agent returned {m.fullText.length.toLocaleString()} characters
                    including repeated internal reasoning — showing its
                    conclusion.
                  </p>
                  <button
                    onClick={() => setShowRaw((s) => ({ ...s, [i]: !s[i] }))}
                    className="text-[10px] text-[var(--off-white-dim)] underline"
                  >
                    {showRaw[i] ? "HIDE" : "SHOW"} FULL AGENT RESPONSE
                  </button>
                  {showRaw[i] && (
                    <pre className="mt-1 text-[10px] text-[var(--off-white-dim)] bg-[var(--carbon)] p-2 max-h-48 overflow-auto whitespace-pre-wrap">
                      {m.fullText}
                    </pre>
                  )}
                </div>
              )}

              {m.sql && (
                <div className="mt-2">
                  <button
                    onClick={() => setShowSql((s) => ({ ...s, [i]: !s[i] }))}
                    className="text-[10px] text-[var(--off-white-dim)] underline"
                  >
                    {showSql[i] ? "HIDE" : "SHOW"} TELEMETRY QUERY
                  </button>
                  {showSql[i] && (
                    <pre className="mt-1 text-[10px] text-[var(--off-white-dim)] bg-[var(--carbon)] p-2 overflow-x-auto">
                      {m.sql}
                    </pre>
                  )}
                  {m.estimatedBytes != null && (
                    <p className="text-[10px] text-[var(--off-white-dim)] mt-1">
                      {(m.estimatedBytes / 1024).toFixed(1)} KB scanned
                      {m.elapsedMs != null &&
                        ` · ${(m.elapsedMs / 1000).toFixed(1)}s`}
                    </p>
                  )}
                </div>
              )}
            </motion.div>
          ))}
        </AnimatePresence>
        {loading && (
          <p className="font-mono text-[11px] text-[var(--off-white-dim)] animate-pulse">
            PIT WALL LINK ESTABLISHED...
          </p>
        )}
      </div>

      <div className="flex gap-2 max-w-2xl">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send(input)}
          placeholder="Ask about any driver, circuit, or tire strategy..."
          className="flex-1 font-mono text-[12px] bg-[var(--panel)] border border-[var(--panel-line)] px-3 py-2 text-[var(--off-white)] focus:border-[var(--cyan)] outline-none"
        />
        <button
          onClick={() => send(input)}
          disabled={loading}
          className="font-mono text-[11px] px-4 py-2 border border-[var(--cyan)] text-[var(--cyan)] disabled:opacity-40"
        >
          SEND
        </button>
      </div>
    </section>
  );
}
