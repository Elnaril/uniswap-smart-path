import asyncio
import logging
import os
from pprint import pp
import subprocess
import time

from uniswap_universal_router_decoder import RouterCodec
from web3 import AsyncWeb3

from uniswap_smart_path import SmartPath


web3_provider = os.environ['WEB3_HTTP_PROVIDER_URL_BSC_MAINNET']
w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider("http://127.0.0.1:8545", {"timeout": 40}))
chain_id = 1337
block_number = 33368277

smart_path = smart_path_v2_only = smart_path_v3_only = None

pancakeswapv2_address = AsyncWeb3.to_checksum_address("0x10ED43C718714eb63d5aA57B78B54704E256024E")
pancakeswapv2_factory = AsyncWeb3.to_checksum_address("0xcA143Ce32Fe78f1f7019d7d551a6402fC5350c73")
pancakeswapv3_quoter_address = AsyncWeb3.to_checksum_address("0xB048Bbc1Ee6b733FFfCFb9e9CeF7375518e25997")
pancakeswapv3_factory = AsyncWeb3.to_checksum_address("0x0BFbCF9fa4f9C56B0F40a671Ad40E0805A091865")

wbnb_address = AsyncWeb3.to_checksum_address("0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c")
usdc_address = AsyncWeb3.to_checksum_address("0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d")
usdt_address = AsyncWeb3.to_checksum_address("0x55d398326f99059fF775485246999027B3197955")
dai_address = AsyncWeb3.to_checksum_address("0x1AF3F329e8BE154074D8769D1FFa4eE058B1DBc3")
uni_address = AsyncWeb3.to_checksum_address("0xBf5140A22578168FD562DCcF235E5D43A02ce9B1")

pivot_tokens = (wbnb_address, usdt_address, usdc_address, dai_address)
v3_pool_fees = (100, 500, 2500, 10000)


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


async def get_uni_dai_path():
    print(" => Getting UNI DAI path")
    amount_in = 100 * 10**18
    path = await smart_path.get_swap_in_path(amount_in, uni_address, dai_address)  # noqa
    pp(f"{path=}")
    print(path[0]["estimate"])
    assert path[0]["estimate"] == 399452796099215583034
    print(" => UNI DAI path: OK")


async def get_wbnb_usdt_path():
    print(" => Getting WBNB USDT path")
    amount_in = 100 * 10**18
    path = await smart_path.get_swap_in_path(amount_in, wbnb_address, usdt_address)  # noqa
    pp(f"{path=}")
    print(path[0]["estimate"])
    assert path[0]["estimate"] == 25260332135985986979008
    print(" => WBNB USDT path: OK")


async def launch_integration_tests():
    print("------------------------------------------")
    print("| Launching integration tests            |")
    print("------------------------------------------")

    global smart_path
    smart_path = await SmartPath.create_custom(
        w3,
        pivot_tokens=pivot_tokens,
        v3_pool_fees=v3_pool_fees,
        v2_router=pancakeswapv2_address,
        v2_factory=pancakeswapv2_factory,
        v3_quoter=pancakeswapv3_quoter_address,
        v3_factory=pancakeswapv3_factory,
    )

    await check_initialization()
    await asyncio.sleep(2)
    await get_uni_dai_path()
    await asyncio.sleep(2)
    await get_wbnb_usdt_path()
    await asyncio.sleep(2)


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
