import asyncio
import os
from pprint import pp

from web3 import AsyncWeb3

from uniswap_smart_path import (
    SmartPath,
    SmartRateLimiter,
)


eth_weth_address = AsyncWeb3.to_checksum_address("0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2")
eth_wbtc_address = AsyncWeb3.to_checksum_address("0x2260fac5e5542a773aa44fbcfedf7c193bc2c599")
amount_in = 10 * 10**18


async def run(_aw3, _smart_rate_limiter):
    smart_path = await SmartPath.create(_aw3, smart_rate_limiter=_smart_rate_limiter)

    path = await smart_path.get_swap_in_path(amount_in, eth_weth_address, eth_wbtc_address)
    print("Ethereum result:")
    pp(path)
    print("\n")


if __name__ == "__main__":
    aw3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(os.environ['WEB3_HTTP_PROVIDER_URL_ETHEREUM_MAINNET']))
    smart_rate_limiter = SmartRateLimiter(1, max_credits=500, method_credits={"eth_call": 80})
    asyncio.run(run(aw3, smart_rate_limiter))
