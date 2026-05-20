# Contract-backed BC-FL MVP notes

Backend: `mock`

Dataset: mnist_784 (n=70000), non-IID Dirichlet alpha=0.4, clients=50, rounds=12.

Plain FL final test accuracy: 0.8990.

Contract-backed BC-FL final test accuracy: 0.8985.

Accuracy gap: -0.0005.

Mean included updates per round: 30.17.

Stored artifacts: puts=375, gets=362, injected/missing get failures=0.

Transactions: 799; total gas used / mock gas estimate: 76207000.
