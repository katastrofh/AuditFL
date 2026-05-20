# Contract-backed BC-FL MVP notes

Backend: `mock`

Dataset: mnist_784 (n=70000), non-IID Dirichlet alpha=0.4, clients=50, rounds=12.

Plain FL final test accuracy: 0.8992.

Contract-backed BC-FL final test accuracy: 0.8980.

Accuracy gap: -0.0012.

Mean included updates per round: 43.08.

Stored artifacts: puts=530, gets=517, injected/missing get failures=0.

Transactions: 1109; total gas used / mock gas estimate: 107052000.
