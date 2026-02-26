from __future__ import annotations

import csv
import os
import statistics
import time
from pathlib import Path
from typing import Iterable, Sequence

from confluent_kafka.admin import AdminClient, NewTopic

DEFAULT_BOOTSTRAP_SERVERS = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS",
    "localhost:9092,localhost:9093,localhost:9094",
)
RESULTS_ROOT = Path("results")


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def make_results_dir(suite_name: str) -> Path:
    return ensure_dir(RESULTS_ROOT / suite_name)


def percentile(values: Sequence[float], q: float) -> float:
    if not values:
        return 0.0
    if q <= 0:
        return float(min(values))
    if q >= 100:
        return float(max(values))

    sorted_values = sorted(values)
    k = (len(sorted_values) - 1) * (q / 100.0)
    floor_idx = int(k)
    ceil_idx = min(floor_idx + 1, len(sorted_values) - 1)
    if floor_idx == ceil_idx:
        return float(sorted_values[floor_idx])
    return float(
        sorted_values[floor_idx] * (ceil_idx - k)
        + sorted_values[ceil_idx] * (k - floor_idx)
    )


def mean(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return float(statistics.fmean(values))


def write_csv(path: Path, rows: Iterable[dict]) -> None:
    rows = list(rows)
    if not rows:
        return
    ensure_dir(path.parent)
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def wait_for_cluster(admin: AdminClient, timeout_s: float = 60.0) -> None:
    deadline = time.time() + timeout_s
    last_error = ""
    while time.time() < deadline:
        try:
            metadata = admin.list_topics(timeout=5)
            if metadata.brokers:
                return
            last_error = "No brokers reported in metadata."
        except Exception as exc:  # pragma: no cover - defensive for transient startup issues
            last_error = str(exc)
        time.sleep(1.0)
    raise TimeoutError(f"Kafka cluster not ready after {timeout_s:.1f}s. Last error: {last_error}")


def topic_exists(admin: AdminClient, topic: str) -> bool:
    metadata = admin.list_topics(timeout=10)
    topic_metadata = metadata.topics.get(topic)
    return topic_metadata is not None and topic_metadata.error is None


def ensure_topic(
    admin: AdminClient,
    topic: str,
    partitions: int = 3,
    replication_factor: int = 3,
    timeout_s: float = 30.0,
) -> None:
    if topic_exists(admin, topic):
        return
    future_map = admin.create_topics(
        [NewTopic(topic=topic, num_partitions=partitions, replication_factor=replication_factor)]
    )
    future = future_map[topic]
    try:
        future.result(timeout=timeout_s)
    except Exception as exc:
        message = str(exc)
        if "TOPIC_ALREADY_EXISTS" not in message:
            raise

    wait_for_topic(admin, topic=topic, timeout_s=timeout_s)


def wait_for_topic(admin: AdminClient, topic: str, timeout_s: float = 30.0) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if topic_exists(admin, topic):
            return
        time.sleep(0.5)
    raise TimeoutError(f"Topic '{topic}' not visible after {timeout_s:.1f}s.")


def delete_topic(admin: AdminClient, topic: str, timeout_s: float = 20.0) -> None:
    if not topic_exists(admin, topic):
        return
    future_map = admin.delete_topics([topic], operation_timeout=timeout_s, request_timeout=timeout_s)
    future = future_map[topic]
    try:
        future.result(timeout=timeout_s)
    except Exception:
        # It can fail while deletion is already in progress. Continue and wait.
        pass

    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if not topic_exists(admin, topic):
            return
        time.sleep(0.5)

