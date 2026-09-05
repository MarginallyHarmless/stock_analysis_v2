# Research and calculation method

## Source hierarchy and freshness

1. Establish security identity on the issuer or exchange website; distinguish listings, share classes, ADRs, splits and redenominations. Separate listing currency from accounting currency.
2. Open the regulator's filing index and the issuer's investor-relations results page. Locate the latest annual and interim financials and any newer earnings release, amendments, restatements, or material-event filing. US examples include 10-K/10-Q/8-K, 20-F/6-K, DEF 14A and Forms 3/4/5. Use the equivalent regulator, exchange and disclosure system for other markets, including BVB/issuer disclosures for Romanian issuers. Filing conventions and reporting frequency vary; verify the relevant market rather than assuming US rules.
3. Prefer filed audited annual figures for annual history. A newer unaudited release can provide the freshest figures, clearly identified as such; it does not become audited because an older annual report was audited. Use later restated comparatives when available and explain their effect.
4. Use original presentations, earnings calls and Investor Day materials for strategy and guidance. Attribute management statements. Seek corroborating customer, competitor, regulator or other original evidence for market-share and moat claims.
5. Use a reputable market-data source for the quote and historical prices; cross-check the identity, currency, session and timestamp with another source when available. State whether a quote is delayed, intraday, regular close or extended hours. A weekend's latest completed session is valid; do not manufacture a weekend quote. Never use the browser retrieval time as the price time.
6. Analyst estimates need provider, estimate date, forecast fiscal period, basis, and contributor count if available. If consensus is inaccessible, label it unavailable. Management guidance and model assumptions are not consensus.
7. Treat Yahoo Finance, Morningstar, Fintel, Barchart, Marketplace Pulse, HedgeFollow, BuyUpside, Macrotrends and Seeking Alpha as possible secondary research paths from the original checklist, not compulsory subscriptions or equally authoritative sources. Trace important claims to their originals. Do not circumvent access restrictions or imply that a paywalled source was inspected.

Record `as_of` (information cutoff), `prepared_at`, `freshness_checked_at`, source publication/access dates, each financial period, and quote timestamp. Use ISO 8601 timestamps with UTC offset for report/quote events. For each major data class, record where the latest available material was checked and what was found. A recently accessed old document is still old; ownership, short-interest and options reports have their own observation dates and publication lags. Say "latest available, period ended ..." where appropriate.

Before delivery repeat the filing/results/material-events check and refresh affected calculations. Do not count multiple aggregators copying one feed as independent confirmation. When sources differ, compare dates, amendments, units, currency, share class, GAAP/IFRS vs adjusted measures, fiscal/calendar periods, denominator construction and consolidation scope. Preserve the conflicting readings and explain why the chosen one is better supported. If unresolved, show a range or unavailable status and its implication.

## Numerical discipline

- Use scripts for arithmetic and retain full precision in the ledger; round only the display. Store units and scale explicitly. Compare ratios only after harmonising definitions.
- Put annual, latest-quarter, year-to-date, trailing-twelve-month (TTM), and forecast results in clearly distinct columns. Do not mix components from different periods.
- TTM flow = latest full year + current YTD - comparable prior-year YTD, or the sum of four non-overlapping fiscal quarters. Check matching YTD duration, 52/53-week years, restatements and scope changes. A balance-sheet stock is a point-in-time value and cannot be constructed with a TTM sum.
- Convert currencies using a sourced rate suitable for the purpose and date; record the rate and direction. Do not silently translate historical results at today's exchange rate. Use split-adjusted per-share histories consistently.
- Missing, zero, and negative values are distinct. Never convert missing values to zero. A ratio with zero or economically invalid denominator is "not meaningful", not infinity, zero, or a checklist pass.

### Consistent definitions

| Measure | Calculation and interpretation |
| --- | --- |
| Gross margin | (Revenue - cost of revenue) / revenue × 100. Explain classifications and lack of comparable gross profit where relevant. |
| Cash CAPEX | Positive magnitude of cash expenditure on property/equipment and the disclosed capitalised intangibles/software relevant to operations. State inclusions; track noncash lease additions separately. Do not include acquisitions silently. |
| Standardised FCF | Operating cash flow - defined cash CAPEX. Show the original lines; reconcile to company-reported adjusted FCF if different. FCF is not cash that is automatically distributable after all obligations. |
| FCF margin | Standardised FCF / revenue × 100. Positive revenue is required; a negative FCF margin is valid. |
| CAPEX / revenue | Same-period positive CAPEX / revenue × 100. Interpret maintenance vs growth investment only if disclosed or explicitly estimated. Low investment alone is not evidence of quality. |
| CAPEX / operating cash flow | Positive CAPEX / same-period CFO × 100. Non-positive CFO makes this ratio unsuitable as a favourable screening measure. |
| Net debt | Interest-bearing short- and long-term debt less cash and cash equivalents. State treatment of leases, restricted cash and liquid investments. Never silently deduct inaccessible cash. |
| Net debt / FCF | Latest balance-sheet net debt / matched TTM FCF. Original target: below 4×. Non-positive FCF is not meaningful. A negative numerator means net cash; explicitly show that state instead of interpreting a negative result as repayment years. |
| Interest coverage | EBIT / gross interest expense, using matched periods. Original checklist says interest payments: clarify whether cash paid or accrual expense is used and show the alternate when material and available. Do not use net interest income as the denominator. Zero interest expense is "no interest expense", not infinite coverage; negative EBIT indicates weak coverage. Original target: above 10×. |
| NOPAT | Operating profit × (1 - disclosed/normalised operating tax rate). Explain chosen tax rate and adjustments, especially when effective tax rate is distorted. |
| ROIC | NOPAT / average invested capital × 100. Define invested capital consistently (e.g. operating assets less non-interest-bearing operating liabilities, or equity + interest-bearing debt - excess cash) and average beginning/end balances. State goodwill/lease treatment; significant acquisitions may justify more frequent averages. Do not equate all cash with excess cash without analysis. Negative or negligible capital can make ROIC misleading; do not use it as a mechanical pass. Original target: above 15%; evaluate sustainability and capital cost when estimable. |
| Historical CAGR | (End / Start)^(1 / elapsed fiscal years) - 1. Five years require endpoints five years apart, normally six annual observations. Ten years require eleven. Use diluted EPS consistently; where endpoints are non-positive, report absolute changes, annual history and recovery/loss context instead of a conventional CAGR. |
| P/E | Timestamped per-share price / compatible diluted EPS. Label TTM or specified forecast year, statutory or adjusted, security class and currency. Non-positive EPS makes P/E unsuitable. |
| Five-year historical P/E | Specify sampling frequency and denominator convention. Prefer a reproducible series of contemporaneous trailing P/E observations, with exclusions and coverage. Never construct historical P/E by dividing old prices by today's EPS. Compare like basis to like basis; forward vs trailing differences need explanation. |
| Enterprise value | Equity market value + relevant debt/preferred/minority interests - applicable cash/investments. State bridge, share count date, and treatment of leases. Match enterprise multiples to enterprise earnings/cash flow. |

Built-in calculator operations: `sum`, `difference` (first minus remaining inputs), `product`, `average`, `ratio`, `percent`, `cagr`, `ttm`. `percent` multiplies a two-input ratio by 100; `cagr` returns percentage points and requires positive endpoints and positive integer `years`; `ttm` takes full-year/current-YTD/prior-YTD. Combine operations to make a ROIC or enterprise-value bridge. Every input is another evidence ID; never place executable expressions in data. Use an explicitly documented calculation extension for a model these operations cannot express; test it and maintain source lineage.

## Checklist applicability and judgment

The thresholds are the source author's screening preferences, not universal laws or calibrated predictors. Preserve their literal comparison (`>` vs `>=`). High-growth outlook thresholds (revenue above 20%, EPS above 15%) apply to that category, not every mature firm. Preparation's structural-change thesis is a preference; a cyclical or stable business still deserves a completed assessment.

For banks and insurers, ordinary industrial-company CFO, net debt, gross margin and ROIC screens may be inappropriate. Show the original item as not applicable with reasoning, then add current sector metrics (e.g. relevant capital adequacy, credit quality, profitability, underwriting and solvency measures) using regulator/issuer definitions. For REITs, assess property cash economics, leverage and clearly reconciled FFO/AFFO where useful. For pre-revenue companies, focus on cash runway, funding and verifiable milestones, and do not use negative P/E or fabricated EPS CAGR. For cyclicals, consider normalised through-cycle earnings; disclose the normalisation.

A moat judgment needs more than high margins: test price/mix, retention, switching costs, cost advantage, distribution, IP, network effects, competitor entry and evidence of persistence as relevant. Distinguish demonstrable advantage from management marketing.

Insider purchases: distinguish open-market purchases from awards, options exercises, conversions and tax withholding. State transaction and filing dates and any disclosed plan context. Institutional filings describe a dated, incomplete view, not current buying. Verify current disclosure scope and delays before interpreting them. Short interest is not daily short-sale volume; options put/call volume is not put/call open interest. Specify settlement/observation date, universe and calculation. Do not interpret online buzz or technical indicators as fundamental proof.

Shareholder alignment: inspect voting/economic ownership, compensation, related-party concerns and capital allocation results. Compare buyback spend with net diluted share-count change and stock-based compensation. Assess debt maturities against liquidity and cash needs, not merely cash-to-debt totals. Attribute reputation allegations and material legal issues to credible evidence, and avoid speculation about personal health.

## Peers, valuation and thesis

Explain why each peer is comparable by business model, customer base, geography, growth or capital requirements. Use compatible dates, periods and accounting definitions, or flag the limitation in the comparison itself. Assess the same relevant checklist dimensions, including management and allocation; a multiples-only peer table is incomplete. If fewer than three suitable peers exist, say so rather than padding.

Use bear/base/bull scenarios with a common valuation date and horizon, a method appropriate to the sector, disclosed assumptions and calculated outputs. A simple terminal EPS × P/E model gives a future price, not today's intrinsic value; discount or label it correctly. A DCF must match cash-flow ownership to discount rate, show terminal assumptions, and bridge enterprise to equity/per-share value. Include dilution, debt, cash, distributions and FX where relevant. Do not silently add dividends to a price-only return or call a cumulative return annualised.

Show sensitivity to the assumptions that drive the outcome. Present ranges with sensible rounding; no invented probabilities or false precision. If insufficient inputs exist, show the scenario framework and unresolved inputs without numerical targets. Separate "business quality" from "attractiveness at the observed price"; include disconfirming evidence and concrete invalidation conditions.

For price history distinguish split-adjusted price return from dividend-reinvested total return. Benchmark against a justified index or peers with the same dates, currency and return convention. Treat past price appreciation as context, not a forecast.

## Primary methodology references

These links support definitions and source selection; verify current guidance when applying jurisdiction-specific rules. They are not company data sources.

- SEC, [How to Read a 10-K](https://www.sec.gov/answers/reada10k.htm).
- SEC, [Non-GAAP Financial Measures](https://www.sec.gov/rules-regulations/staff-guidance/corporation-finance-interpretations/non-gaap-financial-measures), especially 100.05 and 102.07 on labels, comparability and FCF definitions. Reviewed 2026-09-05.
