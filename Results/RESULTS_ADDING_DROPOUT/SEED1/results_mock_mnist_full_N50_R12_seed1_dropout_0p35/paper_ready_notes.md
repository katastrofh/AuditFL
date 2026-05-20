# Contract-backed BC-FL MVP notes

Backend: `mock`

Dataset: mnist_784 (n=70000), non-IID Dirichlet alpha=0.4, clients=50, rounds=12.

Plain FL final test accuracy: 0.8990.

Contract-backed BC-FL final test accuracy: 0.8977.

Accuracy gap: -0.0013.

Mean included updates per round: 32.67.

Stored artifacts: puts=405, gets=392, injected/missing get failures=0.

Transactions: 859; total gas used / mock gas estimate: 82177000.
