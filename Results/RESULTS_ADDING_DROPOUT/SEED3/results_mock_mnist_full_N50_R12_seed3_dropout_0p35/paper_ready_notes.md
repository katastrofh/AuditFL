# Contract-backed BC-FL MVP notes

Backend: `mock`

Dataset: mnist_784 (n=70000), non-IID Dirichlet alpha=0.4, clients=50, rounds=12.

Plain FL final test accuracy: 0.9010.

Contract-backed BC-FL final test accuracy: 0.8994.

Accuracy gap: -0.0016.

Mean included updates per round: 31.33.

Stored artifacts: puts=389, gets=376, injected/missing get failures=0.

Transactions: 827; total gas used / mock gas estimate: 78993000.
