import importlib.util, unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('etcr',Path(__file__).parent/'evaluator/etcr.py'); e=importlib.util.module_from_spec(spec); spec.loader.exec_module(e)
class EvaluatorTests(unittest.TestCase):
 def test_effective_requires_all_criteria(self):
  rows=[dict(id='T01',acceptance_met=True,constraints_met=True,no_major_rework=True),dict(id='T02',acceptance_met=True,constraints_met=False,no_major_rework=True)]
  r=e.evaluate(dict(suite='v1',version='test',tasks=rows)); self.assertEqual(r['etcr'],50); self.assertIsNone(r['mean_tokens'])
 def test_unknown_is_not_success(self):
  with self.assertRaises(ValueError): e.evaluate(dict(suite='v1',version='test',tasks=[dict(id='T01')]))
