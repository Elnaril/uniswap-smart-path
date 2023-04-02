from typing import Any

from web3 import Web3
from web3.types import Wei


def to_wei(amount: Any) -> Wei:
    return Wei(int(amount))


def is_null_address(address: Any) -> bool:
    try:
        return True if Web3.to_checksum_address(address) and "0" * 40 in address else False
    except (TypeError, ValueError):
        return False
