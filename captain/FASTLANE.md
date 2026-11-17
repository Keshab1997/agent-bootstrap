# Worker Fast Lane: checkpoint tasks, finalize batches

[বাংলায় শুরু করুন](HOW_TO_START_BN.md) · [Captain playbook](CAPTAIN_PROMPT.md) · [Copy a task brief](WORKER_BRIEF_TEMPLATE.md)

**An Arena-linked chat can create [one PR](https://help.arena.ai/articles/1655691990-how-to-use-coding-in-agent-mode). Merging _or closing_ it [ends GitHub pushes from that chat](https://help.arena.ai/articles/5432423882-how-to-use-agent-mode).** Fast Lane does not change that. A task checkpoint is a tested, remotely verified commit, **not** a PR. Leave a linked PR unopened where possible; if Arena has already opened one, leave it open while assigning tasks.

| Worker chat | What to do | Reuse |
|---|---|---|
| **Existing repo-linked chat that can push** | Keep its real `arena/*` branch. Publish a checkpoint for each task without merging or closing its linked PR. | The next task starts at its exact last checkpoint, if that checkout still has the dependencies it needs. |
| **Ordinary Agent Mode chat, no repo attached** | Under `~/agent-workbench`, use the worker's own authorized GitHub access and a separate `agent/A/<task>` (or B/C) branch per task. No Arena-managed PR. | Next task fetches current `main` in the same checkout. A Captain review/merge in GitHub is separate from this chat. No Arena Diff/Checks integration for this lane. |
| **Linked PR already merged/closed, or chat no longer usable** | Start fresh with the short handoff below. Do not try to push again from the old linked chat. | Only verified, pushed commits are safe to rely on for handoff. A new standalone workspace may need its own first approval. |

## 1. Once per worker workspace

Reuse the existing `/home/user/agent-bootstrap` if `gh_app.py` is present;
otherwise clone `https://github.com/Keshab1997/agent-bootstrap.git` there. Verify
its `origin` and fast-forward a clean `main` before a new batch. If `origin`
was lost, restore only that known URL; never replace a different remote or
reset local work. Do not copy credentials. Updating bootstrap must not switch
the app worktree.

- **Linked:** use the current authorized HTTPS `origin` in the attached
  app checkout (`https://github.com/Keshab1997/<repo>[.git]`). No new pairing,
  branch switch, or personal token as a workaround. Check that the chat can
  still push. If native access is unavailable, report the block to the Captain.
- **Standalone:** do not attach a repo to the worker chat. Try the workspace's
  own saved login (`python3 -B "$HOME/agent-bootstrap/gh_app.py" status` checks
  and refreshes, with no device flow). If it needs pairing, ask via the Captain
  before starting `connect --show-only`. If a code appears, Keshab approves it
  at `https://github.com/login/device`. Resume that code with
  `python3 "$HOME/agent-bootstrap/device_pair.py" poll 60`. Do not re-pair for a
  transient error. The worker's own app must already have write permission for
  the repo. No new PAT, app settings, or secret sharing is part of Fast Lane.

## 2. Per task: start → edit → check → diff → publish

Save the Captain's JSON, unchanged, at e.g. `~/agent-workbench/inbox/home-overflow-a1.json`.
For the linked case set `checkout` to the verified app checkout root (not the
bootstrap clone). For the standalone case omit `--checkout "$checkout"` on
every invocation; the tool manages one clone per worker/repo and branches
from fetched `origin/main` without modifying local `main`.

```bash
lane="$HOME/agent-bootstrap/captain/worker_lane.py"
task="$HOME/agent-workbench/inbox/home-overflow-a1.json"
# Linked example — use the actual repo root in this chat:
checkout='/path/to/attached/repository'
python3 -B "$lane" --checkout "$checkout" start "$task"
```

Use the printed `workdir`; read `AGENTS.md` if present and stick to the brief.
Never edit `main`, stage, or commit by hand for this task. Run each command
only after the previous one succeeded and inspect the full diff **before**
`publish` (they are separate steps, not a single paste):

```bash
python3 -B "$lane" --checkout "$checkout" check "$task"
python3 -B "$lane" --checkout "$checkout" diff "$task"
python3 -B "$lane" --checkout "$checkout" publish "$task"
```

The tool checks the affected paths, common credential patterns, the exact Git
tree tested, and the remote ref. Review the diff yourself: the secret check is
only a backstop. It commits exactly the allowed changes and makes a normal
push to that one task branch. No CI is dispatched, but automatic previews or
checks configured by the repo can still run. Relay the whole `AGENT A PUSHED`
block (repo, task, branch, `base_sha`, `sha`, files, check) to the Captain.

Interrupted? Keep the same task JSON, mode and checkout. Run `status` to see
the saved task, or repeat `start` if unsure. Fix check failures and re-check.
If a checked commit or push was interrupted, repeat `publish` to finish or
verify it **without** creating another commit. For wrong origin, a moved ref,
unknown dirty files, or lost access, preserve the edits and report `BLOCKED`.
If Fast Lane cannot safely adopt an in-flight manual task, finish that original
brief without changing branch or base. Never start Fast Lane over dirty work.

### Check profiles

| `check` value | Runs |
|---|---|
| `{"kind":"preflight"}` | `python3 -B tool/preflight.py`; suitable only when it covers the task |
| `{"kind":"flutter","version":"3.50.0","test":"test/home_screen_test.dart"}` | Exact named SDK, `flutter pub get --enforce-lockfile`, format changed Dart source, preflight if present, then `flutter test --no-pub` on one test file |
| `{"kind":"pytest","target":"tests"}` | `python3 -m pytest -q tests` (or one named Python test under `test/` or `tests/`) |
| `{"kind":"selftest"}` | `python3 -B selftest.py` |

Use the actual repo's gate. The Flutter version shown is an example, **not a
global default**. Pin the repo's compatible stable SDK, not just its minimum.
The locked dependency check must pass without changing manifests or lockfiles.
For another gate, use a Captain-reviewed manual brief; do not substitute an
irrelevant passing check. No builds or full test battery by default.

Flutter is skipped for non-Flutter profiles. On Linux x86-64 a cold SDK is
from Google's official manifest/archive with SHA-256 verification; a trusted
exact SDK on PATH or a valid same-version local cache is reused. The warmed
SDK and pub cache live under `/var/tmp/agent-bootstrap-flutter-<uid>`, not in
the repo. A cold download is large; Arena can discard that cache between
turns/restarts, so don't promise instant cold setup or cross-chat reuse.

## 3. Captain: verify, review, then assign the next task

1. Maintain a short ledger **outside app repos**: `repo | worker | task |
   branch | base_sha | sha | review/landed/blocked | integration_sha`. Keep
   the original brief/JSON. Assign up to three disjoint filesets in parallel,
   one live task per worker. A follow-on on the same branch waits for review.
2. In a separate verified Captain checkout, fetch and verify the exact server
   ref and scope. Use the original task JSON, not a spec generated from the
   worker's diff. Set `branch`, `base`, and `tip` from the report:

   ```bash
   python3 -B "$HOME/agent-bootstrap/captain/worker_lane.py" \
     --checkout "$captain_repo" --branch "$branch" --base "$base" --tip "$tip" \
     review "$original_task_json"
   ```

   This is a read/fetch check, not approval. Read the diff, check scope and
   secrets, and test the integration on fresh `main` before landing. Use the
   [Captain range-only integration](CAPTAIN_PROMPT.md#2d-integrate--one-reviewed-workstream-at-a-time).
   Do not make `main` point to (or merge in) the actual linked worker commits
   mid-lane. If authorized, apply only each reviewed `base_sha` → `sha` delta
   as a new Captain commit; if PRs are required, use a Captain review branch.
3. For the next linked task put the exact same branch and last verified
   pushed SHA in `arena.branch` and `arena.base_sha`. Before issuing it,
   check whether the worker lacks a required upstream interface or touches
   files changed since that tip. If so, wait or assign from fresh `main` in a
   separate checkout/chat; do not reset or rebase the attached branch. On a
   standalone lane, omit `arena`; a new slug starts at fetched `main`.

If a pushed task needs correction, don't amend it. For a safe linked branch,
issue a new corrective task from its pinned tip, mark the prior checkpoint
pending, and review the combined effect before landing anything that depends
on it. If the old branch is not safe to reuse, start at fresh `main` instead.

## 4. Finalize only when explicitly asked

**`Finalize batch <id>`** is a Captain decision, not a worker command. Freeze
new assignments, check the ledger for unpushed/blocked work, confirm the exact
remote tips and what's already landed, and show Keshab the changes to land.
Never close/merge a linked PR to mark an individual task complete. If a PR is
needed, prefer a clean Captain-owned integration branch containing only the
remaining reviewed ranges. If choosing to merge a linked PR at the end, verify
its **whole** diff against current `main`, not just the last checkpoint. It
must not include rejected, older already-landed, or unreviewed work. Get
Keshab's go-ahead for that terminal action; do not delete the worker branch.
CI dispatch remains Keshab's choice.

When a new chat is unavoidable, paste only this non-secret handoff plus its
next brief; no downloads/uploads between chats:

```text
Resume <repo> / worker <A|B|C> / <linked|standalone>.
Review base for the next task: main at <full SHA>; verify the current remote main.
Last verified checkpoint: <task> <branch> <base_sha>..<sha>; <landed at SHA | reviewed, not landed>.
Next: <one goal>; owns <exact files>; preserve <interface>; gate <profile>.
Read the current bootstrap playbook. No secrets or unfinished local files assumed.
```
