# !/usr/bin/env python3
# -*- coding: utf-8 -*-

# ----------------------------------------------------- IMPORTS ----------------------------------------------------- #

import logging
from typing import Union, List, Tuple
from Crypto.Cipher import PKCS1_OAEP
from Crypto.PublicKey import RSA
from hashlib import sha256
from random import randint
from functools import reduce
from sys import byteorder


__author__ = 'Denis Verstraeten'
__date__ = '2020.3.9'


# --- Constants --- #
SEP = b' - '


# RSA encryption/decryption
def encrypt(plain: Union[str, bytes],
            key: RSA.RsaKey
            ) -> bytes:
    """
    Encrypts arbitrary size message plain text using RSA.
    :param plain: Message to be encrypted.
    :param key: RSA key.
    :return: RSA Encrypted message.
    """

    if isinstance(plain, str):

        msg = plain.encode('utf-8')

    else:

        msg = plain

    # Credit: https://pythonexamples.org/python-split-string-into-specific-length-chunks/
    block_size = 214  # https://info.townsendsecurity.com/bid/29195/how-much-data-can-you-encrypt-with-rsa-keys
    blocks = [msg[i: i + block_size] for i in range(0, len(msg), block_size)]
    logging.debug(f'Blocks to be encrypted: {list(map(bytes.hex, blocks))}.')

    cypher = reduce(bytes.__add__, map(lambda block: __encrypt(block, key), blocks))
    logging.debug(f'Cypher text is: {cypher.hex()}.')
    return cypher


def __encrypt(plain: bytes,
              key: RSA.RsaKey
              ) -> bytes:
    """
    Encrypts message plain using RSA and returns bytes. Maximum length of message is 2048 bits.
    :param plain: Message to be encrypted.
    :param key: RSA key.
    :return: Encrypted message.
    :rtype: bytes
    """

    logging.debug(f'Encrypting: {plain.hex()}.')
    encryptor = PKCS1_OAEP.new(key)
    cipher = encryptor.encrypt(plain)
    logging.debug(f'Ciphered text: {cipher.hex()}.')
    return cipher


def decrypt(cipher: Union[str, bytes],
            key: RSA.RsaKey
            ) -> bytes:
    """
    Decrypts arbitrary length message using RSA.
    :param cipher: Message to be decrypted.
    :param key: RSA key.
    :return: Decrypted message.
    """

    if isinstance(cipher, str):

        msg = cipher.encode('utf-8')

    else:

        msg = cipher

    # Credit: https://pythonexamples.org/python-split-string-into-specific-length-chunks/
    block_size = int(2048 / 8)
    blocks = [msg[i: i + block_size] for i in range(0, len(msg), block_size)]
    logging.debug(f'Blocks to be encrypted: {list(map(bytes.hex, blocks))}.')

    plain = reduce(bytes.__add__, map(lambda block: __decrypt(block, key), blocks))
    logging.debug(f'Plain text is {plain.hex()}.')
    return plain


def __decrypt(cipher: bytes,
              key: RSA.RsaKey
              ) -> bytes:
    """
    Decrypts the ciphered message using RSA decryption. Maximum cypher length: 2048 bits.
    :param cipher: Ciphered message to be decrypted.
    :param key: RSA key.
    :return: Decrypted message.
    :rtype: bytes
    """

    logging.debug(f'Decrypting message: {cipher.hex()}.')
    decryptor = PKCS1_OAEP.new(key)
    plain = decryptor.decrypt(cipher)
    logging.debug(f'Deciphered: {plain.hex()}.')

    return plain


# RSA based ring signature
# Credit: https://en.wikipedia.org/wiki/Ring_signature#Python_implementation
def sign(keys: List[RSA.RsaKey],
         s: int,
         msg: bytes
         ) -> bytes:
    """
    RSA based ring signature. Modified scheme to be able not to use E_k^-1 by closing the loop.
    See: https://crypto.stackexchange.com/questions/52608/
        rivests-ring-signatures-with-hashes-instead-of-symmetric-encryption
    :param keys: List of RSA keys. All of them are only public except the one of the signer which is also private.
    :param s: Index of the key of the signer in the list keys.
    :param msg: Message to be signed.
    :return: Signature.
    :rtype: list
    """

    logging.debug(f'Signing message {msg.hex()}.')
    k = sha256(msg).digest()
    logging.debug(f'Key is {k.hex()}.')
    v_prime = randint(0, 2**256 - 1)
    logging.debug(f"v' = {v_prime}.")
    signature = [None] * len(keys)
    v = __E_k(v_prime.to_bytes(int(2048 / 8), byteorder), k)
    for i in range(s + 1, len(keys)):

        signature[i] = randint(0, 2**256 - 1)  # x_i in algorithm.
        y = __RSA_mult(signature[i], keys[i].e, keys[i].n)
        v = __E_k((v ^ y).to_bytes(int(2048 / 8), byteorder), k)

    glue = v
    for i in range(s):

        signature[i] = randint(0, 2 ** 256 - 1)  # x_i in algorithm.
        y = __RSA_mult(signature[i], keys[i].e, keys[i].n)
        v = __E_k((v ^ y).to_bytes(int(2048 / 8), byteorder), k)

    y_s = v_prime ^ v  # Solving for y_s
    logging.debug(f'y_s: {y_s}.')
    signature[s] = __RSA_mult(y_s, keys[s].d, keys[s].n)
    logging.debug(f'x_s: {signature[s]}.')
    sig = [glue] + signature
    signature = reduce(bytes.__add__, map(lambda x: x.to_bytes(int(2048 / 8), byteorder), sig))
    logging.debug(f'Signature: {signature.hex()}.')
    return signature


def verify(signature: bytes,
           msg: bytes,
           keys: List[RSA.RsaKey]
           ) -> bool:
    """
    Verifies the signature. Signature is : [Glue value, x_1, x_2,..., x_n].
    :param signature: Signature to be verified.
    :param msg: Signed message.
    :param keys: List of RSA public keys.
    :return: Whether message was properly signed.
    :rtype: bool
    """

    logging.debug(f'Verifying signature on message {msg.hex()}.')
    k = sha256(msg).digest()

    # Credit: https://pythonexamples.org/python-split-string-into-specific-length-chunks/
    sig_size = int(2048 / 8)
    sig = [signature[i: i + sig_size] for i in range(0, len(signature), sig_size)]
    signature = list(map(lambda x: int.from_bytes(x, byteorder), sig))

    y = list(map(lambda index: __RSA_mult(
        signature[index + 1], keys[index].e, keys[index].n), range(len(keys))))  # y = g(x), x[0] = glue value
    r = reduce(lambda v, index: __E_k((v ^ y[index]).to_bytes(int(2048 / 8), byteorder), k),
               range(len(keys)), signature[0])
    logging.debug(f'r: {r}, glue: {signature[0]}.')
    return r == signature[0]


def __E_k(msg: bytes,
          k: bytes
          ) -> int:
    """
    One-way keyed function. Returns E_k(msg) = sha256(msg||k).
    :param msg: Message to be digested.
    :param k: Key.
    :return: Output of E_k.
    :rtype: int.
    """

    digest = int.from_bytes(sha256(msg + k).digest(), byteorder)
    logging.debug(f'E_k: {digest}.')
    return digest


def __RSA_mult(x: int,
               e: int,
               n: int
               ) -> int:
    """
    :return: x^e mod(n).
    """

    return pow(x, e, n)


# SHA256 based commitment
def commit(msg: bytes,
           ) -> Tuple[bytes, bytes]:
    """
    Commits to a message. Uses sha256: c = sha256(msg||r).
    :param msg: Message to be committed.
    :return: Commitment.
    """
    r = randint(0, 2**256 - 1).to_bytes(int(256 / 8), byteorder)
    c = sha256(msg + r).digest()
    logging.debug(f'Commitment: c = {c.hex()}, r = {r.hex()}.')
    return c, r


def commit_verify(msg: bytes,
                  random: bytes,
                  commitment: bytes
                  ) -> bool:
    """
    Checks whether commitment is a valid commitment for message msg with randomness random.
    :param msg: Committed message.
    :param random: Randomness used for the commitment.
    :param commitment: Commitment to be checked.
    :return: Check status.
    """
    logging.debug('Checking commitment.')
    return commitment == sha256(msg + random).digest()


# Bytes strings concatenation / parsing
def concatenate(*bytes_str: bytes
                ) -> bytes:
    """"
    :param bytes_str: Bytes strings to concatenate.
    :return: The concatenation of the bytes strings bytes_string.
    """
    return SEP.join(bytes_str)


def parse(msg: bytes
          ) -> Tuple[bytes, ...]:
    """
    :param msg: Message to be parsed.
    :return: A tuple containing the pieces of the parsed message.
    """
    return tuple(msg.split(SEP))


# ZKP
def verifiable_auction(bids: List[int],
                       com: List[bytes],
                       decom: List[bytes]
                       ) -> Tuple[bytes, bool]:
    """
    Zero knowledge proof for the computation of the winning bidder. TODO implement using ZKP.
    :param bids:
    :param com:
    :param decom:
    :return:
    """
    raise NotImplementedError