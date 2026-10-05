"""Regresiones stdlib de utilidades S6. No prueban SDK, modelo ni servicios remotos."""
import csv
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
store = load('s6_manifest', 'app/soporte/manifest_store.py')
report = load('s6_report', 'scripts/resumir_evaluacion.py')
class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name); self.new=self.root/'data/prompts-remotos.json'
        self.old=self.root/'material/profesor/prompts-remotos.json'
        self.value={'name':'aula','versions':{'v1':{'sha256':'abc'}}}
    def test_fresh_clone_creates_parent_only(self):
        store.prepare_manifest(self.new,self.old)
        self.assertTrue(self.new.parent.is_dir()); self.assertFalse(self.new.exists())
    def test_legacy_copied_and_retained(self):
        store.write_manifest(self.old,self.value); store.prepare_manifest(self.new,self.old)
        self.assertEqual(json.loads(self.new.read_text()),self.value); self.assertTrue(self.old.exists())
    def test_new_not_overwritten(self):
        store.write_manifest(self.old,self.value)
        new={'name':'nuevo','versions':{}}; store.write_manifest(self.new,new)
        store.prepare_manifest(self.new,self.old); self.assertEqual(json.loads(self.new.read_text()),new)
    def test_bad_json_rejected(self):
        self.old.parent.mkdir(parents=True);self.old.write_text('no json')
        with self.assertRaises(ValueError): store.prepare_manifest(self.new,self.old)
        self.assertFalse(self.new.exists())
    def test_bad_shape_rejected(self):
        store.write_manifest(self.old,{'versions':[]})
        with self.assertRaises(ValueError): store.prepare_manifest(self.new,self.old)
    def test_unicode(self):
        store.write_manifest(self.new,{'name':'versión','versions':{}})
        self.assertIn('versión',self.new.read_text())
    def test_atomic_failure_preserves_previous(self):
        store.write_manifest(self.new,self.value)
        with patch.object(store.os,'replace',side_effect=OSError('test')):
            with self.assertRaises(OSError): store.write_manifest(self.new,{'versions':{}})
        self.assertEqual(json.loads(self.new.read_text()),self.value)
        self.assertEqual(len(list(self.new.parent.iterdir())),1)
    def test_same_path_not_migrated(self):
        store.prepare_manifest(self.new,self.new); self.assertFalse(self.new.exists())
    def test_partial_registry_can_migrate(self):
        store.write_manifest(self.old,{'name':'aula','versions':{}})
        store.prepare_manifest(self.new,self.old); self.assertTrue(self.new.exists())
class ReportTests(unittest.TestCase):
    def row(self,**kw):
        return {'query_id':'q1','case_id':'E01','prompt_version':'v1','quality':None,
                'duration_s':2.,'total_tokens':None,'cost_usd':None,'errors':[],**kw}
    def review(self,**kw):
        return {'query_id':'q1','case_id':'E01','prompt_version':'v1','quality':'1','motivo':'Cumple rúbrica',**kw}
    def apply(self,review,rows=None):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'r.csv'
            with p.open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=['query_id','case_id','prompt_version','quality','motivo'])
                w.writeheader(); w.writerow(review)
            return report.apply_reviews(rows or [self.row()],p)
    def test_pending_not_failure(self):
        s=report.summarize([self.row()])['v1'];self.assertEqual((s['reviewed'],s['pending']),(0,1))
    def test_missing_cost_not_zero(self):
        s=report.summarize([self.row()])['v1']; self.assertIsNone(s['cost_usd']['sum'])
    def test_zero_known(self):
        s=report.summarize([self.row(cost_usd=0)])['v1'];self.assertEqual(s['cost_usd']['known'],1)
    def test_partial_coverage(self):
        s=report.summarize([self.row(cost_usd=.1),self.row(query_id='q2',case_id='E02')])['v1']
        self.assertEqual((s['cost_usd']['known'],s['total']),(1,2))
    def test_versions_separate(self):
        s=report.summarize([self.row(),self.row(query_id='q2',prompt_version='v2',quality=1)])
        self.assertEqual(s['v2']['correct'],1); self.assertEqual(s['v1']['reviewed'],0)
    def test_bad_numbers(self):
        for value in (True,-1,float('nan'),float('inf'),'2'): self.assertFalse(report.numeric(value))
    def test_duplicate_pair(self):
        with self.assertRaises(ValueError): report.summarize([self.row(),self.row(query_id='q2')])
    def test_duplicate_query(self):
        with self.assertRaises(ValueError): report.summarize([self.row(),self.row(case_id='E02')])
    def test_quality_range(self):
        for value in (True,'1',.5,2):
            with self.assertRaises(ValueError): report.summarize([self.row(quality=value)])
    def test_error_count(self):
        s=report.summarize([self.row(errors=['TimeoutError'])])['v1'];self.assertEqual(s['errors'],1)
    def test_reviews_preserve_original(self):
        rows=[self.row()]; result=self.apply(self.review(),rows)
        self.assertEqual(result[0]['quality'],1); self.assertIsNone(rows[0]['quality'])
    def test_unknown_review(self):
        with self.assertRaises(ValueError): self.apply(self.review(query_id='otra'))
    def test_mismatched_review(self):
        with self.assertRaises(ValueError): self.apply(self.review(case_id='E02'))
    def test_review_needs_reason(self):
        with self.assertRaises(ValueError): self.apply(self.review(motivo=''))
    def test_empty_list(self):
        with self.assertRaises(ValueError): report.summarize([])
if __name__=='__main__': unittest.main()
