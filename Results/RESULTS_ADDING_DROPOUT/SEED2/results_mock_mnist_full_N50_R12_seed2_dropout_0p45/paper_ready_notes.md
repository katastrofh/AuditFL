# Contract-backed BC-FL MVP notes

Backend: `mock`

Dataset: mnist_784 (n=70000), non-IID Dirichlet alpha=0.4, clients=50, rounds=12.

Plain FL final test accuracy: 0.8992.

Contract-backed BC-FL final test accuracy: 0.8995.

Accuracy gap: 0.0003.

Mean included updates per round: 28.83.

Stored artifacts: puts=359, gets=346, injected/missing get failures=0.

Transactions: 767; total gas used / mock gas estimate: 73023000.
