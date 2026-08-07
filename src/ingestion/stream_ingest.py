"""
Simulated streaming ingestion: replay historical lap telemetry via Pub/Sub.

This is NOT true live in-race telemetry — FastF1 doesn't provide that.
Instead, we replay historical lap-by-lap data at configurable intervals to
exercise the full publish → consume → incremental-load pipeline.

Usage:
    python -m src.ingestion.stream_ingest --simulate \\
        --circuit "Hungarian Grand Prix" --year 2024 --interval 2.0
"""

import argparse
import json
import logging
import queue
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.warehouse.bigquery_loader import BigQueryLoader

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Publisher
# ---------------------------------------------------------------------------


class TelemetryPublisher:
    """
    Publishes lap-by-lap telemetry messages.

    In production mode, publishes to Google Pub/Sub.
    In local mode, pushes to an in-memory queue.
    """

    def __init__(self, topic: str = "f1-lap-telemetry",
                 project_id: Optional[str] = None,
                 local_queue: Optional[queue.Queue] = None):
        self.topic = topic
        self.project_id = project_id
        self._local_queue = local_queue
        self._pubsub_publisher = None

        if local_queue is None and project_id:
            try:
                from google.cloud import pubsub_v1
                self._pubsub_publisher = pubsub_v1.PublisherClient()
                self._topic_path = self._pubsub_publisher.topic_path(project_id, topic)
                logger.info(f"✅ Pub/Sub publisher ready: {self._topic_path}")
            except Exception as e:
                logger.warning(f"⚠️  Pub/Sub unavailable ({e}), using local queue")
                self._local_queue = queue.Queue()
        elif local_queue is None:
            self._local_queue = queue.Queue()
            logger.info("📋 Using local in-memory queue (no GCP project)")

    def publish(self, message: Dict) -> None:
        """Publish a single lap telemetry message."""
        message["published_at"] = datetime.utcnow().isoformat()

        if self._pubsub_publisher:
            data = json.dumps(message).encode("utf-8")
            future = self._pubsub_publisher.publish(self._topic_path, data)
            future.result(timeout=10)
        else:
            self._local_queue.put(message)

    def replay_telemetry(self, laps: List[Dict], interval: float = 1.0) -> int:
        """
        Replay a list of lap records at the given interval (seconds).

        Args:
            laps: List of lap dicts (from FastF1 processing)
            interval: Seconds between messages (simulates real-time pace)

        Returns:
            Number of messages published
        """
        logger.info(f"▶️  Replaying {len(laps)} laps at {interval}s intervals")
        for i, lap in enumerate(laps):
            self.publish(lap)
            if (i + 1) % 20 == 0:
                logger.info(f"  📡 Published {i + 1}/{len(laps)} laps")
            time.sleep(interval)
        logger.info(f"✅ Published all {len(laps)} laps")
        return len(laps)


# ---------------------------------------------------------------------------
# Consumer
# ---------------------------------------------------------------------------


class TelemetryConsumer:
    """
    Consumes lap telemetry messages and writes to BigQuery.

    In production mode, subscribes to Pub/Sub.
    In local mode, reads from an in-memory queue.
    """

    def __init__(self, loader: BigQueryLoader,
                 subscription: str = "f1-lap-telemetry-sub",
                 project_id: Optional[str] = None,
                 local_queue: Optional[queue.Queue] = None):
        self.loader = loader
        self.subscription = subscription
        self.project_id = project_id
        self._local_queue = local_queue
        self._running = False
        self._messages_consumed = 0
        self._buffer = []
        self._last_flush_time = time.time()
        self.exit_reason = "running"

    def _flush_buffer(self) -> None:
        if not self._buffer:
            self._last_flush_time = time.time()
            return
        try:
            self.loader.load_live_telemetry(self._buffer)
            self._messages_consumed += len(self._buffer)
        except Exception as e:
            logger.error(f"⚠️ Failed to flush batch of {len(self._buffer)} telemetry messages: {e}")
        finally:
            self._buffer = []
            self._last_flush_time = time.time()

    def _process_message(self, message: Dict) -> None:
        """Process a single telemetry message."""
        self._buffer.append(message)
        if len(self._buffer) >= 50 or (time.time() - self._last_flush_time) >= 2.0:
            self._flush_buffer()

    def consume_local(self, timeout: float = 30.0) -> int:
        """Consume from local queue until empty or timeout."""
        import traceback
        self._running = True
        self.exit_reason = "running"
        start = time.time()
        try:
            while self._running:
                if time.time() - start >= timeout:
                    self.exit_reason = "timed_out"
                    break

                if self._buffer and (time.time() - self._last_flush_time) >= 2.0:
                    self._flush_buffer()

                try:
                    message = self._local_queue.get(timeout=0.5)
                    self._process_message(message)
                    self._local_queue.task_done()
                except queue.Empty:
                    if not self._running:
                        self.exit_reason = "completed"
                        break
                    continue
        except Exception as e:
            logger.error(f"❌ Consumer thread crashed: {e}")
            logger.error(traceback.format_exc())
            self.exit_reason = "crashed"
        finally:
            self._flush_buffer()
            if self.exit_reason == "running":
                self.exit_reason = "completed"
            
        logger.info(f"✅ Consumer: processed {self._messages_consumed} messages (exit reason: {self.exit_reason})")
        return self._messages_consumed

    def consume_pubsub(self, timeout: float = 60.0) -> int:
        """Subscribe to Pub/Sub and process messages."""
        try:
            from google.cloud import pubsub_v1
            subscriber = pubsub_v1.SubscriberClient()
            sub_path = subscriber.subscription_path(self.project_id, self.subscription)

            def callback(message):
                data = json.loads(message.data.decode("utf-8"))
                self._process_message(data)
                message.ack()

            future = subscriber.subscribe(sub_path, callback=callback)
            logger.info(f"📡 Listening on {sub_path}")
            try:
                future.result(timeout=timeout)
            except Exception:
                future.cancel()

        except Exception as e:
            logger.error(f"❌ Pub/Sub consumer error: {e}")

        return self._messages_consumed

    def stop(self) -> None:
        self._running = False


# ---------------------------------------------------------------------------
# Telemetry extraction from FastF1
# ---------------------------------------------------------------------------


def extract_lap_telemetry(circuit_name: str, year: int) -> List[Dict]:
    """Extract lap-by-lap telemetry from FastF1 for replay."""
    import fastf1
    from config.settings import FASTF1_CACHE_DIR

    fastf1.Cache.enable_cache(str(FASTF1_CACHE_DIR))

    try:
        schedule = fastf1.get_event_schedule(year)
        target_lower = circuit_name.lower()
        race_round = None

        for _, event in schedule.iterrows():
            name = str(event.get("EventName", "")).lower()
            if target_lower in name or name in target_lower:
                race_round = int(event.get("RoundNumber", 0))
                break

        if not race_round:
            logger.error(f"Circuit not found: {circuit_name}")
            return []

        session = fastf1.get_session(year, race_round, "Race")
        session.load()

        laps = []
        for _, lap in session.laps.iterrows():
            driver = str(lap.get("Driver", ""))
            if not driver:
                continue

            lap_time = lap.get("LapTime")
            if lap_time is not None and hasattr(lap_time, "total_seconds"):
                lt_seconds = lap_time.total_seconds()
            else:
                lt_seconds = None

            s1 = lap.get("Sector1Time")
            s2 = lap.get("Sector2Time")
            s3 = lap.get("Sector3Time")

            laps.append({
                "year": year,
                "round": race_round,
                "circuit_name": circuit_name,
                "driver_code": driver,
                "lap_number": int(lap.get("LapNumber", 0)),
                "lap_time_seconds": lt_seconds,
                "sector1_seconds": s1.total_seconds() if s1 is not None and hasattr(s1, "total_seconds") else None,
                "sector2_seconds": s2.total_seconds() if s2 is not None and hasattr(s2, "total_seconds") else None,
                "sector3_seconds": s3.total_seconds() if s3 is not None and hasattr(s3, "total_seconds") else None,
                "compound": str(lap.get("Compound", "")),
                "tyre_life": int(lap.get("TyreLife", 0)) if lap.get("TyreLife") is not None else None,
                "position": int(lap.get("Position", 0)) if lap.get("Position") is not None else None,
                "gap_to_leader": None,  # Would need delta calculation
            })

        # Sort by lap number for replay order
        laps.sort(key=lambda x: (x["lap_number"], x["driver_code"]))
        logger.info(f"📊 Extracted {len(laps)} lap records from {circuit_name} {year}")
        return laps

    except Exception as e:
        logger.error(f"❌ Failed to extract telemetry: {e}")
        return []


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="🏎️  Simulated Streaming Ingestion — replay historical telemetry"
    )
    parser.add_argument("--simulate", action="store_true",
                        help="Run in simulation mode (local queue)")
    parser.add_argument("--circuit", type=str, default="Hungarian Grand Prix")
    parser.add_argument("--year", type=int, default=2024)
    parser.add_argument("--interval", type=float, default=0.5,
                        help="Seconds between replayed laps")
    parser.add_argument("--log-level", default="INFO",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    args = parser.parse_args()

    logging.basicConfig(level=getattr(logging, args.log_level),
                        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Extract telemetry
    laps = extract_lap_telemetry(args.circuit, args.year)
    if not laps:
        logger.error("No telemetry data extracted — exiting")
        return

    loader = BigQueryLoader()

    if args.simulate:
        # Local queue mode
        local_q = queue.Queue()
        publisher = TelemetryPublisher(local_queue=local_q)
        consumer = TelemetryConsumer(loader=loader, local_queue=local_q)

        # Run consumer in background thread
        consumer_thread = threading.Thread(
            target=consumer.consume_local,
            kwargs={"timeout": len(laps) * args.interval + 300},
            daemon=True,
        )
        consumer_thread.start()

        # Replay in main thread
        publisher.replay_telemetry(laps, interval=args.interval)

        # Wait for consumer to drain with health checks
        timeout_at = time.time() + 300
        while local_q.unfinished_tasks > 0:
            if not consumer_thread.is_alive():
                reason = getattr(consumer, "exit_reason", "unknown")
                if reason == "timed_out":
                    logger.warning("⚠️ Consumer thread exited early due to timeout.")
                elif reason == "crashed":
                    logger.error("❌ Consumer thread crashed with an exception!")
                else:
                    logger.error(f"❌ Consumer thread died unexpectedly! (reason: {reason})")
                break
            if time.time() > timeout_at:
                logger.error("❌ Timed out waiting for queue to drain!")
                break
            time.sleep(0.5)

        consumer.stop()
        consumer_thread.join(timeout=15)

        expected_laps = len(laps)
        persisted_in_memory = consumer._messages_consumed
        
        # Genuinely reliable completion check via BigQuery
        try:
            import os
            from google.cloud import bigquery
            bq_client = bigquery.Client(project=os.getenv("GCP_PROJECT_ID"))
            query = f"""
                SELECT count(*) as cnt 
                FROM `f1_raw.live_lap_telemetry`
                WHERE circuit_name = '{args.circuit}' AND year = {args.year}
            """
            job = bq_client.query(query)
            result = list(job.result())
            actual_bq_count = result[0]['cnt'] if result else 0
        except Exception as e:
            logger.error(f"⚠️ Could not verify BigQuery count: {e}")
            actual_bq_count = -1

        if actual_bq_count == expected_laps:
            logger.info(f"✅ Stream complete: {actual_bq_count}/{expected_laps} laps actually persisted in BigQuery.")
        else:
            logger.error(f"❌ Stream failed or incomplete: internal counter says {persisted_in_memory}, but BigQuery actually has {actual_bq_count}/{expected_laps} rows.")
    else:
        # Pub/Sub mode
        import os
        project_id = os.getenv("GCP_PROJECT_ID")
        if not project_id:
            logger.error("GCP_PROJECT_ID required for Pub/Sub mode")
            return

        publisher = TelemetryPublisher(project_id=project_id)
        publisher.replay_telemetry(laps, interval=args.interval)
        logger.info("🏁 Published to Pub/Sub. Start consumer separately or use --simulate")


if __name__ == "__main__":
    main()
