import importlib.util
import json
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('workflow_executor_test', ROOT / 'scripts/workflow.py')
w = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)
from verification import MAX_OUTPUT_BYTES, execute


class ExecutionEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cwd = self.tmp.name
        self.event('UserPromptSubmit', prompt='fix bug')

    def event(self, event, **extra):
        return w.handle(dict(cwd=self.cwd, session_id='session', hook_event_name=event, **extra))

    def state(self):
        with w.state_store(self.cwd, 'session') as (s, _):
            return dict(s)

    def check(self, source, timeout=2):
        return execute(self.cwd, 'session', [sys.executable, '-c', source], timeout, w.state_store)

    def cli(self, *args):
        return subprocess.run([sys.executable, str(ROOT / 'scripts/workflow.py'), *args,
                               '--cwd', self.cwd, '--session', 'session'], capture_output=True, text=True)

    def test_real_success_records_output_and_stop_rechecks_receipt(self):
        result, streams, code = self.check("import sys; print('3 checks OK'); print('diagnostic',file=sys.stderr)")
        self.assertEqual(code, 0)
        self.assertEqual(result['validation'], 'passed')
        self.assertIn(b'3 checks OK', streams['stdout'][0])
        self.assertIn(b'diagnostic', streams['stderr'][0])
        self.assertEqual(json.loads(Path(result['receipt']).read_text())['exit_code'], 0)
        self.assertEqual(self.state()['validation_source'], 'executor')
        self.assertEqual(self.event('Stop'), {})

    def test_nonzero_records_actual_failure_and_limitation_cannot_mask_it(self):
        result, _, code = self.check("import sys; print('FAILED'); sys.exit(7)")
        self.assertNotEqual(code, 0)
        self.assertEqual(result['exit_code'], 7)
        self.assertEqual(self.state()['validation'], 'failed')
        r = self.cli('record', '--status', 'unavailable', '--evidence', 'would like to skip')
        self.assertEqual(r.returncode, 0)
        self.assertEqual(self.state()['validation'], 'failed')
        self.event('Stop')
        log = json.loads((Path(self.cwd) / '.workflow/events.jsonl').read_text().splitlines()[-1])
        self.assertEqual(log['exit_code'], 7)
        self.assertEqual(log['validation_source'], 'executor')

    def test_manual_passed_and_failed_are_rejected(self):
        for status in ('passed', 'failed'):
            r = self.cli('record', '--status', status, '--evidence', 'model says so')
            self.assertNotEqual(r.returncode, 0)
        self.assertEqual(self.state()['validation'], 'unknown')

    def test_status_without_process_receipt_is_not_success(self):
        self.event('PreToolUse', tool_name='Edit')
        with w.state_store(self.cwd, 'session') as (s, _):
            s.update(validation='passed', validation_source='executor')
        self.assertEqual(self.event('Stop')['decision'], 'block')
        self.assertEqual(self.state()['validation'], 'unknown')

    def test_later_edit_invalidates_success(self):
        self.check('print("OK")')
        self.event('PreToolUse', tool_name='Edit')
        self.assertEqual(self.state()['validation'], 'unknown')
        self.assertEqual(self.event('Stop')['decision'], 'block')

    def test_changed_output_or_receipt_invalidates_success(self):
        for target in ('stdout', 'json'):
            result, _, _ = self.check('print("OK")')
            artifact = Path(result['receipt']).with_suffix('.' + target)
            artifact.write_text('changed')
            self.event('PreToolUse', tool_name='Read')
            self.event('Stop')
            self.assertEqual(self.state()['validation'], 'unknown')

    def test_timeout_and_missing_executable_never_pass(self):
        result, _, code = self.check('import time; time.sleep(10)', timeout=0.05)
        self.assertEqual(code, 124)
        self.assertEqual(result['outcome'], 'timeout')
        self.assertEqual(self.state()['validation'], 'failed')
        result, _, code = execute(self.cwd, 'session', ['/no/such/workflow-executable'], 1, w.state_store)
        self.assertEqual(code, 127)
        self.assertEqual(result['validation'], 'unavailable')

    def test_output_retention_is_bounded(self):
        result, _, _ = self.check('print("x" * 200000)')
        receipt = json.loads(Path(result['receipt']).read_text())
        self.assertTrue(receipt['stdout_truncated'])
        self.assertEqual(Path(result['receipt']).with_suffix('.stdout').stat().st_size, MAX_OUTPUT_BYTES)
        self.assertEqual(self.event('Stop'), {})

    def race(self, new_prompt):
        marker = Path(self.cwd) / 'started'
        results = []
        worker = threading.Thread(target=lambda: results.append(self.check(
            "from pathlib import Path; import time; Path('started').touch(); time.sleep(0.3)")))
        worker.start()
        try:
            deadline = time.monotonic() + 3
            while not marker.exists() and time.monotonic() < deadline:
                time.sleep(0.005)
            self.assertTrue(marker.exists())
            if new_prompt:
                self.event('UserPromptSubmit', prompt='implement another feature')
            else:
                self.event('PreToolUse', tool_name='Edit')
        finally:
            worker.join(timeout=5)
        self.assertFalse(worker.is_alive())
        self.assertFalse(results[0][0]['accepted'])
        self.assertEqual(results[0][2], 3)
        self.assertEqual(self.state()['validation'], 'unknown')

    def test_edit_during_check_discards_stale_result(self):
        self.race(False)

    def test_new_task_during_check_discards_stale_result(self):
        self.race(True)

    def test_static_review_without_execution_is_automatically_unavailable(self):
        self.event('UserPromptSubmit', prompt='Review app.py, do not modify')
        self.event('PreToolUse', tool_name='Read')
        self.assertEqual(self.event('Stop'), {})
        self.assertEqual(self.state()['validation'], 'unavailable')
        self.assertEqual(self.state()['validation_source'], 'hook_no_execution')
        self.assertEqual(self.event('Stop'), {})
        self.assertEqual(self.state()['validation'], 'unavailable')

    def test_cli_executes_real_command(self):
        command = [sys.executable, str(ROOT / 'scripts/workflow.py'), 'verify', '--cwd', self.cwd,
                   '--session', 'session', '--', sys.executable, '-c', 'print("real check")']
        r = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('real check', r.stdout)
        self.assertEqual(self.state()['validation'], 'passed')


if __name__ == '__main__':
    unittest.main()
