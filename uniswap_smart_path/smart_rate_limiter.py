from typing import (
    Optional,
    TypedDict,
)

from credit_rate_limit import (
    CountRateLimiter,
    CreditRateLimiter,
)


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
