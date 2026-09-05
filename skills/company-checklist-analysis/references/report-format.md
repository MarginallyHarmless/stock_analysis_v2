# Report contract and layout

## Deliverables

Create a dated folder with `report.html` and the supporting `research.json` ledger. Deliver the HTML as the report; PDF generation and export controls are outside the requested format. These are local artifacts; no server, account, CDN, remote font or public hosting is required. Match the user's language in authored prose; the bundled UI supports `en` and `ro`. Use a warm white background, charcoal text, muted green accent, editorial heading, readable sans-serif body, aligned numeric columns and restrained borders. Avoid decoration and motion that competes with reading.

The report begins with identity, cutoff, latest financial period, dated quote, business quality, price attractiveness, strongest evidence on both sides, and data gaps. Then show a clickable checklist map, preparation and the 14 original sections (with trends beside their relevant sections, scenarios in section 12 and peers in section 13), thesis invalidation/monitoring, open questions, optional indicators, evidence, original sources and freshness log. Keep conclusions and material caveats visible. Preserve every full finding and its evidence in the document; let readers expand detailed reasoning individually or with an expand-all control. Every concise finding remains visible, including material adverse evidence, uncertainties and original thresholds; full explanations may start closed. A source marker opens a concise hover/focus preview or a tap/click dialog with linked originals and calculation inputs. Every marker also points to a permanent appendix entry. Do not put essential caveats only in a tooltip or a closed detail.

Use visual structure sparingly: a small trend line beside a metric when its actual history exists, status dots for individual checklist items, simple diagrams for reconciled financial amounts, and a compact scenario results table. Checklist dots are categorical item statuses, not a company rating. The renderer draws a profit/cash diagram only from a validated two-input subtraction with nonnegative amounts, matching units and periods, and a positive total. Scenario results share a row label only when labels, periods and units match; otherwise each cell identifies its own measure and basis of comparison. A scenario's future price is still a future price, not present fair value. No invented chart points, composite scores, probabilities, ornamental gauges, large animations or intrusive effects. Keep the source ledger and all detailed calculations intact.

The report must work on narrow phones as well as desktop. Reflow navigation, metadata and metric groups; keep body text readable and source markers comfortably tappable. Source details open on tap in a viewport-sized, scrollable dialog with an accessible close control. Do not depend on hover. Charts have inspectable underlying tables, and every source includes a visible URL. Prevent page-wide horizontal overflow; use a local scroll container only when dense content cannot sensibly reflow.

## JSON schema, version 1

### English / Romanian switch

New reports include both languages in the same standalone HTML. Keep the canonical ledger prose in `report.language`, then add `translations` for the other language:

```json
{"translations":{"ro":{"strings":{"Strong growth":"Creștere puternică"}}}}
```

This is only a schema illustration; provide a complete mapping of exact canonical strings to reviewed translations. For a Romanian canonical ledger, use `translations.en.strings`. Use `scripts/localization.py:required_strings(data)` to identify mandatory authored strings. Include headings, conclusions, check explanations, evidence labels and notes, human-readable periods/units/bases, formula descriptions, scenario names/commentary, chart titles/descriptions and research-log results. Translate prose in numeric display suffixes and chart series names where applicable too. Preserve financial values and mathematical operators; never change `raw_value`, stable IDs, operations, inputs, timestamps, statuses, source records or URLs. Original publication titles and locators remain in their source language.

Validation rejects missing mandatory translations. Existing ledgers without translations remain renderable in their original language; they do not show a misleading language switch. The switch translates text and accessibility labels in place, keeps open evidence and pagination, and remembers the language when browser storage is available. Without JavaScript, the initial-language report and ordinary evidence links remain usable. Check both languages at 320px, 390px, tablet and desktop widths.

Every report is also registered in the shared company collection. Add `library` metadata for business category, stable identity, logo and two or three sourced statistics as described in [library.md](library.md). The normal render command preserves a dated snapshot and refreshes the shared index automatically.

Use `assets/example-report.json` to see complete structure and [checklist.json](checklist.json) for IDs. The example is **synthetic design/test data**, not an analysed company, a source collection, or a research baseline. For live work create new evidence, source and prose objects from the actual research; never relabel the fixture as real.

Top level:

| Field | Shape / purpose |
| --- | --- |
| `schema_version`, `demo` | `1`, and an explicit boolean. Only set `demo: false` for researched company data. |
| `company` | Strings: `name`, `ticker`, `exchange`, `share_class`, `currency` (clearly describe reporting/trading currencies if different), `industry`. |
| `library` | Primary `category`, `category_evidence_ids`, two or three `stats` evidence IDs, optional stable `company_id`, optional local sourced `logo`. See [library.md](library.md) for the shared collection and unavailable-data fallback. |
| `report` | `language` (`en`/`ro`), `as_of`, `prepared_at`, `freshness_checked_at` (ISO timestamps with timezone); `financial_period`, `horizon`, `subtitle`; `research_status` (`complete` or `partial`); `quote_evidence_id`. |
| `sources` | Array of original source records, below. |
| `evidence` | Array of evidence records, below. |
| `summary` | Array of clauses. Cover business quality, price attractiveness, support and opposition; quantitative assertions reference evidence. |
| `highlights` | Evidence ID array for a small selection of important metrics. |
| `sections` | Exactly 15 objects with string `id` from `0` through `14`, `intro` clause, optional `metrics` evidence ID array, and `checks` for all subitems assigned to that section. |
| `optional` | Six check objects with IDs O1 through O6, even when not researched. |
| `peers` | Array of `{name, rationale: clause, metrics: [evidence IDs], assessment: clause}`. Use a comparison table or aligned metric rows where useful. `peer_note` explains missing coverage or comparability limits. |
| `peer_table` | Optional `{columns: [company names], rows: [{label, cells: [clauses]}]}`. Each row has one cell per column. Prefer one matrix covering revenue mix, management, allocation, capital intensity, financial health, profitability and valuation; add growth when useful. Identify unavailable or incomparable evidence explicitly. Existing `peers` rationale and detail remain expandable. |
| `scenarios` | Exactly three objects with `key` (`bear`/`base`/`bull`), localised `name`, `assumptions` evidence IDs, `results` evidence IDs, and `commentary` clause. An unavailable result record is acceptable when a credible numerical model cannot be built. |
| `monitoring`, `gaps` | Arrays of clauses. State explicitly if no additional gap is identified after the performed checks. |
| `charts` | Optional array: `{title, description, unit, section_id?, series: [{name, points: [{label, evidence_id}]}]}`. `section_id` places the chart beside that checklist section (0–14); unassigned legacy charts remain near the overview. Points require numeric raw values. Each series must use identical time labels and compatible units; the renderer positions categories at equal intervals, so do not use this for irregular-date series without adapting the plotting code. |
| `research_log` | Array `{topic, checked_at, source_ids, result}`. Real reports need topics `filings`, `results`, `material_events`, `quote`, `ownership`, `estimates`. State what was checked, latest available result, disclosure lag and any access limitation. |

A **clause** is `{label?: string, text: string, evidence_ids: [IDs]}`. `label` is a short lead-in. Use references for every material factual/numerical assertion and judgment; pure navigation and explicit statements of research limitations may have no references. All strings are plain text, escaped by the renderer; do not embed HTML or Markdown.

A **check** is `{id, status, explanation, evidence_ids, finding?: clause, related_section?: string}`. New reports should provide a concise `finding` for every core item, normally one or two sentences and one to three primary references. It must include material caveats and original thresholds. The full explanation and all references remain expandable. `related_section` links to the main discussion (0–14). Legacy checks without findings render their original explanation directly. Status is one of `meets`, `mixed`, `does_not_meet`, `insufficient_evidence`, `not_applicable`. A supported positive/negative/mixed assessment needs evidence beyond missing data or model assumptions. Missing evidence needs a reason, never invented inputs. State the original threshold inside the explanation when the subitem contains one, and explain any sector adjustment.

### Source records

Required: `id` (unique safe identifier), `title`, `publisher`, `source_type`, `locator`, `url` (HTTP/S) or `file` (local source path), `published_at` (ISO date/timestamp) or null with `date_note`, `accessed_at` (timestamp with timezone), and `verification` (`opened` or `user_provided`; `demo` only for synthetic previews). A source URL should resolve to the exact filing/article/document. `locator` provides page, table, section, filing accession, transcript timestamp or equivalent. Add `period` when useful.

An `opened` label records that the agent actually inspected the source; the validator cannot prove it. Unknown publication dates should remain unknown. Local paths provide provenance, but need bundled evidence or a source copy if the report is to be portable; never publish local user files without authorisation. Do not include long copyrighted excerpts in the ledger.

### Evidence records

Required: `id`, `label`, `display`, `kind`, `raw_value` (number or precise decimal string; null for qualitative/unavailable entries), `unit`, `period`, `basis`, `note`, `source_ids`, and optional supporting `evidence_ids`.

`kind`: `reported`, `calculated`, `estimate`, `assumption`, `judgment`, `unavailable`. Notes explain method, interpretation or material caveats; they are not a substitute for original evidence. `basis` states statutory/GAAP/IFRS/adjusted, price/session, model assumption, or other relevant convention. For dimensionless or narrative records say `unit: "qualitative"` or `"multiple"`, not an empty string. Store numeric scale such as `USD million`, not just `USD`.

Reported and external-estimate evidence requires source IDs. Judgments require original sources or supporting evidence IDs. Assumptions must be explicit and justified in `note`. Calculated evidence needs `calculation`:

```json
{
  "operation": "percent",
  "inputs": ["fcf", "revenue"],
  "formula": "FCF margin = (operating cash flow - cash CAPEX) / revenue × 100"
}
```

Operations and their conventions are in research-method.md. An optional `years` applies only to CAGR. Store the calculated `raw_value` at sufficient precision; the validator recomputes and checks within relative/absolute 1e-8. `display` is human-readable and may be rounded, but must match raw value and units; review display rounding separately. Cyclic lineage, unsupported input IDs and non-positive ratio denominators fail validation.

For quote evidence add `observed_at` with timezone and `session` (regular close, delayed intraday, extended hours, etc.). If the quote is unavailable, make the record unavailable and qualify price-dependent conclusions. EPS or currency adjustments must be traceable through input records.

## Rendering and mobile review

The Python renderer requires only the standard library:

```text
python scripts/report.py validate /absolute/path/research.json
python scripts/report.py render /absolute/path/research.json --output /absolute/path/report.html
```

Use an available browser to inspect the generated HTML at 320px, 390px, tablet and desktop widths. Test a touch-enabled viewport: tap a source, inspect the calculation inputs, follow an input, close the dialog, and expand a chart's underlying data. Also test keyboard focus and the ordinary appendix-link fallback without JavaScript. Browser automation is useful for these checks but is not a dependency of the delivered report.

## Validation boundaries

`report.py validate` checks required structure, all checklist subitems, evidence/source references, supported numerical operations, calculation cycles, key timestamp ordering, scenario presence and source URL safety. It does **not** verify truth, identify the latest filing, validate a model's economics, resolve URLs, detect every basis/period mismatch, evaluate the quality of an analytical judgment, or certify the prose. Those remain research and review work.

Before delivery check source-to-claim relevance, units, formula applicability, displayed rounding, quote/estimate dates, comparability, historical cutoffs, and scenario interpretation. Inspect desktop, mobile, keyboard focus, touch/click, and no-JavaScript fallback. Report data gaps prominently. Keep past report snapshots when updating.

## Evidence scope

Default the searchable, paginated appendix to direct evidence references in visible findings, section summaries and metrics, highlights, monitoring, peer-table cells and scenario results. The renderer derives this subset; it never deletes records or input lineage. “Include supporting inputs” reveals the complete ledger, search covers every record, and direct links reveal their target even outside the current subset. Keep the freshness log in an expandable block while the actual cutoff and material freshness limitations remain visible.
