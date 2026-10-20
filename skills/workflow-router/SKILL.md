---
name: workflow-router
description: Coordinate task routing, development, review, investigation, and evidence before completion.
---
Treat hook routing as a candidate, not a semantic decision. Use user intent and context to select the workflow. New user authorization to fix review findings changes review to development; retain prior findings. Do not switch modes merely to bypass a denial.

First inspect repository instructions, scope, constraints and acceptance criteria. For ambiguity investigate first, then ask only questions that affect the result. Broad requests such as “优化这个项目的使用体验” or “improve the user experience” do not select a direction. First inspect the code, then ask a concise question offering the material alternatives (for example documentation, errors, or UI). Wait for the user's answer before editing. A recommendation is not user authorization; do not silently choose it, broaden supported input types, or change public behavior while waiting. A route change does not resolve ambiguity. Explicitly scoped changes can proceed without this question.

Simple edits require proportionate verification; complex work needs a concrete plan.

Development: understand → inspect → plan as needed → implement → verify → deliver.
Review: read diff and callers → substantiate findings with locations and failure examples → deliver. Default read-only.
Investigation: collect evidence → hypotheses → test → distinguish confirmed root cause from uncertainty. Default read-only; ask user before invasive probes.

Shell and MCP calls use Claude Code's native permission decisions. The plugin does not force per-call confirmation or auto-approve these tools. Direct edits remain gated in read-only or pending-clarification workflows. This gate does not establish that shell/MCP calls are read-only; respect the user's scope and use read-only operations during review or investigation.

This plugin includes two local method references adapted from Superpowers, without an external dependency or startup hook. Read only the relevant reference, using the absolute method path supplied by the prompt hook (or this skill's references/ directory):
- references/debugging.md: before investigating or proposing a bug fix; skip for typo-only edits. Reuse prior root-cause evidence when switching from Review to repair.
- references/verification.md: before final completion claims or recording validation; use proportionate fresh evidence and respect forbidden execution.

Apply these local methods directly. Do not search for or invoke external superpowers:* skills as part of this workflow. No other Superpowers workflows, agents, worktrees or branch operations are imported.

Use the actual absolute CLI script path supplied by UserPromptSubmit; CLAUDE_PLUGIN_ROOT is guaranteed in hook commands, not in ordinary Bash tool calls.

- Correct routing: `python3 /absolute/plugin/scripts/workflow.py route --session SESSION --type development --cwd PROJECT`.
- Choose checks appropriate to the task. Commands are not required for every task; a content review can be sufficient for a text-only edit. Direct test/build/check results are valid evidence. Describe the scope checked and any relevant limitations honestly.
- Optional result logging: `python3 /absolute/plugin/scripts/workflow.py verify --session SESSION --cwd PROJECT -- python3 -m unittest -v test_app`. Substitute an appropriate check executable/arguments. It executes without a shell, captures stdout/stderr and exit code, and automatically records passed/failed. It supports `--timeout SECONDS` before `--`, default 120, max 600. Native permission checks remain active; do not use the wrapper to hide side effects or bypass read-only constraints.
- Optional limitation logging: `record --session SESSION --cwd PROJECT --status unavailable --evidence "specific limitation"`. Plainly explaining the limitation in the final reply is sufficient; no record command is required. record cannot accept passed or failed or replace a current executor failure with unavailable.

The Stop hook logs available results and never blocks completion for missing, stale or invalid verification records. Optional executor receipts are still checked against log integrity, task and edit revision; subsequent potentially mutating tool calls invalidate them. A missing plugin record does not mean direct tests failed or were never run. Do not repeat checks merely to create records, or edit receipts or task state. A successful process still does not prove test coverage or that the selected check was meaningful.

Lightweight events omit prompts and output. State includes bounded limitation text and verification metadata. Executor artifacts additionally retain command arguments and up to 64 KiB each of stdout/stderr; these may contain private data, so keep them local and inspect any feedback draft. No upload occurs. Use `feedback --session SESSION --cwd PROJECT` to print a redacted Issue draft, inspect it before submitting. Never submit automatically.
