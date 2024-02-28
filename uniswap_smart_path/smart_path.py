import asyncio
import itertools
import logging
from typing import (
    Any,
    cast,
    List,
    Optional,
    Sequence,
    Tuple,
)

from web3 import (
    AsyncHTTPProvider,
    AsyncWeb3,
)
from web3.contract import AsyncContract
from web3.types import (
    ChecksumAddress,
    Wei,
)

from ._constants import (
    erc20_abi,
    irrelevant_value_filter_multiplier,
    pivot_tokens,
    uniswapv2_abi,
    uniswapv2_address,
    uniswapv2_factory_abi,
    uniswapv2_factory_address,
    uniswapv3_factory_abi,
    uniswapv3_factory_address,
    uniswapv3_quoter_abi,
    uniswapv3_quoter_address,
    v3_pool_fees,
    weight_combinations,
)
from ._datastructures import (
    MixedWeightedPath,
    RouterFunction,
    Token,
    V2OrderedPool,
    V2PoolPath,
    V3OrderedPool,
    V3PoolPath,
    WeightedPath,
    WeightedPathResult,
)
from ._utilities import is_null_address
from .exceptions import SmartPathException

logger = logging.getLogger(__name__)


class SmartPath:
    def __init__(
            self,
            w3: AsyncWeb3,
            with_gas_estimate: bool = False,
            chain_id: int = 1,
            with_v2: bool = True,
            with_v3: bool = True,
            **kwargs: Any) -> None:
        if with_gas_estimate:
            raise NotImplementedError("Gas is not yet estimated")
        self.w3 = w3
        self.chain_id = chain_id
        self.with_v2 = with_v2
        self.with_v3 = with_v3

        self.pivots = kwargs.get("pivot_tokens") or pivot_tokens[self.chain_id]

        if self.with_v2:
            v2_router = w3.to_checksum_address(kwargs.get("v2_router") or uniswapv2_address)
            self.uniswapv2 = self.w3.eth.contract(v2_router, abi=kwargs.get("v2_abi") or uniswapv2_abi)
            V2PoolPath.contract = self.uniswapv2

            v2_factory = w3.to_checksum_address(kwargs.get("v2_factory") or uniswapv2_factory_address)
            self.factoryv2 = self.w3.eth.contract(v2_factory, abi=kwargs.get("v2_factory_abi") or uniswapv2_factory_abi)

        if self.with_v3:
            self.v3_pool_fees = tuple(kwargs.get("v3_pool_fees") or v3_pool_fees)
            self.v3_pools_fees_x_pivots = tuple(itertools.product(self.pivots, self.v3_pool_fees))

            v3_quoter = w3.to_checksum_address(kwargs.get("v3_quoter") or uniswapv3_quoter_address)
            self.quoter = self.w3.eth.contract(v3_quoter, abi=kwargs.get("v3_quoter_abi") or uniswapv3_quoter_abi)
            V3PoolPath.contract = self.quoter

            v3_factory = w3.to_checksum_address(kwargs.get("v3_factory") or uniswapv3_factory_address)
            self.factoryv3 = self.w3.eth.contract(v3_factory, abi=kwargs.get("v3_factory_abi") or uniswapv3_factory_abi)

    @classmethod
    async def create(
            cls,
            w3: Optional[AsyncWeb3] = None,
            rpc_endpoint: Optional[str] = None,
            with_gas_estimate: bool = False) -> "SmartPath":
        """
        Create a SmartPath instance which will search for the best path from v2 and v3 pools.

        :param w3: a valid AsyncWeb3 instance (if no rpc endpoint is given)
        :param rpc_endpoint: an rpc endpoint address (if no w3 instance is given)
        :param with_gas_estimate: Not supported at the moment.
        :return: a SmartPath instance using v2 and v3 pools
        """
        _w3 = await cls._get_w3(rpc_endpoint, w3)
        chain_id = await _w3.eth.chain_id
        logger.debug(f"Creating SmartPath for V2 and V3 pools on chain id: {chain_id}")
        return cls(_w3, with_gas_estimate, chain_id, True, True)

    @classmethod
    async def create_v2_only(
            cls,
            w3: Optional[AsyncWeb3] = None,
            rpc_endpoint: Optional[str] = None,
            with_gas_estimate: bool = False) -> "SmartPath":
        """
        Create a SmartPath instance which will search for the best path from v2 pools only.

        :param w3: a valid AsyncWeb3 instance (if no rpc endpoint is given)
        :param rpc_endpoint: an rpc endpoint address (if no w3 instance is given)
        :param with_gas_estimate: Not supported at the moment.
        :return: a SmartPath instance using only v2 pools
        """
        _w3 = await cls._get_w3(rpc_endpoint, w3)
        chain_id = await _w3.eth.chain_id
        logger.debug(f"Creating SmartPath for V2 only pool son chain id: {chain_id}")
        return cls(_w3, with_gas_estimate, chain_id, True, False)

    @classmethod
    async def create_v3_only(
            cls,
            w3: Optional[AsyncWeb3] = None,
            rpc_endpoint: Optional[str] = None,
            with_gas_estimate: bool = False) -> "SmartPath":
        """
        Create a SmartPath instance which will search for the best path from v3 pools only.

        :param w3: a valid AsyncWeb3 instance (if no rpc endpoint is given)
        :param rpc_endpoint: an rpc endpoint address (if no w3 instance is given)
        :param with_gas_estimate: Not supported at the moment.
        :return: a SmartPath instance using only v3 pools
        """
        _w3 = await cls._get_w3(rpc_endpoint, w3)
        chain_id = await _w3.eth.chain_id
        logger.debug(f"Creating SmartPath for V3 only pools on chain id: {chain_id}")
        return cls(_w3, with_gas_estimate, chain_id, False, True)

    @classmethod
    async def create_custom(
            cls,
            w3: Optional[AsyncWeb3] = None,
            rpc_endpoint: Optional[str] = None,
            with_gas_estimate: bool = False,
            **kwargs: Any) -> "SmartPath":
        """
        Create a SmartPath instance with custom V2 and/or v3 addresses and pivot tokens. Customization is done thanks
        to the following optional keyword arguments:

        * pivot_tokens: Sequence[str] - addresses of the token used for multi-hop pools, like weth, usdc, usdt, dai, ...
        * v3_pool_fees: tuple of v3 fees as basis point. eg: (100, 500, 3000, 10000)
        * v2_router: str - v2 router address
        * v2_factory: str - v2 factory address
        * v3_quoter: str - v3 quoter address
        * v3_factory: str - v3 factory address

        :param w3: a valid AsyncWeb3 instance (if no rpc endpoint is given)
        :param rpc_endpoint: an rpc endpoint address (if no w3 instance is given)
        :param with_gas_estimate: Not supported at the moment.
        :param kwargs: keyword args to customize V2 and/or V3 pools (see above)
        :return: a custom SmartPath instance
        """
        _w3 = await cls._get_w3(rpc_endpoint, w3)
        _chain_id = await _w3.eth.chain_id
        logger.debug(f"Creating custom SmartPath on chain id: {_chain_id}")

        if kwargs.get("pivot_tokens"):
            pivots = tuple(cast(Sequence[str], kwargs.get("pivot_tokens")))
            _pivots = await cls._get_pivot_tokens(pivots, _w3)
        else:
            _pivots = None

        with_v2 = kwargs.get("v2_router") and kwargs.get("v2_factory")
        with_v3 = kwargs.get("v3_quoter") and kwargs.get("v3_factory")
        if not with_v2 and not with_v3:
            raise SmartPathException("Must provide v2 and/or v3 addresses")

        return cls(
            _w3,
            with_gas_estimate,
            _chain_id,
            with_v2=bool(with_v2),
            with_v3=bool(with_v3),
            pivot_tokens=_pivots,
            v3_pool_fees=kwargs.get("v3_pool_fees"),
            v2_router=kwargs.get("v2_router"),
            v2_factory=kwargs.get("v2_factory"),
            v3_quoter=kwargs.get("v3_quoter"),
            v3_factory=kwargs.get("v3_factory"),
        )

    @staticmethod
    async def _get_pivot_tokens(pivots: Sequence[str], w3: AsyncWeb3) -> Tuple[Token, ...]:
        pivot_coros = [SmartPath._get_token(AsyncWeb3.to_checksum_address(pivot), w3) for pivot in pivots]
        return tuple(await asyncio.gather(*pivot_coros))

    @staticmethod
    async def _get_w3(rpc_endpoint: Optional[str], w3: Optional[AsyncWeb3]) -> AsyncWeb3:
        if w3:
            _w3 = w3
        elif rpc_endpoint:
            _w3 = AsyncWeb3(AsyncHTTPProvider(rpc_endpoint, {"timeout": 5}))
        else:
            raise ValueError("Invalid parameters. Must provide either an AsyncWeb3 instance or an rpc address")
        return _w3

    @staticmethod
    async def _get_symbol(contract: AsyncContract) -> str:
        try:
            return str(await contract.functions.symbol().call())
        except OverflowError:
            return "???"

    @staticmethod
    async def _get_token(address: ChecksumAddress, w3: AsyncWeb3) -> Token:
        erc20 = w3.eth.contract(address, abi=erc20_abi)
        symbol, decimals = await asyncio.gather(
            SmartPath._get_symbol(erc20),
            erc20.functions.decimals().call(),
        )
        return Token(AsyncWeb3.to_checksum_address(address), symbol, decimals)

    async def _v2_pool_exist(self, token0: Token, token1: Token) -> bool:
        try:
            pool_address = await self.factoryv2.functions.getPair(token0.address, token1.address).call()
            return AsyncWeb3.is_checksum_address(pool_address) and not is_null_address(pool_address)
        except asyncio.exceptions.TimeoutError:
            return False

    async def _v3_pool_exist(self, token0: Token, token1: Token, fees: int) -> bool:
        try:
            pool_address = await self.factoryv3.functions.getPool(token0.address, token1.address, fees).call()
            return AsyncWeb3.is_checksum_address(pool_address) and not is_null_address(pool_address)
        except asyncio.exceptions.TimeoutError:
            return False

    async def _v2_pools_exists_for_pivot_token(self, token0: Token, token1: Token, pivot_token: Token) -> bool:
        pool_1_address, pool_2_address = await asyncio.gather(
            self.factoryv2.functions.getPair(token0.address, pivot_token.address).call(),
            self.factoryv2.functions.getPair(pivot_token.address, token1.address).call(),
        )
        return (
                AsyncWeb3.is_checksum_address(pool_1_address)
                and AsyncWeb3.is_checksum_address(pool_2_address)
                and not is_null_address(pool_1_address)
                and not is_null_address(pool_2_address)
        )

    async def _build_v2_path_list(self, token_in: Token, token_out: Token) -> List[V2PoolPath]:
        v2_path_list: List[V2PoolPath] = []
        if not self.with_v2:
            return v2_path_list

        v2_pools_exist_cor_list = [self._v2_pool_exist(token_in, token_out)]
        filtered_pivots = [pivot for pivot in self.pivots if pivot not in (token_in, token_out)]
        for pivot_token in filtered_pivots:
            v2_pools_exist_cor_list.append(self._v2_pools_exists_for_pivot_token(token_in, token_out, pivot_token))

        v2_pools_exist = await asyncio.gather(*v2_pools_exist_cor_list)

        if v2_pools_exist[0]:
            v2_path_list.append(V2PoolPath((V2OrderedPool(token_in, token_out),)))
        for i, result in enumerate(v2_pools_exist[1:]):
            if result:
                v2_path_list.append(
                    V2PoolPath(
                        (V2OrderedPool(token_in, filtered_pivots[i]), V2OrderedPool(filtered_pivots[i], token_out))
                    )
                )

        return v2_path_list

    async def _get_v3_base_pools(self, token: Token, is_token_in: bool) -> List[V3OrderedPool]:
        v3_pools_exist_cor_list = []
        filtered__v3_pools_fees_x_pivots = [pf for pf in self.v3_pools_fees_x_pivots if pf[0] != token]
        for pivot, fees in filtered__v3_pools_fees_x_pivots:
            if pivot != token:
                v3_pools_exist_cor_list.append(self._v3_pool_exist(token, pivot, fees))

        v3_pools_exist = await asyncio.gather(*v3_pools_exist_cor_list)
        v3_pool_list = []
        for i, result in enumerate(v3_pools_exist):
            if result:
                pivot = filtered__v3_pools_fees_x_pivots[i][0]
                fees = filtered__v3_pools_fees_x_pivots[i][1]
                pool = V3OrderedPool(token, fees, pivot) if is_token_in else V3OrderedPool(pivot, fees, token)
                v3_pool_list.append(pool)

        return v3_pool_list

    async def _get_v3_one_hop_pools(self, token_in: Token, token_out: Token) -> List[V3OrderedPool]:
        v3_pools_exist_cor_list = []
        for fees in self.v3_pool_fees:
            v3_pools_exist_cor_list.append(self._v3_pool_exist(token_in, token_out, fees))
        v3_pools_exist = await asyncio.gather(*v3_pools_exist_cor_list)
        v3_pool_list = []
        for i, result in enumerate(v3_pools_exist):
            if result:
                v3_pool_list.append(V3OrderedPool(token_in, self.v3_pool_fees[i], token_out))
        return v3_pool_list

    async def _build_v3_path_list(self, token_in: Token, token_out: Token) -> List[V3PoolPath]:
        v3_path_list: List[V3PoolPath] = []
        if not self.with_v3:
            return v3_path_list

        one_hop_pools, token_in_base_pools, token_out_base_pools = await asyncio.gather(
            self._get_v3_one_hop_pools(token_in, token_out),
            self._get_v3_base_pools(token_in, True),
            self._get_v3_base_pools(token_out, False),
        )

        for pool in one_hop_pools:
            v3_path_list.append(V3PoolPath((pool,), ))

        if len(token_in_base_pools) > 0 and len(token_out_base_pools) > 0:
            product = itertools.product(token_in_base_pools, token_out_base_pools)
            two_hop_pools = [p for p in product if p[0].token_out == p[1].token_in]
            for two_hop_pool in two_hop_pools:
                v3_path_list.append(V3PoolPath(two_hop_pool, ))

        return v3_path_list

    @staticmethod
    def _filter_irrelevant_low_values(
            mixed_weighted_paths: List[MixedWeightedPath],
            best_value: Wei) -> List[MixedWeightedPath]:
        return [
            path
            for path in mixed_weighted_paths
            if path.total_value > best_value * irrelevant_value_filter_multiplier
        ]

    @staticmethod
    def _get_all_mixed_path(
            lower_value_path: MixedWeightedPath,
            higher_value_path: MixedWeightedPath) -> List[MixedWeightedPath]:
        all_paths = []
        for low_weight, high_weight in weight_combinations:
            lower_weighted_path = WeightedPath(
                router_function=lower_value_path.weighted_paths[0].router_function,
                pool_path=lower_value_path.weighted_paths[0].pool_path,
                weight=low_weight,
            )
            higher_weighted_path = WeightedPath(
                router_function=higher_value_path.weighted_paths[0].router_function,
                pool_path=higher_value_path.weighted_paths[0].pool_path,
                weight=high_weight,
            )
            all_paths.append(MixedWeightedPath((lower_weighted_path, higher_weighted_path)))
        return all_paths

    async def get_swap_in_path(
            self,
            amount: Wei,
            token_in_address: ChecksumAddress,
            token_out_address: ChecksumAddress) -> Tuple[WeightedPathResult, ...]:
        token_in, token_out = await asyncio.gather(
            self._get_token(token_in_address, self.w3),
            self._get_token(token_out_address, self.w3),
        )
        v2_pool_paths, v3_pool_paths = await asyncio.gather(
            self._build_v2_path_list(token_in, token_out),
            self._build_v3_path_list(token_in, token_out),
        )

        v2_mixed_paths = [
            MixedWeightedPath(
                (WeightedPath(RouterFunction.V2_SWAP_EXACT_IN, pool_path, 100),)
            ) for pool_path in v2_pool_paths
        ]
        v3_mixed_paths = [
            MixedWeightedPath(
                (WeightedPath(RouterFunction.V3_SWAP_EXACT_IN, pool_path, 100),)
            ) for pool_path in v3_pool_paths
        ]

        computing_value_coros = [path.compute_path_values(amount) for path in v2_mixed_paths]
        computing_value_coros.extend([path.compute_path_values(amount) for path in v3_mixed_paths])
        await asyncio.gather(*computing_value_coros)

        v2_mixed_paths.sort(key=lambda mp: mp.total_value, reverse=True)
        v3_mixed_paths.sort(key=lambda mp: mp.total_value, reverse=True)

        best_value = max(
            v2_mixed_paths[0].total_value if len(v2_mixed_paths) > 0 else 0,
            v3_mixed_paths[0].total_value if len(v3_mixed_paths) > 0 else 0,
        )

        v2_mixed_paths = self._filter_irrelevant_low_values(v2_mixed_paths, Wei(best_value))
        logger.debug(f"V2 Paths: {v2_mixed_paths}")
        v3_mixed_paths = self._filter_irrelevant_low_values(v3_mixed_paths, Wei(best_value))
        logger.debug(f"V3 Paths: {v3_mixed_paths}")

        if len(v2_mixed_paths) == len(v3_mixed_paths) == 0:
            return ()
        elif len(v3_mixed_paths) == 0:
            return v2_mixed_paths[0].output()
        elif len(v2_mixed_paths) == 0:
            return v3_mixed_paths[0].output()
        else:
            if v2_mixed_paths[0].total_value > v3_mixed_paths[0].total_value:
                lower_value_path = v3_mixed_paths[0]
                higher_value_path = v2_mixed_paths[0]
            else:
                lower_value_path = v2_mixed_paths[0]
                higher_value_path = v3_mixed_paths[0]

            all_mixed_paths = self._get_all_mixed_path(lower_value_path, higher_value_path)
            computing_value_coros = [path.compute_path_values(amount) for path in all_mixed_paths]
            await asyncio.gather(*computing_value_coros)
            all_mixed_paths.extend([v2_mixed_paths[0], v3_mixed_paths[0]])
            all_mixed_paths.sort(key=lambda mp: mp.total_value, reverse=True)
            logger.debug(f"All mixed paths: {all_mixed_paths}")

            return all_mixed_paths[0].output()
