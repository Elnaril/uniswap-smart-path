import asyncio
import os
from typing import Dict

import pytest
from web3 import AsyncWeb3

from uniswap_smart_path._datastructures import Token  # noqa


tokens: Dict[str, Token] = {
    "USDC": Token(AsyncWeb3.to_checksum_address("0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"), "USDC", 6),
    "USDT": Token(AsyncWeb3.to_checksum_address("0xdac17f958d2ee523a2206206994597c13d831ec7"), "USDT", 6),
    "DAI": Token(AsyncWeb3.to_checksum_address("0x6b175474e89094c44da98b954eedeac495271d0f"), "DAI", 18),
    "WETH": Token(AsyncWeb3.to_checksum_address("0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"), "WETH", 18),
    "FAKE": Token(AsyncWeb3.to_checksum_address("0xffffffffffffffffffffffffffffffffffffffff"), "FAKE", 18),
    "UNI": Token(AsyncWeb3.to_checksum_address("0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984"), "UNI", 18),
    "LINK": Token(AsyncWeb3.to_checksum_address("0x514910771AF9Ca656af840dff83E8264EcF986CA"), "LINK", 18),
    "MKR": Token(AsyncWeb3.to_checksum_address("0x9f8f72aa9304c8b593d555f12ef6589cc3a579a2"), "???", 18),
}


@pytest.fixture(scope="session")
def event_loop():  # a bit of magic
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def rpc_endpoint():
    return os.environ["RPC_ENDPOINT"]


@pytest.fixture
def w3(rpc_endpoint):
    return AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(rpc_endpoint))


@pytest.fixture
def uniswapv2_address():
    return AsyncWeb3.to_checksum_address("0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D")


@pytest.fixture
def uniswapv3_quoter_address():
    return AsyncWeb3.to_checksum_address("0x61fFE014bA17989E743c5F6cB21bF9697530B21e")
