# Experiment 3.1: Broker Failures & Leader Elections

## Objective
Kill a broker and observe how leader election for partitions occurs. Measure failover time and impact on producer/consumer operations.

## Config A (Resilient)
- **Parameters**:
  - `acks=all`
  - `retries=5`
  - `replication-factor=2`
- **Code Changes**:
  - Modify `ClickStream-Producer/src/main/resources/producer.properties`

## Config B (Fragile)
- **Parameters**:
  - `acks=1`
  - `retries=0`
  - `replication-factor=2`
- **Code Changes**:
  - Modify `ClickStream-Producer/src/main/resources/producer.properties`

## Execution Steps
1.  **Reset Environment**:
    - Stop and remove containers: `cd docker && docker compose down -v`
    - Start cluster: `docker compose up -d`
    - Create topic `click-events-3.1` with 1 partition, replication factor 2.
2.  **Apply Config A**:
    - Run `ClicksProducer`.
    - Wait 30s.
    - Kill Leader Broker (`docker stop ...`).
    - Observe logs for Leader change and ISR update.
    - Measure time until producer resumes sending (if it blocked) or errors.
3.  **Apply Config B**:
    - Restart cluster.
    - Run `ClicksProducer`.
    - Wait 30s.
    - Kill Leader Broker.
    - Observe impact.

## Resultat

### Config A (Resilient)
- **Total Messages Sent**: 195
- **Behavior**: The producer continued to send messages after the leader broker was killed. The client successfully failed over to the new leader (the remaining broker).
- **Failover**: Seamless. No exception crashed the application.

### Config B (Fragile)
- **Total Messages Sent**: 93
- **Behavior**: The producer stopped sending messages (or significantly slowed down/failed) after the leader was killed.
- **Failover**: Failed or blocked. The application encountered errors it did not recover from due to `retries=0`.

## Interpretation
Config A (`acks=all`, `retries=5`) demonstrated high availability. When the leader broker died, the producer retried until the metadata updated and a new leader was found. The cluster (with replication factor 2) had a replica ready to take over.
Config B (`acks=1`, `retries=0`) was fragile. When the leader died, the send operation failed. Without retries, these messages were lost or the application state became invalid. The significantly lower message count (93 vs 195) confirms that production halted or messages were dropped immediately after the failure.

## Threats to Validity
- The exact moment of failure injection relative to a batch send can influence the number of dropped messages.

## Reproducibility Notes
- Identify leader before killing.
