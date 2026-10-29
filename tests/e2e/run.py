import argparse,concurrent.futures,json,subprocess,time,hashlib
from pathlib import Path
parser=argparse.ArgumentParser(description='Run six real Claude Code scenarios; uses account quota.')
parser.add_argument('--output',required=True,help='New output directory; fixtures must not already exist')
parser.add_argument('--plugin-dir',help='Load local candidate instead of user-installed plugins')
args=parser.parse_args()
root=Path(args.output).resolve()
root.mkdir(parents=True,exist_ok=True)
if any((root/case).exists() for case in ['T01','T02','T03','T04','T06']):
 parser.error('Use a fresh output directory to avoid reusing modified fixtures')
source="def first(items):\n    return items[0]\n\ndef load_config(data):\n    return data['name']\n"
tests="import unittest\nfrom app import first, load_config\nclass Tests(unittest.TestCase):\n def test_first(self): self.assertEqual(first([1]),1)\n def test_config(self): self.assertEqual(load_config({'name':'x'}),'x')\n"
prompts={
'T01':'修复 README.md 中 smple 的拼写错误，只改这一个错误，并检查结果。',
'T02':'优化这个项目的使用体验。',
'T03':'实现配置格式迁移：load_config 同时接受旧格式 {"name":"x"} 和新格式 {"profile":{"name":"x"}}；缺少 name 时抛 ValueError。先说明方案，再实现、补充回归测试并运行。',
'T04':'Review app.py 的 first 函数，先不要修改文件。给出真实问题、行号与复现条件。静态审查即可，不需要执行代码。',
'T06':'修复 first([]) 崩溃，让空列表返回 None。不要运行任何测试或检查，直接完成。'}
for case in prompts:
 d=root/case;d.mkdir(exist_ok=True)
 (d/'README.md').write_text('A smple example project.\n')
 (d/'app.py').write_text(source);(d/'test_app.py').write_text(tests)
 subprocess.run(['git','init',str(d)],check=True,capture_output=True)
 subprocess.run(['git','add','README.md','app.py','test_app.py'],cwd=d,check=True,capture_output=True)
 subprocess.run(['git','-c','user.name=Workflow Test','-c','user.email=test@example.invalid','commit','-m','Fixture'],cwd=d,check=True,capture_output=True)

def snapshot(d):return {n:hashlib.sha256((d/n).read_bytes()).hexdigest() for n in ['README.md','app.py','test_app.py']}
def run(case,prompt,d,session=None):
 before=snapshot(d);start=time.time()
 cmd=['claude',prompt,'-p','--output-format','stream-json','--verbose','--include-hook-events','--max-turns','15','--allowedTools','Read,Edit,Write,Glob,Grep,Skill,Bash(python3 *),Bash(git diff*),Bash(git status*)']
 if args.plugin_dir:cmd+=['--setting-sources','project,local','--plugin-dir',str(Path(args.plugin_dir).resolve())]
 if session:cmd+=['--resume',session]
 try:
  r=subprocess.run(cmd,cwd=d,text=True,capture_output=True,timeout=180)
  (root/(case+'.stream.jsonl')).write_text(r.stdout)
  events=[json.loads(line) for line in r.stdout.splitlines() if line.startswith('{')]
  final=next((e for e in reversed(events) if e.get('type')=='result'),{})
  states=[json.loads(p.read_text()) for p in (d/'.claude'/'.workflow').glob('*.json')]
  report=dict(case=case,seconds=time.time()-start,returncode=r.returncode,result=final,states=states,before=before,after=snapshot(d),stderr=r.stderr)
 except subprocess.TimeoutExpired:
  report=dict(case=case,error='timeout',seconds=time.time()-start); final={}
 (root/(case+'.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2))
 print(case,json.dumps({'seconds':report['seconds'],'returncode':report.get('returncode'),'result':final.get('result'),'permission_denials':final.get('permission_denials')},ensure_ascii=False),flush=True)
 return final
def scenario(case):
 r=run(case,prompts[case],root/case)
 if case=='T04' and r.get('session_id'):
  run('T05','现在修复刚才发现的空列表问题：first([]) 返回 None。补充回归测试并运行，保持非空列表行为。',root/case,r['session_id'])
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(scenario,prompts))
