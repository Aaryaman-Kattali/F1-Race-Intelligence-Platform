import Hero from "@/components/Hero";
import CircuitSelector from "@/components/CircuitSelector";
import DriverPerformance from "@/components/DriverPerformance";
import TireDegradation from "@/components/TireDegradation";
import LiveReplay from "@/components/LiveReplay";
import PitWall from "@/components/PitWall";
import { getPlatformStats } from "@/lib/api";

export default async function Home() {
  const stats = await getPlatformStats();

  return (
    <main>
      <Hero stats={stats} />
      <CircuitSelector />
      <DriverPerformance />
      <TireDegradation />
      <LiveReplay />
      <PitWall />
    </main>
  );
}
