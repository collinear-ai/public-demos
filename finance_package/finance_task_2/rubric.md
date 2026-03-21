# Multi-Source Trade Reconciliation — LLM Judge Rubric

You are evaluating an Excel workbook that reconciles an internal trade blotter against broker confirmations for a two-week trading period (January 6–17, 2025). The task involves matching 58 internal trades against 58 broker confirmations, classifying discrepancies, and computing dollar impact. A programmatic verifier has already checked data accuracy. Your job is to evaluate what code cannot: analytical quality, classification reasoning, and professional presentation.

You will be given the full cell-level content of the submitted workbook. Score each dimension from 1-5, provide a brief justification, then compute a weighted total out of 100.

---

## Dimension 1: Trade Matching Accuracy (Weight: 25%)

Did the agent correctly match internal trades to broker confirmations?

| Score | Description |
|---|---|
| 5 | All trades correctly matched by trade ID where available. Fuzzy matching (ticker+date+side) correctly applied where IDs are missing. Clean matches (no breaks) correctly separated from matched-with-breaks. Clean match count = 40. |
| 4 | Most matches correct. Clean/break separation mostly right but count slightly off. |
| 3 | Trade ID matching works but fuzzy matching or clean/break separation has significant errors. |
| 2 | Many matching errors. Trades misclassified. |
| 1 | Matching is fundamentally broken. |

**Evaluate:**
- Are fuzzy matches (blank confirmation IDs) identified by ticker+date+side?
- Is clean match count exactly 40 (not 56 or 58)?
- Are "missing from broker" and "missing from internal" correctly distinguished?

---

## Dimension 2: Exception Classification (Weight: 25%)

Are discrepancies correctly identified and categorized?

| Score | Description |
|---|---|
| 5 | All 6 exception types correctly identified with exact counts: price_break=5, quantity_break=3, missing_broker=2, missing_internal=2, settlement_date_mismatch=3, corporate_action_adjustment=5. Total=20. NVDA corporate actions correctly recognized as split-related, not treated as quantity breaks. |
| 4 | Most types correct, one miscounted by 1-2. |
| 3 | Exception types present but counts off. Corporate actions may be misclassified. |
| 2 | Only 2-3 types identified. |
| 1 | No meaningful classification. |

---

## Dimension 3: Dollar Impact Calculation (Weight: 25%)

Are P&L impacts correctly quantified?

| Score | Description |
|---|---|
| 5 | Price break impact = |price_diff| × quantity. Quantity break impact = unfilled_qty × price. Missing trades = $0 impact (not notional). Corporate action adjustments = $0 impact. Total ≈ $49,696. |
| 4 | Most impacts correct, total within 20% of golden. |
| 3 | Methodology partially right but total off by 2-5x. |
| 2 | Total off by more than 10x. Uses notional for missing trades. |
| 1 | No meaningful impact calculation. |

**Key check:** Total dollar impact should be approximately $49,696. If the agent reports ~$1.1M, it has incorrectly included notional values for missing trades or used total position value instead of break amounts.

---

## Dimension 4: Corporate Action Handling (Weight: 15%)

Did the agent correctly process the NVDA 4:1 stock split?

| Score | Description |
|---|---|
| 5 | NVDA 4:1 split identified and applied. Pre-split trades show post-split quantities (4x) and prices (÷4) at broker. Classified as corporate_action_adjustment, not quantity/price breaks. |
| 4 | Split correctly identified. Minor issues in explanation. |
| 3 | Split identified but inconsistently applied. |
| 2 | Split mentioned but treated as regular breaks. |
| 1 | Corporate actions ignored. |

---

## Dimension 5: Output Structure & Presentation (Weight: 10%)

| Score | Description |
|---|---|
| 5 | Three sheets as requested (Matched Trades, Exceptions, Summary). All columns present. Numbers formatted consistently. Summary statistics accurate. |
| 4 | All sheets present, minor formatting issues. |
| 3 | Sheets present but incomplete. |
| 2 | Some sheets missing. |
| 1 | Single data dump. |

---

## Scoring

| Dimension | Weight | Score (1-5) | Weighted |
|---|---|---|---|
| 1. Trade Matching Accuracy | 25% | __ | __ |
| 2. Exception Classification | 25% | __ | __ |
| 3. Dollar Impact Calculation | 25% | __ | __ |
| 4. Corporate Action Handling | 15% | __ | __ |
| 5. Output Structure & Presentation | 10% | __ | __ |
| **TOTAL** | **100%** | | **__/100** |

Weighted total = Σ (score × weight × 20)

**Grade thresholds:**
- **90-100:** Exceptional — production-quality reconciliation
- **75-89:** Strong — minor issues, operationally usable
- **60-74:** Adequate — framework correct but execution has gaps
- **40-59:** Below expectations — significant errors in matching or impact
- **Below 40:** Insufficient — fundamental rework needed

---

## Output Format

```json
{
  "dimensions": [
    {"name": "Trade Matching Accuracy", "score": <1-5>, "justification": "<2-3 sentences>"},
    {"name": "Exception Classification", "score": <1-5>, "justification": "<2-3 sentences>"},
    {"name": "Dollar Impact Calculation", "score": <1-5>, "justification": "<2-3 sentences>"},
    {"name": "Corporate Action Handling", "score": <1-5>, "justification": "<2-3 sentences>"},
    {"name": "Output Structure & Presentation", "score": <1-5>, "justification": "<2-3 sentences>"}
  ],
  "weighted_total": <number out of 100>,
  "grade": "<Exceptional/Strong/Adequate/Below Expectations/Insufficient>",
  "summary": "<3-4 sentence overall assessment>"
}
```
