#!/usr/bin/env python3
"""Validate a research ledger and render a standalone, traceable HTML report."""
import argparse
import html
import json
import re
import sys
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
STATUSES = {
    "en": {"meets": "Meets", "mixed": "Mixed", "does_not_meet": "Does not meet", "insufficient_evidence": "Insufficient evidence", "not_applicable": "Not applicable"},
    "ro": {"meets": "Îndeplinit", "mixed": "Mixt", "does_not_meet": "Neîndeplinit", "insufficient_evidence": "Dovezi insuficiente", "not_applicable": "Nu se aplică"},
}
LABELS = {
    "en": {"report": "Company research", "summary": "The investment case", "checklist": "Checklist assessment", "peers": "Peer comparison", "scenarios": "Valuation scenarios", "monitor": "What would change the thesis", "gaps": "Open questions & data gaps", "optional": "Market context · optional", "evidence": "Evidence & calculations", "sources": "Original sources", "log": "Research & freshness checks", "close": "Close", "source": "Evidence", "period": "Period", "basis": "Basis", "unit": "Unit", "kind": "Type", "inputs": "Inputs", "formula": "Calculation", "published": "Published", "accessed": "Accessed", "location": "Location", "asof": "Information as of", "financials": "Latest financial period", "prepared": "Prepared", "checked": "Final freshness check", "coverage": "Core items with an assessment", "coverage_note": "Coverage measures the assessment, not investment quality. Items without sufficient evidence are excluded.", "demo": "DESIGN PREVIEW · Synthetic figures and conclusions. No company research has been performed.", "partial": "PARTIAL RESEARCH · See unresolved evidence and limitations before relying on conclusions.", "data": "Underlying data", "assumptions": "Assumptions", "results": "Scenario results", "reason": "Why this peer", "quote": "Observed share price", "judgment": "Analytical judgment", "reported": "Reported", "calculated": "Calculated", "estimate": "External estimate", "assumption": "Model assumption", "unavailable": "Unavailable", "point": "Observation", "series": "Series", "value": "Value", "skip": "Skip to report", "quote_at": "Quote timestamp", "quote_session": "Market session", "chart_hint": "Swipe the chart, or open the data below."},
    "ro": {"report": "Analiză de companie", "summary": "Cazul de investiție", "checklist": "Evaluarea criteriilor", "peers": "Comparație cu concurenții", "scenarios": "Scenarii de evaluare", "monitor": "Ce ar schimba teza", "gaps": "Întrebări deschise și date lipsă", "optional": "Context de piață · opțional", "evidence": "Dovezi și calcule", "sources": "Surse originale", "log": "Documentare și actualizare", "close": "Închide", "source": "Dovezi", "period": "Perioadă", "basis": "Bază contabilă", "unit": "Unitate", "kind": "Tip", "inputs": "Date de intrare", "formula": "Calcul", "published": "Publicat", "accessed": "Accesat", "location": "Localizare", "asof": "Informații disponibile la", "financials": "Ultima perioadă financiară", "prepared": "Întocmit", "checked": "Verificare finală", "coverage": "Criterii de bază cu evaluare", "coverage_note": "Acoperirea măsoară evaluarea, nu calitatea investiției. Criteriile fără dovezi suficiente sunt excluse.", "demo": "PREVIZUALIZARE · Cifre și concluzii fictive. Nu a fost efectuată o analiză reală.", "partial": "DOCUMENTARE PARȚIALĂ · Consultați datele lipsă și limitările înainte de a folosi concluziile.", "data": "Datele graficului", "assumptions": "Ipoteze", "results": "Rezultatele scenariului", "reason": "Motivul comparației", "quote": "Prețul observat al acțiunii", "judgment": "Interpretare analitică", "reported": "Raportat", "calculated": "Calculat", "estimate": "Estimare externă", "assumption": "Ipoteză de model", "unavailable": "Indisponibil", "point": "Observație", "series": "Serie", "value": "Valoare", "skip": "Salt la raport", "quote_at": "Data și ora cotației", "quote_session": "Sesiune de piață", "chart_hint": "Glisați graficul sau deschideți datele de mai jos."},
}


def esc(value):
    return html.escape(str(value), quote=True)


def stamp(value, full=False):
    if not isinstance(value, str):
        raise ValueError("Expected ISO date or timestamp")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if full and ("T" not in value or result.tzinfo is None):
        raise ValueError("Timestamp needs time and UTC offset: " + value)
    return result.replace(tzinfo=timezone.utc) if result.tzinfo is None else result


def num(value):
    if isinstance(value, bool) or value is None:
        raise ValueError("Missing or boolean numeric input")
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError("Numeric values must be finite")
    return result


def display_date(value, lang="en"):
    if not value:
        return ""
    try:
        dt = stamp(value)
    except (ValueError, TypeError):
        return str(value)
    months = ("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec" if lang == "en" else "ian feb mar apr mai iun iul aug sep oct nov dec").split()
    result = f"{dt.day:02d} {months[dt.month - 1]} {dt.year}"
    if "T" in value:
        offset = dt.strftime("%z")
        result += f", {dt:%H:%M} · UTC{offset[:3]}:{offset[3:]}"
    return result


def calculate(operation, values, years=None):
    vals = [num(v) for v in values]
    if not vals:
        raise ValueError("Calculation needs inputs")
    if operation == "sum":
        return sum(vals, Decimal(0))
    if operation == "difference" and len(vals) >= 2:
        return vals[0] - sum(vals[1:], Decimal(0))
    if operation == "product":
        out = Decimal(1)
        for v in vals:
            out *= v
        return out
    if operation == "average":
        return sum(vals, Decimal(0)) / len(vals)
    if operation in ("ratio", "percent") and len(vals) == 2:
        if vals[1] <= 0:
            raise ValueError("Ratio denominator must be positive; use unavailable with an explanation")
        return vals[0] / vals[1] * (100 if operation == "percent" else 1)
    if operation == "cagr" and len(vals) == 2:
        if min(vals) <= 0 or isinstance(years, bool) or not isinstance(years, int) or years <= 0:
            raise ValueError("CAGR requires positive endpoints and positive integer years")
        return ((vals[1] / vals[0]) ** (Decimal(1) / years) - 1) * 100
    if operation == "ttm" and len(vals) == 3:
        return vals[0] + vals[1] - vals[2]
    raise ValueError("Unknown operation or wrong input count: " + str(operation))


def validate(data):
    if not isinstance(data, dict):
        return ["Report root must be an object"]
    errors = []

    def require(condition, message):
        if not condition:
            errors.append(message)

    def valid_date(value, label, full=False):
        try:
            return stamp(value, full)
        except (ValueError, TypeError):
            errors.append(label + ": invalid date/timestamp")
            return None

    require(data.get("schema_version") == 1, "schema_version must be 1")
    require(isinstance(data.get("demo"), bool), "demo must explicitly be true or false")
    company, report = data.get("company", {}), data.get("report", {})
    for key in ("name", "ticker", "exchange", "share_class", "currency", "industry"):
        require(bool(company.get(key)), "company missing " + key)
    require(report.get("language") in LABELS, "report.language must be en or ro")
    require(report.get("research_status") in ("complete", "partial"), "Invalid research_status")
    for key in ("financial_period", "horizon", "subtitle"):
        require(bool(report.get(key)), "report missing " + key)
    cutoff = valid_date(report.get("as_of"), "as_of", True)
    prepared = valid_date(report.get("prepared_at"), "prepared_at", True)
    checked = valid_date(report.get("freshness_checked_at"), "freshness_checked_at", True)
    if prepared and cutoff:
        require(cutoff <= prepared, "as_of must not be after prepared_at")
    if checked and prepared:
        require(checked <= prepared, "freshness check must not be after prepared_at")
    sources, evidence = {}, {}
    for entries, target, label in ((data.get("sources", []), sources, "source"), (data.get("evidence", []), evidence, "evidence")):
        for item in entries:
            item_id = item.get("id", "")
            require(bool(re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", item_id)), "Invalid " + label + " ID")
            require(item_id not in target, "Duplicate " + label + " ID: " + item_id)
            target[item_id] = item
    require(bool(evidence), "Evidence ledger is empty")
    for key, source in sources.items():
        for field in ("title", "publisher", "locator", "source_type"):
            require(bool(source.get(field)), key + " missing " + field)
        url = source.get("url")
        if url:
            parsed = urlparse(url)
            require(parsed.scheme in ("http", "https") and bool(parsed.netloc), key + " unsafe/invalid source URL")
        else:
            require(bool(source.get("file")) or data.get("demo"), key + " needs a URL or local file")
        require(source.get("verification") in (("demo",) if data.get("demo") else ("opened", "user_provided")), key + " invalid verification type")
        accessed = valid_date(source.get("accessed_at"), key + " accessed_at", True)
        if accessed and prepared:
            require(accessed <= prepared, key + " accessed after preparation")
        if source.get("published_at"):
            published = valid_date(source["published_at"], key + " published_at")
            if published and cutoff:
                require(published <= cutoff, key + " was published after the information cutoff")
            if published and accessed:
                require(published <= accessed, key + " was accessed before publication")
        else:
            require(bool(source.get("date_note")), key + " needs publication date or date_note")
    kinds = ("reported", "calculated", "estimate", "assumption", "judgment", "unavailable")
    for key, item in evidence.items():
        for field in ("label", "display", "unit", "period", "basis", "note"):
            require(bool(item.get(field)), key + " missing " + field)
        require(item.get("kind") in kinds, key + " invalid kind")
        for sid in item.get("source_ids", []):
            require(sid in sources, key + " missing source " + sid)
        for eid in item.get("evidence_ids", []):
            require(eid in evidence, key + " missing supporting evidence " + eid)
        kind = item.get("kind")
        if kind in ("reported", "estimate"):
            require(bool(item.get("source_ids")), key + " reported/estimate needs original sources")
        if kind == "judgment":
            require(bool(item.get("source_ids") or item.get("evidence_ids")), key + " judgment needs supporting evidence")
        if kind == "unavailable":
            require(item.get("raw_value") is None and not item.get("calculation"), key + " unavailable cannot contain numeric results")
        if kind != "calculated":
            require(not item.get("calculation"), key + " calculation must be labelled calculated")
        if item.get("raw_value") is not None:
            try:
                num(item["raw_value"])
            except (ValueError, InvalidOperation):
                errors.append(key + " invalid numeric raw_value")
        if item.get("observed_at"):
            observation = valid_date(item["observed_at"], key + " observed_at", True)
            if observation and cutoff:
                require(observation <= cutoff, key + " observation after cutoff")

    visiting, completed = set(), set()

    def check_calculation(key):
        if key in visiting:
            raise ValueError("Cyclic evidence lineage: " + key)
        if key in completed:
            return
        visiting.add(key)
        item = evidence[key]
        for dependency in item.get("evidence_ids", []):
            if dependency in evidence:
                check_calculation(dependency)
        if item.get("kind") == "calculated":
            calc = item.get("calculation", {})
            require(bool(calc.get("formula")), key + " missing human-readable formula")
            inputs = calc.get("inputs", [])
            vals = []
            for eid in inputs:
                if eid not in evidence:
                    raise ValueError(key + " missing calculation input " + eid)
                check_calculation(eid)
                vals.append(evidence[eid].get("raw_value"))
            result = calculate(calc.get("operation"), vals, calc.get("years"))
            actual = num(item.get("raw_value"))
            require(abs(result - actual) <= max(Decimal("1e-8"), abs(result) * Decimal("1e-8")), key + " calculation does not match stored raw_value")
        visiting.remove(key)
        completed.add(key)

    for eid in evidence:
        try:
            check_calculation(eid)
        except (ValueError, InvalidOperation, KeyError, TypeError) as error:
            errors.append(str(error))
            visiting.clear()

    def references(ids, label):
        for eid in ids:
            require(eid in evidence, label + " missing evidence " + eid)

    def clause(obj, label):
        require(isinstance(obj, dict) and bool(obj.get("text")), label + " needs text")
        if isinstance(obj, dict):
            references(obj.get("evidence_ids", []), label)

    mapping = json.loads((ROOT / "references/checklist.json").read_text(encoding="utf-8"))
    expected_sections = {s["id"]: s for s in mapping["sections"]}
    sections = data.get("sections", [])
    require(len(sections) == len(expected_sections), "Need preparation plus all 14 sections")
    require({s.get("id") for s in sections} == set(expected_sections), "Section IDs must be 0 through 14 exactly once")

    def check_item(item, label):
        if item.get("finding"):
            clause(item["finding"], label + " finding")
        if item.get("related_section") is not None:
            require(str(item["related_section"]) in expected_sections, label + " invalid related section")
        require(item.get("status") in STATUSES["en"], label + " invalid status")
        require(bool(item.get("explanation")), label + " needs an explanation")
        references(item.get("evidence_ids", []), label)
        if item.get("status") in ("meets", "mixed", "does_not_meet"):
            require(bool(item.get("evidence_ids")), label + " assessed item needs evidence")
            def observed_support(eid, seen=None):
                seen = set() if seen is None else seen
                if eid in seen:
                    return False
                seen.add(eid)
                record = evidence.get(eid, {})
                if record.get("kind") in ("reported", "estimate"):
                    return bool(record.get("source_ids"))
                if record.get("kind") in ("unavailable", "assumption", None):
                    return False
                if record.get("source_ids"):
                    return True
                dependencies = record.get("evidence_ids", []) + record.get("calculation", {}).get("inputs", [])
                return any(observed_support(dep, seen.copy()) for dep in dependencies)
            require(any(observed_support(eid) for eid in item.get("evidence_ids", [])), label + " cannot be assessed using only missing data or assumptions")

    for section in sections:
        if section.get("id") not in expected_sections:
            continue
        expected = {c["id"] for c in expected_sections[section["id"]]["checks"]}
        items = section.get("checks", [])
        require(len(items) == len(expected) and {c.get("id") for c in items} == expected, "Missing or duplicate checklist subitems in section " + section["id"])
        clause(section.get("intro", {}), "section " + section["id"])
        references(section.get("metrics", []), "section metrics")
        for item in items:
            check_item(item, item.get("id", "check"))
    optional = data.get("optional", [])
    require(len(optional) == 6 and {o.get("id") for o in optional} == {o["id"] for o in mapping["optional"]}, "Need all six optional indicators, with omissions explained")
    for item in optional:
        check_item(item, item.get("id", "optional"))
    for field in ("summary", "monitoring", "gaps"):
        require(bool(data.get(field)), "Need " + field + " (state none identified if appropriate)")
        for obj in data.get(field, []):
            clause(obj, field)
    references(data.get("highlights", []), "highlights")
    quote_id = report.get("quote_evidence_id")
    require(quote_id in evidence, "Need a quote evidence ID, or an unavailable quote record")
    quote = evidence.get(quote_id, {})
    if quote and quote.get("kind") != "unavailable":
        require(bool(quote.get("observed_at")) and bool(quote.get("session")), "Available quote needs observed_at and session")
    for peer in data.get("peers", []):
        require(bool(peer.get("name")), "Peer needs name")
        clause(peer.get("rationale", {}), "peer rationale")
        clause(peer.get("assessment", {}), "peer assessment")
        references(peer.get("metrics", []), "peer metrics")
    require(bool(data.get("peers")) or bool(data.get("peer_note")), "Need peers or explanation of missing peers")
    comparison = data.get("peer_table")
    if comparison:
        require(bool(comparison.get("columns")) and bool(comparison.get("rows")), "Peer table needs columns and rows")
        for row in comparison.get("rows", []):
            require(bool(row.get("label")), "Peer row needs a label")
            require(len(row.get("cells", [])) == len(comparison["columns"]), "Peer table cell count differs from columns")
            for cell in row.get("cells", []): clause(cell, "peer comparison cell")
    scenarios = data.get("scenarios", [])
    require(len(scenarios) == 3 and {s.get("key") for s in scenarios} == {"bear", "base", "bull"}, "Need bear/base/bull scenarios, even if results are unavailable")
    for scenario in scenarios:
        require(bool(scenario.get("name")), "Scenario needs name")
        references(scenario.get("assumptions", []), "scenario assumptions")
        references(scenario.get("results", []), "scenario results")
        require(bool(scenario.get("results")), "Scenario needs a result or unavailable evidence record")
        clause(scenario.get("commentary", {}), "scenario commentary")
    for chart in data.get("charts", []):
        if chart.get("section_id") is not None:
            require(str(chart["section_id"]) in expected_sections, "Chart has invalid section_id")
        require(bool(chart.get("title")) and bool(chart.get("unit")), "Chart needs title and unit")
        reference_labels = None
        for series in chart.get("series", []):
            require(bool(series.get("name")), "Chart series needs name")
            labels = [p.get("label") for p in series.get("points", [])]
            require(bool(labels) and all(labels), "Chart needs labelled observations")
            require(len(labels) == len(set(labels)), "Chart labels must be unique")
            if reference_labels is None:
                reference_labels = labels
            else:
                require(labels == reference_labels, "Chart series must share identical time labels")
            for point in series.get("points", []):
                eid = point.get("evidence_id")
                references([eid], "chart")
                require(evidence.get(eid, {}).get("raw_value") is not None, "Chart points need numeric evidence")
                require(evidence.get(eid, {}).get("unit") == chart.get("unit"), "Chart point units differ from chart unit")
    logs = data.get("research_log", [])
    require(bool(logs), "Need research_log")
    for log in logs:
        require(bool(log.get("topic")) and bool(log.get("result")), "Research log needs topic and result")
        log_date = valid_date(log.get("checked_at"), "research log checked_at", True)
        if log_date and prepared:
            require(log_date <= prepared, "Research log is dated after preparation")
        for sid in log.get("source_ids", []):
            require(sid in sources, "Research log missing source " + sid)
    if not data.get("demo"):
        require({"filings", "results", "material_events", "quote", "ownership", "estimates"}.issubset({x.get("topic") for x in logs}), "Real report needs freshness logs for filings/results/material_events/quote/ownership/estimates")
    if data.get('translations'):
        from localization import localized
        for language in data['translations']:
            try:
                if language not in ('en','ro'):raise ValueError('Only en/ro translations are supported')
                localized(data,language)
            except (ValueError,KeyError,TypeError) as error:errors.append(str(error))
    from audience import validate_audience
    errors.extend(validate_audience(data))
    return list(dict.fromkeys(errors))


def _render_single(data, library_href=None):
    lang = data["report"]["language"]
    visual_labels = {
        "en": {"map": "The checklist at a glance", "map_note": "Each dot represents one checklist item. Select a topic to inspect the evidence.", "reasoning": "Evidence & reasoning", "criteria": "items", "open_all": "Expand all reasoning", "close_all": "Collapse reasoning", "history": "View history and sources", "scenario_detail": "Assumptions & full analysis", "scenario_note": "A common scale for the scenarios below. These are modelled outcomes, not probabilities.", "flow": "How the numbers connect", "analysis": "The full analysis", "coverage_short": "Research coverage", "part": "share of", "jump": "Jump to"},
        "ro": {"map": "Criteriile, dintr-o privire", "map_note": "Fiecare punct reprezintă un criteriu. Selectați un subiect pentru a consulta dovezile.", "reasoning": "Dovezi și raționament", "criteria": "criterii", "open_all": "Extinde toate explicațiile", "close_all": "Restrânge explicațiile", "history": "Vezi istoricul și sursele", "scenario_detail": "Ipoteze și analiza completă", "scenario_note": "O scară comună pentru scenariile de mai jos. Acestea sunt rezultate modelate, nu probabilități.", "flow": "Cum se leagă cifrele", "analysis": "Analiza completă", "coverage_short": "Acoperirea documentării", "part": "din", "jump": "Salt la"},
    }
    tr, statuses = {**LABELS[lang], **visual_labels[lang]}, STATUSES[lang]
    records = {e["id"]: e for e in data["evidence"]}
    sources = {s["id"]: s for s in data["sources"]}
    mapping = json.loads((ROOT / "references/checklist.json").read_text(encoding="utf-8"))
    section_map = {s["id"]: s for s in mapping["sections"]}
    check_map = {c["id"]: c for s in mapping["sections"] for c in s["checks"]}
    check_map.update({c["id"]: c for c in mapping["optional"]})
    numbering = {eid: str(i + 1).zfill(2) for i, eid in enumerate(records)}

    def ref(eid):
        item = records[eid]
        description = [item["label"] + ": " + item["display"], tr[item["kind"]] + " · " + item["period"], item["basis"]]
        if item.get("calculation"):
            description.append(item["calculation"]["formula"])
        for sid in item.get("source_ids", []):
            source = sources[sid]
            description.append(source["publisher"] + " · " + source["title"] + " · " + source["locator"])
            description.append(tr["published"] + ": " + (display_date(source.get("published_at"), lang) or source.get("date_note", "")))
        description.append(item["note"])
        return '<a class="ev-ref" href="#ev-' + esc(eid) + '" data-evidence="' + esc(eid) + '" data-preview="' + esc("\n".join(description)) + '" aria-label="' + esc(tr["source"] + " " + numbering[eid] + ": " + item["label"]) + '">[' + numbering[eid] + ']</a>'

    def refs(ids):
        return ' <span class="refs">' + " ".join(ref(i) for i in ids) + "</span>" if ids else ""

    def clause(obj):
        label = '<strong>' + esc(obj["label"]) + '</strong> ' if obj.get("label") else ""
        return '<p>' + label + esc(obj["text"]) + refs(obj.get("evidence_ids", [])) + '</p>'

    from audience import Presentation
    audience = Presentation(data, lang, clause, refs)

    def sparkline(eid):
        for chart_index, chart in enumerate(data.get("charts", [])):
            for series in chart.get("series", []):
                pts = series.get("points", [])
                if len(pts) < 2 or pts[-1]["evidence_id"] != eid:
                    continue
                values = [float(records[p["evidence_id"]]["raw_value"]) for p in pts]
                low, high = min(values), max(values)
                extent = high - low or 1
                coords = [(4 + i * 100 / (len(values) - 1), 32 - (v - low) * 26 / extent) for i, v in enumerate(values)]
                path = " ".join(f"{x:.2f},{y:.2f}" for x, y in coords)
                label = tr["history"] + ": " + series["name"] + ", " + pts[0]["label"] + "–" + pts[-1]["label"]
                return '<a class="sparkline" href="#chart-' + str(chart_index) + '" aria-label="' + esc(label) + '" title="' + esc(label) + '"><svg viewBox="0 0 110 38" aria-hidden="true"><polyline points="' + path + '"/><circle cx="' + f'{coords[-1][0]:.2f}' + '" cy="' + f'{coords[-1][1]:.2f}' + '" r="3"/></svg></a>'
        return ""

    def metric(eid):
        item = records[eid]
        teaching = audience.guide.get('metrics', {}).get(eid) if audience.guide else None
        metric_label = audience.pair(esc(teaching['label']), esc(item['label']), True) if teaching else esc(item['label'])
        teaching_html = audience.pair('<p class="metric-teaching">' + esc(teaching['text']) + '</p>', '') if teaching else ''
        return '<div class="metric"><span class="metric-label">' + metric_label + '</span><div class="metric-reading"><span class="metric-value">' + esc(item["display"]) + refs([eid]) + '</span>' + sparkline(eid) + '</div><small>' + esc(item["period"] + " · " + tr[item["kind"]]) + '</small>' + teaching_html + '</div>'

    def flow_diagrams(metric_ids):
        diagrams, seen = [], set()
        for eid in metric_ids:
            parent = records[eid]
            calc = parent.get("calculation", {})
            if calc.get("operation") not in ("percent", "ratio") or not calc.get("inputs"):
                continue
            remainder_id = calc["inputs"][0]
            remainder = records[remainder_id]
            diff = remainder.get("calculation", {})
            if diff.get("operation") != "difference" or len(diff.get("inputs", [])) != 2 or remainder_id in seen:
                continue
            total_id, deduction_id = diff["inputs"]
            total_item, deduction = records[total_id], records[deduction_id]
            items = (total_item, deduction, remainder)
            if len({i["unit"] for i in items}) != 1 or len({i["period"] for i in items}) != 1:
                continue
            if any(i.get("raw_value") is None for i in items):
                continue
            whole, used, left = [num(i["raw_value"]) for i in items]
            if whole <= 0 or min(used, left) < 0 or abs(whole - used - left) > Decimal("1e-8"):
                continue
            seen.add(remainder_id)
            proportion = float(used / whole * 100)
            label = total_item["label"] + ": " + total_item["display"] + "; " + deduction["label"] + ": " + deduction["display"] + "; " + remainder["label"] + ": " + remainder["display"]
            diagrams.append('<figure class="flow-diagram"><figcaption><span>' + esc(total_item["label"]) + '</span><strong>' + esc(total_item["display"]) + refs([total_id]) + '</strong></figcaption><div class="flow-track" role="img" aria-label="' + esc(label) + '"><span class="flow-used" style="width:' + f'{proportion:.8f}' + '%"></span><span class="flow-left" style="width:' + f'{100-proportion:.8f}' + '%"></span></div><div class="flow-legend"><div><span class="flow-dot used"></span><span>' + esc(deduction["label"]) + '<strong>' + esc(deduction["display"]) + refs([deduction_id]) + '</strong></span></div><div><span class="flow-dot left"></span><span>' + esc(remainder["label"]) + '<strong>' + esc(remainder["display"]) + refs([remainder_id]) + '</strong></span></div></div><small>' + esc(total_item["period"] + " · " + total_item["unit"]) + '</small></figure>')
        return '<div class="flow-heading">' + esc(tr["flow"]) + '</div><div class="flow-grid">' + "".join(diagrams) + '</div>' if diagrams else ""

    def checks(items):
        rows = []
        for item in items:
            label = check_map[item["id"]][lang]
            finding = item.get("finding")
            body = clause(finding) if finding else '<p>' + esc(item["explanation"]) + refs(item.get("evidence_ids", [])) + '</p>'
            if item.get("related_section") is not None:
                body += '<a class="section-reference" href="#section-' + esc(item['related_section']) + '">' + ('See section ' if lang == 'en' else 'Vezi secțiunea ') + esc(item['related_section']) + '</a>'
            if finding:
                body += '<details class="analysis-detail check-detail"><summary>' + ('Full reasoning and evidence' if lang == 'en' else 'Raționament și dovezi complete') + '</summary><p>' + esc(item["explanation"]) + refs(item.get("evidence_ids", [])) + '</p></details>'
            if audience.guide:
                teaching = audience.guide['checks'][item['id']]
                body = audience.pair(clause({**teaching, 'label': ''}), body)
                label_html = audience.pair(esc(teaching['label']), esc(label), True)
            else: label_html = esc(label)
            rows.append('<li class="check"><div class="check-top"><strong>' + label_html + '</strong><span class="status ' + item["status"] + '">' + esc(statuses[item["status"]]) + '</span></div>' + body + '</li>')
        return '<ul class="checks">' + "".join(rows) + '</ul>'

    def block(title, body, anchor):
        return '<section class="report-section" id="' + esc(anchor) + '"><h2>' + esc(title) + '</h2>' + body + '</section>'

    def status_dots(items):
        return '<span class="status-dots">' + "".join('<span class="status-dot ' + c["status"] + '" role="img" aria-label="' + esc(check_map[c["id"]][lang] + ": " + statuses[c["status"]]) + '" title="' + esc(check_map[c["id"]][lang] + ": " + statuses[c["status"]]) + '"></span>' for c in items) + '</span>'

    report, company = data["report"], data["company"]
    assessed = sum(c["status"] != "insufficient_evidence" for s in data["sections"] if s["id"] != "0" for c in s["checks"])
    total = sum(len(s["checks"]) for s in data["sections"] if s["id"] != "0")
    banner = '<div class="notice demo">' + esc(tr["demo"]) + '</div>' if data["demo"] else ""
    if report["research_status"] == "partial":
        banner += '<div class="notice">' + esc(tr["partial"]) + '</div>'
    metadata = "".join('<div><dt>' + esc(tr[label]) + '</dt><dd>' + esc(display_date(report[field], lang)) + '</dd></div>' for label, field in (("asof", "as_of"), ("financials", "financial_period"), ("prepared", "prepared_at"), ("checked", "freshness_checked_at")))
    hero = '<header class="hero"><p class="eyebrow">' + esc(tr["report"] + " / " + company["ticker"] + " · " + company["exchange"]) + '</p><h1>' + esc(company["name"]) + '</h1><p class="subtitle">' + esc(report["subtitle"]) + '</p><p class="identity">' + esc(" · ".join(company[k] for k in ("industry", "share_class", "currency"))) + '</p><dl class="metadata">' + metadata + '</dl></header>'
    quote = records[report["quote_evidence_id"]]
    quote_html = '<div class="quote"><span>' + esc(tr["quote"]) + '</span><strong>' + esc(quote["display"]) + refs([quote["id"]]) + '</strong><small>' + esc(display_date(quote.get("observed_at", quote["period"]), lang) + " · " + quote.get("session", tr["unavailable"])) + '</small></div>'
    summary_points = '<div class="summary-grid">' + "".join('<article class="summary-point"><span class="summary-index">' + str(i+1).zfill(2) + '</span>' + clause(x) + '</article>' for i, x in enumerate(data["summary"])) + '</div>'
    if audience.guide:
        summary_points = audience.pair('<div class="summary-grid">' + ''.join('<article class="summary-point">' + clause(c) + '</article>' for c in audience.guide['summary']) + '</div>', summary_points)
    headline_metrics = '<div class="metrics highlights">' + ''.join(metric(e) for e in data.get('highlights', [])) + '</div>'
    if audience.guide:
        headline_metrics = audience.pair('<div class="metrics highlights">' + ''.join(metric(e) for e in audience.guide['highlights']) + '</div>', headline_metrics)
    summary = block(tr["summary"], audience.orientation() + quote_html + headline_metrics + summary_points, "overview")
    main_sections = sorted((s for s in data["sections"] if s["id"] != "0"), key=lambda s: int(s["id"]))
    counts = {state: sum(c["status"] == state for s in main_sections for c in s["checks"]) for state in statuses}
    status_legend = '<div class="status-legend">' + "".join('<span><i class="status-dot ' + state + '" aria-hidden="true"></i>' + esc(statuses[state]) + '<b>' + str(count) + '</b></span>' for state, count in counts.items() if count) + '</div>'
    coverage = '<div class="coverage-visual"><div><span class="eyebrow">' + esc(tr["coverage_short"]) + '</span><p><strong>' + str(assessed) + '<span>/' + str(total) + '</span></strong> ' + esc(tr["coverage"]) + '</p></div><p class="coverage-caption">' + esc(tr["coverage_note"]) + '</p></div>'
    tiles = '<div class="checklist-map">' + "".join('<a class="map-topic" href="#section-' + s["id"] + '"><span class="map-number">' + s["id"].zfill(2) + '</span><span class="map-label">' + esc(section_map[s["id"]][lang]) + '</span>' + status_dots(s["checks"]) + '</a>' for s in main_sections) + '</div>'
    checklist_map = block(tr["map"], coverage + status_legend + tiles + '<p class="map-caption">' + esc(tr["map_note"]) + '</p>', "checklist-map")
    sections = []
    for section in sorted(data["sections"], key=lambda s: int(s["id"])):
        title = '<span class="section-number">' + section["id"].zfill(2) + '</span><span>' + esc(section_map[section["id"]][lang]) + '</span>'
        # A concise finding stays visible for every item, including adverse and missing evidence.
        body = clause(section["intro"]) + '<div class="metrics">' + "".join(metric(e) for e in section.get("metrics", [])) + '</div>' + checks(section["checks"])
        if audience.guide:
            teaching = audience.guide['sections'][section['id']]
            title = '<span class="section-number">' + section['id'].zfill(2) + '</span><span>' + audience.pair(esc(teaching['label']), esc(section_map[section['id']][lang]), True) + '</span>'
            body = audience.pair(clause({**teaching, 'label': ''}), clause(section['intro'])) + audience.pair('', '<div class="metrics">' + ''.join(metric(e) for e in section.get('metrics', [])) + '</div>') + checks(section['checks'])
        if section['id'] == '12': body += '<div id="valuation">__SCENARIO_TABLE__</div>'
        if section['id'] == '13': body += '<div id="peers">__PEER_TABLE__</div>'
        body += "__CHARTS_" + section["id"] + "__"
        sections.append('<section class="report-section analysis-section" id="section-' + section["id"] + '"><h2>' + title + '</h2>' + body + '</section>')
    analysis_controls = '<div class="analysis-controls"><span>' + esc(tr["analysis"]) + '</span><button class="reasoning-toggle" type="button" hidden data-open-label="' + esc(tr["open_all"]) + '" data-close-label="' + esc(tr["close_all"]) + '" aria-expanded="false">' + esc(tr["open_all"]) + '</button></div>'
    more = 'Supporting detail' if lang == 'en' else 'Detalii suplimentare'
    peer_detail = "".join('<article class="peer"><h3>' + esc(peer["name"]) + '</h3>' + clause(peer["rationale"]) + '<p>' + '; '.join(esc(records[e]['label'] + ': ' + records[e]['display']) + refs([e]) for e in peer.get('metrics', [])) + '</p>' + clause(peer["assessment"]) + '</article>' for peer in data.get("peers", []))
    comparison = data.get('peer_table')
    dimension = 'Criterion' if lang == 'en' else 'Criteriu'
    if comparison:
        head = '<th scope="col">' + dimension + '</th>' + ''.join('<th scope="col">' + esc(c) + '</th>' for c in comparison['columns'])
        rows = ''.join('<tr><th scope="row">' + esc(row['label']) + '</th>' + ''.join('<td>' + clause(cell) + '</td>' for cell in row['cells']) + '</tr>' for row in comparison['rows'])
        peers = '<div class="comparison-scroll" tabindex="0" role="region" aria-label="' + esc(tr['peers']) + '"><table class="peer-table"><thead><tr>' + head + '</tr></thead><tbody>' + rows + '</tbody></table></div>'
        peers += '<details class="supplemental"><summary>' + more + '</summary>' + peer_detail + '</details>'
    else:
        peers = peer_detail
    if data.get("peer_note"):
        peers += clause(data["peer_note"]) if isinstance(data["peer_note"], dict) else '<p>' + esc(data["peer_note"]) + '</p>'
    ordered_scenarios = sorted(data["scenarios"], key=lambda s: ("bear", "base", "bull").index(s["key"]))
    result_count = max(len(sc['results']) for sc in ordered_scenarios)
    rows = []
    for index in range(result_count):
        entries = [records[sc['results'][index]] if index < len(sc['results']) else None for sc in ordered_scenarios]
        exemplar = next(e for e in entries if e)
        comparable = all(not e or all(e[k] == exemplar[k] for k in ('label', 'period', 'unit')) for e in entries)
        cells = ''.join('<td>' + ((('<small>' + esc(e['label'] + ' · ' + e['period'] + ' · ' + e['unit']) + '</small>') if not comparable else '') + esc(e['display']) + refs([e['id']]) if e else '<td>—') + '</td>' for e in entries)
        rows.append('<tr><th scope="row">' + esc(exemplar['label'] if comparable else ('Scenario result' if lang == 'en' else 'Rezultatul scenariului')) + '<small>' + esc(exemplar['period'] if comparable else '') + '</small></th>' + cells + '</tr>')
    scenario_table = '<div class="comparison-scroll" tabindex="0" role="region" aria-label="' + esc(tr['scenarios']) + '"><table class="scenario-table"><thead><tr><th scope="col">' + ('Measure' if lang == 'en' else 'Indicator') + '</th>' + ''.join('<th scope="col">' + esc(sc['name']) + '</th>' for sc in ordered_scenarios) + '</tr></thead><tbody>' + ''.join(rows) + '</tbody></table></div>'
    note = 'Conditional model estimates. Present values and future share values have different dates; assumptions and limitations are below.' if lang == 'en' else 'Estimări condiționate de model. Valorile prezente și cele viitoare au date diferite; ipotezele și limitele sunt mai jos.'
    scenarios = '<p class="table-caveat">' + note + '</p>' + scenario_table
    scenarios += '<details class="scenario-detail supplemental"><summary>' + esc(tr['scenario_detail']) + '</summary>'
    for sc in ordered_scenarios:
        scenarios += '<article class="scenario"><h3>' + esc(sc['name']) + '</h3><p>' + '; '.join(esc(records[e]['label'] + ': ' + records[e]['display']) + refs([e]) for e in sc.get('assumptions', [])) + '</p>' + clause(sc['commentary']) + '</article>'
    result_notes = {}
    for sc in ordered_scenarios:
        for eid in sc['results']:result_notes.setdefault(records[eid]['note'], []).append(eid)
    scenarios += ''.join('<p>' + esc(note) + refs(ids) + '</p>' for note, ids in result_notes.items()) + '</details>'
    if audience.guide:
        peers = audience.pair(''.join(clause(c) for c in audience.guide['peers']), peers)
        cards = '<div class="scenario-reading">'
        for sc in ordered_scenarios:
            teaching = audience.guide['scenarios'][sc['key']]
            eid = sc['results'][0]
            cards += '<article><h3>' + esc(teaching['label']) + '</h3><strong>' + esc(records[eid]['display']) + '</strong>' + refs([eid]) + clause({**teaching, 'label': ''}) + '</article>'
        cards += '</div>'
        scenarios = audience.pair(cards, scenarios)
    sections = [section.replace('__SCENARIO_TABLE__', scenarios).replace('__PEER_TABLE__', peers) for section in sections]
    charts = []
    section_charts = {}
    for chart_index, chart in enumerate(data.get("charts", [])):
        series = [s for s in chart.get("series", []) if s.get("points")]
        if not series:
            continue
        values = [float(records[p["evidence_id"]]["raw_value"]) for s in series for p in s["points"]]
        low, high = min(0, min(values)), max(0, max(values))
        span = high - low or 1
        svg = '<svg viewBox="0 0 720 240" role="img" aria-label="' + esc(chart["title"]) + '"><line x1="60" y1="205" x2="690" y2="205" stroke="#c7cfcb"/>'
        for fraction in (0, .5, 1):
            y, value = 205 - 175 * fraction, low + span * fraction
            svg += f'<line x1="60" y1="{y}" x2="690" y2="{y}" stroke="#e2e5e1"/><text x="50" y="{y + 4}" text-anchor="end">{value:,.1f}</text>'
        colours = ["#24624e", "#607884", "#976f49", "#705f85"]
        table_rows, legends = [], []
        for si, s in enumerate(series):
            points = []
            for i, p in enumerate(s["points"]):
                item = records[p["evidence_id"]]
                x = 60 + i * 630 / max(1, len(s["points"]) - 1)
                y = 205 - (float(item["raw_value"]) - low) / span * 175
                points.append(f"{x:.2f},{y:.2f}")
                svg += f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3" fill="{colours[si % 4]}"><title>' + esc(p["label"] + ": " + item["display"]) + '</title></circle>'
                if si == 0 and (len(s["points"]) <= 8 or i in (0, len(s["points"]) - 1)):
                    svg += f'<text x="{x:.2f}" y="228" text-anchor="middle">' + esc(p["label"]) + '</text>'
                table_rows.append('<tr><td>' + esc(s["name"]) + '</td><td>' + esc(p["label"]) + '</td><td>' + esc(item["display"]) + refs([item["id"]]) + '</td></tr>')
            svg += '<polyline points="' + " ".join(points) + '" fill="none" stroke="' + colours[si % 4] + '" stroke-width="2.5"/>'
            legends.append('<span style="color:' + colours[si % 4] + '">' + esc(s["name"]) + '</span>')
        svg += '</svg>'
        chart_markup = ('<figure class="chart" id="chart-' + str(chart_index) + '"><figcaption><h3>' + esc(chart["title"]) + '</h3><p>' + esc(chart.get("description", "") + " · " + chart["unit"]) + '</p></figcaption><p class="chart-hint">' + esc(tr['chart_hint']) + '</p><div class="chart-plot" tabindex="0" role="region" aria-label="' + esc(chart['title']) + '">' + svg + '</div><div class="legend">' + " · ".join(legends) + '</div><details class="chart-data"><summary>' + esc(tr["data"]) + '</summary><table><thead><tr><th>' + esc(tr["series"]) + '</th><th>' + esc(tr["period"]) + '</th><th>' + esc(tr["value"]) + '</th></tr></thead><tbody>' + "".join(table_rows) + '</tbody></table></details></figure>')
        if chart.get('section_id') is not None: section_charts.setdefault(str(chart['section_id']), []).append(chart_markup)
        else: charts.append(chart_markup)
    key_evidence = set(data.get('highlights', []))
    def collect(obj):
        if isinstance(obj, dict):
            key_evidence.update(obj.get('evidence_ids', []))
            for key, value in obj.items():
                if key != 'evidence_ids': collect(value)
        elif isinstance(obj, list):
            for value in obj: collect(value)
    if audience.guide: collect(audience.guide)
    for field in ('summary', 'monitoring', 'peer_table'): collect(data.get(field, []))
    for section in data['sections']:
        collect(section['intro']); key_evidence.update(section.get('metrics', []))
        for item in section['checks']: collect(item.get('finding', {'evidence_ids':item.get('evidence_ids', [])}))
    for sc in data['scenarios']: key_evidence.update(sc['results'])
    evidence_html = []
    for eid, item in records.items():
        fields = (("kind", tr[item["kind"]]), ("period", item["period"]), ("unit", item["unit"]), ("basis", item["basis"]))
        if item.get("observed_at"):
            fields += (("quote_at", item["observed_at"]), ("quote_session", item.get("session", "")))
        body = '<dl class="evidence-meta">' + "".join('<div><dt>' + esc(tr[k]) + '</dt><dd>' + esc(v) + '</dd></div>' for k, v in fields) + '</dl><p>' + esc(item["note"]) + '</p>'
        calc = item.get("calculation")
        if calc:
            body += '<p><strong>' + esc(tr["formula"]) + '</strong> ' + esc(calc["formula"]) + '</p><ul>' + "".join('<li>' + esc(records[i]["label"] + ': ' + records[i]["display"]) + refs([i]) + '</li>' for i in calc["inputs"]) + '</ul>'
        body += refs(item.get("evidence_ids", []))
        for sid in item.get("source_ids", []):
            source = sources[sid]
            body += '<p class="source-detail"><a href="#source-' + esc(sid) + '">' + esc(source["publisher"] + " · " + source["title"]) + '</a><br>' + esc(source["locator"]) + '<br>' + esc(tr["published"] + ': ' + (source.get("published_at") or source.get("date_note", "")) + ' · ' + tr["accessed"] + ': ' + source["accessed_at"]) + '</p>'
            if source.get("url"):
                body += '<a class="original-link" href="' + esc(source["url"]) + '" target="_blank" rel="noopener noreferrer">' + esc(source["url"]) + '</a>'
        detail = '<article class="evidence-entry"><h3><span class="evidence-number">' + numbering[eid] + '</span> ' + esc(item["label"]) + '</h3><p class="evidence-value">' + esc(item["display"]) + '</p>' + body + '</article>'
        value = '<strong class="evidence-row-value">' + esc(item['display']) + '</strong>' if item.get('raw_value') is not None else ''
        row = '<summary><span class="evidence-number">' + numbering[eid] + '</span><span class="evidence-row-label">' + esc(item['label']) + '<small>' + esc(item['period']) + '</small></span>' + value + '<span class="evidence-kind">' + esc(tr[item['kind']]) + '</span></summary>'
        evidence_html.append('<details class="evidence-record" id="ev-' + esc(eid) + '" data-supporting="' + ('false' if eid in key_evidence else 'true') + '" data-kind="' + esc(item['kind']) + '">' + row + detail + '</details>')
    compact = {
        'en': {'hint': 'Search the evidence, then expand a row for its sources and calculation. Numbered citations in the report open the same details directly.', 'search': 'Search evidence', 'placeholder': 'Revenue, credit, EPS…', 'type': 'Evidence type', 'all': 'All types', 'previous': 'Previous', 'next': 'Next', 'empty': 'No matching evidence. Try a broader search or another type.', 'reset': 'Clear filters', 'records': 'records'},
        'ro': {'hint': 'Căutați în dovezi, apoi extindeți un rând pentru surse și calcul. Referințele numerotate din analiză deschid direct aceleași detalii.', 'search': 'Caută dovezi', 'placeholder': 'Venituri, credit, EPS…', 'type': 'Tipul dovezii', 'all': 'Toate tipurile', 'previous': 'Înapoi', 'next': 'Înainte', 'empty': 'Nicio dovadă găsită. Încercați o căutare mai largă sau alt tip.', 'reset': 'Resetează filtrele', 'records': 'înregistrări'},
    }[lang]
    kind_options = '<option value="">' + compact['all'] + '</option>' + ''.join('<option value="' + kind + '">' + esc(tr[kind]) + '</option>' for kind in dict.fromkeys(item['kind'] for item in records.values()))
    evidence_controls = '<div class="evidence-controls" hidden><label>' + compact['search'] + '<input id="evidence-search" type="search" placeholder="' + compact['placeholder'] + '" autocomplete="off" aria-controls="evidence-list"></label><label>' + compact['type'] + '<select id="evidence-type" aria-controls="evidence-list">' + kind_options + '</select></label><button id="evidence-reset" type="button">' + compact['reset'] + '</button></div>'
    evidence_controls += '<label class="supporting-toggle" hidden><input id="evidence-supporting" type="checkbox">' + ('Include supporting inputs' if lang == 'en' else 'Include datele intermediare') + '</label>'
    pager = '<div class="evidence-pager" hidden><span id="evidence-count" role="status" aria-live="polite" aria-atomic="true"></span><div><button id="evidence-previous" type="button">' + compact['previous'] + '</button><button id="evidence-next" type="button">' + compact['next'] + '</button></div></div>'
    evidence_index = '<p class="evidence-intro">' + str(len(records)) + ' ' + compact['records'] + '. ' + compact['hint'] + '</p>' + evidence_controls + '<p id="evidence-empty" hidden>' + compact['empty'] + '</p><div id="evidence-list">' + ''.join(evidence_html) + '</div>' + pager
    source_html = []
    for sid, source in sources.items():
        link = '<a href="' + esc(source["url"]) + '" target="_blank" rel="noopener noreferrer">' + esc(source["url"]) + '</a>' if source.get("url") else esc(source.get("file", "Synthetic layout fixture / date demonstrative"))
        source_html.append('<details class="source-record" id="source-' + esc(sid) + '"><summary>' + esc(source["title"]) + '</summary><article class="source-entry"><p>' + esc(source["publisher"] + " · " + source["source_type"]) + '</p><p>' + esc(source["locator"]) + '</p><p>' + esc(tr["published"] + ': ' + (source.get("published_at") or source.get("date_note", "")) + ' · ' + tr["accessed"] + ': ' + source["accessed_at"]) + '</p><p class="original-link">' + link + '</p></article></details>')
    log_html = '<ul class="research-log">' + "".join('<li><strong>' + esc(log["topic"]) + '</strong> · ' + esc(log["checked_at"]) + '<p>' + esc(log["result"]) + '</p>' + ' '.join('<a href="#source-' + esc(s) + '">' + esc(sources[s]["title"]) + '</a>' for s in log.get("source_ids", [])) + '</li>' for log in data["research_log"]) + '</ul>'
    navigation = [("overview", tr["summary"]), ("checklist-map", tr["checklist"]), ("peers", tr["peers"]), ("valuation", tr["scenarios"]), ("gaps", tr["gaps"]), ("evidence", tr["evidence"])]
    nav = '<nav aria-label="Report navigation">' + "".join('<a href="#' + anchor + '">' + esc(title) + '</a>' for anchor, title in navigation) + '</nav>'
    monitoring = '<ol class="monitoring-list">' + "".join('<li>' + clause(x) + '</li>' for x in data["monitoring"]) + '</ol>'
    for section_id in section_map:
        sections = [section.replace('__CHARTS_' + section_id + '__', ''.join(section_charts.get(section_id, []))) for section in sections]
    content = banner + hero + summary + "".join(charts) + checklist_map + analysis_controls + "".join(sections) + block(tr["monitor"], monitoring, "monitoring") + block(tr["gaps"], "".join(clause(x) for x in data["gaps"]), "gaps") + block(tr["optional"], checks(data["optional"]), "optional") + block(tr["evidence"], evidence_index, "evidence") + block(tr["sources"], "".join(source_html), "sources") + block(tr["log"], '<details class="supplemental"><summary>' + more + '</summary>' + log_html + '</details>', "research-log")
    css = (ROOT / "assets/report.css").read_text(encoding="utf-8")
    js = (ROOT / "assets/report.js").read_text(encoding="utf-8")
    if audience.guide:
        css += (ROOT / "assets/audience.css").read_text(encoding="utf-8")
        js += (ROOT / "assets/audience.js").read_text(encoding="utf-8")
    if library_href:
        title = 'Company collection' if lang == 'en' else 'Colecția de companii'
        nav = nav.replace('>', '><a class="library-back" href="' + esc(library_href) + '">← ' + title + '</a>', 1)
    return '<!doctype html><html lang="' + lang + '"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="referrer" content="no-referrer"><title>' + esc(company["name"] + ' · ' + tr["report"]) + '</title><style>' + css + '</style></head><body><a class="skip-link" href="#report">' + esc(tr["skip"]) + '</a><div class="topbar"><span>' + esc(tr["report"]) + '</span>' + audience.controls() + '</div><div class="layout">' + nav + '<main id="report">' + content + '</main></div><div id="evidence-tooltip" role="tooltip" hidden></div><dialog id="evidence-dialog" aria-labelledby="dialog-title"><div class="dialog-top"><h2 id="dialog-title">' + esc(tr["evidence"]) + '</h2><button id="close-evidence" type="button">' + esc(tr["close"]) + '</button></div><div id="dialog-body"></div></dialog><script>' + js + '</script></body></html>'


def render(data, library_href=None):
    if not data.get('translations'):
        return _render_single(data,library_href)
    from localization import localized,bilingual
    default=data['report']['language']
    pages={language:_render_single(localized(data,language),library_href) for language in ('en','ro')}
    return bilingual(pages,default,(ROOT/'assets/localization.js').read_text(encoding='utf8'),(ROOT/'assets/localization.css').read_text(encoding='utf8'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate", "render"))
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--library", type=Path, help="Override the shared collection root")
    args = parser.parse_args()
    try:
        data = json.loads(args.input.read_text(encoding="utf-8-sig"))
        errors = validate(data)
        from library import validate_metadata
        errors.extend(validate_metadata(data))
        if errors:
            print("Validation failed:\n- " + "\n- ".join(errors), file=sys.stderr)
            return 1
        if args.command == "render":
            if args.output is None:
                parser.error("render requires --output")
            from library import atomic_write, publish, rel_link
            registered_report, index = publish(data, args.input, args.library)
            if args.output.resolve() != registered_report.resolve():
                atomic_write(args.output.resolve(), render(data, library_href=rel_link(index, args.output.resolve().parent)))
            print("Rendered " + str(args.output))
            print("Added to collection: " + str(index))
        print("Internal structure, lineage and arithmetic checks passed. Source truth requires human/agent verification.")
        return 0
    except (ValueError, TypeError, KeyError, OSError, InvalidOperation) as error:
        print("Invalid report: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
