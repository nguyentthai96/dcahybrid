pragma solidity ^0.8.0;

contract SimpleRegistry {
    event Stored(address indexed sender, string indexed cid, uint256 timestamp);

    function storeCID(string calldata cid) external {
        emit Stored(msg.sender, cid, block.timestamp);
    }
}