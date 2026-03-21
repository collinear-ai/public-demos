"""Verifier: Coca-Cola (KO) FY2022-FY2024 Investment Manager Analysis.

Loads reference data from ko_golden.xlsx and verifies the agent's submitted
Google Sheet against it. All expected values are derived from the golden file.

Framework-compatible: implements verify(run_artifacts) -> VerifierResult.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from collinear.core.run_artifacts import RunArtifacts
from collinear.core.verifier import VerifierResult

from . import _common

GOLDEN_PATH = Path(__file__).parent / "ko_golden.xlsx"

# Domain concept keywords — only checked if they actually appear in the golden.
_CONCEPT_CANDIDATES = [
    ("volume", "Volume analysis"),
    ("price", "Price/mix analysis"),
    ("organic", "Organic revenue concept"),
    ("concentrate", "Concentrate operations"),
    ("finished", "Finished product operations"),
    ("north america", "North America segment"),
    ("latin america", "Latin America segment"),
    ("emea", "EMEA segment"),
    ("asia pacific", "Asia Pacific segment"),
    ("free cash flow", "Free Cash Flow concept"),
    ("ebitda", "EBITDA metric"),
    ("cash conversion", "Cash conversion cycle"),
    ("working capital", "Working capital efficiency"),
    ("dividend", "Dividend / shareholder returns"),
    ("repurchase", "Share repurchase"),
    ("ev/ebitda", "EV/EBITDA multiple"),
    ("enterprise value", "Enterprise value"),
    ("net debt", "Net debt methodology"),
    ("market cap", "Market capitalization"),
    ("10-k", "10-K filing reference"),
    ("refranchis", "Refranchising / bottling"),
    ("irs", "IRS tax litigation"),
    ("capex", "Capital expenditure"),
]


# ═════════════════════════════════════════════════════════════════════════
# HELPERS
# ═════════════════════════════════════════════════════════════════════════


def _find_sheet(
    sheets_data: dict[str, list[list[Any]]],
    *keywords: str,
) -> tuple[str, list[list[Any]]]:
    """Find the best-matching sheet by keyword scoring.

    When multiple sheets match all keywords, prefer shorter names (golden-named
    sheets over verbose working sheets).
    """
    candidates: list[tuple[int, int, str]] = []
    for name in sheets_data:
        name_lower = name.lower()
        if all(kw in name_lower for kw in keywords):
            hits = sum(1 for kw in keywords if kw in name_lower)
            candidates.append((hits, -len(name), name))
    if not candidates:
        return "", []
    candidates.sort(reverse=True)
    best = candidates[0][2]
    return best, sheets_data[best]


def _extract_row_values(row: list[Any]) -> list[float | None]:
    """Parse all cells in a row as floats."""
    return [_common.try_float(v) for v in row]


# ═════════════════════════════════════════════════════════════════════════
# CROSS-VALIDATION CHECKS
# ═════════════════════════════════════════════════════════════════════════


def _check_segment_revenue_totals(
    sheets_data: dict[str, list[list[Any]]],
    _all_numbers: list[float],
    _all_text: str,
) -> list[tuple[str, bool, str]]:
    """Verify geographic segment revenues sum to reported total net revenues."""
    results: list[tuple[str, bool, str]] = []
    _, rows = _find_sheet(sheets_data, "segment", "revenue")
    if not rows:
        _, rows = _find_sheet(sheets_data, "geographic")
    if not rows:
        _, rows = _find_sheet(sheets_data, "revenue")
    if not rows:
        results.append(("Segment revenue sheet found", False, "No segment revenue sheet"))
        return results

    segments = [
        "north america",
        "latin america",
        "emea",
        "asia pacific",
        "global ventures",
        "bottling",
    ]
    segment_rows: list[list[float | None]] = []
    total_row: list[float | None] = []

    for row in rows:
        label = ""
        for v in row:
            if isinstance(v, str) and len(v.strip()) > 2:
                label = v.strip().lower()
                break
        parsed = _extract_row_values(row)
        if any(seg in label for seg in segments) and len(label) < 50:
            segment_rows.append(parsed)
        elif ("total" in label and "net revenue" in label and segment_rows and not total_row) or (
            label == "total" and segment_rows and not total_row
        ):
            total_row = parsed

    if not segment_rows:
        results.append(("Revenue: segment rows found", False, "No geographic segment rows"))
        return results

    if not total_row:
        results.append(
            (
                "Revenue: total row found",
                False,
                "No 'Total Net Revenue' row after segments",
            )
        )
        return results

    any_match = False
    detail_parts: list[str] = []
    for col in range(1, 8):
        seg_sum = 0.0
        valid_segs = 0
        for seg_row in segment_rows:
            if col < len(seg_row) and seg_row[col] is not None and abs(seg_row[col]) > 100:
                seg_sum += seg_row[col]
                valid_segs += 1
        if valid_segs < 2:
            continue
        if (
            col < len(total_row)
            and total_row[col] is not None
            and abs(total_row[col]) > 100
            and _common.numbers_close(seg_sum, total_row[col], tol_pct=0.03, abs_tol=50)
        ):
            any_match = True
            detail_parts.append(f"col{col}: segments={seg_sum:,.0f} ≈ total={total_row[col]:,.0f}")

    results.append(
        (
            "Revenue: segments sum to total net revenues",
            any_match,
            "; ".join(detail_parts) if detail_parts else "No column where segment sum ≈ total",
        )
    )
    return results


def _check_organic_revenue_components(
    sheets_data: dict[str, list[list[Any]]],
    _all_numbers: list[float],
    _all_text: str,
) -> list[tuple[str, bool, str]]:
    """Verify organic revenue growth ≈ volume contribution + price/mix contribution."""
    results: list[tuple[str, bool, str]] = []
    _, rows = _find_sheet(sheets_data, "organic")
    if not rows:
        _, rows = _find_sheet(sheets_data, "revenue", "bridge")
    if not rows:
        results.append(("Organic revenue sheet found", False, "No organic revenue sheet"))
        return results

    organic_vals: list[float] = []
    volume_vals: list[float | None] = []
    price_vals: list[float | None] = []

    for row in rows:
        label = ""
        for v in row:
            if isinstance(v, str) and len(v.strip()) > 2:
                label = v.strip().lower()
                break
        parsed = _extract_row_values(row)
        if not any(v is not None for v in parsed):
            continue
        if ("organic" in label and "growth" in label) or label == "organic revenue":
            organic_vals = [v for v in parsed if v is not None]
        elif "volume" in label and "price" not in label and len(label) < 40:
            volume_vals = parsed
        elif ("price" in label or "mix" in label) and "volume" not in label and len(label) < 40:
            price_vals = parsed

    if not organic_vals:
        results.append(("Organic revenue: growth row found", False, "No organic growth row"))
        return results

    if not volume_vals or not price_vals:
        results.append(
            (
                "Organic revenue: volume and price/mix components found",
                False,
                f"Missing: {'volume' if not volume_vals else 'price/mix'} row",
            )
        )
        return results

    any_match = False
    details: list[str] = []
    for col in range(8):
        vol = volume_vals[col] if col < len(volume_vals) else None
        price = price_vals[col] if col < len(price_vals) else None
        if vol is None or price is None:
            continue
        component_sum = vol + price
        for org in organic_vals:
            if _common.numbers_close(org, component_sum, tol_pct=0.10, abs_tol=0.5):
                any_match = True
                details.append(
                    f"col{col}: vol({vol:.1f})+price({price:.1f})="
                    f"{component_sum:.1f} ≈ organic({org:.1f})"
                )
                break

    results.append(
        (
            "Organic revenue: volume + price/mix ≈ organic growth",
            any_match,
            "; ".join(details) if details else "No column where components sum ≈ organic growth",
        )
    )
    return results


def _check_ebitda_derivation(
    sheets_data: dict[str, list[list[Any]]],
    _all_numbers: list[float],
    _all_text: str,
) -> list[tuple[str, bool, str]]:
    """Verify EBITDA = Operating Income + D&A."""
    results: list[tuple[str, bool, str]] = []
    _, rows = _find_sheet(sheets_data, "ebitda")
    if not rows:
        _, rows = _find_sheet(sheets_data, "income", "statement")
    if not rows:
        _, rows = _find_sheet(sheets_data, "p&l")
    if not rows:
        results.append(("EBITDA sheet found", False, "No EBITDA or income sheet"))
        return results

    ebitda_vals: list[float | None] = []
    ebit_vals: list[float | None] = []
    da_vals: list[float | None] = []

    for row in rows:
        label = ""
        for v in row:
            if isinstance(v, str) and len(v.strip()) > 2:
                label = v.strip().lower()
                break
        parsed = _extract_row_values(row)
        if not any(v is not None for v in parsed):
            continue
        if label == "ebitda" or (label.startswith("ebitda") and len(label) < 30):
            ebitda_vals = parsed
        elif label in ("ebit", "operating income") or (
            ("operating income" in label or "ebit" in label)
            and len(label) < 40
            and "margin" not in label
        ):
            ebit_vals = parsed
        elif ("depreciation" in label or "d&a" in label or "amortization" in label) and len(
            label
        ) < 50:
            da_vals = parsed

    if not ebitda_vals:
        results.append(("EBITDA: EBITDA row found", False, "No EBITDA row"))
        return results

    if not ebit_vals or not da_vals:
        results.append(
            (
                "EBITDA: EBIT and D&A components found",
                False,
                f"Missing: {'EBIT/Operating Income' if not ebit_vals else 'D&A'} row",
            )
        )
        return results

    any_match = False
    details: list[str] = []
    for col in range(1, 8):
        ebit = ebit_vals[col] if col < len(ebit_vals) else None
        da = da_vals[col] if col < len(da_vals) else None
        ebitda = ebitda_vals[col] if col < len(ebitda_vals) else None
        if ebit is None or da is None or ebitda is None:
            continue
        expected = ebit + abs(da)  # D&A may be stored as negative
        if _common.numbers_close(expected, ebitda, tol_pct=0.05, abs_tol=50):
            any_match = True
            details.append(
                f"col{col}: EBIT({ebit:,.0f})+D&A({da:,.0f})="
                f"{expected:,.0f} ≈ EBITDA({ebitda:,.0f})"
            )

    results.append(
        (
            "EBITDA: EBIT + D&A ≈ EBITDA",
            any_match,
            "; ".join(details) if details else "No column where EBIT + D&A ≈ EBITDA",
        )
    )
    return results


def _check_fcf_derivation(
    sheets_data: dict[str, list[list[Any]]],
    _all_numbers: list[float],
    _all_text: str,
) -> list[tuple[str, bool, str]]:
    """Verify Free Cash Flow = Operating Cash Flow - CapEx."""
    results: list[tuple[str, bool, str]] = []
    _, rows = _find_sheet(sheets_data, "cash flow")
    if not rows:
        _, rows = _find_sheet(sheets_data, "fcf")
    if not rows:
        _, rows = _find_sheet(sheets_data, "cash")
    if not rows:
        results.append(("Cash flow sheet found", False, "No cash flow sheet"))
        return results

    fcf_vals: list[float | None] = []
    ocf_vals: list[float | None] = []
    capex_vals: list[float | None] = []

    for row in rows:
        label = ""
        for v in row:
            if isinstance(v, str) and len(v.strip()) > 2:
                label = v.strip().lower()
                break
        parsed = _extract_row_values(row)
        if not any(v is not None for v in parsed):
            continue
        if ("free cash flow" in label or label == "fcf") and len(label) < 40:
            fcf_vals = parsed
        elif (
            "operating cash flow" in label
            or "cash from operations" in label
            or "net cash from operating" in label
        ) and len(label) < 60:
            ocf_vals = parsed
        elif (
            "capex" in label or "capital expenditure" in label or "purchase of property" in label
        ) and len(label) < 60:
            capex_vals = parsed

    if not fcf_vals:
        results.append(("FCF: free cash flow row found", False, "No 'Free Cash Flow' row"))
        return results

    if not ocf_vals or not capex_vals:
        results.append(
            (
                "FCF: OCF and CapEx components found",
                False,
                f"Missing: {'OCF' if not ocf_vals else 'CapEx'} row",
            )
        )
        return results

    any_match = False
    details: list[str] = []
    for col in range(1, 8):
        ocf = ocf_vals[col] if col < len(ocf_vals) else None
        capex = capex_vals[col] if col < len(capex_vals) else None
        fcf = fcf_vals[col] if col < len(fcf_vals) else None
        if ocf is None or capex is None or fcf is None:
            continue
        expected = ocf - abs(capex)  # CapEx may be stored as negative
        if _common.numbers_close(expected, fcf, tol_pct=0.05, abs_tol=50):
            any_match = True
            details.append(
                f"col{col}: OCF({ocf:,.0f})-CapEx({capex:,.0f})={expected:,.0f} ≈ FCF({fcf:,.0f})"
            )

    results.append(
        (
            "FCF: OCF - CapEx ≈ Free Cash Flow",
            any_match,
            "; ".join(details) if details else "No column where OCF - CapEx ≈ FCF",
        )
    )
    return results


def _check_net_debt_calculation(
    sheets_data: dict[str, list[list[Any]]],
    _all_numbers: list[float],
    _all_text: str,
) -> list[tuple[str, bool, str]]:
    """Verify Net Debt = Total Debt - Cash & Equivalents."""
    results: list[tuple[str, bool, str]] = []
    _, rows = _find_sheet(sheets_data, "net debt")
    if not rows:
        _, rows = _find_sheet(sheets_data, "valuation")
    if not rows:
        _, rows = _find_sheet(sheets_data, "balance sheet")
    if not rows:
        results.append(("Net debt sheet found", False, "No net debt or valuation sheet"))
        return results

    net_debt_vals: list[float | None] = []
    total_debt_vals: list[float | None] = []
    cash_vals: list[float | None] = []

    for row in rows:
        label = ""
        for v in row:
            if isinstance(v, str) and len(v.strip()) > 2:
                label = v.strip().lower()
                break
        parsed = _extract_row_values(row)
        if not any(v is not None for v in parsed):
            continue
        if (label == "net debt" or label.startswith("net debt")) and len(label) < 30:
            net_debt_vals = parsed
        elif (
            ("total debt" in label or "long-term debt" in label)
            and "net" not in label
            and len(label) < 50
        ):
            total_debt_vals = parsed
        elif ("cash and" in label or label.startswith("cash ") or label == "cash") and len(
            label
        ) < 50:
            cash_vals = parsed

    if not net_debt_vals:
        results.append(("Net Debt: net debt row found", False, "No 'Net Debt' row"))
        return results

    if not total_debt_vals or not cash_vals:
        results.append(
            (
                "Net Debt: debt and cash components found",
                False,
                f"Missing: {'Total Debt' if not total_debt_vals else 'Cash'} row",
            )
        )
        return results

    any_match = False
    details: list[str] = []
    for col in range(1, 8):
        debt = total_debt_vals[col] if col < len(total_debt_vals) else None
        cash = cash_vals[col] if col < len(cash_vals) else None
        nd = net_debt_vals[col] if col < len(net_debt_vals) else None
        if debt is None or cash is None or nd is None:
            continue
        expected = debt - abs(cash)
        if _common.numbers_close(expected, nd, tol_pct=0.05, abs_tol=100):
            any_match = True
            details.append(
                f"col{col}: Debt({debt:,.0f})-Cash({cash:,.0f})={expected:,.0f} ≈ ND({nd:,.0f})"
            )

    results.append(
        (
            "Net Debt: Total Debt - Cash ≈ Net Debt",
            any_match,
            "; ".join(details) if details else "No column where Total Debt - Cash ≈ Net Debt",
        )
    )
    return results


def _check_ev_components(
    sheets_data: dict[str, list[list[Any]]],
    _all_numbers: list[float],
    _all_text: str,
) -> list[tuple[str, bool, str]]:
    """Verify Enterprise Value = Market Cap + Net Debt."""
    results: list[tuple[str, bool, str]] = []
    _, rows = _find_sheet(sheets_data, "valuation")
    if not rows:
        _, rows = _find_sheet(sheets_data, "ev")
    if not rows:
        results.append(("Valuation sheet found", False, "No valuation sheet"))
        return results

    ev_vals: list[float | None] = []
    mktcap_vals: list[float | None] = []
    nd_vals: list[float | None] = []

    for row in rows:
        label = ""
        for v in row:
            if isinstance(v, str) and len(v.strip()) > 2:
                label = v.strip().lower()
                break
        parsed = _extract_row_values(row)
        if not any(v is not None for v in parsed):
            continue
        if (label == "enterprise value" or label.startswith("enterprise value")) and len(
            label
        ) < 40:
            ev_vals = parsed
        elif ("market cap" in label or "market capitaliz" in label) and len(label) < 50:
            mktcap_vals = parsed
        elif (label == "net debt" or label.startswith("net debt")) and len(label) < 30:
            nd_vals = parsed

    if not ev_vals:
        results.append(("EV: enterprise value row found", False, "No 'Enterprise Value' row"))
        return results

    if not mktcap_vals or not nd_vals:
        results.append(
            (
                "EV: market cap and net debt components found",
                False,
                f"Missing: {'Market Cap' if not mktcap_vals else 'Net Debt'} row",
            )
        )
        return results

    any_match = False
    details: list[str] = []
    for col in range(1, 8):
        mc = mktcap_vals[col] if col < len(mktcap_vals) else None
        nd = nd_vals[col] if col < len(nd_vals) else None
        ev = ev_vals[col] if col < len(ev_vals) else None
        if mc is None or nd is None or ev is None:
            continue
        expected = mc + nd
        if _common.numbers_close(expected, ev, tol_pct=0.05, abs_tol=500):
            any_match = True
            details.append(
                f"col{col}: Mktcap({mc:,.0f})+ND({nd:,.0f})={expected:,.0f} ≈ EV({ev:,.0f})"
            )

    results.append(
        (
            "EV: Market Cap + Net Debt ≈ Enterprise Value",
            any_match,
            "; ".join(details) if details else "No column where Market Cap + Net Debt ≈ EV",
        )
    )
    return results


# All cross-checks for this task
_CROSS_CHECKS = [
    _check_segment_revenue_totals,
    _check_organic_revenue_components,
    _check_ebitda_derivation,
    _check_fcf_derivation,
    _check_net_debt_calculation,
    _check_ev_components,
]


def verify(run_artifacts: RunArtifacts) -> VerifierResult:
    """Verify the Coca-Cola Investment Manager Analysis task."""
    return _common.run_verifier(
        run_artifacts,
        golden_path=GOLDEN_PATH,
        concept_candidates=_CONCEPT_CANDIDATES,
        num_tol_pct=0.10,
        num_abs_tol=50,
        rate_tol_pct=0.10,
        rate_abs_tol=0.005,
        min_cells=150,
        text_coverage_threshold=0.4,
        cross_checks=_CROSS_CHECKS,
    )
