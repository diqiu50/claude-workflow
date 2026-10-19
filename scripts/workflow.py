#!/usr/bin/env python3
"""Local workflow coordination. Agent declarations are not independent proof."""
import argparse, contextlib, hashlib, json, os, re, sys, tempfile, time, shlex
from pathlib import Path
import fcntl
VERSION = '0.1.1'

def route(prompt):
    text = prompt.lower()
    text = re.sub(r"(?:不要|先不|禁止|不允许)\s*(?:修改|修复|开发)|do not (?:modify|fix|implement)", "", text)
    if re.search(r'修复|修改|实现|开发|fix|implement|build', text): kind = 'development'
    elif re.search(r'review|审查|审阅', text): kind = 'review'
    elif re.search(r'调查|排查|根因|investigate|debug|diagnos', text): kind = 'investigation'
    else: kind = 'general'
    complexity = 'complex' if re.search(r'复杂|架构|跨模块|迁移|architecture|migration', text) else 'simple' if re.search(r'简单|拼写|typo|rename', text) else 'medium'
    return kind, complexity

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

def is_local_record(data):
    """Exempt only a standalone record command for this script/session/project.

    Never emit permissionDecision=allow: native permissions still apply.
    Shell expansions and unquoted operators are deliberately unsupported.
    """
    if data.get('tool_name') != 'Bash': return False
    command = data.get('tool_input', {}).get('command', '')
    if not isinstance(command, str) or any(c in command for c in '$`\n\r'):
        return False
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|<>()")
        lexer.whitespace_split = True
        lexer.commenters = ""
        args = list(lexer)
        if any(arg and all(c in ";&|<>()" for c in arg) for arg in args): return False
        if len(args) != 11 or args[0] != 'python3' or args[2] != 'record': return False
        if Path(args[1]).resolve() != Path(__file__).resolve(): return False
        pairs = list(zip(args[3::2], args[4::2]))
        options = dict(pairs)
        if len(options) != 4 or set(options) != {'--cwd','--session','--status','--evidence'}: return False
        return (Path(options['--cwd']).resolve() == Path(data['cwd']).resolve()
                and options['--session'] == data['session_id']
                and options['--status'] in ('passed','failed','unavailable')
                and bool(options['--evidence'].strip()))
    except (ValueError, OSError):
        return False

def handle(data):
    event = data['hook_event_name']
    with state_store(data['cwd'], data['session_id']) as (s, root):
        if event == 'UserPromptSubmit':
            kind, level = route(data.get('prompt',''))
            history = s.get('history',[])
            if s: history = (history+[{'type':s.get('type'),'validation':s.get('validation')}])[-20:]
            s.clear(); s.update(version=VERSION,type=kind,complexity=level,history=history,started=time.time(),validation='unknown',dirty=False,blocked=False)
            return context(event, f'Workflow candidate: {kind}; complexity: {level}. Read skill dynamic-workflow:workflow-router. CLI script: {Path(__file__).resolve()}. Semantic routing is your responsibility; correct the candidate with the local CLI before tools if necessary. State session: {data["session_id"]}. Prior workflow summaries: {json.dumps(history)}. Investigate context first; clarify only material ambiguities. Never treat a proposed command as a passed check.')
        if not s: return {}
        if event == 'PreToolUse':
            tool = data.get('tool_name','')
            if is_local_record(data): return {}
            if s['type'] in ('review','investigation'):
                # A shell parser cannot prove arbitrary commands read-only. Defer to native permission UI.
                if tool in ('Write','Edit','MultiEdit','NotebookEdit'):
                    return {'hookSpecificOutput':{'hookEventName':event,'permissionDecision':'deny','permissionDecisionReason':'Read-only workflow. User must request implementation before switching to development.'}}
                if tool in ('Bash','PowerShell') or tool.startswith('mcp__'):
                    return {'hookSpecificOutput':{'hookEventName':event,'permissionDecision':'ask','permissionDecisionReason':'Read-only workflow: inspect this command/tool for side effects.'}}
            if tool in ('Write','Edit','MultiEdit','NotebookEdit','Bash','PowerShell') or tool.startswith('mcp__'):
                s.update(dirty=True,validation='unknown')
        if event == 'Stop':
            if s.get('dirty') and s.get('validation') == 'unknown' and not data.get('stop_hook_active') and not s.get('blocked'):
                s['blocked']=True
                return {'decision':'block','reason':f'Verification evidence is missing. Run an appropriate check, then record: python3 "{Path(__file__).resolve()}" record --cwd <project> --session <session> --status passed|failed|unavailable --evidence "concrete result or limitation". Report failed/unavailable checks honestly.'}
            record = {k:s.get(k) for k in ('version','type','complexity','validation')}
            record.update(duration_seconds=round(time.time()-s['started'],3),user_feedback='unknown')
            with (root/'events.jsonl').open('a') as out: out.write(json.dumps(record)+'\n')
            s['blocked']=False
        return {}

def main():
    parser=argparse.ArgumentParser()
    sub=parser.add_subparsers(dest='cmd',required=True)
    sub.add_parser('hook')
    for name in ('record','route','feedback'):
        q=sub.add_parser(name); q.add_argument('--cwd',default=os.getcwd()); q.add_argument('--session',required=True)
        if name=='record': q.add_argument('--status',choices=['passed','failed','unavailable'],required=True); q.add_argument('--evidence',required=True)
        if name=='route': q.add_argument('--type',choices=['development','review','investigation','general'],required=True)
    a=parser.parse_args()
    if a.cmd=='hook':
        try: print(json.dumps(handle(json.load(sys.stdin))))
        except Exception as exc:
            print('Workflow state error: '+str(exc),file=sys.stderr); sys.exit(2)
    else:
        with state_store(a.cwd,a.session) as (s,root):
            if not s: parser.error('No task for this session')
            if a.cmd=='record':
                if not a.evidence.strip(): parser.error('Evidence cannot be empty')
                s.update(validation=a.status,evidence=a.evidence[:2000])
            elif a.cmd=='route': s.update(type=a.type,validation='unknown')
            else:
                print('## Workflow feedback\nVersion: '+VERSION+'\nType: '+s['type']+'\nValidation: '+s['validation']+'\n\n## Expected / Actual\n\n## Reproduction (redact private data)\n\n## Acceptance criteria for regression\n')
if __name__=='__main__': main()
