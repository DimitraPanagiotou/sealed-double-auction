# !/usr/bin/env python3
# -*- coding: utf-8 -*-

# ----------------------------------------------------- IMPORTS ----------------------------------------------------- #

import logging
import struct
from typing import Optional, List
from Crypto.PublicKey import RSA
from sys import byteorder
from collections import OrderedDict
from src.participant import Participant
from src.helpers.utils.crypto import decrypt, verify, parse, commit_verify

class Auctioneer(Participant):
    """
    This class handles the auctioneer.
    """

    # ------------------------------------------------- CONSTRUCTOR ------------------------------------------------- #

    def __init__(self,
                 address: str,
                 generate_new_keys: Optional[bool] = True
                 ) -> None:
        """
        :param address: Address of the auctioneer.
        :param generate_new_keys: Flag indicating whether new RSA keys need to be generated.
        """
        logging.info('Creating auctioneer.')
        super().__init__(address, generate_new_keys)
        self.bidders = {}
        self.clearingQuantity = 0
        self.clearingPrice = 0
        self.clearingType = 0

    # --------------------------------------------------- METHODS --------------------------------------------------- #

    def bid_opening(self,
                    address: str,
                    ring: List[RSA.RsaKey],
                    c_quantity: bytes,
                    c_bid_value: bytes,
                    sig: bytes,
                    tau_1: bytes,
                    tau_2: bytes,
                    bidder_type: int,
                    ) -> bool:
        """
        Opens the bid value for bidder at address and stores it.
        :param bidder_type:
        :param bid_value:
        :param address: Address of the bidder.
        :param ring: Ring of public keys used by the bidder for the Ring Signature.
        :param c: Commitment to the bid.
        :param sig: Ring Signature to the bid.
        :param tau_1: Bid opening token.
        :return: Whether the bid opening was successful.
        """
        logging.info(f'Opening bid for bidder at {address}.')
        status = False
        # initialise bidder
        self.bidders[address] = {
            'quantity': 0,
            'bid_value': 0,
            'bidder_type': -1,
            'status': status
        }
        logging.info('Parsing sigma.')
        sigma_quantity, sigma_bid_value, c1_quantity, c1_bid_value = parse(sig)
        if self.verify(c_quantity, sigma_quantity, ring) and self.verify(c_bid_value, sigma_bid_value, ring):
            logging.info('Signature sigma successfully verified.')
            C_quantity, d1_quantity = parse(tau_1)
            C_bid_value, d1_bid_value = parse(tau_2)
            if commit_verify(C_quantity, d1_quantity, c1_quantity) and commit_verify(C_bid_value, d1_bid_value, c1_bid_value):
                logging.info('Commitment C successfully verified.')
                m1 = self.decrypt(C_quantity)
                m2 = self.decrypt(C_bid_value)
                logging.info('Cipher text C decrypted.')
                logging.info('Parsing m1.')
                c_quantity_tilde, sigma_quantity_tilde, quantity, d_quantity = parse(m1)
                c_bid_value_tilde, sigma_bid_value_tilde, bid_value, d_bid_value = parse(m2)
                if (c_quantity_tilde == c_quantity and sigma_quantity_tilde == sigma_quantity) and (c_bid_value_tilde == c_bid_value and sigma_bid_value_tilde == sigma_bid_value):
                    if commit_verify(quantity, d_quantity, c_quantity) and commit_verify(bid_value, d_bid_value, c_bid_value):
                        logging.info('Commitment to quantity and bid value successfully verified.')
                        logging.info('Storing bid, bid value and validating opening.')
                        self.bidders[address] = {
                            'quantity': int.from_bytes(quantity, byteorder),
                            'bid_value': int.from_bytes(bid_value, byteorder),
                            'bidder_type': bidder_type,
                            'status': True
                        }
                        # print(f'Quantity: {int.from_bytes(quantity, byteorder)}.')
                        # print(f'Bid Value: {int.from_bytes(bid_value, byteorder)}.')
                        status = True

        return status

    def getAvg(self, a, b):
        return (a + b) / 2

    def get_uniform_price(self) -> None:
        """
        Gets the winning bid value and the winning commitment.
        """
        logging.info('Getting uniform price.')
        demand_quantity = 0
        supply_quantity = 0

        generation = {}
        consumption = {}
        for bidder_address in self.bidders.keys():
            if self.bidders[bidder_address]['status']:
                if self.bidders[bidder_address]['bidder_type'] == 0:
                    generation_quantity = self.bidders[bidder_address]['quantity']
                    generation_price = self.bidders[bidder_address]['bid_value']
                    if generation_price in generation:
                        generation[generation_price] += generation_quantity
                    else:
                        generation[generation_price] = generation_quantity

                else:
                    consumption_quantity = self.bidders[bidder_address]['quantity']
                    consumption_price = self.bidders[bidder_address]['bid_value']
                    if consumption_price in consumption:
                        consumption[consumption_price] += consumption_quantity
                    else:
                        consumption[consumption_price] = consumption_quantity

        consumption_items = consumption.items()
        sorted_consumption = OrderedDict(sorted(consumption_items, reverse=True))  # descending

        generation_items = generation.items()
        sorted_generation = OrderedDict(sorted(generation_items))  # ascending

        sorted_generation_prices = list(sorted_generation.keys())

        sorted_consumption_prices = list(sorted_consumption.keys())

        i = 0
        j = 0
        while j < len(sorted_generation) and i < len(sorted_consumption) and sorted_consumption_prices[i] >= sorted_generation_prices[j]:
            buy_quantity = demand_quantity + sorted_consumption[sorted_consumption_prices[i]]
            sell_quantity = supply_quantity + sorted_generation[sorted_generation_prices[j]]
            if buy_quantity > sell_quantity:
                supply_quantity = sell_quantity
                self.clearingQuantity = sell_quantity
                b = sorted_consumption_prices[i]
                a = sorted_consumption_prices[i]
                j = j + 1

                self.clearingType = 2  # marginal buyer more buy quantity than sell quantity

            elif buy_quantity < sell_quantity:
                demand_quantity = buy_quantity
                self.clearingQuantity = buy_quantity
                b = sorted_generation_prices[j]
                a = sorted_generation_prices[j]
                i=i+1

                self.clearingType = 1  # marginal seller more sell quantity than buy quantity

            else:
                supply_quantity = buy_quantity
                demand_quantity = buy_quantity
                self.clearingQuantity = buy_quantity
                a = sorted_consumption_prices[i]
                b = sorted_generation_prices[j]
                i=i+1
                j=j+1
                self.clearingType = 3  # quantity aggrement

        if self.clearingType == 1:  # marginal seller
            # satisfy all buyers
            self.clearingPrice = b
        elif self.clearingType == 2:  # marginal buyer
            # satisfy all sellers
            self.clearingPrice = a
        else:
            # satisfy both sellers and buyers
            self.clearingPrice = self.getAvg(a, b)

        print("clearing price: ", self.clearingPrice)
        print("clearing quantity: ", self.clearingQuantity)
        print("clearing type: ", self.clearingType)

    def decrypt(self,
                cipher: bytes
                ) -> bytes:
        """
        Uses RSA to decrypt cipher text.
        :return: Plain text.
        """
        logging.debug(f'Cipher text: {cipher.hex()}.')
        plain = decrypt(cipher, self._RSA_key)
        logging.debug(f'Plain text: {plain}.')
        return plain

    def verify(self,
               msg: bytes,
               sig: bytes,
               ring: List[RSA.RsaKey]
               ) -> bool:
        """
        Verifies that a message msg has valid signature sig.
        :param msg: Signed message.
        :param sig: Ring signature.
        :param ring: Ring of keys to be used to check the validity of the signature.
        :return: Validity of signature.
        """
        return verify(sig, msg, ring)

    def __repr__(self) -> str:
        """
        :return: str representation of Auctioneer.
        """
        return f'Auctioneer(address: {self.address})'
