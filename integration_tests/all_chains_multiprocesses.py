import asyncio
from multiprocessing import Pool
import os

from web3 import AsyncWeb3

from integration_tests.base_infura import run as run_base
from integration_tests.eth_infura import run as run_eth
from uniswap_smart_path import SmartRateLimiter


# The below links explain that web3.py supports multiple providers (of the same type) only if they have different URLs.
# However, it seems it does not work neither when the URLs are different.
# Hence the multiprocessing usage in this test
#
# https://github.com/ethereum/web3.py/issues/2814
# https://github.com/ethereum/web3.py/blob/main/docs/providers.rst
# https://github.com/ethereum/web3.py/pull/2861


def eth_worker():
    print("Start eth worker")
    aw3_eth_alchemy = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(os.environ['WEB3_HTTP_PROVIDER_ALCHEMY_ETHEREUM_MAINNET']))
    smart_rate_limiter_alchemy = SmartRateLimiter(1, max_credits=330, method_credits={"eth_call": 26})
    asyncio.run(run_eth(aw3_eth_alchemy, smart_rate_limiter_alchemy))
    print("Stop eth worker")


def base_worker():
    print("Start base worker")
    aw3_base_infura = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(os.environ['BASE_RPC_URL']))
    smart_rate_limiter_infura = SmartRateLimiter(1, max_credits=500, method_credits={"eth_call": 80})
    asyncio.run(run_base(aw3_base_infura, smart_rate_limiter_infura))
    print("Stop base worker")


if __name__ == "__main__":
    with Pool(2) as pool:
        base_result = pool.apply_async(base_worker)
        eth_result = pool.apply_async(eth_worker)

        base_result.wait()
        eth_result.wait()
