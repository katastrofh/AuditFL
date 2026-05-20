# Contract-backed BC-FL MVP notes

Backend: `mock`

Dataset: mnist_784 (n=70000), non-IID Dirichlet alpha=0.4, clients=50, rounds=12.

Plain FL final test accuracy: 0.8992.

Contract-backed BC-FL final test accuracy: 0.8983.

Accuracy gap: -0.0009.

Mean included updates per round: 37.42.

Stored artifacts: puts=462, gets=449, injected/missing get failures=0.

Transactions: 973; total gas used / mock gas estimate: 93520000.
