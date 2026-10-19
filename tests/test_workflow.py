import importlib.util, json, subprocess, sys, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('workflow',ROOT/'scripts/workflow.py')
w=importlib.util.module_from_spec(spec); spec.loader.exec_module(w)
class WorkflowTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
  self.data={'cwd':self.tmp.name,'session_id':'test'}
 def event(self,event,**kw): return w.handle(dict(self.data,hook_event_name=event,**kw))
 def state(self):
  with w.state_store(self.tmp.name,'test') as (s,_): return dict(s)
 def test_T01_simple(self):
  self.event('UserPromptSubmit',prompt='fix typo')
  self.assertEqual(self.state()['complexity'],'simple')
  self.assertEqual(self.event('Stop'),{})
 def test_T02_ambiguous(self):
  r=self.event('UserPromptSubmit',prompt='让它更好用')
  self.assertEqual(self.state()['type'],'general')
  self.assertIn('clarify only material',r['hookSpecificOutput']['additionalContext'])
 def test_T03_complex(self):
  self.event('UserPromptSubmit',prompt='实现跨模块迁移')
  self.assertEqual(self.state()['complexity'],'complex')
  self.event('PreToolUse',tool_name='Edit')
  self.assertEqual(self.event('Stop')['decision'],'block')
  subprocess.run([sys.executable,str(ROOT/'scripts/workflow.py'),'record','--cwd',self.tmp.name,'--session','test','--status','passed','--evidence','unit tests passed'],check=True)
  self.assertEqual(self.event('Stop',stop_hook_active=True),{})
 def test_T04_review(self):
  self.event('UserPromptSubmit',prompt='review PR')
  for tool in ['Write','Edit','NotebookEdit']:
   self.assertEqual(self.event('PreToolUse',tool_name=tool)['hookSpecificOutput']['permissionDecision'],'deny')
  self.assertEqual(self.event('PreToolUse',tool_name='Bash')['hookSpecificOutput']['permissionDecision'],'ask')
  self.assertEqual(self.event('PreToolUse',tool_name='Read'),{})
 def test_T05_switch(self):
  self.event('UserPromptSubmit',prompt='review PR')
  self.event('UserPromptSubmit',prompt='修复发现的问题')
  self.assertEqual(self.state()['type'],'development')
  self.assertEqual(self.state()['history'][0]['type'],'review')
  self.assertEqual(self.event('PreToolUse',tool_name='Edit'),{})
 def test_T06_missing_verification(self):
  self.event('UserPromptSubmit',prompt='fix bug')
  self.event('PreToolUse',tool_name='Bash',tool_input={'command':'pytest'})
  self.assertEqual(self.state()['validation'],'unknown')
  self.assertEqual(self.event('Stop')['decision'],'block')
  self.assertEqual(self.event('Stop',stop_hook_active=True),{})
 def test_session_isolation_and_traversal(self):
  self.event('UserPromptSubmit',prompt='review')
  w.handle(dict(self.data,session_id='../../outside',hook_event_name='UserPromptSubmit',prompt='fix typo'))
  self.assertEqual(self.state()['type'],'review')
  self.assertEqual(len(list((Path(self.tmp.name)/'.workflow').glob('*.json'))),2)
 def test_stdio_contract(self):
  r=subprocess.run([sys.executable,str(ROOT/'scripts/workflow.py'),'hook'],input=json.dumps(dict(self.data,hook_event_name='UserPromptSubmit',prompt='review')),text=True,capture_output=True)
  self.assertEqual(r.returncode,0); self.assertEqual(json.loads(r.stdout)['hookSpecificOutput']['hookEventName'],'UserPromptSubmit')
 def test_corrupt_input_fails_closed(self):
  r=subprocess.run([sys.executable,str(ROOT/'scripts/workflow.py'),'hook'],input='{',text=True,capture_output=True)
  self.assertEqual(r.returncode,2)
if __name__=='__main__': unittest.main()
