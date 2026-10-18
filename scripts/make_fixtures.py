"""Synthetic market fixture generator for Warrant X-Ray.

Produces labeled synthetic Bursa Malaysia warrant snapshots including normal calls/puts,
varied expiries, and intentional edge cases:
- Crossed quotes (bid > ask)
- Missing bids (bid is None)
- Duplicate warrant codes
- Non-positive strike or underlying price (invalid rows)
- Expired warrants

NEVER uses real market data. Output is explicitly tagged as synthetic.
"""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any


def generate_synthetic_fixture(as_of_date: date | None = None) -> dict[str, Any]:
    """Generate a comprehensive synthetic market snapshot."""
    if as_of_date is None:
        as_of_date = date(2026, 10, 16)

    as_of_iso = datetime(
        as_of_date.year, as_of_date.month, as_of_date.day, 9, 30, 0, tzinfo=timezone.utc
    ).isoformat()

    underlyings = [
        {"ticker": "MAYBANK", "code": "1155", "name": "Malayan Banking Berhad", "price": 10.50},
        {"ticker": "TENAGA", "code": "5347", "name": "Tenaga Nasional Berhad", "price": 14.20},
        {"ticker": "INARI", "code": "0166", "name": "Inari Amertron Berhad", "price": 3.80},
        {"ticker": "YTL", "code": "4677", "name": "YTL Corporation Berhad", "price": 3.40},
        {"ticker": "CIMB", "code": "1023", "name": "CIMB Group Holdings Berhad", "price": 8.10},
    ]

    issuers = ["CGS", "RHB", "KENANGA", "MBSB", "MACQUARIE"]
    rows: list[dict[str, Any]] = []

    # 1. Normal warrants across underlyings
    counter = 100
    for und in underlyings:
        ticker = und["ticker"]
        u_price = und["price"]

        for i, issuer in enumerate(issuers):
            counter += 1
            call_code = f"{und['code']}{chr(65 + i)}1"
            # Call warrant
            days_left = 30 + (i * 45)
            expiry = (as_of_date + timedelta(days=days_left)).strftime("%Y-%m-%d")
            strike = round(u_price * (0.90 + (i * 0.05)), 2)
            ratio = 3.0 + i
            intrinsic = max(0.0, (u_price - strike) / ratio)
            time_val = round(0.04 + (i * 0.015), 3)
            theo_mid = round(intrinsic + time_val, 3)
            bid = round(max(0.005, theo_mid - 0.005), 3)
            ask = round(bid + 0.010, 3)

            rows.append({
                "code": call_code,
                "issuer": issuer,
                "type": "call",
                "underlying_ticker": ticker,
                "expiry_date": expiry,
                "strike": strike,
                "ratio_raw": ratio,
                "underlying_bid": u_price,
                "bid": bid,
                "ask": ask,
                "bid_volume": 50000 + (i * 20000),
                "ask_volume": 60000 + (i * 15000),
                "traded_volume": 120000,
                "last_price": round((bid + ask) / 2, 3),
                "last_time": "09:28:15",
                "issuer_iv": 38.5,
                "issuer_eg": 4.2,
                "issuer_delta": 0.52,
                "issuer_premium": 8.5,
                "issuer_theta_raw": -0.004,
                "sensitivity_ticks": 1.2,
                "moneyness": round(u_price / strike, 4),
                "indicators": {"active": True, "liquidity": True},
                "valid": True,
                "raw_json": {"source": "synthetic_generator"},
            })

            # Put warrant
            counter += 1
            put_code = f"{und['code']}{chr(72 + i)}2"
            p_strike = round(u_price * (1.10 - (i * 0.05)), 2)
            p_intrinsic = max(0.0, (p_strike - u_price) / ratio)
            p_theo = round(p_intrinsic + time_val, 3)
            p_bid = round(max(0.005, p_theo - 0.005), 3)
            p_ask = round(p_bid + 0.010, 3)

            rows.append({
                "code": put_code,
                "issuer": issuer,
                "type": "put",
                "underlying_ticker": ticker,
                "expiry_date": expiry,
                "strike": p_strike,
                "ratio_raw": ratio,
                "underlying_bid": u_price,
                "bid": p_bid,
                "ask": p_ask,
                "bid_volume": 35000,
                "ask_volume": 42000,
                "traded_volume": 85000,
                "last_price": round((p_bid + p_ask) / 2, 3),
                "last_time": "09:29:00",
                "issuer_iv": 41.0,
                "issuer_eg": -3.8,
                "issuer_delta": -0.48,
                "issuer_premium": 9.2,
                "issuer_theta_raw": -0.005,
                "sensitivity_ticks": 1.4,
                "moneyness": round(p_strike / u_price, 4),
                "indicators": {"active": True, "liquidity": True},
                "valid": True,
                "raw_json": {"source": "synthetic_generator"},
            })

    # 2. Edge Case: Crossed quote (bid > ask)
    rows.append({
        "code": "5188CX",
        "issuer": "MACQUARIE",
        "type": "call",
        "underlying_ticker": "MAYBANK",
        "expiry_date": (as_of_date + timedelta(days=45)).strftime("%Y-%m-%d"),
        "strike": 10.50,
        "ratio_raw": 4.0,
        "underlying_bid": 10.50,
        "bid": 0.120,
        "ask": 0.090,  # crossed!
        "bid_volume": 10000,
        "ask_volume": 10000,
        "traded_volume": 20000,
        "last_price": 0.100,
        "last_time": "09:15:00",
        "issuer_iv": 35.0,
        "issuer_eg": 4.0,
        "issuer_delta": 0.50,
        "issuer_premium": 5.0,
        "issuer_theta_raw": -0.003,
        "sensitivity_ticks": 1.0,
        "moneyness": 1.0,
        "indicators": {"crossed": True},
        "valid": False,
        "raw_json": {"error": "crossed_quote"},
    })

    # 3. Edge Case: Missing Bid
    rows.append({
        "code": "5188MB",
        "issuer": "RHB",
        "type": "call",
        "underlying_ticker": "MAYBANK",
        "expiry_date": (as_of_date + timedelta(days=60)).strftime("%Y-%m-%d"),
        "strike": 11.20,
        "ratio_raw": 5.0,
        "underlying_bid": 10.50,
        "bid": None,  # no bid
        "ask": 0.050,
        "bid_volume": None,
        "ask_volume": 20000,
        "traded_volume": 5000,
        "last_price": 0.045,
        "last_time": "09:05:00",
        "issuer_iv": None,
        "issuer_eg": None,
        "issuer_delta": None,
        "issuer_premium": None,
        "issuer_theta_raw": None,
        "sensitivity_ticks": None,
        "moneyness": 0.9375,
        "indicators": {"missing_bid": True},
        "valid": True,
        "raw_json": {"note": "no_buyer_quote"},
    })

    # 4. Edge Case: Duplicate code (first row will be kept)
    duplicate_row = dict(rows[0])
    duplicate_row["ask"] = round(duplicate_row["ask"] + 0.02, 3)
    duplicate_row["raw_json"] = {"note": "duplicate_entry"}
    rows.append(duplicate_row)

    # 5. Edge Case: Non-positive strike (invalid row)
    rows.append({
        "code": "5188NS",
        "issuer": "KENANGA",
        "type": "call",
        "underlying_ticker": "MAYBANK",
        "expiry_date": (as_of_date + timedelta(days=45)).strftime("%Y-%m-%d"),
        "strike": 0.0,  # invalid strike
        "ratio_raw": 4.0,
        "underlying_bid": 10.50,
        "bid": 0.080,
        "ask": 0.090,
        "bid_volume": 10000,
        "ask_volume": 10000,
        "traded_volume": 0,
        "last_price": 0.085,
        "last_time": "09:00:00",
        "issuer_iv": None,
        "issuer_eg": None,
        "issuer_delta": None,
        "issuer_premium": None,
        "issuer_theta_raw": None,
        "sensitivity_ticks": None,
        "moneyness": None,
        "indicators": {},
        "valid": False,
        "raw_json": {"error": "non_positive_strike"},
    })

    # 6. Edge Case: Expired warrant (expiry prior to as_of_date)
    rows.append({
        "code": "5188EX",
        "issuer": "CGS",
        "type": "call",
        "underlying_ticker": "MAYBANK",
        "expiry_date": (as_of_date - timedelta(days=10)).strftime("%Y-%m-%d"),
        "strike": 10.00,
        "ratio_raw": 4.0,
        "underlying_bid": 10.50,
        "bid": 0.005,
        "ask": 0.010,
        "bid_volume": 0,
        "ask_volume": 0,
        "traded_volume": 0,
        "last_price": 0.005,
        "last_time": "09:00:00",
        "issuer_iv": None,
        "issuer_eg": None,
        "issuer_delta": None,
        "issuer_premium": None,
        "issuer_theta_raw": None,
        "sensitivity_ticks": None,
        "moneyness": 1.05,
        "indicators": {"expired": True},
        "valid": True,
        "raw_json": {"note": "expired"},
    })

    return {
        "is_synthetic": True,
        "synthetic_notice": "SYNTHETIC MARKET SNAPSHOT FOR TESTING ONLY. NOT REAL BURSA DATA.",
        "id": 1,
        "fetched_at": as_of_iso,
        "source_last_update": as_of_iso,
        "row_count": len(rows),
        "ok": True,
        "note": "Complete synthetic test fixture with varied underlyings and edge cases",
        "suspect": False,
        "quality_json": {
            "crossed_quotes_count": 1,
            "missing_bid_count": 1,
            "duplicate_count": 1,
            "invalid_rows_count": 1,
            "expired_count": 1,
        },
        "underlyings": underlyings,
        "rows": rows,
    }


def main() -> None:
    """Generate and write synthetic fixtures to file."""
    parser = argparse.ArgumentParser(description="Generate synthetic warrant market fixture")
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("tests/fixtures/synthetic_snapshot.json"),
        help="Target output path for JSON fixture",
    )
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    fixture = generate_synthetic_fixture()

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(fixture, f, indent=2)

    print(f"Generated synthetic fixture at {args.output} with {fixture['row_count']} rows.")


if __name__ == "__main__":
    main()
