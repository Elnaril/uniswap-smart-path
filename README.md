# Uniswap Smart Path

#### Project Information
[![Continous Integration](https://github.com/Elnaril/uniswap-smart-path/actions/workflows/ci.yml/badge.svg)](https://github.com/Elnaril/uniswap-smart-path/actions/workflows/ci.yml)
[![License](https://img.shields.io/github/license/Elnaril/uniswap-smart-path)](https://github.com/Elnaril/uniswap-smart-path/blob/master/LICENSE)

#### Code Quality
[![Test Coverage](https://img.shields.io/badge/dynamic/json?color=blueviolet&label=coverage&query=%24.totals.percent_covered_display&suffix=%25&url=https%3A%2F%2Fraw.githubusercontent.com%2FElnaril%2Funiswap-smart-path%2Fmaster%2Fcoverage.json)](https://github.com/Elnaril/uniswap-smart-path/blob/master/coverage.json)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)
[![Type Checker: mypy](https://img.shields.io/badge/%20type%20checker-mypy-%231674b1?style=flat&labelColor=ef8336)](https://mypy-lang.org/)
[![Linter: flake8](https://img.shields.io/badge/%20linter-flake8-%231674b1?style=flat&labelColor=ef8336)](https://flake8.pycqa.org/en/latest/)


## Overview 

With several V2 and V3 pools, and 2 or 3 tokens per path, there may be quite a few routes to perform a swap.
And if you add the gas fees into the equation, it is not straightforward to be sure to get the best deal. 

The object of this library is to find the path(s), from v2 and v3 pools, to swap with the best price,
including gas fees, and to return it/them in order to be used directly with the [UR codec](https://github.com/Elnaril/uniswap-universal-router-decoder),
along with a percentage to know how to divide the amount between them.

⚠ This project is a work in progress. Not all features have been implemented yet.
For instance the gas fees is not evaluated in the current version.

⚠ This tool does not replace your own due diligence to find the best price/path to swap any token.

---

## Installation
A good practice is to use [Python virtual environments](https://python.readthedocs.io/en/latest/library/venv.html), here is a [tutorial](https://www.freecodecamp.org/news/how-to-setup-virtual-environments-in-python/).

The library can be pip installed from [pypi.org](https://pypi.org/project/uniswap-smart-path/) as usual:

```bash
# update pip to latest version if needed
pip install -U pip

# install the decoder from pypi.org
pip install uniswap-smart-path
```

---

## Usage

The library exposes a class, `SmartPath` with a public method `get_swap_in_path()` that can be used to find the best path/price.
For performance's sake, it is asynchronous.

```python
from uniswap_smart_path import SmartPath

smart_path = await SmartPath.create(async_w3)  # where async_w3 is your AsyncWeb3 instance
path = await smart_path.get_swap_in_path(amount_in_wei, token0_address, token1_address)

```

You can also create the `SmartPath` instance from a rpc endpoint:
```python
from uniswap_smart_path import SmartPath

smart_path = await SmartPath.create(rpc_endpoint=rpc_endpoint)

```

## Result
Examples of output paths that you can use with the [UR codec](https://github.com/Elnaril/uniswap-universal-router-decoder) to encode a transaction.

#### Single path
```python
(
    {
        'path': ('0xD533a949740bb3306d119CC777fa900bA034cd52', 3000, '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2', 3000, '0x9f8F72aA9304c8B593d555F12eF6589cC3A579A2'),
        'function': 'V3_SWAP_EXACT_IN',
        'weight': 100,
        'estimate': 128331138758276360764
    },
)
```

#### Multi path
Here, 90% of the amount should be swapped on a V3 pool and 10% on a V2 pool, all that in a single transaction using the UR codec.
```python
(
    {
        'path': ('0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984', '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
        'function': 'V2_SWAP_EXACT_IN',
        'weight': 10,
        'estimate': 32858922292711987411
     },
    {
        'path': ('0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984', 3000, '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
        'function': 'V3_SWAP_EXACT_IN',
        'weight': 90,
        'estimate': 295000857928717844546
    }
)
```
