# Kafka Experiments (Producer, Consumer, Fault Tolerance)

This repository provides 3 Kafka experiment suites in Python:

1. Producer performance and durability tradeoffs
2. Consumer lag, polling behavior, and offset-reset risks
3. Broker failure and leader election impact

Each suite writes `CSV` metrics, `PNG` plots, and a human-readable `summary.md` into `results/`.

## Testbed Setup

### Kafka cluster

- `docker-compose.yml` starts ZooKeeper + 3 Kafka brokers (`kafka1`, `kafka2`, `kafka3`).
- Bootstrap servers used by scripts:
  `localhost:9092,localhost:9093,localhost:9094`
- Replication defaults are set for reliability experiments:
  `default.replication.factor=3`, `min.insync.replicas=2`.

Start cluster:

```bash
docker compose up -d
docker compose ps
```

### Python environment

Install dependencies with `uv`:

```bash
uv sync
```

## Experiment Design

### 1) Producer Experiments

Command:

```bash
uv run producer-tests --messages 20000 --message-size 256
```

Test cases:

- Batch experiment:
  `small_batch` (`batch.size=16384`, `linger.ms=0`) vs
  `large_batch` (`batch.size=524288`, `linger.ms=20`)
- Acknowledgment experiment:
  `acks=0`, `acks=1`, `acks=all`

Metrics:

- Throughput (`messages_delivered / duration_s`)
- Delivery latency (`avg`, `p50`, `p95`, `p99`)
- Delivery errors

What good results look like:

- `large_batch` usually has higher throughput than `small_batch`.
- `acks=0` should be fastest/lowest latency.
- `acks=all` should prioritize durability and may increase latency.
- `delivery_errors` should be 0.

Outputs: `results/producer/`

### 2) Consumer Experiments

Command:

```bash
uv run consumer-tests --lag-messages 1500
```

Test cases:

- Lag under processing delay:
  `delay_0ms` vs `delay_10ms` artificial per-message sleep.
- Poll interval behavior:
  `low_poll_interval` (`max.poll.interval.ms=6000`, delay `7000ms`) and
  `high_poll_interval` (`max.poll.interval.ms=15000`, delay `7000ms`).
- Offset reset misconfiguration:
  new group with `auto.offset.reset=earliest` vs `latest`.

Metrics:

- Consumed messages, throughput, average/max/end lag
- Poll violation flag (`max_poll_exceeded`)
- Missed historical messages under `earliest`/`latest`

What good results look like:

- Added processing delay should increase lag and lower throughput.
- Low poll interval case should exceed poll interval.
- High poll interval case should complete.
- `latest` should miss old messages produced before consumer start.

Outputs: `results/consumer/`

### 3) Fault Tolerance Experiments

Command:

```bash
uv run fault-tolerance-tests --duration-s 30 --warmup-s 6 --produce-rate 300
```

Test flow:

1. Start background producer and consumer on a replicated topic.
2. Identify a broker leading the most partitions.
3. Kill that broker container (`docker compose kill kafkaX`).
4. Measure time until impacted partitions elect new leaders.
5. Keep workload running and capture producer/consumer impact.

Metrics:

- `failover_time_s`
- Producer sent/delivered/errors and p95 delivery latency
- Consumer processed count and max inter-message gap

What good results look like:

- Non-zero failover time with successful leader reassignment.
- Producer delivery should continue (possibly with latency spikes).
- Consumer throughput may dip temporarily but should recover.

Outputs: `results/fault_tolerance/`

## Running Order

Suggested order for the report:

1. Producer tests
2. Consumer tests
3. Fault tolerance tests

This order keeps infrastructure stable before intentionally killing a broker.

## Stop Cluster

```bash
docker compose down
```

## Notes and Caveats

- Scripts create unique topic names (timestamp suffix) to avoid offset collisions.
- Single-run benchmarks are noisy; for the report, run each suite at least 2-3 times and compare trends.
- `acks=0` improves speed but increases message-loss risk during failures.
- `auto.offset.reset=latest` can look like data loss for new consumer groups because historical records are skipped.
