// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract DCALedger {
    // Lưu trữ Merkle Root (32 bytes)
    bytes32 public merkleRoot;

    // Địa chỉ của Admin (Server Python)
    address public admin;

    // Sự kiện để lưu log (giúp tra cứu lịch sử thay đổi)
    event RootUpdated(bytes32 indexed oldRoot, bytes32 indexed newRoot, uint256 timestamp);

    constructor() {
        // Người deploy contract này sẽ là admin
        admin = msg.sender;
    }

    // Hàm cập nhật Root mới
    function updateRoot(bytes32 _newRoot) public {
        require(msg.sender == admin, "Only Admin CA can update root");

        bytes32 oldRoot = merkleRoot;
        merkleRoot = _newRoot;

        // Emit sự kiện để client có thể lắng nghe hoặc query lại
        emit RootUpdated(oldRoot, _newRoot, block.timestamp);
    }

    // Hàm lấy Root hiện tại (thực ra public variable đã tự có getter, nhưng viết rõ cho dễ hiểu)
    function getRoot() public view returns (bytes32) {
        return merkleRoot;
    }
}