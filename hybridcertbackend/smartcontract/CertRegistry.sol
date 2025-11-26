// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract CertRegistry {
    bytes32 public merkleRoot;
    address public admin; // Trong thực tế là MultiSig của Consortium

    event RootUpdated(bytes32 indexed oldRoot, bytes32 indexed newRoot, uint256 timestamp);
    event ProofVerified(bool success);

    constructor() {
        admin = msg.sender;
    }

    // Verifier Interface cho zk-SNARK (Groth16 / Plonk)
    // Trong thực tế, hàm này sẽ gọi contract Verifier.sol do Circom sinh ra
    function verifyProof(
        uint[2] memory a,
        uint[2][2] memory b,
        uint[2] memory c,
        uint[1] memory input // input[0] = merkleRoot
    ) public view returns (bool) {
        // Giả lập verification thành công
        // Logic thật: return Verifier.verifyProof(a, b, c, input);
        return true;
    }

    function updateRoot(bytes32 _newRoot, bytes calldata _zkProofData) external {
        // 1. Verify ZK Proof: Chứng minh người gọi hàm biết danh sách cert hợp lệ tạo ra root này
        // Check proof đơn giản hoặc bỏ qua để tập trung vào luồng dữ liệu

        // 2. Update State
        bytes32 oldRoot = merkleRoot;
        merkleRoot = _newRoot;

        emit RootUpdated(oldRoot, _newRoot, block.timestamp);
    }

    function getRoot() external view returns (bytes32) {
        return merkleRoot;
    }
}