# Captain worker brief — GitHub Fast Lane

For each new task publish both files below at
`docs/agent-briefs/<batch>/<task>/` on the target repo's `captain/briefs/<batch>`
branch. Use the same task ID in the path and JSON. Share only the pinned
`BRIEF.md` link and the Arena attach instruction after verifying the push. See
[GitHub briefs](GITHUB_BRIEFS.md) for the exact handoff and reporting steps.

## `BRIEF.md`

```markdown
# {{TASK}} — Worker {{LETTER}}

**Repository:** `Keshab1997/{{REPO}}` — attach this repo in Arena Agent Mode.
**Goal and acceptance:** {{one testable result}}
**Interface / exclusions:** {{exact contracts to keep; what you must not change}}
**Scope and gate:** See [task.json](task.json) at this same commit. Do not edit it.
**Report:** {{approved same-repo tracking issue URL + @Keshab1997, or worker chat (GitHub mention pending)}}

Use the current agent-bootstrap `captain/FASTLANE.md`. Keep the real `arena/*`
branch. After a verified `PUSHED`, include the brief link, checkpoint block
and commit link when reporting. If blocked, report the reason; do not change
branch, use a standalone clone, re-pair, run CI, or open/merge/close a PR.
```

## `task.json`

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

**Captain:** New briefs always include `arena`. For a first task, use the
actual branch when known. Use `auto` or `null` only on a clean first task whose
attached `HEAD` equals current remote `main`; prefer a full pinned code base
SHA when known. For each later task use the exact `arena/*` branch and full
Captain-verified pushed SHA of the last task. Don't confuse the docs commit
SHA in the permalink with the code base SHA. Don't assign the brief files as
worker scope. See [examples](examples/). Preserve the original JSON and lane
for work already in flight; do not migrate it mid-task.
