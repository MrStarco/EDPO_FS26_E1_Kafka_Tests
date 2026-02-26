# Fault Tolerance Experiment Summary

## Test Setup
- Test duration: `30` seconds.
- Warmup before broker kill: `6` seconds.
- Producer target rate: `300` msg/s.
- Topic configuration: 6 partitions, replication factor 3.

## Broker Failure and Leader Election
- Killed broker id: `3`.
- Impacted partitions: `2`.
- Leader failover time: `19.714` seconds.

## Producer/Consumer Impact
- Producer sent `9001` and delivered `9001` messages.
- Producer errors observed: `0`.
- Consumer processed `8049` messages with max gap `19.682` seconds.
- Producer p95 delivery latency: `19176.295` ms.

- Short spikes in latency and throughput dips are expected during leader election.

## Quality Check
- Verdict: `GOOD`.
- PASS: leader failover was observed after broker kill.
- PASS: producer delivered all sent messages with zero errors.
- PASS: consumer reported zero errors.
- PASS: failover completed within timeout window.