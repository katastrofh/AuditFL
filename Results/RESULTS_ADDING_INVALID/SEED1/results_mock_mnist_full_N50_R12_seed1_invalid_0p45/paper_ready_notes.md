# Contract-backed BC-FL MVP notes

Backend: `mock`

Dataset: mnist_784 (n=70000), non-IID Dirichlet alpha=0.4, clients=50, rounds=12.

Plain FL final test accuracy: 0.8990.

Contract-backed BC-FL final test accuracy: 0.8957.

Accuracy gap: -0.0033.

Mean included updates per round: 28.33.

Stored artifacts: puts=613, gets=600, injected/missing get failures=0.

Transactions: 1275; total gas used / mock gas estimate: 120969000.
