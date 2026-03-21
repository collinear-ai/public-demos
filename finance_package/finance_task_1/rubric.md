# KO Investment Manager Analysis — LLM Judge Rubric

You are evaluating an Excel workbook built for an Investment Manager analyzing The Coca-Cola Company (KO) using FY2022–FY2024 SEC filings and market data as of the 2024-12-31 close. The workbook should have three tabs: Revenue Quality, Cash Economics, and Valuation Context. A programmatic verifier has already checked whether specific golden values are present. Your job is to evaluate what code cannot: analytical quality, sourcing rigor, and professional presentation.

You will be given the full cell-level content of the submitted workbook. Score each dimension from 1-5, provide a brief justification, then compute a weighted total out of 100.

---

## Dimension 1: Revenue Quality Analysis (Weight: 20%)

Does Tab 1 help an Investment Manager understand KO's top-line growth?

| Score | Description |
|---|---|
| 5 | Volume vs. price/mix decomposition is present with exact figures from 10-K MD&A for all three years. Geographic segment revenues (all 6-7 segments) are shown with totals that reconcile. Concentrate vs. finished product revenue mix is quantified with percentages and trend. Analyst commentary adds context (e.g., hyperinflationary markets, refranchising impact). |
| 4 | Volume/price/mix and geographic breakdowns are present and mostly correct. One component missing or one year's data incomplete. Concentrate/finished product split present. |
| 3 | Basic revenue data present but decomposition is incomplete. May show totals but not the volume/price/mix split, or geographic segments are aggregated. Some estimates used instead of filing data. |
| 2 | Revenue figures present but no meaningful decomposition. Missing geographic or volume/price analysis. |
| 1 | Minimal or no revenue analysis. Only total revenue without breakdown. |

**Key values to check:**
- FY2024 Net Revenue: $47,061M (not ~$46,000 estimated)
- Geographic segments: North America $18,636M, EMEA $7,508M, Latin America $6,434M, Asia Pacific $5,546M, Bottling $5,906M
- Organic revenue growth: 16% (FY22), 12% (FY23), 12% (FY24)
- Price/Mix as % of organic: 69% (FY22), 83% (FY23), 92% (FY24) — overwhelmingly price-driven

---

## Dimension 2: Cash Economics Analysis (Weight: 20%)

Does Tab 2 show whether KO converts earnings to cash efficiently?

| Score | Description |
|---|---|
| 5 | Complete cash flow build: Net Income → D&A → EBITDA → CFO → CapEx → FCF for all three years. FCF/NI conversion ratio shown. Working capital metrics computed (DSO, DIO, DPO, CCC). Shareholder returns (dividends + buybacks) vs. reinvestment quantified. IRS tax litigation deposit ($6B) in FY2024 correctly identified and adjusted for in FCF analysis. |
| 4 | Most components present. FCF and conversion ratios correct. Working capital or shareholder returns section slightly incomplete. IRS deposit may be noted but not fully adjusted. |
| 3 | FCF calculated but missing working capital analysis or shareholder returns breakdown. OR: correct components but significant numerical errors. |
| 2 | Basic profitability data without FCF build or working capital analysis. |
| 1 | Minimal cash analysis. No FCF calculation. |

**Key values to check:**
- FY2024 CFO: $6,805M (low due to $6,000M IRS deposit)
- FY2024 FCF: $4,741M (or $10,741M excluding IRS deposit)
- FY2024 EBITDA: $11,067M
- Cash Conversion Cycle: approximately -46 to -49 days (negative — KO collects before paying)
- Total Shareholder Returns FY2024: $10,161M ($8,366M dividends + $1,795M buybacks)

---

## Dimension 3: Valuation Context (Weight: 20%)

Does Tab 3 give a quick valuation snapshot?

| Score | Description |
|---|---|
| 5 | Market cap and enterprise value correctly computed with transparent net debt methodology. 3-4 relevant multiples (P/E, EV/EBITDA, EV/EBIT, FCF Yield, Dividend Yield) using as-of 12/31/2024 price. KO vs. PEP and S&P 500 price returns for 1-year and 3-year windows with correct date endpoints. All values sourced. |
| 4 | EV bridge and multiples mostly correct. Price returns present but one window or comparator slightly off. |
| 3 | Market cap present but EV bridge incomplete or uses wrong debt/cash figures. Multiples present but may use wrong denominators. Returns show directional comparison but without precise date-to-date computation. |
| 2 | Basic market cap only. No EV, limited multiples, vague return comparisons ("~10%"). |
| 1 | No meaningful valuation data. |

**Key values to check:**
- Share price 12/31/2024: $62.17
- Shares outstanding: ~4,320M diluted
- Market Cap: ~$268,574M
- Enterprise Value: ~$298,045M
- EV/EBITDA: ~26.9x
- KO 1-year return: ~5.5%, vs. S&P 500 ~24.7%, vs. PEP ~-12.5%

---

## Dimension 4: Data Sourcing & Documentation (Weight: 20%)

Is every number traceable to a filing?

| Score | Description |
|---|---|
| 5 | Every data input has a precise filing reference (form type, fiscal year, statement name, section). No hardcoded figures without citations. Analyst assumptions clearly labeled. Sign conventions documented. GAAP vs. non-GAAP distinctions noted. |
| 4 | Most values have filing references. One or two items lack specific citations. Assumptions mostly documented. |
| 3 | Some filing references present but inconsistent. Several values appear without sources. Some estimates not clearly labeled as such. |
| 2 | Sporadic sourcing. Many values have no citation. Hard to tell what's from filings vs. estimated. |
| 1 | No source citations. Numbers without context. Uses "~" approximations instead of filed data. |

**Evaluate:**
- Are 10-K filing dates referenced (FY2024: filed 2025-02-20)?
- Does each row cite the specific statement or note (e.g., "Note 20 — Operating Segments")?
- Are estimates clearly labeled as estimates vs. filed data?
- Is the difference between "~46,000" (unsourced estimate) and "$47,061" (10-K filed data) reflected in the score?

---

## Dimension 5: Visual Hierarchy & Readability (Weight: 10%)

Is the workbook organized for quick consumption by an Investment Manager?

| Score | Description |
|---|---|
| 5 | Clear section headers, structured tables with labeled columns, consistent number formatting ($M, %, x multiples). Analyst notes/commentary stand out from data. White space separates sections. Eye naturally flows to key insights. |
| 4 | Good organization, minor formatting inconsistencies. |
| 3 | Adequate but plain. Data present but not visually structured for scanning. |
| 2 | Dense or monotonous. Headers and data blend together. |
| 1 | Wall of text. No visual structure. |

---

## Dimension 6: Completeness vs. Task Requirements (Weight: 10%)

Did the agent address all three questions in each tab?

| Score | Description |
|---|---|
| 5 | All 3 tabs present. Tab 1 addresses volume/price, geographic diversification, and concentrate vs. finished product. Tab 2 addresses earnings-to-cash conversion, capital intensity, shareholder returns, and working capital. Tab 3 has market cap, EV, multiples, and price return comparisons. |
| 4 | All tabs present, one sub-question partially addressed. |
| 3 | All tabs present but each missing 1-2 sub-questions. |
| 2 | One tab largely missing or two tabs significantly incomplete. |
| 1 | Only one meaningful tab. |

---

## Scoring

| Dimension | Weight | Score (1-5) | Weighted |
|---|---|---|---|
| 1. Revenue Quality Analysis | 20% | __ | __ |
| 2. Cash Economics Analysis | 20% | __ | __ |
| 3. Valuation Context | 20% | __ | __ |
| 4. Data Sourcing & Documentation | 20% | __ | __ |
| 5. Visual Hierarchy & Readability | 10% | __ | __ |
| 6. Completeness vs. Task Requirements | 10% | __ | __ |
| **TOTAL** | **100%** | | **__/100** |

Weighted total = Σ (score × weight × 20)

**Grade thresholds:**
- **90-100:** Exceptional — institutional quality, ready for a PM's desk
- **75-89:** Strong — minor polish needed, analytically sound
- **60-74:** Adequate — framework is there but execution has gaps
- **40-59:** Below expectations — significant analytical or data gaps
- **Below 40:** Insufficient — fundamental rework needed

---

## Output Format

```json
{
  "dimensions": [
    {"name": "Revenue Quality Analysis", "score": <1-5>, "justification": "<2-3 sentences>"},
    {"name": "Cash Economics Analysis", "score": <1-5>, "justification": "<2-3 sentences>"},
    {"name": "Valuation Context", "score": <1-5>, "justification": "<2-3 sentences>"},
    {"name": "Data Sourcing & Documentation", "score": <1-5>, "justification": "<2-3 sentences>"},
    {"name": "Visual Hierarchy & Readability", "score": <1-5>, "justification": "<2-3 sentences>"},
    {"name": "Completeness vs. Task Requirements", "score": <1-5>, "justification": "<2-3 sentences>"}
  ],
  "weighted_total": <number out of 100>,
  "grade": "<Exceptional/Strong/Adequate/Below Expectations/Insufficient>",
  "summary": "<3-4 sentence overall assessment>"
}
```
