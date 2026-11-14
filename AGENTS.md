# AGENTS.md

> Guidance for AI coding agents working in this repository.

## What this is

`uniswap-smart-path` is a Python library that finds the best swap route, across Uniswap V2 and V3 pools, for a given
token pair and amount, and returns it/them ready to be fed to the
[Universal Router codec](https://github.com/Elnaril/uniswap-universal-router-decoder). It is the routing companion of
that decoder SDK.

Two public surfaces, both exported from `uniswap_smart_path/__init__.py`:

- `SmartPath` — async router. Factories: `create()`, `create_v2_only()`, `create_v3_only()`, `create_custom()`.
  Entry point: `await get_swap_in_path(amount, token_in_address, token_out_address)`.
- `SmartRateLimiter` — optional RPC throttling, credit/CUPS based (requires both `eth_call` and `eth_chainId` costs) or
  request-count based.

Everything else is private and must stay private.

## The leading project

The [Uniswap Universal Router Decoder](https://github.com/Elnaril/uniswap-universal-router-decoder) (UR SDK) is the
reference project for style. When this repo does not settle a question, follow the UR SDK, not your own preference.

## Layout

- `uniswap_smart_path/` — the package. Modules prefixed with `_` are private; shared constants and ABIs live in
  `_constants.py`.
  - `smart_path.py` — path discovery and selection (the core).
  - `_datastructures.py` — `Token`, `V2/V3OrderedPool`, `V2/V3PoolPath`, `WeightedPath`, `MixedWeightedPath`.
  - `smart_rate_limiter.py` — `SmartRateLimiter`, the `MethodName`/`MethodCredits` vocabulary and the `_rate_limit`
    decorator.
- `tests/` — unit tests. `tests/conftest.py` holds the fixtures, the `tokens` dict and the shared `credit_limiter` /
  `count_limiter`.
- `integration_tests/` — live-RPC scripts (Ethereum, Base, Optimism, BSC) and a Ganache-driven `main.py`.
- `coverage.json` — a tracked, generated artifact (regenerate it before committing).
- `notes/`, `analysis/` — **git-ignored** scratch space, not part of the package.

## Dev setup

```bash
pip install -r requirements.txt          # includes requirements_install.txt + dev tools
```

## Commands that must all pass

```bash
mypy uniswap_smart_path
flake8 uniswap_smart_path
flake8 tests
flake8 integration_tests
isort --check --diff uniswap_smart_path
isort --check --diff tests
isort --check --diff integration_tests
RPC_ENDPOINT=https://... pytest tests
coverage run -m pytest tests && coverage report -m && coverage json
```

`tox` runs all of the above over Python 3.8–3.13 × web3 6 and 7 (`tox -e lint-web37`, `tox -e coverage`, ...).
See `tox.ini`.

Unit tests are **live-network tests**: they hit mainnet Uniswap contracts and require `RPC_ENDPOINT`. Do not "fix"
them by mocking RPC calls — that would change what they are for.

## Ground rules (from the UR SDK's CONTRIBUTING.md)

- PEP 8 names; match the formatting of the surrounding code.
- Line length is 120; isort and flake8 are configured in `tox.ini`.
- Put constants and ABIs in `_constants.py`; do not expose what should stay private.
- A new or changed public API must be documented in its docstring **and** in `README.md`, including the
  `Release notes` section at the top of the README.
- Keep coverage from regressing (it is currently 99%; see `coverage.json`); regenerate `coverage.json` with
  `coverage json` before committing.
- Update integration tests when a change affects live behaviour.
- Squash commits so that 1 PR = 1 commit, with a clear message.

## Style specifics of this codebase

- **Python 3.8 floor.** `pyproject.toml` declares `requires-python = ">=3.8"`, so use `typing.Tuple`, `List`, `Dict`,
  `Optional`, ... — never `tuple[...]`, `dict[...]` or `X | Y` at runtime. The UR SDK can use the lowercase forms; this
  repo cannot until the floor is raised.
- **Imports.** Existing package modules use relative imports (`from ._constants import ...`); `__init__.py` and the UR
  SDK use absolute ones. Match the file you are editing; for a new module, prefer absolute
  (`from uniswap_smart_path._constants import ...`) to align with the UR SDK.
- **isort** settings (`tox.ini`): `multi_line_output = 3`, `force_grid_wrap = 2`, `include_trailing_comma = True`,
  `lines_after_imports = 2` — hence the two blank lines after the import block and the parenthesised, one-per-line
  import style.
- **Multi-line signatures and calls** use an 8-space hanging indent, not a 4-space one:
  ```python
  async def create(
          cls,
          w3: Optional[AsyncWeb3] = None,
          ...
  ```
- **Docstrings** are reST: a short summary, then `:param name:` and `:return:`. No blank line before the closing
  `"""`. Module-level docstrings are not used in this package.
- **Typing is strict** (`mypy.ini` disallows untyped defs, incomplete defs, `Any` generics, untyped calls, ...).
  Use `cast()` where web3's own annotations are too loose, and keep the `# type: ignore` comments that already exist.
- **Async first.** Parallel RPC work goes through `asyncio.gather`; never call `asyncio.run` inside the library.
- **Logging** via a module-level `logger = logging.getLogger(__name__)`, with f-strings in messages.
- **Errors.** Library errors derive from `SmartPathException`. Quote failures are swallowed on purpose (debug log);
  do not turn them into hard failures.
- **Data holders** are `@dataclass(frozen=True)` where possible; structural contracts use `Protocol`; fixed
  vocabularies (router functions) use `Enum`; the result dict is a `TypedDict` (`WeightedPathResult`).
- **Rate-limiter vocabulary.** `MethodName` (the `Literal` of RPC methods) is the single source of truth;
  `MethodCredits = Dict[MethodName, int]` derives from it and the `__init__` check uses `get_args(MethodName)`. Both
  the `eth_call` and `eth_chainId` costs are mandatory when a credit limiter is used.

## How routing works (do not break this)

1. Resolve both tokens (`symbol`, `decimals`).
2. Build V2 candidates: direct pair + every pivot-token hop (default pivots: USDC, USDT, DAI, WETH).
3. Build V3 candidates: direct pools at each fee tier `(100, 500, 3000, 10000)` + every two-hop pivot path.
4. Quote all candidates in parallel (`getAmountsOut` / `quoteExactInput`).
5. Drop paths worth less than `irrelevant_value_filter_multiplier` (0.9) of the best.
6. If both V2 and V3 survive, quote every split in `weight_combinations` (10/90 … 50/50) and return the best.

The output is `Tuple[WeightedPathResult, ...]`: `{path, function, weight, estimate}`.

When a `SmartRateLimiter` is given, the calls made while creating a `SmartPath` are rate limited too: `eth_chainId`
at the `eth_chainId` cost, and the pivot tokens' `symbol`/`decimals` at the `eth_call` cost.

## Gotchas that will bite you

- **Class-level contract injection.** `SmartPath.__init__` assigns `V2PoolPath.contract` and `V3PoolPath.contract` as
  *class* attributes (workaround for async construction). This is process-global mutable state: two differently
  configured `SmartPath` instances in one process overwrite each other's contracts. Do not add more state this way.
- **`METHODS_TO_VALIDATE` is mutated globally.** `eth_call` is removed from
  `web3.middleware.validation.METHODS_TO_VALIDATE` at construction to avoid `eth_chainId` storms. Keep it that way.
- **`with_gas_estimate=True` raises `NotImplementedError`.** Gas estimation is not implemented; do not silently accept
  the flag.
- **Both `eth_call` and `eth_chainId` are rate limited, creation included.** `MethodCredits` requires both costs and
  `SmartRateLimiter` raises `ValueError` when one is missing. Every rate-limited call goes through
  `_rate_limited_call(limiter, method_name, call)`; `_rate_limit` delegates to it — do not re-implement the limiter
  branching.
- **Tests need a session-scoped event loop.** `pytest.ini` sets `asyncio_default_test_loop_scope = session`:
  `credit-rate-limit` refunds credits/semaphore slots with `loop.call_later`, so a per-test loop discards the refund
  when it closes and the next test hangs in `__aenter__`. Do not remove that setting. The shared `credit_limiter` and
  `count_limiter` live in `tests/conftest.py`.
- **`notes/` and `analysis/` are git-ignored.** Do not rely on them as documentation, and do not put deliverables
  there unless the user asks.
- **Generated files.** `coverage.json` is tracked; `dist/`, `*.egg-info/`, `.coverage`, caches are not. The version
  lives in `pyproject.toml` (`[project] version`) and is repeated in the README `Release notes`.
- **Chains.** Out of the box only Ethereum mainnet and Ganache (chain id 1337) have default addresses in
  `_constants.pivot_tokens`; anything else needs `create_custom()`.
- **Address sources.** Check Uniswap addresses against
  https://developers.uniswap.org/deployments?chain=Ethereum (and the matching chain) rather than from memory; the UR
  SDK's `_constants.py` is the reference for Universal Router / Permit2 / PositionManager addresses.

## Maintaining this file

Update `AGENTS.md` whenever a change introduces relevant new information: a new module, a new public API, a new
command or env var, a changed support matrix, a new gotcha, or a resolved one that is no longer true. Keep it short and
factual — it is guidance, not a changelog.
