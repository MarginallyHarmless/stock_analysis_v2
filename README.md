# Company research library

A static, mobile-friendly library of company analysis reports with inspectable evidence and calculations.

## Live site

https://MarginallyHarmless.github.io/stock_analysis_v2/

The index contains real company research only. SOFI and META include the original checklist, peer comparisons, valuation scenarios, dated evidence, and explicit data gaps. Their evidence appendices support search, type filters, pagination, expandable records, and direct citation dialogs.

The [META case study](reports/meta-dd813908e2d1dfd7/2026-09-05-d1e98e5d3e676ba4/report.html) uses research available on September 5, 2026 and includes the corrected official company logo in the library. It provides independent English/Romanian and Beginner/Experienced controls, three valuation scenarios, and comparisons with Alphabet, Pinterest, and Snap. Historical valuation and peer valuation gaps remain explicit.

## Files

- `index.html`: standalone company library.
- `library.json`: report registry and snapshot history.
- `reports/`: report HTML, research ledgers, and issuer logos.
- `.nojekyll`: serves the files directly through GitHub Pages.

Reports retain their research cutoff and quote dates. Publishing or restyling does not refresh the research. The reports describe conditional analytical scenarios, not guaranteed outcomes.

## Publishing updates

GitHub Pages publishes the root of the `main` branch. Commit updated static files and push to `main`; GitHub rebuilds the site automatically. Keep the registry and every referenced report/history path together, and exclude fictional samples and local working files.

There is no package installation or application build. You can open `index.html` locally, or serve this directory with `python -m http.server 8000`.

## Reusable company-analysis skill

`skills/company-checklist-analysis/` contains the complete skill, original checklist, research method, Python renderers, HTML/CSS/JavaScript assets, and synthetic test fixture. Copy this folder into your Codex skills directory to install it.

The portable default library is `~/company-reports`. To write to this repository, pass its absolute path explicitly:

```text
python skills/company-checklist-analysis/scripts/report.py validate PATH/research.json
python skills/company-checklist-analysis/scripts/report.py render PATH/research.json --output PATH/report.html --library ABSOLUTE_REPOSITORY_PATH
```

New reports retain every checklist item and threshold, use concise visible findings with expandable reasoning, place scenarios in section 12 and peer comparisons in section 13, and keep all calculation inputs accessible. SOFI includes independent English/Romanian and Beginner/Experienced switches that remember the reader's choices. Beginner mode explains each criterion, the meaning of key figures and the conditional valuation scenarios, with a glossary; Experienced mode keeps the technical presentation. The evidence appendix initially shows key records, with all 313 records searchable. Both reading levels share the same financial evidence and research cutoff.
