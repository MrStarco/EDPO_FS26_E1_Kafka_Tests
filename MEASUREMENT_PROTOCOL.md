# Measurement Protocol

All critical reruns must follow this exact protocol.

## Scope

This protocol is mandatory for:
- `run_test_1.2_A.sh`
- `run_test_2.3.sh`
- `run_test_2.1_A.sh`

## Standard Sequence

1. Reset environment with `./reset_env.sh`.
2. Create a unique topic for the test/config.
3. Apply producer and consumer properties for the active config.
4. Start consumer process.
5. Start producer process.
6. Warm-up phase: run for 30 seconds (discard this period).
7. Measurement phase: run for 180 seconds.
8. Collect `docker stats --no-stream` at:
   - +60s into measurement (`stats_<test>_60s.txt`)
   - +180s into measurement (`stats_<test>_180s.txt`)
9. Stop producer.
10. Wait 10 seconds for consumer drain.
11. Stop consumer.

## Fixed Timings

- Warm-up: 30s
- Measurement: 180s
- Total active run after startup: 210s
- Drain after producer stop: 10s

## Evidence Rules

- Use measured values only.
- No inferred, assumed, or estimated values in `## Resultat`.
- If a run fails protocol checks (missing stats file, broken lag query, topic collision), rerun.

## Lag Measurement Rule

For lag sampling inside container use:

`docker exec docker-kafka1-1 kafka-consumer-groups --bootstrap-server kafka1:29092 --describe --group <group-id>`

Do not use `localhost:9092` from inside container commands.

## Minimal Acceptance Checks Per Run

- Both stats files exist.
- Producer sent count is taken from run log.
- Consumer received count is taken from run log.
- No placeholders in report output.
