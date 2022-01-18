//SPDX-License-Identifier: GPL-3.0
pragma solidity >= 0.5.16;

contract DoubleAuction{

    constructor() public{
        auctioneer = msg.sender;
    }

    struct Bidder {
        bytes c_quantity;
        bytes c_bid_value;
        bytes sig;
        bytes ring;
        bytes tau_1;
        bytes tau_2;
        int bidder_type;
    }

    struct Clearing {
        int clearingQuantity;
        int clearingPrice;
        int clearingType;
    }

    address auctioneer;
    mapping(address => Bidder) public bidders;
    Clearing public clearing;
    uint public totalDeposit = 0;
    mapping(address => uint) public deposit;
    bool placeBidPhase = false;
    bool openBidPhase = false;
    bool announceResultPhase = false;

    /* Events */
    event newBidder(address newBidderAddress);


    /* Modifiers */
    modifier onlyOwner(){
        require(msg.sender == auctioneer,"Only owner can proceed");
        _;
    }

    modifier canStartAuction {
        require(totalDeposit == 0, 'Cannot start new auction, deposits are not empty.');
        _;
    }

    modifier isPlaceBidPhase {
        require(placeBidPhase = true, 'Cannot proceed to place bid phase of the contract because contract has not started yet');
        _;
    }

    modifier isOpenBidPhase {
        require(openBidPhase = true, 'Cannot proceed to open bid phase of the contract because place bid phase has not been completed yet');
        _;
    }

    modifier isAnnounceResultPhase {
        require(announceResultPhase = true, 'Cannot proceed to announce result phase of the contract because open bid phase has not been completed yet');
        _;
    }

    /* Functions */
    function startAuction() public payable onlyOwner canStartAuction {
        auctioneer = msg.sender;      /* auctioneer is the contract owner */
        placeBidPhase = true;
    }

    function endPlaceBid() public onlyOwner isPlaceBidPhase {
        placeBidPhase = false;
        openBidPhase = true;
    }

    function endOpenBid() public onlyOwner isOpenBidPhase {
        openBidPhase = false;
        announceResultPhase = true;
    }

    function placeBid(bytes memory _c_quantity, bytes memory _c_bid_value, bytes memory _sig, bytes memory _ring, int _bidder_type) public payable isPlaceBidPhase {
        deposit[msg.sender] = msg.value;
        totalDeposit += msg.value;
        bidders[msg.sender].bidder_type = _bidder_type;
        bidders[msg.sender].c_quantity = _c_quantity;
        bidders[msg.sender].c_bid_value = _c_bid_value;
        bidders[msg.sender].sig = _sig;
        bidders[msg.sender].ring = _ring;
        emit newBidder(msg.sender);
    }

    function openBid(bytes memory _tau_1, bytes memory _tau_2) public isOpenBidPhase {
        bidders[msg.sender].tau_1 = _tau_1;
        bidders[msg.sender].tau_2 = _tau_2;
    }

    function announceClearing(int _clearingQuantity, int _clearingPrice, int _clearingType) public onlyOwner isAnnounceResultPhase  {
        clearing.clearingPrice = _clearingPrice;
        clearing.clearingQuantity = _clearingQuantity;
        clearing.clearingType = _clearingType;
    }

    function punishBidder(address bidderAddress) public onlyOwner {
        deposit[bidderAddress] = 0;
        totalDeposit -= deposit[bidderAddress];
    }
}

