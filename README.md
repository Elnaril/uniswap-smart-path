# Uniswap Smart Path

## Overview 

With several V2 and V3 pools, and 2 or 3 tokens per path, there may be quite a few routes to perform a swap.
And if you add the gas fees into the equation, it is not straightforward to be sure to get the best deal. 

The object of this library is to find the path(s), from v2 and v3 pools, to swap with the best price,
including gas fees, and to return it/them in order to be used directly with the [UR codec](https://github.com/Elnaril/uniswap-universal-router-decoder),
along with a percentage to know how to divide the amount between them.

---

But at the moment, it's just the theory ... Let's wait for the implementation! 
