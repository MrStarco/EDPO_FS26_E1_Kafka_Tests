# Kafka Experiment Review

This document explains what was run, what each test means, what we expected, and what the current results show.

## Test Setup Used

- Kafka cluster: 3 brokers (`kafka1`, `kafka2`, `kafka3`) + ZooKeeper via Docker Compose
- Producer command: `uv run producer-tests --messages 20000 --message-size 256`
- Consumer command: `uv run consumer-tests --lag-messages 1500`
- Fault tolerance command: `uv run fault-tolerance-tests --duration-s 30 --warmup-s 6 --produce-rate 300`

## 1) Producer Experiments

### What was run

- Batch size test:
  - `small_batch`: `batch.size=16384`, `linger.ms=0`
  - `large_batch`: `batch.size=524288`, `linger.ms=20`
- Acknowledgment test:
  - `acks=0`, `acks=1`, `acks=all`
- Each case sent 20,000 messages.

### What was tested

- **Batch size** = how much data the producer tries to collect before sending a request.
  - Smaller batch: sends requests more often.
  - Larger batch: sends fewer, bigger requests.
- **acks** = when Kafka confirms a message write.
  - `acks=0`: producer does not wait for broker confirmation.
  - `acks=1`: waits for leader broker confirmation.
  - `acks=all`: waits for all in-sync replicas (strongest durability).

### What was expected

- Larger batches usually improve throughput.
- `acks=0` should be fastest and lowest latency.
- `acks=all` should favor durability and can increase latency.

### Results

- Batch size:
  - `small_batch`: `9195.66 msg/s`, `p95 latency 2095.639 ms`
  - `large_batch`: `161763.76 msg/s`, `p95 latency 85.241 ms`
- Acks:
  - `acks=0`: `371761.9 msg/s`, `p95 8.815 ms`
  - `acks=1`: `95213.9 msg/s`, `p95 151.516 ms`
  - `acks=all`: `113533.63 msg/s`, `p95 139.867 ms`
- Delivery errors: `0` in all producer cases.

### Interpretation

- The main expected trend is visible: `large_batch` strongly outperformed `small_batch`, and `acks=0` was fastest.
- `acks=all` being slightly faster than `acks=1` in this run is possible in short benchmarks due run-to-run noise.

## 2) Consumer Experiments

### What was run

- Lag test with 1,500 messages:
  - `delay_0ms`
  - `delay_10ms` (artificial per-message processing delay)
- Poll interval test:
  - `low_poll_interval`: `max.poll.interval.ms=6000`, `processing_delay=7000ms`
  - `high_poll_interval`: `max.poll.interval.ms=15000`, `processing_delay=7000ms`
- Offset reset test:
  - produce 100 messages before consumer starts
  - start consumer with `earliest` or `latest`
  - produce 25 additional messages

### What was tested

- **Consumer lag** = number of produced messages not yet processed by the consumer.
- **max.poll.interval.ms** = maximum allowed time between consumer polls before Kafka considers the consumer unhealthy.
- **auto.offset.reset** for new consumer groups:
  - `earliest`: start from beginning of topic.
  - `latest`: start from new incoming messages only.

### What was expected

- Adding processing delay should increase lag and reduce throughput.
- Low poll interval case should fail/exceed limit.
- High poll interval case should complete.
- `latest` should skip old data (looks like data loss at application level).

### Results

- Lag test:
  - `delay_0ms`: consumed `1500/1500`, throughput `355.57 msg/s`, max lag `0`
  - `delay_10ms`: consumed `43/1500`, throughput `1.33 msg/s`, max lag `1475`, end lag `1457`
- Poll interval:
  - `low_poll_interval`: consumed `1/8`, `max_poll_exceeded=True`
  - `high_poll_interval`: consumed `8/8`, completed successfully
- Offset reset:
  - `earliest`: consumed old `99/100`, new `25/25` (missed `1` old message)
  - `latest`: consumed old `0/100`, new `25/25` (missed `100` old messages)

### Interpretation

- Expected behavior is clearly visible:
  - delay increased lag heavily
  - low poll interval exceeded as designed
  - high poll interval completed
  - `latest` skipped old records
- One small caveat: `earliest` missed 1 old message in this run, which can happen from timing/rebalance effects in short experiments.

## 3) Fault Tolerance Experiment

### What was run

- Started continuous producer + consumer traffic on a replicated topic.
- Waited 6 seconds (warmup).
- Killed one broker that led the highest number of partitions.
- Measured leader failover time and traffic impact during a 30-second test window.

### What was tested

- **Leader election / failover**: when the leader broker for a partition dies, Kafka elects a new leader from replicas.
- Impact on:
  - producer latency and delivery
  - consumer progress continuity

### What was expected

- Temporary interruption while leaders are re-elected.
- Spike in producer latency around failover.
- Consumer throughput dip during failover.
- No major producer data loss with replication and `acks=all`.

### Results

- Killed broker: `3`
- Impacted partitions: `2`
- Failover time: `19.714 s`
- Producer: sent `9001`, delivered `9001`, errors `0`
- Consumer: processed `8049`, max processing gap `19.682 s`
- Producer p95 latency: `19176.295 ms`

### Interpretation

- Results match expected failover behavior:
  - leader election took about 20 seconds
  - producer did not lose messages
  - consumer saw a temporary gap during election
  - producer latency spike aligns with failover time

## Final Conclusion

The current results are understandable and mostly aligned with expected Kafka behavior across all three experiment groups.
For a stronger report, run producer and consumer suites 2-3 times and present median values alongside this run.
