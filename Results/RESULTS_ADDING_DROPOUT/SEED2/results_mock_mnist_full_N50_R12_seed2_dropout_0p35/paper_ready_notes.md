# Contract-backed BC-FL MVP notes

Backend: `mock`

Dataset: mnist_784 (n=70000), non-IID Dirichlet alpha=0.4, clients=50, rounds=12.

Plain FL final test accuracy: 0.8992.

Contract-backed BC-FL final test accuracy: 0.8994.

Accuracy gap: 0.0002.

Mean included updates per round: 33.25.

Stored artifacts: puts=412, gets=399, injected/missing get failures=0.

Transactions: 873; total gas used / mock gas estimate: 83570000.
