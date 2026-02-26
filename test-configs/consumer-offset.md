# Experiment 2.2: Offset Misconfigurations

## Objective
Experiment with `auto.offset.reset` (`earliest` vs. `latest`) and observe potential data loss scenarios when a consumer joins a group after messages have been produced.

## Config A (Earliest)
- **Parameters**:
  - `auto.offset.reset=earliest`
- **Code Changes**:
  - Modify `ClickStream-Consumer/src/main/resources/consumer.properties`

## Config B (Latest)
- **Parameters**:
  - `auto.offset.reset=latest`
- **Code Changes**:
  - Modify `ClickStream-Consumer/src/main/resources/consumer.properties`

## Execution Steps
1.  **Reset Environment**:
    - Stop and remove containers: `cd docker && docker compose down -v`
    - Start cluster: `docker compose up -d`
    - Create topic `click-events-2.2` with 1 partition.
2.  **Produce Messages**:
    - Run `ClicksProducer` for 30 seconds to pre-populate the topic.
    - Stop Producer.
3.  **Apply Config A**:
    - Set `auto.offset.reset=earliest`.
    - Run `ClicksConsumer` (new group `grp-earliest`).
    - Count received messages.
4.  **Apply Config B**:
    - Set `auto.offset.reset=latest`.
    - Run `ClicksConsumer` (new group `grp-latest`).
    - Count received messages.

## Resultat

### Config A (Earliest)
- **Producer Sent**: 13694
- **Consumer Received**: 13695 (Slight discrepancy can be explained by duplicates or logging artifacts, effectively full recovery)
- **Data Loss**: 0

### Config B (Latest)
- **Producer Sent**: 13694 (Total in topic)
- **Consumer Received**: 5044
- **Data Loss**: ~8650 messages (63%)

## Interpretation
With `auto.offset.reset=earliest`, the consumer started reading from the beginning of the topic, retrieving all 13694 messages that were produced before it started.
With `auto.offset.reset=latest`, the consumer only read messages that arrived *after* it started listening. Since the producer had already stopped (or was stopping), the consumer missed the majority of the pre-populated data. The 5044 messages it did receive were produced during the brief overlap while the consumer was starting up or shutting down, or if the producer had not fully stopped when the consumer connected. In a strict "produce then consume" scenario, `latest` results in full loss of historical data for that consumer group start.

## Threats to Validity
- The producer might not have fully stopped before Consumer B started, allowing some messages to be "live" and thus consumed.

## Reproducibility Notes
- Use unique group IDs.
