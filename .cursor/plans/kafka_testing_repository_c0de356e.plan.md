---
name: Kafka Testing Repository
overview: Systematische Durchführung von Kafka-Experimenten mit Producer, Consumer und Fault Tolerance Tests. Erstellung einer umfassenden Test-Dokumentation mit separaten Konfigurations-Markdowns für jedes Experiment.
todos:
  - id: replace-lab-docs
    content: Replace existing lab README with Testing Repository documentation
    status: completed
  - id: stabilize-topic-lifecycle
    content: Decouple topic creation/deletion from producer startup for reproducible tests
    status: completed
  - id: create-structure
    content: Create test-configs/ folder and TEST_REPORT.md template
    status: completed
  - id: producer-batch
    content: "Test 1.1: Batch Size & Latency experiments (2 configs)"
    status: completed
  - id: producer-acks
    content: "Test 1.2: Acknowledgment Configuration experiments (3 configs: acks=0,1,all)"
    status: completed
  - id: define-measurement-protocol
    content: Define fixed, reproducible measurement protocol for every experiment
    status: completed
  - id: producer-partitions
    content: "Test 1.3: Brokers & Partitions experiments (2 configs)"
    status: completed
  - id: producer-load
    content: "Test 1.4: Load Testing experiments (2 configs)"
    status: completed
  - id: consumer-lag
    content: "Test 2.1: Consumer Lag & Data Loss experiments (2 configs)"
    status: completed
  - id: consumer-offset
    content: "Test 2.2: Offset Misconfigurations experiments (2 configs)"
    status: completed
  - id: consumer-groups
    content: "Test 2.3: Multiple Consumers & Groups experiments (2 configs)"
    status: completed
  - id: fault-broker
    content: "Test 3.1: Broker Failures & Leader Elections experiments (2 configs)"
    status: completed
  - id: fault-durability
    content: "Test 3.2: Dropped Messages & Durability experiments (2 configs)"
    status: completed
  - id: consolidate-report
    content: Consolidate all findings into comprehensive TEST_REPORT.md
    status: completed
isProject: false
---

# Kafka Testing Repository - Comprehensive Test Plan

## Scope and Constraints

- Replace the current lab documentation in [README.md](/Users/Marco/IdeaProjects/lab02Part3-ManyBrokers/README.md) with project-owned "Testing Repository" documentation.
- Produce one consolidated findings report in [TEST_REPORT.md](/Users/Marco/IdeaProjects/lab02Part3-ManyBrokers/TEST_REPORT.md).
- Store individual configuration and run instructions per experiment in separate markdown files under [test-configs/](/Users/Marco/IdeaProjects/lab02Part3-ManyBrokers/test-configs/).
- Apply minimal code changes required to execute experiments and collect reliable evidence; no performance tuning or feature improvements.

## Required Documentation Outputs

- Main report: [TEST_REPORT.md](/Users/Marco/IdeaProjects/lab02Part3-ManyBrokers/TEST_REPORT.md)
- Per-test configuration files:
  - [test-configs/producer-batch-size.md](/Users/Marco/IdeaProjects/lab02Part3-ManyBrokers/test-configs/producer-batch-size.md)
  - [test-configs/producer-acks.md](/Users/Marco/IdeaProjects/lab02Part3-ManyBrokers/test-configs/producer-acks.md)
  - [test-configs/producer-partitions.md](/Users/Marco/IdeaProjects/lab02Part3-ManyBrokers/test-configs/producer-partitions.md)
  - [test-configs/producer-load-testing.md](/Users/Marco/IdeaProjects/lab02Part3-ManyBrokers/test-configs/producer-load-testing.md)
  - [test-configs/consumer-lag.md](/Users/Marco/IdeaProjects/lab02Part3-ManyBrokers/test-configs/consumer-lag.md)
  - [test-configs/consumer-offset.md](/Users/Marco/IdeaProjects/lab02Part3-ManyBrokers/test-configs/consumer-offset.md)
  - [test-configs/consumer-groups.md](/Users/Marco/IdeaProjects/lab02Part3-ManyBrokers/test-configs/consumer-groups.md)
  - [test-configs/fault-broker-failure.md](/Users/Marco/IdeaProjects/lab02Part3-ManyBrokers/test-configs/fault-broker-failure.md)
  - [test-configs/fault-durability.md](/Users/Marco/IdeaProjects/lab02Part3-ManyBrokers/test-configs/fault-durability.md)

## Mandatory Per-Experiment Markdown Structure

Every `test-configs/*.md` file must use this exact section order:

1. `# Experiment <id>: <name>`
2. `## Objective`
3. `## Config A`
4. `## Config B`
5. `## Config C` (only for `acks` experiment)
6. `## Execution Steps`
7. `## Resultat`
8. `## Interpretation`
9. `## Threats to Validity`
10. `## Reproducibility Notes`

Minimum content rules:

- `Config A/B/(C)` must include exact parameters, touched files, and runtime command(s).
- `Resultat` must contain raw observed metrics/log evidence (not expectations).
- `Interpretation` must explain why A vs B (or A/B/C) differ and tie back to Kafka behavior.
- No merged "combined findings only" pages without explicit per-config separation.

## Reproducibility Fixes Before Running Experiments

- Stop auto-reset behavior per run by decoupling topic delete/create from producer startup in [ClickStream-Producer/src/main/java/com/examples/ClicksProducer.java](/Users/Marco/IdeaProjects/lab02Part3-ManyBrokers/ClickStream-Producer/src/main/java/com/examples/ClicksProducer.java).
- Move topic lifecycle actions into explicit setup steps documented in each test markdown.
- Keep baseline infrastructure in [docker/docker-compose.yml](/Users/Marco/IdeaProjects/lab02Part3-ManyBrokers/docker/docker-compose.yml) unless an experiment explicitly requires a temporary variant.

## Fixed Measurement Protocol (Mandatory for Every Experiment)

Each experiment (including each configuration) must follow this exact sequence:

1. **Reset environment**: start clean Kafka cluster, verify brokers reachable.
2. **Apply config**: write exact properties and code toggles listed in the corresponding `test-configs/*.md`.
3. **Warm-up**: run producer/consumer for 30 seconds, discard measurements.
4. **Measurement window**: run for fixed 180 seconds.
5. **Collect evidence**:
  - produced message count (from producer counter/log parsing)
  - consumed message count
  - missing IDs / gaps
  - avg throughput (msg/s)
  - end-to-end latency estimate (where available)
  - lag indicators (consumer lag / delayed consumption)
  - `docker stats --no-stream` snapshots at t=60s and t=180s
  - broker/leader state transitions from logs (for fault tests)
6. **Failure trigger** (fault tests only): inject failure at t=90s, record failover start/end timestamps.
7. **Result template**: fill Outcome, Raw Metrics, Interpretation, Threats to Validity.

## Experiment Matrix

### 1) Producer Experiments

- **Batch size vs latency** (2 configs)
  - A: small batch (`batch.size=1000`, `linger.ms=0`)
  - B: large batch (`batch.size=100000`, `linger.ms=100`)
- **Acknowledgments** (**3 configs, explicit requirement**)
  - A: `acks=0`
  - B: `acks=1`
  - C: `acks=all`
- **Brokers and partitions** (2 configs)
  - A: 1 partition
  - B: 4 partitions
- **Load scaling** (2 configs)
  - A: 1 producer instance
  - B: 3 producer instances

### 2) Consumer Experiments

- **Consumer lag and delay risk** (2 configs)
  - A: no artificial delay
  - B: artificial processing delay + adjusted poll interval
- **Offset reset behavior** (2 configs)
  - A: `auto.offset.reset=earliest`
  - B: `auto.offset.reset=latest`
- **Consumer group behavior** (2 configs)
  - A: same group, multiple consumers
  - B: different groups, multiple consumers

### 3) Fault Tolerance and Reliability

- **Broker failure and leader election** (2 configs)
  - A: resilient producer settings (`acks=all`, retries enabled)
  - B: weaker durability settings (`acks=1`, retries reduced/disabled)
- **Dropped messages and durability** (2 configs)
  - A: replication factor 2
  - B: replication factor 1

## Minimal Code-Change Strategy

- Use configuration-first changes in:
  - [ClickStream-Producer/src/main/resources/producer.properties](/Users/Marco/IdeaProjects/lab02Part3-ManyBrokers/ClickStream-Producer/src/main/resources/producer.properties)
  - [ClickStream-Consumer/src/main/resources/consumer.properties](/Users/Marco/IdeaProjects/lab02Part3-ManyBrokers/ClickStream-Consumer/src/main/resources/consumer.properties)
- Restrict Java code edits to:
  - deterministic measurement hooks/logging
  - optional runtime flags (instead of hard-coded test-specific behavior)
  - removing topic reset side effects from steady-state producer runs

## Execution Order

1. Replace [README.md](/Users/Marco/IdeaProjects/lab02Part3-ManyBrokers/README.md) with Testing Repository documentation skeleton.
2. Create `test-configs/*.md` files with exact parameter sets and run steps.
3. Implement minimal reproducibility edits (topic lifecycle and measurement hooks).
4. Run Producer experiments.
5. Run Consumer experiments.
6. Run Fault Tolerance experiments.
7. Consolidate all findings into [TEST_REPORT.md](/Users/Marco/IdeaProjects/lab02Part3-ManyBrokers/TEST_REPORT.md).

## Acceptance Criteria

- All requested categories executed and documented.
- `acks` experiment includes 3 levels (`0`, `1`, `all`).
- Every experiment uses the same fixed measurement protocol.
- Per-test configuration markdown exists and is sufficient for reproduction.
- Main report contains evidence-based findings, not only expectations.

