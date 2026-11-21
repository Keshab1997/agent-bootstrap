# Captain worker brief — Arena lane (default) / Device Flow (Option B)

For each new task publish both files below at
`docs/agent-briefs/<batch>/<task>/` on the target repo's `captain/briefs/<batch>`
branch, then send the worker ONE copy-paste assignment message. Use the same
task ID in the path and JSON. See [GitHub briefs](GITHUB_BRIEFS.md) for the exact
handoff and reporting steps.

## `BRIEF.md`

```markdown
# {{TASK}} — Worker {{LETTER}}

**Repository:** `Keshab1997/{{REPO}}`
**Goal:** {{one complete deliverable — a whole feature, screen or module; reuse matching tests}}
**Acceptance:**

1. {{testable result}}
2. {{testable result}}
3. {{…as many as the deliverable needs}}

**Interface / exclusions:** {{exact contracts to keep; what you must not change}}
**Branch:** stay on the `arena/*` branch this chat is bound to — never `main`,
never a new branch.
**Scope and gate:** See [task.json](task.json) at this same commit. Do not edit it.
Edit ONLY its `allowed` paths. Run ONE cheap local check —
`python3 tool/preflight.py`, or the single test named in `task.json`
(`--fail-fast`, 30s/test, 120s wall). No analyze, full suite, coverage,
screenshots or builds. Timeout → BLOCKED; two unsuccessful corrective attempts
→ stop and report the exact error, changed files and remaining acceptance.
Never bypass a failed gate.
**Deliver:** one commit with task.json's message, `git push origin HEAD`, then
reply with the `AGENT <LETTER> PUSHED` block. Do not run CI, open a PR, or
touch `main` — the Captain dispatches CI and fixes reds.
**Skill method (optional):** {{skill repo@full SHA — exact SKILL.md path — output file inside allowed list; or "none"}} — a method only; this brief and the playbook still rule.
**Report:** {{approved same-repo tracking issue URL, or worker chat (default)}}

Finish every acceptance item in this one task, deciding details yourself inside
the allowed files; if one item truly cannot be done, push the rest and name the
gap in your report.
```

## `task.json` — Arena lane (default)

```json
{
  "repo": "Keshab1997/{{REPO}}",
  "worker": "{{LETTER}}",
  "task": "{{UNIQUE_TASK_ID}}",
  "allowed": ["{{EXACT_FILE_1}}", "{{EXACT_FILE_2}}"],
  "commit": "{{type(scope): short description}}",
  "check": {{CHECK_PROFILE}},
  "arena": {"branch": "auto", "base_sha": null},
  "tracker": "https://github.com/Keshab1997/{{REPO}}/issues/{{NUM}}"
}
```

- `"arena"`: `{"branch": "auto", "base_sha": null}` for a fresh task from
  `main`; `"base_sha": "<verified arena tip>"` (same `"branch": "auto"`) when the
  task stacks on that worker's unmerged branch. Never mix with top-level
  `base_sha`/`base_branch`.
- `"tracker"`: optional approved same-repo issue URL.

## `task.json` — Option B, unattached chat

```json
{
  "repo": "Keshab1997/{{REPO}}",
  "worker": "{{LETTER}}",
  "task": "{{UNIQUE_TASK_ID}}",
  "allowed": ["{{EXACT_FILE_1}}", "{{EXACT_FILE_2}}"],
  "commit": "{{type(scope): short description}}",
  "check": {{CHECK_PROFILE}},
  "base_sha": null,
  "base_branch": null,
  "tracker": null
}
```

Omit `"arena"`; `"base_sha": null` starts from current `origin/main`, or a full
40-hex SHA (with `"base_branch": "agent/{{LETTER}}/{{PREV_TASK}}"` when it is not
merged) chains onto a verified checkpoint.

## The assignment message (what the worker actually sees)

```text
You are Worker {{LETTER}} on Keshab1997/{{REPO}}.
Brief: docs/agent-briefs/{{BATCH}}/{{TASK}}/BRIEF.md
Spec:  …/task.json   (allowed = your only scope; check = your only gate)
Read captain/WORKER_START_PROMPT.md and BRIEF.md, then:
  · edit ONLY the allowed paths, stay on your arena/* branch
  · run the one check from task.json
  · git add -- <allowed files> && git commit -m "<task.json commit>" && git push origin HEAD
Reply with the AGENT {{LETTER}} PUSHED block. Never main, CI, or a PR.
```

**Captain:** Size every brief by [Speed rule 1](CAPTAIN_PROMPT.md#speed-rules--keshabs-top-priority):
one complete deliverable, up to 40 allowed files — never a micro-task.
Never assign the brief files as worker scope, and never confuse the docs commit
SHA in the permalink with the code `base_sha`. See [examples](examples/). Preserve
the original JSON and lane for work already in flight; do not migrate it mid-task.
