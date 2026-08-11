export type PlatformStats = {
  circuits_ingested: number;
  circuit_names: string[];
  season_range: string;
  total_race_entries: number;
  total_laps_processed: number;
  agent_model: string;
  live: boolean;
};

// If the backend is unreachable (not running, cold start, network hiccup),
// the hero should still render something true, not break or show zeros.
// These match the last confirmed-real numbers from the actual pipeline.
const FALLBACK_STATS: PlatformStats = {
  circuits_ingested: 4,
  circuit_names: [
    "Hungarian Grand Prix",
    "Italian Grand Prix",
    "Belgian Grand Prix",
    "British Grand Prix",
  ],
  season_range: "2018-2024",
  total_race_entries: 540,
  total_laps_processed: 26367,
  agent_model: "gemini-3.1-flash-lite",
  live: false,
};

export async function getPlatformStats(): Promise<PlatformStats> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL;
  if (!baseUrl) return FALLBACK_STATS;

  try {
    const res = await fetch(`${baseUrl}/api/stats`, {
      // Revalidate every 5 minutes — matches the backend's own cache TTL,
      // no point fetching more often than the source data can change.
      next: { revalidate: 300 },
    });
    if (!res.ok) return FALLBACK_STATS;
    const data = await res.json();
    return { ...data, live: data.live ?? true };
  } catch {
    return FALLBACK_STATS;
  }
}
