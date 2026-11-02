import hashlib

import pytest

from bcfl_contract.store import ArtifactUnavailable, ContentAddressedStore


def test_content_address_and_round_trip(tmp_path):
    store = ContentAddressedStore(tmp_path)
    payload = b"model weights"
    expected_cid = "sha256:" + hashlib.sha256(payload).hexdigest()

    assert store.put_bytes(payload) == expected_cid
    assert store.put_bytes(payload) == expected_cid
    assert store.get_bytes(expected_cid) == payload
    assert len(list(tmp_path.iterdir())) == 1
    assert store.put_count == 2
    assert store.get_count == 1
    assert store.get_failures == 0


def test_object_round_trip(tmp_path):
    store = ContentAddressedStore(tmp_path)
    update = {"weights": [1.0, 2.0], "samples": 3}

    assert store.get_obj(store.put_obj(update)) == update


@pytest.mark.parametrize("failure", ["missing", "corrupt", "injected"])
def test_unavailable_artifacts_are_rejected_and_counted(tmp_path, failure):
    store = ContentAddressedStore(tmp_path, seed=7)
    cid = store.put_bytes(b"original model")
    artifact_path = tmp_path / cid.replace(":", "_")
    if failure == "missing":
        artifact_path.unlink()
        message = "missing artifact"
    elif failure == "corrupt":
        artifact_path.write_bytes(b"changed model")
        message = "integrity check failed"
    else:
        store.fail_rate = 1.0
        message = "injected artifact get failure"

    with pytest.raises(ArtifactUnavailable, match=message):
        store.get_bytes(cid)

    assert store.get_count == 1
    assert store.get_failures == 1
