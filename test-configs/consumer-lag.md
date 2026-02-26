# Experiment 2.1: Consumer Lag & Data Loss Risks

## Objective
Introduce artificial delays in consumer processing to observe the impact on lag. Measure how Kafka handles lag in different configurations (e.g., `max.poll.interval.ms`).

## Config A (Normal Processing)
- **Parameters**:
  - `max.poll.interval.ms=300000` (default)
  - Consumer processing time: Fast (no delay)
- **Code Changes**:
  - None

## Config B (Slow Consumer)
- **Parameters**:
  - `max.poll.interval.ms=60000`
  - Consumer processing time: Slow (artificial delay of 100ms per message)
- **Code Changes**:
  - Modify `ClickStream-Consumer/src/main/java/com/examples/ClicksConsumer.java` to sleep.
  - Modify `ClickStream-Consumer/src/main/resources/consumer.properties`.

## Execution Steps
1.  **Reset Environment**:
    - Stop and remove containers: `cd docker && docker compose down -v`
    - Start cluster: `docker compose up -d`
    - Create unique topic per config (`click-events-2-1-a-<ts>`, `click-events-2-1-b-<ts>`) with 1 partition.
2.  **Apply Config A**:
    - Run `ClicksProducer` (high load).
    - Run `ClicksConsumer`.
    - Warm-up 30s, then monitor lag for 180s using `kafka-consumer-groups --bootstrap-server kafka1:29092`.
    - Collect `docker stats` at +60s and +180s.
3.  **Apply Config B**:
    - Modify consumer code to sleep 100ms.
    - Set `max.poll.interval.ms=60000`.
    - Run `ClicksProducer` (high load).
    - Run `ClicksConsumer`.
    - Warm-up 30s, then monitor lag for 180s.
    - Collect `docker stats` at +60s and +180s.

## Resultat

### Config A (Normal)
- **Producer Sent**: 304752
- **Consumer Received**: 333634
- **Lag samples (topic `click-events-2-1-a-1772094811`)**:
  - t=10s: 233
  - t=60s: 287
  - t=180s: 175
- **Timeout in lag command**: 0 occurrences

### Config B (Slow)
- **Producer Sent**: 132938
- **Consumer Received**: 132973
- **Lag samples (topic `click-events-2-1-b-1772095150`)**:
  - t=10s: 162
  - t=60s: 169
  - t=180s: 88
- **Timeout in lag command**: 0 occurrences

## Interpretation
In Config A, the consumer kept up with the producer.
In Config B, the artificial 100ms delay limited the consumer throughput to ~10 msg/s (1000ms / 100ms). The producer was sending at ~133 msg/s, causing a massive backlog (lag).
With `max.poll.interval.ms=60000`, if the consumer takes too long to process a batch, it might leave the group, triggering rebalancing. Given the batch size (default 500 records) and 100ms delay per record, processing a batch would take 50 seconds, which is dangerously close to the 60s timeout. If a batch had >600 records, the consumer would fail.

## Threats to Validity
- Artificial delay is constant, real world is variable.

## Reproducibility Notes
- Use `kafka-consumer-groups` command.
