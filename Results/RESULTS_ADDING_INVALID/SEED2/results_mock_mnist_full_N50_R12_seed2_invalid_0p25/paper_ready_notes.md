# Contract-backed BC-FL MVP notes

Backend: `mock`

Dataset: mnist_784 (n=70000), non-IID Dirichlet alpha=0.4, clients=50, rounds=12.

Plain FL final test accuracy: 0.8992.

Contract-backed BC-FL final test accuracy: 0.8999.

Accuracy gap: 0.0007.

Mean included updates per round: 37.92.

Stored artifacts: puts=613, gets=600, injected/missing get failures=0.

Transactions: 1275; total gas used / mock gas estimate: 122119000.
