# Contract-backed BC-FL MVP notes

Backend: `mock`

Dataset: mnist_784 (n=70000), non-IID Dirichlet alpha=0.4, clients=50, rounds=12.

Plain FL final test accuracy: 0.9010.

Contract-backed BC-FL final test accuracy: 0.9003.

Accuracy gap: -0.0007.

Mean included updates per round: 41.67.

Stored artifacts: puts=513, gets=500, injected/missing get failures=0.

Transactions: 1075; total gas used / mock gas estimate: 103669000.
