# Kafka Experiment Review

This document explains what was run, what each test means, what we expected, and what the current results show.

## Test Setup Used

- Local single-broker laptop setup
- Producer-focused experiment suite
- Variables analyzed: producer count, partition count, acknowledgment mode, batch size

## 1) Producer Experiments

### What was run

- Producer scaling comparison across different numbers of producers
- Partition scaling comparison across different partition counts
- Acknowledgment mode comparison:
  - `acks=0`
  - `acks=1`
  - `acks=all`
- Batch size comparison

### What was tested

- **Producer scaling** = how throughput changes when running more producers in parallel.
- **Partition scaling** = whether higher partition count improves throughput in this environment.
- **Acknowledgment level (`acks`)** = how durability confirmation level affects throughput.
- **Batch size** = whether larger batches improve throughput and how they affect latency.

### What was expected

- More producers should increase throughput.
- More partitions can improve parallelism if hardware and broker capacity allow it.
- `acks=0` should be fastest and less durable.
- Larger batch sizes may improve throughput but can increase latency.

### Results

- Producer scaling:
  - Throughput increases as the number of producers increases.
  - Scaling is weaker when stronger acknowledgment levels (`acks=1`, `acks=all`) are used.
- Partition scaling:
  - Increasing partitions did not significantly improve throughput.
  - On a single-broker laptop setup, all partitions share the same hardware resources.
- Acknowledgment level:
  - `acks=0` achieves the highest throughput.
  - `acks=1` and `acks=all` reduce throughput due to durability guarantees.
  - The difference between `acks=1` and `acks=all` is small in this setup.
- Batch size:
  - Larger batch sizes increase latency.
  - Throughput does not significantly improve in this small-scale setup.

### Interpretation

- Kafka benefits from producer-side parallelism in this setup.
- Partition count alone does not provide significant gains when hardware/broker resources are the bottleneck.
- The durability/performance tradeoff of `acks` is visible and consistent with expectations.
- The batch-size outcome suggests the setup is resource-limited rather than network-limited.

## Final Conclusion

The observed producer-side results are consistent with expected Kafka behavior for a small single-broker environment:
- parallel producers improve throughput,
- stronger durability settings reduce raw speed,
- and larger batches mainly shift latency without clear throughput gains under current resource limits.