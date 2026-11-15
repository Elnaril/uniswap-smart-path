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
from uniswap_smart_path._constants import (
    uniswapv2_abi,
    uniswapv2_address,
    uniswapv3_quoter_abi,
    uniswapv3_quoter_address,
)


web3_provider = os.environ['RPC_ENDPOINT']
w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider("http://127.0.0.1:8545", {"timeout": 40}))
chain_id = 1
block_number = 26420289


uniswapv2 = w3.eth.contract(uniswapv2_address, abi=uniswapv2_abi)
uniswapv3_quoter = w3.eth.contract(uniswapv3_quoter_address, abi=uniswapv3_quoter_abi)

weth_address = AsyncWeb3.to_checksum_address("0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2")
uni_address = AsyncWeb3.to_checksum_address("0x1f9840a85d5af5bf1d1762f925bdaddc4201f984")


codec = RouterCodec()
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("web3").setLevel(logging.WARNING)
logging.getLogger("uniswap_smart_path._datastructures").setLevel(logging.WARNING)


def launch_anvil():
    anvil_process = subprocess.Popen(
        " ".join(
            [
                "anvil",
                f"--fork-url {web3_provider}",
                f"--fork-block-number {block_number}",
                "--mnemonic-seed-unsafe 8721345628937456298",
            ]
        ),
        shell=True,
    )
    time.sleep(2)
    parent_id = anvil_process.pid
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
    assert await w3.eth.chain_id == chain_id  # 1
    assert await w3.eth.block_number == block_number
    print(" => Initialization: OK")


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

    smart_rate_limiter = SmartRateLimiter(1, max_credits=300, method_credits={"eth_call": 26, "eth_chainId": 1})
    smart_path = await SmartPath.create(w3, smart_rate_limiter=smart_rate_limiter)
    smart_path_v2_only = await SmartPath.create_v2_only(w3, smart_rate_limiter=smart_rate_limiter)
    smart_path_v3_only = await SmartPath.create_v3_only(w3, smart_rate_limiter=smart_rate_limiter)

    await check_initialization()
    await get_uni_weth_path(smart_path, smart_path_v2_only, smart_path_v3_only)


def print_success_message():
    print("------------------------------------------")
    print("| Integration tests are successful !! :) |")
    print("------------------------------------------")


def main():
    anvil_pid = launch_anvil()
    try:
        asyncio.run(launch_integration_tests())
        print_success_message()
    finally:
        kill_processes(anvil_pid)


if __name__ == "__main__":
    main()
