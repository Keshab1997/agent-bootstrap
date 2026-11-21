# GitHub briefs: publish → assign → push branch → CI

The **target repo** is the source of truth for task briefs. The Captain writes
them; the worker reads them from its attached checkout (Arena lane) or downloads
them with `worker_lane.py` (Option B). Keshab only forwards one message per
worker — never the brief text, files or tokens.

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
  `worker_lane.validate_task` from the current playbook. Scope to exact,
  disjoint paths. For the default Arena lane include
  `"arena": {"branch": "auto", "base_sha": null}`; for an unattached chat omit
  `"arena"` and set `"base_sha"` / `"base_branch"` when stacking. Add
  `"tracker"` only for an approved same-repo issue. For a public repo get
  approval before publishing briefs or posting comments; for a private repo keep
  the brief and tracker inside that repo.
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
  `docs/agent-briefs/...` straight from its checkout. In the Option B lane send
  the commit-pinned link instead:

  ```text
  Worker A | Repo: Keshab1997/<repo> | Brief: https://github.com/Keshab1997/<repo>/blob/<brief_sha>/docs/agent-briefs/<batch>/<task>/BRIEF.md | Use agent-bootstrap captain/WORKER_START_PROMPT.md
  ```

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

### Option B: no repo attached (Device Flow)

Pair once with `gh_app.py connect` (or `bash worker_up.sh`), then fetch and
validate the pinned brief in one command:

```bash
lane=/home/user/agent-bootstrap/captain/worker_lane.py
python3 -B "$lane" fetch-brief --url "<BRIEF_URL>" --worker <A|B|C>
```

`fetch-brief` verifies that `<brief_sha>` is an ancestor of
`refs/heads/captain/briefs/<batch>`, downloads `BRIEF.md` and `task.json` into
`~/agent-workbench/inbox/...`, validates `task.json`, and prints the exact file
paths. Read `BRIEF.md`, leave `task.json` untouched, and follow
[Fast Lane §3](FASTLANE.md#3-option-b--device-flow-repo-attach-নেই).

## 3. Worker: commit, push your branch, report

- **Arena lane:** commit only the `allowed` files and `git push origin HEAD` on
  your existing `arena/*` branch. Then report the `AGENT <W> PUSHED` block.
- **Option B:** `check` → read `diff` → `publish` pushes `agent/<W>/<task>` and
  verifies the remote SHA.
- A tracker mention (`worker_lane.py mention`, or one `gh_app.py api POST`
  comment) is optional and only when the brief names an approved issue.
  Otherwise the chat report is the report.
- Never open, merge, or close a PR for notification, and never close the
  tracker issue. Never dispatch CI — that is the Captain's step after the report.

## Keep briefs fast and consistent

Follow [SPEED_POLICY.md](SPEED_POLICY.md). Select ONE cheap local check,
preferably an existing test file. Do not append “also run all related
suites/analyze/full tests” as boilerplate — CI covers the broad run. State any
genuinely required extra verification explicitly with its risk and owner
(usually Captain). New global policy never silently removes acceptance from
already-issued pinned briefs.
