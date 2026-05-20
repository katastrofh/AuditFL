# Contract-backed BC-FL MVP notes

Backend: `mock`

Dataset: mnist_784 (n=70000), non-IID Dirichlet alpha=0.4, clients=50, rounds=12.

Plain FL final test accuracy: 0.8990.

Contract-backed BC-FL final test accuracy: 0.8984.

Accuracy gap: -0.0006.

Mean included updates per round: 44.58.

Stored artifacts: puts=548, gets=535, injected/missing get failures=0.

Transactions: 1145; total gas used / mock gas estimate: 110634000.
