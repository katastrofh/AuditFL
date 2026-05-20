// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title BCFLCoordinator
/// @notice Minimal on-chain control plane for blockchain-coordinated federated learning.
/// @dev This contract intentionally stores only metadata and content identifiers. Model tensors
///      remain in off-chain content-addressed storage.
contract BCFLCoordinator {
    struct Model {
        bool exists;
        address lister;
        string globalCID;
        bytes32 rulesHash;
        uint256 currentRound;
        uint256 depositWei;
        uint256 poolWei;
        uint256 nextTicketId;
    }

    struct Ticket {
        bool exists;
        address owner;
        bytes32 modelId;
        uint256 round;
        uint256 depositWei;
        bool revealed;
        bool settled;
        string updateCID;
        bytes32 metricsHash;
    }

    mapping(bytes32 => Model) public models;
    mapping(bytes32 => mapping(uint256 => Ticket)) public tickets;
    mapping(bytes32 => mapping(address => uint256)) public entitlements;

    event ListingCreated(bytes32 indexed modelId, address indexed lister, string initCID, bytes32 rulesHash, uint256 depositWei);
    event RoundFunded(bytes32 indexed modelId, address indexed funder, uint256 amountWei, uint256 poolWei);
    event TicketReserved(bytes32 indexed modelId, uint256 indexed round, uint256 indexed ticketId, address owner, uint256 depositWei);
    event UpdatePublished(bytes32 indexed modelId, uint256 indexed round, uint256 indexed ticketId, address owner, string updateCID, bytes32 metricsHash);
    event RoundFinalized(bytes32 indexed modelId, uint256 indexed round, string globalCID, uint256 includedCount, uint256 refundCount, bytes32 scoresHash);
    event Claimed(bytes32 indexed modelId, address indexed account, uint256 amountWei);

    modifier onlyLister(bytes32 modelId) {
        require(models[modelId].exists, "model missing");
        require(msg.sender == models[modelId].lister, "only lister");
        _;
    }

    function createListing(bytes32 modelId, string calldata initCID, bytes32 rulesHash, uint256 depositWei) external {
        require(!models[modelId].exists, "model exists");
        require(bytes(initCID).length > 0, "empty initCID");
        require(depositWei > 0, "zero deposit");
        models[modelId] = Model({
            exists: true,
            lister: msg.sender,
            globalCID: initCID,
            rulesHash: rulesHash,
            currentRound: 0,
            depositWei: depositWei,
            poolWei: 0,
            nextTicketId: 1
        });
        emit ListingCreated(modelId, msg.sender, initCID, rulesHash, depositWei);
    }

    function fundRound(bytes32 modelId) external payable {
        Model storage m = models[modelId];
        require(m.exists, "model missing");
        require(msg.value > 0, "zero funding");
        m.poolWei += msg.value;
        emit RoundFunded(modelId, msg.sender, msg.value, m.poolWei);
    }

    function reserveTicket(bytes32 modelId, uint256 round) external payable returns (uint256 ticketId) {
        Model storage m = models[modelId];
        require(m.exists, "model missing");
        require(round == m.currentRound, "wrong round");
        require(msg.value == m.depositWei, "bad deposit");
        ticketId = m.nextTicketId;
        m.nextTicketId += 1;
        tickets[modelId][ticketId] = Ticket({
            exists: true,
            owner: msg.sender,
            modelId: modelId,
            round: round,
            depositWei: msg.value,
            revealed: false,
            settled: false,
            updateCID: "",
            metricsHash: bytes32(0)
        });
        emit TicketReserved(modelId, round, ticketId, msg.sender, msg.value);
    }

    function publishUpdate(bytes32 modelId, uint256 round, uint256 ticketId, string calldata updateCID, bytes32 metricsHash) external {
        Model storage m = models[modelId];
        require(m.exists, "model missing");
        require(round == m.currentRound, "wrong round");
        Ticket storage t = tickets[modelId][ticketId];
        require(t.exists, "ticket missing");
        require(t.owner == msg.sender, "not owner");
        require(t.round == round, "ticket round mismatch");
        require(!t.revealed, "already revealed");
        require(bytes(updateCID).length > 0, "empty updateCID");
        t.revealed = true;
        t.updateCID = updateCID;
        t.metricsHash = metricsHash;
        emit UpdatePublished(modelId, round, ticketId, msg.sender, updateCID, metricsHash);
    }

    function finalizeRound(
        bytes32 modelId,
        uint256 round,
        string calldata globalCID,
        uint256[] calldata includedTickets,
        uint256[] calldata refundTickets,
        bytes32 scoresHash
    ) external onlyLister(modelId) {
        Model storage m = models[modelId];
        require(round == m.currentRound, "wrong round");
        require(bytes(globalCID).length > 0, "empty globalCID");

        for (uint256 i = 0; i < refundTickets.length; i++) {
            Ticket storage t = tickets[modelId][refundTickets[i]];
            require(t.exists, "refund ticket missing");
            require(t.round == round, "refund round mismatch");
            require(t.revealed, "refund not revealed");
            require(!t.settled, "refund settled");
            t.settled = true;
            entitlements[modelId][t.owner] += t.depositWei;
        }

        for (uint256 a = 0; a < includedTickets.length; a++) {
            for (uint256 b = a + 1; b < includedTickets.length; b++) {
                require(includedTickets[a] != includedTickets[b], "duplicate included");
            }
        }

        uint256 rewardPerIncluded = 0;
        if (includedTickets.length > 0 && m.poolWei > 0) {
            rewardPerIncluded = m.poolWei / includedTickets.length;
        }
        uint256 paid = 0;
        for (uint256 j = 0; j < includedTickets.length; j++) {
            Ticket storage it = tickets[modelId][includedTickets[j]];
            require(it.exists, "included ticket missing");
            require(it.round == round, "included round mismatch");
            require(it.revealed, "included not revealed");
            entitlements[modelId][it.owner] += rewardPerIncluded;
            paid += rewardPerIncluded;
        }
        if (paid > 0) {
            m.poolWei -= paid;
        }
        m.globalCID = globalCID;
        m.currentRound += 1;
        emit RoundFinalized(modelId, round, globalCID, includedTickets.length, refundTickets.length, scoresHash);
    }

    function claim(bytes32 modelId) external {
        uint256 amount = entitlements[modelId][msg.sender];
        require(amount > 0, "nothing to claim");
        entitlements[modelId][msg.sender] = 0;
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "transfer failed");
        emit Claimed(modelId, msg.sender, amount);
    }

    function getModel(bytes32 modelId) external view returns (
        address lister,
        string memory globalCID,
        bytes32 rulesHash,
        uint256 currentRound,
        uint256 depositWei,
        uint256 poolWei,
        uint256 nextTicketId
    ) {
        Model storage m = models[modelId];
        require(m.exists, "model missing");
        return (m.lister, m.globalCID, m.rulesHash, m.currentRound, m.depositWei, m.poolWei, m.nextTicketId);
    }

    function getTicket(bytes32 modelId, uint256 ticketId) external view returns (
        address owner,
        uint256 round,
        uint256 depositWei,
        bool revealed,
        bool settled,
        string memory updateCID,
        bytes32 metricsHash
    ) {
        Ticket storage t = tickets[modelId][ticketId];
        require(t.exists, "ticket missing");
        return (t.owner, t.round, t.depositWei, t.revealed, t.settled, t.updateCID, t.metricsHash);
    }
}
