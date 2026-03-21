#!/usr/bin/env python3
"""Deterministic programmatic verifier for financial benchmark tasks.

Performs exact field-by-field comparison against golden ground truth.
No LLM judge — every score is computed from numerical checks.

Scoring dimensions:
  1. STATUS accuracy   — did the model get PASS/FAIL right? (binary per covenant)
  2. VALUE accuracy    — is the computed ratio within tolerance of golden?
  3. COMPONENT accuracy — did it extract the right numerator/denominator?
  4. TRAP detection     — did it avoid known error patterns?

Usage:
    uv run python -m benchmarks.verify --task covenant_compliance --results-dir test_results_grok420
    uv run python -m benchmarks.verify --task trade_recon --results-dir test_results_grok420
    uv run python -m benchmarks.verify --all --results-dir test_results_grok420
    uv run python -m benchmarks.verify --all --results-dir test_results_grok420 --json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent.parent

# ═════════════════════════════════════════════════════════════════════════════
# UTILITY: Extract agent output
# ═════════════════════════════════════════════════════════════════════════════

def load_golden(task: str) -> dict:
    """Load golden ground truth for a task."""
    if task == "covenant_compliance":
        p = BASE / "samples" / "covenant_compliance" / "golden_output" / "covenant_analysis.json"
    elif task == "trade_recon":
        p = BASE / "samples" / "trade_recon" / "golden_output" / "reconciliation.json"
    else:
        raise ValueError(f"Unknown task: {task}")
    return json.loads(p.read_text())


def load_agent_output(results_dir: Path, task: str) -> tuple[str | None, dict | None]:
    """Load raw agent output text and try to parse as JSON.

    Returns (raw_text, parsed_json_or_None).
    """
    out_dir = results_dir / task / "agent_output"
    if not out_dir.exists():
        return None, None

    raw = None
    # Prefer .src.txt files (the raw JSON/markdown the agent wrote)
    for f in sorted(out_dir.iterdir()):
        if f.name.endswith(".src.txt"):
            raw = f.read_text()
            break
    if raw is None:
        for f in sorted(out_dir.iterdir()):
            if f.suffix in (".json", ".txt"):
                raw = f.read_text()
                break
    if raw is None:
        return None, None

    # Try parsing as JSON (agent xlsx output is JSON with sheet→rows mapping)
    parsed = _try_parse_json(raw)
    return raw, parsed


def _try_parse_json(text: str) -> dict | None:
    """Try multiple strategies to extract JSON from text."""
    for attempt in [
        lambda: json.loads(text),
        lambda: json.loads(re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text).group(1)),
        lambda: json.loads(re.search(r"(\{[\s\S]*\})", text).group(1)),
    ]:
        try:
            return attempt()
        except Exception:
            continue
    return None


def parse_number(val: Any) -> float | None:
    """Parse a number from various agent output formats."""
    if isinstance(val, (int, float)):
        return float(val)
    if not isinstance(val, str):
        return None
    s = val.strip()
    # Remove formatting: $, commas, x suffix, parens for negatives
    s = s.replace(",", "").replace("$", "").replace("x", "").replace("%", "")
    s = s.replace("(", "-").replace(")", "").strip()
    if s in ("", "N/A", "n/a", "-", "—"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def within_tolerance(agent: float, golden: float, rel_tol: float = 0.005,
                     abs_tol: float = 0.5) -> bool:
    """Check if agent value is within tolerance of golden value.

    rel_tol: relative tolerance (0.5% default)
    abs_tol: absolute tolerance for values near zero
    """
    if golden == 0:
        return abs(agent) <= abs_tol
    return abs(agent - golden) / abs(golden) <= rel_tol


# ═════════════════════════════════════════════════════════════════════════════
# COVENANT COMPLIANCE VERIFIER
# ═════════════════════════════════════════════════════════════════════════════

# Canonical covenant names and their keyword signatures for fuzzy matching
_COVENANT_KEYS = {
    "Senior Secured Leverage Ratio":  ["leverage", "senior", "secured"],
    "Interest Coverage Ratio":        ["interest", "coverage"],
    "Fixed Charge Coverage Ratio":    ["fixed", "charge"],
    "Current Ratio":                  ["current"],
    "Minimum Liquidity":              ["liquidity", "minimum"],
    "Maximum Capital Expenditures":   ["capital", "expenditure", "capex", "maximum"],
}


def _match_covenant_name(agent_name: str, golden_name: str) -> bool:
    """Fuzzy match an agent's covenant name to a golden covenant name."""
    a = agent_name.lower().strip()
    g = golden_name.lower().strip()
    if g in a or a in g:
        return True
    keywords = _COVENANT_KEYS.get(golden_name, [])
    return any(kw in a for kw in keywords)


def _extract_covenant_rows(data: dict) -> list[dict]:
    """Extract covenant result rows from the agent's JSON output.

    Agent writes xlsx as JSON: {"Sheet Name": [[header_row], [row1], ...]}
    We need to find the results sheet and parse it.
    """
    rows = []

    # Strategy 1: Look for a sheet with "result" or "covenant" in name
    for sheet_name, sheet_rows in data.items():
        if not isinstance(sheet_rows, list) or len(sheet_rows) < 2:
            continue
        name_lower = sheet_name.lower()
        if any(kw in name_lower for kw in ["result", "covenant", "summary"]):
            headers = [str(h).lower().strip() for h in sheet_rows[0]]
            for row in sheet_rows[1:]:
                if not isinstance(row, list) or not row:
                    continue
                entry = {}
                for i, val in enumerate(row):
                    if i < len(headers):
                        entry[headers[i]] = val
                rows.append(entry)
            if rows:
                return rows

    # Strategy 2: Try every sheet
    for sheet_name, sheet_rows in data.items():
        if not isinstance(sheet_rows, list) or len(sheet_rows) < 2:
            continue
        headers = [str(h).lower().strip() for h in sheet_rows[0]]
        # Check if headers look like covenant results
        has_status = any("status" in h or "pass" in h or "fail" in h for h in headers)
        has_name = any("name" in h or "covenant" in h for h in headers)
        if has_status or has_name:
            for row in sheet_rows[1:]:
                if not isinstance(row, list) or not row:
                    continue
                entry = {}
                for i, val in enumerate(row):
                    if i < len(headers):
                        entry[headers[i]] = val
                rows.append(entry)
            if rows:
                return rows

    return rows


def _find_agent_covenant(agent_rows: list[dict], golden_name: str) -> dict | None:
    """Find the agent's row matching a golden covenant name."""
    for row in agent_rows:
        for key, val in row.items():
            if isinstance(val, str) and _match_covenant_name(val, golden_name):
                return row
    return None


def _get_field(row: dict, *keywords: str) -> Any:
    """Get a field from a row by matching keywords in header names."""
    for key, val in row.items():
        k = key.lower()
        if any(kw in k for kw in keywords):
            return val
    return None


def _identify_trap(agent_val: float, golden: dict) -> str | None:
    """Check if agent value matches a known trap value."""
    traps = golden.get("traps", {})
    for trap_name, trap_val in traps.items():
        if isinstance(trap_val, (int, float)):
            if within_tolerance(agent_val, float(trap_val), rel_tol=0.02):
                return trap_name
    return None


def verify_covenant(results_dir: Path) -> dict:
    """Full programmatic verification of covenant compliance output."""
    golden = load_golden("covenant_compliance")
    raw, parsed = load_agent_output(results_dir, "covenant_compliance")

    result = {
        "task": "covenant_compliance",
        "model": _get_model(results_dir, "covenant_compliance"),
        "scores": {
            "status_correct": 0,
            "status_total": 0,
            "value_correct": 0,
            "value_close": 0,
            "value_total": 0,
            "numerator_correct": 0,
            "denominator_correct": 0,
            "component_total": 0,
            "traps_avoided": 0,
            "traps_fallen_into": [],
        },
        "covenants": [],
        "overall": {},
    }

    if raw is None:
        result["error"] = f"No agent output found in {results_dir}/covenant_compliance/"
        return result

    if parsed is None:
        result["error"] = "Could not parse agent output as JSON"
        result["raw_preview"] = raw[:500]
        return result

    agent_rows = _extract_covenant_rows(parsed)
    if not agent_rows:
        result["error"] = "Could not find covenant result rows in agent output"
        result["parsed_keys"] = list(parsed.keys()) if isinstance(parsed, dict) else "not a dict"
        return result

    golden_covenants = golden["covenants"]
    trap_count = sum(len(gc.get("traps", {})) for gc in golden_covenants)

    for gc in golden_covenants:
        cov_result = {
            "name": gc["name"],
            "golden_status": gc["status"],
            "golden_value": gc["computed_value"],
            "golden_numerator": gc.get("numerator"),
            "golden_denominator": gc.get("denominator"),
        }

        agent_row = _find_agent_covenant(agent_rows, gc["name"])

        if agent_row is None:
            cov_result["found"] = False
            cov_result["status_correct"] = False
            cov_result["value_correct"] = False
            result["scores"]["status_total"] += 1
            result["scores"]["value_total"] += 1
            if gc.get("numerator") is not None:
                result["scores"]["component_total"] += 2
            result["covenants"].append(cov_result)
            continue

        cov_result["found"] = True
        cov_result["agent_row"] = {k: v for k, v in agent_row.items()}

        # ── STATUS CHECK ──────────────────────────────────────────────────
        result["scores"]["status_total"] += 1
        agent_status = None
        status_val = _get_field(agent_row, "status", "compliance", "result", "pass", "fail")
        if isinstance(status_val, str):
            s = status_val.upper().strip()
            if "PASS" in s:
                agent_status = "PASS"
            elif "FAIL" in s or "BREACH" in s:
                agent_status = "FAIL"

        cov_result["agent_status"] = agent_status
        cov_result["status_correct"] = agent_status == gc["status"]
        if cov_result["status_correct"]:
            result["scores"]["status_correct"] += 1

        # ── VALUE CHECK ───────────────────────────────────────────────────
        result["scores"]["value_total"] += 1
        agent_val_raw = _get_field(agent_row, "computed", "value", "ratio", "amount", "result")
        # Also check "numerator" field for non-ratio covenants (liquidity, capex)
        if agent_val_raw is None or (isinstance(agent_val_raw, str) and agent_val_raw.strip() in ("", "N/A")):
            agent_val_raw = _get_field(agent_row, "numerator")

        agent_val = parse_number(agent_val_raw)
        golden_val = float(gc["computed_value"])

        cov_result["agent_value"] = agent_val

        if agent_val is not None:
            exact = within_tolerance(agent_val, golden_val, rel_tol=0.005)
            close = within_tolerance(agent_val, golden_val, rel_tol=0.02)
            cov_result["value_correct"] = exact
            cov_result["value_close"] = close
            cov_result["value_error_pct"] = (
                round(abs(agent_val - golden_val) / abs(golden_val) * 100, 2)
                if golden_val != 0 else None
            )
            if exact:
                result["scores"]["value_correct"] += 1
            elif close:
                result["scores"]["value_close"] += 1

            # ── TRAP DETECTION ────────────────────────────────────────────
            trap = _identify_trap(agent_val, gc)
            if trap:
                cov_result["trap_fallen"] = trap
                result["scores"]["traps_fallen_into"].append({
                    "covenant": gc["name"],
                    "trap": trap,
                    "agent_value": agent_val,
                    "trap_value": gc["traps"][trap],
                    "golden_value": golden_val,
                })
        else:
            cov_result["value_correct"] = False
            cov_result["value_parse_error"] = True

        # ── COMPONENT CHECK (numerator / denominator) ─────────────────────
        if gc.get("numerator") is not None:
            result["scores"]["component_total"] += 1
            agent_num = parse_number(_get_field(agent_row, "numerator"))
            cov_result["agent_numerator"] = agent_num
            if agent_num is not None and within_tolerance(agent_num, float(gc["numerator"]), rel_tol=0.005):
                result["scores"]["numerator_correct"] += 1
                cov_result["numerator_correct"] = True
            else:
                cov_result["numerator_correct"] = False

        if gc.get("denominator") is not None:
            result["scores"]["component_total"] += 1
            agent_den = parse_number(_get_field(agent_row, "denominator"))
            cov_result["agent_denominator"] = agent_den
            if agent_den is not None and within_tolerance(agent_den, float(gc["denominator"]), rel_tol=0.005):
                result["scores"]["denominator_correct"] += 1
                cov_result["denominator_correct"] = True
            else:
                cov_result["denominator_correct"] = False

        result["covenants"].append(cov_result)

    # ── COMPUTE OVERALL SCORES ────────────────────────────────────────────
    s = result["scores"]
    traps_avoided = trap_count - len(s["traps_fallen_into"])
    s["traps_avoided"] = traps_avoided
    s["traps_total"] = trap_count

    # Weighted score:  status 40%, value 30%, components 20%, traps 10%
    status_pct = s["status_correct"] / s["status_total"] if s["status_total"] else 0
    value_pct = (
        (s["value_correct"] + 0.5 * s["value_close"]) / s["value_total"]
        if s["value_total"] else 0
    )
    comp_pct = (
        (s["numerator_correct"] + s["denominator_correct"]) / s["component_total"]
        if s["component_total"] else 1.0  # no components to check = full marks
    )
    trap_pct = traps_avoided / trap_count if trap_count else 1.0

    weighted = 0.40 * status_pct + 0.30 * value_pct + 0.20 * comp_pct + 0.10 * trap_pct

    result["overall"] = {
        "weighted_score": round(weighted * 100, 1),
        "status_accuracy": round(status_pct * 100, 1),
        "value_accuracy": round(value_pct * 100, 1),
        "component_accuracy": round(comp_pct * 100, 1),
        "trap_avoidance": round(trap_pct * 100, 1),
        "grade": (
            "A" if weighted >= 0.90 else
            "B" if weighted >= 0.75 else
            "C" if weighted >= 0.60 else
            "D" if weighted >= 0.40 else "F"
        ),
    }

    return result


# ═════════════════════════════════════════════════════════════════════════════
# TRADE RECON VERIFIER
# ═════════════════════════════════════════════════════════════════════════════

def verify_recon(results_dir: Path) -> dict:
    """Full programmatic verification of trade reconciliation output."""
    golden = load_golden("trade_recon")
    raw, parsed = load_agent_output(results_dir, "trade_recon")

    result = {
        "task": "trade_recon",
        "model": _get_model(results_dir, "trade_recon"),
        "scores": {
            "summary_stats": {},
            "exception_classification": {},
            "match_accuracy": {},
            "dollar_impact": {},
        },
        "overall": {},
    }

    if raw is None:
        result["error"] = f"No agent output in {results_dir}/trade_recon/"
        return result
    if parsed is None:
        result["error"] = "Could not parse agent output as JSON"
        return result

    gs = golden["summary"]

    # ── FIND SHEETS ───────────────────────────────────────────────────────
    matched_sheet = exceptions_sheet = summary_sheet = None
    for key, rows in parsed.items():
        if not isinstance(rows, list):
            continue
        kl = key.lower()
        if "match" in kl:
            matched_sheet = rows
        elif "exception" in kl:
            exceptions_sheet = rows
        elif "summary" in kl or "stat" in kl:
            summary_sheet = rows

    total_points = 0.0
    max_points = 0.0

    # ── 1. SUMMARY STATS (5 metrics, 1 pt each) ──────────────────────────
    summary_checks = {
        "total_internal_trades": gs["total_internal_trades"],
        "total_broker_confirmations": gs["total_broker_confirmations"],
        "clean_matches": gs["clean_matches"],
        "total_exceptions": gs["total_exceptions"],
        "total_dollar_impact": gs["total_dollar_impact"],
    }

    summary_results = {}
    if summary_sheet and len(summary_sheet) > 1:
        # Parse summary as key-value pairs
        agent_summary = {}
        for row in summary_sheet:
            if isinstance(row, list) and len(row) >= 2:
                agent_summary[str(row[0]).lower().strip()] = row[1]

        for metric, golden_val in summary_checks.items():
            max_points += 1
            keywords = metric.replace("_", " ").split()
            matched = False
            for ak, av in agent_summary.items():
                if all(kw in ak for kw in keywords) or metric.replace("_", " ") in ak:
                    agent_val = parse_number(av)
                    if agent_val is not None:
                        if metric == "total_dollar_impact":
                            ok = within_tolerance(agent_val, golden_val, rel_tol=0.05,
                                                  abs_tol=100)
                        else:
                            ok = abs(agent_val - golden_val) < 1.5
                        summary_results[metric] = {
                            "agent": agent_val, "golden": golden_val,
                            "correct": ok,
                        }
                        if ok:
                            total_points += 1
                        matched = True
                        break
            if not matched:
                summary_results[metric] = {
                    "golden": golden_val, "correct": False, "note": "not found",
                }
    else:
        for metric in summary_checks:
            max_points += 1
            summary_results[metric] = {"correct": False, "note": "no summary sheet"}

    result["scores"]["summary_stats"] = summary_results

    # ── 2. EXCEPTION CLASSIFICATION (2 pts per type: 1 for found, 1 for count) ──
    golden_types = gs["exception_types"]
    exception_results = {}

    if exceptions_sheet and len(exceptions_sheet) > 1:
        headers = [str(h).lower().strip() for h in exceptions_sheet[0]]
        type_col = None
        for i, h in enumerate(headers):
            if "type" in h or "exception" in h or "class" in h:
                type_col = i
                break

        agent_type_counts: dict[str, int] = {}
        if type_col is not None:
            for row in exceptions_sheet[1:]:
                if isinstance(row, list) and len(row) > type_col:
                    raw_type = str(row[type_col]).lower().strip().replace(" ", "_")
                    # Normalize common variations
                    for canon in golden_types:
                        if canon.replace("_", "") in raw_type.replace("_", ""):
                            agent_type_counts[canon] = agent_type_counts.get(canon, 0) + 1
                            break
                    else:
                        agent_type_counts[raw_type] = agent_type_counts.get(raw_type, 0) + 1

        for etype, golden_count in golden_types.items():
            max_points += 2
            agent_count = agent_type_counts.get(etype, 0)
            found = agent_count > 0
            exact = agent_count == golden_count
            pts = (1 if found else 0) + (1 if exact else 0)
            total_points += pts
            exception_results[etype] = {
                "agent_count": agent_count, "golden_count": golden_count,
                "found": found, "count_exact": exact, "points": pts,
            }
    else:
        for etype, golden_count in golden_types.items():
            max_points += 2
            exception_results[etype] = {
                "golden_count": golden_count, "found": False,
                "count_exact": False, "points": 0, "note": "no exceptions sheet",
            }

    result["scores"]["exception_classification"] = exception_results

    # ── 3. MATCH COUNT (2 pts) ────────────────────────────────────────────
    max_points += 2
    match_result = {}
    if matched_sheet and len(matched_sheet) > 1:
        agent_match_count = len(matched_sheet) - 1  # minus header
        golden_match_count = len(golden["matches"])
        diff = abs(agent_match_count - golden_match_count)
        pts = 2 if diff <= 1 else (1 if diff <= 3 else 0)
        total_points += pts
        match_result = {
            "agent_count": agent_match_count,
            "golden_count": golden_match_count,
            "difference": diff,
            "points": pts,
        }
    else:
        match_result = {"points": 0, "note": "no matched trades sheet"}

    result["scores"]["match_accuracy"] = match_result

    # ── 4. DOLLAR IMPACT (2 pts — within 10% of golden) ──────────────────
    max_points += 2
    impact_result = {}
    if exceptions_sheet and len(exceptions_sheet) > 1:
        headers = [str(h).lower().strip() for h in exceptions_sheet[0]]
        impact_col = None
        for i, h in enumerate(headers):
            if "dollar" in h or "impact" in h or "pnl" in h or "p&l" in h:
                impact_col = i
                break

        if impact_col is not None:
            agent_total_impact = 0.0
            for row in exceptions_sheet[1:]:
                if isinstance(row, list) and len(row) > impact_col:
                    v = parse_number(row[impact_col])
                    if v is not None:
                        agent_total_impact += abs(v)

            golden_impact = gs["total_dollar_impact"]
            ok = within_tolerance(agent_total_impact, golden_impact, rel_tol=0.10, abs_tol=500)
            pts = 2 if ok else (1 if within_tolerance(agent_total_impact, golden_impact, rel_tol=0.25, abs_tol=2000) else 0)
            total_points += pts
            impact_result = {
                "agent_total": round(agent_total_impact, 2),
                "golden_total": golden_impact,
                "error_pct": round(
                    abs(agent_total_impact - golden_impact) / golden_impact * 100, 1
                ) if golden_impact else 0,
                "points": pts,
            }
        else:
            impact_result = {"points": 0, "note": "no dollar impact column found"}
    else:
        impact_result = {"points": 0, "note": "no exceptions sheet"}

    result["scores"]["dollar_impact"] = impact_result

    # ── OVERALL ───────────────────────────────────────────────────────────
    pct = round(total_points / max_points * 100, 1) if max_points else 0
    result["overall"] = {
        "points": total_points,
        "max_points": max_points,
        "percentage": pct,
        "grade": (
            "A" if pct >= 90 else
            "B" if pct >= 75 else
            "C" if pct >= 60 else
            "D" if pct >= 40 else "F"
        ),
    }

    return result


# ═════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═════════════════════════════════════════════════════════════════════════════

def _get_model(results_dir: Path, task: str) -> str | None:
    """Extract model name from trajectory."""
    traj_path = results_dir / task / "trajectory.json"
    if traj_path.exists():
        try:
            data = json.loads(traj_path.read_text())
            return data.get("model")
        except Exception:
            pass
    return None


def print_covenant_report(result: dict):
    """Pretty-print covenant verification report."""
    print(f"\n{'='*72}")
    print(f"  COVENANT COMPLIANCE VERIFICATION")
    if result.get("model"):
        print(f"  Model: {result['model']}")
    print(f"{'='*72}")

    if "error" in result:
        print(f"\n  ERROR: {result['error']}")
        return

    o = result["overall"]
    print(f"\n  OVERALL: {o['weighted_score']}% — Grade {o['grade']}")
    print(f"    Status accuracy:    {o['status_accuracy']}%")
    print(f"    Value accuracy:     {o['value_accuracy']}%")
    print(f"    Component accuracy: {o['component_accuracy']}%")
    print(f"    Trap avoidance:     {o['trap_avoidance']}%")

    print(f"\n  {'Covenant':<38s} {'Status':>8s} {'Value':>12s} {'Err%':>6s} {'Traps':>8s}")
    print(f"  {'─'*38} {'─'*8} {'─'*12} {'─'*6} {'─'*8}")

    for c in result["covenants"]:
        name = c["name"][:38]
        if not c.get("found"):
            print(f"  {name:<38s} {'MISS':>8s} {'—':>12s} {'—':>6s} {'—':>8s}")
            continue

        # Status
        gs = c["golden_status"]
        ag_s = c.get("agent_status", "?")
        s_mark = "✓" if c.get("status_correct") else "✗"
        status_str = f"{s_mark} {ag_s}"

        # Value
        ag_v = c.get("agent_value")
        gv = c["golden_value"]
        if ag_v is not None:
            if isinstance(gv, float) and gv < 100:
                val_str = f"{ag_v:.4f}"
            else:
                val_str = f"{ag_v:,.0f}"
        else:
            val_str = "PARSE ERR"

        # Error
        err = c.get("value_error_pct")
        err_str = f"{err:.1f}%" if err is not None else "—"

        # Trap
        trap = c.get("trap_fallen")
        trap_str = f"⚠ {trap}" if trap else "OK"

        print(f"  {name:<38s} {status_str:>8s} {val_str:>12s} {err_str:>6s} {trap_str:>8s}")

    # Print trap details
    traps = result["scores"]["traps_fallen_into"]
    if traps:
        print(f"\n  ⚠ TRAPS TRIGGERED ({len(traps)}):")
        for t in traps:
            print(f"    • {t['covenant']}: {t['trap']}")
            print(f"      Agent got {t['agent_value']}, trap value is {t['trap_value']}, "
                  f"correct is {t['golden_value']}")


def print_recon_report(result: dict):
    """Pretty-print trade recon verification report."""
    print(f"\n{'='*72}")
    print(f"  TRADE RECONCILIATION VERIFICATION")
    if result.get("model"):
        print(f"  Model: {result['model']}")
    print(f"{'='*72}")

    if "error" in result:
        print(f"\n  ERROR: {result['error']}")
        return

    o = result["overall"]
    print(f"\n  OVERALL: {o['percentage']}% ({o['points']}/{o['max_points']} pts) — Grade {o['grade']}")

    # Summary stats
    print(f"\n  Summary Statistics:")
    for metric, info in result["scores"]["summary_stats"].items():
        mark = "✓" if info.get("correct") else "✗"
        agent = info.get("agent", "—")
        golden = info.get("golden", "—")
        print(f"    {mark} {metric}: agent={agent}, golden={golden}")

    # Exception classification
    print(f"\n  Exception Classification:")
    for etype, info in result["scores"]["exception_classification"].items():
        pts = info.get("points", 0)
        ac = info.get("agent_count", "—")
        gc = info.get("golden_count", "—")
        print(f"    [{pts}/2] {etype}: agent={ac}, golden={gc}")

    # Match accuracy
    ma = result["scores"]["match_accuracy"]
    print(f"\n  Match Count: [{ma.get('points', 0)}/2] "
          f"agent={ma.get('agent_count', '—')}, golden={ma.get('golden_count', '—')}")

    # Dollar impact
    di = result["scores"]["dollar_impact"]
    print(f"  Dollar Impact: [{di.get('points', 0)}/2] "
          f"agent=${di.get('agent_total', '—'):,.0f}" if isinstance(di.get('agent_total'), (int, float)) else "",
          f"golden=${di.get('golden_total', '—'):,.0f}" if isinstance(di.get('golden_total'), (int, float)) else "")


# ═════════════════════════════════════════════════════════════════════════════
# MULTI-MODEL COMPARISON
# ═════════════════════════════════════════════════════════════════════════════

def compare_models(task: str, results_dirs: dict[str, Path]) -> dict:
    """Compare multiple models on the same task.

    Args:
        task: "covenant_compliance" or "trade_recon"
        results_dirs: {"model_name": Path_to_results_dir}
    """
    verify_fn = verify_covenant if task == "covenant_compliance" else verify_recon
    results = {}
    for model_name, rdir in results_dirs.items():
        results[model_name] = verify_fn(rdir)

    return results


# ═════════════════════════════════════════════════════════════════════════════
# CLI
# ═════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Deterministic verifier for financial benchmark tasks"
    )
    parser.add_argument("--task", choices=["covenant_compliance", "trade_recon"])
    parser.add_argument("--all", action="store_true", help="Verify all tasks")
    parser.add_argument("--results-dir", type=Path, default=BASE / "test_results",
                        help="Results directory")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    parser.add_argument("--compare", nargs="*", metavar="NAME=DIR",
                        help="Compare models: model1=dir1 model2=dir2")
    args = parser.parse_args()

    if args.compare:
        dirs = {}
        for spec in args.compare:
            name, path = spec.split("=", 1)
            dirs[name] = Path(path)
        task = args.task or "covenant_compliance"
        results = compare_models(task, dirs)
        if args.json:
            print(json.dumps(results, indent=2, default=str))
        else:
            print(f"\n{'='*72}")
            print(f"  MODEL COMPARISON: {task.upper().replace('_', ' ')}")
            print(f"{'='*72}")
            for model, r in results.items():
                o = r.get("overall", {})
                score = o.get("weighted_score", o.get("percentage", "?"))
                grade = o.get("grade", "?")
                print(f"  {model:<30s} {score:>6}% — Grade {grade}")
        return

    if not args.task and not args.all:
        args.all = True

    results = {}

    if args.task == "covenant_compliance" or args.all:
        r = verify_covenant(args.results_dir)
        results["covenant_compliance"] = r
        if not args.json:
            print_covenant_report(r)

    if args.task == "trade_recon" or args.all:
        r = verify_recon(args.results_dir)
        results["trade_recon"] = r
        if not args.json:
            print_recon_report(r)

    if args.json:
        print(json.dumps(results, indent=2, default=str))

    # Save results
    out_path = args.results_dir / "verification_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2, default=str))
    if not args.json:
        print(f"\n  Results saved to {out_path}")


if __name__ == "__main__":
    main()
