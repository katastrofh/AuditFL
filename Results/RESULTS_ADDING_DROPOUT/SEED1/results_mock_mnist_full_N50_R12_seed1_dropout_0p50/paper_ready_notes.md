# Contract-backed BC-FL MVP notes

Backend: `mock`

Dataset: mnist_784 (n=70000), non-IID Dirichlet alpha=0.4, clients=50, rounds=12.

Plain FL final test accuracy: 0.8990.

Contract-backed BC-FL final test accuracy: 0.8976.

Accuracy gap: -0.0014.

Mean included updates per round: 26.33.

Stored artifacts: puts=329, gets=316, injected/missing get failures=0.

Transactions: 707; total gas used / mock gas estimate: 67053000.
