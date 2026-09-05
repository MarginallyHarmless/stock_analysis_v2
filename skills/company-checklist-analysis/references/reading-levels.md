# Reading levels: one analysis, two explanations

Provide a Beginner / Experienced switch independent of EN/RO. Experienced keeps the full technical presentation. Beginner is an authored teaching layer, not a shorter summary selected by a word filter. Explain the business first, then the few decisive numbers, opposing evidence and valuation assumptions. Give each section a question the reader can answer. For a metric, explain its unit, period, meaning and relevant limitation. Explain how it can change a judgment without turning a threshold into a mechanical trade instruction or assuming the reader's risk tolerance.

For example, describe a forward P/E as the price paid for each unit of estimated annual earnings per share. State that forecast earnings may not arrive and that this is not a guaranteed payback period. Distinguish revenue from profit, company profit from per-share profit, accounting return on equity from stock return, bank capital from cash, and present value from a future price. Use only distinctions relevant to the company. A glossary supports these explanations but does not replace them.

## Ledger contract

New reports add `audience` alongside the existing canonical financial ledger and translation map:

```json
{"audience":{"default":"beginner","versions":{"en":{},"ro":{}}}}
```

Each version contains the following reviewed prose. The English and Romanian versions use identical item keys, matching list lengths and the same evidence IDs. This object is excluded from the general exact-string translation mapping because its two reviewed language versions are already explicit.

- `orientation`: clauses explaining how to read the analysis and its scope/limitations.
- `summary`: clauses covering business quality, price attractiveness, strongest support and opposition. Do not soften the conclusion in Beginner mode.
- `sections`: map of every section ID `0`–`14` to a clause whose `label` is a plain-language question and whose `text` explains the section's practical role and company-specific interpretation.
- `checks`: map of every core and optional checklist ID to a clause with a plain-language `label`, finding and meaningful caveats. Preserve all original numeric thresholds and explain sector exceptions. Beginner mode keeps the original status; it cannot turn insufficient evidence into a pass.
- `highlights`: a small selection of existing evidence IDs, identical across languages.
- `metrics`: map of each selected highlight ID to a clause with an understandable `label` and a short explanation of the value, unit and limitation. The renderer takes the displayed value from the shared ledger; never make a second numerical dataset.
- `scenarios`: map of `bear`, `base`, `bull` to clauses explaining the conditions and limitations. The first result of each scenario must be the same measure on the same date (usually present value per share), since these are the values shown in the Beginner cards. If results are not comparable, explain the differences rather than presenting a comparable set of cards.
- `peers`: clauses explaining why the chosen businesses are useful comparisons and where comparisons break down.
- `glossary`: clauses whose labels are unfamiliar terms and whose text gives concise definitions relevant to this report.

A clause uses the existing `{label, text, evidence_ids}` shape. Company-specific assertions require references. Pure reading instructions and definitions may have an empty reference array. Full methods, caveats and source links remain in the original ledger. Do not invent figures, probabilities, peer equivalence or a confidence score to make the explanation easier.

## Behavior and checks

The renderer validates coverage and evidence IDs, compiles both reading levels into one standalone report and defaults new readers to Beginner when JavaScript is available. The level and language switches update the current document in place and store separate preferences, with a safe fallback when browser storage is unavailable. They must preserve section identity, open evidence dialogs and source/calculation links. Without JavaScript the original complete technical report and evidence disclosures remain readable; switch controls are hidden.

Legacy ledgers without `audience` remain renderable and show no misleading level control. Do not fabricate generic Beginner prose to retrofit them automatically. For a user-requested rewrite, author and review the teaching layer, preserve the evidence and dates, and update the requested current report while preserving prior snapshots.

Test RO/Beginner, RO/Experienced, EN/Beginner and EN/Experienced at phone and desktop widths. Check keyboard activation, persisted independent choices, blocked storage, switching with a calculation open, search, nested evidence, direct links and no-JavaScript fallback. Confirm financial values, source records, checklist statuses, estimates, calculations and historical cutoffs are identical before and after a readability-only edit. Validate prose for beginner comprehension as well as schema correctness.
