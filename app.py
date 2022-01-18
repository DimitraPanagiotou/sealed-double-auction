import json
from web3 import Web3, HTTPProvider
from argparse import ArgumentParser
import logging
from requests.exceptions import ConnectionError

from src.auction import Auction


def main():
    auction = Auction()
    try:
        auction.deploy()
        auction.proof_of_concept()
    except ConnectionError as e:
        print('Cannot connect to Ganache.')
        print('Make sure that Ganache is running and try again...')


main()
