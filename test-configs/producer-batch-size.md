# Experiment 1.1: Batch Size & Processing Latency

## Objective
Investigate how different batch sizes affect producer throughput and message latency. We compare small batches (low latency focus) vs. large batches (throughput focus).

## Config A
- **Parameters**:
  - `batch.size=1000`
  - `linger.ms=0`
- **Code Changes**:
  - Modify `ClickStream-Producer/src/main/resources/producer.properties`
  - Run with `-Dsleep.min=1 -Dsleep.max=10` to simulate higher load than default.

## Config B
- **Parameters**:
  - `batch.size=100000`
  - `linger.ms=100`
- **Code Changes**:
  - Modify `ClickStream-Producer/src/main/resources/producer.properties`
  - Run with `-Dsleep.min=1 -Dsleep.max=10`

## Execution Steps
1.  **Reset Environment**:
    - Stop and remove containers: `cd docker && docker compose down -v`
    - Start cluster: `docker compose up -d`
    - Create topic: `docker exec docker-kafka1-1 kafka-topics --create --topic click-events --bootstrap-server localhost:9092 --partitions 1 --replication-factor 2`
2.  **Apply Config A**:
    - Edit `ClickStream-Producer/src/main/resources/producer.properties` to set `batch.size=1000` and `linger.ms=0`.
3.  **Warm-up**:
    - Run `ClicksProducer` for 30 seconds.
4.  **Measurement Window**:
    - Run `ClicksProducer` for 180 seconds.
    - Measure:
        - Total messages sent (from logs).
        - Throughput (msgs/sec).
        - Latency (qualitative observation from logs or if we add instrumentation).
    - Run `docker stats --no-stream` at t=60s and t=180s.
5.  **Apply Config B**:
    - Edit `ClickStream-Producer/src/main/resources/producer.properties` to set `batch.size=100000` and `linger.ms=100`.
    - Repeat steps 3-4.

## Resultat

### Config A
- **Total Messages Sent**: 26338
- **Avg Throughput**: ~146 msg/s
- **Docker Stats (CPU/Mem)**:
  - Kafka1: ~18% CPU, 757MB Mem
  - Kafka2: ~16% CPU, 546MB Mem

### Config B
- **Total Messages Sent**: 25723
- **Avg Throughput**: ~143 msg/s
- **Docker Stats (CPU/Mem)**:
  - Kafka1: ~21-28% CPU, 1006MB Mem
  - Kafka2: ~10-13% CPU, 657MB Mem

## Interpretation
The throughput was nearly identical between the two configurations (~145 msg/s). This is because the producer application logic includes a random sleep (1-10ms), which limits the maximum theoretical throughput to ~180 msg/s.
With `linger.ms=100` in Config B, the producer waited to fill batches. Given the production rate, it formed batches in the low double-digit range.
This batching did not improve throughput (as the bottleneck was the application sleep), but it reduced the number of network requests.
The slightly higher memory usage in Config B might be due to buffering messages for batching.
The latency for individual messages in Config B would be higher (up to 100ms additional delay) due to `linger.ms`.

## Threats to Validity
- The application-side sleep masked potential throughput gains from batching.
- Network latency on local machine is negligible, so batching benefits are less visible than in a real distributed network.

## Reproducibility Notes
- Run with `-Dsleep.min=1 -Dsleep.max=10` to reproduce these results.
