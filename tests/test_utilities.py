import pytest
from web3.types import Wei

from uniswap_smart_path._utilities import (  # noqa
    is_null_address,
    to_wei,
)

from .conftest import tokens


@pytest.mark.parametrize(
    "amount, expected_result",
    (
        (10**18, Wei(10**18)),
        (123.45, Wei(123)),
    )
)
def test_to_wei(amount, expected_result):
    assert expected_result == to_wei(amount)


@pytest.mark.parametrize(
    "address, expected_result",
    (
        (tokens["UNI"], False,),
        ("0"*40, True),
        ("Not an address", False),
        (None, False),
    )
)
def test_is_null_address(address, expected_result):
    assert expected_result == is_null_address(address)
