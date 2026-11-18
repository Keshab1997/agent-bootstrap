# Worker Fast Lane: GitHub brief → Arena checkpoint

[বাংলায় শুরু করুন](HOW_TO_START_BN.md) · [GitHub briefs](GITHUB_BRIEFS.md) · [Captain playbook](CAPTAIN_PROMPT.md)

**New Captain workers must attach the target repo in Arena Agent Mode.** The
Captain publishes briefs in that repo's GitHub docs, not in chat. An
[Arena-linked chat can create one PR](https://help.arena.ai/articles/1655691990-how-to-use-coding-in-agent-mode);
merging or closing it [ends GitHub pushes from that chat](https://help.arena.ai/articles/5432423882-how-to-use-agent-mode).
A task checkpoint is a tested, remotely verified commit, **not** a PR.

| Worker chat | Action |
|---|---|
| Live linked chat, correct target repo | Keep its actual `arena/*` branch and native access. Wait for Captain review before the next pinned task. |
| No repo, wrong repo, or terminal linked PR | `BLOCKED`. Ask for a correctly attached session; don't work around it with a clone, new auth, or a branch switch. |
| Task already in flight under an earlier brief | Finish or reconcile in that original lane with the same scope, branch and base. No new standalone Captain assignments. |

## 1. Resolve the GitHub brief before editing

Use a separate verified clone of `Keshab1997/agent-bootstrap` for these tools
and docs (normally `/home/user/agent-bootstrap`). Verify origin (if an Arena
snapshot dropped `.git/config`, restore `https://github.com/Keshab1997/agent-bootstrap.git`
only when `origin` is absent) and fast-forward clean `main` before every new
batch. If dirty, or if bootstrap is itself the attached target checkout, read
the current playbook from a separate fresh read-only clone (e.g. under `/tmp`).
Never switch the attached target checkout for this update.

The Captain's launch line gives the target repo, worker letter and pinned
`BRIEF.md` link. Follow [the GitHub brief fetch steps](GITHUB_BRIEFS.md#2-worker-attach-the-target-repo-then-read-the-pinned-docs).
Read the Markdown and use the unchanged `task.json` from the same commit.
The brief's docs ref is **not** a working branch. Use the attached repo's
existing authorized access; no device flow, credential copying or replacement.

## 2. Per task: start → edit → check → diff → publish

Set `checkout` to the verified Arena app checkout root, `lane` to the tool in
the separate bootstrap clone, `task` to the saved `task.json`, and `workbench`
to the path used to fetch it. Reuse those exact paths on each command (set
the variables again if your tool starts a new shell):

```bash
python3 -B "$lane" --checkout "$checkout" --root "$workbench" start "$task"
```

Use the printed `workdir`; read its `AGENTS.md` if present. If the target is
`flutter-builder` or uses an older installed agent pack, any direct-to-`main`
loop in that file is for independent work only. For a Captain task, use the
JSON gate and this lane, not `tool/agent_loop.py`. Edit only the exact
`allowed` paths. Do not stage, commit by hand, touch the brief files, edit
`main`, or switch branches. Run separately in order, only if the
previous step succeeded, and **read** the diff before publishing:

```bash
python3 -B "$lane" --checkout "$checkout" --root "$workbench" check "$task"
python3 -B "$lane" --checkout "$checkout" --root "$workbench" diff "$task"
python3 -B "$lane" --checkout "$checkout" --root "$workbench" publish "$task"
```

The tool checks changed paths, common credential patterns, the exact tested
Git tree and the remote ref. Read the diff yourself; the credential check is
only a backstop. A push can start configured automatic checks; don't dispatch
or wait for CI. After `AGENT … PUSHED`, [post the approved mention](GITHUB_BRIEFS.md#3-worker-report-and-mention-only-after-verification)
with the exact checkpoint block and link. If comment access is unavailable,
return the block in Arena with `MENTION PENDING`, not a false mention. Report
`BLOCKED` with the reason when code has not pushed.

Interrupted or resumed in a restored sandbox? Keep the same permalink, task
JSON, checkout and workbench, and update the separate `agent-bootstrap` clone
first. If Arena wakes a linked session with local `HEAD` back at an earlier
ancestor commit while GitHub's `arena/*` branch is at the verified checkpoint
and the restored files carry no unsaved divergence, `worker_lane.py` fast-forwards
the existing branch ref cleanly (logging `restored_from:`) and preserves any
in-scope edits. Never run manual `git reset` on the attached checkout yourself:
if any file differs from the verified checkpoint, or for wrong origin, moved
refs or lost access, leave the worktree untouched and report `BLOCKED`. Existing
manual tasks use their [original handoff](LEGACY_WORKER_BRIEF.md).

### Check profiles

| `check` value | Runs |
|---|---|
| `{"kind":"preflight"}` | `python3 -B tool/preflight.py`; suitable only when it covers the task |
| `{"kind":"flutter","version":"3.50.0","test":"test/home_screen_test.dart"}` | Exact named SDK, `flutter pub get --enforce-lockfile`, format changed Dart source, preflight if present, then `flutter test --no-pub` on one test file |
| `{"kind":"pytest","target":"tests"}` | `python3 -m pytest -q tests` (or one named Python test under `test/` or `tests/`) |
| `{"kind":"selftest"}` | `python3 -B selftest.py` |

Use the actual repo's gate. The Flutter version shown is an example, **not** a
global default. Pin a compatible stable SDK, not the minimum. The lockfile
must not change. For a gate outside these profiles, have the Captain specify
a reviewed linked manual check; do not substitute an unrelated passing gate.
No builds or full test battery by default.

Flutter is skipped for other profiles. On Linux x86-64 a cold SDK is from
Google's official manifest/archive with SHA-256 verification; an exact
trusted SDK on PATH or a valid local cache is reused. The warmed SDK and pub
cache live under `/var/tmp/agent-bootstrap-flutter-<uid>`, not in the repo.
Arena can discard that cache between turns or chats. If an attached Arena
sandbox blocks outbound TLS to `storage.googleapis.com`, report `BLOCKED`; the
Captain can publish a newly pinned `task.json` with `{"kind":"preflight"}` for
the worker checkpoint and run the full Flutter gate during Captain review before
landing (workers never edit `task.json` themselves).

## 3. Captain: verify, review, then assign the next task

1. Keep a ledger **outside app repos**: `repo | worker | task | brief URL/SHA |
   tracker/report | branch | base_sha | sha | review/landed/blocked |
   integration_sha`. Retain the original task JSON. Assign up to three
   disjoint filesets in parallel, one live task per worker. On a check-in read
   the tracker; if a mention is pending, use the worker's report and post it
   only after verification with approved access. No cross-chat polling is
   implied.
2. In a separate verified Captain checkout, fetch and verify the exact server
   ref and scope. Use the original JSON from the pinned docs commit, never a
   spec generated from the worker's diff. Set `branch`, `base` and `tip` from
   the handoff, and `lane` to `captain/worker_lane.py` in your verified
   bootstrap checkout:

   ```bash
   python3 -B "$lane" \
     --checkout "$captain_repo" --branch "$branch" --base "$base" --tip "$tip" \
     review "$original_task_json"
   ```

   Read the patch, check scope and secrets, and run the integration gate on
   fresh `main` before landing. Use [range-only integration](CAPTAIN_PROMPT.md#2d-integrate--one-reviewed-workstream-at-a-time):
   `main` never points at the actual linked worker commits mid-lane. Apply
   only the reviewed base-to-tip delta as a new Captain commit if authorized;
   use a Captain review branch if PRs are required.
3. For the next task in that chat, publish a **new** pinned GitHub brief with
   the exact same branch and last Captain-verified pushed SHA as `base_sha`.
   If required upstream changes aren't in that checkout, wait or start a
   fresh properly attached chat at current `main`. Do not rebase or reset the
   old chat to update it. Fix a pushed task with a new corrective checkpoint,
   not an amend; review the combined effect before landing dependent work.

## 4. Finalize only when explicitly asked

**`Finalize batch <id>`** is a Captain decision, not a worker command. Freeze
new assignments, verify the report and exact ref of each task, and show what's
landed, pending and blocked. Prefer a Captain-owned integration PR containing
only remaining reviewed changes. If using a linked PR at batch end, verify
its **whole** diff against current `main`; it must not include already landed,
rejected, or unreviewed work. Confirm all worker edits are pushed; get
Keshab's go-ahead for that terminal action. Don't delete worker branches or
dispatch CI.

For a replacement chat, attach the **same target repo** in Arena, then use
only the Captain's newly pinned brief link and worker letter. The Captain
records the previous verified checkpoint in the ledger; an old branch tip
is not a base for an unrelated new chat. No files or credentials are relayed.
