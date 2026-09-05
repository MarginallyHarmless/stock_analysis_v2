import base64
import copy
import json
import tempfile
import unittest
from pathlib import Path
from library import card_metrics, identity, locked, publish, read_registry, render_index, safe_path

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / 'assets/example-report.json').read_text(encoding='utf-8'))


class CompanyLibrary(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'collection'
        self.ledger = self.base / 'research.json'
        self.data = copy.deepcopy(DATA)
        self.data['library'] = {'company_id': 'alder-common', 'category': 'Industrials', 'stats': ['revenue-2025', 'fcf-margin']}

    def add(self, data=None):
        return publish(data or self.data, self.ledger, self.root)

    def test_register_latest_and_preserve_older_versions(self):
        old_report, index = self.add()
        original = old_report.read_bytes()
        newer = copy.deepcopy(self.data)
        newer['report']['prepared_at'] = '2026-09-06T12:30:00+03:00'
        newer['company']['ticker'] = 'NEW'
        new_report, _ = self.add(newer)
        registry = read_registry(self.root)
        self.assertEqual(len(registry['companies']), 1)
        company = registry['companies'][0]
        self.assertEqual(company['ticker'], 'NEW')
        self.assertEqual(len(company['history']), 1)
        self.assertEqual((self.root / company['history'][0]['report']).read_bytes(), original)
        self.assertEqual(self.root / company['report'], new_report)
        self.assertIn('Previous reports', index.read_text(encoding='utf-8'))
        # Same dataset is idempotent and importing an old version never takes over.
        self.add(newer)
        self.add()
        self.assertEqual(read_registry(self.root), registry)
        self.assertIn('../../../index.html', new_report.read_text(encoding='utf-8'))

    def test_out_of_order_new_snapshot_stays_in_history(self):
        self.data['report']['prepared_at'] = '2026-09-07T12:30:00+03:00'
        newest, _ = self.add()
        older = copy.deepcopy(self.data)
        older['report']['prepared_at'] = '2026-09-06T12:30:00+03:00'
        old, _ = self.add(older)
        company = read_registry(self.root)['companies'][0]
        self.assertEqual(self.root / company['report'], newest)
        self.assertEqual(self.root / company['history'][0]['report'], old)

    def test_bad_stat_does_not_change_collection(self):
        self.add()
        before = (self.root / 'library.json').read_bytes()
        for stats in (['revenue-2025', 'base-price'], ['fcf-margin', 'absent'], ['fcf-margin', 'fcf-margin']):
            self.data['library']['stats'] = stats
            with self.assertRaises(ValueError): self.add()
            self.assertEqual((self.root / 'library.json').read_bytes(), before)

    def test_registry_links_cannot_escape_or_disappear(self):
        self.add()
        with self.assertRaises(ValueError): safe_path(self.root, '../outside.html')
        registry = read_registry(self.root)
        registry['companies'][0]['report'] = 'reports/missing.html'
        (self.root / 'library.json').write_text(json.dumps(registry), encoding='utf-8')
        with self.assertRaises(ValueError): read_registry(self.root)

    def test_exchange_share_class_and_demo_do_not_collide(self):
        keys = {identity(self.data)}
        for field in ('exchange', 'share_class'):
            data = copy.deepcopy(self.data)
            del data['library']['company_id']
            data['company'][field] = 'Different security'
            keys.add(identity(data))
        data = copy.deepcopy(self.data)
        data['demo'] = False
        keys.add(identity(data))
        self.assertEqual(len(keys), 4)

    def test_busy_writer_does_not_overwrite_registry(self):
        self.add()
        before = (self.root / 'library.json').read_bytes()
        with locked(self.root):
            with self.assertRaisesRegex(ValueError, 'in progress'): self.add()
        self.assertEqual((self.root / 'library.json').read_bytes(), before)

    def test_card_values_link_to_ledger_and_dates_do_not_refresh(self):
        _, index = self.add()
        registry = read_registry(self.root)
        company = registry['companies'][0]
        evidence = {item['id']: item for item in self.data['evidence']}
        for metric in company['metrics']:
            self.assertEqual(metric['display'], evidence[metric['id']]['display'])
            self.assertIn('#ev-' + metric['id'], index.read_text(encoding='utf-8'))
        render_index(registry)
        self.assertEqual(company['updated_at'], self.data['report']['prepared_at'])
        self.assertEqual(company['as_of'], self.data['report']['as_of'])

    def test_embedded_logo_and_portable_archive(self):
        png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aPRkAAAAASUVORK5CYII=')
        (self.base / 'logo.png').write_bytes(png)
        self.data['library']['logo'] = {'file': 'logo.png', 'source_id': 'demo-source'}
        report, index = self.add()
        archived = json.loads(report.with_name('research.json').read_text(encoding='utf-8'))
        self.assertEqual((report.parent / archived['library']['logo']['file']).read_bytes(), png)
        self.assertIn('data:image/png;base64,', index.read_text(encoding='utf-8'))
        replay, _ = publish(archived, report.with_name('research.json'), self.root)
        self.assertEqual(replay, report)
        self.assertEqual(read_registry(self.root)['companies'][0]['history'], [])

    def test_escaped_text_and_empty_collection(self):
        self.add()
        registry = read_registry(self.root)
        registry['companies'][0]['name'] = '<img src=x onerror=alert(1)>'
        output = render_index(registry)
        self.assertNotIn('<img src=x', output)
        self.assertIn('&lt;img', output)
        self.assertIn('Your company reports will gather here', render_index({'companies': []}))


if __name__ == '__main__':
    unittest.main()
