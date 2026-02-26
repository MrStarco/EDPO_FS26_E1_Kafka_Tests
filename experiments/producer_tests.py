from __future__ import annotations

import argparse
import time
from pathlib import Path

import matplotlib.pyplot as plt
from confluent_kafka import Producer
from confluent_kafka.admin import AdminClient

from experiments.common import (
    DEFAULT_BOOTSTRAP_SERVERS,
    ensure_topic,
    make_results_dir,
    mean,
    percentile,
    wait_for_cluster,
    write_csv,
)


BATCH_CASES = [
    {"name": "small_batch", "batch.size": 16_384, "linger.ms": 0},
    {"name": "large_batch", "batch.size": 524_288, "linger.ms": 20},
]

ACK_CASES = [
    {"name": "acks_0", "acks": "0"},
    {"name": "acks_1", "acks": "1"},
    {"name": "acks_all", "acks": "all"},
]


def run_producer_case(
    bootstrap_servers: str,
    topic: str,
    case_name: str,
    message_count: int,
    message_size: int,
    extra_config: dict,
) -> dict:
    latencies_ms: list[float] = []
    delivery_errors = 0
    delivered = 0
    produced = 0
    payload = b"x" * message_size

    base_config = {
        "bootstrap.servers": bootstrap_servers,
        "queue.buffering.max.messages": max(100_000, message_count * 2),
        "compression.type": "none",
    }
    base_config.update(extra_config)
    producer = Producer(base_config)

    def on_delivery(err, _msg, start_ns: int) -> None:
        nonlocal delivered, delivery_errors
        if err is not None:
            delivery_errors += 1
            return
        delivered += 1
        latencies_ms.append((time.perf_counter_ns() - start_ns) / 1_000_000.0)

    start = time.perf_counter()
    for idx in range(message_count):
        while True:
            try:
                sent_ns = time.perf_counter_ns()
                producer.produce(
                    topic=topic,
                    key=str(idx % 64),
                    value=payload,
                    on_delivery=lambda err, msg, s=sent_ns: on_delivery(err, msg, s),
                )
                produced += 1
                break
            except BufferError:
                producer.poll(0.01)

        if idx % 500 == 0:
            producer.poll(0)

    producer.flush(120)
    duration_s = max(0.0001, time.perf_counter() - start)
    throughput = delivered / duration_s

    return {
        "case": case_name,
        "topic": topic,
        "messages_requested": message_count,
        "messages_produced": produced,
        "messages_delivered": delivered,
        "delivery_errors": delivery_errors,
        "duration_s": round(duration_s, 3),
        "throughput_mps": round(throughput, 2),
        "latency_avg_ms": round(mean(latencies_ms), 3),
        "latency_p50_ms": round(percentile(latencies_ms, 50), 3),
        "latency_p95_ms": round(percentile(latencies_ms, 95), 3),
        "latency_p99_ms": round(percentile(latencies_ms, 99), 3),
    }


def plot_case_results(rows: list[dict], out_path: Path, title: str) -> None:
    labels = [row["case"] for row in rows]
    throughputs = [row["throughput_mps"] for row in rows]
    p95_latency = [row["latency_p95_ms"] for row in rows]

    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    axes[0].bar(labels, throughputs, color="#2A9D8F")
    axes[0].set_title("Throughput (msg/s)")
    axes[0].set_ylabel("Messages / sec")
    axes[0].tick_params(axis="x", rotation=20)

    axes[1].bar(labels, p95_latency, color="#E76F51")
    axes[1].set_title("P95 Delivery Latency (ms)")
    axes[1].set_ylabel("Milliseconds")
    axes[1].tick_params(axis="x", rotation=20)

    fig.suptitle(title)
    fig.tight_layout()
    fig.savefig(out_path, dpi=140)
    plt.close(fig)


def write_summary(batch_rows: list[dict], ack_rows: list[dict], out_path: Path) -> None:
    batch_by_case = {row["case"]: row for row in batch_rows}
    ack_by_case = {row["case"]: row for row in ack_rows}

    best_batch_tp = max(batch_rows, key=lambda row: row["throughput_mps"])
    best_batch_latency = min(batch_rows, key=lambda row: row["latency_p95_ms"])
    best_ack_tp = max(ack_rows, key=lambda row: row["throughput_mps"])
    best_ack_latency = min(ack_rows, key=lambda row: row["latency_p95_ms"])

    small_batch = batch_by_case.get("small_batch")
    large_batch = batch_by_case.get("large_batch")
    ack0 = ack_by_case.get("acks_0")
    ack1 = ack_by_case.get("acks_1")
    ack_all = ack_by_case.get("acks_all")

    quality_checks: list[str] = []
    quality_pass = True

    no_delivery_errors = all(row["delivery_errors"] == 0 for row in [*batch_rows, *ack_rows])
    if no_delivery_errors:
        quality_checks.append("PASS: no producer delivery errors in all cases.")
    else:
        quality_checks.append("REVIEW: delivery errors were observed.")
        quality_pass = False

    if small_batch and large_batch:
        if large_batch["throughput_mps"] > small_batch["throughput_mps"]:
            quality_checks.append("PASS: large batch throughput is higher than small batch throughput.")
        else:
            quality_checks.append("REVIEW: large batch throughput did not exceed small batch throughput.")
            quality_pass = False

    if ack0 and ack1 and ack_all:
        if ack0["throughput_mps"] >= max(ack1["throughput_mps"], ack_all["throughput_mps"]):
            quality_checks.append("PASS: acks=0 is the fastest as expected.")
        else:
            quality_checks.append("REVIEW: acks=0 is not the fastest in this run.")
            quality_pass = False

        ack_all_latency_higher = ack_all["latency_p95_ms"] >= ack1["latency_p95_ms"]
        if ack_all_latency_higher:
            quality_checks.append("PASS: acks=all has >= p95 latency than acks=1.")
        else:
            quality_checks.append(
                "REVIEW: acks=all p95 latency is below acks=1 (possible benchmark noise)."
            )

    messages_per_case = batch_rows[0]["messages_requested"] if batch_rows else "n/a"
    verdict = "GOOD" if quality_pass else "REVIEW"

    lines = [
        "# Producer Experiment Summary",
        "",
        "## Test Setup",
        f"- Messages per case: `{messages_per_case}`.",
        "- Batch cases: `small_batch` (`batch.size=16384, linger.ms=0`) and "
        "`large_batch` (`batch.size=524288, linger.ms=20`).",
        "- Acks cases: `acks=0`, `acks=1`, `acks=all`.",
        "",
        "## Batch Size vs Latency/Throughput",
        f"- Highest throughput: `{best_batch_tp['case']}` at `{best_batch_tp['throughput_mps']}` msg/s.",
        f"- Lowest p95 latency: `{best_batch_latency['case']}` at `{best_batch_latency['latency_p95_ms']}` ms.",
        "- Larger batches usually improve throughput by reducing request overhead, but can increase buffering delay.",
        "",
        "## `acks` Durability vs Performance",
        f"- Highest throughput among `acks` configs: `{best_ack_tp['case']}` at `{best_ack_tp['throughput_mps']}` msg/s.",
        f"- Lowest p95 latency among `acks` configs: `{best_ack_latency['case']}` at `{best_ack_latency['latency_p95_ms']}` ms.",
        "- Durability interpretation: `acks=0` fastest but highest loss risk, `acks=all` strongest durability.",
        "",
        "## Quality Check",
        f"- Verdict: `{verdict}`.",
    ]
    lines.extend([f"- {check}" for check in quality_checks])
    out_path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Kafka producer experiments.")
    parser.add_argument(
        "--bootstrap-servers",
        default=DEFAULT_BOOTSTRAP_SERVERS,
        help="Kafka bootstrap servers (comma-separated).",
    )
    parser.add_argument("--messages", type=int, default=20_000, help="Messages per test case.")
    parser.add_argument("--message-size", type=int, default=256, help="Payload size in bytes.")
    parser.add_argument(
        "--output-dir",
        default="results/producer",
        help="Directory for CSV, plots, and summary.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = make_results_dir("producer") if args.output_dir == "results/producer" else Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    admin = AdminClient({"bootstrap.servers": args.bootstrap_servers})
    wait_for_cluster(admin)

    batch_topic = "producer-batch-test"
    ack_topic = "producer-acks-test"
    ensure_topic(admin, batch_topic, partitions=6, replication_factor=3)
    ensure_topic(admin, ack_topic, partitions=6, replication_factor=3)

    batch_rows = []
    for case in BATCH_CASES:
        cfg = {
            "batch.size": case["batch.size"],
            "linger.ms": case["linger.ms"],
            "acks": "1",
        }
        batch_rows.append(
            run_producer_case(
                bootstrap_servers=args.bootstrap_servers,
                topic=batch_topic,
                case_name=case["name"],
                message_count=args.messages,
                message_size=args.message_size,
                extra_config=cfg,
            )
        )

    ack_rows = []
    for case in ACK_CASES:
        cfg = {
            "batch.size": 131_072,
            "linger.ms": 5,
            "acks": case["acks"],
        }
        ack_rows.append(
            run_producer_case(
                bootstrap_servers=args.bootstrap_servers,
                topic=ack_topic,
                case_name=case["name"],
                message_count=args.messages,
                message_size=args.message_size,
                extra_config=cfg,
            )
        )

    write_csv(output_dir / "batch_size_results.csv", batch_rows)
    write_csv(output_dir / "acks_results.csv", ack_rows)
    plot_case_results(batch_rows, output_dir / "batch_size_results.png", "Producer Batch Size Experiment")
    plot_case_results(ack_rows, output_dir / "acks_results.png", "Producer acks Experiment")
    write_summary(batch_rows, ack_rows, output_dir / "summary.md")


if __name__ == "__main__":
    main()
