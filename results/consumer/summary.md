# Consumer Experiment Summary

## Test Setup
- Lag test messages per case: `1500`.
- Lag cases: `delay_0ms` and `delay_10ms`.
- Poll cases: `low_poll_interval` (`6000ms`) and `high_poll_interval` (`15000ms`) with `7000ms` processing delay.
- Offset reset cases: `earliest` and `latest` for new consumer groups.

## Consumer Lag Under Processing Delay
- Highest lag observed in `delay_10ms` with `1431` messages.
- Lowest throughput observed in `delay_10ms` with `70.83` msg/s.

## max.poll.interval.ms Behavior
- At least one case failed or stalled when processing was slower than poll expectations.

## Offset Reset Misconfiguration Risk
- `earliest` consumed old messages missed: `1`.
- `latest` consumed old messages missed: `100`.
- `latest` can skip historical data for new consumer groups, which looks like data loss from the app point of view.

## Quality Check
- Verdict: `GOOD`.
- PASS: added processing delay increased consumer lag.
- PASS: added processing delay reduced consumer throughput.
- PASS: low poll interval case exceeded max poll interval.
- PASS: high poll interval case completed.
- PASS: latest skipped more historical records than earliest.
- REVIEW: earliest missed historical records (possible timing/rebalance noise).