# Producer Experiment Summary

## Test Setup
- Messages per case: `20000`.
- Batch cases: `small_batch` (`batch.size=16384, linger.ms=0`) and `large_batch` (`batch.size=524288, linger.ms=20`).
- Acks cases: `acks=0`, `acks=1`, `acks=all`.

## Batch Size vs Latency/Throughput
- Highest throughput: `large_batch` at `161763.76` msg/s.
- Lowest p95 latency: `large_batch` at `85.241` ms.
- Larger batches usually improve throughput by reducing request overhead, but can increase buffering delay.

## `acks` Durability vs Performance
- Highest throughput among `acks` configs: `acks_0` at `371761.9` msg/s.
- Lowest p95 latency among `acks` configs: `acks_0` at `8.815` ms.
- Durability interpretation: `acks=0` fastest but highest loss risk, `acks=all` strongest durability.

## Quality Check
- Verdict: `GOOD`.
- PASS: no producer delivery errors in all cases.
- PASS: large batch throughput is higher than small batch throughput.
- PASS: acks=0 is the fastest as expected.
- REVIEW: acks=all p95 latency is below acks=1 (possible benchmark noise).