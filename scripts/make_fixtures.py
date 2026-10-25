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
        # Banking & Financial Services
        {"ticker": "MAYBANK", "code": "1155", "name": "Malayan Banking Berhad", "price": 10.50},
        {"ticker": "PBBANK", "code": "1295", "name": "Public Bank Berhad", "price": 4.50},
        {"ticker": "CIMB", "code": "1023", "name": "CIMB Group Holdings Berhad", "price": 8.10},
        {"ticker": "HLBANK", "code": "5819", "name": "Hong Leong Bank Berhad", "price": 20.80},
        {"ticker": "RHBBANK", "code": "1066", "name": "RHB Bank Berhad", "price": 6.45},
        {"ticker": "AMBANK", "code": "1015", "name": "AMMB Holdings Berhad", "price": 5.15},
        {"ticker": "BURSA", "code": "1818", "name": "Bursa Malaysia Berhad", "price": 9.30},
        {"ticker": "HLFG", "code": "1082", "name": "Hong Leong Financial Group Berhad", "price": 18.20},

        # Utilities & Infrastructure
        {"ticker": "TENAGA", "code": "5347", "name": "Tenaga Nasional Berhad", "price": 14.20},
        {"ticker": "YTL", "code": "4677", "name": "YTL Corporation Berhad", "price": 3.40},
        {"ticker": "YTLPOWR", "code": "6742", "name": "YTL Power International Berhad", "price": 4.80},
        {"ticker": "PETGAS", "code": "6033", "name": "Petronas Gas Berhad", "price": 18.00},
        {"ticker": "GASMSIA", "code": "5209", "name": "Gas Malaysia Berhad", "price": 3.65},
        {"ticker": "TIMECOM", "code": "5031", "name": "TIME dotCom Berhad", "price": 5.00},

        # Technology & Semiconductor
        {"ticker": "INARI", "code": "0166", "name": "Inari Amertron Berhad", "price": 3.80},
        {"ticker": "MYEG", "code": "0138", "name": "MyEG Services Berhad", "price": 0.90},
        {"ticker": "CTOS", "code": "5301", "name": "CTOS Digital Berhad", "price": 1.30},
        {"ticker": "FRONTKN", "code": "0128", "name": "Frontken Corporation Berhad", "price": 4.10},
        {"ticker": "GREATEC", "code": "0208", "name": "Greatech Technology Berhad", "price": 4.80},
        {"ticker": "D&O", "code": "7204", "name": "D&O Green Technologies Berhad", "price": 2.50},
        {"ticker": "VS", "code": "6963", "name": "V.S. Industry Berhad", "price": 1.15},
        {"ticker": "UNISEM", "code": "5005", "name": "Unisem (M) Berhad", "price": 3.40},

        # Energy & Oil & Gas
        {"ticker": "DIALOG", "code": "7277", "name": "Dialog Group Berhad", "price": 2.15},
        {"ticker": "HIBISCS", "code": "5199", "name": "Hibiscus Petroleum Berhad", "price": 2.20},
        {"ticker": "DAYANG", "code": "5141", "name": "Dayang Enterprise Holdings Berhad", "price": 2.40},
        {"ticker": "ARMADA", "code": "5210", "name": "Bumi Armada Berhad", "price": 0.55},
        {"ticker": "VELESTO", "code": "5243", "name": "Velesto Energy Berhad", "price": 0.20},
        {"ticker": "YINSON", "code": "7293", "name": "Yinson Holdings Berhad", "price": 2.70},

        # Plantations & Commodities
        {"ticker": "SIMEPLT", "code": "5285", "name": "SD Guthrie Berhad", "price": 4.60},
        {"ticker": "IOICORP", "code": "1961", "name": "IOI Corporation Berhad", "price": 3.90},
        {"ticker": "KLK", "code": "2445", "name": "Kuala Lumpur Kepong Berhad", "price": 21.50},
        {"ticker": "FGV", "code": "5222", "name": "FGV Holdings Berhad", "price": 1.25},
        {"ticker": "GENP", "code": "2291", "name": "Genting Plantations Berhad", "price": 5.60},
        {"ticker": "TAANN", "code": "5012", "name": "Ta Ann Holdings Berhad", "price": 4.10},

        # Telecommunications & Media
        {"ticker": "CELCOMDIGI", "code": "6947", "name": "CelcomDigi Berhad", "price": 3.75},
        {"ticker": "MAXIS", "code": "6012", "name": "Maxis Berhad", "price": 3.60},
        {"ticker": "AXIATA", "code": "6888", "name": "Axiata Group Berhad", "price": 2.40},
        {"ticker": "TM", "code": "4863", "name": "Telekom Malaysia Berhad", "price": 6.70},
        {"ticker": "ASTRO", "code": "6399", "name": "Astro Malaysia Holdings Berhad", "price": 0.28},

        # Construction, Property & Building Materials
        {"ticker": "GAMUDA", "code": "5398", "name": "Gamuda Berhad", "price": 8.80},
        {"ticker": "SUNWAY", "code": "5211", "name": "Sunway Berhad", "price": 4.50},
        {"ticker": "IJM", "code": "3336", "name": "IJM Corporation Berhad", "price": 3.10},
        {"ticker": "PMETAL", "code": "8869", "name": "Press Metal Aluminium Holdings Berhad", "price": 5.20},
        {"ticker": "SPSETIA", "code": "8664", "name": "S P Setia Berhad", "price": 1.35},
        {"ticker": "ECOWLD", "code": "8206", "name": "Eco World Development Group Berhad", "price": 1.75},
        {"ticker": "UEMS", "code": "5148", "name": "UEM Sunrise Berhad", "price": 1.05},
        {"ticker": "MAHSING", "code": "8583", "name": "Mah Sing Group Berhad", "price": 1.65},

        # Healthcare, Consumer, Aviation & Industrial
        {"ticker": "IHH", "code": "5225", "name": "IHH Healthcare Berhad", "price": 7.25},
        {"ticker": "KPJ", "code": "5878", "name": "KPJ Healthcare Berhad", "price": 2.10},
        {"ticker": "TOPGLOV", "code": "7113", "name": "Top Glove Corporation Bhd", "price": 1.05},
        {"ticker": "HARTA", "code": "5168", "name": "Hartalega Holdings Berhad", "price": 3.30},
        {"ticker": "MRDIY", "code": "5296", "name": "MR D.I.Y. Group (M) Berhad", "price": 2.10},
        {"ticker": "GENTING", "code": "3182", "name": "Genting Berhad", "price": 4.20},
        {"ticker": "GENM", "code": "4715", "name": "Genting Malaysia Berhad", "price": 2.45},
        {"ticker": "AIRASIA", "code": "5099", "name": "Capital A Berhad", "price": 0.98},
        {"ticker": "PCHEM", "code": "5183", "name": "Petronas Chemicals Group Berhad", "price": 5.60},
        {"ticker": "MISC", "code": "3816", "name": "MISC Berhad", "price": 8.10},
        {"ticker": "WESTPORTS", "code": "5246", "name": "Westports Holdings Berhad", "price": 4.30},
    ]

    issuers = ["CGS", "RHB", "KENANGA", "MBSB", "MACQUARIE"]
    rows: list[dict[str, Any]] = []

    # Benchmark / Sample Warrant (115510, MAYBANK-C28)
    rows.append({
        "code": "115510",
        "issuer": "CGS",
        "type": "call",
        "underlying_ticker": "MAYBANK",
        "expiry_date": "2027-06-30",
        "strike": 10.50,
        "ratio_raw": 4.0,
        "underlying_bid": 10.20,
        "bid": 0.150,
        "ask": 0.155,
        "bid_volume": 120000,
        "ask_volume": 150000,
        "traded_volume": 250000,
        "last_price": 0.152,
        "last_time": "09:30:00",
        "issuer_iv": 42.5,
        "issuer_eg": 5.2,
        "issuer_delta": 0.52,
        "issuer_premium": 8.5,
        "issuer_theta_raw": -0.002,
        "sensitivity_ticks": 1.1,
        "moneyness": round(10.20 / 10.50, 4),
        "indicators": {"active": True, "liquidity": True},
        "valid": True,
        "raw_json": {"source": "synthetic_generator", "note": "canonical_sample_warrant"},
    })

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
