import copy
import json
import sys
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from report import calculate, render, validate

DATA = json.loads((ROOT / "assets/example-report.json").read_text(encoding="utf-8"))

class Calculations(unittest.TestCase):
    def test_cash_flow_bridge(self):
        self.assertEqual(calculate("difference", [248, 63]), Decimal(185))
        self.assertEqual(calculate("ttm", [920, 550, 460]), Decimal(1010))
        self.assertEqual(calculate("percent", [-20, 100]), Decimal(-20))
        self.assertEqual(calculate("ratio", [-100, 20]), Decimal(-5))

    def test_denominators_cannot_silently_pass(self):
        for denominator in (0, -1, None):
            with self.subTest(denominator=denominator), self.assertRaises(ValueError):
                calculate("ratio", [100, denominator])

    def test_cagr_elapsed_years_and_sign(self):
        self.assertAlmostEqual(float(calculate("cagr", [100, 200], 5)), 14.8698355, places=6)
        for endpoints in ((-5, 10), (0, 10), (5, -10)):
            with self.assertRaises(ValueError): calculate("cagr", endpoints, 5)
        for years in (0, -1, 1.5, True):
            with self.assertRaises(ValueError): calculate("cagr", [100, 200], years)

    def test_non_finite_is_rejected(self):
        for val in ("NaN", "Infinity", True):
            with self.assertRaises(ValueError): calculate("sum", [val, 2])

class Ledger(unittest.TestCase):
    def setUp(self): self.data = copy.deepcopy(DATA)
    def entry(self, id): return next(e for e in self.data["evidence"] if e["id"] == id)
    def test_fixture(self): self.assertEqual(validate(self.data), [])
    def test_false_arithmetic(self):
        self.entry("fcf")["raw_value"] = 999
        self.assertTrue(any("does not match" in e for e in validate(self.data)))
    def test_lineage_cycle(self):
        self.entry("fcf")["calculation"]["inputs"] = ["fcf-margin", "capex"]
        self.assertTrue(any("Cyclic" in e for e in validate(self.data)))
    def test_missing_original_reference(self):
        self.entry("cfo")["source_ids"] = ["absent"]
        self.assertTrue(any("missing source" in e for e in validate(self.data)))
    def test_checklist_omission(self):
        self.data["sections"][8]["checks"].pop()
        self.assertTrue(any("subitems" in e for e in validate(self.data)))
    def test_optional_omission(self):
        self.data["optional"].pop()
        self.assertTrue(any("optional indicators" in e for e in validate(self.data)))
    def test_assumptions_are_not_observations(self):
        self.data["sections"][8]["checks"][1]["evidence_ids"] = ["base-price"]
        self.assertTrue(any("only missing data or assumptions" in e for e in validate(self.data)))
    def test_unavailable_is_not_zero(self):
        self.entry("no-history")["raw_value"] = 0
        self.assertTrue(any("unavailable cannot" in e for e in validate(self.data)))
    def test_future_source(self):
        self.data["sources"][0]["published_at"] = "2027-01-01"
        self.assertTrue(any("after the information cutoff" in e for e in validate(self.data)))
    def test_bad_timestamp(self):
        self.data["report"]["as_of"] = "2026-09-05T12:00:00"
        self.assertTrue(any("invalid date/timestamp" in e for e in validate(self.data)))
    def test_quote_needs_actual_observation(self):
        del self.entry("quote")["observed_at"]
        self.assertTrue(any("observed_at and session" in e for e in validate(self.data)))
    def test_unsafe_link(self):
        self.data["sources"][0]["url"] = "javascript:alert(1)"
        self.assertTrue(any("unsafe/invalid" in e for e in validate(self.data)))
    def test_demo_cannot_be_relabelled_real(self):
        self.data["demo"] = False
        self.assertTrue(any("verification" in e for e in validate(self.data)))
    def test_unit_mismatch(self):
        self.data["charts"][0]["unit"] = "RON million"
        self.assertTrue(any("units differ" in e for e in validate(self.data)))
    def test_markup_is_escaped(self):
        self.data["company"]["name"] = '<img src=x onerror="alert(1)">'
        doc = render(self.data)
        self.assertNotIn('<img src=x', doc)
        self.assertIn('&lt;img', doc)
    def test_romanian_ui(self):
        self.data["report"]["language"] = "ro"
        doc = render(self.data)
        self.assertIn('<html lang="ro">', doc)
        self.assertIn('Dovezi și calcule', doc)
        self.assertIn('Pregătire', doc)

    def test_visuals_preserve_all_research_text(self):
        from html.parser import HTMLParser
        class Text(HTMLParser):
            def __init__(self):
                super().__init__()
                self.parts, self.skip = [], False
            def handle_starttag(self, tag, attrs):
                if tag in ('script', 'style'): self.skip = True
            def handle_endtag(self, tag):
                if tag in ('script', 'style'): self.skip = False
            def handle_data(self, text):
                if not self.skip: self.parts.append(text)
        original = copy.deepcopy(self.data)
        parser = Text()
        parser.feed(render(self.data))
        body = ' '.join(' '.join(parser.parts).split())
        expected = [x['text'] for key in ('summary', 'monitoring', 'gaps') for x in self.data[key]]
        expected += [s['intro']['text'] for s in self.data['sections']]
        expected += [c['explanation'] for s in self.data['sections'] for c in s['checks']]
        expected += [c['explanation'] for c in self.data['optional']]
        expected += [s['commentary']['text'] for s in self.data['scenarios']]
        expected += [e['note'] for e in self.data['evidence']]
        expected += [e['calculation']['formula'] for e in self.data['evidence'] if e.get('calculation')]
        for text in expected:
            self.assertIn(' '.join(text.split()), body)
        self.assertEqual(self.data, original)

    def test_flow_diagrams_require_matched_periods(self):
        self.assertEqual(render(self.data).count('class="flow-diagram"'), 3)
        self.entry('cfo')['period'] = 'Different financial year'
        self.assertEqual(render(self.data).count('class="flow-diagram"'), 2)

    def test_flow_diagrams_require_matched_units(self):
        self.entry('cfo')['unit'] = 'EUR million'
        self.assertEqual(render(self.data).count('class="flow-diagram"'), 2)

    def test_scenario_table_identifies_incomparable_results(self):
        doc = render(self.data)
        self.assertEqual(doc.count('class="scenario-table"'), 1)
        self.entry('bull-price')['period'] = 'Year 6'
        doc = render(self.data)
        table = doc.split('class="scenario-table"', 1)[1].split('</table>', 1)[0]
        self.assertTrue('Year 6' in table)
        self.assertTrue('Scenario result' in table)
        self.assertEqual(doc.count('class="scenario"'), 3)

if __name__ == "__main__": unittest.main(verbosity=2)
