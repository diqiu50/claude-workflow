# Evidence before completion

Adapted from Superpowers verification-before-completion. Attribution and MIT
license: ../../../third_party/superpowers/ (relative to this directory).

Before a completion claim or a workflow record:

1. Identify what would substantiate the actual claim: a targeted test for behavior, a build for compilation, or a diff/content comparison for a text edit. Passing lint does not establish a passing build. Passing tests alone does not establish every requirement.
2. Choose an appropriate allowed check against the final artifact when needed, then read its result. Commands are not required for every task; text edits may only need content review. Direct check results are valid evidence. The local `verify --cwd PROJECT --session SESSION -- EXECUTABLE ARGS` entry point is optional result logging, using the actual script path from the hook. A proposed command, a denied tool call, or another agent's assertion is not a successful execution. Reuse fresh evidence obtained after the last relevant change; do not rerun merely to create plugin records.
3. Compare the evidence with the acceptance criteria. Report the exact scope checked and any remaining uncertainty. For a regression, establish that the test exposes the original symptom when feasible and permitted.
4. If optional logging is used, the executor records passed/failed from the real exit code; the Stop hook checks the receipt against the current task and edit revision without blocking completion. The optional `record` command accepts only unavailable with a specific reason when execution is missing/prohibited. It cannot turn a current failed execution into an unavailable or successful one. Never edit state or evidence to obtain a pass. A zero exit code establishes only that the selected command succeeded, not that coverage was sufficient.

A static Review may finish without running code: cite locations and trigger conditions and label conclusions as static. If the user forbids tests/checks, respect that and disclose unverified changes. Explaining relevant limitations in the final reply is sufficient; no logging command is required. Do not weaken permissions or change files merely to obtain a passing status. Simple edits need proportionate checks, not a full test suite.
