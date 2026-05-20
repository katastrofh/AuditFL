# Contract-backed BC-FL MVP notes

Backend: `mock`

Dataset: mnist_784 (n=70000), non-IID Dirichlet alpha=0.4, clients=50, rounds=12.

Plain FL final test accuracy: 0.8992.

Contract-backed BC-FL final test accuracy: 0.8990.

Accuracy gap: -0.0002.

Mean included updates per round: 31.00.

Stored artifacts: puts=385, gets=372, injected/missing get failures=0.

Transactions: 819; total gas used / mock gas estimate: 78197000.
