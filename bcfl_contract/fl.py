from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple
import numpy as np
from sklearn.datasets import load_digits, fetch_openml
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler


@dataclass
class DatasetSplits:
    client_data: List[Tuple[np.ndarray, np.ndarray]]
    val: Tuple[np.ndarray, np.ndarray]
    test: Tuple[np.ndarray, np.ndarray]
    n_features: int
    n_classes: int
    name: str
    n_total: int


def _fetch_openml_compat(*args, **kwargs):
    """Compatibility wrapper for sklearn versions with/without the parser kwarg."""
    try:
        return fetch_openml(*args, **kwargs, as_frame=False, parser="auto")
    except TypeError:
        return fetch_openml(*args, **kwargs, as_frame=False)


def _load_raw_dataset(dataset: str) -> tuple[np.ndarray, np.ndarray, str]:
    key = dataset.lower().replace("-", "_")
    if key in {"digits", "sklearn_digits"}:
        d = load_digits()
        X = d.data.astype(np.float64) / 16.0
        y = d.target.astype(np.int64)
        return X, y, "sklearn_digits"
    if key in {"mnist", "mnist_784"}:
        d = _fetch_openml_compat("mnist_784", version=1)
        X = d.data.astype(np.float64) / 255.0
        y = d.target.astype(np.int64)
        return X, y, "mnist_784"
    if key in {"fashion", "fashion_mnist", "fashion-mnist"}:
        # OpenML dataset id 40996 is Fashion-MNIST. This requires internet on first run.
        d = _fetch_openml_compat(data_id=40996)
        X = d.data.astype(np.float64) / 255.0
        y = d.target.astype(np.int64)
        return X, y, "fashion_mnist"
    raise ValueError(f"unknown dataset '{dataset}'. Use digits, mnist, or fashion_mnist")


def _stratified_cap(X: np.ndarray, y: np.ndarray, max_samples: int | None, seed: int) -> tuple[np.ndarray, np.ndarray]:
    if max_samples is None or max_samples <= 0 or max_samples >= len(y):
        return X, y
    # Keep label proportions. If the requested cap is too small for all classes, sklearn will raise;
    # in that case the caller should use a larger cap.
    X_keep, _, y_keep, _ = train_test_split(
        X, y, train_size=max_samples, random_state=seed, stratify=y
    )
    return X_keep, y_keep


def load_dataset_noniid(
    num_clients: int,
    alpha: float = 0.4,
    seed: int = 7,
    dataset: str = "digits",
    max_samples: int | None = None,
) -> DatasetSplits:
    rng = np.random.default_rng(seed)
    X, y, name = _load_raw_dataset(dataset)
    X, y = _stratified_cap(X, y, max_samples, seed)

    X_train_full, X_test, y_train_full, y_test = train_test_split(
        X, y, test_size=0.25, random_state=seed, stratify=y
    )
    X_train, X_val, y_train, y_val = train_test_split(
        X_train_full, y_train_full, test_size=0.20, random_state=seed + 1, stratify=y_train_full
    )
    scaler = StandardScaler().fit(X_train)
    X_train = scaler.transform(X_train)
    X_val = scaler.transform(X_val)
    X_test = scaler.transform(X_test)
    n_classes = int(y.max() + 1)

    client_indices = [[] for _ in range(num_clients)]
    for c in range(n_classes):
        idx = np.where(y_train == c)[0]
        rng.shuffle(idx)
        probs = rng.dirichlet(np.full(num_clients, alpha))
        cuts = (np.cumsum(probs)[:-1] * len(idx)).astype(int)
        parts = np.split(idx, cuts)
        for i, part in enumerate(parts):
            client_indices[i].extend(part.tolist())
    client_data = []
    all_indices = np.arange(len(y_train))
    for inds in client_indices:
        if len(inds) == 0:
            inds = rng.choice(all_indices, size=1, replace=False).tolist()
        arr = np.array(inds, dtype=int)
        rng.shuffle(arr)
        client_data.append((X_train[arr], y_train[arr]))
    return DatasetSplits(
        client_data=client_data,
        val=(X_val, y_val),
        test=(X_test, y_test),
        n_features=X_train.shape[1],
        n_classes=n_classes,
        name=name,
        n_total=len(y),
    )


def load_digits_noniid(num_clients: int, alpha: float = 0.4, seed: int = 7) -> DatasetSplits:
    return load_dataset_noniid(num_clients, alpha=alpha, seed=seed, dataset="digits")


def init_model(n_features: int, n_classes: int, seed: int = 0) -> dict:
    rng = np.random.default_rng(seed)
    return {"W": rng.normal(0, 0.01, size=(n_features, n_classes)), "b": np.zeros(n_classes)}


def softmax(z: np.ndarray) -> np.ndarray:
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def evaluate(model: dict, X: np.ndarray, y: np.ndarray) -> float:
    logits = X @ model["W"] + model["b"]
    pred = logits.argmax(axis=1)
    return float((pred == y).mean())


def train_local(model: dict, X: np.ndarray, y: np.ndarray, *, epochs: int, lr: float, l2: float = 1e-4) -> dict:
    W = model["W"].copy()
    b = model["b"].copy()
    n = len(y)
    if n == 0:
        return {"W": W, "b": b, "n": 0}
    C = W.shape[1]
    Y = np.eye(C)[y]
    for _ in range(epochs):
        probs = softmax(X @ W + b)
        grad_logits = (probs - Y) / n
        grad_W = X.T @ grad_logits + l2 * W
        grad_b = grad_logits.sum(axis=0)
        W -= lr * grad_W
        b -= lr * grad_b
    return {"W": W, "b": b, "n": n}


def aggregate(updates: list[dict]) -> dict:
    valid = [u for u in updates if "W" in u and "b" in u and "n" in u and u["n"] > 0]
    if not valid:
        raise ValueError("no valid updates to aggregate")
    total = sum(int(u["n"]) for u in valid)
    W = sum(u["W"] * (int(u["n"]) / total) for u in valid)
    b = sum(u["b"] * (int(u["n"]) / total) for u in valid)
    return {"W": W, "b": b}


def validate_update(update: dict, expected_shape: tuple[int, int], n_classes: int) -> bool:
    try:
        return update["W"].shape == expected_shape and update["b"].shape == (n_classes,) and int(update["n"]) >= 0
    except Exception:
        return False
