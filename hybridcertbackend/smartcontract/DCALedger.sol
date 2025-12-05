// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract DCALedger {
    // Lưu trữ Merkle Root (32 bytes)
    bytes32 public merkleRoot;

    // Địa chỉ của Admin (Server Python); Trong thực tế là MultiSig của Consortium
    address public admin;

    // Mapping để kiểm tra xem một public signal (file hash zk) đã được commit chưa
    mapping(uint256 => bool) public validSignals;

    // Sự kiện để lưu log (giúp tra cứu lịch sử thay đổi)
    //tra cứu lại qua tx_hash
    event CertificateCommitted(
        bytes32 indexed oldRoot,
        bytes32 indexed newRoot,
        uint256 indexed publicSignal, // Đây là giá trị Hash ZK cần lấy lại   Hash Poseidon
        uint256 timestamp
    );

    constructor() {
        // Người deploy contract này sẽ là admin
        admin = msg.sender;
    }

    // Hàm cập nhật Root mới, để cấp chứng chỉ
    function submitCertificate(bytes32 _newRoot, uint256 _zkPublicSignal) external {
        require(msg.sender == admin, "Only Admin CA can update root");

        bytes32 oldRoot = merkleRoot;
        merkleRoot = _newRoot;

        // Kiểm tra logic (tuỳ chọn): Không cho phép submit lại cùng 1 tín hiệu nếu muốn
        // require(!validSignals[_zkPublicSignal], "Signal already processed");
        // NTT now not check allow commit many time,
        // validSignals[_zkPublicSignal] = true;

        // Emit sự kiện để lưu dữ liệu vào Logs client có thể lắng nghe hoặc query lại
        emit CertificateCommitted(oldRoot, _newRoot, _zkPublicSignal, block.timestamp);
    }

    // Hàm lấy Root hiện tại (thực ra public variable đã tự có getter, nhưng viết rõ cho dễ hiểu)
    function getRoot() public view returns (bytes32) {
        return merkleRoot;
    }

    // Hàm cho bên thứ 3 kiểm tra
    function checkSignal(uint256 _signal) external view returns (bool) {
        return validSignals[_signal];
    }
}