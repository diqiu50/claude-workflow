# Verification executor

Since v0.1.6, verify and record are optional logging tools. Tasks may finish without running commands or creating plugin records. Direct test results are valid evidence for the final reply; missing plugin records do not imply those tests failed or never ran. Choose checks appropriate to the task and report results and relevant limitations honestly. There is no output-text heuristic or extra model judge.

When verify is used, the normal Bash tool runs the local CLI; the executor observes the real subprocess exit status and stores evidence. Stop derives the logged validation from that evidence rather than trusting an agent-supplied status, without blocking completion.

## Interface

`python3 SCRIPT verify --cwd PROJECT --session SESSION [--timeout 120] -- EXECUTABLE ARGS...`

Arguments are passed as an argv list with shell=False; no implicit shell evaluation. Native permissions still apply to the caller. Default timeout is 120 seconds, maximum 600. Choose the actual test/build/content check appropriate to the task, not a command that merely prints a success message. Inline scripts and test commands can themselves hide or omit checks; the executor cannot establish their semantic adequacy.

The executor stores a per-run UUID receipt, process outcome, exact exit code, argv, cwd, task ID, edit revision, timing and hashes of retained stdout/stderr. Each stream retains its last 64 KiB, with total byte count and truncation flag. Local verification artifacts may contain sensitive output; they are not uploaded automatically and can be removed with the task state after use. Temporary files can grow during execution before retained output is bounded.

## Status

| Observation | State |
|---|---|
| Completed with exit 0 | passed |
| Completed with nonzero exit, including signals | failed |
| Executor timeout | failed |
| Process cannot start or executor interrupted | unavailable |
| No intact matching receipt after a change | unknown |
| Read-only task ends without a managed check | unavailable, hook_no_execution |
| User limitation recorded without current actual result | unavailable, agent_limitation |

Only unavailable can be submitted through record. A limitation does not erase a current executor result. The JSON CLI summary includes accepted=false and exits nonzero when another task/check/edit superseded this run. A current failed check can be reported honestly; it does not force repeated attempts indefinitely.

## Freshness and limits

Each user prompt starts a new task ID. Potentially mutating tool attempts increment the revision and invalidate previous evidence. The state lock is released while a check runs. Only the latest active verification for the same task/revision may update validation. Stop re-reads the receipt and output hashes; missing/corrupted/stale artifacts cannot produce passed.

This tracks changes observed by the configured PreToolUse hook. External/manual modifications outside those events are not automatically detected. State, receipts and plugin source remain locally editable: this prevents accidental self-reported success, not malicious tampering by an agent able to edit the evidence system. It does not prove test selection, coverage, acceptance, or the truth of the final natural-language answer.

Normal direct test commands do not update the plugin's internal validation field, but their actual results can be reported in the final reply. Internal unknown means no current executor evidence, not that no checks were run. Never rerun completed checks merely to add a plugin record. Read/Grep and other non-mutating inspection need not invalidate an optional receipt; conservative Bash/MCP handling may invalidate it even when the command was read-only. This never requires another check to finish.

## Non-blocking completion (v0.1.6)

The v0.1.5 completion guard has been removed. Stop returns an empty JSON object after saving a summary, including when receipts are missing, stale or corrupted. It emits no recovery command or verification reminder. A real script exception still exits nonzero and is an error.

Optional receipts are still checked for freshness and integrity. Missing or invalid evidence cannot produce passed, and recording a limitation cannot overwrite a current actual failed result. Plainly explaining a relevant limitation in the final reply is sufficient; neither verify nor record is required for completion.

A successful optional record prints a short confirmation, or reports the executor status it preserved. Native permissions and read-only workflow constraints remain in effect.
