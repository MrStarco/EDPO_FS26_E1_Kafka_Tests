from __future__ import annotations

import argparse
import subprocess
import threading
import time
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
from confluent_kafka import Consumer, KafkaError, Producer
from confluent_kafka.admin import AdminClient

from experiments.common import (
    DEFAULT_BOOTSTRAP_SERVERS,
    ensure_topic,
    make_results_dir,
    percentile,
    wait_for_cluster,
    write_csv,
)


class ProducerWorker(threading.Thread):
    def __init__(self, bootstrap_servers: str, topic: str, stop_event: threading.Event, rate_mps: int) -> None:
        super().__init__(daemon=True)
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.stop_event = stop_event
        self.rate_mps = max(rate_mps, 1)

        self._lock = threading.Lock()
        self.sent = 0
        self.delivered = 0
        self.errors = 0
        self.delivery_latencies_ms: list[float] = []
        self.delivery_times_s: list[float] = []

    def _on_delivery(self, err, start_ns: int) -> None:
        with self._lock:
            if err is not None:
                self.errors += 1
                return
            self.delivered += 1
            self.delivery_latencies_ms.append((time.perf_counter_ns() - start_ns) / 1_000_000.0)
            self.delivery_times_s.append(time.perf_counter())

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "sent": self.sent,
                "delivered": self.delivered,
                "errors": self.errors,
                "delivery_latencies_ms": list(self.delivery_latencies_ms),
                "delivery_times_s": list(self.delivery_times_s),
            }

    def run(self) -> None:
        producer = Producer(
            {
                "bootstrap.servers": self.bootstrap_servers,
                "acks": "all",
                "batch.size": 65_536,
                "linger.ms": 5,
            }
        )

        payload = b"fault-test-message"
        send_interval_s = 1.0 / self.rate_mps
        next_send_at = time.perf_counter()

        while not self.stop_event.is_set():
            now = time.perf_counter()
            if now < next_send_at:
                time.sleep(min(next_send_at - now, 0.01))
                continue
            if now - next_send_at > send_interval_s:
                next_send_at = now
            next_send_at += send_interval_s

            try:
                sent_ns = time.perf_counter_ns()
                producer.produce(
                    topic=self.topic,
                    key=str(self.sent % 64),
                    value=payload,
                    on_delivery=lambda err, msg, s=sent_ns: self._on_delivery(err, s),
                )
                with self._lock:
                    self.sent += 1
            except BufferError:
                producer.poll(0.01)
                continue

            producer.poll(0)

        producer.flush(20)


class ConsumerWorker(threading.Thread):
    def __init__(self, bootstrap_servers: str, topic: str, stop_event: threading.Event) -> None:
        super().__init__(daemon=True)
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.stop_event = stop_event

        self._lock = threading.Lock()
        self.consumed = 0
        self.errors = 0
        self.consume_times_s: list[float] = []

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "consumed": self.consumed,
                "errors": self.errors,
                "consume_times_s": list(self.consume_times_s),
            }

    def run(self) -> None:
        group_id = f"fault-consumer-{int(time.time() * 1000)}"
        consumer = Consumer(
            {
                "bootstrap.servers": self.bootstrap_servers,
                "group.id": group_id,
                "auto.offset.reset": "latest",
                "enable.auto.commit": True,
            }
        )
        consumer.subscribe([self.topic])

        try:
            while not self.stop_event.is_set():
                msg = consumer.poll(0.5)
                if msg is None:
                    continue
                if msg.error():
                    if msg.error().code() != KafkaError._PARTITION_EOF:
                        with self._lock:
                            self.errors += 1
                    continue

                with self._lock:
                    self.consumed += 1
                    self.consume_times_s.append(time.perf_counter())
        finally:
            consumer.close()


def run_compose(compose_file: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["docker", "compose", "-f", compose_file, *args],
        check=True,
        capture_output=True,
        text=True,
    )


def get_partition_leaders(admin: AdminClient, topic: str) -> dict[int, int]:
    metadata = admin.list_topics(topic=topic, timeout=10)
    topic_metadata = metadata.topics[topic]
    return {
        partition_id: partition_metadata.leader
        for partition_id, partition_metadata in topic_metadata.partitions.items()
    }


def choose_victim_broker(leaders: dict[int, int]) -> int:
    counts = Counter([leader for leader in leaders.values() if leader >= 0])
    if not counts:
        raise RuntimeError("Could not identify partition leaders for victim selection.")
    return max(counts, key=counts.get)


def wait_for_failover(
    admin: AdminClient,
    topic: str,
    victim_broker: int,
    leaders_before: dict[int, int],
    timeout_s: float = 60.0,
) -> tuple[float, dict[int, int]]:
    impacted = {partition for partition, leader in leaders_before.items() if leader == victim_broker}
    if not impacted:
        return 0.0, leaders_before

    start = time.perf_counter()
    deadline = start + timeout_s
    while time.perf_counter() < deadline:
        leaders_after = get_partition_leaders(admin, topic)
        all_reassigned = all(
            leaders_after.get(partition, -1) not in {-1, victim_broker} for partition in impacted
        )
        if all_reassigned:
            return time.perf_counter() - start, leaders_after
        time.sleep(0.5)
    return timeout_s, get_partition_leaders(admin, topic)


def max_gap_seconds(timestamps: list[float]) -> float:
    if len(timestamps) < 2:
        return 0.0
    return max(curr - prev for prev, curr in zip(timestamps[:-1], timestamps[1:]))


def per_second_counts(timestamps: list[float], start_s: float, end_s: float) -> tuple[list[int], list[int]]:
    total_seconds = max(1, int(end_s - start_s) + 1)
    bins = [0 for _ in range(total_seconds)]
    for ts in timestamps:
        idx = int(ts - start_s)
        if 0 <= idx < total_seconds:
            bins[idx] += 1
    seconds = list(range(total_seconds))
    return seconds, bins


def plot_results(
    producer_snapshot: dict,
    consumer_snapshot: dict,
    test_start_s: float,
    test_end_s: float,
    out_path: Path,
) -> None:
    producer_times = producer_snapshot["delivery_times_s"]
    consumer_times = consumer_snapshot["consume_times_s"]
    seconds, producer_counts = per_second_counts(producer_times, test_start_s, test_end_s)
    _, consumer_counts = per_second_counts(consumer_times, test_start_s, test_end_s)
    delivery_latencies = producer_snapshot["delivery_latencies_ms"]

    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    axes[0].plot(seconds, producer_counts, label="Producer deliveries/sec", color="#2A9D8F")
    axes[0].plot(seconds, consumer_counts, label="Consumer messages/sec", color="#264653")
    axes[0].set_title("Traffic During Broker Failure")
    axes[0].set_xlabel("Seconds since test start")
    axes[0].set_ylabel("Messages")
    axes[0].legend()

    if delivery_latencies:
        axes[1].hist(delivery_latencies, bins=30, color="#E76F51")
    axes[1].set_title("Producer Delivery Latency")
    axes[1].set_xlabel("Latency (ms)")
    axes[1].set_ylabel("Count")

    fig.tight_layout()
    fig.savefig(out_path, dpi=140)
    plt.close(fig)


def write_summary(
    row: dict,
    out_path: Path,
    duration_s: int,
    warmup_s: int,
    produce_rate: int,
) -> None:
    quality_checks: list[str] = []
    quality_pass = True

    if row["failover_time_s"] > 0:
        quality_checks.append("PASS: leader failover was observed after broker kill.")
    else:
        quality_checks.append("REVIEW: failover time is zero, check whether impacted partitions were selected.")
        quality_pass = False

    if row["produce_errors"] == 0 and row["produced_delivered"] == row["produced_sent"]:
        quality_checks.append("PASS: producer delivered all sent messages with zero errors.")
    else:
        quality_checks.append("REVIEW: producer had errors or undelivered messages.")
        quality_pass = False

    if row["consumer_errors"] == 0:
        quality_checks.append("PASS: consumer reported zero errors.")
    else:
        quality_checks.append("REVIEW: consumer errors were observed.")
        quality_pass = False

    if row["failover_time_s"] >= 55:
        quality_checks.append("REVIEW: failover likely reached timeout window; cluster may be unhealthy.")
        quality_pass = False
    else:
        quality_checks.append("PASS: failover completed within timeout window.")

    verdict = "GOOD" if quality_pass else "REVIEW"

    lines = [
        "# Fault Tolerance Experiment Summary",
        "",
        "## Test Setup",
        f"- Test duration: `{duration_s}` seconds.",
        f"- Warmup before broker kill: `{warmup_s}` seconds.",
        f"- Producer target rate: `{produce_rate}` msg/s.",
        "- Topic configuration: 6 partitions, replication factor 3.",
        "",
        "## Broker Failure and Leader Election",
        f"- Killed broker id: `{row['victim_broker']}`.",
        f"- Impacted partitions: `{row['impacted_partitions']}`.",
        f"- Leader failover time: `{row['failover_time_s']}` seconds.",
        "",
        "## Producer/Consumer Impact",
        f"- Producer sent `{row['produced_sent']}` and delivered `{row['produced_delivered']}` messages.",
        f"- Producer errors observed: `{row['produce_errors']}`.",
        f"- Consumer processed `{row['consumed_messages']}` messages with max gap `{row['max_consume_gap_s']}` seconds.",
        f"- Producer p95 delivery latency: `{row['producer_p95_latency_ms']}` ms.",
        "",
        "- Short spikes in latency and throughput dips are expected during leader election.",
        "",
        "## Quality Check",
        f"- Verdict: `{verdict}`.",
    ]
    lines.extend([f"- {check}" for check in quality_checks])
    out_path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Kafka broker failure and leader election experiment.")
    parser.add_argument(
        "--bootstrap-servers",
        default=DEFAULT_BOOTSTRAP_SERVERS,
        help="Kafka bootstrap servers (comma-separated).",
    )
    parser.add_argument(
        "--compose-file",
        default="docker-compose.yml",
        help="Path to docker-compose file with kafka1..kafka3 services.",
    )
    parser.add_argument(
        "--duration-s",
        type=int,
        default=30,
        help="Total duration for producer/consumer workload.",
    )
    parser.add_argument(
        "--warmup-s",
        type=int,
        default=6,
        help="Warmup duration before broker kill.",
    )
    parser.add_argument(
        "--produce-rate",
        type=int,
        default=300,
        help="Producer target message rate per second.",
    )
    parser.add_argument(
        "--output-dir",
        default="results/fault_tolerance",
        help="Directory for CSV, plot, and summary.",
    )
    parser.add_argument(
        "--skip-restart",
        action="store_true",
        help="Do not restart killed broker at the end.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = (
        make_results_dir("fault_tolerance")
        if args.output_dir == "results/fault_tolerance"
        else Path(args.output_dir)
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    admin = AdminClient({"bootstrap.servers": args.bootstrap_servers})
    wait_for_cluster(admin)

    topic = f"fault-tolerance-test-{int(time.time())}"
    ensure_topic(admin, topic=topic, partitions=6, replication_factor=3)

    stop_event = threading.Event()
    producer_worker = ProducerWorker(
        bootstrap_servers=args.bootstrap_servers,
        topic=topic,
        stop_event=stop_event,
        rate_mps=args.produce_rate,
    )
    consumer_worker = ConsumerWorker(
        bootstrap_servers=args.bootstrap_servers,
        topic=topic,
        stop_event=stop_event,
    )

    producer_worker.start()
    consumer_worker.start()

    test_start = time.perf_counter()
    time.sleep(max(1, args.warmup_s))

    leaders_before = get_partition_leaders(admin, topic)
    victim_broker = choose_victim_broker(leaders_before)
    impacted_partitions = len([p for p, leader in leaders_before.items() if leader == victim_broker])
    victim_service = f"kafka{victim_broker}"

    run_compose(args.compose_file, "kill", victim_service)
    failover_time_s, leaders_after = wait_for_failover(
        admin,
        topic=topic,
        victim_broker=victim_broker,
        leaders_before=leaders_before,
    )

    elapsed = time.perf_counter() - test_start
    remaining = max(0.0, float(args.duration_s) - elapsed)
    if remaining > 0:
        time.sleep(remaining)

    stop_event.set()
    producer_worker.join(timeout=10)
    consumer_worker.join(timeout=10)
    test_end = time.perf_counter()

    if not args.skip_restart:
        run_compose(args.compose_file, "up", "-d", victim_service)

    producer_snapshot = producer_worker.snapshot()
    consumer_snapshot = consumer_worker.snapshot()
    max_consume_gap_s = max_gap_seconds(consumer_snapshot["consume_times_s"])
    p95_latency = percentile(producer_snapshot["delivery_latencies_ms"], 95)

    row = {
        "topic": topic,
        "victim_broker": victim_broker,
        "victim_service": victim_service,
        "impacted_partitions": impacted_partitions,
        "failover_time_s": round(failover_time_s, 3),
        "produced_sent": producer_snapshot["sent"],
        "produced_delivered": producer_snapshot["delivered"],
        "produce_errors": producer_snapshot["errors"],
        "consumed_messages": consumer_snapshot["consumed"],
        "consumer_errors": consumer_snapshot["errors"],
        "max_consume_gap_s": round(max_consume_gap_s, 3),
        "producer_p95_latency_ms": round(p95_latency, 3),
        "leaders_before": leaders_before,
        "leaders_after": leaders_after,
    }

    write_csv(output_dir / "fault_tolerance_results.csv", [row])
    plot_results(
        producer_snapshot=producer_snapshot,
        consumer_snapshot=consumer_snapshot,
        test_start_s=test_start,
        test_end_s=test_end,
        out_path=output_dir / "fault_tolerance_results.png",
    )
    write_summary(
        row,
        output_dir / "summary.md",
        duration_s=args.duration_s,
        warmup_s=args.warmup_s,
        produce_rate=args.produce_rate,
    )


if __name__ == "__main__":
    main()
