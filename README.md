# Kafka Testing Repository

This repository contains systematic experiments with Apache Kafka, focusing on Producer, Consumer, and Fault Tolerance aspects. It is based on the `lab02Part3-ManyBrokers` exercise.

## Project Structure

- `TEST_REPORT.md`: The main report consolidating all findings from the experiments.
- `test-configs/`: Contains individual configuration and execution instructions for each experiment.
- `docker/`: Docker Compose infrastructure for the Kafka cluster (Controller + 2 Brokers).
- `ClickStream-Producer/`: Java Producer implementation.
- `ClickStream-Consumer/`: Java Consumer implementation.

## Experiments Overview

### 1. Producer Experiments
- **Batch Size & Latency**: Investigating the impact of batching on throughput and latency.
- **Acknowledgment Configuration**: Testing `acks=0`, `acks=1`, and `acks=all` for durability vs. performance trade-offs.
- **Brokers & Partitions**: Analyzing behavior with different partition counts.
- **Load Testing**: Evaluating system behavior under increased load.

### 2. Consumer Experiments
- **Consumer Lag & Data Loss**: Observing the impact of artificial delays and lag.
- **Offset Misconfigurations**: Testing `earliest` vs `latest` offset reset policies.
- **Multiple Consumers & Groups**: Analyzing rebalancing and message distribution.

### 3. Fault Tolerance & Reliability
- **Broker Failures**: Testing leader election and failover times.
- **Dropped Messages & Durability**: Assessing data loss risks under failure scenarios with different replication factors.

## How to Run Experiments

Each experiment has a dedicated markdown file in `test-configs/` with detailed instructions.
General workflow:
1.  Navigate to `docker/` and start the cluster: `docker compose up --build`
2.  Apply the specific configurations described in the experiment file.
3.  Run the Producer and Consumer applications.
4.  Collect metrics and observations.
5.  Document findings in the corresponding section of `TEST_REPORT.md`.

## Prerequisites

- Docker & Docker Compose
- Java 17+
- Maven
