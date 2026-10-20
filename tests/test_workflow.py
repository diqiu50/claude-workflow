import shlex, importlib.util, json, subprocess, sys, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
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
  self.assertEqual(self.event('Stop'),{})
  subprocess.run([sys.executable,str(ROOT/'scripts/workflow.py'),'verify','--cwd',self.tmp.name,'--session','test','--',sys.executable,'-c','print(\"check passed\")'],check=True,capture_output=True)
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
  self.assertEqual(self.event('Stop'),{})
  self.assertEqual(self.event('Stop',stop_hook_active=True),{})
 def record_command(self, **changes):
  options={'--cwd':self.tmp.name,'--session':'test','--status':'unavailable','--evidence':'Static first([]) review; empty input raises IndexError'}
  options.update(changes)
  return shlex.join(['python3',str(ROOT/'scripts/workflow.py'),'record']+[v for pair in options.items() for v in pair])
 def test_review_record_does_not_invalidate_or_request_permission(self):
  self.event('UserPromptSubmit',prompt='Review app.py，先不要修改文件')
  self.assertEqual(self.state()['type'],'review')
  command=self.record_command()
  self.assertTrue(w.is_local_record(dict(self.data,tool_name='Bash',tool_input={'command':command})))
  self.assertEqual(self.event('PreToolUse',tool_name='Bash',tool_input={'command':command}),{})
  subprocess.run(shlex.split(command),check=True)
  self.assertEqual(self.state()['validation'],'unavailable')
  self.assertEqual(self.event('Stop'),{})
 def test_record_exemption_rejects_injection_and_other_sessions(self):
  self.event('UserPromptSubmit',prompt='review')
  base=self.record_command()
  commands=[base+'; touch bad',base+' && touch bad',base+' | cat',base+' > out',base+'\ntrue',self.record_command(**{'--session':'other'}),self.record_command(**{'--cwd':'/tmp'}),base.replace(' record ',' route '),base.replace(str(ROOT/'scripts/workflow.py'),'/tmp/workflow.py'),self.record_command(**{'--evidence':'$(touch bad)'})]
  for command in commands:
   with self.subTest(command=command):
    self.assertEqual(self.event('PreToolUse',tool_name='Bash',tool_input={'command':command})['hookSpecificOutput']['permissionDecision'],'ask')
 def test_development_record_preserves_validation(self):
  self.event('UserPromptSubmit',prompt='fix typo')
  command=self.record_command()
  subprocess.run(shlex.split(command),check=True)
  self.event('PreToolUse',tool_name='Bash',tool_input={'command':command})
  self.assertEqual(self.state()['validation'],'unavailable')
 def test_record_accepts_only_quoted_pwd_as_cwd(self):
  self.event('UserPromptSubmit',prompt='review')
  base=self.record_command()
  literal=shlex.quote(self.tmp.name)
  for pwd in ['"$PWD"','"${PWD}"']:
   command=base.replace('--cwd '+literal,'--cwd '+pwd)
   with self.subTest(pwd=pwd):
    self.assertTrue(w.is_local_record(dict(self.data,tool_name='Bash',tool_input={'command':command})))
    result=self.event('PreToolUse',tool_name='Bash',tool_input={'command':command,'description':'Record evidence'})
    output=result['hookSpecificOutput']
    self.assertNotIn('permissionDecision',output)
    self.assertEqual(output['updatedInput']['description'],'Record evidence')
    self.assertNotIn('$',output['updatedInput']['command'])
    subprocess.run(output['updatedInput']['command'],shell=True,cwd=self.tmp.name,check=True)
    self.assertEqual(self.state()['validation'],'unavailable')
  for pwd in ['"$HOME"','"$(pwd)"','"$PWD/.."','"${PWD:-/tmp}"']:
   command=base.replace('--cwd '+literal,'--cwd '+pwd)
   self.assertFalse(w.is_local_record(dict(self.data,tool_name='Bash',tool_input={'command':command})))
 def test_broad_ux_requires_user_direction_even_after_route_change(self):
  r=self.event('UserPromptSubmit',prompt='优化这个项目的使用体验。')
  self.assertTrue(self.state()['needs_clarification'])
  self.assertIn('ask the user to choose',r['hookSpecificOutput']['additionalContext'])
  self.assertEqual(self.event('PreToolUse',tool_name='Read'),{})
  subprocess.run([sys.executable,str(ROOT/'scripts/workflow.py'),'route','--cwd',self.tmp.name,'--session','test','--type','development'],check=True)
  self.assertEqual(self.event('PreToolUse',tool_name='Edit')['hookSpecificOutput']['permissionDecision'],'deny')
  self.assertEqual(self.event('PreToolUse',tool_name='Bash',tool_input={'command':'python3 app.py'})['hookSpecificOutput']['permissionDecision'],'ask')
  self.event('UserPromptSubmit',prompt='只改 README，补充现有 API 用法，不修改代码。')
  self.assertFalse(self.state()['needs_clarification'])
  self.assertEqual(self.event('PreToolUse',tool_name='Edit'),{})
 def test_explicit_scope_does_not_trigger_clarification(self):
  for prompt in ['优化使用体验：只改 README 的用法说明','Improve UX, specifically document the existing API','修复 first([])，空列表返回 None']:
   self.assertFalse(w.needs_clarification(prompt))
  self.assertTrue(w.needs_clarification('Improve the user experience'))
 def test_local_methods_are_selected_lazily(self):
  cases=[('修复 README 拼写错误',['verification']),('修复 first([]) 崩溃',['debugging','verification']),('排查登录失败',['debugging','verification']),('Review app.py',['verification']),('优化这个项目的使用体验',[])]
  for prompt,expected in cases:
   with self.subTest(prompt=prompt):
    output=self.event('UserPromptSubmit',prompt=prompt)
    self.assertEqual(self.state()['method_candidates'],expected)
    for name in expected:
     target=ROOT/'skills/workflow-router/references'/(name+'.md')
     self.assertTrue(target.is_file())
     self.assertIn(str(target),output['hookSpecificOutput']['additionalContext'])
 def test_packaged_methods_have_pinned_attribution(self):
  provenance=json.loads((ROOT/'third_party/superpowers/upstream.json').read_text())
  self.assertRegex(provenance['commit'],r'^[a-f0-9]{40}$')
  self.assertEqual(len(provenance['local_files']),2)
  for name in provenance['local_files']:self.assertTrue((ROOT/name).is_file())
  self.assertTrue((ROOT/'third_party/superpowers/LICENSE').is_file())
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
