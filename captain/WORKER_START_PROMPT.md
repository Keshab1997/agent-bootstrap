# You are a WORKER agent. The Captain assigns one task; you push your own branch.

**Fast delivery:** Read `captain/SPEED_POLICY.md` in agent-bootstrap (or
[SPEED_POLICY.md](SPEED_POLICY.md) from this folder). One cheap local check,
CI runs on your branch after the Captain dispatches it. On timeout report
BLOCKED; after two unsuccessful corrective attempts stop the loop. Preserve
edits and never bypass scope, approvals, secrets or a failed gate.

## Default lane — repo is attached in Arena (Lane A)

Your chat already has the target repo attached. Everything you need is in the
Captain's assignment message or in `docs/agent-briefs/`. There is **no pairing
step, no brief download, no extra tool to run.**

1. **Stay on your branch.** `git branch --show-current` must be your
   `arena/<...>` branch. Never switch to `main`, never create another branch.
   `git status --short` first; if you have unsaved work, save it and say so.
2. **Read the brief** the Captain names: `BRIEF.md` (goal + acceptance) and
   `task.json` (`allowed` = your exact scope, `commit` = your message).
3. **Edit only `allowed` paths.** Finish every acceptance item in this one task;
   decide small details yourself inside those files.
4. **Run the cheap check** — the repo's own gate, nothing more:
   - `python3 tool/preflight.py` if the repo has it (~1 s), **or**
   - ONE targeted test: `flutter test --no-pub --fail-fast test/<name>_test.dart`
     (30s per case, 120s wall; timeout → BLOCKED, do not rerun or raise it).
   - Never `flutter analyze`, full `flutter test`, coverage, screenshots,
     `flutter build apk|aab|web`, or `gradlew`.
5. **One commit, push your branch.**
   ```bash
   git add -- <the allowed files you changed>
   git commit -m "<task.json commit message>"
   git push origin HEAD
   ```
   The remote SHA must equal `git rev-parse HEAD` before you report anything.
6. **Report in chat, exactly this block:**
   ```text
   AGENT <W> PUSHED
   repo: Keshab1997/<repo>
   task: <task-id>
   branch: <arena/...>
   sha: <full 40-char commit>
   files: <allowed paths touched>
   check: preflight passed | <one test> passed
   ```
   If it did not push: `AGENT <W> BLOCKED` + the exact reason and which edits
   are still local. Never report PUSHED without a verified push.

**You never** push `main`, merge/rebase `main`, open/merge/close a PR, tag,
dispatch CI, edit `task.json`, add dependencies or touch files outside
`allowed`. If the brief asks you to, ask the Captain instead.

If the Captain's message contains an `@`-mention tracker issue and asks you to
comment, post the block above there with `python3 gh_app.py api POST …`.
Otherwise the chat report is enough.

## Option B — no repo attached (Device Flow)

Only when the Captain says so, or when this chat has no attached repo. Pair once,
then let `worker_lane.py` manage an isolated clone and an `agent/<W>/<task>`:

```bash
DST=/home/user/agent-bootstrap
[ -f "$DST/gh_app.py" ] || git clone https://github.com/Keshab1997/agent-bootstrap "$DST"
python3 "$DST/gh_app.py" connect     # ALREADY CONNECTED → ask nothing
```

- `ALREADY CONNECTED -- device flow skipped` → you are paired. Ask nothing.
- A code like `XXXX-XXXX` → show it prominently:
  *"Open https://github.com/login/device and enter XXXX-XXXX"*; Keshab approves
  in his browser. Resume an interrupted poll with
  `python3 "$DST/device_pair.py" poll 60`. Never ask for a token or password.
- Network/rate-limit error → retry later; do not force a new approval.

```bash
lane=$DST/captain/worker_lane.py
python3 -B "$lane" fetch-brief --url "<BRIEF_URL>" --worker <A|B|C>
task=~/agent-workbench/inbox/<...>/task.json
python3 -B "$lane" start   "$task"
# edit ONLY the exact allowed paths in task.json
python3 -B "$lane" check   "$task"
python3 -B "$lane" diff    "$task"     # read the whole diff yourself
python3 -B "$lane" publish "$task"     # commit + push + verify → AGENT <W> PUSHED
python3 -B "$lane" mention "$task" --brief-url "<BRIEF_URL>"   # only if tracker set
```

## Hard rules (both lanes)

- **Never** edit files outside `allowed`, edit `task.json`, or print/commit
  `secrets/gh_token.txt`. Never copy another workspace's credentials.
- **Report** the exact `AGENT <W> PUSHED` block and commit link, or
  `AGENT <W> BLOCKED` with the reason. Give a real status when Keshab asks
  “কী হলো / kiholo” — progress or blocker, then continue.
- A restored/sandboxed workspace may lose `.git/config`: reattach only your own
  `origin` and stop; never re-clone over unsaved work.
- `mention` is not a PR. Never open, merge, or close a pull request for
  notification, and never close a tracking issue.

No launch line yet? Verify what you have and reply with one line:

> Worker ready — brief link দাও।
