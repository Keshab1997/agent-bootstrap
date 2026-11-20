# Captain: GitHub briefs for Arena-linked workers

Keshab gives work to one Captain. The Captain publishes up to three big,
disjoint assignments at a time as pinned docs in the target repo, and works
its own lane in parallel ([Speed rules](CAPTAIN_PROMPT.md#speed-rules--keshabs-top-priority)). Workers attach that
repo in Arena, read the brief from GitHub, and push tested checkpoints on their
real `arena/*` branches. No brief or app file uploads between chats.

1. Start with [`CAPTAIN_START_PROMPT.md`](../CAPTAIN_START_PROMPT.md).
2. [Publish a brief](GITHUB_BRIEFS.md) and pass its one-line link to a worker
   chat with the target repo attached. No new task in an unattached chat.
3. Worker runs [Fast Lane](FASTLANE.md). After a verified push, the worker
   mentions `@Keshab1997` on the approved tracker when permitted, or reports
   `MENTION PENDING` in Arena. The Captain reviews only the task's exact range.
4. Keep live Arena branches for the next safe checkpoint. **Merging or closing
   a linked PR ends pushes from that chat**; finalize only when asked.

| File | Purpose |
|---|---|
| [HOW_TO_START_BN.md](HOW_TO_START_BN.md) | মানুষের জন্য ধাপে ধাপে ব্যবহার |
| [CAPTAIN_PROMPT.md](CAPTAIN_PROMPT.md) | Scope, review, integration and finalization rules |
| [WORKER_BRIEF_TEMPLATE.md](WORKER_BRIEF_TEMPLATE.md) | `BRIEF.md` + `task.json` template |
| [`worker_lane.py`](worker_lane.py) | Start, check, diff, publish, and fetch-only review |
| [`flutter_sdk.py`](flutter_sdk.py) | Pinned Flutter SDK setup for Flutter profiles |
| [`examples/`](examples/) | Three compatible, file-disjoint example briefs |
| [LEGACY_WORKER_BRIEF.md](LEGACY_WORKER_BRIEF.md) | Manual handoff only for work already started |

No shared tokens, settings changes, releases, or manual CI dispatch by workers.
