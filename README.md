# EDPO FS2026 - Exercise 1 (Kafka)

## Course and Group
- Course: Event-driven and Process-oriented Architectures (EDPO), FS2026, University of St.Gallen
- Group 4
  - Evan Martino
  - Marco Birchler
  - Roman Babukh

## Repository Purpose
This repository documents Kafka experiments for Exercise 1 (E1), covering:
- Producer experiments
- Consumer experiments
- Fault tolerance and reliability

The branch setup separates detailed implementation evidence from the final hand-in summary.

## Branch Setup
- `main`: Consolidated submission branch with overview and combined report
- `marco`: Java-based experiment branch (2-broker KRaft setup, manual runs, logs/stats, lower-level report)
- `roman`: Python-based experiment branch (3-broker ZooKeeper setup, automated suites, CSV/PNG outputs, lower-level report)
- `evan`: Producer-focused experiment branch with single-broker benchmark runs and review summary

## How To Navigate To Specific Results

### High-level report (submission view)
- Combined summary: `TEST_REPORT.md` on `main`
- Repository overview: `README.md` on `main`

### Marco branch evidence
- Main report: `TEST_REPORT.md`
- Experiment configs: `test-configs/`
- Measurement files: `Stats/`

### Roman branch evidence
- Consolidated interpretation: `results/review.md`
- Category summaries: `results/producer/summary.md`, `results/consumer/summary.md`, `results/fault_tolerance/summary.md`
- Raw metrics and plots: `results/**` (`.csv` and `.png`)

### Evan branch evidence
- Consolidated interpretation: `review.md`
- Plots and result artifacts: `plots/`

## Contribution Mapping
- Marco Birchler: Java-based experiments and measurements on `marco`
- Roman Babukh: Python-based experiment suite and result artifacts on `roman`
- Evan Martino: Producer-focused experiment runs and summary artifacts on `evan`

## Reproducibility Entry Points
- Start from `main/TEST_REPORT.md` for the combined interpretation
- Follow branch-specific evidence paths above for detailed values, scripts, and experiment setup
