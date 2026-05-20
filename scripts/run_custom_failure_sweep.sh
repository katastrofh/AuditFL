#!/usr/bin/env bash
set -u

cd bcfl_contract_mvp

source .venv/bin/activate

mkdir -p failure_logs_full_mnist_custom

SEEDS=(1 2 3)
RATES=(0.00 0.10 0.15 0.20 0.25 0.30 0.35 0.40 0.45 0.50)

CLIENTS=50
ROUNDS=12
MAX_SAMPLES=0
DATASET="mnist"
BACKEND="mock"

echo "============================================================"
echo "AuditFL custom failure sweep"
echo "Dataset: full MNIST via --max-samples ${MAX_SAMPLES}"
echo "Clients: ${CLIENTS}"
echo "Rounds: ${ROUNDS}"
echo "Seeds: ${SEEDS[*]}"
echo "Rates: ${RATES[*]}"
echo "Backend: ${BACKEND}"
echo "============================================================"

for SEED in "${SEEDS[@]}"; do
  for RATE in "${RATES[@]}"; do
    RATE_LABEL="${RATE/./p}"

    echo "============================================================"
    echo "Seed=${SEED}, storage failure rate=${RATE}"
    echo "============================================================"

    OUT_DIR="results_mock_mnist_full_N${CLIENTS}_R${ROUNDS}_seed${SEED}_storage_${RATE_LABEL}"

    if [ -f "${OUT_DIR}/contract_mvp_summary.csv" ]; then
      echo "Skipping existing ${OUT_DIR}"
    else
      python3 scripts/run_contract_mvp.py \
        --backend "${BACKEND}" \
        --dataset "${DATASET}" \
        --max-samples "${MAX_SAMPLES}" \
        --clients "${CLIENTS}" \
        --rounds "${ROUNDS}" \
        --seed "${SEED}" \
        --storage-fail-rate "${RATE}" \
        --out "${OUT_DIR}" \
        2>&1 | tee "failure_logs_full_mnist_custom/seed${SEED}_storage_${RATE_LABEL}.log"
    fi

    echo "============================================================"
    echo "Seed=${SEED}, dropout rate=${RATE}"
    echo "============================================================"

    OUT_DIR="results_mock_mnist_full_N${CLIENTS}_R${ROUNDS}_seed${SEED}_dropout_${RATE_LABEL}"

    if [ -f "${OUT_DIR}/contract_mvp_summary.csv" ]; then
      echo "Skipping existing ${OUT_DIR}"
    else
      python3 scripts/run_contract_mvp.py \
        --backend "${BACKEND}" \
        --dataset "${DATASET}" \
        --max-samples "${MAX_SAMPLES}" \
        --clients "${CLIENTS}" \
        --rounds "${ROUNDS}" \
        --seed "${SEED}" \
        --dropout-rate "${RATE}" \
        --out "${OUT_DIR}" \
        2>&1 | tee "failure_logs_full_mnist_custom/seed${SEED}_dropout_${RATE_LABEL}.log"
    fi

    echo "============================================================"
    echo "Seed=${SEED}, invalid update rate=${RATE}"
    echo "============================================================"

    OUT_DIR="results_mock_mnist_full_N${CLIENTS}_R${ROUNDS}_seed${SEED}_invalid_${RATE_LABEL}"

    if [ -f "${OUT_DIR}/contract_mvp_summary.csv" ]; then
      echo "Skipping existing ${OUT_DIR}"
    else
      python3 scripts/run_contract_mvp.py \
        --backend "${BACKEND}" \
        --dataset "${DATASET}" \
        --max-samples "${MAX_SAMPLES}" \
        --clients "${CLIENTS}" \
        --rounds "${ROUNDS}" \
        --seed "${SEED}" \
        --invalid-rate "${RATE}" \
        --out "${OUT_DIR}" \
        2>&1 | tee "failure_logs_full_mnist_custom/seed${SEED}_invalid_${RATE_LABEL}.log"
    fi
  done
done

echo "============================================================"
echo "Failure sweep finished."
echo "============================================================"
