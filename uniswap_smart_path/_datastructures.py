import asyncio
from dataclasses import dataclass
from enum import Enum
import logging
from typing import (
    Any,
    cast,
    Coroutine,
    Dict,
    List,
    Protocol,
    Sequence,
    Tuple,
    TypedDict,
    TypeVar,
    Union,
)

from uniswap_universal_router_decoder import RouterCodec
from web3 import AsyncWeb3
from web3.contract import AsyncContract
from web3.exceptions import Web3Exception
from web3.types import (
    ChecksumAddress,
    Wei,
)

from ._utilities import to_wei


logger = logging.getLogger(__name__)
codec = RouterCodec()


@dataclass(frozen=True)
class Token:
    address: ChecksumAddress
    symbol: str
    decimals: int


class RouterFunction(Enum):
    V3_SWAP_EXACT_IN = "V3_SWAP_EXACT_IN"
    V3_SWAP_EXACT_OUT = "V3_SWAP_EXACT_OUT"
    V2_SWAP_EXACT_IN = "V2_SWAP_EXACT_IN"
    V2_SWAP_EXACT_OUT = "V2_SWAP_EXACT_OUT"


@dataclass(frozen=True)
class V2OrderedPool:
    token_in: Token
    token_out: Token


@dataclass(frozen=True)
class V3OrderedPool:
    token_in: Token
    pool_fee: int
    token_out: Token


OrderedPool = TypeVar('OrderedPool', V2OrderedPool, V3OrderedPool)
V2PathList = Tuple[ChecksumAddress, ...]
V3PathList = Tuple[Union[int, ChecksumAddress], ...]
PathList = TypeVar('PathList', V2PathList, V3PathList)


class PoolPath(Protocol[OrderedPool, PathList]):
    pools: Sequence[OrderedPool]
    def get_path(self) -> PathList: ...
    def to_dict(self) -> Dict[str, PathList]: ...
    async def get_amount_out(self, amount_in: Wei) -> Wei: ...


class V2PoolPath(PoolPath[V2OrderedPool, V2PathList]):
    contract: AsyncContract = AsyncWeb3().eth.contract(AsyncWeb3.to_checksum_address("0" * 40))

    def __init__(self, pools: Sequence[V2OrderedPool]) -> None:
        self.pools = pools
        self.path = self._build_path()

    def get_path(self) -> V2PathList:
        return self.path

    def _build_path(self) -> V2PathList:
        path = [self.pools[0].token_in.address]
        for pool in self.pools:
            path.append(pool.token_out.address)
        return tuple(path)

    def to_dict(self) -> Dict[str, V2PathList]:
        return {"path": self.get_path()}

    async def get_amount_out(self, amount_in: Wei) -> Wei:
        quote = await self.contract.functions.getAmountsOut(amount_in, self.get_path()).call()
        return to_wei(quote[-1])

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}: {self.path}"


class V3PoolPath(PoolPath[V3OrderedPool, V3PathList]):
    contract: AsyncContract = AsyncWeb3().eth.contract(AsyncWeb3.to_checksum_address("0" * 40))

    def __init__(self, pools: Sequence[V3OrderedPool]) -> None:
        self.pools = pools
        self.path = self._build_path()

    def get_path(self) -> V3PathList:
        return self.path

    def _build_path(self) -> V3PathList:
        path: List[Union[int, ChecksumAddress]] = [self.pools[0].token_in.address]
        for pool in self.pools:
            path.append(pool.pool_fee)
            path.append(pool.token_out.address)
        return tuple(path)

    def to_dict(self) -> Dict[str, V3PathList]:
        return {"path": self.get_path()}

    async def get_amount_out(self, amount_in: Wei) -> Wei:
        encoded_path = codec.encode.v3_path("V3_SWAP_EXACT_IN", self.get_path())
        quote = await self.contract.functions.quoteExactInput(encoded_path, amount_in).call()
        return to_wei(quote[0])

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}: {self.path}"


@dataclass(frozen=True)
class WeightedPath:
    router_function: RouterFunction
    pool_path: PoolPath  # type: ignore
    weight: int

    def to_dict(self) -> Dict[str, Union[str, PathList, int]]:
        result = self.pool_path.to_dict()
        result["function"] = self.router_function.value
        result["weight"] = self.weight
        return result


class WeightedPathResult(TypedDict):
    function: str
    path: PathList  # type: ignore
    weight: int
    estimate: Wei


class MixedWeightedPath:
    def __init__(self, weighted_paths: Sequence[WeightedPath]) -> None:
        self.weighted_paths: Tuple[WeightedPath, ...] = tuple(weighted_paths)
        self.values: Tuple[Wei, ...] = (Wei(0), Wei(0))
        self.total_value: Wei = Wei(0)

    async def compute_path_values(self, amount: Wei) -> None:
        computing_coros: List[Coroutine[Any, Any, Wei]] = [
            w_p.pool_path.get_amount_out(Wei(amount * w_p.weight // 100))
            for w_p in self.weighted_paths
        ]
        try:
            self.values = await asyncio.gather(*computing_coros)
            self.total_value = Wei(sum(self.values))
        except (asyncio.exceptions.TimeoutError, ValueError, Web3Exception) as e:
            logger.debug(f"Could not compute value for path(s): {self.weighted_paths}. Reason: {e}")

    def output(self) -> Tuple[WeightedPathResult, ...]:
        output = []
        for i, path in enumerate(self.weighted_paths):
            path_dict = path.to_dict()
            path_dict["estimate"] = self.values[i]
            output.append(cast(WeightedPathResult, path_dict))

        return tuple(output)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}: {self.weighted_paths}, "
            f"values: {self.values}, "
            f"total_value: {self.total_value}"
        )
