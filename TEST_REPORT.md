# Combined Test Report - E1 Kafka

## Submission Header
- Course: Event-driven and Process-oriented Architectures (EDPO), FS2026, University of St.Gallen
- Assignment: Exercise 1 - Kafka Getting Started
- Group 4
  - Evan Martino
  - Marco Birchler
  - Roman Babukh

## Scope and Method
This document is the combined, high-level E1 report on `main`. It consolidates results from:
- `marco` branch (Java-based manual experiment workflow, 2-broker setup)
- `roman` branch (Python-based automated experiment workflow, 3-broker setup)

The structure follows the E1 task categories:
1. Producer experiments
2. Consumer experiments
3. Fault tolerance and reliability

## Branch-Based Evidence Map
- `marco`: `TEST_REPORT.md`, `test-configs/`, `Stats/`, `Logs/`
- `roman`: `results/review.md`, `results/producer/summary.md`, `results/consumer/summary.md`, `results/fault_tolerance/summary.md`

---

## 1) Producer Experiments

### 1.1 Batch Size and Latency
Observed trend across both branches: batching materially affects throughput/latency characteristics, but the absolute impact depends on the benchmark harness.

- Marco (`marco`): small and large batch setups are both around `~145 msg/s`, with application-side sleep identified as the dominant bottleneck.
- Roman (`roman`): `small_batch` = `9195.66 msg/s` (p95 `2095.639 ms`) vs `large_batch` = `161763.76 msg/s` (p95 `85.241 ms`).

Interpretation:
- Both branches support the same conceptual result from Kafka literature: larger batches improve wire efficiency.
- The stronger effect in `roman` is consistent with a less application-throttled test harness.

Source citations:
- Marco: `origin/marco:TEST_REPORT.md`
- Roman: `origin/roman:results/review.md`

### 1.2 Acknowledgment Settings (`acks`)
- Marco (`marco`): throughput remains similar for `acks=0`, `acks=1`, and `acks=all` (`~143-150 msg/s`) under low-rate local conditions.
- Roman (`roman`): clear ordering by performance and latency:
  - `acks=0`: `371761.9 msg/s`, p95 `8.815 ms`
  - `acks=1`: `95213.9 msg/s`, p95 `151.516 ms`
  - `acks=all`: `113533.63 msg/s`, p95 `139.867 ms`

Interpretation:
- The reliability/performance trade-off exists in both branches, but is easier to observe under higher-throughput automation.
- `acks=all` is acceptable in both branches when durability is prioritized.

Source citations:
- Marco: `origin/marco:TEST_REPORT.md`
- Roman: `origin/roman:results/review.md`

### 1.3 Brokers, Partitions, and Load Scaling
- Marco (`marco`): increasing partitions from 1 to 4 raises broker CPU from `~50%` to `~75%`, while single-producer throughput remains around `~150 msg/s`.
- Marco (`marco`) load test: scaling from 1 to 3 producers increases aggregate throughput from `~145` to `~514 msg/s`, with CPU near saturation at peak.
- Roman (`roman`): higher-end automated producer numbers show that benchmark setup can expose substantially larger throughput envelopes.

Interpretation:
- Partitioning increases management overhead but supports parallelism.
- Throughput scaling with more producers is confirmed.

Source citations:
- Marco: `origin/marco:TEST_REPORT.md`
- Roman: `origin/roman:results/review.md`

---

## 2) Consumer Experiments

### 2.1 Consumer Lag Under Processing Delay
- Marco (`marco`): normal consumption at `~255 msg/s`; with artificial delay, lag grows heavily (`24k` produced vs `1.7k` consumed in one scenario).
- Roman (`roman`): delay comparison on 1500 messages:
  - `delay_0ms`: consumed `1500/1500`, max lag `0`, throughput `355.57 msg/s`
  - `delay_10ms`: consumed `43/1500`, max lag `1475`, end lag `1457`, throughput `1.33 msg/s`

Interpretation:
- Both branches strongly confirm that added per-message processing delay can destabilize consumer progress and produce large lag.

Source citations:
- Marco: `origin/marco:TEST_REPORT.md`
- Roman: `origin/roman:results/review.md`

### 2.2 Offset Reset Misconfiguration Risk
- Marco (`marco`): with `latest`, approximately `63%` effective data loss in scenarios where production starts before consumer.
- Roman (`roman`):
  - `earliest`: old `99/100`, new `25/25`
  - `latest`: old `0/100`, new `25/25`

Interpretation:
- Both branches confirm the same operational warning: `auto.offset.reset=latest` can skip historical records for fresh groups and look like data loss.

Source citations:
- Marco: `origin/marco:TEST_REPORT.md`
- Roman: `origin/roman:results/review.md`

### 2.3 Multiple Consumers and Group Behavior
- Marco (`marco`): same-group consumers split partitions approximately `50/50`; different groups each receive full stream copies (pub-sub behavior).
- Roman (`roman`): poll-interval experiment shows group stability is sensitive to processing duration:
  - `low_poll_interval`: `max_poll_exceeded=True`, consumed `1/8`
  - `high_poll_interval`: consumed `8/8`

Interpretation:
- Group assignment and poll timing settings are critical for stable consumption and predictable throughput.

Source citations:
- Marco: `origin/marco:TEST_REPORT.md`
- Roman: `origin/roman:results/review.md`

---

## 3) Fault Tolerance and Reliability

### 3.1 Broker Failure and Leader Election
- Marco (`marco`):
  - resilient config (`acks=all`, retries enabled): producer continued (`195` msgs sent)
  - fragile config (`acks=1`, retries disabled): early failure (`93` msgs sent)
- Roman (`roman`):
  - failover time `19.714 s`
  - producer sent `9001`, delivered `9001`, errors `0`
  - consumer processed `8049`
  - producer p95 latency spike `19176.295 ms`

Interpretation:
- Both branches show expected failover behavior: temporary service disturbance, latency spikes, and strong dependence on client/server reliability settings.

Source citations:
- Marco: `origin/marco:TEST_REPORT.md`
- Roman: `origin/roman:results/review.md`

### 3.2 Durability and Message Loss Risk
- Marco (`marco`):
  - `RF=1`: `67.8%` loss in failure scenario
  - high-durability setup (`RF=2`, strict ISR): `19.7%` failed-write/loss effect under degraded cluster
- Roman (`roman`):
  - replicated setup with `acks=all` and controlled failover maintained full producer delivery in the measured run

Interpretation:
- A single replica is unsafe for reliable workloads.
- Durability settings reduce silent loss but can lower write availability during failures.

Source citations:
- Marco: `origin/marco:TEST_REPORT.md`
- Roman: `origin/roman:results/review.md`

---

## Consolidated Conclusions
1. Keep `acks=all` for reliability-sensitive use cases; benchmark cost in your own environment.
2. Avoid `RF=1` for critical data paths.
3. Monitor consumer lag continuously; lag growth is an early warning for instability.
4. Treat `auto.offset.reset` as a data-safety setting, not a convenience default.
5. Interpret performance numbers in context of harness constraints (application sleeps, cluster topology, and load model).

## Contribution Mapping
- Marco Birchler: Java/manual experiment design and execution (`marco` branch evidence)
- Roman Babukh: Python/automated experiment framework and outputs (`roman` branch evidence)
- Evan Martino: Group member for the consolidated E1 submission

## GitHub Branch References
- Repository root: https://github.com/MrStarco/EDPO_FS26_E1_Kafka_Tests
- Marco branch: https://github.com/MrStarco/EDPO_FS26_E1_Kafka_Tests/tree/marco
- Roman branch: https://github.com/MrStarco/EDPO_FS26_E1_Kafka_Tests/tree/roman
