import pytest
from web3 import Web3
from web3.exceptions import BadFunctionCallOutput
from web3.types import Wei

from uniswap_smart_path import (
    SmartPath,
    SmartRateLimiter,
)
import uniswap_smart_path._constants as const  # noqa
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
from uniswap_smart_path.exceptions import SmartPathException

from .conftest import tokens


credit_limiter = SmartRateLimiter(1, max_credits=40, method_credits={"eth_call": 20})
count_limiter = SmartRateLimiter(1, max_count=2)


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

    with pytest.raises(ValueError):
        _ = SmartRateLimiter(1, max_credits=40)

    with pytest.raises(ValueError):
        _ = SmartRateLimiter(1)

    with pytest.raises(NotImplementedError):
        _ = await SmartPath.create(w3=w3, with_gas_estimate=True)


@pytest.mark.parametrize(
    "token, smart_rate_limiter, expected_exception",
    (
        (tokens["WETH"], None, None),
        (tokens["WETH"], credit_limiter, None),
        (tokens["WETH"], count_limiter, None),
        (tokens["MKR"], None, None),
        (tokens["MKR"], credit_limiter, None),
        (tokens["MKR"], count_limiter, None),
        (tokens["FAKE"], None, BadFunctionCallOutput),  # BadFunctionCallOutput because of decimals call
        (Token(Web3.to_checksum_address("0" * 40), "NotAToken", 0), None, BadFunctionCallOutput)
    )
)
async def test_get_token(token, smart_rate_limiter, expected_exception, w3):
    smart_path = await SmartPath.create(w3, smart_rate_limiter=smart_rate_limiter)
    if expected_exception:
        with pytest.raises(expected_exception):
            _ = await smart_path._get_token(token.address, w3)
    else:
        assert token == await smart_path._get_token(token.address, w3)


@pytest.mark.parametrize(
    "token0, token1, smart_rate_limiter, expected_result",
    (
        (tokens["WETH"], tokens["USDC"], None, True),
        (tokens["WETH"], tokens["USDC"], credit_limiter, True),
        (tokens["WETH"], tokens["USDC"], count_limiter, True),
        (tokens["WETH"], tokens["FAKE"], None, False),
        (tokens["WETH"], tokens["FAKE"], credit_limiter, False),
        (tokens["WETH"], tokens["FAKE"], count_limiter, False),
        (tokens["WETH"], Token(Web3.to_checksum_address("0" * 40), "NotAToken", 0), None, False),
        (tokens["WETH"], Token(Web3.to_checksum_address("0" * 40), "NotAToken", 0), credit_limiter, False),
        (tokens["WETH"], Token(Web3.to_checksum_address("0" * 40), "NotAToken", 0), count_limiter, False),
        (Token(Web3.to_checksum_address("0" * 40), "NotAToken", 0), tokens["USDC"], None, False),
    )
)
async def test_v2_pool_exist(token0, token1, smart_rate_limiter, expected_result, w3):
    smart_path = await SmartPath.create(w3, smart_rate_limiter=smart_rate_limiter)
    assert expected_result == await smart_path._v2_pool_exist(token0, token1)


@pytest.mark.parametrize(
    "token0, token1, fees, smart_rate_limiter, expected_result",
    (
        (tokens["WETH"], tokens["USDC"], 3000, None, True),
        (tokens["WETH"], tokens["USDC"], 3000, credit_limiter, True),
        (tokens["WETH"], tokens["USDC"], 3000, count_limiter, True),
        (tokens["WETH"], tokens["FAKE"], 3000, None, False),
        (tokens["WETH"], Token(Web3.to_checksum_address("0" * 40), "NotAToken", 0), 3000, None, False),
        (Token(Web3.to_checksum_address("0" * 40), "NotAToken", 0), tokens["USDC"], 3000, None, False),
    )
)
async def test_v3_pool_exist(token0, token1, fees, smart_rate_limiter, expected_result, w3):
    smart_path = await SmartPath.create(w3, smart_rate_limiter=smart_rate_limiter)
    assert expected_result == await smart_path._v3_pool_exist(token0, token1, fees)


@pytest.mark.parametrize(
    "token0, token1, pivot, smart_rate_limiter, expected_result",
    (
        (tokens["DAI"], tokens["WETH"], tokens["USDC"], None, True),
        (tokens["DAI"], tokens["WETH"], tokens["USDC"], credit_limiter, True),
        (tokens["DAI"], tokens["WETH"], tokens["FAKE"], None, False),
        (tokens["DAI"], tokens["WETH"], tokens["FAKE"], count_limiter, False),
    )
)
async def test_v2_pools_exists_for_pivot_token(token0, token1, pivot, smart_rate_limiter, expected_result, w3):
    smart_path = await SmartPath.create(w3, smart_rate_limiter=smart_rate_limiter)
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
mixed_path_2.total_value = Wei(int(best_value * (const.irrelevant_value_filter_multiplier - 0.1)))

v3_pool_path_3 = V3PoolPath([V3OrderedPool(tokens["WETH"], 500, tokens["USDC"])])
weighted_path_3 = WeightedPath(RouterFunction.V3_SWAP_EXACT_IN, v3_pool_path_3, 100)
mixed_path_3 = MixedWeightedPath([weighted_path_3, ])
mixed_path_3.total_value = Wei(int(best_value * (const.irrelevant_value_filter_multiplier + 0.1)))

mixed_weighted_paths = [mixed_path_1, mixed_path_2, mixed_path_3]
expected_mixed_weighted_paths = [mixed_path_1, mixed_path_3]


def test_filter_irrelevant_low_values():
    assert expected_mixed_weighted_paths == SmartPath._filter_irrelevant_low_values(mixed_weighted_paths, best_value)


def test_get_all_mixed_path():
    all_mixed_paths = SmartPath._get_all_mixed_path(mixed_path_3, mixed_path_1)
    for i, mixed_path in enumerate(all_mixed_paths):
        assert mixed_path.weighted_paths[0].router_function == RouterFunction.V3_SWAP_EXACT_IN
        assert mixed_path.weighted_paths[0].pool_path == v3_pool_path_3
        assert mixed_path.weighted_paths[0].weight == const.weight_combinations[i][0]

        assert mixed_path.weighted_paths[1].router_function == RouterFunction.V2_SWAP_EXACT_IN
        assert mixed_path.weighted_paths[1].pool_path == v2_pool_path_1
        assert mixed_path.weighted_paths[1].weight == const.weight_combinations[i][1]


async def perform_get_swap_in_path_tests(amount, expected_estimate, smart_path, token_in, token_out):
    weighted_paths = await smart_path.get_swap_in_path(amount, token_in.address, token_out.address)
    total_estimate = 0
    for path in weighted_paths:
        total_estimate += path["estimate"]
    if expected_estimate:
        assert expected_estimate * 0.98 < total_estimate < expected_estimate * 1.02
    else:
        assert weighted_paths == ()


@pytest.mark.parametrize(
    "amount, token_in, token_out, expected_estimate",
    (
        (Wei(100 * 10**18), tokens["DAI"], tokens["USDT"], 100 * 10**6),
        (Wei(100 * 10**18), Token(Web3.to_checksum_address("0x1fB90FFC02D01238Cd8AFE3a82B8C65BAC37042f"), "", 18), tokens["USDT"], None),  # noqa
    )
)
async def test_get_swap_in_path(amount, token_in, token_out, expected_estimate, w3):
    smart_path = await SmartPath.create(w3)
    await perform_get_swap_in_path_tests(amount, expected_estimate, smart_path, token_in, token_out)

    pivots = [token.address for token in const.pivot_tokens[1]]
    custom_smart_path = await SmartPath.create_custom(
        w3,
        pivot_tokens=pivots,
        v3_pool_fees=(100, 500, 3000, 10000),
        v2_router=const.uniswapv2_address,
        v2_factory=const.uniswapv2_factory_address,
        v3_quoter=const.uniswapv3_quoter_address,
        v3_factory=const.uniswapv3_factory_address,
    )
    await perform_get_swap_in_path_tests(amount, expected_estimate, custom_smart_path, token_in, token_out)


@pytest.mark.parametrize(
    "amount, token_in, token_out, smart_rate_limiter, expected_estimate",
    (
            (Wei(100 * 10 ** 18), tokens["DAI"], tokens["USDT"], None, 100 * 10 ** 6),
            (Wei(100 * 10 ** 18), tokens["DAI"], tokens["USDT"], credit_limiter, 100 * 10 ** 6),
            # (Wei(100 * 10 ** 18), tokens["DAI"], tokens["USDT"], count_limiter, 100 * 10 ** 6),  # issue between pytest-asyncio and python 3.8 & 3.9  # noqa
            (Wei(100 * 10 ** 18), Token(Web3.to_checksum_address("0x1fB90FFC02D01238Cd8AFE3a82B8C65BAC37042f"), "", 18), tokens["USDT"], None, None),  # noqa
    )
)
async def test_get_swap_in_path_v2_only(amount, token_in, token_out, smart_rate_limiter, expected_estimate, w3):
    smart_path = await SmartPath.create_v2_only(w3, smart_rate_limiter=smart_rate_limiter)
    assert smart_rate_limiter == smart_path.smart_rate_limiter
    await perform_get_swap_in_path_tests(amount, expected_estimate, smart_path, token_in, token_out)

    custom_smart_path = await SmartPath.create_custom(
        w3,
        v2_router=const.uniswapv2_address,
        v2_factory=const.uniswapv2_factory_address,
        smart_rate_limiter=smart_rate_limiter,
    )
    assert smart_rate_limiter == custom_smart_path.smart_rate_limiter
    await perform_get_swap_in_path_tests(amount, expected_estimate, custom_smart_path, token_in, token_out)


@pytest.mark.parametrize(
    "amount, token_in, token_out, smart_rate_limiter, expected_estimate",
    (
            (Wei(100 * 10 ** 18), tokens["DAI"], tokens["USDT"], None, 100 * 10 ** 6),
            (Wei(100 * 10 ** 18), tokens["DAI"], tokens["USDT"], credit_limiter, 100 * 10 ** 6),
            # (Wei(100 * 10 ** 18), tokens["DAI"], tokens["USDT"], count_limiter, 100 * 10 ** 6),  # issue between pytest-asyncio and python 3.8 & 3.9  # noqa
            (Wei(100 * 10 ** 18), Token(Web3.to_checksum_address("0x1fB90FFC02D01238Cd8AFE3a82B8C65BAC37042f"), "", 18), tokens["USDT"], None, None),  # noqa
    )
)
async def test_get_swap_in_path_v3_only(amount, token_in, token_out, smart_rate_limiter, expected_estimate, w3):
    smart_path = await SmartPath.create_v3_only(w3, smart_rate_limiter=smart_rate_limiter)
    assert smart_rate_limiter == smart_path.smart_rate_limiter
    await perform_get_swap_in_path_tests(amount, expected_estimate, smart_path, token_in, token_out)

    custom_smart_path = await SmartPath.create_custom(
        w3,
        v3_quoter=const.uniswapv3_quoter_address,
        v3_factory=const.uniswapv3_factory_address,
        smart_rate_limiter=smart_rate_limiter,
    )
    assert smart_rate_limiter == custom_smart_path.smart_rate_limiter
    await perform_get_swap_in_path_tests(amount, expected_estimate, custom_smart_path, token_in, token_out)


@pytest.mark.parametrize(
    "pivots, expected_pivot_tokens",
    (
        ((tokens["USDC"].address, tokens["WETH"].address), (tokens["USDC"], tokens["WETH"])),
        ((), ()),
    )
)
async def test_get_pivot_tokens(pivots, expected_pivot_tokens, w3):
    smart_path = await SmartPath.create(w3)
    assert await smart_path._get_pivot_tokens(pivots, w3) == expected_pivot_tokens


async def test_create_custom_exception(w3):
    with pytest.raises(SmartPathException):
        _ = await SmartPath.create_custom(
            w3,
            v3_factory=const.uniswapv3_factory_address,
        )

    with pytest.raises(SmartPathException):
        _ = await SmartPath.create_custom(
            w3,
            v3_quoter=const.uniswapv3_quoter_address,
        )

    with pytest.raises(SmartPathException):
        _ = await SmartPath.create_custom(
            w3,
            v2_factory=const.uniswapv2_factory_address,
        )

    with pytest.raises(SmartPathException):
        _ = await SmartPath.create_custom(
            w3,
            v2_router=const.uniswapv2_address,
        )
