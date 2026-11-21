# Captain worker brief — GitHub Fast Lane

For each new task publish both files below at
`docs/agent-briefs/<batch>/<task>/` on the target repo's `captain/briefs/<batch>`
branch. Use the same task ID in the path and JSON. Share only the one-line
launch link after verifying the push. See [GitHub briefs](GITHUB_BRIEFS.md) for
the exact handoff and reporting steps.

## `BRIEF.md`

```markdown
# {{TASK}} — Worker {{LETTER}}

**Repository:** `Keshab1997/{{REPO}}`
**Goal:** {{one complete deliverable — a whole feature, screen or module with its tests}}
**Acceptance:**

1. {{testable result}}
2. {{testable result}}
3. {{…as many as the deliverable needs}}

**Interface / exclusions:** {{exact contracts to keep; what you must not change}}
**Scope and gate:** See [task.json](task.json) at this same commit. Do not edit it.
**Skill method (optional):** {{skill repo@full SHA — exact SKILL.md path — output file inside allowed list; or "none"}} — a method only; this brief and the playbook still rule.
**Report:** {{approved same-repo tracking issue URL + @Keshab1997, or worker chat (no tracker)}}

Finish every acceptance item in this one task, deciding details yourself inside
the allowed files; if one item truly cannot be done, push the rest and name the
gap in your report. Use `agent-bootstrap` `captain/FASTLANE.md` (`worker_lane.py`).
After a verified `PUSHED`, run `mention` (if `tracker` is set) and report the
brief link, checkpoint block, and commit/mention links. Never touch `main`, open/merge/close
a PR, run CI, or share tokens.
```

## `task.json` (Device Flow — primary)

```json
{
  "repo": "Keshab1997/{{REPO}}",
  "worker": "{{LETTER}}",
  "task": "{{UNIQUE_TASK_ID}}",
  "allowed": ["{{EXACT_FILE_1}}", "{{EXACT_FILE_2}}"],
  "commit": "{{type(scope): short description}}",
  "check": {{CHECK_PROFILE}},
  "base_sha": null,
  "tracker": "https://github.com/Keshab1997/{{REPO}}/issues/{{NUM}}"
}
```

Optional fields in Device Flow mode:
- `"base_sha"`: `null` (or omit) to start from current `origin/main`; or a full 40-hex SHA to pin `main` or chain onto a prior verified checkpoint.
- `"base_branch"`: optional branch holding `"base_sha"` (e.g. `"agent/{{LETTER}}/{{PREV_TASK}}"` when stacking on an unmerged checkpoint).
- `"tracker"`: optional approved same-repo GitHub issue URL for `worker_lane.py mention`.

Optional Arena-attached mode: omit top-level `"base_sha"` / `"base_branch"` and include `"arena": {"branch": "{{ARENA_BRANCH}}", "base_sha": {{BASE_SHA_OR_NULL}}}` instead.

**Captain:** Size every brief by [Speed rule 1](CAPTAIN_PROMPT.md#speed-rules--keshabs-top-priority):
one complete deliverable, up to 40 allowed files — never a micro-task.
Never assign the brief files as worker scope, and never confuse the docs commit
SHA in the permalink with the code `base_sha`. See [examples](examples/). Preserve
the original JSON and lane for work already in flight; do not migrate it mid-task.
