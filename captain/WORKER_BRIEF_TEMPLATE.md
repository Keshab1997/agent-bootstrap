# Captain worker brief — Fast Lane

Copy the block below. Fill all fields. Give each worker one task at a time and
one exclusive set of paths. Use a new `task` ID for the next task; leave the
original JSON unchanged on resume. See [profiles and examples](FASTLANE.md).
For an in-flight pre-Fast-Lane task, keep its [original workflow](LEGACY_WORKER_BRIEF.md).

✂ ────────────────── COPY FROM HERE ──────────────────

**Goal and acceptance:** {{one testable result}}

**Interface / exclusions:** {{exact contracts to keep; what you must not change}}

```json
{
  "repo": "Keshab1997/{{REPO}}",
  "worker": "{{LETTER}}",
  "task": "{{UNIQUE_TASK_ID}}",
  "allowed": ["{{EXACT_FILE_1}}", "{{EXACT_FILE_2}}"],
  "commit": "{{type(scope): short description}}",
  "check": {{CHECK_PROFILE}},
  "arena": {"branch": "{{ARENA_BRANCH}}", "base_sha": {{BASE_SHA_OR_NULL}}}
}
```

**Worker:** Read `captain/FASTLANE.md` from your verified bootstrap clone. Save
the JSON under `~/agent-workbench/inbox/`, outside the app repo. Use the lane's
`start` → read repo `AGENTS.md` → edit only `allowed` → `check` → inspect `diff`
→ `publish` sequence. Report the tool's `AGENT … PUSHED` block and one line about
what changed, or `AGENT … BLOCKED` with the exact problem. No `main`, PR, CI
manual run, force-push, branch deletion, or credential sharing. Wait for a new
Captain brief before starting another task. For a linked chat stay on its
actual `arena/*` branch; never try to revive a terminal chat.

✂ ────────────────── COPY ENDS HERE ───────────────────

**Captain:** For a first linked task, use `"auto"` (or the real branch) and
`null` only if the attached branch's HEAD equals current remote `main`. For
later linked tasks use the **exact branch** and the full **Captain-verified
pushed SHA** of the last task as `base_sha`.
For an ordinary chat with **no repo attached**, omit the entire `arena` field
and its preceding comma. Standalone uses a new branch from fetched `main`.
