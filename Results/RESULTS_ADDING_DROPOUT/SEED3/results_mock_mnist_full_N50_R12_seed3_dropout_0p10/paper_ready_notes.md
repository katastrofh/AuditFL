# Contract-backed BC-FL MVP notes

Backend: `mock`

Dataset: mnist_784 (n=70000), non-IID Dirichlet alpha=0.4, clients=50, rounds=12.

Plain FL final test accuracy: 0.9010.

Contract-backed BC-FL final test accuracy: 0.9005.

Accuracy gap: -0.0005.

Mean included updates per round: 44.25.

Stored artifacts: puts=544, gets=531, injected/missing get failures=0.

Transactions: 1137; total gas used / mock gas estimate: 109838000.
