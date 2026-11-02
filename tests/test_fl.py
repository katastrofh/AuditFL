import numpy as np
import pytest

from bcfl_contract.fl import aggregate, train_local, validate_update


def test_aggregation_is_weighted_by_sample_count():
    updates = [
        {"W": np.array([[2.0, 6.0]]), "b": np.array([0.0, 4.0]), "n": 1},
        {"W": np.array([[6.0, 2.0]]), "b": np.array([4.0, 0.0]), "n": 3},
        {"W": np.array([[99.0, 99.0]]), "b": np.array([99.0, 99.0]), "n": 0},
    ]
    result = aggregate(updates)
    np.testing.assert_allclose(result["W"], [[5.0, 3.0]])
    np.testing.assert_allclose(result["b"], [3.0, 1.0])


def test_aggregation_rejects_empty_updates():
    with pytest.raises(ValueError, match="no valid updates"):
        aggregate([])


def test_training_does_not_mutate_global_model():
    model = {"W": np.zeros((1, 2)), "b": np.zeros(2)}
    update = train_local(model, np.array([[1.0], [-1.0]]), np.array([0, 1]), epochs=1, lr=0.1)
    np.testing.assert_array_equal(model["W"], [[0.0, 0.0]])
    np.testing.assert_array_equal(model["b"], [0.0, 0.0])
    np.testing.assert_allclose(update["W"], [[0.05, -0.05]])
    assert update["n"] == 2
    assert validate_update(update, expected_shape=(1, 2), n_classes=2)
    assert not validate_update(update, expected_shape=(2, 2), n_classes=2)
    assert not validate_update({}, expected_shape=(1, 2), n_classes=2)
