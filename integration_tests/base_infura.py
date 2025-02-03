import asyncio
import os
from pprint import pp

from web3 import AsyncWeb3

from uniswap_smart_path import (
    SmartPath,
    SmartRateLimiter,
)


base_usdc_address = AsyncWeb3.to_checksum_address("0x833589fcd6edb6e08f4c7c32d4f71b54bda02913")
base_weth_address = AsyncWeb3.to_checksum_address("0x4200000000000000000000000000000000000006")
base_wbtc_address = AsyncWeb3.to_checksum_address("0xcbb7c0000ab88b473b1f5afd9ef808440eed33bf")


# - Quoters & Factories
# -- Uniswap V2
base_uniswapv2_router_address = AsyncWeb3.to_checksum_address("0x4752ba5dbc23f44d87826276bf6fd6b1c372ad24")
base_uniswapv2_factory_address = AsyncWeb3.to_checksum_address("0x8909Dc15e40173Ff4699343b6eB8132c65e18eC6")

# -- Uniswap V3
base_uniswapv3_quoter_address = AsyncWeb3.to_checksum_address("0x3d4e44Eb1374240CE5F1B871ab261CD16335B76a")
base_uniswapv3_factory_address = AsyncWeb3.to_checksum_address("0x33128a8fC17869897dcE68Ed026d694621f6FDfD")


amount_in = 10 * 10**18


async def run(_aw3, _smart_rate_limiter):
    pivot_tokens = (
        base_usdc_address,
        base_weth_address,
    )

    smart_path = await SmartPath.create_custom(
        _aw3,
        smart_rate_limiter=_smart_rate_limiter,
        pivot_tokens=pivot_tokens,
        v3_pool_fees=(100, 500, 3000, 10000),
        v2_router=base_uniswapv2_router_address,
        v2_factory=base_uniswapv2_factory_address,
        v3_quoter=base_uniswapv3_quoter_address,
        v3_factory=base_uniswapv3_factory_address,
    )

    path = await smart_path.get_swap_in_path(amount_in, base_weth_address, base_wbtc_address)
    print("Base result:")
    pp(path)
    print("\n")


if __name__ == "__main__":
    aw3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(os.environ['BASE_RPC_URL']))
    smart_rate_limiter = SmartRateLimiter(1, max_credits=500, method_credits={"eth_call": 80})
    asyncio.run(run(aw3, smart_rate_limiter))
