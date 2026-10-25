"""Deterministic HTML table parser for Bursa warrant screener data (T118, FR-007, Principle I).

Strictly deterministic Python parsing using BeautifulSoup:
0% LLM extraction and 0% LLM math.
"""

from __future__ import annotations

import math
import re
from typing import Any
from bs4 import BeautifulSoup

HEADER_MAPPINGS: dict[str, str] = {
    "code": "code",
    "warrant": "code",
    "warrant code": "code",
    "stock code": "code",
    "symbol": "code",
    "issuer": "issuer",
    "type": "type",
    "call/put": "type",
    "warrant type": "type",
    "underlying": "underlying_ticker",
    "underlying ticker": "underlying_ticker",
    "underlying stock": "underlying_ticker",
    "mother share": "underlying_ticker",
    "share": "underlying_ticker",
    "strike": "strike",
    "strike price": "strike",
    "exercise price": "strike",
    "ratio": "ratio_raw",
    "exercise ratio": "ratio_raw",
    "conversion ratio": "ratio_raw",
    "expiry": "expiry_date",
    "expiry date": "expiry_date",
    "maturity": "expiry_date",
    "maturity date": "expiry_date",
    "expiration": "expiry_date",
    "bid": "bid",
    "buy": "bid",
    "bid price": "bid",
    "ask": "ask",
    "sell": "ask",
    "offer": "ask",
    "ask price": "ask",
    "underlying price": "underlying_bid",
    "underlying bid": "underlying_bid",
    "mother price": "underlying_bid",
    "share price": "underlying_bid",
    "iv (%)": "issuer_iv",
    "iv": "issuer_iv",
    "implied vol": "issuer_iv",
    "implied volatility": "issuer_iv",
    "issuer iv": "issuer_iv",
    "delta": "issuer_delta",
    "issuer delta": "issuer_delta",
    "eff gearing": "issuer_eg",
    "effective gearing": "issuer_eg",
    "eff. gearing": "issuer_eg",
    "eg": "issuer_eg",
    "issuer eg": "issuer_eg",
    "premium (%)": "issuer_premium",
    "premium": "issuer_premium",
}

NUMERIC_FIELDS = {
    "strike",
    "ratio_raw",
    "bid",
    "ask",
    "underlying_bid",
    "issuer_iv",
    "issuer_delta",
    "issuer_eg",
    "issuer_premium",
}

PLACEHOLDER_STRINGS = {"-", "n/a", "na", "null", "none", "", "--"}


def _clean_header(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip().lower()
    return cleaned


def _clean_float(val: Any) -> float | None:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        if math.isnan(val) or math.isinf(val):
            return None
        return float(val)
    s = str(val).strip()
    if s.lower() in PLACEHOLDER_STRINGS:
        return None
    if s.endswith("%"):
        s = s[:-1].strip()
    # Remove commas from formatted numbers like "1,050.00"
    s = s.replace(",", "")
    try:
        f = float(s)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except ValueError:
        return None


def parse_warrant_table_html(html_content: str) -> list[dict[str, Any]]:
    """Parse HTML tables deterministically to extract warrant market data rows.

    Returns a list of raw extracted row dictionaries compatible with warrant normalization.
    """
    if not html_content or not html_content.strip():
        return []

    soup = BeautifulSoup(html_content, "html.parser")
    tables = soup.find_all("table")
    if not tables:
        return []

    extracted_rows: list[dict[str, Any]] = []

    for table in tables:
        # Check table headers in <thead> or first <tr>
        header_row = table.find("thead")
        if header_row:
            th_cells = header_row.find_all(["th", "td"])
        else:
            first_tr = table.find("tr")
            th_cells = first_tr.find_all(["th", "td"]) if first_tr else []

        if not th_cells:
            continue

        col_map: dict[int, str] = {}
        for idx, cell in enumerate(th_cells):
            cleaned = _clean_header(cell.get_text())
            if cleaned in HEADER_MAPPINGS:
                col_map[idx] = HEADER_MAPPINGS[cleaned]
            else:
                # Fuzzy check if cleaned text contains one of the mapping keys
                for key, mapped_field in HEADER_MAPPINGS.items():
                    if key in cleaned:
                        col_map[idx] = mapped_field
                        break

        # Check if table has essential warrant columns
        required_cols = {"code"}
        mapped_values = set(col_map.values())
        if not required_cols.issubset(mapped_values):
            continue
        # Also require at least one other warrant field to avoid matching arbitrary tables with "Code"
        secondary_cols = {"strike", "ratio_raw", "expiry_date", "type", "issuer", "underlying_ticker"}
        if not (mapped_values & secondary_cols):
            continue

        # Extract data rows from <tbody> or subsequent <tr> elements
        tbody = table.find("tbody")
        row_elements = tbody.find_all("tr") if tbody else table.find_all("tr")[1:]

        for tr in row_elements:
            cells = tr.find_all(["td", "th"])
            if not cells:
                continue

            row_dict: dict[str, Any] = {}
            for idx, col_name in col_map.items():
                if idx < len(cells):
                    raw_text = cells[idx].get_text().strip()
                    if col_name in NUMERIC_FIELDS:
                        row_dict[col_name] = _clean_float(raw_text)
                    elif col_name == "type":
                        lower_val = raw_text.lower()
                        if "call" in lower_val:
                            row_dict[col_name] = "call"
                        elif "put" in lower_val:
                            row_dict[col_name] = "put"
                        else:
                            row_dict[col_name] = raw_text
                    elif col_name in ("code", "issuer", "underlying_ticker"):
                        row_dict[col_name] = raw_text.upper() if raw_text else None
                    else:
                        row_dict[col_name] = raw_text if raw_text not in PLACEHOLDER_STRINGS else None

            # Only add rows that have a code
            if row_dict.get("code"):
                extracted_rows.append(row_dict)

    return extracted_rows
