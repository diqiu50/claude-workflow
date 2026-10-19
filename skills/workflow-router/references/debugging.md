# Focused debugging

Adapted from Superpowers systematic-debugging. Attribution and MIT license:
../../../third_party/superpowers/ (relative to this references directory).

Apply only to a bug, failure, or investigation. A spelling edit does not need this procedure. Keep effort proportional; an obvious failure may need only a short explanation and one focused check.

1. Inspect the exact symptom, relevant source, callers and recent changes. Reproduce with the smallest allowed example. If execution is forbidden or unavailable, use static reasoning and label the cause as inferred rather than runtime-confirmed.
2. Trace the bad value or state to its origin. Compare a nearby working case. In a multi-component failure, inspect boundaries rather than editing several layers at once. Do not print secrets while gathering evidence.
3. State one cause hypothesis and its supporting evidence. Test one variable at a time. Distinguish a failed hypothesis from a successful fix.
4. With user authorization to modify, add a focused regression where appropriate, establish failure before the fix when allowed, and make the smallest correction. Keep unrelated cleanup separate. Reuse already established investigation evidence from this conversation.
5. If attempts repeatedly fail, reassess assumptions instead of stacking patches. Ask the user only when an unresolved decision or missing access actually blocks progress.

Investigation and Review stay read-only until the user requests a fix. This method grants no permission to edit, execute invasive probes, create worktrees, delegate, commit or publish. Before claiming success, apply verification.md.
