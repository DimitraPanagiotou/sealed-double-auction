# !/usr/bin/env python3
# -*- coding: utf-8 -*-

# ----------------------------------------------------- IMPORTS ----------------------------------------------------- #

import logging
import struct
from typing import Optional, List, Tuple
from random import randint, sample, shuffle
from Crypto.PublicKey import RSA
from sys import byteorder

from src.participant import Participant
from src.helpers.utils.crypto import sign, commit, encrypt, concatenate

__author__ = 'Denis Verstraeten'
__date__ = '2020.3.6'


class Bidder(Participant):
    """
    This class handles a bidder.
    """

    # ------------------------------------------------- CONSTRUCTOR ------------------------------------------------- #

    def __init__(self,
                 bid_value: Optional[float] = None,
                 quantity: Optional[int] = None,
                 bidder_type: Optional[int] = None,
                 address: Optional[str] = None,
                 generate_new_keys: Optional[bool] = True
                 ) -> None:
        """
        :param bid: Amount of the bid.
        :param address: Address of the bidder.
        :param generate_new_keys: Flag indicating whether new RSA keys need to be generated.
        """

        logging.info('Creating Bidder.')
        super().__init__(address, generate_new_keys)
        self.bid_value = bid_value
        self.quantity = quantity
        self.bidder_type = bidder_type  # 0 seller, 1 buyer
        self.auctioneer_pub_key = None
        self.ring = None
        self.__s = None  # bidder's secret key
        self.c_quantity = None  # commintment parameter for quantity
        self.d_quantity = None  # commintment parameter for quantity
        self.sigma_quantity = None  # signed quantity message
        self.C_quantity = None
        self.c1_quantity = None
        self.d1_quantity = None
        self.c_bidValue = None  # commintment parameter for bid value
        self.d_bidValue = None  # commintment parameter for bid value
        self.sigma_bidValue = None  # signed bid value message
        self.C_bidValue = None
        self.c1_bidValue = None
        self.d1_bidValue = None
        self.sig = None
        self.tau_1 = None
        self.tau_2 = None
        logging.info('Bidder created.')

    # --------------------------------------------------- METHODS --------------------------------------------------- #

    def make_ring(self, keys: List[RSA.RsaKey]) -> None:
        """
        Builds a ring of possible signers.
        :param keys: Keys from which the ring is constructed.
        """
        logging.info('Making ring for bidder.')
        self.ring = [self.public_key, self.auctioneer_pub_key]
        self.ring.extend(sample(list(filter(
            lambda key: key != self.public_key and key != self.auctioneer_pub_key, keys)), randint(0, len(keys) - 2)))
        shuffle(self.ring)
        self.__s = self.ring.index(self.public_key)
        self.ring[self.__s] = self._RSA_key
        logging.info(f'Ring of size {len(self.ring)} created. s = {self.__s}.')
        logging.debug(f'Ring: {self.ring}.')

    def export_ring(self) -> bytes:
        """
        :return: The concatenation of the keys of the ring.
        """
        return concatenate(*list(map(lambda key: key.publickey().exportKey(), self.ring)))

    def bid(self) -> Tuple[bytes, bytes, bytes]:
        """
        :return: Commitments and signatures to the bid to be placed.
        """
        logging.info('Generating bid.')
        logging.info('Computing c and d for quantity and bid value.')
        # Generate commitment for quantity factor
        self.c_quantity, self.d_quantity = commit(self.quantity.to_bytes(int(256 / 8), byteorder))
        # Generate commitment for bid value
        self.c_bidValue, self.d_bidValue = commit(self.bid_value.to_bytes(int(256 / 8), byteorder))
        logging.info('Computing sigma for quantity.')
        self.sigma_quantity = sign(self.ring, self.__s, self.c_quantity)  # __s stands for bidder's secret key
        logging.info('Computing sigma for bid value.')
        self.sigma_bidValue = sign(self.ring, self.__s, self.c_bidValue)
        logging.info('Computing C1.')
        # msg = c_quantity || sigma || quantity || d_quantity
        quantity_msg = concatenate(self.c_quantity, self.sigma_quantity, self.quantity.to_bytes(int(256 / 8), byteorder), self.d_quantity)
        # msg = c_bidValue || sigma || quantity || d_bidValue
        bid_value_msg = concatenate(self.c_bidValue, self.sigma_bidValue, self.bid_value.to_bytes(int(256 / 8), byteorder), self.d_bidValue)
        # encrypted message for quantity and bid value
        self.C_quantity = encrypt(quantity_msg, self.auctioneer_pub_key)
        self.C_bidValue = encrypt(bid_value_msg, self.auctioneer_pub_key)
        logging.info('Computing commitments for encrypted C.')
        self.c1_quantity, self.d1_quantity = commit(self.C_quantity)
        self.c1_bidValue, self.d1_bidValue = commit(self.C_bidValue)
        # modified signature equals σ_quantity | σ_bidValue | c1_quantity | c1_bidValue
        self.sig = concatenate(self.sigma_quantity, self.sigma_bidValue, self.c1_quantity, self.c1_bidValue)
        self.tau_1 = concatenate(self.C_quantity, self.d1_quantity)  # opening token for quantity
        self.tau_2 = concatenate(self.C_bidValue, self.d1_bidValue)  # opening token for bid value

        return self.c_quantity, self.c_bidValue, self.sig

    def __repr__(self) -> str:
        """
        :return: str representation of Bidder.
        """

        return f'Bidder(bidder type: {self.bidder_type}, address: {self.address}, key: {self.public_key})'
