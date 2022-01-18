#from __future__ import annotations
import logging
from abc import ABC
from Crypto.PublicKey import RSA


class Participant(ABC):
    """
    This super class handles everything related to participants of the auction.
    It should be extended in Auctioneer and in Bidder.
    """

    # ------------------------------------------------- CONSTRUCTOR ------------------------------------------------- #

    def __init__(self, address: str, generate_new_keys: bool) -> None:
        """
        :param address: Address of the Participant.
        :param generate_new_keys: Flag indicating whether new RSA keys need to be generated.
        """
        logging.info('Creating Participant.')
        self.address = address
        self.gas = 0
        if generate_new_keys:
            self._RSA_key = RSA.generate(2048)
            self.public_key = self._RSA_key.publickey()

        else:
            self._RSA_key = None
            self.public_key = None