// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Wallet {
    address public owner;
    event TransferLogged(address indexed fromUser, address indexed to);

    constructor() {
        owner = msg.sender;
    }

    function withdraw(uint256 amount) external {
        require(tx.origin == owner, "not owner");
        payable(owner).transfer(amount);
    }

    function logTransfer(address to) external {
        emit TransferLogged(tx.origin, to);
    }
}
