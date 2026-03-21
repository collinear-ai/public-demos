# Multi-Source Trade Reconciliation with Exception Classification

## Objective

Perform a daily trade reconciliation for Apex Capital Management for the period January 6–17, 2025. Match the firm's internal trade blotter against broker confirmations, identify and classify all discrepancies, and quantify the financial impact of each break.

## Input Files

- **internal_blotter.xlsx** — The firm's internal trade records (book of record). Contains trade ID, ticker, side, quantity, price, trade/settlement dates, and broker for each trade.
- **broker_confirmations.xlsx** — Consolidated confirmations received from all brokers. Some confirmations have matching trade IDs; others may have blank or different IDs and must be matched on trade attributes.
- **corporate_actions.xlsx** — Registry of corporate actions (stock splits, dividends) effective during the period. These may cause legitimate differences between internal and broker records.
- **prices.xlsx** — Official end-of-day closing prices for all tickers in the trading universe, used for P&L impact calculations.

## Required Output

Produce an Excel file named **reconciliation.xlsx** with the following:

### Sheet 1: "Matched Trades"

All trades that were successfully matched between internal blotter and broker confirmations. Columns:

| Column | Description |
|--------|-------------|
| Trade ID | Internal trade ID |
| Ticker | Security ticker |
| Side | BUY or SELL |
| Internal Qty | Quantity per internal blotter |
| Internal Price | Price per internal blotter |
| Broker Qty | Quantity per broker confirmation |
| Broker Price | Price per broker confirmation |
| Match Method | "exact" (matched on trade ID) or "fuzzy" (matched on attributes) |
| Status | "clean" if no breaks, "break" if discrepancies exist |

### Sheet 2: "Exceptions"

All identified discrepancies. Columns:

| Column | Description |
|--------|-------------|
| Trade ID | Internal trade ID (or broker confirmation ID if missing internally) |
| Ticker | Security ticker |
| Exception Type | One of: price_break, quantity_break, missing_internal, missing_broker, settlement_date_mismatch, corporate_action_adjustment |
| Internal Value | The internal record's value for the discrepant field |
| Broker Value | The broker's value for the discrepant field |
| Dollar Impact | Estimated P&L impact of the break in dollars |
| Notes | Brief explanation |

### Sheet 3: "Summary"

Aggregate statistics:

| Metric | Value |
|--------|-------|
| Total Internal Trades | count |
| Total Broker Confirmations | count |
| Matched (Clean) | count |
| Matched (With Breaks) | count |
| Missing from Broker | count |
| Missing from Internal | count |
| Total Exceptions | count |
| Total Dollar Impact | sum |

## Critical Instructions

1. **Internal blotter is the book of record** — when a trade exists internally but not at the broker, classify as "missing_broker" (not the other way).
2. **Fuzzy matching**: Some broker confirmations lack trade IDs. Match these on ticker + trade date + side. If quantities also match, it's a clean match.
3. **Corporate actions**: Check the corporate_actions file. A stock split means pre-split trades may show different quantities/prices at the broker (which already reflects post-split). After adjustment, these should match — classify as "corporate_action_adjustment", not a break.
4. **Price breaks**: Small price differences (< $1.00) between internal and broker are typically commission adjustments. Still classify as "price_break" and calculate the dollar impact (|price_diff| × quantity).
5. **P&L impact**: For quantity breaks, impact = unfilled quantity × trade price. For price breaks, impact = |price_diff| × matched quantity. For missing trades, impact = $0 (no counterparty confirmation to compare against). For corporate action adjustments, impact = $0 (legitimate adjustment, not a real break).
