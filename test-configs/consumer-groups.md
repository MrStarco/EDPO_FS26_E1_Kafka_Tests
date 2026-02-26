# Experiment 2.3: Multiple Consumers & Consumer Groups

## Objective
Test multiple consumers consuming from the same topic. Observe how Kafka distributes messages among consumers within the same group vs. different groups.

## Config A (Same Group)
- **Parameters**:
  - 2 Consumers
  - `group.id=grp-shared`
  - Topic with 2 partitions
- **Code Changes**:
  - Modify `ClickStream-Consumer/src/main/resources/consumer.properties`

## Config B (Different Groups)
- **Parameters**:
  - 2 Consumers
  - `group.id=grp-A` and `group.id=grp-B`
  - Topic with 2 partitions
- **Code Changes**:
  - Modify `ClickStream-Consumer/src/main/resources/consumer.properties`

## Execution Steps
1.  **Reset Environment**:
    - Stop and remove containers: `cd docker && docker compose down -v`
    - Start cluster: `docker compose up -d`
    - Create unique topic per config (`click-events-2.3-A`, `click-events-2.3-B`) with 2 partitions.
2.  **Apply Config A**:
    - Start Consumer 1 (`grp-shared`).
    - Start Consumer 2 (`grp-shared`).
    - Run `ClicksProducer`.
    - Warm-up 30s, then measure for 180s.
    - Collect `docker stats` at +60s and +180s.
3.  **Apply Config B**:
    - Start Consumer 1 (`grp-A`).
    - Start Consumer 2 (`grp-B`).
    - Run `ClicksProducer`.
    - Warm-up 30s, then measure for 180s.
    - Collect `docker stats` at +60s and +180s.

## Resultat

### Config A (Same Group)
- **Producer Sent**: 294109
- **Consumer A1 Received**: 204203
- **Consumer A2 Received**: 524005
- **Total Received (A1 + A2)**: 728208
- **Distribution (A1/A2)**: 28.04% / 71.96%

### Config B (Different Groups)
- **Producer Sent**: 260483
- **Consumer B1 Received**: 744783
- **Consumer B2 Received**: 562673
- **Total Received (B1 + B2)**: 1307456
- **Distribution (B1/B2)**: 56.96% / 43.04%

## Interpretation
In Config A (Same Group), the 2 partitions were assigned to the 2 consumers (1 partition each). The workload was shared, and each message was processed exactly once by the group.
In Config B (Different Groups), each consumer group is independent. Kafka treats them as separate subscribers. Every message sent to the topic was delivered to Group A (Consumer B1) AND Group B (Consumer B2). This is the pub-sub model where multiple applications can consume the same data stream independently.

## Threats to Validity
- Counts might be slightly off due to startup/shutdown timing.

## Reproducibility Notes
- Use unique group IDs.
