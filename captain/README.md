# Captain: one chat per worker, multiple task checkpoints

Keshab works through the Captain. Up to three workers get disjoint file lists;
workers publish tested branch checkpoints, and the Captain reviews only the
reported base-to-tip range. No app-file download/upload between chats.

**Do not merge or close a linked Arena PR per task.** That ends push access
from its chat. Keep that branch for the next safe task; finalize at the end of
the batch. An ordinary chat with no repo attached can instead use its own
approved GitHub access and a fresh task branch per task.

1. Start the Captain with [`CAPTAIN_START_PROMPT.md`](../CAPTAIN_START_PROMPT.md).
2. Use [Fast Lane](FASTLANE.md) and the [compact brief](WORKER_BRIEF_TEMPLATE.md)
   for new work. Resume old in-flight work without resetting it.
3. Relay `AGENT … PUSHED` or `BLOCKED`. The Captain verifies, reviews, and
   assigns the next brief without requiring a linked PR merge.

| File | Purpose |
|---|---|
| [HOW_TO_START_BN.md](HOW_TO_START_BN.md) | মানুষের জন্য ধাপে ধাপে ব্যবহার |
| [CAPTAIN_PROMPT.md](CAPTAIN_PROMPT.md) | Scope, review, integration, and finalization rules |
| [`worker_lane.py`](worker_lane.py) | Start, check, diff, publish, and fetch-only review |
| [`flutter_sdk.py`](flutter_sdk.py) | Exact Flutter SDK installation/reuse for Flutter profiles |
| [`examples/`](examples/) | Three compatible, file-disjoint example briefs |
| [LEGACY_WORKER_BRIEF.md](LEGACY_WORKER_BRIEF.md) | Manual branch handoff for work already started |

No shared tokens, settings changes, releases, or manual CI dispatch by workers.
