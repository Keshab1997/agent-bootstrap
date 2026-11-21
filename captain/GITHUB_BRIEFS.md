# GitHub briefs: publish → assign → push branch → CI

The **target repo** is the source of truth for task briefs. The Captain writes
them; the worker reads them from its attached checkout (Arena lane) or downloads
them from the attached checkout. Keshab only forwards one message per worker —
never the brief text, files or tokens.

## 1. Captain: publish the brief before assigning it

- Use `captain/briefs/<batch>` in the **same GitHub repo being worked on**, not
  the public `agent-bootstrap` repo for tasks from other repos. On that branch,
  keep two files per task: `docs/agent-briefs/<batch>/<task>/BRIEF.md` and
  `docs/agent-briefs/<batch>/<task>/task.json`. Batch and task IDs use lowercase
  letters, digits and hyphens, start with a letter or digit, and are at most
  64 characters. Use a fresh task ID for every assignment or revision.
- Prepare the branch from fetched `origin/main` in a separate Captain worktree;
  if it exists, continue from its verified remote tip. Do not put briefs on
  `main`, `agent/*`, or `arena/*` refs, change app files on the docs branch, or
  merge that branch. Add new task folders; never overwrite an issued folder or
  force-push. Supersede it explicitly with a new task ID.
- Fill the [template](WORKER_BRIEF_TEMPLATE.md) and validate the JSON with
  `python3 captain/task_spec.py <task.json>`. Scope to exact, disjoint paths
  with `"arena": {"branch": "auto", "base_sha": null}` (or a verified tip when
  stacking). Add `"tracker"` only for an approved same-repo issue. For a public
  repo get approval before publishing briefs or posting comments; for a private
  repo keep the brief and tracker inside that repo.
- Stage only the two named files (or the exact list for a batch), inspect
  `git diff --cached`, and run `git diff --cached --check`. After committing,
  push only the docs ref and verify GitHub has the exact commit:

  ```bash
  set -euo pipefail
  ref="refs/heads/captain/briefs/$batch"
  test "$(git symbolic-ref HEAD)" = "$ref"
  brief_sha=$(git rev-parse HEAD)
  git -c remote.origin.mirror=false -c push.followTags=false -c http.followRedirects=false \\
    push --recurse-submodules=no origin "$brief_sha:$ref"
  test "$(git -c http.followRedirects=false ls-remote --exit-code --refs origin "$ref")" \\
    = "$(printf '%s\\t%s' "$brief_sha" "$ref")"
  ```

- Record the docs SHA in the Captain ledger and send each worker **one message**
  with the brief path, the task JSON path, its allowed files, the cheap check
  and the push/report steps. In the Arena lane the worker can read
  `docs/agent-briefs/...` straight from its checkout, so no link juggling is
  needed. The ledger keeps the docs SHA so a later audit can point at the exact
  brief commit.

## 2. Worker: read the brief

### Default: repo attached in Arena

The checkout already has the repo. Read the two files directly, no download:

```bash
git fetch origin && git switch <arena branch Arena gave you>   # never main
cat docs/agent-briefs/<batch>/<task>/BRIEF.md
cat docs/agent-briefs/<batch>/<task>/task.json
```

If the brief commit is not on your branch yet, read it by SHA
(`git fetch origin <brief_sha>` then `git show <brief_sha>:docs/agent-briefs/...`)
— do not merge the docs branch into your work.

## 3. Worker: commit, push your branch, report

- Commit only the `allowed` files and `git push origin HEAD` on your existing
  `arena/*` branch. Then report the `AGENT <W> PUSHED` block.
- A tracker mention (one `gh_app.py api POST` comment) is optional and only when
  the brief names an approved issue. Otherwise the chat report is the report.
- Never open, merge, or close a PR for notification, and never close the
  tracker issue. Never dispatch CI — that is the Captain's step after the report.

## Keep briefs fast and consistent

Follow [SPEED_POLICY.md](SPEED_POLICY.md). Select ONE cheap local check,
preferably an existing test file. Do not append “also run all related
suites/analyze/full tests” as boilerplate — CI covers the broad run. State any
genuinely required extra verification explicitly with its risk and owner
(usually Captain). New global policy never silently removes acceptance from
already-issued pinned briefs.
