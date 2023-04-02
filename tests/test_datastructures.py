import pytest
from web3.types import Wei

from uniswap_smart_path import SmartPath
from uniswap_smart_path._datastructures import (  # noqa
    MixedWeightedPath,
    RouterFunction,
    Token,
    V2OrderedPool,
    V2PoolPath,
    V3OrderedPool,
    V3PoolPath,
    WeightedPath,
)

from .conftest import tokens


@pytest.mark.parametrize(
    "pools, weight, amount_in, expected_path, expected_amount",
    (
            ((V2OrderedPool(tokens["USDC"], tokens["DAI"]), ), 100, 1000 * 10**6, (tokens["USDC"].address, tokens["DAI"].address), 1000 * 10**18),  # noqa
            ((V2OrderedPool(tokens["USDC"], tokens["DAI"]), V2OrderedPool(tokens["DAI"], tokens["USDT"])), 100, 1000 * 10 ** 6, (tokens["USDC"].address, tokens["DAI"].address, tokens["USDT"].address), 1000 * 10 ** 6),  # noqa
    )
)
async def test_v2_pool_path(pools, weight, amount_in, expected_path, expected_amount, w3):
    await SmartPath.create(w3)
    v2_pool_path = V2PoolPath(pools, weight)

    assert expected_path == v2_pool_path.get_path() == v2_pool_path.to_dict()["path"]
    assert 0.95 * expected_amount < await v2_pool_path.get_amount_out(amount_in) < 1.05 * expected_amount


@pytest.mark.parametrize(
    "pools, weight, amount_in, expected_path, expected_amount",
    (
            ((V3OrderedPool(tokens["USDC"], 500, tokens["DAI"]), ), 100, 1000 * 10**6, (tokens["USDC"].address, 500, tokens["DAI"].address), 1000 * 10**18),  # noqa
            ((V3OrderedPool(tokens["USDC"], 100, tokens["DAI"]), V3OrderedPool(tokens["DAI"], 100, tokens["USDT"])), 100, 1000 * 10 ** 6, (tokens["USDC"].address, 100, tokens["DAI"].address, 100, tokens["USDT"].address), 1000 * 10 ** 6),  # noqa
    )
)
async def test_v3_pool_path(pools, weight, amount_in, expected_path, expected_amount, w3):
    await SmartPath.create(w3)
    v3_pool_path = V3PoolPath(pools, weight)

    assert expected_path == v3_pool_path.get_path() == v3_pool_path.to_dict()["path"]
    assert 0.95 * expected_amount < await v3_pool_path.get_amount_out(amount_in) < 1.05 * expected_amount


v2_pool_path_1 = V2PoolPath([V2OrderedPool(tokens["DAI"], tokens["USDC"])])
weighted_path_1 = WeightedPath(RouterFunction.V2_SWAP_EXACT_IN, v2_pool_path_1, 40)

v3_pool_path_2 = V3PoolPath([V3OrderedPool(tokens["DAI"], 500, tokens["USDC"])])
weighted_path_2 = WeightedPath(RouterFunction.V3_SWAP_EXACT_IN, v3_pool_path_2, 60)


async def test_mixed_weighted_path(w3):
    await SmartPath.create(w3)
    mixed_path = MixedWeightedPath([weighted_path_1, weighted_path_2])
    await mixed_path.compute_path_values(Wei(100 * 10**18))
    assert 40 * 10**6 * 0.97 < mixed_path.values[0] < 40 * 10**6 * 1.03
    assert 60 * 10 ** 6 * 0.97 < mixed_path.values[1] < 60 * 10 ** 6 * 1.03
    assert 100 * 10 ** 6 * 0.97 < mixed_path.total_value < 100 * 10 ** 6 * 1.03
