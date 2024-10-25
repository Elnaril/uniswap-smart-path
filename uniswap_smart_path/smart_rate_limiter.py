from functools import wraps
from typing import (
    Any,
    Callable,
    Literal,
    Optional,
    Protocol,
    TypedDict,
)

from credit_rate_limit import (
    CountRateLimiter,
    CreditRateLimiter,
    throughput,
)
from credit_rate_limit.rate_limiter import DecoratedSignature


class MethodCredit(TypedDict):
    eth_call: int


class SmartRateLimiter:
    def __init__(
            self,
            interval: float,
            max_count: Optional[int] = None,
            max_credits: Optional[int] = None,
            method_credits: Optional[MethodCredit] = None,
            ) -> None:
        self.interval = interval
        self.max_count = max_count
        self.max_credits = max_credits
        self.method_credits = method_credits
        if self.max_credits:
            if self.method_credits:
                self.rate_limiter = CreditRateLimiter(max_credits, interval)
            else:
                raise ValueError("Missing parameter 'method_credits' needed for credit rate limit")
        elif self.max_count:
            self.rate_limiter = CountRateLimiter(max_count, interval)
        else:
            raise ValueError("Missing parameter: either 'max_count' or 'max_credits' (and 'method_credits') is needed")


class GotSmartRateLimiter(Protocol):
    def get_smart_rate_limiter(self) -> Optional[SmartRateLimiter]: ...


def _rate_limit(method_name: Literal["eth_call"]) -> Callable[[Callable[..., Any]], Any]:
    def decorator(func: DecoratedSignature) -> Any:
        @wraps(func)
        def wrapper(self_: GotSmartRateLimiter, *args: Any, **kwargs: Any) -> Any:
            smart_rate_limiter = self_.get_smart_rate_limiter()
            if smart_rate_limiter:
                rate_limiter = smart_rate_limiter.rate_limiter
                if isinstance(rate_limiter, CreditRateLimiter) and smart_rate_limiter.method_credits:
                    request_credits = smart_rate_limiter.method_credits[method_name]
                    return throughput(rate_limiter, request_credits=request_credits)(func)(self_, *args, **kwargs)
                elif isinstance(rate_limiter, CountRateLimiter):
                    return throughput(rate_limiter)(func)(self_, *args, **kwargs)
                else:
                    raise ValueError("Missing parameter 'method_credits' , or unknown rate limiter")
            else:
                return func(self_, *args, **kwargs)
        return wrapper
    return decorator
