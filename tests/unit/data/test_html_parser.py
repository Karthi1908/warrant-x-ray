"""Unit tests for deterministic HTML warrant table parser (T116, FR-007, Principle I)."""

from __future__ import annotations

import pytest
from warrantx.data.html_parser import parse_warrant_table_html


SAMPLE_WARRANT_HTML = """
<html>
<body>
    <div class="content">
        <h1>Bursa Structured Warrants Screener</h1>
        <table class="warrant-table" id="warrantsTable">
            <thead>
                <tr>
                    <th>Code</th>
                    <th>Issuer</th>
                    <th>Type</th>
                    <th>Underlying</th>
                    <th>Strike</th>
                    <th>Ratio</th>
                    <th>Expiry Date</th>
                    <th>Bid</th>
                    <th>Ask</th>
                    <th>Underlying Price</th>
                    <th>IV (%)</th>
                    <th>Delta</th>
                    <th>Eff Gearing</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>115510</td>
                    <td>CGS</td>
                    <td>Call</td>
                    <td>MAYBANK</td>
                    <td>10.50</td>
                    <td>4.0</td>
                    <td>2027-06-30</td>
                    <td>0.150</td>
                    <td>0.155</td>
                    <td>10.20</td>
                    <td>42.0%</td>
                    <td>0.52</td>
                    <td>5.20</td>
                </tr>
                <tr>
                    <td>51881C</td>
                    <td>CGS</td>
                    <td>Call</td>
                    <td>MAYBANK</td>
                    <td>10.50</td>
                    <td>4.0</td>
                    <td>2026-12-31</td>
                    <td>0.080</td>
                    <td>0.090</td>
                    <td>10.20</td>
                    <td>45.5%</td>
                    <td>0.35</td>
                    <td>6.80</td>
                </tr>
                <tr>
                    <td>0166A1</td>
                    <td>KAF</td>
                    <td>Put</td>
                    <td>INARI</td>
                    <td>3.20</td>
                    <td>3.0</td>
                    <td>2026-10-30</td>
                    <td>0.120</td>
                    <td>0.125</td>
                    <td>3.00</td>
                    <td>50.0%</td>
                    <td>-0.45</td>
                    <td>4.50</td>
                </tr>
            </tbody>
        </table>
    </div>
</body>
</html>
"""

MALFORMED_HTML = """
<div>
    <table>
        <tr><th>Unrelated</th><th>Header</th></tr>
        <tr><td>Data1</td><td>Data2</td></tr>
    </table>
</div>
"""


def test_parse_warrant_table_html_extracts_rows():
    rows = parse_warrant_table_html(SAMPLE_WARRANT_HTML)
    assert len(rows) == 3

    r0 = rows[0]
    assert r0["code"] == "115510"
    assert r0["issuer"] == "CGS"
    assert r0["type"] == "call"
    assert r0["underlying_ticker"] == "MAYBANK"
    assert r0["strike"] == 10.50
    assert r0["ratio_raw"] == 4.0
    assert r0["expiry_date"] == "2027-06-30"
    assert r0["bid"] == 0.150
    assert r0["ask"] == 0.155
    assert r0["underlying_bid"] == 10.20
    assert r0["issuer_iv"] == 42.0
    assert r0["issuer_delta"] == 0.52
    assert r0["issuer_eg"] == 5.20


def test_parse_warrant_table_html_put_warrant():
    rows = parse_warrant_table_html(SAMPLE_WARRANT_HTML)
    put_row = [r for r in rows if r["code"] == "0166A1"][0]
    assert put_row["type"] == "put"
    assert put_row["underlying_ticker"] == "INARI"
    assert put_row["issuer_delta"] == -0.45


def test_parse_warrant_table_html_empty_or_malformed():
    assert parse_warrant_table_html("") == []
    assert parse_warrant_table_html("<html><body>No tables here</body></html>") == []
    # Table without warrant headers returns empty list
    assert parse_warrant_table_html(MALFORMED_HTML) == []


def test_parse_warrant_table_html_handles_missing_cells_gracefully():
    partial_html = """
    <table>
        <tr><th>Code</th><th>Strike</th><th>Ratio</th><th>Expiry</th><th>Type</th><th>Issuer</th><th>Underlying</th></tr>
        <tr><td>9999AA</td><td>-</td><td>N/A</td><td>2027-01-01</td><td>Call</td><td>RHB</td><td>CIMB</td></tr>
    </table>
    """
    rows = parse_warrant_table_html(partial_html)
    assert len(rows) == 1
    assert rows[0]["code"] == "9999AA"
    assert rows[0]["strike"] is None
    assert rows[0]["ratio_raw"] is None
    assert rows[0]["type"] == "call"
