#!/usr/bin/env python3
"""Local workflow coordination. Agent declarations are not independent proof."""
import argparse, contextlib, hashlib, json, os, re, sys, tempfile, time, shlex, uuid
from pathlib import Path
import fcntl
VERSION = '0.1.4'
from verification import execute, invalidate, refresh

def route(prompt):
    text = prompt.lower()
    text = re.sub(r"(?:不要|先不|禁止|不允许)\s*(?:修改|修复|开发)|do not (?:modify|fix|implement)", "", text)
    if re.search(r'修复|修改|实现|开发|fix|implement|build', text): kind = 'development'
    elif re.search(r'review|审查|审阅', text): kind = 'review'
    elif re.search(r'调查|排查|根因|investigate|debug|diagnos', text): kind = 'investigation'
    else: kind = 'general'
    complexity = 'complex' if re.search(r'复杂|架构|跨模块|迁移|architecture|migration', text) else 'simple' if re.search(r'简单|拼写|typo|rename', text) else 'medium'
    return kind, complexity

def needs_clarification(prompt):
    """Conservative guard for broad improvement requests without a chosen scope.

    This is a bounded heuristic, not proof that all other prompts are clear.
    Agent semantic clarification remains required for other material ambiguity.
    """
    text = prompt.lower()
    broad = re.search(r'优化|改善|提升|改进|improve|optimi[sz]e|make.{0,30}better', text)
    subject = re.search(r'体验|好用|易用|usability|user experience|\bux\b', text)
    # Concrete acceptance or explicit focus makes the direction reviewable.
    scoped = re.search(r'只(?:改|做|修|优化)|仅|重点|范围|验收|具体|要求|方向|例如|比如|限定|只需|scope|acceptance|specifically|only|focus|such as|for example', text)
    return bool(broad and subject and not scoped)

def method_modules(kind, prompt):
    modules = []
    symptom = re.search(r'bug|debug|排查|调查|根因|崩溃|失败|异常|修复', prompt, re.I)
    typo_only = re.search(r'拼写|typo', prompt, re.I) and not re.search(r'bug|crash|崩溃|失败|异常|根因', prompt, re.I)
    if kind == 'investigation' or (kind == 'development' and symptom and not typo_only):
        modules.append('debugging')
    if kind in ('development', 'review', 'investigation'):
        modules.append('verification')
    return modules

@contextlib.contextmanager
def state_store(cwd, session):
    root = Path(cwd).resolve()/'.workflow'
    root.mkdir(mode=0o700, exist_ok=True)
    key = hashlib.sha256(session.encode()).hexdigest()[:24]
    target = root/(key+'.json')
    with (root/(key+'.lock')).open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = json.loads(target.read_text()) if target.exists() else {}
        yield state, root
        fd, name = tempfile.mkstemp(dir=root)
        try:
            with os.fdopen(fd,'w') as out: json.dump(state,out,ensure_ascii=False)
            os.replace(name,target)
        finally:
            if os.path.exists(name): os.unlink(name)

def context(event, text):
    return {'hookSpecificOutput':{'hookEventName':event,'additionalContext':text}}

def local_record_command(data):
    """Return a literal command only for this script/session/project.

    Never emit permissionDecision=allow: native permissions still apply.
    Only quoted cwd PWD is normalized; other expansions remain unsupported.
    """
    if data.get('tool_name') != 'Bash': return None
    command = data.get('tool_input', {}).get('command', '')
    if not isinstance(command, str): return None
    # Resolve ONLY a quoted PWD used as the cwd option. No environment or shell
    # evaluation: compare the resulting literal to the trusted hook input below.
    command = re.sub(r'(?<!\S)--cwd[ \t]+"\$(?:PWD|\{PWD\})"(?=\s|$)',
                     lambda _: '--cwd ' + shlex.quote(data['cwd']), command)
    if any(c in command for c in '$`\n\r'): return None
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|<>()")
        lexer.whitespace_split = True
        lexer.commenters = ""
        args = list(lexer)
        if any(arg and all(c in ";&|<>()" for c in arg) for arg in args): return None
        if len(args) != 11 or args[0] != 'python3' or args[2] != 'record': return None
        if Path(args[1]).resolve() != Path(__file__).resolve(): return None
        pairs = list(zip(args[3::2], args[4::2]))
        options = dict(pairs)
        if len(options) != 4 or set(options) != {'--cwd','--session','--status','--evidence'}: return None
        valid = (Path(options['--cwd']).resolve() == Path(data['cwd']).resolve()
                and options['--session'] == data['session_id']
                and options['--status'] == 'unavailable'
                and bool(options['--evidence'].strip()))
        return command if valid else None
    except (ValueError, OSError):
        return None

def is_local_record(data):
    return local_record_command(data) is not None

def handle(data):
    event = data['hook_event_name']
    with state_store(data['cwd'], data['session_id']) as (s, root):
        if event == 'UserPromptSubmit':
            kind, level = route(data.get('prompt',''))
            history = s.get('history',[])
            if s: history = (history+[{'type':s.get('type'),'validation':s.get('validation')}])[-20:]
            s.clear(); s.update(task_id=uuid.uuid4().hex,revision=0,version=VERSION,type=kind,complexity=level,history=history,started=time.time(),validation='unknown',dirty=False,blocked=False,needs_clarification=needs_clarification(data.get('prompt','')),method_candidates=method_modules(kind,data.get('prompt','')))
            references = Path(__file__).resolve().parents[1] / 'skills/workflow-router/references'
            methods = ' Local method candidates: ' + ', '.join(str(references / (name + '.md')) for name in s['method_candidates']) + '. Read debugging before bug fixes; read verification before completion claims or validation records. Apply these local references, not external Superpowers skills.' if s['method_candidates'] else ''
            clarification = (' Material ambiguity: broad UX improvement without a selected scope. Inspect context with read tools first, then ask the user to choose a direction before implementation. Do not pick a direction yourself, change APIs, or treat routing as authorization. File edits are gated until a concrete user follow-up.' if s['needs_clarification'] else '')
            return context(event, f'Workflow candidate: {kind}; complexity: {level}. Read skill dynamic-workflow:workflow-router. CLI script: {Path(__file__).resolve()}. Semantic routing is your responsibility; correct the candidate with the local CLI before tools if necessary. State session: {data["session_id"]}. Prior workflow summaries: {json.dumps(history)}. Investigate context first; clarify only material ambiguities. To record real results, run python3 <CLI-script> verify --cwd <project> --session <session> -- <check argv>. The executor records exit code and output; record only accepts --status unavailable. Never treat a proposed command as a passed check.{clarification}{methods}')
        if not s: return {}
        if event == 'PreToolUse':
            tool = data.get('tool_name','')
            record_command = local_record_command(data)
            if record_command is not None:
                if record_command != data['tool_input']['command']:
                    # Resolve the supported cwd alias before native permission
                    # checking. Do not auto-approve the rewritten command.
                    updated = dict(data['tool_input'], command=record_command)
                    return {'hookSpecificOutput':{'hookEventName':event,'updatedInput':updated}}
                return {}
            if s['type'] in ('review','investigation') or s.get('needs_clarification'):
                # A shell parser cannot prove arbitrary commands read-only. Defer to native permission UI.
                if tool in ('Write','Edit','MultiEdit','NotebookEdit'):
                    return {'hookSpecificOutput':{'hookEventName':event,'permissionDecision':'deny','permissionDecisionReason':('Clarify the improvement direction with the user before editing. A route change does not clear this requirement.' if s.get('needs_clarification') else 'Read-only workflow. User must request implementation before switching to development.')}}
                if tool in ('Bash','PowerShell') or tool.startswith('mcp__'):
                    return {'hookSpecificOutput':{'hookEventName':event,'permissionDecision':'ask','permissionDecisionReason':('Pending clarification: inspect this command/tool for side effects; use read tools to investigate before asking the user.' if s.get('needs_clarification') else 'Read-only workflow: inspect this command/tool for side effects.')}}
            if tool in ('Write','Edit','MultiEdit','NotebookEdit','Bash','PowerShell') or tool.startswith('mcp__'):
                s['dirty']=True
                invalidate(s)
        if event == 'Stop':
            receipt = refresh(s, root, data['session_id'])
            if not receipt and not s.get('dirty') and s['type'] in ('review','investigation') and s['validation']=='unknown':
                s.update(validation='unavailable',validation_source='hook_no_execution',evidence='No managed verification process completed for this read-only task; static findings are not runtime verification.')
            if s.get('dirty') and s.get('validation') == 'unknown' and not data.get('stop_hook_active') and not s.get('blocked'):
                s['blocked']=True
                return {'decision':'block','reason':f'Actual verification evidence is missing. Run python3 "{Path(__file__).resolve()}" verify --cwd <project> --session <session> -- <check executable and args>. Only the executor can record passed/failed. If checks are prohibited or unavailable, use record --status unavailable --evidence "specific limitation". Do not claim unexecuted checks passed.'}
            record = {k:s.get(k) for k in ('version','type','complexity','validation','validation_source')}
            if receipt: record.update(verification_id=receipt['id'],exit_code=receipt['exit_code'],outcome=receipt['outcome'])
            record.update(duration_seconds=round(time.time()-s['started'],3),user_feedback='unknown')
            with (root/'events.jsonl').open('a') as out: out.write(json.dumps(record)+'\n')
            s['blocked']=False
        return {}

def main():
    parser=argparse.ArgumentParser()
    sub=parser.add_subparsers(dest='cmd',required=True)
    sub.add_parser('hook')
    q=sub.add_parser('verify')
    q.add_argument('--cwd',default=os.getcwd()); q.add_argument('--session',required=True)
    q.add_argument('--timeout',type=float,default=120)
    q.add_argument('command',nargs=argparse.REMAINDER)
    for name in ('record','route','feedback'):
        q=sub.add_parser(name); q.add_argument('--cwd',default=os.getcwd()); q.add_argument('--session',required=True)
        if name=='record': q.add_argument('--status',choices=['unavailable'],required=True); q.add_argument('--evidence',required=True)
        if name=='route': q.add_argument('--type',choices=['development','review','investigation','general'],required=True)
    a=parser.parse_args()
    if a.cmd=='hook':
        try: print(json.dumps(handle(json.load(sys.stdin))))
        except Exception as exc:
            print('Workflow state error: '+str(exc),file=sys.stderr); sys.exit(2)
    elif a.cmd=='verify':
        argv=a.command[1:] if a.command[:1]==['--'] else a.command
        try:
            result, streams, code = execute(a.cwd,a.session,argv,a.timeout,state_store)
        except ValueError as exc:
            parser.error(str(exc))
        for name, target in (('stdout',sys.stdout),('stderr',sys.stderr)):
            if streams[name][0]:
                print(streams[name][0].decode('utf-8',errors='replace'),file=target,end='')
        print('\n'+json.dumps({'workflow_verification':result}))
        sys.exit(code)
    else:
        with state_store(a.cwd,a.session) as (s,root):
            if not s: parser.error('No task for this session')
            if a.cmd=='record':
                if not a.evidence.strip(): parser.error('Evidence cannot be empty')
                actual = refresh(s,root,a.session)
                s['limitation']=a.evidence[:2000]
                if not actual:
                    s.update(validation='unavailable',validation_source='agent_limitation',evidence=a.evidence[:2000])
            elif a.cmd=='route':
                s['type']=a.type
                invalidate(s)
            else:
                print('## Workflow feedback\nVersion: '+VERSION+'\nType: '+s['type']+'\nValidation: '+s['validation']+'\n\n## Expected / Actual\n\n## Reproduction (redact private data)\n\n## Acceptance criteria for regression\n')
if __name__=='__main__': main()
