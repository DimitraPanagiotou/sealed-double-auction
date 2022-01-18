import logging
from typing import List, Optional
from pathlib import Path
from json import load, dump
from random import randint
from src.bidder import Bidder

def get_bidders(bidder_file: Path,
                bidders_number: Optional[int] = 6,
                min_bid: Optional[int] = 0,
                max_bid: Optional[int] = 20,
                min_quantity: Optional[int] = 10,
                max_quantity: Optional[int] = 100
                ) -> List[Bidder]:
    """
    Parses the file in which the bidder data is stored.
    Data structure in bidder_file: {'bidders': [{'name': bidder_name, 'value': bid_value}]}
    :param bidder_file: File in which bidder data is stored. If file path does not exist,
    a new file is created at this path with randomly generated data.
    :param bidders_number: number of bidders to be generated.
    :param min_bid: min value  of the bids.
    :param max_bid: max value of the bids.
    :return: List of Bidder.
    """
    if bidder_file.exists():
        logging.info(f'Parsing data file: {bidder_file}.')
        with open(bidder_file, 'r') as file:
            data = load(file)
            bidders = list(map(lambda bidder: Bidder(bidder['bid_value'], bidder['quantity'], bidder['bidder_type']), data['bidders']))
            logging.debug(f'Bidders: {bidders}.')
            return bidders

    else:
        logging.info(f'Creating/updating {bidder_file}.')
        bids = []
        bidders = []
        quantities = []
        for i in range(bidders_number):
            #name = f'bidder{i}'
            bid = randint(min_bid, max_bid)
            quantity = randint(min_quantity, max_quantity)
            bidder_type = randint(0, 1)

            bids.append(bid)
            quantities.append(quantity)
            bidders.append(Bidder(bid, quantity, bidder_type))

        with open(bidder_file, 'w') as file:
            data = {
                'bidders': list(map(lambda bidder: {
                    'bid_value': bidder.bid_value,
                    'quantity': bidder.quantity,
                    'bidder_type': bidder.bidder_type
                }, bidders))
            }
            logging.debug(f'Data to be stored: {data}.')
            dump(data, file, indent=4)

        logging.debug(f'Bidders: {bidders}.')
        return bidders