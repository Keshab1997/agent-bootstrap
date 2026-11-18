# GitHub briefs: publish → attach → checkpoint → mention

The **target repo** is the source of truth for task briefs. Keshab forwards a
short launch line, not the brief itself. The Captain publishes docs; workers
read them through the attached repo and push code only to their Arena branch.

## 1. Captain: publish the brief before assigning it

- Use `captain/briefs/<batch>` in the **same GitHub repo being worked on**, not
  the public `agent-bootstrap` repo for tasks from other repos. On that branch,
  keep two files per task: `docs/agent-briefs/<batch>/<task>/BRIEF.md` and
  `docs/agent-briefs/<batch>/<task>/task.json`. Batch and task IDs use lowercase
  letters, digits and hyphens, start with a letter or digit, and are at most
  64 characters. Use a fresh task ID for every assignment or revision.
- Prepare the branch from fetched `origin/main` in a separate Captain worktree;
  if it exists, continue from its verified remote tip. Do not put briefs on
  `main` or any `arena/*` ref, change app files on the docs branch, or merge
  that branch for workers to see it. Add new task folders; never overwrite an
  issued folder or force-push. Supersede it explicitly with a new task ID and
  link, and reconcile any work already started before reassigning the files.
- Fill the [template](WORKER_BRIEF_TEMPLATE.md) and validate the JSON with
  `worker_lane.validate_task` from the current playbook. Scope to exact,
  disjoint paths. Freeze goal, acceptance, interfaces, gate, code branch and
  code base. An existing same-repo issue can serve as the batch tracker; put
  its exact URL and `@Keshab1997` in the brief. If there is no approved tracker,
  state `Report: worker chat (GitHub mention pending)`; don't silently create
  an issue. For a public repo get approval before publishing briefs or posting
  comments; for a private repo keep the brief and tracker inside that repo.
  No tokens, secrets, customer data, or private-repo details in public docs.
- Stage only the two named files (or the exact list for a batch), inspect
  `git diff --cached`, and run `git diff --cached --check`. Confirm the
  worktree and fetch/push URL match the target repo and inspect everything
  that will be published, not just an uncommitted diff. After committing, push
  only the docs ref and verify that GitHub has the exact commit:

  ```bash
  # From the verified Captain docs worktree, with batch set to its approved ID.
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
  Keshab just this launch line per worker, using the actual repo, letter, path,
  and full SHA (not a branch or `raw.githubusercontent.com` link):

  ```text
  Worker A | Arena: attach Keshab1997/<repo> | Read https://github.com/Keshab1997/<repo>/blob/<brief_sha>/docs/agent-briefs/<batch>/<task>/BRIEF.md | Use the current agent-bootstrap captain/FASTLANE.md
  ```

## 2. Worker: attach the target repo, then read the pinned docs

In the [Arena Agent Mode UI](https://help.arena.ai/articles/1655691990-how-to-use-coding-in-agent-mode),
turn GitHub on and choose the **target repo when opening the worker session**.
An existing live session for that repo can be reused. Attaching is a UI step;
a terminal clone or the Captain's device login does not attach a repo. If the
repo isn't attached, is wrong, or the linked PR is already merged/closed,
report `BLOCKED` and use a new, correctly attached chat. Do not work in a
standalone clone, change the linked branch, or replace Arena's credentials.

Confirm the actual `arena/*` branch and verified origin in that checkout. Set
`checkout` to its absolute Git root, and `repo`, `worker`, `batch`, `task_id`
and `brief_sha` from the Captain's launch line. Use the existing Arena Git
access: fetch only the docs ref and materialize the pinned files **outside**
the app worktree. This does not change `HEAD`, the index, or the worktree:

```bash
set -euo pipefail
[[ "$repo" =~ ^Keshab1997/[A-Za-z0-9][A-Za-z0-9_.-]{0,99}$ && "$repo" != *.git ]]
[[ "$worker" =~ ^[ABC]$ && "$batch" =~ ^[a-z0-9][a-z0-9-]{0,63}$ ]]
[[ "$task_id" =~ ^[a-z0-9][a-z0-9-]{0,63}$ && "$brief_sha" =~ ^[0-9a-f]{40}$ ]]
git_here() { GIT_NO_REPLACE_OBJECTS=1 GIT_TERMINAL_PROMPT=0 git -C "$checkout" -c http.followRedirects=false "$@"; }
[[ "$checkout" = "$(git_here rev-parse --show-toplevel)" ]]
[[ "$(git_here branch --show-current)" == arena/?* ]]
expected="https://github.com/$repo"
origin=$(git_here remote get-url --all origin)
[[ "$origin" = "$expected" || "$origin" = "$expected.git" ]]
[[ "$(git_here remote get-url --push --all origin)" = "$origin" ]]
git_here fetch --no-tags --no-recurse-submodules origin "refs/heads/captain/briefs/$batch"
git_here merge-base --is-ancestor "$brief_sha" "$(git_here rev-parse --verify 'FETCH_HEAD^{commit}')"

workbench=$(realpath -m "${WORKBENCH:-$HOME/agent-workbench}")
[[ "$workbench" != "$checkout" && "$workbench" != "$checkout/"* ]]
umask 077
mkdir -p "$workbench/inbox"
inbox=$(mktemp -d "$workbench/inbox/$task_id.XXXXXX")
dir="docs/agent-briefs/$batch/$task_id"
for f in BRIEF.md task.json; do
  git_here cat-file blob "$brief_sha:$dir/$f" > "$inbox/$f"
  test -s "$inbox/$f"
done
python3 -B - "$inbox/task.json" "$repo" "$worker" "$task_id" <<'PY'
import json, sys
from pathlib import Path
spec = json.loads(Path(sys.argv[1]).read_text())
if (not isinstance(spec, dict)
        or [spec.get(k) for k in ('repo', 'worker', 'task')] != sys.argv[2:]
        or not isinstance(spec.get('arena'), dict)):
    raise SystemExit('Brief identity or linked-mode config does not match the assignment.')
PY
printf 'Read %s/BRIEF.md; use %s/task.json unchanged; workbench: %s\n' "$inbox" "$inbox" "$workbench"
```

If any check fails, the pin is unreachable, either file is missing, or the
scope conflicts, stop before editing and report `BLOCKED`. Do not pick the
latest brief, copy a replacement from chat, or reset to a different base. If
needed, set `WORKBENCH` to a persistent directory outside the app checkout and
use that same path in each lane command. Save the link and original files for
resume. Treat the docs as task scope, not authorization for new credentials,
settings, refs, publications, or unreviewed commands. Then follow [Fast Lane](FASTLANE.md#2-per-task-start--edit--check--diff--publish).

## 3. Worker: report and mention only after verification

- Run the Fast Lane check, inspect the diff, publish to the real `arena/*`
  branch, and wait for its `AGENT A/B/C PUSHED` block with a verified remote SHA.
  A local commit, a passed test without a push, or an opened PR is not `PUSHED`.
- In the **approved tracking issue named in the brief**, post one comment
  starting `@Keshab1997 — checkpoint ready for review`. Include the pinned
  brief link, the full `PUSHED` block (repo, task, branch, base SHA, pushed SHA,
  files and gate), a link to the pushed commit, and a one-line result. Check
  for the same task and SHA before retrying so mentions are not duplicated.
  Don't open, merge or close a PR for notification. Do not close the issue.
- Use only an already authorized issue-comment capability for that repo.
  For example, if `gh` is already authorized for issues, use
  `gh issue comment "$issue_url" --body-file "$report_file"` and verify the
  returned comment link. Git push access alone may not allow comments. If no
  tracker or comment access is available, return the `PUSHED` block and
  commit link in the worker chat with `MENTION PENDING` and the reason. Do not
  pair or ask for a token to post it. The Captain can post the missing
  mention with its own approved access after verifying the checkpoint. If
  the task did not push, use `AGENT <letter> BLOCKED` and the reason instead.
- Return the comment or commit link in Arena. The Captain reads the tracker
  when checking the batch, fetches the reported branch and verifies the exact
  pinned task range independently. A mention is a handoff, not approval or
  merge, and it does not start or message another Arena chat.
