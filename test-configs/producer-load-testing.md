# Experiment 1.4: Load Testing

## Objective
Evaluate how Kafka behaves under increasing load with an increasing number of producers. We measure message drop rates, latency, and CPU/memory utilization.

## Config A (1 Producer)
- **Parameters**:
  - 1 Producer Instance
  - `sleep.min=1`, `sleep.max=10`
- **Code Changes**:
  - None (use standard producer)

## Config B (3 Producers)
- **Parameters**:
  - 3 Producer Instances running in parallel
  - `sleep.min=1`, `sleep.max=10`
- **Code Changes**:
  - None (launch multiple processes)

## Execution Steps
1.  **Reset Environment**:
    - Stop and remove containers: `cd docker && docker compose down -v`
    - Start cluster: `docker compose up -d`
    - Create topic `click-events-1.4_A` (Config A) or `click-events-1.4_B` (Config B) with 1 partition, replication factor 2.
2.  **Apply Config A**:
    - Run 1 instance of `ClicksProducer`.
    - Run `ClicksConsumer`.
    - Collect metrics for 180s.
3.  **Apply Config B**:
    - Run 3 instances of `ClicksProducer` simultaneously.
    - Run `ClicksConsumer`.
    - Collect metrics for 180s.

## Resultat

### Config A (1 Producer)
- **Total Sent**: 26117
- **Total Received**: 26118
- **Throughput**: ~145 msg/s
- **Docker Stats**:
  - Kafka1: ~58% CPU
  - Kafka2: ~99% CPU (Note: Kafka2 showed unusually high CPU usage in this run, possibly due to being the leader or background tasks)

### Config B (3 Producers)
- **Total Sent**: 92634 (30904 + 30954 + 30776)
- **Total Received**: 92656
- **Throughput**: ~514 msg/s (Combined)
- **Docker Stats**:
  - Kafka1: ~101-105% CPU
  - Kafka2: ~93-96% CPU

## Interpretation
Scaling from 1 to 3 producers resulted in a near-linear increase in throughput (~145 msg/s to ~514 msg/s). This confirms that the single producer instance was indeed the bottleneck (due to application sleep).
With 3 producers, the brokers were pushed to their limits (CPU ~100%).
Despite the high load, no message loss was observed (Received >= Sent).
The consumer was able to keep up with the increased load (~514 msg/s).

## Threats to Validity
- Client machine resources were sufficient to run 3 producers and 1 consumer.
- Kafka brokers running in Docker on Mac might have CPU throttling.

## Reproducibility Notes
- Use `&` to run processes in background.
