from functools import wraps
from typing import (
    Any,
    Awaitable,
    Callable,
    cast,
    Dict,
    get_args,
    Literal,
    Optional,
    Protocol,
)

from credit_rate_limit import (
    CountRateLimiter,
    CreditRateLimiter,
    throughput,
)
from credit_rate_limit.rate_limiter import DecoratedSignature


MethodName = Literal["eth_call", "eth_chainId"]
MethodCredits = Dict[MethodName, int]


class SmartRateLimiter:
    def __init__(
            self,
            interval: float,
            max_count: Optional[int] = None,
            max_credits: Optional[int] = None,
            method_credits: Optional[MethodCredits] = None,
            ) -> None:
        self.interval = interval
        self.max_count = max_count
        self.max_credits = max_credits
        self.method_credits = method_credits
        if self.max_credits:
            if not self.method_credits:
                raise ValueError("Missing parameter 'method_credits' needed for credit rate limit")
            missing_methods = [method for method in get_args(MethodName) if method not in self.method_credits]
            if missing_methods:
                raise ValueError(f"Missing method(s) in 'method_credits': {', '.join(missing_methods)}")
            self.rate_limiter = CreditRateLimiter(max_credits, interval)
        elif self.max_count:
            self.rate_limiter = CountRateLimiter(max_count, interval)
        else:
            raise ValueError("Missing parameter: either 'max_count' or 'max_credits' (and 'method_credits') is needed")


class GotSmartRateLimiter(Protocol):
    def get_smart_rate_limiter(self) -> Optional[SmartRateLimiter]: ...


def _rate_limited_call(
        smart_rate_limiter: Optional[SmartRateLimiter],
        method_name: MethodName,
        call: Callable[[], Awaitable[Any]]) -> Awaitable[Any]:
    if not smart_rate_limiter:
        return call()
    rate_limiter = smart_rate_limiter.rate_limiter
    if isinstance(rate_limiter, CreditRateLimiter) and smart_rate_limiter.method_credits:
        request_credits = smart_rate_limiter.method_credits[method_name]
        return cast(Awaitable[Any], throughput(rate_limiter, request_credits=request_credits)(call)())
    elif isinstance(rate_limiter, CountRateLimiter):
        return cast(Awaitable[Any], throughput(rate_limiter)(call)())
    else:
        raise ValueError("Missing parameter 'method_credits' , or unknown rate limiter")


def _rate_limit(method_name: MethodName) -> Callable[[Callable[..., Any]], Any]:
    def decorator(func: DecoratedSignature) -> Any:
        @wraps(func)
        def wrapper(self_: GotSmartRateLimiter, *args: Any, **kwargs: Any) -> Any:
            return _rate_limited_call(
                self_.get_smart_rate_limiter(),
                method_name,
                lambda: func(self_, *args, **kwargs),
            )
        return wrapper
    return decorator
