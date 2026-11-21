# Captain: repo-attached workers, pushed branches, Captain-run CI

Keshab gives work to one Captain. **The default flow is the Arena lane:**
Keshab attaches the target repo in each worker chat, the Captain sends one
self-contained assignment message (brief + `task.json`), the worker edits
`allowed` files, runs one cheap check and pushes **its own `arena/*` branch**,
and the Captain reviews the diff, **runs CI on that branch**, fixes small reds,
and lands the change on `main`. Up to three big, file-disjoint tasks at a time;
the Captain works its own lane in parallel
([Speed rules](CAPTAIN_PROMPT.md#speed-rules--keshabs-top-priority)).

That is the only lane — there is no pairing step, no brief download tool and no
second branch naming scheme to remember.

1. Start Captain with [`CAPTAIN_START_PROMPT.md`](../CAPTAIN_START_PROMPT.md) (or `captain_up.sh`).
2. Start Workers with [`WORKER_START_PROMPT.md`](WORKER_START_PROMPT.md).
3. [Publish a brief](GITHUB_BRIEFS.md) and paste ONE assignment message into the attached worker chat.
4. Worker edits → one cheap check → `git push origin HEAD` → `AGENT A PUSHED` ([Fast Lane](FASTLANE.md)).
5. Captain verifies the exact `base..tip`, runs CI (`ci_dispatch.py --ref <branch> --logs`), fixes reds, lands on `main`, and sends the next big task.

| File | Purpose |
|---|---|
| [HOW_TO_START_BN.md](HOW_TO_START_BN.md) | মানুষের জন্য ধাপে ধাপে ব্যবহার |
| [WORKER_START_PROMPT.md](WORKER_START_PROMPT.md) | Copy-paste starter for a worker chat |
| [CAPTAIN_PROMPT.md](CAPTAIN_PROMPT.md) | Scope, review, integration and finalization rules |
| [`task_spec.py`](task_spec.py) | Validate a brief's `task.json` before publishing |
| [WORKER_BRIEF_TEMPLATE.md](WORKER_BRIEF_TEMPLATE.md) | `BRIEF.md` + `task.json` template |

No shared tokens between workspaces, no settings changes, no releases, and no manual CI dispatch by workers.

## Fast execution

Read [SPEED_POLICY.md](SPEED_POLICY.md): one cheap local check for the worker,
one CI run on the pushed branch by the Captain, no debugging loops and no
redundant full-suite local runs. Worker Flutter tests have a 120s process wall
limit and 30s per-test timeout; timeout never counts as a pass.
