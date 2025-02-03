import asyncio
import logging
import os
from pprint import pp
import subprocess
import time

from uniswap_universal_router_decoder import RouterCodec
from web3 import AsyncWeb3

from uniswap_smart_path import (
    SmartPath,
    SmartRateLimiter,
)


web3_provider = os.environ['WEB3_HTTP_PROVIDER_URL_ETHEREUM_MAINNET']
w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider("http://127.0.0.1:8545", {"timeout": 40}))
chain_id = 1337
block_number = 16961688


uniswapv2_abi = '[{"inputs":[{"internalType":"address","name":"_factory","type":"address"},{"internalType":"address","name":"_WETH","type":"address"}],"stateMutability":"nonpayable","type":"constructor"},{"inputs":[],"name":"WETH","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"tokenA","type":"address"},{"internalType":"address","name":"tokenB","type":"address"},{"internalType":"uint256","name":"amountADesired","type":"uint256"},{"internalType":"uint256","name":"amountBDesired","type":"uint256"},{"internalType":"uint256","name":"amountAMin","type":"uint256"},{"internalType":"uint256","name":"amountBMin","type":"uint256"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"addLiquidity","outputs":[{"internalType":"uint256","name":"amountA","type":"uint256"},{"internalType":"uint256","name":"amountB","type":"uint256"},{"internalType":"uint256","name":"liquidity","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"token","type":"address"},{"internalType":"uint256","name":"amountTokenDesired","type":"uint256"},{"internalType":"uint256","name":"amountTokenMin","type":"uint256"},{"internalType":"uint256","name":"amountETHMin","type":"uint256"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"addLiquidityETH","outputs":[{"internalType":"uint256","name":"amountToken","type":"uint256"},{"internalType":"uint256","name":"amountETH","type":"uint256"},{"internalType":"uint256","name":"liquidity","type":"uint256"}],"stateMutability":"payable","type":"function"},{"inputs":[],"name":"factory","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountOut","type":"uint256"},{"internalType":"uint256","name":"reserveIn","type":"uint256"},{"internalType":"uint256","name":"reserveOut","type":"uint256"}],"name":"getAmountIn","outputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"}],"stateMutability":"pure","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"reserveIn","type":"uint256"},{"internalType":"uint256","name":"reserveOut","type":"uint256"}],"name":"getAmountOut","outputs":[{"internalType":"uint256","name":"amountOut","type":"uint256"}],"stateMutability":"pure","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountOut","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"}],"name":"getAmountsIn","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"}],"name":"getAmountsOut","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountA","type":"uint256"},{"internalType":"uint256","name":"reserveA","type":"uint256"},{"internalType":"uint256","name":"reserveB","type":"uint256"}],"name":"quote","outputs":[{"internalType":"uint256","name":"amountB","type":"uint256"}],"stateMutability":"pure","type":"function"},{"inputs":[{"internalType":"address","name":"tokenA","type":"address"},{"internalType":"address","name":"tokenB","type":"address"},{"internalType":"uint256","name":"liquidity","type":"uint256"},{"internalType":"uint256","name":"amountAMin","type":"uint256"},{"internalType":"uint256","name":"amountBMin","type":"uint256"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"removeLiquidity","outputs":[{"internalType":"uint256","name":"amountA","type":"uint256"},{"internalType":"uint256","name":"amountB","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"token","type":"address"},{"internalType":"uint256","name":"liquidity","type":"uint256"},{"internalType":"uint256","name":"amountTokenMin","type":"uint256"},{"internalType":"uint256","name":"amountETHMin","type":"uint256"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"removeLiquidityETH","outputs":[{"internalType":"uint256","name":"amountToken","type":"uint256"},{"internalType":"uint256","name":"amountETH","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"token","type":"address"},{"internalType":"uint256","name":"liquidity","type":"uint256"},{"internalType":"uint256","name":"amountTokenMin","type":"uint256"},{"internalType":"uint256","name":"amountETHMin","type":"uint256"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"removeLiquidityETHSupportingFeeOnTransferTokens","outputs":[{"internalType":"uint256","name":"amountETH","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"token","type":"address"},{"internalType":"uint256","name":"liquidity","type":"uint256"},{"internalType":"uint256","name":"amountTokenMin","type":"uint256"},{"internalType":"uint256","name":"amountETHMin","type":"uint256"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"},{"internalType":"bool","name":"approveMax","type":"bool"},{"internalType":"uint8","name":"v","type":"uint8"},{"internalType":"bytes32","name":"r","type":"bytes32"},{"internalType":"bytes32","name":"s","type":"bytes32"}],"name":"removeLiquidityETHWithPermit","outputs":[{"internalType":"uint256","name":"amountToken","type":"uint256"},{"internalType":"uint256","name":"amountETH","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"token","type":"address"},{"internalType":"uint256","name":"liquidity","type":"uint256"},{"internalType":"uint256","name":"amountTokenMin","type":"uint256"},{"internalType":"uint256","name":"amountETHMin","type":"uint256"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"},{"internalType":"bool","name":"approveMax","type":"bool"},{"internalType":"uint8","name":"v","type":"uint8"},{"internalType":"bytes32","name":"r","type":"bytes32"},{"internalType":"bytes32","name":"s","type":"bytes32"}],"name":"removeLiquidityETHWithPermitSupportingFeeOnTransferTokens","outputs":[{"internalType":"uint256","name":"amountETH","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"tokenA","type":"address"},{"internalType":"address","name":"tokenB","type":"address"},{"internalType":"uint256","name":"liquidity","type":"uint256"},{"internalType":"uint256","name":"amountAMin","type":"uint256"},{"internalType":"uint256","name":"amountBMin","type":"uint256"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"},{"internalType":"bool","name":"approveMax","type":"bool"},{"internalType":"uint8","name":"v","type":"uint8"},{"internalType":"bytes32","name":"r","type":"bytes32"},{"internalType":"bytes32","name":"s","type":"bytes32"}],"name":"removeLiquidityWithPermit","outputs":[{"internalType":"uint256","name":"amountA","type":"uint256"},{"internalType":"uint256","name":"amountB","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountOut","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapETHForExactTokens","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"payable","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountOutMin","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapExactETHForTokens","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"payable","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountOutMin","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapExactETHForTokensSupportingFeeOnTransferTokens","outputs":[],"stateMutability":"payable","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"amountOutMin","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapExactTokensForETH","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"amountOutMin","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapExactTokensForETHSupportingFeeOnTransferTokens","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"amountOutMin","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapExactTokensForTokens","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"amountOutMin","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapExactTokensForTokensSupportingFeeOnTransferTokens","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountOut","type":"uint256"},{"internalType":"uint256","name":"amountInMax","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapTokensForExactETH","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountOut","type":"uint256"},{"internalType":"uint256","name":"amountInMax","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapTokensForExactTokens","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"nonpayable","type":"function"},{"stateMutability":"payable","type":"receive"}]'  # noqa
uniswapv2_address = AsyncWeb3.to_checksum_address("0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D")
uniswapv2 = w3.eth.contract(uniswapv2_address, abi=uniswapv2_abi)
uniswapv3_quoter_address = AsyncWeb3.to_checksum_address("0x61fFE014bA17989E743c5F6cB21bF9697530B21e")
uniswapv3_quoter_abi = '[{"inputs":[{"internalType":"address","name":"_factory","type":"address"},{"internalType":"address","name":"_WETH9","type":"address"}],"stateMutability":"nonpayable","type":"constructor"},{"inputs":[],"name":"WETH9","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"factory","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"bytes","name":"path","type":"bytes"},{"internalType":"uint256","name":"amountIn","type":"uint256"}],"name":"quoteExactInput","outputs":[{"internalType":"uint256","name":"amountOut","type":"uint256"},{"internalType":"uint160[]","name":"sqrtPriceX96AfterList","type":"uint160[]"},{"internalType":"uint32[]","name":"initializedTicksCrossedList","type":"uint32[]"},{"internalType":"uint256","name":"gasEstimate","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"components":[{"internalType":"address","name":"tokenIn","type":"address"},{"internalType":"address","name":"tokenOut","type":"address"},{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint24","name":"fee","type":"uint24"},{"internalType":"uint160","name":"sqrtPriceLimitX96","type":"uint160"}],"internalType":"struct IQuoterV2.QuoteExactInputSingleParams","name":"params","type":"tuple"}],"name":"quoteExactInputSingle","outputs":[{"internalType":"uint256","name":"amountOut","type":"uint256"},{"internalType":"uint160","name":"sqrtPriceX96After","type":"uint160"},{"internalType":"uint32","name":"initializedTicksCrossed","type":"uint32"},{"internalType":"uint256","name":"gasEstimate","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"bytes","name":"path","type":"bytes"},{"internalType":"uint256","name":"amountOut","type":"uint256"}],"name":"quoteExactOutput","outputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint160[]","name":"sqrtPriceX96AfterList","type":"uint160[]"},{"internalType":"uint32[]","name":"initializedTicksCrossedList","type":"uint32[]"},{"internalType":"uint256","name":"gasEstimate","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"components":[{"internalType":"address","name":"tokenIn","type":"address"},{"internalType":"address","name":"tokenOut","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"},{"internalType":"uint24","name":"fee","type":"uint24"},{"internalType":"uint160","name":"sqrtPriceLimitX96","type":"uint160"}],"internalType":"struct IQuoterV2.QuoteExactOutputSingleParams","name":"params","type":"tuple"}],"name":"quoteExactOutputSingle","outputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint160","name":"sqrtPriceX96After","type":"uint160"},{"internalType":"uint32","name":"initializedTicksCrossed","type":"uint32"},{"internalType":"uint256","name":"gasEstimate","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"int256","name":"amount0Delta","type":"int256"},{"internalType":"int256","name":"amount1Delta","type":"int256"},{"internalType":"bytes","name":"path","type":"bytes"}],"name":"uniswapV3SwapCallback","outputs":[],"stateMutability":"view","type":"function"}]'  # noqa
uniswapv3_quoter = w3.eth.contract(uniswapv3_quoter_address, abi=uniswapv3_quoter_abi)

weth_address = AsyncWeb3.to_checksum_address("0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2")
usdc_address = AsyncWeb3.to_checksum_address("0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48")
crv_address = AsyncWeb3.to_checksum_address("0xd533a949740bb3306d119cc777fa900ba034cd52")
mkr_address = AsyncWeb3.to_checksum_address("0x9f8f72aa9304c8b593d555f12ef6589cc3a579a2")
uni_address = AsyncWeb3.to_checksum_address("0x1f9840a85d5af5bf1d1762f925bdaddc4201f984")


codec = RouterCodec()
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("web3").setLevel(logging.WARNING)
logging.getLogger("uniswap_smart_path._datastructures").setLevel(logging.WARNING)


def launch_ganache():
    ganache_process = subprocess.Popen(
        f"""ganache
        --logging.quiet='true'
        --fork.url='{web3_provider}'
        --fork.blockNumber='{block_number}'
        --miner.defaultGasPrice='15000000000'
        """.replace("\n", " "),
        shell=True,
    )
    time.sleep(3)
    parent_id = ganache_process.pid
    return parent_id


def kill_processes(parent_id):
    processes = [str(parent_id), ]
    pgrep_process = subprocess.run(
        f"pgrep -P {parent_id}", shell=True, text=True, capture_output=True
    ).stdout.strip("\n")
    children_ids = pgrep_process.split("\n") if len(pgrep_process) > 0 else []
    processes.extend(children_ids)
    subprocess.run(f"kill {' '.join(processes)}", shell=True, text=True, capture_output=True)


async def check_initialization():
    assert await w3.eth.chain_id == chain_id  # 1337
    assert await w3.eth.block_number == block_number + 1
    print(" => Initialization: OK")


async def get_weth_usdc_path(smart_path, smart_path_v2_only, smart_path_v3_only):
    print(" => Getting WETH USDC path")
    amount_in = 100 * 10**18
    path = await smart_path.get_swap_in_path(amount_in, weth_address, usdc_address)  # noqa
    pp(f"{path=}")
    print(path[0]["estimate"])

    path_v2_only = await smart_path_v2_only.get_swap_in_path(amount_in, weth_address, usdc_address)  # noqa
    pp(f"{path_v2_only=}")

    path_v3_only = await smart_path_v3_only.get_swap_in_path(amount_in, weth_address, usdc_address)  # noqa
    pp(f"{path_v3_only=}")

    uniswapv2_value = (await uniswapv2.functions.getAmountsOut(amount_in, [weth_address, usdc_address]).call())[-1]
    print(uniswapv2_value)
    assert path[0]["estimate"] > uniswapv2_value, f"actual values: {path[0]['estimate']}, {uniswapv2_value}"

    encoded_v3_path_100 = codec.encode.v3_path("V3_SWAP_EXACT_IN", [weth_address, 100, usdc_address])
    uniswapv3_value_100 = (await uniswapv3_quoter.functions.quoteExactInput(encoded_v3_path_100, amount_in).call())[0]
    print(uniswapv3_value_100)
    assert path[0]["estimate"] > uniswapv3_value_100

    encoded_v3_path_500 = codec.encode.v3_path("V3_SWAP_EXACT_IN", [weth_address, 500, usdc_address])
    uniswapv3_value_500 = (await uniswapv3_quoter.functions.quoteExactInput(encoded_v3_path_500, amount_in).call())[0]
    print(uniswapv3_value_500)
    assert path[0]["estimate"] == uniswapv3_value_500

    encoded_v3_path_3000 = codec.encode.v3_path("V3_SWAP_EXACT_IN", [weth_address, 3000, usdc_address])
    uniswapv3_value_3000 = (await uniswapv3_quoter.functions.quoteExactInput(encoded_v3_path_3000, amount_in).call())[0]
    print(uniswapv3_value_3000)
    assert path[0]["estimate"] > uniswapv3_value_3000

    assert path_v2_only[0]["estimate"] == uniswapv2_value
    assert path_v3_only == path

    print(" => WETH USDC path: OK")


async def get_crv_mkr_path(smart_path, smart_path_v2_only, smart_path_v3_only):
    print(" => Getting CRV MKR path")
    amount_in = 100_000 * 10**18
    path = await smart_path.get_swap_in_path(amount_in, crv_address, mkr_address)  # noqa
    pp(path)
    print(path[0]["estimate"])

    path_v2_only = await smart_path_v2_only.get_swap_in_path(amount_in, crv_address, mkr_address)  # noqa
    pp(f"{path_v2_only=}")

    path_v3_only = await smart_path_v3_only.get_swap_in_path(amount_in, crv_address, mkr_address)  # noqa
    pp(f"{path_v3_only=}")

    uniswapv2_value = (await uniswapv2.functions.getAmountsOut(amount_in, [crv_address, weth_address, mkr_address]).call())[-1]  # noqa
    print(uniswapv2_value)
    assert path[0]["estimate"] > uniswapv2_value

    encoded_v3_path_3000 = codec.encode.v3_path("V3_SWAP_EXACT_IN", [crv_address, 3000, weth_address, 3000, mkr_address])  # noqa
    uniswapv3_value_3000 = (await uniswapv3_quoter.functions.quoteExactInput(encoded_v3_path_3000, amount_in).call())[0]
    print(uniswapv3_value_3000)
    assert path[0]["estimate"] == uniswapv3_value_3000

    assert path_v2_only[0]["estimate"] == uniswapv2_value
    assert path_v3_only == path

    print(" => CRV MKR path: OK")


async def get_uni_weth_path(smart_path, smart_path_v2_only, smart_path_v3_only):
    print(" => Getting UNI WETH path")
    amount_in = 25_000 * 10 ** 18
    path = await smart_path.get_swap_in_path(amount_in, uni_address, weth_address)  # noqa
    pp(path)
    print(path[0]["estimate"], path[1]["estimate"])
    assert path[0]["weight"] == 10
    assert path[1]["weight"] == 90

    path_v2_only = await smart_path_v2_only.get_swap_in_path(amount_in, uni_address, weth_address)  # noqa
    pp(f"{path_v2_only=}")

    path_v3_only = await smart_path_v3_only.get_swap_in_path(amount_in, uni_address, weth_address)  # noqa
    pp(f"{path_v3_only=}")

    uniswapv2_value = (await uniswapv2.functions.getAmountsOut(amount_in, [uni_address, weth_address]).call())[-1]
    print(uniswapv2_value)
    assert path[0]["estimate"] + path[1]["estimate"] > uniswapv2_value

    encoded_v3_path_3000 = codec.encode.v3_path("V3_SWAP_EXACT_IN", [uni_address, 3000, weth_address])
    uniswapv3_value_3000 = (await uniswapv3_quoter.functions.quoteExactInput(encoded_v3_path_3000, amount_in).call())[0]
    print(uniswapv3_value_3000)
    assert path[0]["estimate"] + path[1]["estimate"] > uniswapv3_value_3000

    assert path[0]["estimate"] + path[1]["estimate"] > path_v3_only[0]["estimate"] > path_v2_only[0]["estimate"] > 0

    print(" => UNI WETH path: OK")


async def launch_integration_tests():
    print("------------------------------------------")
    print("| Launching integration tests            |")
    print("------------------------------------------")

    smart_path = await SmartPath.create(w3)
    smart_path_v2_only = await SmartPath.create_v2_only(w3)
    smart_path_v3_only = await SmartPath.create_v3_only(w3)

    await check_initialization()
    await asyncio.sleep(2)
    await get_weth_usdc_path(smart_path, smart_path_v2_only, smart_path_v3_only)
    await asyncio.sleep(5)
    await get_crv_mkr_path(smart_path, smart_path_v2_only, smart_path_v3_only)
    await asyncio.sleep(5)
    await get_uni_weth_path(smart_path, smart_path_v2_only, smart_path_v3_only)
    await asyncio.sleep(5)

    print("\nTest SmartPath with SmartRateLimiter")
    smart_rate_limiter = SmartRateLimiter(1, max_credits=1000, method_credits={"eth_call": 80})
    smart_path_rl = await SmartPath.create(w3, smart_rate_limiter=smart_rate_limiter)
    smart_path_v2_only_rl = await SmartPath.create_v2_only(w3, smart_rate_limiter=smart_rate_limiter)
    smart_path_v3_only_rl = await SmartPath.create_v3_only(w3, smart_rate_limiter=smart_rate_limiter)
    await get_uni_weth_path(smart_path_rl, smart_path_v2_only_rl, smart_path_v3_only_rl)
    await asyncio.sleep(5)


def print_success_message():
    print("------------------------------------------")
    print("| Integration tests are successful !! :) |")
    print("------------------------------------------")


def main():
    ganache_pid = launch_ganache()
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(launch_integration_tests())
        print_success_message()
    finally:
        kill_processes(ganache_pid)


if __name__ == "__main__":
    main()
