# Kafka Experiments - Test Report

## Executive Summary
This report documents the findings from a series of experiments conducted on an Apache Kafka cluster with 2 brokers and a dedicated controller. The experiments cover Producer configurations, Consumer behavior, and Fault Tolerance scenarios. The tests were performed using a custom Java Producer and Consumer, running in a Dockerized environment.

Key findings include:
- **Throughput**: Heavily influenced by application-side logic (sleep times) in this specific test setup, masking some low-level Kafka performance differences.
- **Scalability**: Linear throughput scaling was observed when increasing the number of producers, indicating the cluster could handle significantly higher loads than a single client could generate.
- **Durability**: Single-replica topics (`RF=1`) are highly susceptible to data loss during broker failures. High durability configurations (`RF=2`, `acks=all`, `min.insync.replicas=2`) protect data but trade off availability when the cluster is degraded.
- **Consumer Behavior**: Offset misconfiguration (`latest`) can lead to massive data loss (63% observed) if consumers start after production. Slow consumers can cause significant lag and instability.

## Test Environment Setup
- **Kafka Version**: Confluent Platform (latest)
- **Cluster**: 1 Controller, 2 Brokers
- **Producer**: Java-based ClickStream Producer
- **Consumer**: Java-based ClickStream Consumer
- **Infrastructure**: Docker Compose on Localhost

## Detailed Results per Category

### 1. Producer Experiments

#### 1.1 Batch Size & Processing Latency
[Link to Config](test-configs/producer-batch-size.md)

**Summary of Findings:**
- **Throughput**: Similar for both small (`batch.size=1000`) and large (`batch.size=100000`) batches (~145 msg/s), limited by application sleep.
- **Resource Usage**: Large batches with `linger.ms=100` resulted in slightly higher memory usage on brokers but likely reduced network request frequency.
- **Conclusion**: Application-side bottlenecks must be addressed before Kafka tuning yields significant throughput gains.

#### 1.2 Acknowledgment Configuration (acks)
[Link to Config](test-configs/producer-acks.md)

**Summary of Findings:**
- **Throughput**: Surprisingly consistent across `acks=0`, `1`, and `all` (~143-150 msg/s) due to the low-throughput nature of the test.
- **Reliability**: No message loss observed in any configuration under normal conditions (localhost network is reliable).
- **Conclusion**: `acks=all` is viable even for moderate throughput requirements without significant performance penalty in this setup.

#### 1.3 Different Brokers & Partitions
[Link to Config](test-configs/producer-partitions.md)

**Summary of Findings:**
- **Distribution**: 4 partitions distributed load evenly across the 2 brokers.
- **Overhead**: Increasing from 1 to 4 partitions increased broker CPU usage from ~50% to ~75%, indicating a cost to managing more partitions.
- **Throughput**: Remained constant (~150 msg/s) due to single-producer bottleneck.

#### 1.4 Load Testing
[Link to Config](test-configs/producer-load-testing.md)

**Summary of Findings:**
- **Scaling**: Increasing from 1 to 3 producers increased total throughput from ~145 msg/s to ~514 msg/s (linear scaling).
- **Saturation**: At 514 msg/s, broker CPU usage reached ~100%, indicating the cluster capacity limit for this specific hardware/docker allocation.
- **Stability**: No message loss occurred even at saturation.

### 2. Consumer Experiments

#### 2.1 Consumer Lag & Data Loss Risks
[Link to Config](test-configs/consumer-lag.md)

**Summary of Findings:**
- **Normal**: Consumer kept pace with producer (~255 msg/s).
- **Slow Consumer**: Artificial 100ms delay reduced consumer throughput to ~10 msg/s.
- **Consequence**: Massive lag accumulated (24k produced vs 1.7k consumed). Risk of consumer group rebalancing due to timeouts.

#### 2.2 Offset Misconfigurations
[Link to Config](test-configs/consumer-offset.md)

**Summary of Findings:**
- **Earliest**: 100% data recovery (read all historical messages).
- **Latest**: ~63% data loss (missed all messages produced before consumer start).
- **Conclusion**: `auto.offset.reset` is a critical configuration for data integrity.

#### 2.3 Multiple Consumers & Consumer Groups
[Link to Config](test-configs/consumer-groups.md)

**Summary of Findings:**
- **Same Group**: Load balanced. 2 consumers shared the 2 partitions (approx. 50/50 split).
- **Different Groups**: Pub-Sub behavior. Each group received a full copy of the data (Total processed = 2x Produced).

### 3. Fault Tolerance & Reliability

#### 3.1 Broker Failures & Leader Elections
[Link to Config](test-configs/fault-broker-failure.md)

**Summary of Findings:**
- **Resilient (`acks=all`, `retries=5`)**: Seamless failover. Producer continued sending (195 msgs sent).
- **Fragile (`acks=1`, `retries=0`)**: Production halted/failed immediately upon broker death (93 msgs sent).
- **Conclusion**: Client-side configuration (`retries`) is just as important as server-side replication for availability.

#### 3.2 Dropped Messages & Durability
[Link to Config](test-configs/fault-durability.md)

**Summary of Findings:**
- **High Durability (`RF=2`)**: 19.7% "loss" (likely failed sends due to `min.insync.replicas` enforcement preventing writes to single surviving broker). Data on surviving broker was safe.
- **Low Durability (`RF=1`)**: 67.8% loss. Partition became unavailable, and all subsequent writes failed. Data on dead broker is inaccessible.

## Comparative Analysis
The experiments highlight the trade-off between **Availability** and **Durability**.
- **RF=1**: High Availability (if the *right* broker stays up), Low Durability.
- **RF=2, min.insync=1**: High Availability, Medium Durability.
- **RF=2, min.insync=2**: Low Availability (requires both brokers), High Durability.

## Conclusions & Recommendations
1.  **Default to `acks=all`**: The performance penalty is negligible for low-to-medium throughput, but the reliability gain is massive.
2.  **Use `RF=2` or higher**: `RF=1` is unsafe for any production workload.
3.  **Monitor Consumer Lag**: It is the primary indicator of system health and potential data loss (due to retention policies).
4.  **Configure Offsets Carefully**: Default to `earliest` for data-critical applications to avoid missing historical data.

## Reproducibility
All experiments are reproducible using the configurations provided in the `test-configs/` directory and the source code in this repository.
