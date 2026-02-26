from __future__ import annotations

import argparse
import time
from pathlib import Path

import matplotlib.pyplot as plt
from confluent_kafka import Consumer, KafkaError, Producer
from confluent_kafka.admin import AdminClient

from experiments.common import (
    DEFAULT_BOOTSTRAP_SERVERS,
    ensure_topic,
    make_results_dir,
    mean,
    wait_for_cluster,
    write_csv,
)


LAG_CASES = [
    {"name": "delay_0ms", "processing_delay_ms": 0},
    {"name": "delay_10ms", "processing_delay_ms": 10},
]

POLL_INTERVAL_CASES = [
    {"name": "low_poll_interval", "max_poll_interval_ms": 6_000, "processing_delay_ms": 7_000},
    {"name": "high_poll_interval", "max_poll_interval_ms": 15_000, "processing_delay_ms": 7_000},
]

OFFSET_RESET_POLICIES = ["earliest", "latest"]


def produce_integer_messages(
    bootstrap_servers: str,
    topic: str,
    start_value: int,
    count: int,
) -> int:
    producer = Producer({"bootstrap.servers": bootstrap_servers, "acks": "all"})
    produced = 0
    for value in range(start_value, start_value + count):
        while True:
            try:
                producer.produce(topic=topic, key=str(value % 32), value=str(value).encode("utf-8"))
                produced += 1
                break
            except BufferError:
                producer.poll(0.01)
        if value % 500 == 0:
            producer.poll(0)
    producer.flush(120)
    return produced


def consumer_total_lag(consumer: Consumer) -> int:
    assignments = consumer.assignment()
    if not assignments:
        return 0

    positions = consumer.position(assignments)
    position_map = {(item.topic, item.partition): item.offset for item in positions}

    lag = 0
    for assignment in assignments:
        low, high = consumer.get_watermark_offsets(assignment, cached=True)
        position = position_map.get((assignment.topic, assignment.partition), low)
        if position < 0:
            position = low
        lag += max(high - position, 0)
    return lag


def run_lag_case(
    bootstrap_servers: str,
    topic: str,
    case_name: str,
    message_count: int,
    processing_delay_ms: int,
) -> dict:
    group_id = f"consumer-lag-{case_name}-{int(time.time() * 1_000)}"
    consumer = Consumer(
        {
            "bootstrap.servers": bootstrap_servers,
            "group.id": group_id,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": True,
            "max.poll.interval.ms": 300_000,
        }
    )
    consumer.subscribe([topic])

    consumed = 0
    errors = 0
    lag_samples: list[int] = []
    delay_s = processing_delay_ms / 1_000.0
    lag_sample_interval_s = 2.0
    next_lag_sample = time.perf_counter() + lag_sample_interval_s
    start = time.perf_counter()
    expected_processing_s = message_count * delay_s
    timeout_at = start + max(60.0, expected_processing_s * 3.0 + 15.0)

    try:
        while consumed < message_count and time.perf_counter() < timeout_at:
            msg = consumer.poll(0.5)
            if msg is None:
                pass
            elif msg.error():
                if msg.error().code() != KafkaError._PARTITION_EOF:
                    errors += 1
            else:
                consumed += 1
                if delay_s > 0:
                    time.sleep(delay_s)

            if time.perf_counter() >= next_lag_sample:
                lag_samples.append(consumer_total_lag(consumer))
                next_lag_sample += lag_sample_interval_s
    finally:
        final_lag = consumer_total_lag(consumer)
        consumer.close()

    duration_s = max(0.0001, time.perf_counter() - start)
    throughput_mps = consumed / duration_s

    if not lag_samples:
        lag_samples.append(final_lag)

    return {
        "case": case_name,
        "topic": topic,
        "messages_expected": message_count,
        "messages_consumed": consumed,
        "processing_delay_ms": processing_delay_ms,
        "consumer_errors": errors,
        "duration_s": round(duration_s, 3),
        "throughput_mps": round(throughput_mps, 2),
        "lag_avg_messages": round(mean(lag_samples), 2),
        "lag_max_messages": max(lag_samples),
        "lag_end_messages": final_lag,
    }


def run_poll_interval_case(
    bootstrap_servers: str,
    topic: str,
    case_name: str,
    message_count: int,
    max_poll_interval_ms: int,
    processing_delay_ms: int,
) -> dict:
    session_timeout_ms = 6_000
    if max_poll_interval_ms < session_timeout_ms:
        raise ValueError(
            "Invalid poll interval case: max_poll_interval_ms must be >= 6000 to satisfy "
            "max.poll.interval.ms >= session.timeout.ms."
        )

    group_id = f"consumer-poll-{case_name}-{int(time.time() * 1_000)}"
    consumer = Consumer(
        {
            "bootstrap.servers": bootstrap_servers,
            "group.id": group_id,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
            "max.poll.interval.ms": max_poll_interval_ms,
            "session.timeout.ms": session_timeout_ms,
        }
    )
    consumer.subscribe([topic])

    consumed = 0
    errors = 0
    max_poll_exceeded = False
    delay_s = processing_delay_ms / 1_000.0
    start = time.perf_counter()
    timeout_at = start + max(20.0, message_count * max(delay_s, 0.2) * 3.0)

    try:
        while consumed < message_count and time.perf_counter() < timeout_at:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                code = msg.error().code()
                if code == KafkaError._MAX_POLL_EXCEEDED:
                    max_poll_exceeded = True
                    break
                if code != KafkaError._PARTITION_EOF:
                    errors += 1
                continue

            consumed += 1
            if delay_s > 0:
                time.sleep(delay_s)
    finally:
        consumer.close()

    duration_s = max(0.0001, time.perf_counter() - start)
    completed = consumed >= message_count and not max_poll_exceeded

    return {
        "case": case_name,
        "topic": topic,
        "messages_expected": message_count,
        "messages_consumed": consumed,
        "max_poll_interval_ms": max_poll_interval_ms,
        "processing_delay_ms": processing_delay_ms,
        "max_poll_exceeded": max_poll_exceeded,
        "completed": completed,
        "consumer_errors": errors,
        "duration_s": round(duration_s, 3),
    }


def wait_for_assignment(consumer: Consumer, timeout_s: float = 10.0) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        consumer.poll(0.2)
        if consumer.assignment():
            return True
    return False


def run_offset_reset_case(
    bootstrap_servers: str,
    topic: str,
    reset_policy: str,
    produced_before: int,
    produced_after: int,
) -> dict:
    produce_integer_messages(bootstrap_servers, topic, start_value=0, count=produced_before)

    group_id = f"offset-reset-{reset_policy}-{int(time.time() * 1_000)}"
    consumer = Consumer(
        {
            "bootstrap.servers": bootstrap_servers,
            "group.id": group_id,
            "auto.offset.reset": reset_policy,
            "enable.auto.commit": False,
        }
    )
    consumer.subscribe([topic])
    if not wait_for_assignment(consumer):
        raise TimeoutError("Consumer did not receive partition assignment in time for offset reset test.")

    produce_integer_messages(
        bootstrap_servers,
        topic,
        start_value=produced_before,
        count=produced_after,
    )

    seen_values: set[int] = set()
    total_expected = produced_before + produced_after
    idle_limit_s = 15.0
    idle_deadline = time.perf_counter() + idle_limit_s
    hard_deadline = time.perf_counter() + 45.0

    try:
        while time.perf_counter() < hard_deadline and time.perf_counter() < idle_deadline:
            msg = consumer.poll(0.5)
            if msg is None:
                continue
            if msg.error():
                continue
            value = int(msg.value().decode("utf-8"))
            seen_values.add(value)
            if len(seen_values) >= total_expected:
                break
            idle_deadline = time.perf_counter() + idle_limit_s
    finally:
        consumer.close()

    consumed_before = len([v for v in seen_values if v < produced_before])
    consumed_after = len([v for v in seen_values if v >= produced_before])
    total_consumed = len(seen_values)

    return {
        "policy": reset_policy,
        "topic": topic,
        "produced_before_consumer_start": produced_before,
        "produced_after_consumer_start": produced_after,
        "consumed_before": consumed_before,
        "consumed_after": consumed_after,
        "consumed_total": total_consumed,
        "missed_old_messages": produced_before - consumed_before,
        "missed_total_messages": total_expected - total_consumed,
    }


def plot_lag_results(rows: list[dict], out_path: Path) -> None:
    labels = [row["case"] for row in rows]
    max_lag = [row["lag_max_messages"] for row in rows]
    throughput = [row["throughput_mps"] for row in rows]

    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    axes[0].bar(labels, max_lag, color="#D62828")
    axes[0].set_title("Max Consumer Lag")
    axes[0].set_ylabel("Messages")
    axes[0].tick_params(axis="x", rotation=20)

    axes[1].bar(labels, throughput, color="#1D3557")
    axes[1].set_title("Consumer Throughput")
    axes[1].set_ylabel("Messages / sec")
    axes[1].tick_params(axis="x", rotation=20)

    fig.suptitle("Consumer Lag Under Processing Delay")
    fig.tight_layout()
    fig.savefig(out_path, dpi=140)
    plt.close(fig)


def plot_offset_results(rows: list[dict], out_path: Path) -> None:
    labels = [row["policy"] for row in rows]
    consumed_total = [row["consumed_total"] for row in rows]
    produced_total = [
        row["produced_before_consumer_start"] + row["produced_after_consumer_start"] for row in rows
    ]

    x_positions = list(range(len(labels)))
    width = 0.35

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar([x - width / 2 for x in x_positions], produced_total, width=width, label="Produced", color="#457B9D")
    ax.bar([x + width / 2 for x in x_positions], consumed_total, width=width, label="Consumed", color="#2A9D8F")
    ax.set_xticks(x_positions, labels)
    ax.set_ylabel("Messages")
    ax.set_title("Offset Reset Policy: Produced vs Consumed")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=140)
    plt.close(fig)


def plot_poll_interval_results(rows: list[dict], out_path: Path) -> None:
    labels = [row["case"] for row in rows]
    completion_ratio = [
        100.0 * row["messages_consumed"] / max(1, row["messages_expected"]) for row in rows
    ]

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(labels, completion_ratio, color="#F4A261")
    ax.set_ylim(0, 110)
    ax.set_ylabel("Consumed % of expected")
    ax.set_title("Impact of max.poll.interval.ms")
    ax.tick_params(axis="x", rotation=20)
    fig.tight_layout()
    fig.savefig(out_path, dpi=140)
    plt.close(fig)


def write_summary(
    lag_rows: list[dict],
    poll_rows: list[dict],
    offset_rows: list[dict],
    out_path: Path,
) -> None:
    lag_by_case = {row["case"]: row for row in lag_rows}
    poll_by_case = {row["case"]: row for row in poll_rows}
    offset_by_policy = {row["policy"]: row for row in offset_rows}

    worst_lag = max(lag_rows, key=lambda row: row["lag_max_messages"])
    slowest_throughput = min(lag_rows, key=lambda row: row["throughput_mps"])
    poll_failure_rows = [row for row in poll_rows if not row["completed"] or row["max_poll_exceeded"]]
    latest_row = offset_by_policy["latest"]
    earliest_row = offset_by_policy["earliest"]

    quality_checks: list[str] = []
    quality_pass = True

    lag_0 = lag_by_case.get("delay_0ms")
    lag_10 = lag_by_case.get("delay_10ms")
    if lag_0 and lag_10:
        if lag_10["lag_max_messages"] > lag_0["lag_max_messages"]:
            quality_checks.append("PASS: added processing delay increased consumer lag.")
        else:
            quality_checks.append("REVIEW: processing delay did not increase lag.")
            quality_pass = False

        if lag_10["throughput_mps"] < lag_0["throughput_mps"]:
            quality_checks.append("PASS: added processing delay reduced consumer throughput.")
        else:
            quality_checks.append("REVIEW: throughput did not drop under processing delay.")
            quality_pass = False

    poll_low = poll_by_case.get("low_poll_interval")
    poll_high = poll_by_case.get("high_poll_interval")
    if poll_low and poll_high:
        if poll_low["max_poll_exceeded"]:
            quality_checks.append("PASS: low poll interval case exceeded max poll interval.")
        else:
            quality_checks.append("REVIEW: low poll interval case did not exceed as expected.")
            quality_pass = False

        if poll_high["completed"]:
            quality_checks.append("PASS: high poll interval case completed.")
        else:
            quality_checks.append("REVIEW: high poll interval case did not complete.")
            quality_pass = False

    if latest_row["missed_old_messages"] > earliest_row["missed_old_messages"]:
        quality_checks.append("PASS: latest skipped more historical records than earliest.")
    else:
        quality_checks.append("REVIEW: latest did not show stronger skipping behavior than earliest.")
        quality_pass = False

    if earliest_row["missed_old_messages"] == 0:
        quality_checks.append("PASS: earliest consumed all historical records in this run.")
    else:
        quality_checks.append(
            "REVIEW: earliest missed historical records (possible timing/rebalance noise)."
        )

    verdict = "GOOD" if quality_pass else "REVIEW"
    lag_messages = lag_rows[0]["messages_expected"] if lag_rows else "n/a"

    lines = [
        "# Consumer Experiment Summary",
        "",
        "## Test Setup",
        f"- Lag test messages per case: `{lag_messages}`.",
        "- Lag cases: `delay_0ms` and `delay_10ms`.",
        "- Poll cases: `low_poll_interval` (`6000ms`) and `high_poll_interval` (`15000ms`) with `7000ms` processing delay.",
        "- Offset reset cases: `earliest` and `latest` for new consumer groups.",
        "",
        "## Consumer Lag Under Processing Delay",
        f"- Highest lag observed in `{worst_lag['case']}` with `{worst_lag['lag_max_messages']}` messages.",
        f"- Lowest throughput observed in `{slowest_throughput['case']}` with `{slowest_throughput['throughput_mps']}` msg/s.",
        "",
        "## max.poll.interval.ms Behavior",
    ]
    if poll_failure_rows:
        lines.append("- At least one case failed or stalled when processing was slower than poll expectations.")
    else:
        lines.append("- All poll interval cases completed without max poll violations.")
    lines.extend(
        [
            "",
            "## Offset Reset Misconfiguration Risk",
            f"- `earliest` consumed old messages missed: `{earliest_row['missed_old_messages']}`.",
            f"- `latest` consumed old messages missed: `{latest_row['missed_old_messages']}`.",
            "- `latest` can skip historical data for new consumer groups, which looks like data loss from the app point of view.",
            "",
            "## Quality Check",
            f"- Verdict: `{verdict}`.",
        ]
    )
    lines.extend([f"- {check}" for check in quality_checks])
    out_path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Kafka consumer experiments.")
    parser.add_argument(
        "--bootstrap-servers",
        default=DEFAULT_BOOTSTRAP_SERVERS,
        help="Kafka bootstrap servers (comma-separated).",
    )
    parser.add_argument(
        "--lag-messages",
        type=int,
        default=1_500,
        help="Message count used for lag experiments.",
    )
    parser.add_argument(
        "--output-dir",
        default="results/consumer",
        help="Directory for CSV, plots, and summary.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = make_results_dir("consumer") if args.output_dir == "results/consumer" else Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    admin = AdminClient({"bootstrap.servers": args.bootstrap_servers})
    wait_for_cluster(admin)

    base_time = int(time.time())

    lag_rows: list[dict] = []
    for case in LAG_CASES:
        topic = f"consumer-lag-{case['name']}-{base_time}"
        ensure_topic(admin, topic, partitions=3, replication_factor=3)
        produce_integer_messages(args.bootstrap_servers, topic, start_value=0, count=args.lag_messages)
        lag_rows.append(
            run_lag_case(
                bootstrap_servers=args.bootstrap_servers,
                topic=topic,
                case_name=case["name"],
                message_count=args.lag_messages,
                processing_delay_ms=case["processing_delay_ms"],
            )
        )

    poll_rows: list[dict] = []
    poll_message_count = 8
    for case in POLL_INTERVAL_CASES:
        topic = f"consumer-poll-{case['name']}-{base_time}"
        ensure_topic(admin, topic, partitions=1, replication_factor=3)
        produce_integer_messages(
            args.bootstrap_servers,
            topic,
            start_value=0,
            count=poll_message_count,
        )
        poll_rows.append(
            run_poll_interval_case(
                bootstrap_servers=args.bootstrap_servers,
                topic=topic,
                case_name=case["name"],
                message_count=poll_message_count,
                max_poll_interval_ms=case["max_poll_interval_ms"],
                processing_delay_ms=case["processing_delay_ms"],
            )
        )

    offset_rows: list[dict] = []
    for policy in OFFSET_RESET_POLICIES:
        topic = f"consumer-offset-{policy}-{base_time}"
        ensure_topic(admin, topic, partitions=1, replication_factor=3)
        offset_rows.append(
            run_offset_reset_case(
                bootstrap_servers=args.bootstrap_servers,
                topic=topic,
                reset_policy=policy,
                produced_before=100,
                produced_after=25,
            )
        )

    write_csv(output_dir / "lag_results.csv", lag_rows)
    write_csv(output_dir / "poll_interval_results.csv", poll_rows)
    write_csv(output_dir / "offset_reset_results.csv", offset_rows)
    plot_lag_results(lag_rows, output_dir / "lag_results.png")
    plot_poll_interval_results(poll_rows, output_dir / "poll_interval_results.png")
    plot_offset_results(offset_rows, output_dir / "offset_reset_results.png")
    write_summary(lag_rows, poll_rows, offset_rows, output_dir / "summary.md")


if __name__ == "__main__":
    main()
