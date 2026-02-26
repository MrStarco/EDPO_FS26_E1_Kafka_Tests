# Experiment 1.3: Different Brokers & Partitions

## Objective
Assess producer behavior when sending messages to topics with different partition counts (1 vs 4) across 2 brokers. We measure throughput and distribution.

## Config A (1 Partition)
- **Parameters**:
  - `partitions=1`
  - `replication-factor=2`
- **Code Changes**:
  - Modify `ClickStream-Producer/src/main/resources/producer.properties` (standard config)
  - Run with `-Dsleep.min=1 -Dsleep.max=10`

## Config B (4 Partitions)
- **Parameters**:
  - `partitions=4`
  - `replication-factor=2`
- **Code Changes**:
  - Modify `ClickStream-Producer/src/main/resources/producer.properties` (standard config)
  - Run with `-Dsleep.min=1 -Dsleep.max=10`

## Execution Steps
1.  **Reset Environment**:
    - Stop and remove containers: `cd docker && docker compose down -v`
    - Start cluster: `docker compose up -d`
2.  **Apply Config A**:
    - Create topic `click-events-1.3_A` with 1 partition.
    - Run `ClicksProducer` for 180 seconds.
    - Run `ClicksConsumer` for 180 seconds.
    - Collect metrics.
3.  **Apply Config B**:
    - Create topic `click-events-1.3_B` with 4 partitions.
    - Run `ClicksProducer` for 180 seconds.
    - Run `ClicksConsumer` for 180 seconds.
    - Collect metrics.

## Resultat

### Config A (1 Partition)
- **Producer Sent**: 26995
- **Consumer Received**: 26996
- **Throughput**: ~150 msg/s
- **Partition Distribution**: All messages in partition 0.
- **Docker Stats**:
  - Kafka1: ~52% CPU
  - Kafka2: ~46% CPU

### Config B (4 Partitions)
- **Producer Sent**: 26581
- **Consumer Received**: 26584
- **Throughput**: ~147 msg/s
- **Partition Distribution**: Messages distributed across partitions 0, 1, 2, 3.
- **Docker Stats**:
  - Kafka1: ~70-78% CPU
  - Kafka2: ~50-58% CPU

## Interpretation
Throughput was similar for both configurations (~147-150 msg/s), again limited by the producer application sleep.
However, Config B (4 partitions) showed significantly higher CPU usage on the brokers (~70-78% vs ~52%). This indicates additional overhead from managing more partitions, including metadata updates, replication coordination, and file handle management.
Despite the overhead, multiple partitions allow for parallel consumption (which we didn't fully exploit with a single consumer thread group).
The load balancing across brokers was effective in both cases due to replication (both brokers handle leader/follower roles), but 4 partitions allow for finer-grained leadership distribution.

## Threats to Validity
- Single producer instance.
- Application-side bottleneck masks throughput potential of partitioning.

## Reproducibility Notes
- Ensure unique topic names.
