import pytest
from web3 import Web3
from web3.exceptions import BadFunctionCallOutput
from web3.types import Wei

from uniswap_smart_path import SmartPath
from uniswap_smart_path._constants import (  # noqa
    irrelevant_value_filter_multiplier,
    weight_combinations,
)
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


async def test_create(w3, rpc_endpoint, uniswapv2_address, uniswapv3_quoter_address):
    sp_init_w3 = SmartPath(w3=w3)

    assert V2PoolPath.contract.address == uniswapv2_address == sp_init_w3.uniswapv2.address
    assert V3PoolPath.contract.address == uniswapv3_quoter_address == sp_init_w3.quoter.address

    sp_create_w3 = await SmartPath.create(w3=w3)
    sp_create_rpc = await SmartPath.create(rpc_endpoint=rpc_endpoint)

    assert sp_init_w3.chain_id == sp_create_w3.chain_id == sp_create_rpc.chain_id == 1

    assert len(sp_create_w3.v3_pools_fees_x_pivots) == 16
    assert (tokens["WETH"], 3000) in sp_create_w3.v3_pools_fees_x_pivots

    with pytest.raises(ValueError):
        _ = await SmartPath.create()


@pytest.mark.parametrize(
    "token, expected_exception",
    (
        (tokens["WETH"], None),
        (tokens["FAKE"], BadFunctionCallOutput),
        (Token(Web3.to_checksum_address("0" * 40), "NotAToken", 0), BadFunctionCallOutput)
    )
)
async def test_get_token(token, expected_exception, w3):
    smart_path = await SmartPath.create(w3)
    if expected_exception:
        with pytest.raises(expected_exception):
            _ = await smart_path._get_token(token.address)
    else:
        assert token == await smart_path._get_token(token.address)


@pytest.mark.parametrize(
    "token0, token1, expected_result",
    (
        (tokens["WETH"], tokens["USDC"], True),
        (tokens["WETH"], tokens["FAKE"], False),
        (tokens["WETH"], Token(Web3.to_checksum_address("0" * 40), "NotAToken", 0), False),
        (Token(Web3.to_checksum_address("0" * 40), "NotAToken", 0), tokens["USDC"], False),
    )
)
async def test_v2_pool_exist(token0, token1, expected_result, w3):
    smart_path = await SmartPath.create(w3)
    assert expected_result == await smart_path._v2_pool_exist(token0, token1)


@pytest.mark.parametrize(
    "token0, token1, fees, expected_result",
    (
        (tokens["WETH"], tokens["USDC"], 3000, True),
        (tokens["WETH"], tokens["FAKE"], 3000, False),
        (tokens["WETH"], Token(Web3.to_checksum_address("0" * 40), "NotAToken", 0), 3000, False),
        (Token(Web3.to_checksum_address("0" * 40), "NotAToken", 0), tokens["USDC"], 3000, False),
    )
)
async def test_v3_pool_exist(token0, token1, fees, expected_result, w3):
    smart_path = await SmartPath.create(w3)
    assert expected_result == await smart_path._v3_pool_exist(token0, token1, fees)


@pytest.mark.parametrize(
    "token0, token1, pivot, expected_result",
    (
        (tokens["DAI"], tokens["WETH"], tokens["USDC"], True),
        (tokens["DAI"], tokens["WETH"], tokens["FAKE"], False),
    )
)
async def test_v2_pools_exists_for_pivot_token(token0, token1, pivot, expected_result, w3):
    smart_path = await SmartPath.create(w3)
    assert expected_result == await smart_path._v2_pools_exists_for_pivot_token(token0, token1, pivot)


expected_v2_path_list_01 = [
    ('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2', '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
    ('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2', '0xdAC17F958D2ee523a2206206994597C13D831ec7', '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),  # noqa
    ('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2', '0x6B175474E89094C44Da98b954EedeAC495271d0F', '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),  # noqa
]
expected_v2_path_list_02 = [
    ('0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984', '0x514910771AF9Ca656af840dff83E8264EcF986CA'),
    ('0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984', '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48', '0x514910771AF9Ca656af840dff83E8264EcF986CA'),  # noqa
    ('0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984', '0xdAC17F958D2ee523a2206206994597C13D831ec7', '0x514910771AF9Ca656af840dff83E8264EcF986CA'),  # noqa
    ('0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984', '0x6B175474E89094C44Da98b954EedeAC495271d0F', '0x514910771AF9Ca656af840dff83E8264EcF986CA'),  # noqa
    ('0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984', '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2', '0x514910771AF9Ca656af840dff83E8264EcF986CA'),  # noqa
]


@pytest.mark.parametrize(
    "token_in, token_out, expected_result",
    (
        (tokens["WETH"], tokens["USDC"], expected_v2_path_list_01),
        (tokens["UNI"], tokens["LINK"], expected_v2_path_list_02),
        (tokens["FAKE"], tokens["WETH"], []),
    )
)
async def test_build_v2_path_list(token_in, token_out, expected_result, w3):
    smart_path = await SmartPath.create(w3)
    v2_pool_path_list = await smart_path._build_v2_path_list(token_in, token_out)
    assert len(v2_pool_path_list) == len(expected_result)
    for pool in v2_pool_path_list:
        assert pool.get_path() in expected_result


@pytest.mark.parametrize(
    "token_in, is_token_in, expected_number_of_results",
    (
        (tokens["USDC"], True, 12),
        (tokens["WETH"], True, 12),
        (tokens["UNI"], False, 13),
        (tokens["FAKE"], True, 0),
    )
)
async def test_build_v3_base_pool_list(token_in, is_token_in, expected_number_of_results, w3):
    smart_path = await SmartPath.create(w3)
    v3_base_pool_list = await smart_path._get_v3_base_pools(token_in, is_token_in)
    assert len(v3_base_pool_list) == expected_number_of_results
    for pool in v3_base_pool_list:
        assert pool.token_in != pool.token_out
        assert token_in == pool.token_in if is_token_in else pool.token_out


@pytest.mark.parametrize(
    "token_in, token_out, expected_number_of_results, expected_fees",
    (
        (tokens["WETH"], tokens["USDC"], 4, (100, 500, 3000, 10000)),
        (tokens["UNI"], tokens["LINK"], 2, (3000, 10000)),
        (tokens["WETH"], tokens["FAKE"], 0, ()),
    )
)
async def test_get_v3_one_hop_pools(token_in, token_out, expected_number_of_results, expected_fees, w3):
    smart_path = await SmartPath.create(w3)
    v3_one_hop_pools = await smart_path._get_v3_one_hop_pools(token_in, token_out)
    assert len(v3_one_hop_pools) == expected_number_of_results
    for pool in v3_one_hop_pools:
        assert token_in == pool.token_in
        assert token_out == pool.token_out
        assert pool.pool_fee in expected_fees


@pytest.mark.parametrize(
    "token_in, token_out, expected_number_of_results",
    (
        (tokens["WETH"], tokens["USDC"], 36),
        (tokens["UNI"], tokens["LINK"], 35),
    )
)
async def test_build_v3_path_list(token_in, token_out, expected_number_of_results, w3):
    smart_path = await SmartPath.create(w3)
    v3_pool_paths = await smart_path._build_v3_path_list(token_in, token_out)
    assert len(v3_pool_paths) == expected_number_of_results
    for pool in v3_pool_paths:
        assert pool.pools[0].token_in != pool.pools[0].token_out
        assert pool.pools[-1].token_in != pool.pools[-1].token_out
        pool_path = pool.get_path()
        assert pool_path[0] == token_in.address
        assert pool_path[-1] == token_out.address


v2_pool_path_1 = V2PoolPath([V2OrderedPool(tokens["WETH"], tokens["USDC"])])
weighted_path_1 = WeightedPath(RouterFunction.V2_SWAP_EXACT_IN, v2_pool_path_1, 100)
mixed_path_1 = MixedWeightedPath([weighted_path_1, ])
best_value = 1800 * 10**6
mixed_path_1.total_value = Wei(best_value)

v3_pool_path_2 = V3PoolPath([V3OrderedPool(tokens["WETH"], 3000, tokens["USDC"])])
weighted_path_2 = WeightedPath(RouterFunction.V3_SWAP_EXACT_IN, v3_pool_path_2, 100)
mixed_path_2 = MixedWeightedPath([weighted_path_2, ])
mixed_path_2.total_value = Wei(int(best_value * (irrelevant_value_filter_multiplier - 0.1)))

v3_pool_path_3 = V3PoolPath([V3OrderedPool(tokens["WETH"], 500, tokens["USDC"])])
weighted_path_3 = WeightedPath(RouterFunction.V3_SWAP_EXACT_IN, v3_pool_path_3, 100)
mixed_path_3 = MixedWeightedPath([weighted_path_3, ])
mixed_path_3.total_value = Wei(int(best_value * (irrelevant_value_filter_multiplier + 0.1)))

mixed_weighted_paths = [mixed_path_1, mixed_path_2, mixed_path_3]
expected_mixed_weighted_paths = [mixed_path_1, mixed_path_3]


def test_filter_irrelevant_low_values():
    assert expected_mixed_weighted_paths == SmartPath._filter_irrelevant_low_values(mixed_weighted_paths, best_value)


def test_get_all_mixed_path():
    all_mixed_paths = SmartPath._get_all_mixed_path(mixed_path_3, mixed_path_1)
    for i, mixed_path in enumerate(all_mixed_paths):
        assert mixed_path.weighted_paths[0].router_function == RouterFunction.V3_SWAP_EXACT_IN
        assert mixed_path.weighted_paths[0].pool_path == v3_pool_path_3
        assert mixed_path.weighted_paths[0].weight == weight_combinations[i][0]

        assert mixed_path.weighted_paths[1].router_function == RouterFunction.V2_SWAP_EXACT_IN
        assert mixed_path.weighted_paths[1].pool_path == v2_pool_path_1
        assert mixed_path.weighted_paths[1].weight == weight_combinations[i][1]


@pytest.mark.parametrize(
    "amount, token_in, token_out, expected_estimate",
    (
        (Wei(100 * 10**18), tokens["DAI"], tokens["USDT"], 100 * 10**6),
        (Wei(100 * 10**18), Token(Web3.to_checksum_address("0x1fB90FFC02D01238Cd8AFE3a82B8C65BAC37042f"), "", 18), tokens["USDT"], None),  # noqa
    )
)
async def test_get_swap_in_path(amount, token_in, token_out, expected_estimate, w3):
    smart_path = await SmartPath.create(w3)
    weighted_paths = await smart_path.get_swap_in_path(amount, token_in.address, token_out.address)
    total_estimate = 0
    for path in weighted_paths:
        total_estimate += path["estimate"]
    if expected_estimate:
        assert expected_estimate * 0.98 < total_estimate < expected_estimate * 1.02
    else:
        assert weighted_paths == ()
