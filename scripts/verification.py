"""Execute checks and retain process evidence. No model-supplied success status."""
import hashlib
import json
import math
import os
import re
import shlex
import signal
import subprocess
import tempfile
import time
import uuid
from pathlib import Path

MAX_OUTPUT_BYTES = 65536


def invalidate(state, tool=None):
    state['last_invalidation'] = {
        'tool': tool or 'workflow route change',
        'previous_validation': state.get('validation', 'unknown'),
        'had_executor_receipt': bool(state.get('verification')),
    }
    state['revision'] = state.get('revision', 0) + 1
    state.update(validation='unknown', validation_source=None, verification=None,
                 active_verification=None)


def _digest(data):
    return hashlib.sha256(data).hexdigest()


def refresh(state, root, session):
    """The Stop hook derives status from matching, intact executor artifacts."""
    reference = state.get('verification')
    if not reference:
        if not (state.get('validation_source') in ('agent_limitation', 'hook_no_execution')
                and state.get('validation') == 'unavailable'):
            state.update(validation='unknown', validation_source=None)
        state['verification_problem']='No current managed verification receipt.'
        return None
    try:
        run_id = reference['id']
        if not re.fullmatch(r'[a-f0-9]{32}', run_id):
            raise ValueError('invalid verification id')
        base = root / 'verification'
        raw = (base / (run_id + '.json')).read_bytes()
        if _digest(raw) != reference['sha256']:
            raise ValueError('receipt changed')
        receipt = json.loads(raw)
        if (receipt['task_id'] != state.get('task_id')
                or receipt['revision'] != state.get('revision')
                or receipt['session_key'] != _digest(session.encode())
                or receipt['id'] != run_id):
            raise ValueError('stale or different task/session')
        for stream in ('stdout', 'stderr'):
            data = (base / (run_id + '.' + stream)).read_bytes()
            if _digest(data) != receipt[stream + '_sha256']:
                raise ValueError('output changed')
        if receipt['outcome'] == 'completed':
            status = 'passed' if receipt['exit_code'] == 0 else 'failed'
        elif receipt['outcome'] == 'timeout':
            status = 'failed'
        elif receipt['outcome'] in ('spawn_error', 'interrupted'):
            status = 'unavailable'
        else:
            raise ValueError('incomplete verification')
        state.pop('verification_problem', None)
        state.update(validation=status, validation_source='executor',
                     evidence=(shlex.join(receipt['argv']) + ': ' +
                               receipt['outcome'] + ', exit=' +
                               str(receipt['exit_code']))[:2000])
        return receipt
    except (OSError, ValueError, KeyError, TypeError) as exc:
        state['verification_problem']='Verification receipt is missing, stale, or changed: ' + str(exc)[:300]
        state.update(validation='unknown', validation_source=None)
        return None


def _atomic_write(path, data):
    fd, name = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as output:
            output.write(data)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def _stop_process(process):
    if process.poll() is None:
        try:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
        except ProcessLookupError:
            process.wait()


def execute(cwd, session, argv, timeout, store):
    if not argv or not all(isinstance(arg, str) for arg in argv) or not argv[0]:
        raise ValueError('verify needs an executable and arguments after --')
    if not math.isfinite(timeout) or not 0 < timeout <= 600:
        raise ValueError('timeout must be greater than 0 and at most 600 seconds')
    cwd = str(Path(cwd).resolve())
    run_id = uuid.uuid4().hex
    with store(cwd, session) as (state, root):
        if not state or not state.get('task_id'):
            raise ValueError('No current task; submit a user prompt first')
        task_id, revision = state['task_id'], state['revision']
        state.update(active_verification=run_id, verification=None,
                     validation='unknown', validation_source=None)
    base = root / 'verification'
    base.mkdir(mode=0o700, exist_ok=True)
    started = time.time()
    outcome, exit_code, error = 'completed', None, None
    captured = {}
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        process = None
        try:
            process = subprocess.Popen(argv, cwd=cwd, stdin=subprocess.DEVNULL,
                                       stdout=stdout, stderr=stderr,
                                       start_new_session=True)
            exit_code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            outcome = 'timeout'
            _stop_process(process)
            exit_code = process.returncode
        except (OSError, ValueError) as exc:
            outcome, error = 'spawn_error', str(exc)
        except KeyboardInterrupt:
            outcome = 'interrupted'
            if process is not None:
                _stop_process(process)
                exit_code = process.returncode
        for name, stream in (('stdout', stdout), ('stderr', stderr)):
            size = stream.seek(0, os.SEEK_END)
            stream.seek(max(0, size - MAX_OUTPUT_BYTES))
            captured[name] = (stream.read(), size)
    receipt = dict(id=run_id, task_id=task_id, revision=revision,
                   session_key=_digest(session.encode()), cwd=cwd, argv=argv,
                   started_at=started, finished_at=time.time(),
                   duration_seconds=round(time.time() - started, 3),
                   outcome=outcome, exit_code=exit_code, error=error)
    for name, (data, size) in captured.items():
        _atomic_write(base / (run_id + '.' + name), data)
        receipt[name + '_sha256'] = _digest(data)
        receipt[name + '_bytes'] = size
        receipt[name + '_truncated'] = size > len(data)
    raw = json.dumps(receipt, ensure_ascii=False).encode()
    _atomic_write(base / (run_id + '.json'), raw)
    with store(cwd, session) as (state, root):
        accepted = (state.get('task_id') == task_id
                    and state.get('revision') == revision
                    and state.get('active_verification') == run_id)
        if accepted:
            state.update(active_verification=None,
                         verification={'id': run_id, 'sha256': _digest(raw)})
            refresh(state, root, session)
        status = state.get('validation', 'unknown')
    result = dict(id=run_id, accepted=accepted, validation=status,
                  outcome=outcome, exit_code=exit_code,
                  receipt=str(base / (run_id + '.json')))
    # Preserve failure at the CLI, including non-starts/timeouts and stale runs.
    code = (0 if exit_code == 0 else 1) if outcome == 'completed' else {
        'timeout': 124, 'spawn_error': 127, 'interrupted': 130}[outcome]
    if not accepted:
        code = 3
    return result, captured, code
