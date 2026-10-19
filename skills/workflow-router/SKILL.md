---
name: workflow-router
description: Coordinate task routing, development, review, investigation, and evidence before completion.
---
Treat hook routing as a candidate, not a semantic decision. Use user intent and context to select the workflow. New user authorization to fix review findings changes review to development; retain prior findings. Do not switch modes merely to bypass a denial.

First inspect repository instructions, scope, constraints and acceptance criteria. For ambiguity investigate first, then ask only questions that affect the result. Simple edits require proportionate verification; complex work needs a concrete plan.

Development: understand → inspect → plan as needed → implement → verify → deliver.
Review: read diff and callers → substantiate findings with locations and failure examples → deliver. Default read-only.
Investigation: collect evidence → hypotheses → test → distinguish confirmed root cause from uncertainty. Default read-only; ask user before invasive probes.

When installed, reuse Superpowers brainstorming/writing-plans for complex development, systematic-debugging for investigation, requesting-code-review when appropriate, and verification-before-completion. Discover available skills; do not assume Superpowers exists, copy its implementation, or delegate without authorization. If absent follow the workflows above.

CLI: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/workflow.py" route --session SESSION --type development --cwd PROJECT` corrects routing. `record --session SESSION --cwd PROJECT --status passed|failed|unavailable --evidence "actual result or specific limitation"` records agent-reported evidence. A PreToolUse event is an attempt, never evidence of success. Record after the last potentially mutating tool. Never fabricate passed checks. Evidence is a declaration, not independently verified proof. Mention limitations in the final answer.

Local logs omit prompts, code, commands and evidence text. State includes bounded agent evidence; avoid secrets. No upload occurs. Use `feedback --session SESSION --cwd PROJECT` to print a redacted Issue draft, inspect it before submitting. Never submit automatically.
