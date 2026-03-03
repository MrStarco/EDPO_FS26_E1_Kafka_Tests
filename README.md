# Kafka Producer Experiment Suite

This branch contains a Python-based Kafka experiment setup focused on producer behavior under different configuration and load conditions.

The implemented experiment families are:

1. Batch size impact on throughput and latency
2. Acknowledgment level impact (`acks=0`, `acks=1`, `acks=all`)
3. Partition scaling impact
4. Producer scaling impact (multiple concurrent producers)

The scripts generate numeric metrics (`results.csv`) and plot outputs for reporting.

## Repository Structure

- `scripts/config.py`: central test parameters (bootstrap server, message size/count, batch/acks/producer options)
- `scripts/experiment_runner.py`: executes all experiment combinations and writes `results.csv`
- `scripts/producer_worker.py`: producer workload and per-message latency measurement
- `scripts/topic_manager.py`: topic recreation with configurable partition count
- `scripts/experiment_monitor.py`: CPU and memory sampling via `psutil`
- `scripts/plots.py`: generates figure files from `results.csv`
- `plots/`: exported plots
- `EDPO_FS26_E1.pdf`: assignment sheet reference
- `review.md`: summary notes of results

## Testbed Setup

### Kafka

The scripts assume a reachable Kafka broker at:

- `localhost:9092`

This is configured in `scripts/config.py` (`KAFKA_BOOTSTRAP = "localhost:9092"`).

Make sure Kafka is running before executing the experiments.

### Python environment

Use Python 3.10+ and install the required packages:

```bash
pip install kafka-python psutil pandas matplotlib seaborn
```

## Running the Experiments

Run the complete experiment matrix from the `scripts/` directory:

```bash
cd scripts
python experiment_runner.py
```

What this run does:

- recreates topics with partition counts from `PARTITION_OPTIONS = [1, 3, 6]`
- executes all combinations of:
  - `BATCH_SIZES = [0, 16384, 65536]`
  - `ACKS_OPTIONS = [0, 1, "all"]`
  - `PRODUCER_COUNTS = [1, 2, 4]`
- writes one row per experiment case to `results.csv`

Collected metrics per run:

- throughput (`throughput(msg/sec)`)
- average producer-side latency (`avg_latency(sec)`)
- average CPU usage (`cpu(%)`)
- average memory usage (`memory(%)`)
- total run duration (`duration(sec)`)

## Generating Plots

After `results.csv` is created, generate figures with:

```bash
cd scripts
python plots.py
```

The plotting script produces:

- `fig_batch_throughput.png`
- `fig_batch_latency.png`
- `fig_acks_throughput.png`
- `fig_partition_scaling.png`
- `fig_producer_scaling.png`

## Reading Results

This branch already includes outputs in `plots/`, such as:

- `EffectBatchThroughput.png`
- `EffectBatchLatency.png`
- `ImpactAcknowledgementThroughput.png`
- `ThroughputwithPartition.png`
- `ProducerScaling.png`
- `ThroughputWithProducer.png`

## Expected Trends

In line with Kafka behavior, expected outcomes are:

- larger batch sizes can improve throughput but may increase latency
- `acks=0` is usually fastest and least durable
- higher `acks` levels improve durability with additional coordination cost
- more producers generally increase aggregate throughput until CPU/network becomes the bottleneck
- more partitions can improve parallelism, but gains depend on available hardware and broker count

## Notes

- Topic names are recreated per partition scenario (`experiment-p<partitions>`), so previous data may be overwritten for those topics.
- Single-run measurements are noisy; for reporting, run multiple repetitions and compare trends, not only single absolute values.
