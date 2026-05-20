# Contract-backed BC-FL MVP notes

Backend: `mock`

Dataset: mnist_784 (n=70000), non-IID Dirichlet alpha=0.4, clients=50, rounds=12.

Plain FL final test accuracy: 0.8990.

Contract-backed BC-FL final test accuracy: 0.8988.

Accuracy gap: -0.0002.

Mean included updates per round: 41.17.

Stored artifacts: puts=507, gets=494, injected/missing get failures=0.

Transactions: 1063; total gas used / mock gas estimate: 102475000.
