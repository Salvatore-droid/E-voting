pragma solidity ^0.8.0;

contract VotingContract {
    struct Vote {
        bytes32 voteHash;
        uint256 voterId;
        uint256 candidateId;
        uint256 positionId;
        uint256 electionId;
        uint256 timestamp;
        bool exists;
    }
    
    struct ElectionResult {
        uint256 candidateId;
        uint256 voteCount;
    }
    
    address public admin;
    mapping(bytes32 => Vote) public votes;
    mapping(uint256 => mapping(uint256 => uint256)) public electionResults; // electionId => candidateId => voteCount
    mapping(uint256 => bool) public elections; // electionId => exists
    
    event VoteCast(bytes32 indexed voteHash, uint256 voterId, uint256 candidateId, uint256 positionId, uint256 electionId);
    event VoteVerified(bytes32 indexed voteHash, bool isValid);
    
    modifier onlyAdmin() {
        require(msg.sender == admin, "Only admin can perform this action");
        _;
    }
    
    constructor() {
        admin = msg.sender;
    }
    
    function castVote(
        bytes32 _voteHash,
        uint256 _voterId,
        uint256 _candidateId,
        uint256 _positionId,
        uint256 _electionId
    ) external onlyAdmin {
        require(!votes[_voteHash].exists, "Vote already exists");
        require(elections[_electionId], "Election does not exist");
        
        votes[_voteHash] = Vote({
            voteHash: _voteHash,
            voterId: _voterId,
            candidateId: _candidateId,
            positionId: _positionId,
            electionId: _electionId,
            timestamp: block.timestamp,
            exists: true
        });
        
        // Update election results
        electionResults[_electionId][_candidateId] += 1;
        
        emit VoteCast(_voteHash, _voterId, _candidateId, _positionId, _electionId);
    }
    
    function verifyVote(bytes32 _voteHash) external view returns (bool) {
        return votes[_voteHash].exists;
    }
    
    function getElectionResults(uint256 _electionId) external view returns (uint256[] memory, uint256[] memory) {
        require(elections[_electionId], "Election does not exist");
        
        // This is a simplified implementation
        // In a real scenario, you'd need a more efficient way to return results
        uint256 candidateCount = 100; // This should be dynamic based on your needs
        uint256[] memory candidateIds = new uint256[](candidateCount);
        uint256[] memory voteCounts = new uint256[](candidateCount);
        
        for (uint256 i = 0; i < candidateCount; i++) {
            candidateIds[i] = i;
            voteCounts[i] = electionResults[_electionId][i];
        }
        
        return (candidateIds, voteCounts);
    }
    
    function addElection(uint256 _electionId) external onlyAdmin {
        elections[_electionId] = true;
    }
    
    function transferAdmin(address _newAdmin) external onlyAdmin {
        admin = _newAdmin;
    }
}