# Company research library

A static, mobile-friendly library of company analysis reports with inspectable evidence and calculations.

## Live site

https://MarginallyHarmless.github.io/stock_analysis_v2/

The index contains real company research only. SOFI includes the original checklist, peer comparisons, valuation scenarios, dated evidence, and explicit data gaps. Its evidence appendix supports search, type filters, pagination, expandable records, and direct citation dialogs.

## Files

- `index.html`: standalone company library.
- `library.json`: report registry and snapshot history.
- `reports/`: report HTML, research ledgers, and issuer logos.
- `.nojekyll`: serves the files directly through GitHub Pages.

Reports retain their research cutoff and quote dates. Publishing or restyling does not refresh the research. The reports describe conditional analytical scenarios, not guaranteed outcomes.

## Publishing updates

GitHub Pages publishes the root of the `main` branch. Commit updated static files and push to `main`; GitHub rebuilds the site automatically. Keep the registry and every referenced report/history path together, and exclude fictional samples and local working files.

There is no package installation or application build. You can open `index.html` locally, or serve this directory with `python -m http.server 8000`.
