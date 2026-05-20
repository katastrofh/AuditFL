# AuditFL Anonymous Artifact

This repository contains the anonymous review artifact for **AuditFL**, a contract-backed clearing layer for auditable federated learning (FL). AuditFL separates the FL learning path from the coordination path: model training and aggregation run off chain, while the ledger records ticket reservations, update identifiers, round finalization, refunds, rewards, claims, and other economic state.

This artifact supports the paper's implementation and evaluation claims. It is intended for reproducibility and review, not for production deployment.

## What this artifact demonstrates

The artifact validates AuditFL as a **control-plane system**:

- Clients reserve update tickets with deposits.
- Clients train locally and place update artifacts in an off-chain content-addressed artifact store.
- Clients publish only update identifiers on chain.
- The Task Coordinator retrieves available updates, filters invalid artifacts, aggregates valid updates, writes the next global artifact, and finalizes the round.
- The contract records listings, tickets, reward pools, update identifiers, global identifiers, refunds, rewards, claims, and entitlements.
- Model tensors stay outside the contract execution path.
- The Anvil/EVM backend reports transaction counts and EVM gas usage.
- The deterministic state-machine backend supports controlled dropout, invalid-update, and artifact-unavailability stress tests.

The evaluation treats AuditFL as a clearing/control-plane layer, not as a new FL optimizer.

## Scope

This is a research artifact for double-blind review. It is **not**:

- an audited production smart-contract system,
- a public mainnet or testnet deployment,
- a complete staking/slashing protocol,
- a privacy-preserving FL stack,
- a Byzantine-robust FL optimizer,
- a wide-area storage system,
- or an IPFS deployment.

AuditFL assumes a reliable distributed off-chain artifact layer. The evaluated artifact uses a local SHA-256 content-addressed artifact store. Systems such as IPFS are compatible deployment substrates, but the reported experiments do not run IPFS.

## Execution backends

The artifact contains two execution backends.

1. **State-machine backend**

   A deterministic Python implementation of the ticket, refund, scoring, and round-finalization rules. It is used for fast debugging and controlled failure-stress sweeps.

2. **Anvil/EVM backend**

   A Solidity `BCFLCoordinator` contract deployed on a local Ethereum-compatible Anvil chain. It is used to collect transaction receipts and EVM gas measurements.

Both backends use the same Python client and Task Coordinator logic and the same local SHA-256 content-addressed artifact store.

## Paper experiment summary

The paper evaluates AuditFL on full MNIST loaded through OpenML.

Main clean-scaling configuration:

| Item | Value |
|---|---:|
| Dataset | Full MNIST via OpenML |
| Examples | 70,000 |
| Rounds | 12 |
| Client counts | 1, 2, 5, 10, 15, 20, 30, 40, 50, 75, 100, 150, 200 |
| Split | Non-IID Dirichlet, alpha = 0.4 for N > 1 |
| Baseline | Plain FL with the same model, split, local training rule, and aggregation rule |
| Contract backend | Solidity `BCFLCoordinator` on local Anvil |
| Artifact store | Local SHA-256 content-addressed store |

At N = 200, the contract-backed run reports:

| Metric | Value |
|---|---:|
| Transactions, including deployment | 5,026 |
| Off-chain artifacts | 2,413 |
| Off-chain artifact bytes | 144.9 MiB |
| EVM gas | 829.7M |
| Dominant calls | `reserveTicket`, `publishUpdate` |
| Plain FL / AuditFL accuracy gap | 0 in clean runs |

Controlled failure-stress configuration:

| Item | Value |
|---|---:|
| Dataset | Full MNIST |
| Clients | 50 |
| Rounds | 12 |
| Seeds | 3 |
| Failure rates | 0% to 50% |
| Failure types | dropout, invalid update, artifact unavailability |
| Backend | deterministic state-machine backend |

At 50% injected failure, rounds still finalize and the final-accuracy gap remains below 0.14 percentage points in the reported stress runs.

## Repository layout

```text
contracts/BCFLCoordinator.sol      Solidity clearing-layer contract
bcfl_contract/store.py             SHA-256 content-addressed artifact store
bcfl_contract/fl.py                Dataset loading, non-IID split, local training, aggregation
bcfl_contract/mock_chain.py        Deterministic Python state-machine backend
bcfl_contract/evm_chain.py         Anvil/EVM Solidity backend
bcfl_contract/experiment.py        End-to-end experiment runner
scripts/run_contract_mvp.py        Main Plain FL vs AuditFL runner
scripts/run_failure_sweep.py       Controlled failure-stress sweeps
scripts/plot_results.py            Plotting and gas-summary utilities
requirements.txt                   Core Python dependencies
requirements-evm.txt               EVM/web3/Solidity dependencies
```

Some internal code names may use older implementation terms. In the paper and this README, the FL-side aggregator role is called the **Task Coordinator**.

## Environment

The artifact was tested on a recent Linux environment with Python 3 and Foundry/Anvil. Other recent Linux distributions should also work.

Create and activate a Python environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
```

For Anvil/EVM experiments, also install:

```bash
python3 -m pip install -r requirements-evm.txt
```

Install Foundry/Anvil if needed:

```bash
curl -L https://foundry.paradigm.xyz | bash
source ~/.bashrc
foundryup
anvil --version
```

## Quick smoke test: state-machine backend

This checks that the Python backend, dataset pipeline, local artifact store, and experiment runner work.

```bash
source .venv/bin/activate
python3 scripts/run_contract_mvp.py --quick --out results_mock_quick
```

Expected outputs include CSV summaries and run notes, for example:

```text
results_mock_quick/plain_fl_rounds.csv
results_mock_quick/bcfl_mock_rounds.csv
results_mock_quick/contract_mock_receipts.csv
results_mock_quick/contract_mvp_summary.csv
results_mock_quick/paper_ready_notes.md
```

## Quick smoke test: Anvil/EVM backend

Start Anvil in one terminal:

```bash
anvil --host 127.0.0.1 --port 8545 --accounts 20 --silent
```

In a second terminal:

```bash
cd <repo-root>
source .venv/bin/activate
python3 -m pip install -r requirements.txt -r requirements-evm.txt
python3 scripts/run_contract_mvp.py --backend anvil --quick --out results_anvil_quick
```

The first Anvil run may download Solidity compiler 0.8.24 through `py-solc-x`.

## Controlled failure sweeps

The deterministic state-machine backend is used for controlled stress tests because these tests concern ticket inclusion, update validity, and artifact availability rather than EVM execution cost.

```bash
source .venv/bin/activate
python3 scripts/run_failure_sweep.py --out results_failure_sweep
python3 scripts/plot_results.py results_failure_sweep
```

The sweep output contains CSV summaries and plots under the output directory.

## Full MNIST run

Use OpenML MNIST with all 70,000 examples by setting `--max-samples 0` if supported by the runner.

Example Anvil command for a single full-MNIST run:

```bash
anvil --host 127.0.0.1 --port 8545 --accounts 250 --silent
```

In another terminal:

```bash
source .venv/bin/activate
python3 scripts/run_contract_mvp.py \
  --backend anvil \
  --dataset mnist \
  --max-samples 0 \
  --rounds 12 \
  --out results_anvil_mnist_full_12r
```

For large client counts, start Anvil with enough unlocked accounts for the Task Coordinator and all clients. For example, use at least N + 1 accounts.

Generate summaries and plots:

```bash
python3 scripts/plot_results.py results_anvil_mnist_full_12r
```

## Paper figures

The paper figures are generated from the paper-result CSVs and plotting scripts.

Typical usage:

```bash
source .venv/bin/activate
python3 scripts/plot_results.py <results-directory>
```

The plotting script produces control-plane, artifact-scaling, gas-breakdown, and failure-stress plots when the required CSV files are present.

The paper reports:

- control-plane transaction scaling,
- EVM gas scaling and gas breakdown,
- artifact count and artifact-byte scaling,
- identifier bytes versus artifact bytes,
- artifact bytes per client-round,
- and controlled failure-stress behavior.

## Reproducing the paper claims

The paper uses two classes of runs:

1. **Clean scaling runs**

   These use the Anvil/EVM backend and measure transaction receipts, gas usage, artifact counts, and clean Plain FL versus AuditFL learning behavior.

2. **Failure-stress runs**

   These use the deterministic state-machine backend and inject dropout, invalid updates, and artifact unavailability.

The clean setting is expected to produce the same learning trajectory as Plain FL because AuditFL changes only coordination, publication, finalization, and settlement. It does not change the model, local training rule, aggregation rule, or data split.

## Artifact-store note

The evaluated artifact store is local and content-addressed:

- artifacts are addressed by SHA-256-derived identifiers,
- fetched bytes are rehashed before use,
- tensors are never stored on chain,
- and the chain records only identifiers and economic state.

The artifact store is not a contribution of this repository. It is a local implementation of the off-chain artifact interface assumed by AuditFL.

## Troubleshooting

### `anvil: command not found`

Install Foundry:

```bash
curl -L https://foundry.paradigm.xyz | bash
source ~/.bashrc
foundryup
```

### Not enough unlocked Anvil accounts

Restart Anvil with more accounts:

```bash
anvil --host 127.0.0.1 --port 8545 --accounts 250 --silent
```

For a run with N clients, use at least N + 1 accounts.

### Solidity compilation downloads compiler on first run

The Anvil backend may use `py-solc-x` to install Solidity compiler 0.8.24 on the first run. This requires internet access once.

### `Stack too deep` during Solidity compilation

The EVM backend should compile with optimizer and `viaIR: true`. Check the compiler settings in `bcfl_contract/evm_chain.py` if this error appears.

Expected compiler settings include:

```python
"optimizer": {"enabled": True, "runs": 200},
"viaIR": True,
```

### `ModuleNotFoundError`

Activate the virtual environment and reinstall dependencies:

```bash
source .venv/bin/activate
python3 -m pip install -r requirements.txt -r requirements-evm.txt
```

### OpenML dataset download fails

Check internet access and retry. For a quick offline sanity check, run the quick state-machine smoke test if it uses a local or built-in dataset path.


