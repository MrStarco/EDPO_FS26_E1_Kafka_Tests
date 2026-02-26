# Experiment 3.2: Dropped Messages & Durability

## Objective
Test the risk of dropped messages when a broker goes down. Compare message durability when using different replication factors and acknowledgment settings.

## Config A (High Durability)
- **Parameters**:
  - `replication-factor=2`
  - `acks=all`
  - `min.insync.replicas=2` (Strict durability)
- **Code Changes**:
  - Modify `ClickStream-Producer/src/main/resources/producer.properties`

## Config B (Low Durability)
- **Parameters**:
  - `replication-factor=1`
  - `acks=1`
- **Code Changes**:
  - Modify `ClickStream-Producer/src/main/resources/producer.properties`

## Execution Steps
1.  **Reset Environment**:
    - Stop and remove containers: `cd docker && docker compose down -v`
    - Start cluster: `docker compose up -d`
2.  **Apply Config A**:
    - Create topic `click-events-3.2_A` with replication factor 2.
    - Configure topic `min.insync.replicas=2`.
    - Run `ClicksProducer`.
    - Kill Leader Broker.
    - Measure dropped messages (Producer Sent - Consumer Received).
3.  **Apply Config B**:
    - Create topic `click-events-3.2_B` with replication factor 1.
    - Run `ClicksProducer`.
    - Kill Leader Broker.
    - Measure dropped messages.

## Resultat

### Config A (High Durability)
- **Producer Sent**: 557
- **Consumer Received**: 447
- **Loss**: 110 messages (19.7%)
- **Observation**: The producer with `acks=all` and `min.insync.replicas=2` stopped making durable progress when one broker died (2 replicas required, 1 alive). The 110-message gap (sent vs. received) can be explained by producer-side buffering and failed sends during degraded ISR conditions. With `retries=5`, send attempts were retried until failure or process termination. The consumer received the records that were committed successfully.

### Config B (Low Durability)
- **Producer Sent**: 255
- **Consumer Received**: 82
- **Loss**: 173 messages (67.8%)
- **Observation**: With `replication-factor=1`, when the leader broker died, the partition became unavailable. There was no replica to take over. All messages sent after the broker death were lost. The producer (with `acks=1`) might have thought some were sent if they were in flight, or simply failed to send. The high loss rate confirms that single-replica topics are not durable against broker failure.

## Interpretation
Config A provides better durability but sacrifices availability when `min.insync.replicas=2` cannot be met (i.e., when 1 of 2 brokers is down). The observed "loss" is "failed to produce" rather than "committed and lost".
Config B is catastrophic for durability. When the only broker hosting the partition dies, the data is inaccessible (and potentially lost if the broker disk is ephemeral or corrupted), and no new data can be written.

## Threats to Validity
- "Producer Sent" count in logs might include messages that threw an exception which was caught and logged but not successfully sent.

## Reproducibility Notes
- Use `kafka-configs` to set topic configs.
