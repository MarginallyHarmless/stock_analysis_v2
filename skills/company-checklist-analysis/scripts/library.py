"""A local, portable company library. No network access or runtime dependencies."""
import argparse
import base64
import hashlib
import html
import json
import os
import re
import sys
import tempfile
from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]


def esc(value):
    return html.escape(str(value), quote=True)


def config():
    return json.loads((ROOT / "assets/library-config.json").read_text(encoding="utf-8"))


def settings_for(root):
    settings = config()
    settings["gallery"] = (root / "design-preview/index.html").is_file()
    if root.name == "design-preview":
        settings["title"] = "A sample collection"
        settings["parent_href"] = "../index.html"
    return settings


def library_root(override=None):
    configured = Path(override or config()["root"]).expanduser()
    if not configured.is_absolute():
        raise ValueError("Library root must be absolute so reports from different tasks join the same collection")
    return configured.resolve()


def encode(data):
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def atomic_write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=".writing-", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextmanager
def locked(root):
    root.mkdir(parents=True, exist_ok=True)
    lock = root / ".library.lock"
    try:
        handle = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise ValueError("Another library update is in progress. Retry after it finishes; inspect an abandoned lock before removing it.")
    try:
        os.close(handle)
        yield
    finally:
        lock.unlink()


def safe_path(root, relative):
    if not isinstance(relative, str) or "\\" in relative or ":" in relative:
        raise ValueError("Library paths must be relative")
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()) or path == root.resolve():
        raise ValueError("Library path escapes its collection")
    return path


def rel_link(target, parent):
    return quote(os.path.relpath(target, parent).replace(os.sep, "/"), safe="/.-_")


def card_metrics(data):
    evidence = {item["id"]: item for item in data["evidence"]}

    def observed(key, seen=None):
        seen = set() if seen is None else seen
        if key in seen or key not in evidence:
            return False
        item = evidence[key]
        if item["kind"] not in ("reported", "calculated") or item.get("raw_value") is None:
            return False
        inputs = item.get("calculation", {}).get("inputs", []) + item.get("evidence_ids", [])
        return all(observed(child, seen | {key}) for child in inputs)

    explicit = data.get("library", {}).get("stats")
    keys = explicit if explicit is not None else data.get("highlights", [])
    selected = [key for key in dict.fromkeys(keys) if observed(key)]
    if explicit is not None and (len(keys) not in (2, 3) or len(selected) != len(keys)):
        raise ValueError("library.stats needs two or three unique numeric reported/calculated evidence IDs without forecast inputs")
    return [{key: evidence[eid].get(key, "") for key in ("id", "label", "display", "period", "unit", "basis", "note", "observed_at")} for eid in selected[:3]]


def validate_metadata(data):
    metadata = data.get("library")
    if metadata is None:
        return []
    try:
        if not isinstance(metadata, dict) or not str(metadata.get("category", "")).strip():
            raise ValueError("library.category must identify the company's primary business category")
        if metadata.get("company_id") is not None and not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,99}", metadata["company_id"]):
            raise ValueError("library.company_id must be a stable lowercase identifier")
        refs = metadata.get("category_evidence_ids", [])
        ids = {item["id"] for item in data["evidence"]}
        if not isinstance(refs, list) or any(key not in ids for key in refs):
            raise ValueError("library category has an unknown evidence reference")
        if not data["demo"] and not refs:
            raise ValueError("A real company's business category needs evidence references")
        card_metrics(data)
        logo = metadata.get("logo")
        if logo:
            if not isinstance(logo, dict) or not logo.get("file") or logo.get("source_id") not in {s["id"] for s in data["sources"]}:
                raise ValueError("library.logo needs a local file and its original source_id")
        return []
    except (ValueError, KeyError, TypeError) as error:
        return [str(error)]


def logo_data(data, ledger):
    logo = data.get("library", {}).get("logo")
    if not logo:
        return ""
    path = (ledger.parent / logo["file"]).resolve()
    raw = path.read_bytes()
    mime = ""
    if raw.startswith(b"\x89PNG\r\n\x1a\n"):
        mime = "image/png"
    elif raw.startswith(b"\xff\xd8\xff"):
        mime = "image/jpeg"
    elif raw.startswith(b"RIFF") and raw[8:12] == b"WEBP":
        mime = "image/webp"
    if not mime or len(raw) > 512_000:
        raise ValueError("Company logo must be a PNG, JPEG or WebP under 500 KB")
    return "data:" + mime + ";base64," + base64.b64encode(raw).decode("ascii")


def identity(data):
    company = data["company"]
    key = data.get("library", {}).get("company_id") or "|".join(company[field].strip().casefold() for field in ("exchange", "ticker", "share_class"))
    return ("demo:" if data["demo"] else "company:") + key


def record(data, ledger, relative):
    meta, company, report = data.get("library", {}), data["company"], data["report"]
    return {
        "id": identity(data), "name": company["name"], "ticker": company["ticker"],
        "exchange": company["exchange"], "industry": company["industry"],
        "category": meta.get("category", company["industry"]).strip(),
        "category_evidence_ids": meta.get("category_evidence_ids", []),
        "updated_at": report["prepared_at"], "as_of": report["as_of"],
        "checked_at": report["freshness_checked_at"], "status": report["research_status"],
        "demo": data["demo"], "report": relative, "ledger": relative.replace("report.html", "research.json"),
        "metrics": card_metrics(data), "logo": logo_data(data, ledger), "history": [],
    }


def read_registry(root):
    file = root / "library.json"
    if not file.exists():
        return {"schema_version": 1, "companies": []}
    registry = json.loads(file.read_text(encoding="utf-8-sig"))
    if registry.get("schema_version") != 1 or not isinstance(registry.get("companies"), list):
        raise ValueError("Unrecognised library registry; existing data has been left intact")
    seen = set()
    for entry in registry["companies"]:
        if entry["id"] in seen:
            raise ValueError("Duplicate company identity in the library registry")
        seen.add(entry["id"])
        for version in [entry] + entry.get("history", []):
            for key in ("report", "ledger"):
                if not safe_path(root, version[key]).is_file():
                    raise ValueError("A registered report or ledger is missing: " + version[key])
    return registry


def publish(data, ledger, override=None):
    from report import render, validate
    errors = validate(data) + validate_metadata(data)
    if errors:
        raise ValueError("; ".join(errors))
    if not data["demo"] and not data.get("library"):
        raise ValueError("Add library.category, category_evidence_ids and two or three sourced stats before indexing a real report")
    root, ledger = library_root(override), Path(ledger)
    # The content hash makes unchanged re-renders idempotent; no old snapshot is overwritten.
    brand = logo_data(data, ledger)
    hash_data = json.loads(encode(data))
    if brand:
        hash_data['library']['logo']['file'] = '<embedded-logo>'
    fingerprint = hashlib.sha256((encode(hash_data) + brand).encode()).hexdigest()[:16]
    key = hashlib.sha256(identity(data).encode()).hexdigest()[:16]
    ticker = re.sub(r"[^a-z0-9]+", "-", data["company"]["ticker"].lower()).strip("-")[:30] or "company"
    snapshot = data["report"]["prepared_at"][:10] + "-" + fingerprint
    relative = f"reports/{ticker}-{key}/{snapshot}/report.html"
    incoming = record(data, ledger, relative)
    target = safe_path(root, relative)
    with locked(root):
        registry = read_registry(root)
        previous = next((item for item in registry["companies"] if item["id"] == incoming["id"]), None)
        versions = [] if previous is None else [previous] + previous.get("history", [])
        if any(item["report"] == relative for item in versions):
            atomic_write(root / "index.html", render_index(registry, settings_for(root)))
            return target, root / "index.html"
        # Generate everything before changing the visible registry.
        report_html = render(data, library_href=rel_link(root / "index.html", target.parent))
        if previous:
            history = [{field: item[field] for field in ("report", "ledger", "updated_at", "as_of")} for item in versions]
            if datetime.fromisoformat(incoming["updated_at"]) >= datetime.fromisoformat(previous["updated_at"]):
                incoming["history"] = sorted(history, key=lambda item: datetime.fromisoformat(item["updated_at"]), reverse=True)
                registry["companies"] = [incoming if item["id"] == incoming["id"] else item for item in registry["companies"]]
            else:
                previous["history"].append({field: incoming[field] for field in ("report", "ledger", "updated_at", "as_of")})
                previous["history"].sort(key=lambda item: datetime.fromisoformat(item["updated_at"]), reverse=True)
        else:
            registry["companies"].append(incoming)
        index_html = render_index(registry, settings_for(root))
        if target.exists():
            raise ValueError("An unregistered snapshot already exists; inspect it before retrying")
        atomic_write(target, report_html)
        # Bundle the logo beside the snapshot ledger so it can be re-rendered offline.
        archived = json.loads(encode(data))
        if brand:
            prefix, encoded = brand.split(',', 1)
            extension = {'data:image/png;base64': '.png', 'data:image/jpeg;base64': '.jpg', 'data:image/webp;base64': '.webp'}[prefix]
            logo_file = 'company-logo' + extension
            target.with_name(logo_file).write_bytes(base64.b64decode(encoded))
            archived['library']['logo']['file'] = logo_file
        atomic_write(target.with_name("research.json"), encode(archived))
        atomic_write(root / "library.json", encode(registry))
        atomic_write(root / "index.html", index_html)
    return target, root / "index.html"


def short_date(value, lang="en"):
    date = datetime.fromisoformat(value.replace("Z", "+00:00"))
    months = ("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec" if lang == "en" else "ian feb mar apr mai iun iul aug sep oct nov dec").split()
    return f"{date.day} {months[date.month - 1]} {date.year}"


def render_index(registry, settings=None):
    settings = settings or config()
    lang = settings.get("language", "en")
    ro = lang == "ro"
    tr = lambda en, romanian: romanian if ro else en
    entries = registry["companies"]
    categories = sorted({item["category"] for item in entries}, key=str.casefold)
    groups = defaultdict(list)
    for item in entries:
        groups[(item["demo"], item["category"])].append(item)
    arrow = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h14m-6-6 6 6-6 6"/></svg>'

    def card(item):
        href = quote(item["report"], safe="/.-_")
        logo = item.get("logo", "")
        if logo and not re.fullmatch(r"data:image/(?:png|jpeg|webp);base64,[A-Za-z0-9+/=]+", logo):
            raise ValueError("Unsafe embedded company logo")
        initials = "".join(word[0] for word in item["name"].split()[:2]).upper()
        mark = '<img src="' + logo + '" alt="' + esc(item["name"] + ' logo') + '" width="48" height="48">' if logo else '<span class="monogram" role="img" aria-label="' + esc(tr('Company initials; logo unavailable', 'Inițialele companiei; sigla indisponibilă')) + '">' + esc(initials) + '</span>'
        metrics = []
        for metric in item["metrics"]:
            tip = " · ".join(str(metric.get(key, "")) for key in ("label", "period", "unit", "basis") if metric.get(key))
            tip += "\n" + metric.get("note", "")
            metrics.append('<div class="card-stat"><dt>' + esc(metric["label"]) + '</dt><dd><a href="' + href + '#ev-' + esc(metric["id"]) + '" title="' + esc(tip) + '" aria-label="' + esc(metric["label"] + ': ' + metric['display'] + ' · ' + tr('View evidence', 'Vezi dovezile')) + '">' + esc(metric["display"]) + '<span aria-hidden="true">↗</span></a><small>' + esc(metric.get("observed_at") and short_date(metric["observed_at"], lang) or metric["period"]) + '</small></dd></div>')
        status = tr("Sample report", "Exemplu fictiv") if item["demo"] else (tr("Partial research", "Documentare parțială") if item["status"] == "partial" else tr("Research report", "Analiză documentată"))
        history = ''
        if item.get("history"):
            history = '<details class="versions"><summary>' + esc(tr('Previous reports', 'Analize anterioare')) + ' · ' + str(len(item["history"])) + '</summary><ul>' + ''.join('<li><a href="' + quote(old["report"], safe="/.-_") + '">' + esc(short_date(old["updated_at"], lang)) + ' · ' + esc(old["updated_at"].split('T')[-1]) + '</a></li>' for old in item['history']) + '</ul></details>'
        return '<article class="company-card" data-name="' + esc(' '.join([item["name"], item["ticker"], item["industry"], item["category"]]).casefold()) + '" data-date="' + esc(item["updated_at"]) + '" data-company="' + esc(item["name"]) + '"><div class="card-top"><div class="brand-mark">' + mark + '</div><span class="card-status' + (' partial' if item['status'] == 'partial' and not item['demo'] else '') + '">' + esc(status) + '</span></div><a class="company-title" href="' + href + '"><h3>' + esc(item["name"]) + '</h3><span>' + esc(item["ticker"]) + ' <i>·</i> ' + esc(item["industry"]) + '</span></a><dl class="card-metrics">' + (''.join(metrics) or '<p>' + tr('Metrics unavailable; see report gaps.', 'Indicatori indisponibili; consultați analiza.') + '</p>') + '</dl><footer class="card-footer"><div><span>' + tr('Updated', 'Actualizat') + '</span><time datetime="' + esc(item["updated_at"]) + '" title="' + esc(item["updated_at"]) + '">' + esc(short_date(item["updated_at"], lang)) + '</time><small>' + tr('Data as of ', 'Date la ') + esc(short_date(item['as_of'], lang)) + '</small></div><a class="open-report" href="' + href + '" aria-label="' + esc(tr('Open report for ', 'Deschide analiza pentru ') + item["name"]) + '">' + arrow + '</a></footer>' + history + '</article>'

    clusters = []
    for index, ((demo, category), items) in enumerate(sorted(groups.items(), key=lambda pair: (pair[0][0], pair[0][1].casefold()))):
        items.sort(key=lambda item: item["name"].casefold())
        clusters.append('<section class="cluster tone-' + str(index % 3) + '" data-category="' + esc(category) + '" aria-labelledby="cluster-' + str(index) + '"><header class="cluster-heading"><span class="cluster-symbol" aria-hidden="true">' + ['✳', '◈', '✺'][index % 3] + '</span><div><p class="cluster-kicker">' + esc(tr('Sample collection', 'Colecție de exemple') if demo else tr('Business category', 'Categorie de activitate')) + '</p><h2 id="cluster-' + str(index) + '">' + esc(category) + '</h2></div><span class="cluster-count">' + str(len(items)) + '</span></header><div class="cluster-cards">' + ''.join(card(item) for item in items) + '</div></section>')
    count = len(entries)
    live = sum(not item["demo"] for item in entries)
    label = tr('companies', 'companii') if count != 1 else tr('company', 'companie')
    category_label = tr('business categories', 'categorii de activitate') if len(categories) != 1 else tr('business category', 'categorie de activitate')
    demo_note = '<p class="demo-note">' + tr('Design samples use fictional companies and figures. Real research appears in its own category clusters.', 'Exemplele folosesc companii și cifre fictive. Analizele reale apar în grupuri separate.') + '</p>' if any(item['demo'] for item in entries) else ''
    gallery = '<a class="gallery-link" href="design-preview/index.html">' + tr('See a fuller sample collection', 'Vezi o colecție de exemple') + ' ↗</a>' if settings.get('gallery') else ''
    if settings.get('parent_href'):
        gallery += '<a class="gallery-link" href="' + esc(settings['parent_href']) + '">← ' + tr('Back to your collection', 'Înapoi la colecția ta') + '</a>'
    options = ''.join('<option value="' + esc(category) + '">' + esc(category) + '</option>' for category in categories)
    empty = '<div class="empty-state"><span aria-hidden="true">✳</span><h2>' + tr('A place for your next discovery.', 'Un loc pentru următoarea descoperire.') + '</h2><p>' + tr('Your company reports will gather here, grouped by the businesses behind them.', 'Analizele companiilor se vor aduna aici, grupate după activitatea lor.') + '</p></div>' if not entries else ''
    css = (ROOT / 'assets/library.css').read_text(encoding='utf-8')
    js = (ROOT / 'assets/library.js').read_text(encoding='utf-8')
    title = settings.get('title', 'The company collection')
    return '<!doctype html><html lang="' + lang + '"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="referrer" content="no-referrer"><meta name="description" content="A personal library of sourced company research, grouped by business category."><title>' + esc(title) + '</title><style>' + css + '</style></head><body><a class="skip-link" href="#collection">' + tr('Skip to companies', 'Salt la companii') + '</a><div class="page-shell"><div class="library-intro"><div><p class="eyebrow">' + tr('The research library', 'Biblioteca de analize') + '</p><h1>' + esc(title) + '<span class="heading-dot">.</span></h1></div><div class="collection-tally"><span>' + str(count).zfill(2) + '</span><div>' + esc(label) + '<br><small>' + str(len(categories)) + ' ' + esc(category_label) + '</small></div></div></div>' + demo_note + gallery + '<div class="toolbar" hidden><label class="search-field"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="10.8" cy="10.8" r="6.8"/><path d="m16 16 5 5"/></svg><input id="company-search" type="search" placeholder="' + tr('Find a company or ticker', 'Caută o companie sau un simbol') + '" aria-label="' + tr('Find a company or ticker', 'Caută o companie sau un simbol') + '"></label><label class="select-field"><span>' + tr('Category', 'Categorie') + '</span><select id="category-filter"><option value="">' + tr('All businesses', 'Toate activitățile') + '</option>' + options + '</select></label><label class="select-field"><span>' + tr('Sort by', 'Sortează după') + '</span><select id="sort-order"><option value="name">' + tr('Company name', 'Nume') + '</option><option value="updated">' + tr('Recently updated', 'Actualizare recentă') + '</option></select></label></div><div class="collection-meta"><p id="result-count" role="status" aria-live="polite" data-label="' + esc(tr('companies shown', 'companii afișate')) + '">' + str(count) + ' ' + esc(label) + '</p><p>' + tr('Figures are dated snapshots · select a stat to see its source', 'Cifrele sunt istorice · selectează un indicator pentru sursă') + '</p></div><main id="collection"><div class="cluster-grid">' + ''.join(clusters) + '</div>' + empty + '<div id="no-results" class="empty-state" hidden><h2>' + tr('No companies found.', 'Nicio companie găsită.') + '</h2><p>' + tr('Try a different name, ticker, or business category.', 'Încearcă alt nume, simbol sau categorie.') + '</p><button id="reset-filters" type="button">' + tr('Clear filters', 'Resetează filtrele') + '</button></div></main><footer class="library-footer"><span>' + tr('A little curiosity. A clear trail of evidence.', 'Puțină curiozitate. Dovezi ușor de urmărit.') + '</span><span>' + str(live) + ' ' + tr('researched companies', 'companii analizate') + '</span></footer></div><script>' + js + '</script></body></html>'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('add', 'rebuild'))
    parser.add_argument('input', nargs='?', type=Path)
    parser.add_argument('--library', type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'add':
            if not args.input:
                parser.error('add needs research.json')
            data = json.loads(args.input.read_text(encoding='utf-8-sig'))
            report, index = publish(data, args.input, args.library)
            print('Report: ' + str(report))
        else:
            root = library_root(args.library)
            with locked(root):
                atomic_write(root / 'index.html', render_index(read_registry(root), settings_for(root)))
            index = root / 'index.html'
        print('Library: ' + str(index))
        return 0
    except (OSError, ValueError, TypeError, KeyError) as error:
        print('Library update failed: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
