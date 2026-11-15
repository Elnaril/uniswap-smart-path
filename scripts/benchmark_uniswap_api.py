"""Benchmark the Uniswap Trading API against uniswap-smart-path.

Quotes 0.1 WBTC -> UNI on Ethereum mainnet, fires both requests at the same
time, then resolves the block mined immediately before the send timestamp via
Etherscan and compares it with the block the Uniswap API quoted against.

Required environment variables:
    RPC_ENDPOINT           Ethereum mainnet JSON-RPC endpoint used by SmartPath.
    UNISWAP_API_KEY        Uniswap Trading API key (sent as the x-api-key header).
    ETHERSCAN_API_KEY      Etherscan API key (V2 API, chainid=1).

Optional environment variables:
    SWAPPER_ADDRESS        Address used in the Uniswap API quote request.
                           Defaults to the OpenChainBench burner address.
    UNISWAP_API_PROTOCOLS  Comma-separated protocols, e.g. "V2,V3". If unset,
                           the API uses its default (all protocols).

Output:
    scripts/results_YYYY_MM_DD.log (appended).

Run from the repository root:
    python scripts/benchmark_uniswap_api.py
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
import json
import logging
import os
from pathlib import Path
import sys
import time
from typing import Any
from urllib.parse import urlparse

import aiohttp
from web3 import (
    AsyncHTTPProvider,
    AsyncWeb3,
)


sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from uniswap_smart_path import (  # noqa: E402
    SmartPath,
    SmartRateLimiter,
)


WBTC_ADDRESS = AsyncWeb3.to_checksum_address("0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599")
UNI_ADDRESS = AsyncWeb3.to_checksum_address("0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984")
WBTC_DECIMALS = 8
UNI_DECIMALS = 18
AMOUNT_WEI = 10_000_000  # 0.1 WBTC

UNISWAP_API_URL = "https://trade-api.gateway.uniswap.org/v1/quote"
ETHERSCAN_API_URL = "https://api.etherscan.io/v2/api"
DEFAULT_SWAPPER = "0xbb663a119193cA68512c351b0fdfDEB9c22Dc416"

API_TIMEOUT_SECONDS = 30
LIB_TIMEOUT_SECONDS = 180
RPC_TIMEOUT_SECONDS = 30

# Generous credit limiter: the benchmark measures path-finding, not throttling.
# Lower max_credits (or raise the method costs) to measure the limiter's impact.
CREDIT_INTERVAL_SECONDS = 1
MAX_CREDITS = 3000
METHOD_CREDITS: dict[str, int] = {"eth_call": 26, "eth_chainId": 5}


@dataclass(frozen=True)
class Config:
    rpc_endpoint: str
    uniswap_api_key: str
    etherscan_api_key: str
    swapper: str
    protocols: list[str] | None


def load_config() -> Config:
    missing = [
        name
        for name in ("RPC_ENDPOINT", "UNISWAP_API_KEY", "ETHERSCAN_API_KEY")
        if not os.getenv(name)
    ]
    if missing:
        raise ValueError(f"Missing required environment variable(s): {', '.join(missing)}")

    protocols_raw = os.getenv("UNISWAP_API_PROTOCOLS", "").strip()
    protocols = [protocol.strip() for protocol in protocols_raw.split(",") if protocol.strip()] or None

    return Config(
        rpc_endpoint=os.environ["RPC_ENDPOINT"],
        uniswap_api_key=os.environ["UNISWAP_API_KEY"],
        etherscan_api_key=os.environ["ETHERSCAN_API_KEY"],
        swapper=os.getenv("SWAPPER_ADDRESS", DEFAULT_SWAPPER),
        protocols=protocols,
    )


class RunLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        if not record.getMessage():
            return ""
        return super().format(record)


def setup_logging() -> logging.Logger:
    log_path = Path(__file__).resolve().parent / f"results_{datetime.now().strftime('%Y_%m_%d')}.log"
    logger = logging.getLogger("uniswap_smart_path_benchmark")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    if not logger.handlers:
        formatter = RunLogFormatter(
            "%(asctime)s.%(msecs)03d %(levelname)s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler = logging.FileHandler(log_path, mode="a", encoding="utf-8")
        file_handler.setFormatter(formatter)
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.addHandler(stream_handler)

    logger.info("Log file: %s", log_path)
    return logger


def iso_timestamp(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp).astimezone().isoformat(timespec="milliseconds")


def log_run_header(logger: logging.Logger) -> None:
    logger.info("")
    logger.info("#" * 100)
    logger.info("# RUN START: %s", iso_timestamp(time.time()))
    logger.info("# WBTC -> UNI | 0.1 WBTC | Uniswap API vs uniswap-smart-path")
    logger.info("#" * 100)
    logger.info("")


def log_run_footer(logger: logging.Logger) -> None:
    logger.info("")
    logger.info("#" * 100)
    logger.info("# RUN END: %s", iso_timestamp(time.time()))
    logger.info("#" * 100)
    logger.info("")
    logger.info("")
    logger.info("")


def json_dumps(value: Any) -> str:
    return json.dumps(value, indent=2, default=str, ensure_ascii=False)


def to_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def format_units(value: int | None, decimals: int) -> str:
    if value is None:
        return "n/a"
    return f"{Decimal(value) / Decimal(10 ** decimals):.{decimals}f}"


async def uniswap_api_quote(
        session: aiohttp.ClientSession,
        config: Config,
        barrier: asyncio.Event) -> dict[str, Any]:
    body: dict[str, Any] = {
        "type": "EXACT_INPUT",
        "amount": str(AMOUNT_WEI),
        "tokenInChainId": 1,
        "tokenOutChainId": 1,
        "tokenIn": WBTC_ADDRESS,
        "tokenOut": UNI_ADDRESS,
        "swapper": config.swapper,
        "routingPreference": "BEST_PRICE",
    }
    if config.protocols:
        body["protocols"] = config.protocols

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "x-api-key": config.uniswap_api_key,
    }

    await barrier.wait()
    send_time = time.time()
    start = time.perf_counter()
    try:
        async with session.post(UNISWAP_API_URL, json=body, headers=headers) as response:
            raw_body = await response.text()
            return {
                "send_time": send_time,
                "duration": time.perf_counter() - start,
                "status": response.status,
                "body": raw_body,
            }
    except Exception as exc:
        return {
            "send_time": send_time,
            "duration": time.perf_counter() - start,
            "error": repr(exc),
        }


async def smart_path_quote(smart_path: SmartPath, barrier: asyncio.Event) -> dict[str, Any]:
    await barrier.wait()
    send_time = time.time()
    start = time.perf_counter()
    try:
        result = await asyncio.wait_for(
            smart_path.get_swap_in_path(AMOUNT_WEI, WBTC_ADDRESS, UNI_ADDRESS),
            timeout=LIB_TIMEOUT_SECONDS,
        )
        return {
            "send_time": send_time,
            "duration": time.perf_counter() - start,
            "result": result,
        }
    except Exception as exc:
        return {
            "send_time": send_time,
            "duration": time.perf_counter() - start,
            "error": repr(exc),
        }


async def etherscan_block_for_timestamp(
        session: aiohttp.ClientSession,
        api_key: str,
        timestamp: int) -> dict[str, Any]:
    params = {
        "chainid": "1",
        "module": "block",
        "action": "getblocknobytime",
        "timestamp": str(timestamp),
        "closest": "before",
        "apikey": api_key,
    }
    try:
        async with session.get(ETHERSCAN_API_URL, params=params) as response:
            raw_body = await response.text()
            return {"status": response.status, "body": raw_body}
    except Exception as exc:
        return {"error": repr(exc)}


def parse_etherscan_block(result: dict[str, Any]) -> int | None:
    if "error" in result:
        return None
    try:
        payload = json.loads(result["body"])
    except (KeyError, json.JSONDecodeError):
        return None
    if payload.get("status") != "1":
        return None
    try:
        return int(payload["result"])
    except (KeyError, TypeError, ValueError):
        return None


def parse_api_quote(result: dict[str, Any]) -> dict[str, Any]:
    if "error" in result or "body" not in result:
        return {}
    try:
        payload = json.loads(result["body"])
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


async def main() -> None:
    logger = setup_logging()
    log_run_header(logger)
    try:
        await run_benchmark(logger)
    finally:
        log_run_footer(logger)


async def run_benchmark(logger: logging.Logger) -> None:
    try:
        config = load_config()
    except ValueError as exc:
        logger.error("%s", exc)
        return

    logger.info("Token in:  WBTC %s (%d decimals)", WBTC_ADDRESS, WBTC_DECIMALS)
    logger.info("Token out: UNI  %s (%d decimals)", UNI_ADDRESS, UNI_DECIMALS)
    logger.info("Amount in: %d base units (0.1 WBTC)", AMOUNT_WEI)
    logger.info("RPC endpoint host: %s", urlparse(config.rpc_endpoint).hostname)
    logger.info("Uniswap API key: configured")
    logger.info("Etherscan API key: configured")
    logger.info("Swapper: %s", config.swapper)
    logger.info("Uniswap API protocols: %s", config.protocols or "default (all)")
    logger.info(
        "Credit limiter: interval=%ss, max_credits=%s, method_credits=%s",
        CREDIT_INTERVAL_SECONDS,
        MAX_CREDITS,
        METHOD_CREDITS,
    )

    w3 = AsyncWeb3(AsyncHTTPProvider(config.rpc_endpoint, {"timeout": RPC_TIMEOUT_SECONDS}))
    credit_limiter = SmartRateLimiter(
        CREDIT_INTERVAL_SECONDS,
        max_credits=MAX_CREDITS,
        method_credits=METHOD_CREDITS,
    )

    try:
        creation_start = time.perf_counter()
        smart_path = await SmartPath.create(w3, smart_rate_limiter=credit_limiter)
        creation_duration = time.perf_counter() - creation_start
        logger.info("SmartPath creation duration: %.3f s", creation_duration)
        logger.info("SmartPath chain_id: %s", smart_path.chain_id)
        logger.info("SmartPath pivots: %s", [token.address for token in smart_path.pivots])
    except Exception as exc:
        logger.exception("SmartPath creation failed: %s", exc)
        await w3.provider.disconnect()
        return

    try:
        async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=API_TIMEOUT_SECONDS),
                trust_env=True) as session:
            try:
                rpc_block_before = await w3.eth.block_number
                logger.info("RPC block before request: %s", rpc_block_before)
            except Exception as exc:
                logger.exception("Could not read the RPC block before the request: %s", exc)
                rpc_block_before = None

            barrier = asyncio.Event()
            api_task = asyncio.create_task(uniswap_api_quote(session, config, barrier))
            lib_task = asyncio.create_task(smart_path_quote(smart_path, barrier))

            # Let both tasks reach the barrier before releasing them together.
            await asyncio.sleep(0)
            start_time = time.time()
            logger.info("Common send timestamp: %s (unix %.6f)", iso_timestamp(start_time), start_time)
            barrier.set()

            api_result, lib_result = await asyncio.gather(api_task, lib_task)

            try:
                rpc_block_after = await w3.eth.block_number
                logger.info("RPC block after response: %s", rpc_block_after)
            except Exception as exc:
                logger.exception("Could not read the RPC block after the response: %s", exc)
                rpc_block_after = None

            logger.info("-" * 100)
            logger.info(
                "Uniswap API send time: %s (unix %.6f)",
                iso_timestamp(api_result["send_time"]),
                api_result["send_time"],
            )
            logger.info(
                "SmartPath send time: %s (unix %.6f)",
                iso_timestamp(lib_result["send_time"]),
                lib_result["send_time"],
            )
            logger.info("Send time delta: %.6f s", abs(api_result["send_time"] - lib_result["send_time"]))
            logger.info("Uniswap API duration: %.3f s", api_result.get("duration", 0.0))
            logger.info("SmartPath duration: %.3f s", lib_result.get("duration", 0.0))

            if "error" in api_result:
                logger.error("Uniswap API error: %s", api_result["error"])
            else:
                logger.info("Uniswap API status: %s", api_result.get("status"))
                logger.info("Uniswap API raw response:\n%s", api_result.get("body"))

            if "error" in lib_result:
                logger.error("SmartPath error: %s", lib_result["error"])
            else:
                logger.info("SmartPath result:\n%s", json_dumps(lib_result.get("result")))

            api_payload = parse_api_quote(api_result)
            api_quote = api_payload.get("quote", {}) if isinstance(api_payload.get("quote"), dict) else {}
            api_output = to_int(
                api_quote.get("output", {}).get("amount")
                if isinstance(api_quote.get("output"), dict)
                else None
            )
            api_block = to_int(api_quote.get("blockNumber"))
            api_routing = api_payload.get("routing")
            api_request_id = api_payload.get("requestId")
            api_slippage = api_quote.get("slippageTolerance", api_quote.get("slippage"))
            api_gas_fee = api_quote.get("gasFee")
            api_gas_fee_usd = api_quote.get("gasFeeUSD")
            api_classic_gas_usd = api_quote.get("classicGasUseEstimateUSD")
            api_price_difference = api_quote.get("priceDifference")
            api_minimum_output = to_int(
                api_quote.get("output", {}).get("minimumAmount")
                if isinstance(api_quote.get("output"), dict)
                else None
            )
            api_aggregated_outputs = api_quote.get("aggregatedOutputs")

            lib_results = lib_result.get("result") or ()
            lib_output = sum(to_int(item.get("estimate")) or 0 for item in lib_results)

            logger.info("-" * 100)
            logger.info("Uniswap API routing: %s", api_routing)
            logger.info("Uniswap API requestId: %s", api_request_id)
            logger.info("Uniswap API slippageTolerance: %s", api_slippage)
            logger.info("Uniswap API gasFee: %s wei", api_gas_fee)
            logger.info("Uniswap API gasFeeUSD: %s", api_gas_fee_usd)
            logger.info("Uniswap API classicGasUseEstimateUSD: %s", api_classic_gas_usd)
            logger.info("Uniswap API priceDifference: %s", api_price_difference)
            logger.info(
                "Uniswap API output (expected): %s base units (%s UNI)",
                api_output,
                format_units(api_output, UNI_DECIMALS),
            )
            logger.info(
                "Uniswap API output (minimum): %s base units (%s UNI)",
                api_minimum_output,
                format_units(api_minimum_output, UNI_DECIMALS),
            )
            logger.info("Uniswap API aggregatedOutputs:\n%s", json_dumps(api_aggregated_outputs))
            logger.info(
                "SmartPath output: %s base units (%s UNI)",
                lib_output,
                format_units(lib_output, UNI_DECIMALS),
            )
            logger.info("SmartPath gas estimate: not implemented (with_gas_estimate raises NotImplementedError)")

            if api_output and lib_output:
                diff = api_output - lib_output
                diff_bps = Decimal(diff) / Decimal(api_output) * Decimal(10_000)
                logger.info(
                    "Output difference vs API expected (API - SmartPath): %s base units (%s UNI, %s bps)",
                    diff,
                    format_units(diff, UNI_DECIMALS),
                    f"{diff_bps:.4f}",
                )
            else:
                logger.info("Output difference vs API expected: not computed (missing output)")

            if api_minimum_output and lib_output:
                diff_min = api_minimum_output - lib_output
                diff_min_bps = Decimal(diff_min) / Decimal(api_minimum_output) * Decimal(10_000)
                logger.info(
                    "Output difference vs API minimum (API - SmartPath): %s base units (%s UNI, %s bps)",
                    diff_min,
                    format_units(diff_min, UNI_DECIMALS),
                    f"{diff_min_bps:.4f}",
                )
            else:
                logger.info("Output difference vs API minimum: not computed (missing output)")

            logger.info("-" * 100)
            etherscan_result = await etherscan_block_for_timestamp(
                session,
                config.etherscan_api_key,
                int(start_time),
            )
            logger.info("Etherscan response:\n%s", json_dumps(etherscan_result))
            etherscan_block = parse_etherscan_block(etherscan_result)
            logger.info("Etherscan block at send timestamp: %s", etherscan_block)
            logger.info("Uniswap API blockNumber: %s", api_block)

            if etherscan_block is not None and api_block is not None:
                lag = etherscan_block - api_block
                logger.info("API block lag (etherscan_block - api_block): %d", lag)
                if lag > 0:
                    logger.info("=> The Uniswap API quoted a block %d block(s) behind the send-time block.", lag)
                elif lag == 0:
                    logger.info("=> The Uniswap API quoted the send-time block.")
                else:
                    logger.info("=> The Uniswap API quoted a block %d block(s) ahead of the send-time block.", -lag)
            else:
                logger.info("API block lag: not computed (missing block number)")

            if rpc_block_before is not None and api_block is not None:
                logger.info("API block vs RPC block before request: %d", api_block - rpc_block_before)
            if rpc_block_after is not None and api_block is not None:
                logger.info("API block vs RPC block after response: %d", api_block - rpc_block_after)
            if rpc_block_before is not None and rpc_block_after is not None:
                logger.info("RPC block range during request: %s -> %s", rpc_block_before, rpc_block_after)

    finally:
        try:
            await w3.provider.disconnect()
        except Exception as exc:
            logger.debug("Could not disconnect the RPC provider: %s", exc)


if __name__ == "__main__":
    asyncio.run(main())
