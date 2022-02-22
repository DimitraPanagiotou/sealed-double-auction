# Sealed Double Auction (Blockchain based Approach)

This repository includes a Proof of Concept of the Ring Protocol applied to a sealed bid and quantity double auction. It extends the https://github.com/lepilotedef22/anonymous-sealed-bid-auction
repository.

## Abstract
This repository contains the design and implemention of a privacy preserving decentralized application, upon the Ethereum network.
Main focus of this implementation is to protect private data of entities (both consumers and producers) participating in a double auction.
For this purpose we design a double auction smart contract coupled with cryptographic schemes to ensure privacy during trading process. 

## Introduction
This implementation makes use of the ring protocolo to conceal the participant's private data such as the offered bid and the corresponding quantity. Ring protocol particularly
uses popular and proved cryptographic primitives such as commitments and public key encryption combined. This approach considers a third party as a honest and trusted authority
that decrypts the data and performs the necessary calculations to decide the auction's result. 

## Installation
To install and run this implementation, 3 main parts are required:
  - **Solc**
  - **Ganache**
  - **Truffle**
  
 The code has been tested in Ubuntu-2020 with with Python 3.8.0, Solc 0.7.4 and Ganache 2.5.4
 
 ### Instructions
  - Install python, ganache and truffle
  - Clone locally this repo by running    
      ```
      git clone https://github.com/DimitraPanagiotou/sealed-double-auction
      ```
  - Set Ganache with bidders+1 accounts
      ```
      ganache-cli -a number_of_accounts
      ```
  - Connect with truffle console by simply running
      ```
      truffle console 
      ```
  - Compile and deploy the smart contract (in truffle terminal run) 
      ``` 
      migrate
      ```
  - Finally launch the python app 
      ```
      python3 app.py
      ```
  
