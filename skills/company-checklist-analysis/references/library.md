# Shared report library

Every rendered report also joins the personal HTML collection. Its default root is configured once in `assets/library-config.json`; use that same absolute root across tasks and projects. Do not create a separate library for every ticker. The portable default is `~/company-reports`, expanded to the current user’s home directory. An explicitly requested alternative can be passed with `--library ABSOLUTE_FOLDER` or saved in the configuration. This is local file storage, not hosting.

## Preparing a company card

Add this object alongside the research ledger's existing fields:

```json
{
  "library": {
    "company_id": "stable-company-and-security-id",
    "category": "Industrials",
    "category_evidence_ids": ["business-model"],
    "stats": ["revenue-ttm", "fcf-margin-ttm", "pe-ttm"],
    "logo": {"file": "company-logo.png", "source_id": "official-brand-source"}
  }
}
```

These IDs illustrate the structure; use real ledger IDs. `company_id` and `logo` are optional. For subsequent updates, retain the same company ID; assign a distinct ID to a different share class or ADR. Without an explicit ID, identity uses exchange, ticker and share class. A ticker rename with an explicit stable ID updates the same card.

Choose one primary business category supported by cited business/revenue evidence, using existing category names from `library.json` where they fit. Categories are broad business groupings, such as Software & services, Semiconductors, Industrials, Healthcare, Financial services, Consumer businesses, Energy, or Real estate; they are not an asserted formal GICS classification. Use the company's actual dominant economics; diversified businesses may have a Diversified category. Keep its specific industry visible on the card. Research conflicts or unknown classifications should remain explicit rather than guessed.

Choose two or three decision-relevant, numeric, sourced statistics for that business. Revenue/growth, profitability/returns, and a meaningful valuation measure are useful candidates; banks and REITs need appropriate sector measures. Reuse ledger values, display strings and IDs, including currency, units, periods and accounting basis. Do not use a model target, forecast, composite score or stale unlabeled live price. The renderer excludes assumptions and forecast-derived figures and links each statistic to its permanent evidence entry. If insufficient evidence makes two legitimate statistics impossible, omit `stats`; the renderer uses available observed headline metrics and states when none is available. Explain missing figures in the report.

Use the verified company logo from an official source, retain its source record, and save a local PNG, JPEG or WebP under 500 KB. The renderer embeds it into the index and bundles a copy beside the archived ledger. It makes no network requests. When no usable logo can be verified, omit `logo`: the card displays company initials with an accessible explanation. Do not substitute a lookalike logo or another company's mark. The sample collection uses initials for fictional companies.

The card's **Updated** date is `report.prepared_at`, and **Data as of** is `report.as_of`. Rebuilding the index or changing its style must not make old research appear newly verified. Quote metrics retain their observation date. Exact timestamps and metric context are inspectable, and material report gaps stay in the report; partial research is visibly labeled on its card.

## Registration and archive

The normal command validates, renders, archives, and refreshes the index automatically:

```text
python scripts/report.py render PATH/research.json --output PATH/report.html
```

Import an existing ledger or rebuild only the collection presentation with:

```text
python scripts/library.py add PATH/research.json
python scripts/library.py rebuild
```

`library.json` stores one current card per company/security and a history of report paths. Reports and ledgers live in dated, content-addressed snapshot folders under `reports/`. Identical re-renders do not create duplicates; updates keep old snapshots, and importing an older snapshot does not replace the latest card. A library lock prevents simultaneous writers from dropping each other's entries. If a command reports a busy library, retry once the writer finishes. If the writer crashed, inspect the abandoned lock before removing it. An error should be surfaced, never silently treated as successful registration. After an interrupted index write, `library.py rebuild` recovers the page from the registry.

The index is self-contained HTML and all report links within the collection are relative. Copy the entire library folder to move it, preserving `reports/` and `library.json`. Reports retain a link back to the index. Outside copies of an HTML report may need the shared library path to remain in place. Local source documents elsewhere on disk are not automatically bundled; retain those separately where authorized.

## Presentation and checks

Arrange cards in softly tinted business clusters with slight, stable offsets, readable text, subtle shadows and a restrained hover lift. Do not add continuous bobbing, dragging, force layouts, zoom controls, card overlap that hides content, or motion-dependent reading. Reflow to a phone-friendly column. Respect reduced-motion preferences. Search, category filters and sorting by name/update date enhance browsing; all cards and report links remain usable without JavaScript.

Keep synthetic examples separate from real company entries and visibly labeled. A separate `design-preview/` collection demonstrates multiple clusters without fabricating researched companies in the personal library. Do not add its fixtures during normal research.

Verify registration, latest/older snapshot behavior, source links, history and back-navigation. Inspect the collection at 320px, 390px, tablet and desktop widths; exercise search/filter/reset, keyboard focus and touch controls. Deliver both the company report and the shared index link.
