# Worker Fast Lane: Device Flow brief → verified checkpoint

**Fast delivery:** Read `captain/SPEED_POLICY.md` in agent-bootstrap (or
[SPEED_POLICY.md](SPEED_POLICY.md) from this folder). One pinned worker gate,
one narrow integration check, no repeated full suites. Flutter tests fail fast:
30s per test, 120s process wall limit. On timeout report BLOCKED; after two
unsuccessful corrective attempts stop the loop. Preserve edits and never bypass
scope, approvals, secrets or a failed gate. Existing pinned task specs remain
binding; Captain must explicitly supersede them, not silently drop acceptance.


[বাংলায় শুরু করুন](HOW_TO_START_BN.md) · [Worker starter](WORKER_START_PROMPT.md) · [GitHub briefs](GITHUB_BRIEFS.md) · [Captain playbook](CAPTAIN_PROMPT.md)

**Device Flow (`gh_app.py connect`) is the primary worker mode.** Workers do
**not** need to attach the target repo in Arena Agent Mode, have no 1-PR
dead-end limit, and can keep one paired chat alive across tasks and repos.
(Optional Arena-attached `arena/*` chats remain supported when a brief
specifies `"arena"`.)

| Worker chat | Action |
|---|---|
| Unattached chat paired via Device Flow (`gh_app.py status` → `PAIRED`) | Primary lane: run `fetch-brief` → `start` → edit → `check` → `diff` → `publish` → `mention` on `agent/<W>/<task>`. |
| Attached chat with `"arena"` in `task.json` | Optional linked mode: pass `--checkout <repo_root>` to `worker_lane.py`; stay on its `arena/*` branch and never open/merge/close its linked PR. |
| Task already in flight under an earlier brief | Finish or reconcile in that original lane with the same scope, branch and base. |

## 1. Boot & pair once per worker workspace

Keep `agent-bootstrap` at `/home/user/agent-bootstrap`. Run `bash worker_up.sh`
(or `python3 /home/user/agent-bootstrap/gh_app.py connect` if already cloned):

- If `ALREADY CONNECTED -- device flow skipped`, ask Keshab nothing.
- If a code like `XXXX-XXXX` prints, show it prominently (`Open https://github.com/login/device and enter XXXX-XXXX`); resume interrupted polls with `python3 /home/user/agent-bootstrap/device_pair.py poll 60`.
- Fast-forward clean `main` before each new batch (`git -C /home/user/agent-bootstrap pull --ff-only origin main`).

## 2. Fetch the Captain's pinned brief

The Captain's launch line gives a commit-pinned `BRIEF.md` URL. Fetch and
verify it in one command (downloads `BRIEF.md` and `task.json` into
`~/agent-workbench/inbox/...` and checks that the commit belongs to
`captain/briefs/<batch>`):

```bash
lane=/home/user/agent-bootstrap/captain/worker_lane.py
python3 -B "$lane" fetch-brief --url "<BRIEF_URL>"
```

Read `BRIEF.md` and keep `task.json` unchanged. Do not edit brief files.

## 3. Per task: start → edit → check → diff → publish → mention

Set `task` to the downloaded `task.json` path (pass `--checkout "$checkout"`
only when the brief specifies `"arena"`):

```bash
python3 -B "$lane" start "$task"
```

Use the printed `workdir` (`~/agent-workbench/repos/<W>/<repo>` in Device Flow
mode); read its `AGENTS.md` if present. Any direct-to-`main` / `tool/agent_loop.py`
rule in `AGENTS.md` is for independent work only — for a Captain task, follow
the brief's JSON gate and `worker_lane.py`.

Edit **only** the exact `allowed` paths. Finish every acceptance item before
`check`, deciding details inside those paths yourself. Do not stage, commit by
hand, touch the brief files, edit `main`, or switch branches. Run in order,
and **read** the diff before publishing:

```bash
python3 -B "$lane" check "$task"
python3 -B "$lane" diff "$task"
python3 -B "$lane" publish "$task"
```

If `task.json` has `"tracker"` (or the brief gives an approved tracking issue URL):

```bash
python3 -B "$lane" mention "$task" --brief-url "<BRIEF_URL>"
```

`mention` checks for existing comments to avoid duplicates and posts
`@Keshab1997 — checkpoint ready for review` with the verified `AGENT <W> PUSHED`
block and commit link via `gh_app.py`. If no tracker is configured, return the
`PUSHED` block and commit URL directly in the worker chat. Report `BLOCKED`
with the reason if the code could not be pushed.

Interrupted or resumed in a restored sandbox? Keep the same `task.json`,
workbench (`~/agent-workbench`), and `agent-bootstrap` clone. In Device Flow
mode, `worker_lane.py` restores `.git/config` automatically from `.origin.json`
when Arena snapshots drop it between turns. In optional Arena-linked mode,
`worker_lane.py` fast-forwards an ancestor `HEAD` cleanly when safe. Never run
manual `git reset`.

### Check profiles

| `check` value | Runs |
|---|---|
| `{"kind":"preflight"}` | `python3 -B tool/preflight.py`; suitable only when it covers the task |
| `{"kind":"flutter","version":"3.50.0","test":"test/home_screen_test.dart"}` | Exact SDK, locked pub get, changed-file format, preflight, then ONE test file with `--fail-fast --timeout 30s`; 120s test-process wall limit |
| `{"kind":"pytest","target":"tests"}` | `python3 -m pytest -q tests` (or one named Python test under `test/` or `tests/`) |
| `{"kind":"selftest"}` | `python3 -B selftest.py` |

Use the actual repo's gate. The Flutter version shown is an example, **not** a
global default. Pin a compatible stable SDK, not the minimum. The lockfile
must not change. No builds or full test battery by default.

On Linux x86-64 a cold Flutter SDK is downloaded from Google's official manifest
with SHA-256 verification under `/var/tmp/agent-bootstrap-flutter-<uid>`. If a
worker sandbox blocks outbound TLS to `storage.googleapis.com`, report `BLOCKED`;
the Captain can publish a newly pinned `task.json` with `{"kind":"preflight"}`
and run the Flutter gate during Captain review before landing.

## 4. Captain: verify, review, then assign the next task

1. Keep a ledger **outside app repos**: `captain/ledger.py` writes to
   `captain/LEDGER.json` (gitignored) and `captain/batch_status.py` diffs the
   ledger against live GitHub `agent/*` + `arena/*` refs, tracker mentions, and
   CI runs in one call; see [LEDGER.md](LEDGER.md).
2. In a separate Captain checkout, verify the exact remote ref, base, and scope
   using the original `task.json` from the pinned docs commit:

   ```bash
   python3 -B "$lane" \
     --checkout "$captain_repo" --branch "$branch" --base "$base" --tip "$tip" \
     review "$original_task_json"
   ```

   Once this passes, publish the worker's next big brief right away (Speed rule 5):
   - In Device Flow mode, omit `"base_sha"` to start from current `main`, or
     set `"base_sha": "<verified_tip>"` (and `"base_branch": "agent/<W>/<prev_task>"`
     if not yet integrated into `main`) to stack on the unmerged checkpoint.
   - Then inspect the patch, run the integration gate on `main`, and integrate
     the reviewed `base..tip` diff.

## 5. Finalize only when explicitly asked

**`Finalize batch <id>`** is a Captain decision, not a worker command. Freeze
new assignments, verify every expected checkpoint, and show what's landed,
pending, and blocked. In Device Flow mode there are no terminal linked PRs;
you can integrate remaining reviewed `agent/*` commits onto `main` (or into a
single Captain PR if branch rules require PRs).
