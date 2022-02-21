import logging
from pathlib import Path

import solcx
from web3 import Web3
from json import loads, dump
from solcx import compile_standard
from random import randint, getrandbits, sample
from sys import byteorder
from typing import Optional, Any, Union, List
from hexbytes import HexBytes
import json
from web3 import Web3, HTTPProvider
from cryptocompare import get_price
from Crypto.PublicKey import RSA
from csv import writer
from src.auctioneer import Auctioneer
from src.helpers.utils.file_helper import get_bidders
from src.helpers.utils.crypto import parse
from src.participant import Participant


class Auction:
    """
    This class handles everything which is related to the auction.
    """

    # --- Constants --- #
    DEPOSIT = 1000000000000000000  # 1 ETH deposit expressed in Wei.

    # ------------------------------------------------- CONSTRUCTOR ------------------------------------------------- #
    def __init__(self) -> None:
        logging.info('Creating Auction object.')
        self.__contract = None
        self.__w3 = Web3(Web3.HTTPProvider('http://127.0.0.1:9545'))
        self.__abi = None
        self.__is_deployed = False
        self.__auctioneer = None
        self.__bidders = []
        self.__number_of_tx = 0
        logging.info('Auction object created.')

    # --------------------------------------------------- METHODS --------------------------------------------------- #
    def deploy(self) -> None:
        """
        This method deploys the Auction smart contract on the Ganache Ethereum local chain.
        See: https://www.trufflesuite.com/ganache
        Credit: https://web3py.readthedocs.io/en/stable/contracts.html
        Credit: https://github.com/ethereum/py-solc
        """
        logging.info('Deploying Auction smart contract on chain.')
        logging.info('Compiling smart contract source code into bytecode using solc.')
        contract_path = Path.cwd() / 'contracts' / 'Double_Auction.sol'
        logging.info(f'Contract path: {contract_path}.')
        compiled = compile_standard(
            {
                'language': 'Solidity',
                'sources': {
                    'Double_Auction.sol': {
                        'urls': [str(contract_path)]
                    }
                },
                'settings': {
                    'outputSelection': {
                        '*': {
                            '*': [
                                'metadata',
                                'evm.bytecode',
                                'evm.bytecode.sourceMap'
                            ]
                        }
                    }
                }
            },
            allow_paths=str(contract_path)
        )
        self.__w3.eth.defaultAccount = self.__w3.eth.accounts[0]  # First account is default account.
        bytecode = compiled['contracts']['Double_Auction.sol']['DoubleAuction']['evm']['bytecode']['object']
        self.__abi = loads(compiled['contracts']['Double_Auction.sol']['DoubleAuction']['metadata'])['output']['abi']
        logging.info('Creating temporary contract object.')
        temp_contract = self.__w3.eth.contract(abi=self.__abi, bytecode=bytecode)
        logging.info('Transacting contract on the chain.')
        tx_hash = temp_contract.constructor().transact()
        logging.info(f'Transaction hash: {tx_hash.hex()}.')
        tx_receipt = self.__w3.eth.waitForTransactionReceipt(tx_hash)
        contract_address = tx_receipt.contractAddress
        logging.info('Transacting contract on the chain.')
        logging.info(f'Contract address: {contract_address}.')
        data = {
            'abi': self.__abi,
            'bytecode': bytecode,
            'contractAddress': contract_address
        }
        compile_path = Path.cwd() / 'compile'
        if not compile_path.exists():
            compile_path.mkdir(parents=True, exist_ok=True)

        with open(Path.cwd() / 'compile' / 'out.json', 'w') as output_file:
            logging.info('Storing abi, bytecode and contract address in compile/out.json.')
            dump(data, output_file, indent=4)
            logging.info('Abi, bytecode and address stored.')

        logging.info('Connecting to actual smart contract.')
        self.__contract = self.__w3.eth.contract(address=contract_address,
                                                 abi=self.__abi,
                                                 bytecode=bytecode)
        logging.info('Connected to smart contract.')
        self.__is_deployed = True
        print('Auction smart contract successfully deployed.')

    def proof_of_concept(self
                         ) -> None:
        """
        This method implements the proof of concept.
        :param show_total_price: Flag indicating total price of auction for each participant should be displayed.
        """
        # --- Deploying Smart Contract --- #
        if not self.__is_deployed:
            logging.info('Deploying smart contract.')
            self.deploy()

        # --- Getting bidders indices --- #
        bidders_dic = None
        for entry in self.__abi:
            try:
                if entry['name'] == 'bidders':
                    bidders_dic = entry
                    break

            except KeyError:
                pass

        outputs = bidders_dic['outputs']
        indices = {}
        for index, output in enumerate(outputs):
            indices[output['name']] = index

        c_quantity_index = indices['c_quantity']
        c_bid_value_index = indices['c_bid_value']
        sig_index = indices['sig']
        ring_index = indices['ring']
        bidder_type_index = indices['bidder_type']
        tau_1_index = indices['tau_1']
        tau_2_index = indices['tau_2']

        # --- Setting up filters --- #
        new_bidder_filter = self.__contract.events.newBidder.createFilter(fromBlock='latest')

        print('Simulating anonymous sealed-bid auction protocol...')
        # --- Generating auctioneer and bidders --- #
        self.__auctioneer = Auctioneer(address=self.__w3.eth.defaultAccount)
        print(f'Auctioneer created: {self.__auctioneer}.')
        self.__bidders = get_bidders(Path('bidders.json'))  # If new file is created,
        # max number of bidders must be < number of accounts on the blockchain.
        pub_keys = list(map(lambda b: b.public_key, self.__bidders)) # function is first argument of map while __bidders is the second one
        pub_keys.append(self.__auctioneer.public_key)
        bidder_addresses = sample(self.__w3.eth.accounts[1:], len(self.__bidders))
        # Randomly picks n = len(self.__bidders) addresses out of the accounts list.
        # Element zero is excluded because it is auctioneer address.
        for (index, bidder) in enumerate(self.__bidders):
            bidder.address = bidder_addresses[index]
            bidder.auctioneer_pub_key = self.__auctioneer.public_key
            bidder.make_ring(pub_keys) # create a ring for every bidder

        logging.debug(f'Bidders created: {self.__bidders}.')

        # --- Starting auction --- #
        logging.info('Starting auction.')
        tx = {
            'from': self.__auctioneer.address,
            'value': 0
        }
        self.__send_transaction(tx, 'startAuction')
        print("Auctioneer send transaction to initialise the contract!")

        # --- Placing bids --- #
        for bidder in self.__bidders:
            logging.info(f'Placing bid for bidder {bidder}.')
            c_quantity, c_bid_value, sig = bidder.bid()
            tx = {
                'from': bidder.address,
                'value': Auction.DEPOSIT
            }
            self.__send_transaction(tx, 'placeBid', c_quantity, c_bid_value, sig, bidder.export_ring(),  bidder.bidder_type)

        # --- Opening bids --- #
        for bidder in self.__bidders:
            tau_1 = bidder.tau_1
            tau_2 = bidder.tau_2
            tx = {
                'from': bidder.address
            }
            self.__send_transaction(tx, 'openBid', tau_1, tau_2)

        for event in new_bidder_filter.get_new_entries():
            new_bidder_address = event['args']['newBidderAddress']
            event_name = event['event']
            logging.info(f'Catching event {event_name} from bidder at {new_bidder_address}.')
            self.__auctioneer.bidders[new_bidder_address] = None

        for bidder_address in self.__auctioneer.bidders.keys():
            bidder = self.__call('bidders', bidder_address)
            c_quantity = bidder[c_quantity_index]
            c_bid_value = bidder[c_bid_value_index]
            sig = bidder[sig_index]
            tau_1 = bidder[tau_1_index]
            tau_2 = bidder[tau_2_index]
            bidder_type = bidder[bidder_type_index]

            ring = list(map(lambda key: RSA.importKey(key), parse(bidder[ring_index]))) ########???????
            logging.info(f'Opening bid for bidder at {bidder_address}.')
            if self.__auctioneer.bid_opening(bidder_address, ring, c_quantity, c_bid_value, sig, tau_1, tau_2, bidder_type):
                logging.info(f'Bid opening successful for bidder at {bidder_address}.')
            else:
                logging.info(f'Bid opening failed, punishing bidder at {bidder_address}.')
                self.__auctioneer.bidders.pop(bidder_address, None)
                tx = {
                    'from': self.__auctioneer.address
                }
                self.__send_transaction(tx, 'punishBidder', bidder_address)

        # --- Getting clearing information --- #
        logging.info('Getting uniform price.')
        self.__auctioneer.get_uniform_price()

        # --- Announce clearing information --- #
        clearingQuantity = self.__auctioneer.clearingQuantity
        clearingPrice = self.__auctioneer.clearingPrice
        clearingType = self.__auctioneer.clearingType
        tx = {
            'from': self.__auctioneer.address
        }
        logging.info('Publishing clearing price')
        self.__send_transaction(tx, 'announceClearing', clearingQuantity, clearingPrice, clearingType)

        print(self.__call('clearing'))

    def __send_transaction(self,
                           transaction,
                           func_name: Optional[str] = None,
                           *args
                           ) -> None:
        """
        Executes a transaction. Can be the execution of a smart contract function.
        :param transaction: Transaction data.
        :param participant: Optional participant whose gas consumption should be updated.
        :param func_name: Optional name of the smart contract function to be executed.
        :param args: Argument to be passed to the function.
        """
        if func_name is not None:
            logging.info(f'Executing function {func_name}.')
            tx_hash = self.__contract.functions[func_name](*args).transact(transaction)

        else:
            logging.info('Executing transaction.')
            tx_hash = self.__w3.eth.sendTransaction(transaction)

        logging.info(f'Transaction hash: {tx_hash.hex()}.')
        self.__number_of_tx += 1

    def __call(self,
               func_name: str,
               *args
               ) -> Any:
        """
        Executes a call to the smart contract. Does not consume gas. Does not alter smart contract state.
        :param func_name: Name of the function to be called.
        :param args: Argument to be passed to the function.
        :return: Output of the function.
        """
        logging.info(f'Calling function {func_name}.')
        rtn = self.__contract.functions[func_name](*args).call()
        logging.debug(f'Return value is {rtn}.')
        return rtn

