import pytest

from bcfl_contract.mock_chain import MockCoordinator


@pytest.fixture
def chain():
    coordinator = MockCoordinator(["coordinator", "alice", "bob", "carol"], deposit_wei=3)
    coordinator.create_listing("coordinator", "model", "initial-cid", "rules-hash")
    return coordinator


def test_settlement_refunds_rewards_and_claims(chain):
    chain.fund_round("coordinator", "model", amount_wei=11)
    tickets = []
    for client in ["alice", "bob", "carol"]:
        ticket_id, _ = chain.reserve_ticket(client, "model", 0, deposit_wei=3)
        chain.publish_update(client, "model", 0, ticket_id, f"{client}-cid", "metrics")
        tickets.append(ticket_id)

    # All retrievable updates are refunded; only included updates earn rewards.
    receipt = chain.finalize_round(
        "coordinator", "model", 0, "next-cid",
        included=tickets[:2], refunds=tickets, scores_hash="scores",
    )

    assert receipt.event == "RoundFinalized"
    assert receipt.data["included"] == 2
    assert receipt.data["refunds"] == 3
    assert chain.current_round("model") == 1
    assert chain.global_cid("model") == "next-cid"
    assert chain.models["model"]["pool_wei"] == 1
    assert all(chain.tickets[("model", ticket)].settled for ticket in tickets)
    for client, expected_amount in [("alice", 8), ("bob", 8), ("carol", 3)]:
        claim = chain.claim(client, "model")
        assert claim.event == "Claimed"
        assert claim.data["amount_wei"] == expected_amount
        with pytest.raises(ValueError, match="nothing to claim"):
            chain.claim(client, "model")

    assert all(receipt.status == 1 for receipt in chain.receipts)
    assert len({receipt.tx for receipt in chain.receipts}) == len(chain.receipts)
    with pytest.raises(ValueError, match="wrong round"):
        chain.reserve_ticket("alice", "model", 0)
    chain.reserve_ticket("alice", "model", 1)


@pytest.mark.parametrize(
    ("round_index", "deposit", "message"),
    [(1, 3, "wrong round"), (0, 2, "bad deposit")],
)
def test_ticket_reservation_rejects_invalid_terms(chain, round_index, deposit, message):
    with pytest.raises(ValueError, match=message):
        chain.reserve_ticket("alice", "model", round_index, deposit_wei=deposit)
    assert chain.tickets == {}


def test_only_owner_can_publish_once(chain):
    ticket_id, _ = chain.reserve_ticket("alice", "model", 0)
    with pytest.raises(ValueError, match="not owner"):
        chain.publish_update("bob", "model", 0, ticket_id, "update-cid", "metrics")
    with pytest.raises(ValueError, match="wrong round"):
        chain.publish_update("alice", "model", 1, ticket_id, "update-cid", "metrics")
    assert not chain.tickets[("model", ticket_id)].revealed

    chain.publish_update("alice", "model", 0, ticket_id, "update-cid", "metrics")
    with pytest.raises(ValueError, match="already revealed"):
        chain.publish_update("alice", "model", 0, ticket_id, "other-cid", "metrics")
    assert chain.tickets[("model", ticket_id)].update_cid == "update-cid"


@pytest.mark.parametrize(
    ("sender", "round_index", "message"),
    [("alice", 0, "only lister"), ("coordinator", 1, "wrong round")],
)
def test_finalization_requires_lister_and_current_round(chain, sender, round_index, message):
    with pytest.raises(ValueError, match=message):
        chain.finalize_round(sender, "model", round_index, "next-cid", [], [], "scores")
    assert chain.current_round("model") == 0
    assert chain.global_cid("model") == "initial-cid"


@pytest.mark.parametrize("kind", ["included", "refund"])
def test_unpublished_ticket_cannot_be_settled(chain, kind):
    ticket_id, _ = chain.reserve_ticket("alice", "model", 0)
    included = [ticket_id] if kind == "included" else []
    refunds = [ticket_id] if kind == "refund" else []
    with pytest.raises(ValueError, match=f"bad {kind} ticket"):
        chain.finalize_round("coordinator", "model", 0, "next-cid", included, refunds, "scores")


def test_empty_round_preserves_funding(chain):
    chain.fund_round("coordinator", "model", amount_wei=11)
    chain.finalize_round("coordinator", "model", 0, "unchanged-cid", [], [], "scores")
    assert chain.current_round("model") == 1
    assert chain.models["model"]["pool_wei"] == 11
    with pytest.raises(ValueError, match="nothing to claim"):
        chain.claim("alice", "model")
