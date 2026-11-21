# Captain: GitHub briefs for Device-Flow (and optional Arena) workers

Keshab gives work to one Captain. Both the Captain and Workers connect via
**GitHub Device Flow** (`gh_app.py connect`) — no Arena repo attachment
needed, no 1-PR limit, and one paired worker chat works across tasks and repos.
The Captain publishes up to three big, disjoint assignments at a time as
pinned docs in the target repo, and works its own lane in parallel
([Speed rules](CAPTAIN_PROMPT.md#speed-rules--keshabs-top-priority)).
Workers fetch the brief from GitHub, test in an isolated clone, push to
`agent/<worker>/<task>`, and mention `@Keshab1997` via `gh_app.py`.
(Arena-attached `arena/*` chats remain supported as an optional mode.)

1. Start Captain with [`CAPTAIN_START_PROMPT.md`](../CAPTAIN_START_PROMPT.md) (or `captain_up.sh`).
2. Start Workers with [`WORKER_START_PROMPT.md`](WORKER_START_PROMPT.md) (or `worker_up.sh`).
3. [Publish a brief](GITHUB_BRIEFS.md) and pass its one-line link to the worker chat.
4. Worker runs `fetch-brief` → `start` → edit → `check` → `diff` → `publish` → `mention` ([Fast Lane](FASTLANE.md)).
5. Captain reviews only the task's exact `base..tip` range (`worker_lane.py review`), integrates into `main`, and assigns the next big brief (chaining with `base_sha`/`base_branch` if needed).

| File | Purpose |
|---|---|
| [HOW_TO_START_BN.md](HOW_TO_START_BN.md) | মানুষের জন্য ধাপে ধাপে ব্যবহার |
| [WORKER_START_PROMPT.md](WORKER_START_PROMPT.md) | Copy-paste starter for Device-Flow workers |
| [CAPTAIN_PROMPT.md](CAPTAIN_PROMPT.md) | Scope, review, integration and finalization rules |
| [WORKER_BRIEF_TEMPLATE.md](WORKER_BRIEF_TEMPLATE.md) | `BRIEF.md` + `task.json` template |
| [`worker_lane.py`](worker_lane.py) | Fetch brief, start, check, diff, publish, mention, and review |
| [`flutter_sdk.py`](flutter_sdk.py) | Pinned Flutter SDK setup for Flutter profiles |
| [`examples/`](examples/) | Three compatible, file-disjoint example briefs |
| [LEGACY_WORKER_BRIEF.md](LEGACY_WORKER_BRIEF.md) | Manual handoff only for work already started |

No shared tokens between workspaces, no settings changes, no releases, and no manual CI dispatch by workers.

## Fast execution

Read [SPEED_POLICY.md](SPEED_POLICY.md): one bounded gate, no debugging loops,
no redundant full-suite integration checks. Worker Flutter tests have a 120s
process wall limit and 30s per-test timeout; timeout never counts as a pass.
