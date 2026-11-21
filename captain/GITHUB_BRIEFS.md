# GitHub briefs: publish → fetch → checkpoint → mention

The **target repo** is the source of truth for task briefs. Keshab forwards a
one-line launch link, not the brief itself. The Captain publishes docs;
Device-Flow workers fetch them via `worker_lane.py fetch-brief`, work in an
isolated clone on `agent/<W>/<task>`, push, and post `@Keshab1997` via
`worker_lane.py mention`.

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
  merge that branch for workers to see it. Add new task folders; never overwrite
  an issued folder or force-push. Supersede it explicitly with a new task ID.
- Fill the [template](WORKER_BRIEF_TEMPLATE.md) and validate the JSON with
  `worker_lane.validate_task` from the current playbook. Scope to exact,
  disjoint paths. For Device Flow tasks (default), omit `"arena"`; set
  `"base_sha"` / `"base_branch"` when chaining onto an unmerged checkpoint,
  and `"tracker"` to an approved same-repo issue URL when available. For a
  public repo get approval before publishing briefs or posting comments; for a
  private repo keep the brief and tracker inside that repo.
- Stage only the two named files (or the exact list for a batch), inspect
  `git diff --cached`, and run `git diff --cached --check`. After committing,
  push only the docs ref and verify GitHub has the exact commit:

  ```bash
  set -euo pipefail
  ref="refs/heads/captain/briefs/$batch"
  test "$(git symbolic-ref HEAD)" = "$ref"
  brief_sha=$(git rev-parse HEAD)
  git -c remote.origin.mirror=false -c push.followTags=false -c http.followRedirects=false \
    push --recurse-submodules=no origin "$brief_sha:$ref"
  test "$(git -c http.followRedirects=false ls-remote --exit-code --refs origin "$ref")" \
    = "$(printf '%s\t%s' "$brief_sha" "$ref")"
  ```

- Record the exact docs SHA and GitHub permalink in the Captain ledger. Send
  Keshab one launch line per worker using the full commit SHA:

  ```text
  Worker A | Repo: Keshab1997/<repo> | Brief: https://github.com/Keshab1997/<repo>/blob/<brief_sha>/docs/agent-briefs/<batch>/<task>/BRIEF.md | Use agent-bootstrap captain/FASTLANE.md
  ```

## 2. Worker: fetch the pinned brief

### Primary: Device Flow (no Arena repo attachment required)

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
[Fast Lane §3](FASTLANE.md#3-per-task-start--edit--check--diff--publish--mention).

### Optional: Arena-attached mode (only when `"arena"` is in `task.json`)

If a chat already has the target repo attached in Arena Agent Mode and the
brief uses `"arena"`, materialize the brief from the attached checkout using
`git cat-file blob` (without changing `HEAD` or touching `origin`) and pass
`--checkout "$checkout"` to `worker_lane.py`.

## 3. Worker: report and mention only after verification

- Run `check`, inspect `diff`, and run `publish` to push `agent/<W>/<task>`
  (or `arena/*` in optional linked mode) and get the `AGENT A/B/C PUSHED` block.
- If `task.json` has `"tracker"` (or the brief names an approved tracking issue):

  ```bash
  python3 -B "$lane" mention "$task" --brief-url "<BRIEF_URL>"
  ```

  `mention` posts `@Keshab1997 — checkpoint ready for review` with the brief
  link, commit link, and `PUSHED` block using `gh_app.py` (skipping duplicates
  automatically). If there is no tracker or comment access is unavailable,
  return the `PUSHED` block and commit link in chat with `MENTION PENDING`.
- Never open, merge, or close a PR for notification, and never close the tracker issue.
