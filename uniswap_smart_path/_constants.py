from typing import (
    Dict,
    Tuple,
)

from web3 import Web3

from ._datastructures import Token


erc20_abi = '[{"constant":true,"inputs":[],"name":"name","outputs":[{"name":"","type":"string"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"_spender","type":"address"},{"name":"_value","type":"uint256"}],"name":"approve","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"totalSupply","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"_from","type":"address"},{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transferFrom","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transfer","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[{"name":"_owner","type":"address"},{"name":"_spender","type":"address"}],"name":"allowance","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"anonymous":false,"inputs":[{"indexed":true,"name":"_from","type":"address"},{"indexed":true,"name":"_to","type":"address"},{"indexed":false,"name":"_value","type":"uint256"}],"name":"Transfer","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"name":"_owner","type":"address"},{"indexed":true,"name":"_spender","type":"address"},{"indexed":false,"name":"_value","type":"uint256"}],"name":"Approval","type":"event"}]'  # noqa
uniswapv2_abi = '[{"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"}],"name":"getAmountsOut","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"view","type":"function"}]'  # noqa
uniswapv2_address = Web3.to_checksum_address("0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D")
uniswapv2_factory_abi = '[{"constant":true,"inputs":[{"internalType":"address","name":"","type":"address"},{"internalType":"address","name":"","type":"address"}],"name":"getPair","outputs":[{"internalType":"address","name":"","type":"address"}],"payable":false,"stateMutability":"view","type":"function"}]'  # noqa
uniswapv2_factory_address = Web3.to_checksum_address("0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f")

uniswapv3_quoter_address = Web3.to_checksum_address("0x61fFE014bA17989E743c5F6cB21bF9697530B21e")
uniswapv3_quoter_abi = '[{"inputs":[{"internalType":"bytes","name":"path","type":"bytes"},{"internalType":"uint256","name":"amountIn","type":"uint256"}],"name":"quoteExactInput","outputs":[{"internalType":"uint256","name":"amountOut","type":"uint256"},{"internalType":"uint160[]","name":"sqrtPriceX96AfterList","type":"uint160[]"},{"internalType":"uint32[]","name":"initializedTicksCrossedList","type":"uint32[]"},{"internalType":"uint256","name":"gasEstimate","type":"uint256"}],"stateMutability":"nonpayable","type":"function"}]'  # noqa
uniswapv3_factory_address = Web3.to_checksum_address("0x1F98431c8aD98523631AE4a59f267346ea31F984")
uniswapv3_factory_abi = '[{"inputs":[{"internalType":"address","name":"","type":"address"},{"internalType":"address","name":"","type":"address"},{"internalType":"uint24","name":"","type":"uint24"}],"name":"getPool","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"}]'  # noqa

pivot_tokens: Dict[int, Tuple[Token, ...]] = {
    1: (  # Ethereum
        Token(Web3.to_checksum_address("0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"), "USDC", 6),
        Token(Web3.to_checksum_address("0xdac17f958d2ee523a2206206994597c13d831ec7"), "USDT", 6),
        Token(Web3.to_checksum_address("0x6b175474e89094c44da98b954eedeac495271d0f"), "DAI", 18),
        Token(Web3.to_checksum_address("0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"), "WETH", 18),
    ),
    1337: (  # Ganache for Ethereum
        Token(Web3.to_checksum_address("0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"), "USDC", 6),
        Token(Web3.to_checksum_address("0xdac17f958d2ee523a2206206994597c13d831ec7"), "USDT", 6),
        Token(Web3.to_checksum_address("0x6b175474e89094c44da98b954eedeac495271d0f"), "DAI", 18),
        Token(Web3.to_checksum_address("0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"), "WETH", 18),
    ),
}

v3_pool_fees = (100, 500, 3000, 10000)
weight_combinations = tuple((i, j) for i in range(10, 100, 10) for j in range(10, 100, 10) if i + j == 100 and i <= j)

irrelevant_value_filter_multiplier = 0.9
