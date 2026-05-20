# Contract-backed BC-FL MVP notes

Backend: `mock`

Dataset: mnist_784 (n=70000), non-IID Dirichlet alpha=0.4, clients=50, rounds=12.

Plain FL final test accuracy: 0.9010.

Contract-backed BC-FL final test accuracy: 0.8993.

Accuracy gap: -0.0017.

Mean included updates per round: 36.67.

Stored artifacts: puts=453, gets=440, injected/missing get failures=0.

Transactions: 955; total gas used / mock gas estimate: 91729000.
